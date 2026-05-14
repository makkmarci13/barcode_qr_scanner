# EAN-13 scanner statisztikai riport

Készült: 2026-05-14 12:47:49
Forrásmappa: `tests/images/rec`
Képek száma: **1200**

## 1. Eredményösszesítés

| Kategória | Darab | Arány |
| --- | --- | --- |
| OK | 713 | 59.42% |
| WRONG | 10 | 0.83% |
| ERROR | 477 | 39.75% |

## 2. Minőségi mutatók

| Mutató | Érték |
| --- | --- |
| Jó találatok átlag score | 757.33 |
| Jó találatok medián score | 503.08 |
| Rossz találatok átlag score | 26.6 |
| Rossz találatok medián score | 18.28 |
| Jó találatok átlag találatszám | 935.91 |
| Rossz találatok átlag találatszám | 33.9 |
| Sikeres dekódolások átlag ROI száma | 55.28 |

## 3. Hibák gyakorisága

| Hibatípus | Darab | Arány a hibákon belül |
| --- | --- | --- |
| tul_keves_valtas | 258 | 54.09% |
| bizonytalan_olvasas | 207 | 43.4% |
| nem_talalt_roi | 12 | 2.52% |

## 4. Sikeres és rossz találatok módszer szerinti megoszlása

| Módszercsalád | Találatszám |
| --- | --- |
| roi180/otsu | 215412 |
| roi0/otsu | 215254 |
| roi180/adaptive | 71128 |
| roi0/adaptive | 71081 |
| roi270/otsu | 28120 |
| roi90/otsu | 28013 |
| roi270/adaptive | 19300 |
| roi90/adaptive | 19161 |
| roi0/otsu_inverted | 81 |
| roi180/otsu_inverted | 80 |
| roi90/otsu_inverted | 7 |
| roi270/otsu_inverted | 7 |

## 5. Fejlesztési javaslatok

- A legfontosabb fejlesztési irány a hamis pozitív találatok csökkentése. Dokumentációban érdemes kiemelni, hogy a rendszer inkább dobjon bizonytalan hibát, mint rossz EAN-kódot.
- Sok esetben már a ROI-detektálás sem talál vonalkód-gyanús területet. Ezen a barcode-terület keresésének további bővítése segíthet: kisebb/keskenyebb ROI-k, görbült címkék, táblázat melletti vonalkódok, valamint több orientáció kezelése.
- Gyakori a túl kevés fekete-fehér váltás. Ez általában azt jelenti, hogy a scanline nem a vonalkódon halad át, a kivágás túl nagy, a vonalkód túl kicsi, vagy a küszöbölés eltünteti a vékony vonalakat.
- Több eltérő, checksum-helyes jelölt is előfordul. Itt a konszenzuslogika és a minimális score/találatszám küszöb finomhangolása a kulcs.
- A rossz találatok medián score-ja jóval alacsonyabb, mint a jó találatoké. Ez alapján érdemes minimális score- és hits-küszöböt használni.
- A jelenlegi sikerarány 59.42%. Ezt a dokumentációban célszerű külön bontani: jó olvasás, rossz olvasás, és biztonságosan elutasított kép.

## 6. Legfontosabb rossz beolvasások

| Fájl | Elvárt | Olvasott | Score | Találatok | ROI |
| --- | --- | --- | --- | --- | --- |
| 4016364011725-01.jpg | 4016364011725 | 6288601711721 | 64.47958188399477 | 75 | 50 |
| 7613030780564-01.jpg | 7613030780564 | 4161487040470 | 61.226984340942124 | 80 | 52 |
| 4017026055484-01.jpg | 4017026055484 | 5184110628226 | 41.187659375838415 | 54 | 42 |
| 8801037012682.jpg | 8801037012682 | 3228031012688 | 25.886740116987358 | 32 | 58 |
| 8480017169723.jpg | 8480017169723 | 8480017069313 | 19.848391680657524 | 24 | 22 |
| 3256220210492.jpg | 3256220210492 | 8219621522040 | 16.71559095557105 | 24 | 76 |
| 3260260206667.jpg | 3260260206667 | 0737390206667 | 9.535159767518136 | 12 | 54 |
| 4779039730306.jpg | 4779039730306 | 8089831777772 | 9.120957025092709 | 12 | 72 |
| 0047400307308.jpg | 0047400307308 | 7725702732228 | 9.029310993551729 | 12 | 78 |
| 5900531000010.jpg | 5900531000010 | 3289237121222 | 8.966886978394294 | 14 | 42 |

## 7. Példa hibák

| Fájl | Hibatípus | Rövid hibaüzenet |
| --- | --- | --- |
| 0008080025111.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást. Leggyakoribb okok:   - Legjobb jelölt: 0008080025111, score=6.42, találatok=8, módszerek={'... |
| 0011110414380.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást. Leggyakoribb okok:   - Legjobb jelölt: 1382611151111, score=1.99, találatok=3, módszerek={'... |
| 0011110669711.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 38. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0011110855893.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 6088710855893: 16.11, 0011110855893: 7.44   ... |
| 0011110878960.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 0011110878960: 46.56, 0011110777980: 19.07  ... |
| 0011110881786.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 20. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0011111396487.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 0011111396487: 1.63, 3513225711226: 1.62, 02... |
| 0012044039991.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 0012044039991: 1.41, 4107674500112: 1.37   -... |
| 0012546676113.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 14. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0012587783610.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 16. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0013562300846.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 56. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0019100194304.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást. Leggyakoribb okok:   - Legjobb jelölt: 0012101295704, score=3.18, találatok=4, módszerek={'... |
| 0019200893312.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 60. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0020000111971.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást. Leggyakoribb okok:   - Legjobb jelölt: 4537017312162, score=1.61, találatok=2, módszerek={'... |
| 0022506104105.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 8320781877878: 10.05, 8727127459451: 8.06, 0... |
| 0022796916167.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 9133121817927: 1.52, 3451210317162: 0.75, 88... |
| 0025700156215.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: a checksum-helyes jelölt nem kapott elég erős támogatást. Leggyakoribb okok:   - Legjobb jelölt: 0025700156215, score=6.86, találatok=9, módszerek={'... |
| 0028400044042.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 8300718594269: 1.51, 3172479793275: 1.35, 06... |
| 0036000123234.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 62. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0036000373738.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 44. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0036000373905.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 6. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a vi... |
| 0037000042495.jpg | bizonytalan_olvasas | Bizonytalan EAN-13 olvasás: több eltérő kód is checksum-helyes és nem elég nagy köztük a különbség. Leggyakoribb okok:   - Jelöltek: 2157817477070: 4.33, 8282872738577: 3.05, 63... |
| 0037000062219.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 10. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0037000123408.jpg | tul_keves_valtas | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 16. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a v... |
| 0037000867821.jpg | nem_talalt_roi | Nem sikerült EAN-13 kódot olvasni. Vizsgált ROI-k száma: 8. Leggyakoribb okok:   - Túl kevés fekete-fehér váltás látszik a scanline-on; valószínűleg nem a vonalkódon fut át a vi... |
