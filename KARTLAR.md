# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v4.0.1)

**Amaç:** 1 dakikalık kripto vadeli grafikte yalnızca komisyon ve kaymadan sonra da kâr bırakabilecek az sayıda işlemi göstermek ve sonuçları dürüstçe ölçmek.

**v3.0 testinden çıkan ders (5 parite, 296 işlem):**
- Toplam sonuç −77R, işlem başına −0,26R. Bu kayıp kabaca işlem maliyetine eşit; yani sinyallerin maliyet öncesi kenarı sıfıra yakındı.
- Skor, kazanan ve kaybeden işlemleri ayırt etmiyordu: 80+ skorlu işlemler 70'in altındakilerden daha iyi değildi.
- Kayıpların çoğu, NEAR'da yuvarlak sayılar ve kısa salınım seviyelerindeki aşırı sık süpürme sinyallerinden geldi.

v4.0 bu üç soruna göre yeniden kuruldu.

**Emir ve maliyet modeli:**
- **Giriş:** Varsayılan olarak **limit (maker)** emir.
  - Sinyal mumunun kapanış fiyatına konur ve 3 mum geçerli kalır.
  - Dolmuş sayılması için fiyatın limit seviyesini **aşması** gerekir; yalnızca dokunması yetmez. Bu ihtiyatlı bir varsayımdır.
  - Dolum mumunda stop görülürse işlem stop sayılır.
- **Çıkışlar:**
  - TP çıkışları limit (maker) kabul edilir.
  - Stop, zaman stopu ve ters sinyal çıkışları taker komisyonu ve kayma ile hesaplanır.
- **Kayma:**
  - Amihud likiditesine göre 0,5x ile 3x arasında ölçeklenir.
  - Çeyrek saat açılışlarında 1,5 katına çıkar.
- **Maliyet / risk sınırı:** En kötü durum maliyeti (giriş + stop çıkışı) riskin %20'sini aşarsa sinyal verilmez.

**Kurulum 1 — Trend devamı (yeşil/kırmızı etiket):**
- **Sert koşullar (hepsi zorunlu):**
  - EMA 9/21 trendi ve fiyatın VWAP'ın doğru tarafında olması.
  - Üst ZD (15 dk) aynı yönde.
  - BTC aynı yönde.
  - ER ≥ 0,30.
  - Varyans oranı > 1 (momentum rejimi).
  - Hareket kovalanmıyor olmalı (15 mumluk z < 2).
  - RSI aşırı bölgede olmamalı ve fiyat VWAP ±2σ bandının içinde olmalı.
  - Aşırı mum olmamalı.
- **Tetik:** Hızlı EMA'ya geri çekilip trend yönünde kapanış.
- **Skor:** Koşulları geçen sinyal 50 puanla başlar.
  - Eklenenler: ADX +10, BVC delta +15, OI artışı +10, göreli hacim +10, likit saat +5.
  - Kalabalık pozisyon −10.

**Kurulum 2 — Likidite süpürme + yapı kırılımı (turkuaz/turuncu etiket):**
- **Seviyeler (varsayılan):** Önceki gün yüksek/düşük (25), Asya seansı yüksek/düşük (20), son 240 mumun (4 saat) ucu (15).
- **Varsayılan olarak kapalı:** Yuvarlak sayılar ve kısa salınım noktaları. Bu seviyeler 1 dakikalıkta gürültü üretti.
- **Süpürme mumu:**
  - Seviye son 30 mumda dokunulmamış (taze) olmalıdır.
  - İğne seviyenin 0,1 ile 1,5 ATR ötesine gitmelidir.
  - Mum seviyenin içine geri kapanmalıdır.
  - Akış toksik olmamalı ve güçlü karşı trend olmamalıdır.
