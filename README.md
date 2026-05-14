# <u>Barcode</u> & QR Code processor

## Folyamatok leírása

- [Barcode folyamat](https://github.com/makkmarci13/barcode_qr_scanner/blob/development/docs/Barcode.md) - Ez lett kidolgozva
- [QR code folyamat](https://github.com/makkmarci13/barcode_qr_scanner/blob/development/docs/QR.md)

## Használata

### Általános használat

```bash
source .venv/bin/activate
python main.py [kép / mappa]
```

### Egyetlen fájl dekódolása példa

```bash
python main.py tests/images/0037000867821.jpg
```

### Mappák dekódolása példa

```bash
python main.py tests/images/rec
python main.py tests/images/single_test
```

## Dokumentáció

```
TODO...
```

## Tesztelés & Statisztika

- Használt adatforrás: [DEAL KAIST Lab Barcode Dataser](https://www.kaggle.com/datasets/s0dium/deal-kaist-lab-barcode-main/data)
- [Statisztika generálása](https://github.com/makkmarci13/barcode_qr_scanner/blob/development/STATISTICS_USAGE.md)
