#!/usr/bin/env python3
"""generate_recipe_pdf.py — Erzeugt ein Rezept-PDF im festen Magazin-Layout.

Seite 1: blauer Kopfbalken, Serif-Titel, Zeiten, Hero-Bild ueber volle Breite,
darunter zweispaltig links "Zutaten" / rechts "Zubereitung".

Passt eine der beiden Spalten nicht komplett auf Seite 1, laeuft der Rest auf
weiteren Seiten weiter ("Zutaten (Fortsetzung)" / "Zubereitung (Fortsetzung)",
volle Breite, gleicher Kopfbalken, fortlaufende Seitenzahlen).
Es wird NIE Text abgeschnitten — weder Zutaten noch Zubereitung.

Beispielaufruf:
    python generate_recipe_pdf.py --json recipe.json --image hero.jpg \
        --output ./Rezepte/spaghetti-carbonara.pdf
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image

# ---------- Designkonstanten ----------

BAR_BLUE = HexColor("#1F3B5F")
BODY_TEXT = HexColor("#3A3A3A")
MUTED_TEXT = HexColor("#6A6A6A")
SEPARATOR = HexColor("#CFCFCF")

PAGE_MARGIN = 40
TOP_BAR_H = 6
TITLE_FONT = "Times-Bold"
SECTION_FONT = "Times-Bold"
BODY_FONT = "Helvetica"
TITLE_SIZE = 26
SECTION_SIZE = 14
BODY_SIZE = 10
SUBTITLE_SIZE = 11

LINE_H = 13.5          # Zeilenhoehe Fliesstext
ITEM_GAP = 4           # Abstand zwischen Zutaten
STEP_GAP = 8           # Abstand zwischen Zubereitungsschritten


# ---------- Hilfsfunktionen ----------

def slugify(text: str) -> str:
    """Dateinamentauglicher Slug aus dem Titel."""
    text = text.lower()
    for a, b in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "rezept"


def fetch_image(image_path_or_url: str, scratch_dir: Path) -> Path:
    """URL lokal herunterladen; lokale Pfade unveraendert zurueckgeben."""
    if image_path_or_url.startswith(("http://", "https://")):
        scratch_dir.mkdir(parents=True, exist_ok=True)
        dst = scratch_dir / "hero_download.jpg"
        req = urllib.request.Request(
            image_path_or_url, headers={"User-Agent": "Mozilla/5.0 (recipe-pdf)"}
        )
        with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as f:
            f.write(r.read())
        return dst
    return Path(image_path_or_url)


def wrap_text(text, font_name, font_size, max_width, c):
    """Bricht Text auf max_width um. Zu lange Einzelwoerter bleiben erhalten."""
    words = text.split()
    lines, current = [], []
    for word in words:
        trial = " ".join(current + [word])
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            if c.stringWidth(word, font_name, font_size) > max_width:
                lines.append(word)
                current = []
            else:
                current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _flow(items, font, size, width, c, gap):
    """Liste von Textbloecken -> Flow aus ('text', str) und ('gap', pt)."""
    flow = []
    for item in items:
        for ln in wrap_text(str(item), font, size, width, c):
            flow.append(("text", ln))
        flow.append(("gap", gap))
    return flow


def _draw_flow(c, flow, x, y, width, bottom):
    """Zeichnet so viel vom Flow wie passt. Gibt (rest_flow, y) zurueck."""
    c.setFont(BODY_FONT, BODY_SIZE)
    c.setFillColor(BODY_TEXT)
    for idx, (kind, val) in enumerate(flow):
        if kind == "gap":
            y -= val
            continue
        if y < bottom:
            return flow[idx:], y
        c.drawString(x, y, val)
        y -= LINE_H
    return [], y


def draw_image_cover(c, img_path, x, y, w, h):
    """Bild 'object-fit: cover' — Box fuellen, Ueberhang beschneiden."""
    img = Image.open(img_path)
    iw, ih = img.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        new_w = int(ih * box_ratio)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / box_ratio)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, width=w, height=h, mask="auto")


def _top_bar(c, page_w, page_h):
    c.setFillColor(BAR_BLUE)
    c.rect(0, page_h - TOP_BAR_H, page_w, TOP_BAR_H, fill=1, stroke=0)


def _page_number(c, page_w, n):
    c.setFont(BODY_FONT, 9)
    c.setFillColor(MUTED_TEXT)
    c.drawRightString(page_w - PAGE_MARGIN, 28, str(n))


def _section_heading(c, x, y, text):
    c.setFillColor(black)
    c.setFont(SECTION_FONT, SECTION_SIZE)
    c.drawString(x, y, text)


# ---------- PDF-Erzeugung ----------

def generate_recipe_pdf(recipe, image_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_w, page_h = A4

    has_nutrition = bool(recipe.get("nutrition_per_serving"))
    bottom = 95 if has_nutrition else 55

    # --- Seite 1: Kopf ---
    _top_bar(c, page_w, page_h)

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
    if image_path and image_path.exists():
        try:
            draw_image_cover(c, image_path, 0, img_y, page_w, img_h)
        except Exception as e:  # noqa: BLE001 — Bildfehler darf das PDF nicht kippen
            print(f"Warnung: Bild konnte nicht geladen werden ({e}).", file=sys.stderr)
            _draw_image_placeholder(c, 0, img_y, page_w, img_h)
    else:
        _draw_image_placeholder(c, 0, img_y, page_w, img_h)

    # --- Zwei Spalten ---
    col_top = img_y - 30
    left_x = PAGE_MARGIN
    left_col_w = 150
    sep_x = left_x + left_col_w + 22
    right_x = sep_x + 18
    right_w = page_w - right_x - PAGE_MARGIN
    full_w = page_w - 2 * PAGE_MARGIN

    ing_flow = _flow(recipe.get("ingredients", []), BODY_FONT, BODY_SIZE, left_col_w, c, ITEM_GAP)
    dir_flow = _flow(recipe.get("directions", []), BODY_FONT, BODY_SIZE, right_w, c, STEP_GAP)

    _section_heading(c, left_x, col_top, "Zutaten")
    ing_rest, y_left = _draw_flow(c, ing_flow, left_x, col_top - 22, left_col_w, bottom)

    c.setStrokeColor(SEPARATOR)
    c.setLineWidth(0.6)
    c.line(sep_x, col_top + 6, sep_x, max(bottom, min(y_left, 70)))

    _section_heading(c, right_x, col_top, "Zubereitung")
    dir_rest, _ = _draw_flow(c, dir_flow, right_x, col_top - 22, right_w, bottom)

    page_num = 1
    # Nur wenn nichts uebrig ist, gehoert der Naehrwert-Footer auf diese Seite.
    if has_nutrition and not ing_rest and not dir_rest:
        _draw_nutrition_footer(c, recipe, page_w, recipe.get("servings"))
    _page_number(c, page_w, page_num)
    c.showPage()

    # --- Fortsetzungsseiten (volle Breite) ---
    # Zutaten zuerst, danach die Zubereitung. Beide werden neu umbrochen,
    # weil die Fortsetzung die volle Seitenbreite nutzt.
    pending = []
    if ing_rest:
        rest_items = [v for k, v in ing_rest if k == "text"]
        pending.append(("Zutaten (Fortsetzung)",
                        _flow(rest_items, BODY_FONT, BODY_SIZE, full_w, c, 0)))
    if dir_rest:
        rest_items = [v for k, v in dir_rest if k == "text"]
        pending.append(("Zubereitung (Fortsetzung)",
                        _flow(rest_items, BODY_FONT, BODY_SIZE, full_w, c, 0)))

    for heading, flow in pending:
        first = True
        while flow or first:
            page_num += 1
            _top_bar(c, page_w, page_h)
            top = page_h - 50
            _section_heading(c, PAGE_MARGIN, top, heading)
            flow, _ = _draw_flow(c, flow, PAGE_MARGIN, top - 22, full_w, bottom)
            first = False
            is_last_page = (not flow) and (heading == pending[-1][0])
            if has_nutrition and is_last_page:
                _draw_nutrition_footer(c, recipe, page_w, recipe.get("servings"))
            _page_number(c, page_w, page_num)
            c.showPage()

    c.save()


def _draw_nutrition_footer(c, recipe, page_w, servings):
    """Dezenter Footer-Block mit Naehrwerten oberhalb der Seitenzahl."""
    nut = recipe["nutrition_per_serving"]
    footer_top = 80
    c.setStrokeColor(SEPARATOR)
    c.setLineWidth(0.5)
    c.line(PAGE_MARGIN, footer_top, page_w - PAGE_MARGIN, footer_top)

    source = (nut.get("source") or "schaetzung").lower()
    is_estimate = source != "quelle"
    serv_part = ""
    if servings:
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
    c.setFont(BODY_FONT, 10)
    c.setFillColor(BODY_TEXT)
    c.drawString(PAGE_MARGIN, footer_top - 30, "   •   ".join(parts))


def _draw_image_placeholder(c, x, y, w, h):
    c.setFillColor(HexColor("#EEEEEE"))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(MUTED_TEXT)
    c.setFont(BODY_FONT, 10)
    c.drawCentredString(x + w / 2, y + h / 2, "(kein Bild)")


# ---------- CLI ----------

def default_output(title: str) -> Path:
    """Ziel: $REZEPTE_DIR, sonst ./Rezepte relativ zum Arbeitsverzeichnis."""
    base = os.environ.get("REZEPTE_DIR") or "Rezepte"
    return Path(base).expanduser() / f"{slugify(title)}.pdf"


def main():
    parser = argparse.ArgumentParser(description="Erzeugt Rezept-PDF im festen Magazin-Layout.")
    parser.add_argument("--json", required=True, help="Pfad zur Rezept-JSON-Datei")
    parser.add_argument("--image", default=None, help="Pfad oder URL zum Hero-Bild (optional)")
    parser.add_argument("--output", default=None,
                        help="Ausgabe-PDF (default: $REZEPTE_DIR/<slug>.pdf bzw. ./Rezepte/<slug>.pdf)")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        recipe = json.load(f)
    if not recipe.get("title"):
        print("Fehler: 'title' fehlt in der Rezept-JSON.", file=sys.stderr)
        return 1

    image_path = None
    if args.image:
        scratch = Path(os.environ.get("TMPDIR", "/tmp")) / "rezept-pdf-img"
        try:
            image_path = fetch_image(args.image, scratch)
        except Exception as e:  # noqa: BLE001
            print(f"Warnung: Bild nicht abrufbar ({e}).", file=sys.stderr)

    output = Path(args.output) if args.output else default_output(recipe["title"])
    generate_recipe_pdf(recipe, image_path, output)
    print(f"Geschrieben: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
