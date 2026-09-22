---
name: "rezept-pdf"
description: "Erstellt aus Rezeptinhalten (Webseiten, eingefügter Text, Notion-Seiten, Fotos von Rezepten, auch handschriftlichen) ein PDF im festen Magazin-Layout (Titel, Zeiten, Hero-Bild, zweispaltige Zutaten/Zubereitung auf Seite 1, bei Bedarf weitere Seiten ohne Textkürzung, geschätzte Nährwerte als Footer). Immer verwenden, wenn der Nutzer ein Rezept als PDF haben will, ein Rezept \"aufbereiten\", \"schön machen\", \"formatieren\" oder \"ins Rezeptformat bringen\" möchte."
---

# rezept-pdf — Rezepte ins Magazin-PDF-Layout bringen

Dieses Skill nimmt Rezeptinhalte aus beliebigen Quellen und erzeugt daraus ein PDF in einem festen, ansprechenden Layout.

## Was das Skill garantiert

- **Einheitliches Layout** (siehe `references/template-design.md`): blauer Kopfbalken, fetter Serif-Titel, Vorbereitung/Kochzeit, Hero-Bild, auf Seite 1 zwei Spalten „Zutaten“ und „Zubereitung“ mit Trennlinie.
- **Kein Text wird abgeschnitten oder gekürzt.** Passt die Zubereitung nicht komplett auf Seite 1, läuft der Rest auf einer oder mehreren weiteren Seiten weiter („Zubereitung (Fortsetzung)“, volle Breite, gleicher Kopfbalken, fortlaufende Seitenzahlen). Das PDF ist also nicht zwingend einseitig.
- **Bei fotografierten/handschriftlichen Rezepten**: der transkribierte Text muss 1:1 vom Foto stammen. Niemals durch ein ähnliches Web-Rezept ersetzen. Unleserliche Stellen explizit als unsicher kennzeichnen und den Nutzer um Bestätigung bitten, statt zu raten.
- **Deutsche Sektionsüberschriften** (Zutaten, Zubereitung, Vorbereitung, Kochzeit) — unabhängig von der Quellsprache. Fremdsprachige Inhalte werden ins Deutsche übersetzt.
- **Kein Logo** oben links.
- **Speicherort**: Workspace-Ordner „Rezepte“. Dateiname aus dem Titel generiert (kleingeschrieben, Bindestriche statt Leerzeichen, ohne Umlaute-Probleme).
- **Bildauswahl durch den Nutzer**: bis zu 3 Kandidaten werden präsentiert, der Nutzer entscheidet.

## Workflow (Pflichtablauf)

### Schritt 1 — Rezeptdaten extrahieren

Je nach Quelltyp:
- **URL (Webseite)**: `web_extract` auf die URL, dann aus dem Markdown extrahieren — „Extrahiere den Rezepttitel, Vorbereitungszeit, Kochzeit, Zutatenliste (als Array), und die Zubereitungsschritte (als Array von Absätzen). Gib das als JSON zurück.“
- **Notion-Seite**: über den `notion`-Skill die Seiten-ID/URL abrufen und die Blöcke auslesen.
- **Roher Text**: Direkt aus dem Chat extrahieren.
- **Foto eines Rezepts** (Kochbuch, Zeitschrift, handschriftliche Karte): Bild lesen und Text möglichst genau abtippen — siehe Hinweis oben zu unleserlichen Stellen.

**Datenschema:**
```json
{
  "title": "Spaghetti Carbonara",
  "prep_time": "15 Minuten",
  "cook_time": "20 Minuten",
  "servings": 4,
  "ingredients": ["400 g Spaghetti", "150 g Pancetta", "..."],
  "directions": ["Reichlich Salzwasser zum Kochen bringen...", "..."],
  "nutrition_per_serving": {"kcal": 620, "protein_g": 28, "fat_g": 24, "carbs_g": 72, "fiber_g": 3}
}
```

### Schritt 2 — Nährwerte pro Portion schätzen

Immer schätzen (nie weglassen), klar als „(Schätzung)“ gekennzeichnet, außer die Quelle liefert echte Werte (dann `"source": "quelle"`). Richtwerte: Nudeln/Reis/Brot ~350 kcal/100g; mageres Fleisch ~160 kcal/100g; fettes Fleisch ~450 kcal/100g; Hartkäse ~390 kcal/100g; Ei ~75 kcal/Stück; Öl/Butter ~880/720 kcal/100g; Nüsse ~650 kcal/100g; Schokolade ~550 kcal/100g; Gemüse ~25–50 kcal/100g. Portionenzahl aus der Quelle übernehmen oder plausibel schätzen (im Zweifel 4).

### Schritt 3 — Bild des Originalrezepts sichern

Wenn die Quelle bereits ein Bild mitliefert, dessen URL merken — Kandidat Nr. 1.

### Schritt 4 — Weitere Bildkandidaten beschaffen

`web_search` mit Suchphrasen wie "<Rezeptname> Rezept chefkoch" oder "<Rezeptname> Foto". 2–3 vielversprechende Bild-URLs identifizieren (direkte CDN-URLs bevorzugen, Google-Thumbnails und Social-Media-Bilder meiden — die brauchen meist Auth oder werden geblockt). Mit `scripts/download_images.py` herunterladen.

### Schritt 5 — Bilder dem Nutzer zeigen und auswählen lassen

Thumbnails zeigen, dann per `clarify`: "Welches Bild soll ins Rezept?" mit den Kandidaten plus "Eigene URL/Datei" und "Ohne Bild".

### Schritt 6 — PDF generieren

Rezeptdaten als JSON schreiben, dann `scripts/generate_recipe_pdf.py --json ... --image ... --output ...` aufrufen (Abhängigkeiten: `pip install --break-system-packages reportlab Pillow`).

**Wichtig:** Vor dem ersten Aufruf prüfen, ob `scripts/generate_recipe_pdf.py` die Mehrseiten-Logik enthält (Suche nach `directions_start_idx` im Skript). Falls nicht vorhanden (z.B. eine ältere Version ohne Fortsetzungsseiten), das vollständige, aktuelle Skript aus dem Skill `rezept-pdf-generator` (Abschnitt "scripts/generate_recipe_pdf.py") an den Skriptpfad schreiben, bevor generiert wird — damit nie Zubereitungstext abgeschnitten wird.

### Schritt 7 — Fertige PDF teilen

PDF an den Nutzer liefern (Download bereitstellen). Keine lange Nachrede.

## Mehrfach-Rezepte

Pro Rezept ein eigenes PDF. Bildauswahl per `clarify` zu einer Mehrfachfrage bündeln.

## Was nicht tun

- Keine Änderungen am Layout ohne ausdrückliche Nutzeranweisung.
- Kein Logo einfügen.
- Nicht nach Einzelheiten fragen, die sich aus der Quelle extrahieren lassen. Nur bei wirklich fehlenden oder unleserlichen Angaben nachfragen.
- Bei Fotos/handschriftlichen Rezepten: niemals den transkribierten Text durch ein online gefundenes ähnliches Rezept ersetzen.

## Weiterführendes

- `references/template-design.md` — exakte Layout-Specs.
- `references/recipe-sources.md` — Tipps zum Parsen häufiger Quellen.
- `scripts/download_images.py` — Bild-Download-Tool.
- `scripts/generate_recipe_pdf.py` — der PDF-Generator mit Mehrseiten-Logik.