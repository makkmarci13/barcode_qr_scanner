# Statisztikai riport használata

A `stats_report.py` nem módosítja a barcode-feldolgozást. Ugyanazt a `read_ean13_from_image()` függvényt hívja meg, mint a meglévő tesztelő `main.py`, csak az eredményeket strukturáltan összegyűjti.

## Futtatás

```bash
python stats_report.py tests/images/rec
python stats_report.py tests/images/single_test
```

Eredményként három fájlt készít:

```text
scanner_report.md      # Markdown riport
scanner_results.csv    # Képenkénti részletes eredménylista
scanner_stats.json     # Géppel feldolgozható statisztika
```

Egyedi kimeneti fájlokkal:

```bash
python stats_report.py tests/images \
  --out reports/ean13_report.md \
  --csv reports/ean13_results.csv \
  --json reports/ean13_stats.json
```

Kevesebb párhuzamos workerrel:

```bash
python stats_report.py tests/images --workers 4
```

## Mit mér?

- jó olvasások száma és aránya
- rossz olvasások száma és aránya
- hibák száma és aránya
- hibatípusok gyakorisága
- jó és rossz találatok score / hits statisztikája
- leggyakoribb módszercsaládok
- legfontosabb rossz beolvasások listája
- fejlesztési javaslatok a hibatípusok alapján

## Hibatípusok jelentése

- `nem_talalt_roi`: a rendszer nem talált barcode-gyanús képrészletet
- `tul_keves_valtas`: a scanline-on kevés fekete-fehér váltás volt, tehát valószínűleg nem a vonalkódon haladt át
- `bizonytalan_olvasas`: több eltérő checksum-helyes jelölt is volt, nincs stabil konszenzus
- `checksum_hiba`: a kód szerkezete olvasható volt, de az ellenőrző számjegy nem stimmelt
- `guard_*`: a start/middle/end guard minták nem voltak elég jók
- `bizonytalan_szamjegy_minta`: egy vagy több számjegy vonalszélesség-mintája túl bizonytalan volt
- `parity_hiba`: a bal oldali L/G mintázatból nem lehetett meghatározni az első számjegyet

## Riport kategorizálása

A riportban a legfontosabb három kategória:

1. **OK**: a fájlnévből várt EAN és az olvasott EAN megegyezik.
2. **ROSSZ**: a scanner adott EAN-t, de az nem egyezik a fájlnévvel. Ez a legkritikusabb kategória.
3. **HIBA**: a scanner nem adott vissza EAN-t. Ez általában jobb, mint a rossz olvasás, mert nem ad hamis eredményt.
