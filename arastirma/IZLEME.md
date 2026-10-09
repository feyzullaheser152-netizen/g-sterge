# VSP İzleme (yeniden doğrulama)

Piyasa değişir; bir özellik zamanla güçlenebilir ya da bozulabilir. Bu dosya `arastirma/izleme.py` ile üretilir: Göstergenin dayandığı her bulgu ay ay yeniden ölçülür.

- **Son çalıştırma:** 2026-10-09 08:16 UTC
- **Veri:** 22 Binance USDT-M paritesi, 2025-01 – 2026-10-05.
- **Durum pencereleri (yalnızca tam aylar):** son 3 tam ay (2026-07 – 2026-09); turuncu uyarı ve FOMC için son 12 tam ay (2025-10 – 2026-09). Eksik ay seride gösterilir, duruma girmez: 2026-10.
- **Yenileme:** `python3 arastirma/izleme.py guncelle`, ardından `python3 arastirma/izleme.py rapor`. Her ay başında çalıştırılmalı.

## Göstergedeki özellikler: durum

| Özellik | Değer | Durum | Bir önceki pencere | Kural |
|---|---|---|---|---|
| Beklenen hareket %80 bandı (hedef 80) | %80,8 | **TUTUYOR** | TUTUYOR | son 3 tam ay; mutlak sapma ≤ 3 tutuyor, ≤ 6 zayıfladı |
| Beklenen hareket %50 bandı (hedef 50) | %51,6 | **TUTUYOR** | TUTUYOR | son 3 tam ay; aynı |
| Sarı beklenen hareket: %80 bandın sarı anlarda kapsaması | %70,0 (diğer anlar %81,1) | **TUTUYOR** | TUTUYOR | son 3 tam ay; sarı uyarı, bant dar kaldığı sürece gerekli: ≤ %76 tutuyor, ≤ %78 zayıfladı, > %78 bozuldu (uyarı gereksiz) |
| Turuncu: SHORT kovalama, 5 dk kayıp | +3,66 bp (t 2,2; parite %100); son 3 ay +2,59 | **TUTUYOR** | TUTUYOR | son 12 tam ay; ≥ +1 bp tutuyor, 0–1 zayıfladı, < 0 bozuldu |
| Turuncu: SHORT kovalama, 15 dk kayıp | +5,08 bp (t 2,0) | **TUTUYOR** | TUTUYOR | son 12 tam ay; aynı |
| Kırmızı: CPI/NFP 08:30 | ×6,48 (22 gün) | **TUTUYOR** | TUTUYOR | son 12 tam ay; ≥ ×3,0 tutuyor, ≥ ×2,0 zayıfladı |
| Mor: CPI/NFP 08:30–08:38 | ×2,62 (22 gün) | **TUTUYOR** | TUTUYOR | son 12 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: Diğer Sal–Cum 08:30 | ×1,59 (n 1034) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: NY açılışı 09:30–09:43 | ×1,71 (n 20328) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: ABD verisi 10:00–10:08 | ×1,63 (n 13068) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: Pazar 18:00–18:07 | ×2,19 (n 2288) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Kırmızı: FOMC 14:00–14:05 | ×3,99 (8 toplantı) | **TUTUYOR** | TUTUYOR | son 12 tam ay; ≥ ×3,0 tutuyor, ≥ ×2,0 zayıfladı |
| Mor: FOMC 13:59–14:44 | ×2,56 (8 toplantı) | **TUTUYOR** | TUTUYOR | son 12 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: Aşırı mum sonrası 4 mum | ×1,66 (n 55744) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |
| Mor: İki yönde sert akış | ×2,05 (n 2304) | **TUTUYOR** | TUTUYOR | son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı |

- **Kaldırma kuralı:** Bir özellik iki ardışık tam ay penceresinde (bu tabloda "Durum" ve "Bir önceki pencere") BOZULDU ise göstergeden çıkarılır. Tek pencerede bozuksa ön kayıtlı testle yeniden sınanır.
- Turuncu uyarı gürültülüdür: 3 aylık ortalamanın standart hatası 2–5 bp. Bu yüzden durumu 12 aylık pencereden verilir.

## İzlenen, göstergede olmayanlar

| Ölçü | Değer | Sonuç | Kural |
|---|---|---|---|
| LONG kovalama, 5 dk kayıp (göstergede yok) | +1,18 bp (t 0,9) | gerek yok | son 12 tam ay; ≥ +1 bp ve t ≥ 2 olursa ön kayıtlı testle yeniden sına |
| Fonlama −3..+2 dk (göstergede yok) | ×1,02 | gerek yok | son 3 tam ay; ≥ ×1,5 olursa yeniden sına |

## Bekleyen ön kayıtlı test: karışım oynaklık tahmini (BULGULAR 10d)

- Kural: Ondalık RMS küçülmeli; genel %80 ve %50 kapsama sapması mevcut modelden en fazla 0,5 puan büyük olabilir.
- Veri birikiyor: 2026-10, 2026-11, 2026-12 tam ayları gerekli; tamamlanan: yok.

## Aylık seri

Oynaklık sütunları ×normal (ayın tüm mumlarına göre). Kovalama sütunları bp (pozitif = o yönde kovalayan ortalamada geride). "Hareket ≥ maliyet %": 15 dk tipik hareketin %0,08 maliyeti (maker + taker + kayma) geçtiği anların oranı.

