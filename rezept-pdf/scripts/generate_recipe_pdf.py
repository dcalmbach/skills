#!/usr/bin/env python3
"""
generate_recipe_pdf.py — Erzeugt ein Rezept-PDF im festen Magazin-Layout.

Eingabe: JSON-Datei mit Rezeptdaten + optional ein Bildpfad (oder URL).
Ausgabe: einseitiges PDF im A4-Format.

Das Layout ist bewusst fix, damit alle Rezepte im Rezeptbuch einheitlich
aussehen. Details siehe references/template-design.md.

Beispielaufruf:
    python generate_recipe_pdf.py \
        --json recipe.json \
        --image hero.jpg \
        --output /Rezepte/spaghetti-carbonara.pdf

recipe.json:
    {
      "title": "Spaghetti Carbonara",
      "prep_time": "15 Minuten",
      "cook_time": "20 Minuten",
      "servings": 4,
      "ingredients": ["400 g Spaghetti", "150 g Pancetta", ...],
      "directions": ["Wasser zum Kochen bringen...", ...],
      "nutrition_per_serving": {
        "kcal": 620, "protein_g": 28, "fat_g": 24,
        "carbs_g": 72, "fiber_g": 3,
        "source": "schaetzung"
      }
    }
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image


# ---------- Designkonstanten (Template-Farben, Abstände) ----------

BAR_BLUE = HexColor("#1F3B5F")      # Dezenter Dunkelblau für den Kopfbalken
BODY_TEXT = HexColor("#3A3A3A")      # Haupttext — nicht reines Schwarz
MUTED_TEXT = HexColor("#6A6A6A")     # Unterzeile, Seitenzahl
SEPARATOR = HexColor("#CFCFCF")      # Vertikale Trennlinie

PAGE_MARGIN = 40                     # Seitenrand links/rechts (pt)
TOP_BAR_H = 6                        # Höhe blauer Kopfbalken
TITLE_FONT = "Times-Bold"            # Serif, fett — für Titel
SECTION_FONT = "Times-Bold"          # Überschriften Zutaten/Zubereitung
BODY_FONT = "Helvetica"              # Fließtext
TITLE_SIZE = 26
SECTION_SIZE = 14
BODY_SIZE = 10
SUBTITLE_SIZE = 11


# ---------- Hilfsfunktionen ----------

def slugify(text: str) -> str:
    """Dateinamentauglicher Slug aus Titel erzeugen.

    Ersetzt Umlaute, macht alles kleinbuchstabig und nimmt Bindestriche.
    """
    text = text.lower()
    for a, b in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "rezept"


def fetch_image(image_path_or_url: str, scratch_dir: Path) -> Path:
    """Wenn image_path_or_url eine URL ist, lokal runterladen; sonst Pfad zurückgeben."""
    if image_path_or_url.startswith(("http://", "https://")):
        scratch_dir.mkdir(parents=True, exist_ok=True)
        dst = scratch_dir / "hero_download.jpg"
        req = urllib.request.Request(
            image_path_or_url,
            headers={"User-Agent": "Mozilla/5.0 (recipe-pdf)"}
        )
        with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as f:
            f.write(r.read())
        return dst
    return Path(image_path_or_url)


def wrap_text(text: str, font_name: str, font_size: int, max_width: float, c: canvas.Canvas) -> list[str]:
    """Bricht Text in Zeilen um, die in max_width passen."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            # Wort selbst zu lang? Hart umbrechen, sonst verliert man es.
            if c.stringWidth(word, font_name, font_size) > max_width:
                lines.append(word)
                current = []
            else:
                current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_image_cover(c: canvas.Canvas, img_path: Path, x: float, y: float, w: float, h: float) -> None:
    """Zeichnet Bild 'object-fit: cover' — Box füllen, Überhang beschneiden."""
    img = Image.open(img_path)
    iw, ih = img.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        # Bild breiter als Box → links/rechts beschneiden
        new_w = int(ih * box_ratio)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        # Bild höher als Box → oben/unten beschneiden
        new_h = int(iw / box_ratio)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, width=w, height=h, mask="auto")


# ---------- PDF-Erzeugung ----------

