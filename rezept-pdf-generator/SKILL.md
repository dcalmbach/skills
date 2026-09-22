---
name: "rezept-pdf-generator"
description: "Erstellt aus strukturierten Rezeptdaten ein professionelles, druckfertiges PDF im Magazin-Layout mit Bild und Naehrwerten. Seite 1 zweispaltig (Zutaten/Zubereitung), Text wird nie gekuerzt, laeuft bei Bedarf auf weitere Seiten."
---

# rezept-pdf-generator — Rezeptdaten zu PDF

Nimmt strukturierte Rezeptdaten (z.B. vom Skill `rezept-erfassen`) entgegen und erzeugt ein PDF im festen Magazin-Layout.

## Layout-Regeln (verbindlich)

- **Seite 1**: blauer Kopfbalken, Serif-Titel, Vorbereitung/Kochzeit, Hero-Bild über die volle Breite, darunter **zweispaltig**: links "Zutaten", rechts "Zubereitung".
- **Kein Text wird abgeschnitten oder gekürzt.** Wenn die Zubereitung nicht komplett auf Seite 1 passt, läuft der Rest auf einer oder mehreren weiteren Seiten weiter (Überschrift "Zubereitung (Fortsetzung)", volle Breite, gleicher blauer Kopfbalken, fortlaufende Seitenzahlen).
- Nährwerte als dezenter Footer-Block, klar als "Schätzung" markiert falls nicht aus der Quelle übernommen — erscheinen auf der letzten Seite.
- Kein Logo oben links.

## Eingabeformat

```json
{
  "title": "Spaghetti Carbonara",
  "prep_time": "15 Minuten",
  "cook_time": "20 Minuten",
  "servings": 4,
  "ingredients": ["400 g Spaghetti", "..."],
  "directions": ["Schritt 1...", "..."],
  "nutrition_per_serving": {"kcal": 620, "protein_g": 28, "fat_g": 24, "carbs_g": 72, "fiber_g": 3, "source": "schaetzung"},
  "image_url": "https://..."
}
```

Wenn `nutrition_per_serving` fehlt, grob aus den Zutaten schätzen (Größenordnung reicht: Nudeln/Reis ~350 kcal/100g, mageres Fleisch ~160 kcal/100g, Butter/Öl ~880/720 kcal/100g, Nüsse ~650 kcal/100g, Schokolade ~550 kcal/100g) und durch die Portionenzahl teilen. Immer mit `"source": "schaetzung"` markieren, außer die Quelle liefert echte Werte (dann `"source": "quelle"`).

## Workflow

1. Bild vorbereiten: Wenn `image_url` gesetzt ist oder der Nutzer eine URL/Datei nennt, dieses Bild verwenden. Bei mehreren Kandidaten den Nutzer per `AskUserQuestion` wählen lassen.
2. Rezept-JSON in eine Datei schreiben (`recipe.json`).
3. `scripts/generate_recipe_pdf.py` mit `--json`, `--image` (Pfad oder URL) und `--output` aufrufen. Abhängigkeiten bei Bedarf installieren: `pip install --break-system-packages reportlab Pillow`.
4. PDF an den Nutzer liefern (Download bereitstellen). Speicherort standardmäßig im Workspace-Ordner "Rezepte".

## scripts/generate_recipe_pdf.py

Dieses exakte Skript vor der ersten Nutzung (und bei jedem Verdacht auf eine veraltete/gekürzte Version) nach `scripts/generate_recipe_pdf.py` schreiben, damit garantiert die Mehrseiten-Logik ohne Textkürzung verwendet wird:

