#!/usr/bin/env python3
"""
download_images.py — Lädt Bildkandidaten für Rezept-PDFs robust herunter.

Nimmt eine oder mehrere URLs und speichert sie als cand1.jpg, cand2.jpg, …
in ein Zielverzeichnis. Setzt einen realistischen User-Agent (viele
Bildhoster blocken sonst), macht Retries bei Timeouts und konvertiert
alle Formate mit Pillow nach JPEG, damit der PDF-Generator immer
dasselbe Format bekommt.

Beispielaufrufe:

    # Drei URLs:
    python download_images.py \\
        --out /sessions/pensive-amazing-hypatia/.img-candidates \\
        "https://site1.de/foto.jpg" \\
        "https://site2.de/image.png" \\
        "https://cdn.site3.com/abc.webp"

    # Oder URLs aus stdin (eine pro Zeile):
    cat urls.txt | python download_images.py --out /tmp/imgs

Rückgabe (stdout): eine Zeile pro erfolgreich gespeicherter Datei mit Pfad.
Nicht erreichbare URLs werden auf stderr protokolliert, unterbrechen
den Lauf aber nicht. Exitcode 0, wenn mindestens ein Bild geladen wurde.
"""

from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image, UnidentifiedImageError


# Realistischer Desktop-User-Agent. Viele Bildhoster liefern sonst 403 —
# gerade Rezeptseiten mit Bildrechte-Hinweisen. Keine „bot"-ähnliche
# Signatur verwenden.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 20        # Sekunden
MAX_RETRIES = 2             # zusätzliche Versuche nach dem ersten
RETRY_SLEEP = 1.5           # Sekunden zwischen Retries
MAX_BYTES = 12 * 1024 * 1024  # Bilder über 12 MB als Fehler behandeln
MIN_BYTES = 1024              # Unter 1 KB ist vermutlich kein echtes Bild
TARGET_MAX_WIDTH = 2000       # Bilder auf diese Breite verkleinern (PDF braucht nicht mehr)


def fetch_url(url: str) -> bytes:
    """Lädt eine URL, mit Retries und ordentlichen Fehlern."""
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.8",
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
                },
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                data = r.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError(f"Datei > {MAX_BYTES // (1024 * 1024)} MB, abgelehnt")
                if len(data) < MIN_BYTES:
                    raise ValueError(f"Datei < {MIN_BYTES} B — vermutlich keine Bilddatei")
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP)
                continue
            break
    assert last_err is not None
    raise last_err


def convert_to_jpeg(raw: bytes) -> bytes:
    """Nimmt die Rohbytes (beliebiges Bildformat) und liefert JPEG-Bytes.

    Pillow versteht PNG/WebP/AVIF (mit pillow-avif)/JPEG/GIF. Wenn das Bild
    breiter als TARGET_MAX_WIDTH ist, wird es verkleinert — sonst wird die
    PDF unnötig groß.
    """
    img = Image.open(io.BytesIO(raw))
    img.load()
    # RGB erzwingen (JPEG kann kein Alpha)
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > TARGET_MAX_WIDTH:
        ratio = TARGET_MAX_WIDTH / img.width
        new_size = (TARGET_MAX_WIDTH, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def collect_urls(cli_urls: list[str]) -> list[str]:
    """URLs aus CLI-Argumenten oder stdin kombinieren."""
    urls = [u.strip() for u in cli_urls if u.strip()]
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    # Duplikate entfernen, Reihenfolge erhalten
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def download_all(urls: list[str], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for idx, url in enumerate(urls, start=1):
        dst = out_dir / f"cand{idx}.jpg"
        try:
            print(f"[{idx}/{len(urls)}] Lade {url}", file=sys.stderr)
            raw = fetch_url(url)
            jpeg = convert_to_jpeg(raw)
            dst.write_bytes(jpeg)
            saved.append(dst)
            print(str(dst))  # stdout: der Pfad zum Weiterverarbeiten
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"  → fehlgeschlagen ({e}). Überspringe.", file=sys.stderr)
        except UnidentifiedImageError:
            print(f"  → kein Bildformat erkannt. Überspringe.", file=sys.stderr)
        except Exception as e:  # pragma: no cover
            print(f"  → Fehler: {e}. Überspringe.", file=sys.stderr)
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Rezept-Bildkandidaten herunterladen.")
    parser.add_argument("urls", nargs="*", help="Bild-URLs. Alternativ/zusätzlich via stdin.")
    parser.add_argument(
        "--out",
        default="/sessions/pensive-amazing-hypatia/.img-candidates",
        help="Zielverzeichnis (Default: /sessions/pensive-amazing-hypatia/.img-candidates)",
    )
    args = parser.parse_args()

    urls = collect_urls(args.urls)
    if not urls:
        print("Keine URLs angegeben. Nutze entweder Positionsargumente oder stdin.", file=sys.stderr)
        return 2

    saved = download_all(urls, Path(args.out))
    if not saved:
        print("Kein Bild erfolgreich geladen.", file=sys.stderr)
        return 1
    print(f"\n{len(saved)} von {len(urls)} Bildern gespeichert in {args.out}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
