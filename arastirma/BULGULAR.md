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
- Not (v5.5): Binance metrics verisinde T damgalı satır, T ile T+5 dk arasındaki işlemleri yansıtıyor (bölüm 9b). Bu testlerde kayma düzeltilmemişti; düzeltme yalnızca etkileri küçültür, sonuç değişmez.

**BVC tahmini deltası (`bvc_check.py`):**
- Gerçek taker deltasıyla korelasyon 0,67.
- BVC ile tanımlanan "sert akış" sonrası dönüş: 2025'te +3,8 / +4,7 bp, 2026'da +1,4 / +1,8 bp (5 / 15 dk).
- Bu sonuç, göstergedeki "kovalamayın" uyarısının dayanağıdır.
- Not (v5.6): Bölüm 10c'deki ayrıntılı testte etki yalnızca ilk mumda ve yalnızca sert satış tarafında çıktı.

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
| Haftalık pivot P | +4,4 / +7,2 bp | +4,8 / +5,0 | 0,94 / 0,99 ve 0,88 / 0,92 | v5.3'te eklendi. **Bölüm 9'daki sıkı kontrolde tutmadı; v5.5'te kaldırıldı.** |
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

## 9. Haftalık/aylık seviyeler ve OI (v5.5; bağımsız doğrulama)

### 9a. Seviyeler, yakın placebo kontrolüyle (`levels2.py`, `levels2_rob.py`, `levels3.py`; 22 parite)

**Yöntem:**
- Bölüm 7'deki ölçümler aynı: ilk temastan 15 dk sonra seviyeden geri itilme (bp), tutma oranı, oynaklık.
- **Yeni kontrol:** Her gerçek seviye için aynı dönemde, seviyenin %0,3–1,5 yakınına (rastgele yön) kaydırılmış 4 sahte seviye.
- Bölüm 7'deki eski kontrol, dönemin açılış fiyatına ±%1 uzaklıktaki rastgele seviyelerdi. Bu seviyelere çoğunlukla dönemin başında, fiyat zaten yanındayken dokunuluyor; bağlamları gerçek seviyelerinkinden farklı.
- Standart hata olay haftasına göre kümelendi.
- Ön kayıtlı kural: Bir seviye ancak 2025 ve 2026'da fark ≥ +3 bp, t ≥ 2 ve tutma farkı > 0 ise eklenir.

**Haftalık pivot P, farklı kontrollere karşı (fark bp, t):**

| Kontrol | 2025 | 2026 |
|---|---|---|
| Yakın sahte seviye %0,3–0,75 | +0,1 (0,1) | +1,9 (1,0) |
| Orta %0,75–1,5 | +3,1 (1,0) | +3,7 (2,2) |
| Uzak %1,5–3 | −3,0 (−1,2) | +4,9 (2,8) |
| Eski: açılış ±%1 | +5,3 (1,8) | +5,6 (2,9) |

- Pivotun hemen yanındaki sahte seviyeler pivotla aynı davranıyor; tutma farkı ≈ 0.
- Yani bölüm 7'deki fark, pivotun kendisinden değil, kontrolün seçiminden geliyordu.
- **Bağımsız doğrulama** (ayrı kod, 20 farklı tohum): yakın placeboya karşı +1,6 (t 0,7) / +2,2 (t 1,4); 20 tohumun hiçbirinde kural geçmedi. Eski kontrole karşı bile 20 tohumdan yalnızca birinde geçti.

**Diğer seviyeler (yakın placeboya karşı fark bp, t; 2025 / 2026):**

| Seviye | Fark | Sonuç |
|---|---|---|
| Haftalık R1 / S1 / R2 / S2 | −5 ile +11 bp, t ≤ 2,1, işaret tutarsız | Fark yok |
| Önceki hafta düşük | −7,9 (−3,3) / −5,8 (−1,8); tutma −6,3 / −3,5 puan | Daha sık kırılıyor |
| Önceki hafta yüksek | −3,8 (−1,6) / −3,9 (−1,2) | Biraz daha sık kırılıyor |
| Aylık P / R1 / S1 / önceki ay yüksek-düşük | Küçük örnek, işaret tutarsız | Fark yok |
| Önceki gün düşük | −3,3 (−3,3) / −2,2 (−1,5) | Biraz daha sık kırılıyor |
| Önceki gün yüksek | −1,5 (−1,7) / −0,3 (−0,3) | Fark yok |
| Asya yüksek / düşük | −1,3 ile −0,3 bp | Fark yok |

