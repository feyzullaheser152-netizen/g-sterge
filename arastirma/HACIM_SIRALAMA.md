# Binance USD-M vadeli: tüm zamanlar toplam hacim sıralaması (ilk 28 sembol)

- Kaynak: data.binance.vision (Binance resmî arşivi), `arastirma/hacim_siralama.py`. Kesim: 2026-10-09. Ölçü: quote hacmi (USDT/USDC/BUSD ≈ USD).
- Dönem: 2019-09 (BTCUSDT) – 2026-10-09. Kapanmış semboller dahil, 1.056 sembol. COIN-M dahil değil.
- Doğrulama: İlk 35 sembol 4 saatlik mumlardan bağımsız yeniden hesaplandı, fark ±%0,005, sıra aynı.

| Sıra | Sembol | Toplam hacim (milyar $) | İlk ay | Durum (son işlem günü) |
|---|---|---|---|---|
| 1 | BTCUSDT | 32.437,1 | 2019-09 | işlemde |
| 2 | ETHUSDT | 19.300,3 | 2019-11 | işlemde |
| 3 | SOLUSDT | 4.367,4 | 2020-09 | işlemde |
| 4 | XRPUSDT | 2.709,5 | 2020-01 | işlemde |
| 5 | DOGEUSDT | 2.206,6 | 2020-07 | işlemde |
| 6 | BTCUSDC | 1.980,6 | 2024-01 | işlemde |
| 7 | ETHUSDC | 1.827,4 | 2024-01 | işlemde |
| 8 | BNBUSDT | 1.472,8 | 2020-02 | işlemde |
| 9 | BTCBUSD | 1.252,8 | 2021-01 | kapandı (2023-12-11) |
| 10 | ADAUSDT | 1.115,4 | 2020-01 | işlemde |
| 11 | 1000PEPEUSDT | 955,6 | 2023-05 | işlemde |
| 12 | LINKUSDT | 810,6 | 2020-01 | işlemde |
| 13 | 1000SHIBUSDT | 766,0 | 2021-05 | işlemde |
| 14 | ETHBUSD | 750,9 | 2021-06 | kapandı (2023-12-11) |
| 15 | LTCUSDT | 748,2 | 2020-01 | işlemde |
| 16 | AVAXUSDT | 745,5 | 2020-09 | işlemde |
| 17 | DOTUSDT | 611,9 | 2020-08 | işlemde |
| 18 | ETCUSDT | 611,4 | 2020-01 | işlemde |
| 19 | SUIUSDT | 606,9 | 2023-05 | işlemde |
| 20 | MATICUSDT | 596,2 | 2020-10 | kapandı (2024-09-04) |
| 21 | BCHUSDT | 553,5 | 2019-12 | işlemde |
| 22 | ZECUSDT | 510,9 | 2020-02 | işlemde |
| 23 | NEARUSDT | 495,1 | 2020-10 | işlemde |
| 24 | FILUSDT | 493,7 | 2020-10 | işlemde |
| 25 | FTMUSDT | 474,5 | 2020-09 | kapandı (2025-01-06) |
| 26 | GMTUSDT | 430,1 | 2022-03 | işlemde |
| 27 | LUNAUSDT | 420,0 | 2021-01 | kapandı (2022-05-12) |
| 28 | EOSUSDT | 410,9 | 2020-01 | kapandı (2025-05-21) |

- Ad değişikliğiyle bölünen hacim: MATICUSDT + POLUSDT = 622,7 (17. sıraya çıkar), FTMUSDT + SUSDT = 496,9 (23.), EOSUSDT + AUSDT = 414,4 (28. kalır). İlk 28'e giren semboller değişmez.
- 28. sıra kırılgan: EOSUSDT (kapandı) ile SANDUSDT arasında 0,9 milyar $ var; SAND güncel hızla birkaç gün içinde geçer.
- Varlık bazında (aynı coinin USDT/USDC/BUSD çiftleri birleşik) sıralanırsa BTCUSDC, ETHUSDC, BTCBUSD ve ETHBUSD çıkar; yerlerine SAND, WIF, GALA ve AXS girer.
- Arşiv notları: 1mo dosyaları 2023-06'da bitiyor, bu yüzden 1d kullanıldı. 1d dosyalarındaki 106 eksik ay 1mo ile tamamlandı (kalan 3 gün eksik). 2019 ayları işlem (trades) dosyalarından eklendi: BTC +88,6, ETH +2,0, BCH +0,4 milyar $.
