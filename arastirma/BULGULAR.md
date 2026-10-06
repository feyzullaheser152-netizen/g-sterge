# Geriye Dönük Test Bulguları

## Veri

- **Kaynak:** Bitstamp BTC/USD spot, 1 dakikalık mumlar ([ff137/bitstamp-btcusd-minute-data](https://github.com/ff137/bitstamp-btcusd-minute-data), `data/updates/btcusd_bitstamp_1min_latest.csv`).
- **Dönem:** 7 Ocak 2025 – 6 Ekim 2026, 917.480 mum.
- **Bölme:** 2025 keşif, 2026 doğrulama.
- **Kısıtlar:**
  - Vadeli değil spot verisi; tek parite (BTC).
  - OI ve fonlama verisi yok.
  - Bitstamp hacmi Binance vadeliye göre ince.

## 1. VSP v4.0 mantığının birebir simülasyonu (`run1.py`)

| Ayar | İşlem | Brüt R / işlem | Maliyet R / işlem | Net R / işlem | t |
|---|---|---|---|---|---|
| Varsayılan (maliyet / risk ≤ 0,20R) | 74 | +0,015 | 0,137 | −0,122 | −0,99 |
| Maliyet sınırı yok | 2.746 | −0,179 | 1,354 | −1,533 | −30,0 |
| — Trend devamı | 2.593 | −0,190 | 1,396 | −1,586 | −29,6 |
| — Süpürme | 153 | 0,000 | 0,643 | −0,643 | −6,7 |

**Sonuç:**
- v4.0 sinyallerinin maliyet öncesi kenarı yok. Trend devamı kurulumunun brüt kenarı istatistiksel olarak anlamlı biçimde negatif.
- BTC'de 1 dakikalık ATR ortalama 5,4 baz puan, gidiş-dönüş maliyet ise 8–13 baz puan. Bu yüzden dar stoplarla maliyet riskin üzerine çıkıyor.

## 2. Olay çalışmaları (ileri getiri, baz puan, işlem yönünde)

Maliyet referansı: Gidiş-dönüş yaklaşık 8–13 baz puan.

| Olay | 2025 | 2026 | Yorum |
|---|---|---|---|
| 15 dk aşırı hareket (z ≥ 2) sonrası dönüş | 0 ile +1 | −2 ile 0 | Maliyetin çok altında |
| VWAP ±2σ dışı → VWAP'a dönüş | −1 ile +3 | 0 ile +5 | Maliyetin altında, tutarsız |
| Süpürme (önceki gün / Asya / 4 saat) dönüşü | Long: −16 ile +4; Short: +6 ile +16 | Long: +1 ile +20; Short: −9 ile +2 | İşaret yıllar arasında değişiyor; az örnek |
| Önceki gün tepe/dip kırılımı | −8 ile +1 | 0 ile +8 | Tutarsız |
| 4 saatlik uç kırılımı | −1 ile +2 | −3 ile −1 | Kenar yok |
| Sıkışma sonrası kırılım | −1 ile +5 | −3 ile +3 | Kenar yok |
| Dev mum (> 5 ATR) sonrası dönüş | −4 ile +1 | −8 ile +4 | Kenar yok |
| Saatlik trend (EMA50 + 24 saat momentum) | −7 (t −3,4) | +5 (t +2,0) | Rejime bağlı, işaret değişiyor |
| Saate göre getiri | — | — | Yıllar arasında tutarlı saat yok |

## Genel sonuç

- Bu veride, OHLCV'den türetilen klasik 1 dakikalık kalıpların hiçbiri maliyeti aşan ve iki yılda da tutarlı bir kenar göstermedi.
- Bu sonuç akademik bulguyla uyumludur: Kripto paritelerinde 15 dakikalık ters dönüş yaygın, ancak kenar yaklaşık 1,3 baz puan, maliyet yaklaşık 5 baz puan ([arXiv 2608.21888](https://arxiv.org/abs/2608.21888)).
- Kullanıcının TradingView ekran görüntüleri de aynı yönde:
  - v3.0: 296 işlemde −77R.
  - v4.0: 19 işlemde −5R.

## 3. Binance USDⓈ-M vadeli testi (22 parite, gerçek taker delta)

**Veri ve yöntem:**
- **Kaynak:** `data.binance.vision`, 1 dakikalık mumlar, Ocak 2025 – Eylül 2026. 22 parite, yaklaşık 20 milyon mum, boşluk yok.
- **Pariteler:** BTC, ETH, SOL, XRP, DOGE, BNB, ADA, AVAX, LINK, LTC, DOT, NEAR, SUI, AAVE, UNI, ENA, 1000PEPE, WIF, ARB, OP, ZEC, HYPE.
- **Delta:** `2 × taker alış hacmi − hacim`. Bu gerçek değerdir, tahmin değildir.
- **Hipotezler:** Testten önce belirlendi. 2025 keşif, 2026 doğrulama dönemi olarak kullanıldı.
- **Betikler:** `events_bn.py`, `dose.py`, `h1sim.py`.

**Sonuçlar** (ileri getiri, işlem yönünde, baz puan; parantez içinde getirisi pozitif çıkan parite oranı):

| Hipotez | 2025 (5 / 15 dk) | 2026 (5 / 15 dk) | Sonuç |
|---|---|---|---|
| H1: Saldırgan akışın sürüklediği 15 dk hareket (z ≥ 3) → dönüş | +3,4 / +3,4 (%95 / %77) | +2,5 / +3,0 (%91 / %86) | **Tutarlı, ama küçük** |
| H2b: Aşırı akış + fiyat aynı yönde → devam | −0,5 / −1,0 | −0,5 / −0,5 | Devam etmiyor, hafif dönüyor |
| H4: 4 saatlik kırılım + güçlü akış → devam | −1,6 / −1,8 | −1,9 / −1,7 | Kırılım kısa vadede başarısız |
| H5: BTC liderliği (altcoin geride) | +1,1 / +7,9 | +0,6 / +0,4 | 2026'da kayboldu |
| H2: Emilim | ≈ 0 | ≈ 0 | Kenar yok |
| H3: Tasfiye benzeri dev mum → dönüş | tutarsız | tutarsız | Kenar yok |
| H6: Önceki gün seviyesi süpürme + karşı akış | negatif | hafif pozitif | Tutarsız |

**Doz-yanıt (`dose.py`):**
- Güvenilir bölgede (z 2–4) dönüş kenarı 1–3 baz puan.
- Uç değerler (z ≥ 5) çok az olaydan oluşuyor ve işaretleri tutarsız.

**Gerçekçi işlem simülasyonu (`h1sim.py`):** H1 sinyaline limit emirle girilip 15 dakika tutulduğunda:

| | 2025 | 2026 |
|---|---|---|
| Limit dolum oranı | %95 | %93 |
| Dolan işlemlerde brüt getiri | −2,3 bp | +0,5 bp |
| Net, limit giriş + limit çıkış (4 bp) | −6,3 bp | −3,5 bp |
| Net, limit giriş + piyasa çıkış (8 bp) | −10,3 bp | −7,5 bp |
| Net, piyasa / piyasa (12 bp) | −11,9 bp | −9,8 bp |

Limit emirler, kenarın bulunduğu anlarda değil, fiyat aleyhe giderken doluyor (ters seçim). Bu yüzden limit emir maliyet avantajını geri alıyor.

## Genel sonuç (güncel)

- 1 dakikalık vadeli işlemlerde istatistiksel olarak tutarlı tek etki, saldırgan akış sonrası kısa vadeli dönüştür. Büyüklüğü 1–3 baz puandır.
- Standart (VIP 0) komisyonlarla bu etki her senaryoda maliyetin altında kalır. Net getiri negatiftir.
- Akademik bulguyla birebir uyumludur ([arXiv 2608.21888](https://arxiv.org/abs/2608.21888)). Bu etkiyi kâra çevirebilenler maker iadesi alan piyasa yapıcılardır.
- **Uygulamadaki anlamı:** Perakende komisyonlarıyla 1 dakikalık grafikte göstergeye dayalı yön tahmini, kanıta göre net zarar üretir.


## 4. Ek testler (1 dakikalık işlemde kenar arayışının son adımları)

**Akış dönüşünü yakalama ızgarası (`revgrid.py`):**
- Toplam 144 ayar denendi: limit mesafesi 0/0,5/1 ATR, TP, SL, süre ve eşikler.
- Üç maliyet senaryosu kullanıldı:

| Senaryo | 2025'te pozitif ayar | 2026'da pozitif ayar | En iyi 8 ayarın 2026 ortalaması |
|---|---|---|---|
| Binance VIP 0 (maker %0,02 / taker %0,05) | %0 | %0 | −5,5 bp |
| Hyperliquid (maker %0,015 / taker %0,045) | %0 | %0 | −4,5 bp |
| Düşük ücret (maker %0 / taker %0,02) | %1 | %1 | −0,9 bp |

**Fonlama saati etkisi (`funding.py`):** İşaretler yıllar arasında değişiyor. Etki, o yılın genel piyasa yönünden ayırt edilemiyor; kenar yok.

**OI ve long/short oranı (`oi_test.py`, `oi_base.py`; 10 parite, 5 dakikalık metrikler):**
- OI sıçraması ya da düşüşü: Tutarsız.
- Kalabalık short (L/S oranı en düşük %5'lik dilim) → long: Piyasa yönünden arındırıldıktan sonra 2025'te +4 ile +10 bp, 2026'da 30–60 dakikalık ufukta yalnızca +0,6 ile +0,9 bp. 1 dakikalık işlem için yetersiz; ayrıca TradingView'de bu veri yok.

**BVC tahmini deltası (`bvc_check.py`):**
- Gerçek taker deltasıyla korelasyon 0,67.
- BVC ile tanımlanan "sert akış" sonrası dönüş: 2025'te +3,8 / +4,7 bp, 2026'da +1,4 / +1,8 bp (5 / 15 dk).
- Bu sonuç, göstergedeki "kovalamayın" uyarısının dayanağıdır.

**Karar:** Göstergeden AL/SAT sinyalleri kaldırıldı (v5.0). Kullanıcı kararı kendisi verir; gösterge maliyet, koşul, akış ve pozisyon büyüklüğü bilgisi sunar.

## 5. Oynaklık kalibrasyonu (v5.1 için; `volcal.py`, `bracket.py`)

**Beklenen hareket:** Getiri oranı = |15 dk getiri| / (öngörülen σ × √15).

| Model | Yıl | %50 dilim | %80 dilim | %95 dilim |
|---|---|---|---|---|
| Kısa EWMA (30 mum) | 2025 | 0,629 | 1,246 | 2,106 |
| Kısa EWMA (30 mum) | 2026 | 0,588 | 1,205 | 2,129 |

Göstergede 0,61 ve 1,23 katsayıları kullanılır. HAR benzeri karışım ve saat etkisi eklemek tahmin gücünü artırmadı.

**Stopun gürültüyle vurulma oranı (%):** k = stop mesafesi / (σ × √N).

| k | 0,5 | 1,0 | 1,5 | 2,0 | 2,5 | 3,0 |
|---|---|---|---|---|---|---|
| Gerçek (5/15/30 dk ve iki yıl ortalaması) | 57,5 | 28,8 | 13,5 | 6,4 | 3,2 | 1,8 |
| Brown hareketi formülü | 61,7 | 31,7 | 13,4 | 4,6 | 1,2 | 0,3 |

**Rastgele girişte hedefin stoptan önce gelme oranı (stop = 1σ×√15):**

| Hedef | 1R | 1,5R | 2R | 3R |
|---|---|---|---|---|
| Gerçek | %49 | %39 | %31,5 | %21 |
| Teorik 1/(1+R) | %50 | %40 | %33 | %25 |

## 6. TradingView yerleşik göstergeleri (`tvind.py` – `tvind4.py`; 22 parite, 2025 / 2026)

**Yön (15 dk ileri getiri):** Test edilen 48 göstergenin hepsi aynı sonucu verdi:
- Test edilen göstergeler: RSI, MACD, CCI, Awesome, Aroon, Balance of power, Bull bear power, CMF, Chaikin osc., CMO, Connors RSI, Elder force, Fisher, DPO, %b, Ichimoku, KAMA/Hull/DEMA/EMA eğimi, Donchian, VWMA−SMA, Ease of movement, A/D, BBTrend, Stokastik, Stokastik RSI, Williams %R, MFI, TSI, Ultimate, TRIX, ROC, Momentum, Vortex, Supertrend, Parabolik SAR, OBV, Klinger, Keltner, lineer regresyon, RVI, SMI ergodic, Woodie CCI, PVT, Alligator, McGinley, RCI.
- **Ters işaret:** "Yukarı" okumanın ardından fiyat hafifçe düşüyor. IC −0,01 ile −0,046 arasında ve bu işaret paritelerin %95–100'ünde tutuyor.
- **Büyüklük:** %10'luk uç dilimler arasındaki fark yalnızca 0,1–1,2 baz puan. Maliyet 4–12 baz puan.
- **Sonuç:** 1 dakikalık grafikte bu göstergeler kısa vadeli dönüş etkisinin farklı biçimlerde ölçümüdür. Hiçbiri maliyeti aşan yön bilgisi vermez.

**Oynaklık (sonraki 15 dk gerçekleşen oynaklık, EWMA tahminine ek açıklama gücü):**
- **ATR (14):** R² +0,04–0,05. Bu artış gerçekleşen oynaklığı (toplam salınımı) açıklıyor. Ancak 15 dk sonraki fiyat konumunu öngörmeyi iyileştirmiyor; log korelasyon 0,255'e karşı 0,251. Bu yüzden göstergeye eklenmedi.
- **Diğerleri** (Bollinger genişliği, tarihsel oynaklık, Donchian genişliği, Choppiness, ADX, Mass index, Relative volatility index, Ulcer, Relative volume at time): R² artışı ≤ 0,0026.

**Rejim (sonraki 30 dk verimlilik oranı):** ADX, Choppiness, ER, BBTrend ve Aroon ile korelasyon |0,02|'nin altında. Bu göstergeler geçmişi tarif eder, gelecek 30 dakikanın trend mi yatay mı olacağını öngörmez.

**Seans (saat profili) ve ADR:** 60 dk oynaklık tahminine ek açıklama gücü ≤ 0,0024.

**Pivot noktaları (standart, günlük; günün ilk teması, gün boyu sabit rastgele seviyelerle karşılaştırma):** Seviyeden geri itilme farkı:

| Seviye | 2025 | 2026 |
|---|---|---|
| P | +0,9 bp | +1,4 bp |
| R1 | +1,7 bp | +0,1 bp |
| S1 | +1,7 bp | +2,0 bp |

Fark maliyetin çok altında.

**Karar:** Listedeki göstergelerden hiçbiri, 1 dakikalık grafikte VSP'nin verdiği bilgiye anlamlı bir şey eklemiyor. Bu yüzden panel sade tutuldu (v5.2).

## 7. Topluluk göstergelerindeki seviye kavramları (`levels.py`; 22 parite)

**Kapsam:**
- SMC/ICT: FVG, Order Block.
- Volume Profile: önceki günün POC, VAH ve VAL seviyeleri.
- HTF Power of Three: gün açılışı.
- Günlük VWAP.
- CM Pivot Points MTF: haftalık ve 4 saatlik pivot P.
- Salınım tepe/dip seviyeleri: Pivot Points High Low, Price Action S/R, Key Levels.

**Ölçüm:**
- Seviyeye ilk temastan 15 dakika sonra seviyeden geri itilme (bp).
- Tutma oranı: Kapanışın, seviyenin 0,5σ ötesine geçmeme oranı.
- Oynaklık: Gerçekleşen oynaklığın tahmine oranı.
- Karşılaştırma: Gün boyu sabit rastgele seviyeler.

| Seviye | Tepki farkı (2025 / 2026) | Tutma farkı (puan) | Oynaklık (seviye / rastgele) | Sonuç |
|---|---|---|---|---|
| Haftalık pivot P | +4,4 / +7,2 bp | +4,8 / +5,0 | 0,94 / 0,99 ve 0,88 / 0,92 | **Tutarlı; göstergeye eklendi (v5.3)** |
| Önceki gün POC | +1,3 / +1,8 bp | +3,4 / +0,7 | 0,96 / 0,98 | Zayıf |
| Önceki gün VAH | +0,4 / +1,8 bp | +3,2 / +1,1 | — | Zayıf |
| Önceki gün VAL | +1,1 / −0,4 bp | +2,5 / +0,1 | — | Tutarsız |
| FVG | −1,6 / −1,1 bp | −3,6 / −4,1 | — | Rastgele seviyeden **daha sık kırılıyor** |
| Order Block | −0,4 / +0,2 bp | +0,3 / −0,4 | 0,88 / 0,93 | Fark yok |
| Salınım tepe/dip | −1,2 / −0,2 bp | −2,1 / −1,3 | — | Biraz daha sık kırılıyor |
| Gün açılışı | −0,3 / −0,4 bp | −3,2 / −2,6 | 1,04 / 0,98 | Fark yok, temas anında biraz daha oynak |
| VWAP | −0,2 / −0,4 bp | ≈ 0 | — | Fark yok |
| 4 saatlik pivot P | +0,1 / +0,5 bp | ≈ 0 | — | Fark yok |

Notlar:
- Topluluk göstergelerinin yön sinyali veren kısımları (SuperTrend, UT Bot, WaveTrend, Squeeze Momentum, VuManChu, Lorentzian vb.) bölüm 6'da test edilen osilatör ve trend ailelerinden oluşur. Ayrıca test edilmedi.
- Nadaraya-Watson'ın orijinal sürümü geçmişi yeniden çizer (repaint).

## 8. Coine özel / piyasa geneli ayrımı ve zamanlanmış oynaklık anları (v5.4; çoklu ajan analizi ve bağımsız doğrulama)

### 8a. "Hareket coine mi özel, piyasa geneli mi?" (`coin_vs_market*.py`, doğrulama `dogrula/verify_cvm*.py`)

**Yöntem:**
- BTC dışındaki 21 paritede sert akışlı 15 dk hareketler alındı (|z15| ≥ 3, akış aynı yönde ≥ 0,15).
- Hareketler, aynı anda BTC'nin 15 dk z-skoruna göre sınıflandırıldı:
  - **Piyasa geneli:** BTC aynı yönde ≥ 1,5.
  - **Coine özel:** |BTC| < 0,75.
  - **Karışık:** Diğerleri.
- Bağımsız doğrulama 68.695 olayın tamamını birebir yeniden üretti.

**Sonuçlar:**
- **Sınıflar arası fark:** Coine özel ile piyasa geneli arasındaki 15 dk dönüş farkı iki yılda ve iki delta türünde de anlamsız (|güne göre kümelenmiş t| ≤ 1,4). İşareti de tutarsız.
- **2025 piyasa geneli:** +4,1 bp'nin neredeyse tamamı 10 Ekim 2025 çöküşünden geliyor. O gün hariç tutulunca +1,9 bp (tG 0,7) kalıyor.
- **2026 piyasa geneli:** +4,0 bp'nin yaklaşık dörtte üçü BTC'nin kendi dönüşü; BTC'ye göre hedge edilmiş getiri +1,1 bp.
- **Coine özel:** BTC'ye göre hedge edilmiş getiri +3–4 bp ile sınırda anlamlı (tG 1,8–1,9). Ancak göstergenin BVC deltasıyla 2026'da kayboluyor ve hedge iki bacak gerektirdiği için maliyet iki katına çıkıyor.

**Karar:** Göstergeye eklenmedi.

### 8b. Zamanlanmış oynaklık anları (`zaman_oynak*.py`, doğrulama `dogrula/zv_*.py`)

**Yöntem:**
- Normalize 1 dk hareket: x = |r1| / σ_önceki (EWMA 1440, bir mum gecikmeli).
- Dakika profili UTC ve New York saatinde ayrı ayrı çıkarıldı; hafta içi ve hafta sonu ayrı tutuldu.
- Hafta içinde iki yılda da ≥ ×1,5 olan dakikaların **hepsi** New York saatine bağlı. UTC'de görünen sıçramalar, aynı olayların yaz/kış saatiyle 1 saat kayan kopyası.
- Doğrulayıcı rakamları üç farklı normalizasyonla yeniden üretti (EWMA σ, Pine'daki 1440 mumluk std, haftalık taban).

| Olay | 2025 | 2026 | Not |
|---|---|---|---|
| ABD verisi 08:30 ET (Sal–Cum) | ×2,1–2,6 | ×1,8–2,0 | Etki veri günlerinde yoğunlaşıyor. Gün medyanı ×1,0–1,4; fazlalığın %70'i günlerin %10'undan geliyor. Pazartesi ×1,1–1,2. Süre 2–3 dk. |
| NY borsa açılışı 09:30 ET (Pzt–Cum) | ×2,0, 09:31'de ×2,3 | ×2,0, 09:31'de ×2,2 | 09:30–10:30 arası ×1,6–1,7. NYSE tatillerinde kayboluyor. |
| ABD verisi 10:00 ET (Pzt–Cum) | ×2,0 | ×1,9 | Açılış bloğunun içinde; yerel sıçrama ×1,2–1,3. Cuma ×2,4. |
| Haftalık vadeli açılışı, Pazar 18:00 ET | ×2,1 | ×3,6 | Kaynağı Globex endeks/döviz vadelileri. CME kripto 29 Mayıs 2026'da 7/24'e geçtikten sonra da sürüyor. |
| FOMC 14:00 ET (yalnızca FOMC günü) | medyan ×5,6 | medyan ×4,3 | Örnek küçük (8 / 6 gün), ama 14 günün 14'ünde ×1,5'in üstünde. 14:30 basın toplantısında ×2–3. 13:59 FOMC günlerinde sakin değil. |

**Eşiği iki yılda geçmeyenler:**

| Dakika | Çarpan |
|---|---|
| Fonlama dakikaları (00/08/16 UTC) | ×1,07–1,47 |
| 16:00 ET | ×1,2–1,3 |
| Hafta içi 18:00 ET | ×1,4 |
| Çeyrek saat başları | ×1,03–1,20 |

**Göstergeye etkisi:**
- Çeyrek saat sonuçlarına göre v3.0'dan beri kullanılan "çeyrek saat kayma çarpanı ×1,5" kanıtsızdı. v5.4'te kaldırıldı.
- Zamanlanmış olaylar "Sıradaki oynaklık anı" satırı, arka plan rengi ve DURUM uyarısı olarak eklendi (v5.4).
- Bu bilgi yön söylemez; yalnızca o dakikalarda oynaklığın ve kaymanın arttığını bildirir.

### 8c. Literatür ve TradingView ücretsiz plan (araştırma ajanı)

**Literatür:**
- **FOMC:** BTC'nin saatlik mutlak getirisi açıklama saatinde yaklaşık 1,9 kat artıyor ("Scheduled FOMC statements and intraday macro event risk in cryptocurrency markets", FRL 2026).
- **Spot ETF dönemi:** BTC'nin gün içi oynaklık tepeleri NY saatine bağlı. Saat, oynaklığı ve hacmi öngörüyor ama **yönü öngörmüyor** ("Keeping New York's hours", SSRN 2026; "Bitcoin on Wall Street Time", JRFM 2026).
- **Kripto dönüşü ve maliyet:** Kriptoda 15 dk dönüşün büyük kısmı coine özel. Ancak brüt kenar işlem başına 1,3 bp, maliyet 5 bp (arXiv 2608.21888). Bu, 8a'daki bulguyla çelişmiyor: Dönüş var, ama sınıflandırma onu maliyeti aşacak ölçüde ayırmıyor.

**Ücretsiz plan:**
- Grafikte en fazla 5.000 mum yükleniyor. 1 dk grafikte bu yaklaşık 3,5 gün demek; ilk 1–1,5 gün ısınma dönemi.
- request.* çağrıları için sınır 40; VSP 5 tane kullanıyor.
- Gösterge (teknik) alarmları ücretsiz planda büyük olasılıkla kullanılamıyor. Bu yüzden VSP'nin uyarıları grafikte görsel olarak verilir.
