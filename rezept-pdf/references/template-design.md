# Rezept-Template — Layout-Spezifikation

Diese Datei ist die „Wahrheit" für das Erscheinungsbild. Der Generator
`scripts/generate_recipe_pdf.py` implementiert diese Specs — Änderungen
bitte hier UND im Skript synchron halten.

## Seite

- Format: A4 (595 × 842 pt)
- Seitenrand links/rechts: 40 pt
- Oben/unten ohne extra Margin (Bild geht auf Vollbreite)

## Farben

| Rolle | Hex | Verwendung |
|-------|-----|------------|
| BAR_BLUE | `#1F3B5F` | Dünner Kopfbalken oben |
| BODY_TEXT | `#3A3A3A` | Standard-Fließtext |
| MUTED_TEXT | `#6A6A6A` | Untertitel, Seitenzahl |
| SEPARATOR | `#CFCFCF` | Vertikale Trennlinie zwischen Spalten |

Keine bunten Akzente — das Template lebt vom Foto. Daran nichts ändern.

## Typografie

- **Titel**: Times-Bold, 26 pt, schwarz. Z. B. „Spaghetti Carbonara"
- **Untertitel (Zeiten)**: Helvetica, 11 pt, BODY_TEXT. Format: „Vorbereitung 15 Minuten | Kochzeit 20 Minuten"
- **Sektionsüberschriften** („Zutaten", „Zubereitung"): Times-Bold, 14 pt, schwarz
- **Fließtext**: Helvetica, 10 pt, BODY_TEXT
- **Seitenzahl**: Helvetica, 9 pt, MUTED_TEXT, rechtsbündig unten

Times und Helvetica sind ReportLab-Builtins und funktionieren ohne Font-Installation. Wenn einmal eine „schönere" Schrift gewünscht ist (z. B. Playfair Display für Titel), müssten TTF-Dateien mit `pdfmetrics.registerFont` registriert werden — aktuell bewusst nicht gemacht, damit der Generator portabel bleibt.

## Vertikaler Aufbau (von oben)

1. **Blauer Kopfbalken** — 6 pt hoch, Vollbreite, BAR_BLUE.
2. **Titelbereich** — ~35 pt unterhalb Oberkante. Titel linksbündig. 18 pt tiefer der Untertitel.
3. **Hero-Bild** — startet ca. 35 pt unter dem Untertitel. Höhe 290 pt, Breite = Vollbreite der Seite. Bild wird im „cover"-Modus eingepasst: Box immer füllen, Überhang beschneiden.
4. **Content-Bereich** — beginnt 30 pt unterhalb des Bildes.
5. **Nährwerte-Footer** (optional) — horizontale Leiste bei y = 80 pt. Wenn vorhanden, wird der Content-Bereich bei 95 pt unterer Margin abgeschnitten (statt 55 pt), damit die Leiste nicht mit den Spalten kollidiert.
6. **Seitenzahl** — unten rechts, 28 pt über Unterkante.

## Nährwerte-Footer

- Horizontale 0,5-pt-Linie in SEPARATOR-Farbe bei y = 80 pt, volle Breite zwischen den Seitenrändern.
- 13 pt darunter: Label in Helvetica 9 pt, MUTED_TEXT, z.B. „Nährwerte pro Portion (4 Portionen) — Schätzung".
- Weitere 17 pt darunter: Werte-Zeile in Helvetica 10 pt, BODY_TEXT, mit „   •   " als Trenner. Format: `620 kcal   •   28 g Eiweiß   •   24 g Fett   •   72 g Kohlenhydrate   •   3 g Ballaststoffe`.
- Ballaststoffe sind optional; fehlt der Wert, einfach weglassen.
- Der Zusatz „Schätzung" entfällt, wenn im JSON `nutrition_per_serving.source == "quelle"` steht (Werte direkt aus der Originalquelle).

## Zweispalten-Content

- Linke Spalte („Zutaten"): Breite 150 pt, startet bei x=40.
- Vertikale Trennlinie bei x=212 (40+150+22), Farbe SEPARATOR, 0,6 pt breit.
- Rechte Spalte („Zubereitung"): startet bei x=230, Breite = Seitenbreite - 230 - 40 = 325 pt.

### Zutaten-Liste

- Kein Bullet-Symbol — einfach Zeilen untereinander.
- Zeilenhöhe 14 pt.
- Zwischen Einträgen zusätzlich 4 pt Abstand.
- Bei mehrzeiligen Zutaten (selten, aber z. B. „2 EL Olivenöl, extra nativ") umbrechen innerhalb der 150 pt Spalte.

### Zubereitung

- Jeder Schritt ist ein Absatz.
- Zeilenhöhe 13,5 pt.
- Zwischen Absätzen 8 pt extra Abstand.

## Seitenumbruch

Das Template ist **einseitig**. Wenn Inhalte nicht passen:

- Zutaten abschneiden ist unschön → lieber Zutaten knapper formulieren.
- Zubereitungstext zu lang → Schritte zusammenfassen oder kürzen, damit sie auf eine Seite passen. Alternative (später): zweite Seite nur für Zubereitung, aber das bricht die Magazin-Ästhetik.

## Was nicht geändert werden darf

Ohne ausdrücklichen Nutzerwunsch:

- Farbpalette
- Font-Wahl
- Spaltenbreiten
- Bildhöhe
- Seitenformat