- **Yapı kırılımı onayı:** Süpürmeden sonraki 5 mum içinde süpürme mumunun tepesinin (short'ta dibinin) üzerinde kapanış gerekir. Stop, süpürme iğnesinin ötesine konur.
- **Skor (130 üzerinden, 100'e ölçeklenir):**
  - Seviye: 25 / 20 / 15
  - Göreli hacim: 20
  - Güçlü iğne reddi: 15
  - OI düşüşü: 15
  - BTC karşı yönde değil: 10
  - Fiyat VWAP'ın karşı tarafında: 15
  - VR < 1 (ters dönüş rejimi): 10
  - Seviyeye saldırgan akışla gelinmiş: 10
  - Kalabalık pozisyon (prim z-skoru ≥ 2) kalabalık tarafa karşı: 10

**Genel filtreler:**
- Sinyaller yalnızca mum kapanışında oluşur.
- Fonlama saatine ±3 dakika kala sinyal verilmez.
- Sinyaller arasında en az 5 mum olmalıdır.
- En düşük skor 60'tır.

**Risk yönetimi:**
- **Stop:**
  - Trendde son 5 mumun dibi/tepesi, süpürmede iğnenin ucu (0,2 ATR tamponla).
  - Stop mesafesi 0,6 ile 3 ATR arasında tutulur.
- **TP1 = 1R:** Pozisyonun %50'si kapatılır, stop girişe çekilir.
- **TP2 = 2R.**
- **Zaman stopu:** TP1'e 20 mumda ulaşılmazsa pozisyon kapatılır.

**Paneller:**
- **Piyasa paneli (sağ üst):** Rejim, Eğilim (VR), Üst ZD, BTC, Akış (delta / VPIN), OI, Prim, Hacim / kayma, Maliyet / risk, Fonlama, Süpürme takibi, Durum, Uyarı.
- **Performans paneli (sağ alt, komisyon ve kayma dahil):** İşlem / isabet, Net R / PF, Ortalama R, En büyük düşüş, Güven (t), Önerilen risk (yarım Kelly), kurulum bazında sonuçlar, dolmayan limit emir sayısı.
- **Teşhis paneli (sol alt):**
  - 8 bileşenin her biri için, bileşen **varken** ve **yokken** işlem başına ortalama net R'yi gösterir.
  - Yeşil renk, bileşenin sonucu iyileştirdiğini gösterir.
  - Hangi filtrenin gerçekten işe yaradığını veriyle görmek için kullanılır.

**Grafikte:** EMA bulutu, VWAP ve ±2σ bantları, önceki gün (gri), Asya (mor) ve 4 saatlik uç (mavi) seviyeleri, açık pozisyonun çizgileri, bekleyen limit emir (sarı noktalar).

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Grafiği **1 dakika** yapın ve **vadeli (.P)** parite açın.
4. Ayarlar → **Emir ve maliyet** bölümünde borsanızın maker ve taker komisyonlarını girin. Varsayılanlar maker %0,02, taker %0,05 ve kayma %0,01'dir.
5. **Sinyal gelince:**
   - Etiketteki fiyata hemen **limit emir** koyun.
   - Emir 3 mum içinde dolmazsa iptal edin.
   - Dolunca stop emrini ve TP1/TP2 limit emirlerini girin.
   - TP1 dolunca stopu giriş seviyesine çekin.
6. Etiketin üzerine gelince emir fiyatı, stop, TP ve maliyet bilgileri görünür.
7. Alarm için Koşul: VSP → **"Any alert() function call"** seçeneğini seçin. Mesajda emir tipi ve seviyeler hazır gelir.
8. Gerçek parayla işlem yapmadan önce **Performans** panelindeki "Güven" satırına bakın. "Anlamlı kenar" görmeden gerçek para kullanmayın.
9. Geliştirme için 3–5 paritede üç panelin (özellikle **Teşhis**) ekran görüntüsünü gönderin.

## Test Kanıtı (21 ay BTC 1 dakikalık veri)

- Ayrıntılar: `arastirma/BULGULAR.md`.
- **v4.0 mantığı:** 917 bin mum ve 2.746 işlem üzerinde maliyet öncesi kenar yok. Trend kurulumunun brüt kenarı anlamlı biçimde negatif (−0,19R, t −30).
- **Klasik kalıplar:** 15 dk dönüş, VWAP sapması, süpürme, kırılım, sıkışma, dev mum ve saat etkileri test edildi. Hiçbiri maliyeti (8–13 baz puan) aşan ve iki yılda tutarlı bir kenar göstermedi.
- **Uygulamadaki anlamı:** Göstergenin AL/SAT sinyalleri şu an **kanıtlanmış bir kenara sahip değildir**. Gerçek parayla işlem için kullanılmamalıdır.
- **Binance vadeli testi (22 parite, 21 ay, gerçek taker delta):**
  - Tutarlı tek etki, saldırgan akış sonrası 5–15 dakikalık dönüş (1–3 baz puan).
  - Limit ya da piyasa emri fark etmeksizin, gerçekçi maliyetlerle net sonuç her senaryoda negatif (−3,5 ile −12 baz puan).

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- v3.0 (296 işlem) ve v4.0 (19 işlem) ekran görüntüleri ile 21 aylık BTC testi aynı sonucu veriyor: Sinyallerin **kenarı yok**.
- Limit emir simülasyonu TradingView mumlarıyla yapılan bir yaklaşımdır. Gerçekte emir kuyruğundaki sıranız dolumu etkiler.
- Araştırmalar, limit emirlerin en çok fiyat aleyhe giderken dolduğunu söylüyor. Simülasyon bunu kısmen yansıtır.
- Sinyal sayısı v3.0'a göre belirgin şekilde azalacak. Bu bilinçli bir tercih: Az sayıda işlem, daha düşük maliyet yükü demek.
