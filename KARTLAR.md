# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v1.0)

**Amaç:** TradingView'de 1 dakikalık kripto vadeli işlem grafiğinde yalnızca trend yönünde, hacimle desteklenen ve komisyonu karşılayan işlemleri göstermek.

**Bileşenler:**
- **Üst zaman dilimi trendi:** 15 dk kapanışı, 50 EMA'nın üstünde veya altında.
- **1 dk trend:** EMA 9/21 bulutu ve günlük VWAP.
- **Tetik:** Fiyat hızlı EMA'ya geri çekilir ve trend yönünde kapanır.
- **Filtreler:**
  - ADX ≥ 20: yatay piyasayı eler.
  - Göreli hacim ≥ 1,3x.
  - RSI aşırılık sınırı.
  - Fiyat VWAP ±2σ bandının dışına taşmamış olmalıdır.
- **Komisyon filtresi:** TP2 mesafesi, gidiş-dönüş komisyonun en az 2 katı olmalıdır. Aksi hâlde sinyal verilmez.
- **Risk:**
  - Stop: 1,5 × ATR.
  - TP1: 1R. TP1'e ulaşılınca stop giriş seviyesine çekilir.
  - TP2: 2R.
- **Panel:** Trendleri, VWAP konumunu, ADX'i, hacmi, komisyon oranını ve pozisyon durumunu gösterir.
- **Repaint yok:** Sinyaller mum kapanışında oluşur. Üst zaman dilimi verisi kapanmış mumdan alınır.

## Talimat Kartı

1. TradingView'de **Pine Düzenleyici**'yi açın, `VSP.pine` içeriğini yapıştırın ve **Grafiğe ekle**'ye basın.
2. Grafiği **1 dakika** yapın. Hacim verisi olan bir vadeli parite seçin (ör. BINANCE:BTCUSDT.P).
3. Ayarlar → Risk → **Gidiş-dönüş komisyon %** değerini kendi borsanıza göre girin. Varsayılan değer %0,10'dur (taker + taker).
4. **AL/SAT** etiketi çıktığında gösterilen Giriş/Stop/TP seviyelerini kullanın. Panelde "Durum" satırını izleyin.
5. Alarm kurmak için Alarm → Koşul: VSP → **"Any alert() function call"** seçeneğini seçin. Mesajda seviyeler hazır gelir.
6. Panel "Hacim verisi yok" veya "1 dk grafiğe geçin" uyarısı veriyorsa işlem yapmayın.
7. İşlem başına sermayenin en fazla %1'ini riske atın. Kaldıracı stop mesafesine göre belirleyin.

## Dürüst Not

Hiçbir gösterge kâr garantisi vermez. 1 dakikalık işlemlerde komisyon ve kayma, getiriyi en çok azaltan kalemlerdir. Gerçek parayla işlem yapmadan önce en az 100 sinyali kayıt altına alın ve test edin.
