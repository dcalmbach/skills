# Rezepte aus verschiedenen Quellen extrahieren

Beim Extrahieren zählt: Titel, Zeiten, Zutatenliste (Array), Zubereitungsschritte (Array von Absätzen). Alles andere (Tipps, Nährwerte, Kommentare) **ignorieren** — das Template hat dafür keinen Platz.

## Webseiten (allgemein)

Nutze `web_extract` auf die Rezept-URL und extrahiere aus dem zurückgegebenen Markdown. Zielstruktur:

> „Extrahiere aus dieser Seite den Rezepttitel, die Vorbereitungszeit, die Kochzeit, die Zutatenliste (als JSON-Array von Strings, eine Zutat pro Eintrag inklusive Menge und Einheit) und die Zubereitungsschritte (als JSON-Array von Absätzen). Gib nur das JSON zurück, keine Einleitung."

Viele Rezeptseiten haben strukturierte Daten (`application/ld+json` mit `@type: Recipe`), was die Extraktion deutlich zuverlässiger macht. Bei Deutschsprachigkeit auf korrekt geparste Mengenangaben achten (500 g vs. 500g).

## Spezifische Seiten

### chefkoch.de

- Titel: in `<h1>`
- Zutaten: Tabelle mit Spalten „Menge" und „Zutat" — beim Extrahieren zu `"500 g Spaghetti"` zusammenbauen.
- Zubereitung: ein einzelner großer Textblock — sinnvoll in logische Absätze splitten (meist schon durch Leerzeilen getrennt).
- Zeiten: Block mit Icon + Minutenangabe. Format in der Quelle oft „45 Min." — ins Template als „45 Minuten" umformulieren.

### essen-und-trinken.de / chefkoch.de / kochbar.de / lecker.de

Ähnlich wie oben — strukturierte Daten sind meist vorhanden.

### bbcgoodfood.com, seriouseats.com, nytimes cooking

Englischsprachig. Ins Deutsche übersetzen beim Extrahieren. Typische Übersetzungen:
- „tbsp" → „EL" (Esslöffel)
- „tsp" → „TL" (Teelöffel)
- „cup" → bei Volumen in ml/g umrechnen wo möglich (1 cup ≈ 240 ml Flüssigkeit, bei Mehl ≈ 125 g)
- „pinch" → „Prise"

## Notion

Der `notion`-Skill (ntn CLI / Notion-API) holt die Seitenblöcke. Für ein Notion-Rezept:

1. Wenn der Nutzer eine URL/Seiten-ID angibt, direkt fetchen.
2. Ansonsten `notion-search` mit dem Rezeptnamen.
3. Die Blöcke durchgehen: Titel aus Page-Property, Zutaten oft als Bulleted-List-Block, Zubereitung als Paragraph-Blöcke oder Numbered-List.
4. Embedded Images aus Image-Blöcken können als erstes Bild-Kandidat genutzt werden (`file.url` oder `external.url`).

## Roher Text (Chat/Paste)

Oft unstrukturiert. Musterschritte:

1. Ersten Zeilen-/Absatzblock als Titel erkennen.
2. „Zutaten:" / „Ingredients:" als Sektionstrennung suchen.
3. Zutaten sind üblicherweise eine Liste; wenn nicht, zeilenweise aufteilen.
4. „Zubereitung:" / „Anleitung:" / „Directions:" → Zubereitung.

## Foto eines Rezepts (z. B. aus Kochbuch)

1. Bild lesen (Multimodal-Capability).
2. OCR-artig Titel, Zutaten, Schritte herausholen.
3. Bei handschriftlichen/unklaren Stellen ausdrücklich vom Nutzer bestätigen lassen.
4. Das Foto kann als Bildkandidat Nr. 1 dienen, wenn kein besseres Online-Bild gefunden wird.

## Ausgabe-Format (nach Extraktion)

Immer dieses JSON-Schema für das Generator-Skript erzeugen:

```json
{
  "title": "Rezepttitel",
  "prep_time": "15 Minuten",
  "cook_time": "45 Minuten",
  "ingredients": ["400 g Spaghetti", "150 g Pancetta"],
  "directions": ["Erster Schritt...", "Zweiter Schritt..."]
}
```

`prep_time` und `cook_time` sind optional und können fehlen. Leere Strings bitte weglassen, nicht als `""` übergeben.