def generate_recipe_pdf(recipe: dict, image_path: Path | None, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_w, page_h = A4

    # --- Blauer Kopfbalken oben ---
    c.setFillColor(BAR_BLUE)
    c.rect(0, page_h - TOP_BAR_H, page_w, TOP_BAR_H, fill=1, stroke=0)

    # --- Titel + Untertitel (Zeiten) ---
    title_y = page_h - 58
    c.setFillColor(black)
    c.setFont(TITLE_FONT, TITLE_SIZE)
    c.drawString(PAGE_MARGIN, title_y, recipe["title"])

    subtitle_parts = []
    if recipe.get("prep_time"):
        subtitle_parts.append(f"Vorbereitung {recipe['prep_time']}")
    if recipe.get("cook_time"):
        subtitle_parts.append(f"Kochzeit {recipe['cook_time']}")
    if subtitle_parts:
        c.setFont(BODY_FONT, SUBTITLE_SIZE)
        c.setFillColor(BODY_TEXT)
        c.drawString(PAGE_MARGIN, title_y - 18, "  |  ".join(subtitle_parts))

    # --- Hero-Bild ---
    img_y_top = title_y - 35
    img_h = 290
    img_y = img_y_top - img_h
    img_w = page_w  # Vollbreite wie im Template
    if image_path and image_path.exists():
        try:
            draw_image_cover(c, image_path, 0, img_y, img_w, img_h)
        except Exception as e:
            print(f"Warnung: Bild konnte nicht geladen werden ({e}). Fahre ohne Bild fort.", file=sys.stderr)
            _draw_image_placeholder(c, 0, img_y, img_w, img_h)
    else:
        _draw_image_placeholder(c, 0, img_y, img_w, img_h)

    # --- Zwei Spalten: Zutaten (links) + Zubereitung (rechts) ---
    col_top = img_y - 30
    # Platz unten reservieren: Seitenzahl + (optional) Nährwerte-Footer
    has_nutrition = bool(recipe.get("nutrition_per_serving"))
    bottom_margin = 95 if has_nutrition else 55

    # Linke Spalte: Zutaten
    left_x = PAGE_MARGIN
    left_col_w = 150
    c.setFillColor(black)
    c.setFont(SECTION_FONT, SECTION_SIZE)
    c.drawString(left_x, col_top, "Zutaten")

    y_left = col_top - 22
    c.setFont(BODY_FONT, BODY_SIZE)
    c.setFillColor(BODY_TEXT)
    for ing in recipe.get("ingredients", []):
        lines = wrap_text(ing, BODY_FONT, BODY_SIZE, left_col_w, c)
        for ln in lines:
            if y_left < bottom_margin:
                break
            c.drawString(left_x, y_left, ln)
            y_left -= 14
        y_left -= 4  # Zusatz-Abstand zwischen Zutaten

    # Vertikale Trennlinie
    sep_x = left_x + left_col_w + 22
    c.setStrokeColor(SEPARATOR)
    c.setLineWidth(0.6)
    sep_bottom = max(bottom_margin, min(y_left, 70))
    c.line(sep_x, col_top + 6, sep_x, sep_bottom)

    # Rechte Spalte: Zubereitung
    right_x = sep_x + 18
    right_w = page_w - right_x - PAGE_MARGIN
    c.setFillColor(black)
    c.setFont(SECTION_FONT, SECTION_SIZE)
    c.drawString(right_x, col_top, "Zubereitung")

    y_right = col_top - 22
    c.setFont(BODY_FONT, BODY_SIZE)
    c.setFillColor(BODY_TEXT)
    for step in recipe.get("directions", []):
        lines = wrap_text(step, BODY_FONT, BODY_SIZE, right_w, c)
        for ln in lines:
            if y_right < bottom_margin:
                # Rest überspringen; kein Seitenumbruch (Template ist 1-seitig)
                break
            c.drawString(right_x, y_right, ln)
            y_right -= 13.5
        y_right -= 8  # Absatzabstand zwischen Schritten

    # --- Nährwerte-Footer ---
    if has_nutrition:
        _draw_nutrition_footer(c, recipe, page_w, recipe.get("servings"))

    # --- Seitenzahl ---
    c.setFont(BODY_FONT, 9)
    c.setFillColor(MUTED_TEXT)
    c.drawRightString(page_w - PAGE_MARGIN, 28, "1")

    c.showPage()
    c.save()


def _draw_nutrition_footer(c: canvas.Canvas, recipe: dict, page_w: float, servings) -> None:
    """Dezenter Footer-Block mit Nährwerten oberhalb der Seitenzahl.

    Layout: dünne horizontale Trennlinie, darunter Label + Werte-Zeile.
    Wenn die Werte aus der Originalquelle stammen (source='quelle'), entfällt
    der 'Schätzung'-Zusatz.
    """
    nut = recipe["nutrition_per_serving"]
    footer_top = 80  # y-Koordinate der Trennlinie

    # Trennlinie
    c.setStrokeColor(SEPARATOR)
    c.setLineWidth(0.5)
    c.line(PAGE_MARGIN, footer_top, page_w - PAGE_MARGIN, footer_top)

    # Label-Zeile
    source = (nut.get("source") or "schaetzung").lower()
    is_estimate = source != "quelle"
    serv_part = ""
    if servings:
        # Hübsche Darstellung: "4 Portionen" oder "1 Portion"
        try:
            n = int(servings)
            serv_part = f" ({n} Portion{'en' if n != 1 else ''})"
        except (TypeError, ValueError):
            serv_part = f" ({servings})"

    label = f"Nährwerte pro Portion{serv_part}"
    if is_estimate:
        label += " — Schätzung"

    c.setFont(BODY_FONT, 9)
    c.setFillColor(MUTED_TEXT)
    c.drawString(PAGE_MARGIN, footer_top - 13, label)

    # Werte-Zeile: kcal | Eiweiß | Fett | KH | (Ballaststoffe)
    parts = []
    if nut.get("kcal") is not None:
        parts.append(f"{int(round(nut['kcal']))} kcal")
    if nut.get("protein_g") is not None:
        parts.append(f"{int(round(nut['protein_g']))} g Eiweiß")
    if nut.get("fat_g") is not None:
        parts.append(f"{int(round(nut['fat_g']))} g Fett")
    if nut.get("carbs_g") is not None:
        parts.append(f"{int(round(nut['carbs_g']))} g Kohlenhydrate")
    if nut.get("fiber_g") is not None:
        parts.append(f"{int(round(nut['fiber_g']))} g Ballaststoffe")

    values_line = "   •   ".join(parts)
    c.setFont(BODY_FONT, 10)
    c.setFillColor(BODY_TEXT)
    c.drawString(PAGE_MARGIN, footer_top - 30, values_line)


def _draw_image_placeholder(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(HexColor("#EEEEEE"))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(MUTED_TEXT)
    c.setFont(BODY_FONT, 10)
    c.drawCentredString(x + w / 2, y + h / 2, "(kein Bild)")


# ---------- CLI ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt Rezept-PDF im festen Magazin-Layout.")
    parser.add_argument("--json", required=True, help="Pfad zur Rezept-JSON-Datei")
    parser.add_argument("--image", default=None, help="Pfad oder URL zum Hero-Bild (optional)")
    parser.add_argument("--output", default=None,
                        help="Ausgabe-PDF-Pfad (default: /Rezepte/<slug>.pdf)")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    if not recipe.get("title"):
        print("Fehler: 'title' fehlt in der Rezept-JSON.", file=sys.stderr)
        return 1

    # Bild vorbereiten
    image_path = None
    if args.image:
        scratch = Path("/sessions/pensive-amazing-hypatia/.img-candidates")
        try:
            image_path = fetch_image(args.image, scratch)
        except Exception as e:
            print(f"Warnung: Bild nicht abrufbar ({e}). Fahre ohne Bild fort.", file=sys.stderr)

    # Output-Pfad bestimmen
    if args.output:
        output = Path(args.output)
    else:
        output = Path(f"/sessions/pensive-amazing-hypatia/mnt/Rezepte/{slugify(recipe['title'])}.pdf")

    generate_recipe_pdf(recipe, image_path, output)
    print(f"Geschrieben: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