| Ay | %50 kapsama | %80 kapsama | Sarı %80 kapsama | SHORT kov. 5 dk | SHORT n | LONG kov. 5 dk | CPI/NFP | 08:30 diğer | 09:30 | 10:00 | Pazar | FOMC | Aşırı mum | İki yön | Fonlama | Hareket ≥ maliyet % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-01 | 48,5 | 79,6 | 69,9 | 13,8 | 1113 | -6,3 | 22,43 | 2,51 | 1,88 | 1,79 | 1,67 | 3,35 | 2,16 | 2,42 | 1,07 | 98 |
| 2025-02 | 47,1 | 78,8 | 67,7 | 4,6 | 1150 | 1,4 | 13,33 | 2,20 | 1,66 | 1,78 | 1,94 |  | 2,13 | 2,08 | 1,07 | 98 |
| 2025-03 | 48,4 | 79,9 | 66,8 | 3,2 | 981 | 0,6 | 8,59 | 1,80 | 1,85 | 1,71 | 1,59 | 2,24 | 2,10 | 2,27 | 1,07 | 99 |
| 2025-04 | 48,8 | 79,7 | 67,0 | 11,5 | 975 | 9,6 | 4,73 | 1,30 | 1,86 | 1,67 | 1,89 |  | 1,98 | 2,58 | 0,95 | 97 |
| 2025-05 | 47,7 | 79,0 | 71,3 | 3,1 | 976 | 3,3 | 6,59 | 1,44 | 1,58 | 1,47 | 2,03 | 1,89 | 1,65 | 2,03 | 1,02 | 97 |
| 2025-06 | 48,4 | 79,3 | 64,6 | -4,9 | 995 | -2,8 | 8,20 | 1,56 | 1,60 | 1,52 | 2,21 | 2,20 | 1,61 | 1,62 | 0,95 | 94 |
| 2025-07 | 48,4 | 79,3 | 74,5 | 2,2 | 1090 | -2,4 | 6,80 | 1,37 | 1,59 | 1,46 | 1,92 | 1,79 | 1,61 | 1,86 | 0,94 | 96 |
| 2025-08 | 48,1 | 79,0 | 65,2 | 8,6 | 995 | 1,0 | 9,42 | 4,85 | 2,08 | 2,00 | 1,38 |  | 2,00 | 2,23 | 0,99 | 97 |
| 2025-09 | 47,8 | 78,6 | 69,5 | 7,1 | 1051 | 0,1 | 24,08 | 3,00 | 1,66 | 1,66 | 2,06 | 3,72 | 2,32 | 2,00 | 1,03 | 94 |
| 2025-10 | 50,2 | 80,0 | 73,5 | 15,2 | 1002 | 2,3 | 16,30 | 1,10 | 1,78 | 1,62 | 3,07 | 3,41 | 4,18 | 1,91 | 1,03 | 98 |
| 2025-11 | 49,2 | 79,5 | 68,0 | 4,7 | 1088 | -2,4 | 5,00 | 0,88 | 1,88 | 1,64 | 2,03 |  | 2,36 | 1,76 | 0,98 | 99 |
| 2025-12 | 52,7 | 81,7 | 72,8 | -5,3 | 1038 | 11,6 | 4,08 | 1,18 | 2,07 | 2,21 | 2,18 | 2,94 | 1,83 | 2,39 | 1,08 | 95 |
| 2026-01 | 50,5 | 80,3 | 68,8 | 8,1 | 1237 | 0,3 | 2,73 | 1,26 | 2,09 | 1,80 | 3,00 | 1,81 | 2,24 | 2,14 | 1,27 | 93 |
| 2026-02 | 52,0 | 81,0 | 63,8 | -1,1 | 1058 | -0,9 | 1,29 | 1,57 | 2,17 | 2,08 | 2,48 |  | 1,88 | 2,52 | 0,97 | 99 |
| 2026-03 | 51,8 | 80,4 | 65,7 | 2,6 | 964 | 5,0 | 2,45 | 1,84 | 1,93 | 1,82 | 3,04 | 1,59 | 1,91 | 1,95 | 1,08 | 97 |
| 2026-04 | 52,3 | 81,4 | 73,2 | 0,5 | 890 | 3,4 | 2,36 | 1,29 | 1,45 | 1,38 | 2,70 | 2,93 | 1,71 | 1,72 | 1,07 | 92 |
| 2026-05 | 51,6 | 81,1 | 68,5 | 3,4 | 1187 | 0,1 | 4,05 | 1,60 | 1,52 | 1,67 | 2,72 |  | 1,86 | 2,16 | 1,04 | 92 |
| 2026-06 | 52,3 | 81,4 | 70,1 | 6,9 | 1085 | -1,1 | 6,16 | 1,70 | 1,75 | 1,71 | 2,42 | 2,94 | 1,84 | 2,08 | 1,00 | 98 |
| 2026-07 | 52,6 | 81,9 | 69,0 | 3,9 | 887 | 4,1 | 10,34 | 1,33 | 1,66 | 1,59 | 2,54 | 2,05 | 1,56 | 1,91 | 1,04 | 93 |
| 2026-08 | 52,3 | 81,0 | 74,6 | -2,4 | 997 | -0,8 | 4,76 | 1,60 | 1,69 | 1,61 | 1,95 |  | 1,70 | 2,12 | 1,06 | 87 |
| 2026-09 | 49,9 | 79,5 | 66,8 | 5,9 | 1171 | -5,7 | 21,77 | 1,86 | 1,79 | 1,70 | 2,15 | 2,79 | 1,75 | 2,04 | 0,97 | 96 |
| 2026-10 (eksik) | 50,5 | 80,6 | 68,4 | -4,1 | 159 | 2,4 | 5,28 | 0,47 | 1,78 | 1,82 | 3,56 |  | 1,57 | 1,77 | 1,19 | 90 |