```python
#!/usr/bin/env python3
"""generate_recipe_pdf.py — Erzeugt ein Rezept-PDF im festen Magazin-Layout.
Seite 1: Titel, Bild, zweispaltig Zutaten/Zubereitung. Passt die Zubereitung
nicht komplett auf Seite 1, laeuft der Rest auf weiteren Seiten weiter —
es wird NIE Text abgeschnitten.
"""
from __future__ import annotations
import argparse, io, json, re, sys, urllib.request
from pathlib import Path
from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image

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


def slugify(text: str) -> str:
    text = text.lower()
    for a, b in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "rezept"


def fetch_image(image_path_or_url: str, scratch_dir: Path) -> Path:
    if image_path_or_url.startswith(("http://", "https://")):
        scratch_dir.mkdir(parents=True, exist_ok=True)
        dst = scratch_dir / "hero_download.jpg"
        req = urllib.request.Request(image_path_or_url, headers={"User-Agent": "Mozilla/5.0 (recipe-pdf)"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as f:
            f.write(r.read())
        return dst
    return Path(image_path_or_url)


def wrap_text(text, font_name, font_size, max_width, c):
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
                lines.append(word); current = []
            else:
                current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_image_cover(c, img_path, x, y, w, h):
    img = Image.open(img_path)
    iw, ih = img.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        new_w = int(ih * box_ratio); left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / box_ratio); top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, width=w, height=h, mask="auto")


def generate_recipe_pdf(recipe, image_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_w, page_h = A4

    c.setFillColor(BAR_BLUE)
    c.rect(0, page_h - TOP_BAR_H, page_w, TOP_BAR_H, fill=1, stroke=0)

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

    img_y_top = title_y - 35
    img_h = 290
    img_y = img_y_top - img_h
    img_w = page_w
    if image_path and image_path.exists():
        try:
            draw_image_cover(c, image_path, 0, img_y, img_w, img_h)
        except Exception as e:
            print(f"Warnung: Bild konnte nicht geladen werden ({e}).", file=sys.stderr)
            _draw_image_placeholder(c, 0, img_y, img_w, img_h)
    else:
        _draw_image_placeholder(c, 0, img_y, img_w, img_h)

    col_top = img_y - 30
    has_nutrition = bool(recipe.get("nutrition_per_serving"))
    bottom_margin = 95 if has_nutrition else 55

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
        y_left -= 4

    sep_x = left_x + left_col_w + 22
    c.setStrokeColor(SEPARATOR)
    c.setLineWidth(0.6)
    sep_bottom = max(bottom_margin, min(y_left, 70))
    c.line(sep_x, col_top + 6, sep_x, sep_bottom)

    right_x = sep_x + 18
    right_w = page_w - right_x - PAGE_MARGIN
    c.setFillColor(black)
    c.setFont(SECTION_FONT, SECTION_SIZE)
    c.drawString(right_x, col_top, "Zubereitung")

    y_right = col_top - 22
    c.setFont(BODY_FONT, BODY_SIZE)
    c.setFillColor(BODY_TEXT)

    all_directions_lines = []
    for step in recipe.get("directions", []):
        lines = wrap_text(step, BODY_FONT, BODY_SIZE, right_w, c)
        all_directions_lines.extend(lines)
        all_directions_lines.append(None)

    directions_start_idx = 0
    for idx, ln in enumerate(all_directions_lines):
        if ln is None:
            y_right -= 8
        else:
            if y_right < bottom_margin:
                directions_start_idx = idx
                break
            c.drawString(right_x, y_right, ln)
            y_right -= 13.5

    if has_nutrition and directions_start_idx == 0:
        _draw_nutrition_footer(c, recipe, page_w, recipe.get("servings"))

    c.setFont(BODY_FONT, 9)
    c.setFillColor(MUTED_TEXT)
    c.drawRightString(page_w - PAGE_MARGIN, 28, "1")
    c.showPage()

    if directions_start_idx > 0:
        page_num = 2
        col_top = page_h - 50

        c.setFillColor(BAR_BLUE)
        c.rect(0, page_h - TOP_BAR_H, page_w, TOP_BAR_H, fill=1, stroke=0)
        c.setFillColor(black)
        c.setFont(SECTION_FONT, SECTION_SIZE)
        c.drawString(PAGE_MARGIN, col_top, "Zubereitung (Fortsetzung)")

        y = col_top - 22
        c.setFont(BODY_FONT, BODY_SIZE)
        c.setFillColor(BODY_TEXT)
        bottom_margin = 95 if has_nutrition else 55

        for ln in all_directions_lines[directions_start_idx:]:
            if ln is None:
                y -= 8
            else:
                if y < bottom_margin:
                    c.setFont(BODY_FONT, 9)
                    c.setFillColor(MUTED_TEXT)
                    c.drawRightString(page_w - PAGE_MARGIN, 28, str(page_num))
                    c.showPage()
                    page_num += 1
                    c.setFillColor(BAR_BLUE)
                    c.rect(0, page_h - TOP_BAR_H, page_w, TOP_BAR_H, fill=1, stroke=0)
                    c.setFillColor(black)
                    c.setFont(SECTION_FONT, SECTION_SIZE)
                    c.drawString(PAGE_MARGIN, col_top, "Zubereitung (Fortsetzung)")
                    y = col_top - 22
                    c.setFont(BODY_FONT, BODY_SIZE)
                    c.setFillColor(BODY_TEXT)
                c.drawString(PAGE_MARGIN, y, ln)
                y -= 13.5

        if has_nutrition:
            _draw_nutrition_footer(c, recipe, page_w, recipe.get("servings"))

        c.setFont(BODY_FONT, 9)
        c.setFillColor(MUTED_TEXT)
        c.drawRightString(page_w - PAGE_MARGIN, 28, str(page_num))
        c.showPage()

    c.save()


def _draw_nutrition_footer(c, recipe, page_w, servings):
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
    values_line = "   •   ".join(parts)
    c.setFont(BODY_FONT, 10)
    c.setFillColor(BODY_TEXT)
    c.drawString(PAGE_MARGIN, footer_top - 30, values_line)


def _draw_image_placeholder(c, x, y, w, h):
    c.setFillColor(HexColor("#EEEEEE"))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(MUTED_TEXT)
    c.setFont(BODY_FONT, 10)
    c.drawCentredString(x + w / 2, y + h / 2, "(kein Bild)")


def main():
    parser = argparse.ArgumentParser(description="Erzeugt Rezept-PDF im festen Magazin-Layout.")
    parser.add_argument("--json", required=True)
    parser.add_argument("--image", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    with open(args.json, "r", encoding="utf-8") as f:
        recipe = json.load(f)
    if not recipe.get("title"):
        print("Fehler: 'title' fehlt in der Rezept-JSON.", file=sys.stderr)
        return 1
    image_path = None
    if args.image:
        scratch = Path("/tmp/rezept-pdf-img-candidates")
        try:
            image_path = fetch_image(args.image, scratch)
        except Exception as e:
            print(f"Warnung: Bild nicht abrufbar ({e}).", file=sys.stderr)
    output = Path(args.output) if args.output else Path(f"/Rezepte/{slugify(recipe['title'])}.pdf")
    generate_recipe_pdf(recipe, image_path, output)
    print(f"Geschrieben: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Was nicht tun

- Keine Änderung des Layouts ohne ausdrückliche Nutzeranweisung.
- Nie Zubereitungs- oder Zutatentext abschneiden, um auf eine Seite zu passen — stattdessen weitere Seite anhängen.
- Kein Logo einfügen.