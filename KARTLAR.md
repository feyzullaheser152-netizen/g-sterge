# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v3.0)

**Amaç:** 1 dakikalık kripto vadeli grafikte yalnızca komisyon ve kaymadan sonra da kâr bırakabilecek, puanı yüksek işlemleri göstermek ve geçmiş sonuçları dürüstçe ölçmek.

**Dayandığı disiplinler:**
- **Piyasa mikro yapısı:**
  - BVC delta (Easley, López de Prado, O'Hara)
  - VPIN akış toksisitesi
  - Amihud likiditesi
- **Ekonometri:** Varyans oranı testi (Lo–MacKinlay).
- **Davranışsal finans:** Yuvarlak sayılarda emir kümelenmesi (Osler).
- **Olasılık ve bilgi kuramı:** Kelly oranı.
- **İstatistik:** t-testi.

**İki kurulum:**
1. **Trend devamı (yeşil/kırmızı etiket):**
   - Fiyat EMA 9/21 trendinde ve günlük VWAP'ın doğru tarafında olmalıdır.
   - Fiyat hızlı EMA'ya geri çekilip trend yönünde kapanmalıdır.
   - RSI aşırı bölgede olmamalı, fiyat VWAP ±2σ bandını aşmamış olmalıdır.
2. **Likidite süpürme (turkuaz/turuncu etiket):**
   - Fiyat şu seviyelerden birinin ötesine iğne atmalıdır: önceki gün yüksek/düşük, Asya seansı (00–08 UTC) yüksek/düşük, **yuvarlak sayı** ya da son salınım seviyesi.
   - Mum aynı seviyenin içine geri kapanmalıdır.
   - Güçlü ve karşı yönde bir trendde ya da **toksik akışta** (VPIN yüzdeliği ≥ 90) bu sinyal verilmez.

**Skor (0–100):** Puanlar toplanır ve kurulumun en yüksek puanına göre 100'e ölçeklenir (trend 110, süpürme 130 üzerinden). Varsayılan en düşük skor 60'tır.

| Bileşen | Trend devamı | Likidite süpürme |
|---|---|---|
| Üst ZD (15 dk EMA 50) yönü | +20 | – |
| Süpürülen seviye: önceki gün / Asya / yuvarlak sayı / salınım | – | +25 / +20 / +15 / +10 |
| BTC yönü (altcoinlerde) | +15 | +10 (BTC karşı yönde değilse) |
| Rejim: Verimlilik oranı (ER) ≥ 0,25 | +15 | – |
| ADX ≥ 20 ve DI yönü | +10 | – |
| BVC delta (3 mum) | +15 | – |
| Güçlü geri kapanış (iğne reddi) | – | +15 |
| Açık pozisyon (OI) | +10 (artıyorsa) | +15 (düşüyorsa) |
| Göreli hacim ≥ 1,3x | +10 | +20 |
| Likit saat (07–21 UTC) | +5 | – |
| Fiyat VWAP'ın karşı tarafında | – | +15 |
| Varyans oranı (15 mum) | +10 (VR > 1, momentum) | +10 (VR < 1, ters dönüş) |
| Seviyeye saldırgan akışla gelinmiş (önceki delta güçlü ve karşı yönde) | – | +10 |
| Kalabalık pozisyon (prim z-skoru ≥ 2) | −10 (kalabalık yönde) | +10 (kalabalık tarafa karşı) |
| Kovalamaca (15 mumluk hareket z ≥ 2, giriş yönünde) | −10 | – |
| Hedef yönünde 0,5R içinde yuvarlak sayı (kâr-al duvarı) | −10 | – |

**Sert filtreler:**
- Sinyaller yalnızca mum kapanışında oluşur.
- Fonlama saatine ±3 dakika kala sinyal verilmez.
- Sinyaller arasında en az 5 mum olmalıdır.
- **Aşırı mum:** Mum boyu 4 ATR'yi aşarsa trend sinyali, 8 ATR'yi aşarsa süpürme sinyali verilmez.
- **Maliyet / risk:** Komisyon ve kaymanın toplamı riskin %30'unu aşarsa sinyal verilmez.

**Kayma modeli:**
- Kayma, **Amihud likidite oranına** göre 0,5x ile 3x arasında ölçeklenir. Piyasa inceldikçe kayma artar.
- Giriş bir çeyrek saat açılışına (:00, :15, :30, :45) denk gelirse kayma 1,5 katına çıkar. Bu dakikaların ilk saniyeleri daha oynaktır.

**Risk yönetimi:**
- **Stop:** Son 5 mumun dibi/tepesi ya da süpürme iğnesinin ucu, 0,2 ATR tamponla. Stop mesafesi 0,6 ile 2,5 ATR arasında tutulur.
- **TP1 = 1R:** Pozisyonun %50'si kapatılır, stop girişe çekilir.
- **TP2 = 2R.**
- **Zaman stopu:** TP1'e 20 mumda ulaşılmazsa pozisyon kapatılır.

**Performans paneli (sağ alt, komisyon ve kayma dahil):**
- **İşlem / isabet**, **Net R / PF**, **Ortalama R / işlem**, **En büyük düşüş.**
- **Güven (t):**
  - 30'dan az işlem: "Az veri".
  - t ≥ 2: "Anlamlı kenar".
  - 1 ≤ t < 2: "Zayıf kanıt".
  - −1 < t < 1: "Kenar yok".
  - t ≤ −1: "Negatif kenar".
- **Önerilen risk (yarım Kelly):** Geçmiş sonuçlardan hesaplanır ve en fazla %1 olur. 30 işlemden önce en fazla %0,25 önerilir.
- **Trend devamı / Likidite süpürme:** İki kurulumun sonuçları ayrı gösterilir.
- **Skor <70 / 70–79 / 80+:** Her skor aralığının işlem sayısı ve net R'si gösterilir. Böylece en düşük skor eşiği veriye göre ayarlanabilir.
- Aynı mumda hem stop hem hedef görülürse önce stop sayılır (ihtiyatlı varsayım).

**Piyasa paneli (sağ üst):** Rejim, Eğilim (VR), Üst ZD, BTC, Akış (delta / VPIN), OI, Prim, Hacim / kayma, Maliyet / risk, Fonlama, Trend skoru, Durum, Uyarı.

**Grafikte:** EMA bulutu, VWAP ve ±2σ bantları, önceki gün ve Asya seviyeleri, en yakın yuvarlak sayı (gri noktalar), açık pozisyonun giriş/stop/TP çizgileri.

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Grafiği **1 dakika** yapın ve **vadeli (.P)** parite açın, ör. BINANCE:ETHUSDT.P. OI ve prim verisi yalnızca vadeli paritelerde gelir.
4. Ayarlar → **Risk ve maliyet** bölümünde kendi komisyonunuzu girin:
   - Varsayılan değerler taker için tek yön %0,05 ve normal likiditede kayma için tek yön %0,01'dir.
   - Limit (maker) emirle giriyorsanız komisyonu %0,02 yapın.
5. Ayarlar → **Fonlama aralığı** değerini paritenize göre seçin (8, 4 ya da 1 saat).
6. Etiketi okuyun:
   - **AL/SAT + sayı:** Yön ve skor.
   - **Renk:** Kurulum tipi.
   - Etiketin üzerine gelince giriş, stop, TP, maliyet, VR ve VPIN bilgileri görünür.
7. **Maliyet / risk** satırı kırmızıysa o paritede o anki oynaklık komisyonu karşılamıyordur ve sinyal gelmez. Bu bir koruma; daha oynak paritelere geçin ya da limit emir kullanın.
8. Alarm için Koşul: VSP → **"Any alert() function call"** seçeneğini seçin.
9. Gerçek parayla işlem yapmadan önce sağ alttaki **Performans** paneline bakın:
   - "Güven" satırı **"Anlamlı kenar"** demiyorsa sonuç şanstan ayırt edilemiyor demektir.
   - Risk olarak **Önerilen risk** satırındaki değeri aşmayın.
   - Eksi veren kurulumu ya da skor aralığını kapatın: Ayarlar → Sinyal → kurulum seçimi veya en düşük skor.
   - Panelin ekran görüntüsünü gönderin, ayarları birlikte iyileştirelim.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- Akademik bulgu: Kripto paritelerinde 15 dakikalık ters dönüş eğilimi yaygın, ancak tek başına kazancı (yaklaşık 1,3 baz puan) maliyetin (yaklaşık 5 baz puan) altında. Bu yüzden gösterge bu etkiyi yalnızca filtre olarak kullanır.
- BVC delta, 1 dakikalık mumda gerçek alış/satış verisine göre yaklaşık bir tahmindir.
- VPIN'in tahmin gücü akademide tartışmalıdır. Gösterge onu yalnızca süpürme sinyallerini durduran bir uyarı olarak kullanır.
- Panel, grafikte yüklü kısa bir geçmişi ölçer. Bu, gelecekteki sonuçların kanıtı değildir.
