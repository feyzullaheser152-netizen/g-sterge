# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v2.0)

**Amaç:** 1 dakikalık kripto vadeli grafikte yalnızca komisyon ve kaymadan sonra da kâr bırakabilecek, puanı yüksek işlemleri göstermek ve geçmiş sonuçları dürüstçe ölçmek.

**İki kurulum:**
1. **Trend devamı (yeşil/kırmızı etiket):**
   - Fiyat EMA 9/21 trendinde ve günlük VWAP'ın doğru tarafında olmalıdır.
   - Fiyat hızlı EMA'ya geri çekilip trend yönünde kapanmalıdır.
   - RSI aşırı bölgede olmamalı ve fiyat VWAP ±2σ bandını aşmamış olmalıdır.
2. **Likidite süpürme (turkuaz/turuncu etiket):**
   - Fiyat önceki gün yüksek/düşük, Asya seansı (00–08 UTC) yüksek/düşük ya da son salınım seviyesinin ötesine iğne atmalıdır.
   - Mum aynı seviyenin içine geri kapanmalıdır.
   - Güçlü ve karşı yönde bir trendde bu sinyal verilmez.

**Skor (0–100):** Etiketteki sayı sinyalin skorudur. Varsayılan en düşük skor 60'tır.

| Bileşen | Trend devamı | Likidite süpürme |
|---|---|---|
| Üst ZD (15 dk EMA 50) yönü | 20 | – |
| Süpürülen seviye: önceki gün / Asya / salınım | – | 25 / 20 / 10 |
| BTC yönü (altcoinlerde) | 15 | 10 (BTC karşı yönde değilse) |
| Rejim: Verimlilik oranı (ER) ≥ 0,25 | 15 | – |
| ADX ≥ 20 ve DI yönü | 10 | – |
| Tahmini delta (3 mum) | 15 | 15 (güçlü geri kapanış) |
| Açık pozisyon (OI) | 10 (OI artıyorsa) | 15 (OI düşüyorsa) |
| Göreli hacim ≥ 1,3x | 10 | 20 |
| Likit saat (07–21 UTC) | 5 | – |
| Fiyat VWAP'ın karşı tarafında | – | 15 |

**Sert filtreler:**
- Sinyaller yalnızca mum kapanışında oluşur.
- Fonlama saatine ±3 dakika kala sinyal verilmez.
- Sinyaller arasında en az 5 mum olmalıdır.
- **Maliyet / risk:** Komisyon ve kaymanın toplamı riskin %30'unu aşarsa sinyal verilmez.

**Risk yönetimi:**
- **Stop:** Son 5 mumun dibi/tepesi ya da süpürme iğnesinin ucu, 0,2 ATR tamponla. Stop mesafesi 0,6 ile 2,5 ATR arasında tutulur.
- **TP1 = 1R:** Pozisyonun %50'si kapatılır, stop girişe çekilir.
- **TP2 = 2R.**
- **Zaman stopu:** TP1'e 20 mumda ulaşılmazsa pozisyon kapatılır.

**Geçmiş performans:**
- Panel, grafikte yüklü geçmişteki bütün sinyalleri bu kurallarla işler.
- İşlem sayısını, isabet oranını, toplam net R'yi ve kâr faktörünü (PF) gösterir.
- Komisyon ve kayma bu hesaba dahildir.
- Aynı mumda hem stop hem hedef görülürse önce stop sayılır (ihtiyatlı varsayım).

**Panel satırları:** Rejim, Üst ZD, BTC, Delta, OI, Göreli hacim, Maliyet / risk, Fonlama, Trend skoru, Durum, Geçmiş işlem / isabet, Net R / PF, Uyarı.

## Talimat Kartı

1. Pine Düzenleyici'de eski kodu **Ctrl+A** ile seçip silin. Kodu GitHub'daki **"Copy raw file"** düğmesiyle kopyalayın ve yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Grafiği **1 dakika** yapın ve **vadeli (.P)** parite açın, ör. BINANCE:ETHUSDT.P. OI verisi yalnızca vadeli paritelerde gelir.
4. Ayarlar → **Risk ve maliyet** bölümünde kendi komisyonunuzu girin:
   - Varsayılan değerler taker için tek yön %0,05 ve kayma için tek yön %0,01'dir.
   - Limit (maker) emirle giriyorsanız komisyonu %0,02 yapın.
5. Ayarlar → **Fonlama aralığı** değerini paritenize göre seçin. Bazı paritelerde fonlama 8 yerine 4 ya da 1 saatte bir yapılır.
6. Etiketi okuyun:
   - **AL/SAT + sayı:** Yön ve skor.
   - **Renk:** Kurulum tipi.
   - Etiketin üzerine gelince giriş, stop, TP ve maliyet bilgileri görünür.
7. **Maliyet / risk** satırı kırmızıysa, o paritede o anki oynaklık komisyonu karşılamıyordur. Bu durumda sinyal gelmez. Bu bir hata değil, korumadır. BTC'de taker emirle sık görülür; daha oynak paritelere geçin ya da limit emir kullanın.
8. Alarm için Koşul: VSP → **"Any alert() function call"** seçeneğini seçin. Mesajda kurulum, skor ve seviyeler hazır gelir.
9. Gerçek parayla işlem yapmadan önce panelin **Net R / PF** satırına bakın:
   - PF 1,2'nin altındaysa ya da işlem sayısı 50'den azsa sonuç güvenilir değildir.
   - Ayarları birlikte iyileştirelim.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- 1 dakikalık işlemlerde net getiriyi en çok komisyon ve kayma belirler. Bu yüzden gösterge maliyeti riskle karşılaştırır.
- Delta, mum içi işlem verisinden değil, kapanışın mum içindeki konumundan **tahmin** edilir.
- Panel, grafikte yüklü geçmişi (planınıza göre birkaç gün ile birkaç hafta arası) ölçer. Bu kısa süre, gelecekteki sonuçların kanıtı değildir.
- İşlem başına sermayenin en fazla %1'ini riske atın.
