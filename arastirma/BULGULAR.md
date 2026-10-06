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

## Sonraki araştırma adımı

Binance USDⓈ-M vadeli verisiyle (`data.binance.vision`) çok pariteli test:
- 1 dakikalık mumlardaki **gerçek taker alış hacmi** ile gerçek delta.
- 5 dakikalık **OI ve long/short oranları.**
- Birçok altcoin.

Bu test için bulut ortamının ağ izinlerine `data.binance.vision` eklenmelidir.