- Önceki hafta düşüğü bağımsız doğrulamada da aynı çıktı: −8,1 (t −2,8) / −6,7 (t −2,2), parite tutarlılığı %23.
- Önceki dönem uçlarının ilk temasta daha sık kırılması, stop emirlerinin bu seviyelerin hemen ötesinde biriktiği görüşüyle uyumlu. Ancak fark (2–8 bp) maliyetin altında.

**Karar:**
- Haftalık pivot göstergeden kaldırıldı (v5.5).
- Yeni seviye eklenmedi.
- Önceki gün ve Asya çizgileri bilgi amaçlı kaldı; kartlarda ve kodda "tutan seviye" iddiası yok.

### 9b. OI (açık pozisyon) ve oynaklık (`oi_vol.py`, `oi_zaman.py`; 10 parite, 5 dakikalık OI)

**Zaman damgası:**
- T damgalı satırdaki OI değişimi (T−5 → T), en çok [T, T+5) dakikalarındaki hacim ve oynaklıkla ilişkili (Spearman 0,58–0,65 hacim, 0,38–0,47 oynaklık). [T−5, T) penceresinde bu değerler 0,36–0,45 ve 0,28–0,36.
- Yani satır, yaklaşık T+5'teki durumu gösteriyor. T anında kullanmak geleceğe bakmak demek.
- Bağımsız doğrulama bunu 10 paritenin 10'unda, iki yılda da buldu.
- Üçüncü taraf bir ölçüm de arşivin API'ye göre 5 dk erken damgalandığını gösteriyor ([qOeOp/trade#1250](https://github.com/qOeOp/trade/pull/1250)). Binance'te bu konuda yanıtlanmış bir belge bulunamadı ([binance-public-data#509](https://github.com/binance/binance-public-data/issues/509)).
- TradingView'de `BORSA:SEMBOL.P_OI` biçiminde OI sembolleri var. Ücretsiz planda Pine içinden çalıştığı resmi kaynakla doğrulanamadı.

**Sonraki 15 dk oynaklığına ek bilgi** (EWMA + hacim tabanına göre, örneklem dışı R² artışı, parite medyanı):

| Zamanlama | Konum hedefi (log \|getiri\|) | Oynaklık hedefi (log RV) |
|---|---|---|
| Dürüst (OI 5 dk gecikmeli) | +0,0002 / +0,0003 | +0,0004 / +0,0008 |
| Kaymış (geleceğe bakan) | +0,0046 / +0,0067 | +0,017 / +0,023 |

- Dürüst zamanlamada katkı eşiğin (0,005) yaklaşık 20'de biri. Kaymış zamanlama katkıyı 20–25 kat şişiriyor.
- Bağımsız doğrulama aynı sonucu verdi.

**Karar:** OI eklenmedi. Bir `request.*` çağrısı ve ek veri bağımlılığı getirirdi; karşılığında bilgi yok.

### 9c. Yan bulgu: Hacim ve beklenen hareket kutusu

- Son 15 dk hacmi, önceki 24 saatin ortalamasına göre düşükse kutu biraz dar kalıyor; %80 kapsama %75–76. Hacim çok yüksekse kutu biraz geniş kalıyor; kapsama %84–85. İki yılda da aynı yönde.
- Örneklem dışı R² artışı yalnızca +0,001–0,004.
- **Karar:** Eklenmedi. Fark kullanımda hissedilmeyecek kadar küçük.

### 9d. Panel (v5.5)

- Kullanıcının ekran görüntüsünde panel son mumların üstünü kapatıyordu. Satırlar kısaltıldı:
  - "Sıradaki oynaklık anı" yaklaşık yarıya indi.
  - "Uyarı" satırı kaldırıldı; aynı bilgi zaten DURUM satırında.
  - Haftalık pivot satırı kaldırıldı.
- Sayılar Türkçe biçime geçti (ondalık virgül, %4 yazımı).
- "Bağlam" satırı artık neyi ölçtüğünü açıkça yazıyor: fiyatın 15 dk EMA50'ye ve VWAP'a göre konumu. Karşılaştırma son 15 dk kapanışıyla değil, anlık fiyatla yapılıyor.
- `request.*` çağrısı 5'ten 3'e indi.

## 10. Kanıt temizliği ve eksik kategoriler (v5.6; çoklu ajan, bağımsız doğrulama)

Bir denetimde VSP'deki bazı kuralların test edilmediği, bazı kart rakamlarının da iki ayrı testten karıştırıldığı görüldü. Bu bölüm, göstergedeki her kuralı ve daha önce test edilmemiş gösterge kategorilerini aynı yöntemle sınar.

**Ortak ölçü ("× normal"):**
- x = |r1| / σ_taban; σ_taban, önceki 1440 mumun r1 standart sapmasıdır (bir mum gecikmeli).
- Kalın kuyruklar yüzünden x'in sıradan bir dakikadaki ortalaması 1 değil, 0,725 (2025) ve 0,701 (2026) (`taban_oran.py`).
- "× normal" = pencere ortalaması / bu taban. Bölüm 8b'deki çarpanlar farklı bir normalizasyonla hesaplandığından rakamlar biraz farklıdır.
- Ön kayıtlı renk kuralı: Bir koşul iki yılda da ≥ ×3 ise kırmızı, ≥ ×1,5 ise sarı (v5.6'da mor arka plan); aksi hâlde DURUM'u etkilemez.
- Not: Kural ilk yazıldığında eşikler ham x'e uygulanacak biçimde yazılmıştı. Bu ölçek hatası sonuçları gördükten sonra düzeltildi. Fonlama, iki yönlü akış ve likidite için iki okuma aynı kararı veriyor; aşırı mumda yalnızca sarı pencerenin uzunluğu değişiyor.

### 10a. DURUM kuralları (`kural_durum.py`, `kural_likidite.py`, `taban_oran.py`)

| Kural (v5.5) | Ölçüm 2025 / 2026 | Karar (v5.6) |
|---|---|---|
| Fonlama saati ±3 dk → kırmızı | ×1,00 / ×1,04; ≥ ×1,5 olan parite 0/22; komşu saatlere göre fark t −0,7 / 0,4. Ortalama fonlama ödemesi 0,83 / 0,66 bp. | **Kaldırıldı** (DURUM'u etkilemez; fonlama satırı da kaldırıldı) |
| Aşırı mum (> 4 ATR) → 5 mum kırmızı | Sonraki 1–5 mum ×2,11 / ×1,76; hiçbir mum iki yılda ≥ ×3 değil. ≥ ×1,5 kalan mum sayısı 4. | **Kırmızıdan sarıya (mor arka plan)**; süre: spike'tan sonraki 4 mum (5. mum 2026'da ×1,498) |
| İki yönde sert akış → sarı | ×2,36 / ×2,35 (t 8,6 / 12,4); n 1.825 / 1.465 bölüm. Göstergedeki repaint yapmayan tanımla (yalnızca kapanmış mumlar) ×2,13 / ×2,10. | **Sarı kaldı (mor arka plan)** |
| Likidite ince (Amihud liqMult > 1,5) → sarı, kayma × liqMult | Sonraki mumda ×0,82 / ×0,83 (daha sakin). İleri Kyle λ oranı (ref 0,8–1,2 kovası): liqMult 1,5–2 → 1,00 / 0,96; 2–3 → 0,83 / 0,80; =3 → 0,58 / 0,65. Kural ≥ 1,3 istiyordu; artış yok. Üst kovalardaki düşüş büyük ölçüde parite bileşiminden geliyor; parite içinde λ yatay (0,97–1,05). | **Tamamen kaldırıldı** (maliyetten, DURUM'dan ve panelden) |

- Likidite testinde gerçek taker deltası (2·tbv − v) yalnızca doğrulama için kullanıldı. Sabit büyüklükteki emre en yakın ölçüde (ham λ) artış yalnızca %7–21 (en uç kovada %34–81); liqMult ise ×1,7–3 iddia ediyordu. Maliyete etkisi en çok ≈ 0,004 puan.
- liqMult kalıcı bir şeyi doğru ölçüyor: fiyat hareketine göre düşük hacim. Ama bu ne yüksek oynaklık ne de anlamlı ek kayma demek.

### 10b. Zamanlanmış olay pencereleri (`olay_pencere.py`, `olay_suresi.py`)

Dakika başına × normal (22 parite; ABD verisi 08:30 için FOMC günleri hariç tüm Salı–Cuma günleri):

| Olay | Olay dakikası 2025 / 2026 | ≥ ×1,5 ardışık pencere (iki yılda) | v5.6 penceresi |
|---|---|---|---|
| ABD verisi 08:30 ET | ×2,93 / ×2,10 | yalnızca 08:30 (08:31 ×1,60 / ×1,48) | 08:30 |
| NY açılışı 09:30 ET | ×1,89 / ×1,92; 09:31 ×2,20 / ×2,09 | 09:30–09:43; ilk saat ortalaması ×1,62 / ×1,63 | 09:30–09:43 |
| ABD verisi 10:00 ET | ×2,05 / ×1,90 | 10:00–10:08 | 10:00–10:08 |
| Pazar 18:00 ET | ×2,44 / ×4,32 | 18:00–18:07 | 18:00–18:07 |
| FOMC 14:00 ET | ×6,87 / ×7,50 | 14:00–14:13; 14:00–14:05 ortalaması ×3,9 / ×3,9; 14:00–14:44 ortalaması ×2,64 / ×2,36; 13:59 ×4,84 / ×2,32 | 13:59–14:44 mor, 14:00–14:05 kırmızı |

- Olaydan önceki dakikalar (FOMC'de 13:59 hariç) normal düzeyde. Bu yüzden v5.4'teki "2 dk önceden başlayan" pencereler kaldırıldı; yaklaşan olay durum satırındaki geri sayımla görülür.

### 10c. Kovalama uyarısı (`kural_kovalama.py`, bağımsız kontrol `kovalama_yon.py`)

Olay: Önceki 15 mumda aynı yönde akış olmayan ilk sert akış mumu (Pine'daki BVC tanımı). L = olaydan sonra giriş gecikmesi (mum). Kayıp = akış yönünde girenin 15 dk sonraki ortalama zararı (bp).

| L | 2025 (t; + parite) | 2026 (t; + parite) |
|---|---|---|
| 0 | +2,21 (1,0; %77) | +1,75 (1,0; %68) |
| 1–4 | −0,49 (−0,2; %36) | +0,83 (0,6; %68) |
| 5–9 | −2,67 | +1,36 |
| 10–14 | −5,63 | +2,56 |

- Ön kayıtlı kurala göre (her kova ≥ +1 bp, iki yılda) yalnızca ilk mum geçiyor. v5.5'teki 15 mumluk uyarı süresi kanıtsızdı.
- Bağımsız doğrulayıcı bütün kova sayılarını birebir yeniden üretti.
- **Yön ayrımı (iki yılda da aynı; bağımsız kodla birebir yeniden üretildi):**

| L = 0 | 5 dk 2025 / 2026 (t; + parite) | 15 dk 2025 / 2026 (t; + parite) |
|---|---|---|
| Sert satıştan sonra SHORT | +5,32 (2,8; %95) / +3,30 (1,9; %100) | +5,71 (1,9; %91) / +3,37 (1,3; %86) |
| Sert alıştan sonra LONG | +1,30 (1,0; %73) / +0,39 (0,3; %59) | −1,04 (−0,4; %36) / +0,29 (0,1; %64) |

- "LONG kovalamayın" uyarısı iki yılda da desteklenmiyor; kaldırıldı. Kalan uyarı: sert satış akışının ardındaki tek mum.
- BVC filtresi (imb15 ≥ 0,15) pratikte bir şey elemiyor: |z15| ≥ 3 olaylarının %99,7'si filtreden geçiyor. Uyarı fiilen "sert 15 dk düşüş" uyarısıdır.
- v5.5 kartındaki "1,4–4,7 bp, paritelerin %77–95'i" ifadesi iki ayrı testten (BVC ve gerçek delta) karışmıştı; düzeltildi.
- Etki maliyetin (8–12 bp) altında: işlem kenarı değil, "o mumda girersen ortalamada geride başlarsın" bilgisi.

### 10d. Beklenen hareket ufku ve rejim (`kural_ufuk.py`)

- %50 ve %80 katsayıları 1–240 dk ufuklarının hepsinde 0,61 / 1,23'ten %10'dan az sapıyor (en büyük: 1 dk'da +7,8%). Ufka özel katsayı gerekmedi.
- 1 dk ufukta beklenen hareket mumların yalnızca %21–30'unda 8 bp maliyeti geçiyor; 15 dk'da %93–97.
- **Rejim:** Kısa EWMA, piyasa sakinleşince kutuyu fazla daraltıyor (ρ en alt ondalığında %80 kapsama %73), hızlanınca fazla genişletiyor (%87–88).
  - Karışım var = 0,8·ewVar + 0,2·σ_taban² bu sapmayı 2026'da 4,26'dan 1,83 puana indiriyor; paritelerin %100'ünde iyileşme var.
  - Ancak ön kayıtlı "genel kapsama kötüleşmesin (0,5 puan tolerans)" şartı kaldı: %80'de 1,43'e karşı 0,88 puan sapma. Karşılaştırma mevcut modelin lehine eğik, çünkü 0,61 / 1,23 2026 verisiyle de belirlenmişti.
  - **Karar:** Değişiklik yok. Karışım (w = 0,8; katsayılar 0,575 / 1,152) önceden kaydedildi; Ekim 2026 sonrası yeni veride adil kıyasla yeniden sınanacak.

### 10e. Daha önce test edilmemiş kategoriler (`kategori_mum.py`, `kategori_fib.py`, `kategori_prim.py`, `kategori_genislik.py`)

| Kategori | Ön kayıtlı kural | Sonuç |
|---|---|---|
| Mum formasyonları (yutan, çekiç, kayan yıldız, doji, iç/dış mum, üç asker/karga, marubozu; bağlam filtreli sürümler) | 15 dk'da iki yılda \|etki\| ≥ 3 bp, aynı işaret, t ≥ 2 | 12 formasyonun hiçbiri geçmedi; en büyük etki üç kara karga −2,2 / −1,1 bp |
| Fibonacci (önceki gün ve hafta; 0,236–0,786) | Yakın placeboya karşı ≥ +3 bp, t ≥ 2, tutma > 0 | 10 seviyenin hiçbiri geçmedi (5 tohumda 0/5) |
| Baz / prim (Binance premium index, 1 dk) | Yön: ondalık farkı ≥ 4 bp; oynaklık: R² artışı ≥ 0,005 | Yön farkı < 1 bp, işaret yıla göre değişiyor; R² artışı 0,0003–0,0010 |
| Piyasa genişliği, piyasa z15, dominans vekili | ≥ 3 bp ya da R² artışı ≥ 0,005 | Etki ≤ 1 bp (piyasa z15'in 2025'teki +3,4 bp'si 10 Ekim 2025'ten); R² artışı 0,0018–0,0024 |

- Prim verisinin zaman damgası kontrol edildi; geleceğe sızıntı yok.
- TradingView'de CRYPTOCAP:TOTAL ve BTC.D sembolleri var, ancak ücretsiz planda 1 dk erişimi doğrulanmadı; bilgi değeri de yok.
- Test edilmeyenler ve nedeni:
  - Duyarlılık (Korku/Açgözlülük): veri günlük.
  - Grafik formasyonları ve Elliott: 1 dk'da öznel ve seyrek; sıkışma kırılımı bölüm 2'de test edildi (kenar yok).
  - Likidasyon: Binance'in kamuya açık likidasyon arşivi yok.
  - Emir defteri / makas: Pine'da bu veri yok.

### 10f. Kullanıcı isteğiyle görünüm (v5.6)

- Panel (tablo) ve beklenen hareket kutusu grafikten kaldırıldı.
- Bilgi artık durum satırında (hareket / maliyet, beklenen hareket %50 ve %80, sıradaki oynaklık anına kalan dakika) ve Veri Penceresi'nde veriliyor.
- DURUM metni yerine arka plan rengi kullanılıyor: mor (olağandışı oynaklık), kırmızı (FOMC ilk dakikaları), turuncu (sert satıştan sonraki mum).
- Bağlam satırı (15 dk EMA50, VWAP konumu) kaldırıldı; bölüm 6'ya göre trend göstergeleri yön bilgisi vermiyor.
- Çizgiler varsayılan olarak en kalın (4) ve karanlık mod için açık renkli.
- `request.*` çağrısı 3'ten 2'ye indi.

## 11. Sürekli izleme (v5.6.1; `izleme.py`, `IZLEME.md`)

Piyasa değişir: Bir bulgu zamanla güçlenebilir ya da bozulabilir. Bu yüzden göstergenin dayandığı her ölçü ay ay yeniden hesaplanır.

- **Araç:** `arastirma/izleme.py`
  - `guncelle` komutu, data.binance.vision'dan eksik 1 dk mumları indirir. İlk eksik günde durur, böylece kalıcı boşluk oluşmaz.
  - `rapor` komutu, aylık ölçümleri hesaplayıp `arastirma/IZLEME.md` dosyasını yazar.
  - Araştırma betiklerinin kullandığı veri değiştirilmez; izleme verisi ayrı bir klasörde tutulur.
- **Tanımlar** VSP.pine ve bölüm 10 ile aynıdır: aşırı mum olay bazlı, tatil listeleri Pine'daki gibi.
- **Durum pencereleri** yalnızca tam aylardan oluşur:
  - Kapsama ve mor özellikler için son 3 tam ay.
  - Turuncu uyarı ve FOMC için son 12 tam ay. 3 aylık turuncu ortalamasının standart hatası 2–5 bp olduğundan, 3 aylık pencere geçmişte iki kez yanlış "ZAYIFLADI" verirdi.
- **Kaldırma kuralı:** İki ardışık tam ay penceresinde BOZULDU olan özellik çıkarılır. Tek pencerede bozuk çıkarsa ön kayıtlı testle yeniden sınanır.
- **Bekleyen ön kayıtlı test:** 10d'deki karışım oynaklık tahmini. Yalnızca tam 2026-10, 2026-11 ve 2026-12 aylarıyla, bir kez değerlendirilecek.
- **Bağımsız denetim:** Ayrı kodla 2026-09 rakamları birebir yeniden üretildi (turuncu +5,89 bp, n 1171; 08:30 ×4,24; %80 kapsama %79,5). Denetimin bulduğu durum kuralı sorunları düzeltildi.

**İlk rapor (veri 2025-01 – 2026-10-05):**
- Göstergedeki bütün özellikler son tam pencerelerde tutuyor. Turuncu uyarı, son 12 ayda 5 dk'da +3,7 bp (t 2,2; paritelerin %100'ü).
- Zaman içindeki eğilimler:
  - **Aşırı mum sonrası oynaklık azalıyor:** 2025'te çoğunlukla ×2,0–2,3; 2026'da ×1,6–2,2; son 3 ay ×1,56–1,75. Eşiğe en yakın özellik bu.
  - **08:30 ABD verisi** aydan aya çok değişiyor (×1,1–5,5); önemli veri olan aylarda yüksek. 2026 Ocak–Nisan ×1,4–1,9 arasında kaldı.
  - **%50 bandı:** 2025'te %47–49, 2026'da %50–53 kapsıyor. Tolerans içinde ama yön değiştirmiş.
  - **Turuncu uyarı** aydan aya gürültülü (−5 ile +15 bp). Tek ay sonucu tek başına karar için yetmez.
  - Fonlama dakikaları bütün aylarda ×0,9–1,3; LONG kovalamada kalıcı bir etki yok (12 ayda +1,2 bp, t 0,9).

## 12. LuxAlgo "Smart Money Concepts" (`smc_port.py`, `lux_seviye.py`, `lux_olay.py`; bağımsız iki port)

TradingView topluluk betikleri arasında en çok kullanılan gösterge. Bölüm 7'deki FVG/OB testi basitleştirilmiş tanımlarla yapılmıştı. Bu bölüm, betiğin kendi tanımlarını (varsayılan girdiler) birebir sınar.

**Port:**
- İki ajan birbirinden bağımsız Python portu yazdı. Tüm dönemde 1,16 milyon olayın 19'u dışında birebir aynı çıktılar.
- Kalan 19 fark, Pine'ın karşılaştırmalarda 9 ondalık yuvarlama kuralıyla çözüldü.
- Kanonik modül `smc_port.py`; LuxAlgo kodu kopyalanmadı. Mantık uyarlaması olduğu için dosya aynı lisansla (CC BY-NC-SA 4.0) paylaşılır. VSP.pine bu dosyayı kullanmaz.
- TradingView çıktısıyla karşılaştırma yapılamadı. İki portun aynı yorumda birleşmesi spesifikasyonun doğru okunduğunu gösterir, ama kanıtlamaz.

**Olaylar ve durumlar** (z15 eşleştirmeli 15 dk etki, bp, t; 2025 / 2026):

| Öğe | Etki | Sonuç |
|---|---|---|
| BOS iç (5) | −0,50 (−1,2) / −0,40 (−1,4) | Bilgi yok |
| CHoCH iç | −0,02 / +0,03 | Bilgi yok |
| BOS swing (50) | −1,44 (−1,7) / +0,29 (0,4) | Bilgi yok |
| CHoCH swing | −0,36 / +0,80 (1,3) | Bilgi yok |
| İç eğilim ("Color Candles") yönünde | −0,23 (−1,5) / −0,28 (−2,2) | Bilgi yok, hafif ters |
| Premium + Discount (ortalamaya dönüş) | +0,81 (2,0) / +0,96 (2,2) | İstatistik olarak seçilebiliyor ama ≈ 1 bp; 3 bp eşiğinin ve 8–12 bp maliyetin çok altında |

- VSP'nin mor koşulları dışında hiçbir olaydan sonra oynaklık ×1,22'yi geçmedi. z15 eşleştirmesiyle ×0,96–1,06.

**Seviyeler** (yakın placeboya karşı tepki farkı, bp, t; 2025 / 2026):

| Seviye | Fark | Sonuç |
|---|---|---|
| İç Order Block | +2,14 (0,65) / −0,35 (−0,42) | Fark yok; ham tutma farkı bağlam eşleştirmesinde işaret değiştiriyor |
| FVG (otomatik eşik) | +0,24 / −2,33 (−2,95) | Destek/direnç değil; biraz daha sık kırılıyor (≈ 2 bp) |
| EQH (eşit tepeler) | −0,35 / +2,07 | Fark yok |
| EQL (eşit dipler) | +1,85 / −2,13 | Kırpılmış veride biraz daha sık kırılıyor (−3 bp); dayanıksız |
| Strong/Weak High | +0,76 / −0,21 | Fark yok; "Strong" etiketinin bilgisi yok |
| Strong/Weak Low | −0,60 / −0,57 | Fark yok; 2026'da "Strong Low" daha sık kırıldı (iddianın tersi) |

**LuxAlgo'ya özgü notlar:**
- Swing yapısı 50 dk, iç yapı 5 dk gecikmeyle bilinir. Kutular ve etiketler geçmişe çizilir, geçersizleşen bölgeler silinir. Bu yüzden ekran görüntüleri olduğundan isabetli görünür.
- Ayı FVG'nin silme kuralı asimetrik: Fiyat boşluğa dokununca siliniyor (%44'ü bir sonraki mumda).
- 1 dk grafikte parite başına günde yaklaşık 85 FVG ve 70 iç OB oluşuyor.

**Literatür:**
- SMC'nin kendi iddiaları için hakemli kanıt bulunamadı.
- En sistematik iki test kayda değer bir avantaj bulmuyor: hakemsiz bir SSRN çalışması (G10 FX) ve StatOasis'in açık backtest'i (ABD endeksleri). SSRN çalışmasında likidite süpürmesi dönüşü değil, devamı öngörüyor.
- Sağlam yakın bulgu Osler'e (2003, 2005) ait: Stop emirleri belirgin seviyelerin hemen ötesinde kümelenir ve tetiklenince hareket hızlanır. Bizim "önceki gün/hafta düşüğü ve EQL biraz daha sık kırılıyor" bulgumuzla uyumlu, ama etki maliyetin altında.
- Rastgele yürüyüşte de FVG'lerin %73–84'ü dolar; aynı uzaklıktaki rastgele seviyelerde de oran aynıdır. "FVG dolum oranı" tek başına bir şey kanıtlamaz.

**Karar:** VSP'ye LuxAlgo SMC öğesi eklenmedi.
