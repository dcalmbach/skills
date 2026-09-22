---
name: "rezept-erfassen"
description: "Extrahiert und strukturiert Rezeptinhalte aus Webseiten, Text, Notion-Seiten, handschriftlichen Rezepten oder Rezeptfotos in standardisiertes Format."
---

# Rezept erfassen & strukturieren

Dieser Skill verarbeitet Rezepte aus verschiedenen Quellen und extrahiert sie in ein standardisiertes Datenformat — auch von Hand geschriebene Rezepte. Er liefert die Daten, mit denen der Skill `rezept-pdf-generator` anschließend ein PDF baut.

## Eingabenquellen
- **Webseiten**: Links zu Kochblogs oder Rezept-Plattformen (chefkoch.de, essen-und-trinken.de, bbcgoodfood, etc.) — per `WebFetch`.
- **Text**: Rezepte als eingefügter oder hochgeladener Text — direkt aus dem Chat.
- **Notion**: Rezept-Seiten aus Notion — per `notion-fetch`.
- **Handschriftliche Rezepte**: Fotos von handschriftlichen Rezeptkarten, Notizbüchern oder Zeitschriften — Bild lesen und Text so genau wie möglich abtippen.
- **Rezeptfotos**: Fotos von fertigen Rezepten aus Kochbüchern oder Zeitschriften.

## Wichtig bei handschriftlichen/fotografierten Rezepten

Bei Fotos (besonders handschriftlich oder gedreht/unscharf fotografiert) NIEMALS Text durch ein ähnliches Web-Rezept ersetzen oder ergänzen, auch wenn ein passendes Rezept online gefunden wird. Der transkribierte Text muss 1:1 vom Foto stammen. Wenn Teile unleserlich sind:
- Das Gelesene so präzise wie möglich wiedergeben.
- Unsichere Stellen explizit als unsicher markieren und den Nutzer um Bestätigung oder ein schärferes Foto bitten — nicht raten und als Fakt ausgeben.
- Erst nach Bestätigung durch den Nutzer als final behandeln.

## Extrahierte Daten
Strukturiert folgende Rezept-Angaben:
- Titel
- Beschreibung/Einleitung
- Zubereitungszeit
- Gesamtzeit / Backzeit
- Anzahl Portionen
- Zutaten (mit Mengen und Einheiten, inkl. Zuordnung zu Teig/Füllung/Guss etc. falls die Quelle das vorgibt)
- Zubereitungsschritte (vollständig, nicht gekürzt)
- Tipps/Anmerkungen
- Bilder/Hero-Fotos (wenn vorhanden)
- Quelle/URL

## Ausgabeformat

```json
{
  "title": "Spaghetti Carbonara",
  "prep_time": "15 Minuten",
  "cook_time": "20 Minuten",
  "servings": 4,
  "ingredients": ["400 g Spaghetti", "150 g Pancetta", "..."],
  "directions": ["Reichlich Salzwasser zum Kochen bringen...", "..."],
  "nutrition_per_serving": {"kcal": 620, "protein_g": 28, "fat_g": 24, "carbs_g": 72, "fiber_g": 3},
  "image_url": "https://..."
}
```

Rückgabe der strukturierten Rezeptdaten, bereit zur Verarbeitung durch den `rezept-pdf-generator` Skill.

## Verwendung
Automatisch triggern bei:
- "Rezept von diesem Link erfassen"
- "Diese Rezeptseite aufnehmen"
- "Rezept aus Notion importieren"
- "Dieses Rezeptfoto verarbeiten"
- "Rezept aus Text extrahieren"
- "Handgeschriebenes Rezept erfassen"
- "Foto von meiner Rezeptkarte einscannen"
- "Rezept aus meinem Kochbuch abtippen"