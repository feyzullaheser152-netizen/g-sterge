# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v5.3)

**Ne yapar:**
- 1 dakikalık kripto vadeli grafikte **piyasayı anlatır**.
- AL/SAT sinyali, stop ya da pozisyon önerisi vermez. Nereden alıp satacağınıza ve stopunuza siz karar verirsiniz.

**Dört soruya cevap verir:**
1. Piyasa şu an işlem için uygun mu? (Fonlama saati, aşırı mum, likidite)
2. Fiyat, komisyonu karşılayacak kadar hareket ediyor mu?
3. Son 15 dakikada sert, saldırgan bir akış oldu mu?
4. Önümüzdeki dakikalarda fiyat tipik olarak ne kadar oynar?

**Panel satırları:**

| Satır | Ne gösterir |
|---|---|
| DURUM | **Yeşil:** "Koşullar uygun". **Sarı:** "DİKKAT", sebebiyle birlikte (hareket maliyete yakın, likidite ince, iki yönde sert akış). **Kırmızı:** "UYGUN DEĞİL", sebebiyle birlikte (fonlama saati, aşırı mum, hareket maliyetten küçük, yanlış zaman dilimi, hacim verisi yok). |
| Hareket / maliyet | Seçilen ufukta tipik hareketin (%50 dilim), gidiş-dönüş komisyon ve kaymanın kaç katı olduğu. 2 kat ve üstü yeşil, 1–2 kat sarı, 1'in altı kırmızı. |
| Beklenen hareket | Seçilen ufukta fiyatın %50 ve %80 olasılıkla kalacağı aralık (±%). |
| Son 15 dk akış | Tahmini delta (%) ve hareketin z-skoru. Sert alış akışıyla yükselişten sonra 15 mum "LONG kovalamayın", sert satış akışıyla düşüşten sonra "SHORT kovalamayın". |
| Fonlama | Bir sonraki fonlamaya kalan süre. |
| Oynaklık (1 dk ATR) | 1 dakikalık ortalama hareket (%). Mum boyu 4 ATR'yi aşarsa 5 mum boyunca "aşırı mum" uyarısı verir. |
| Likidite (kayma çarpanı) | Amihud ölçüsüne göre piyasanın ince olup olmadığı ve kaymanın kaç kat arttığı. |
| Bağlam (bilgi, sinyal değil) | 15 dakikalık trend yönü ve fiyatın VWAP'a göre konumu. |
| Haftalık pivot (P) | Geçen haftanın (yüksek + düşük + kapanış) / 3 seviyesi ve fiyatın bu seviyeye uzaklığı (%). |
| Uyarı | Yanlış zaman dilimi ya da eksik hacim verisi. |

**Grafikte:**
- VWAP ve ±2σ bantları.
- Önceki gün yüksek/düşük (gri).
- Asya seansı yüksek/düşük (mor).
- Haftalık pivot P (açık mavi, kalın).
- Beklenen hareket kutusu (mavi): Seçilen ufukta fiyatın %80 olasılıkla kalacağı aralık.
- Kovalama uyarısı sırasında turuncu arka plan.
- Çizgilerin değerleri durum satırını kalabalıklaştırmaz.

**Dayanak (22 Binance vadeli paritesi, 21 ay):**
- **Beklenen hareket:**
  - 15 dakikalık gerçek hareketlerin %50'si öngörülen oynaklığın 0,61 katı içinde kalır, %80'i 1,23 katı içinde.
  - Bu oranlar 2025 ve 2026'da neredeyse aynıdır.
- **Kovalama uyarısı:** Saldırgan akışla gelen sert 15 dakikalık hareketten sonra fiyat 5–15 dakika içinde ortalama 1,4–4,7 baz puan geri döner. Bu, paritelerin %77–95'inde ve iki yılda da tutar.
- **Haftalık pivot:** Fiyat bu seviyeye ilk dokunduğunda, rastgele seviyelere göre 15 dakika içinde 4–7 baz puan daha fazla geri itilir ve %5 daha sık tutunur. Seviyede oynaklık da azalır. Bu fark 22 paritede, iki yılda da görüldü.
- **Topluluk göstergelerindeki seviyeler (SMC/ICT, Volume Profile, pivotlar):**
  - FVG, rastgele seviyeden daha sık kırılır.
  - Order Block, gün açılışı, VWAP ve 4 saatlik pivot rastgele seviyeden farksızdır.
  - Önceki günün POC seviyesi yalnızca zayıf bir fark gösterir.
  - Bu yüzden bu seviyeler panele eklenmedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 7.
- **TradingView'in yerleşik göstergeleri (48 gösterge test edildi):**
  - Hiçbiri 1 dakikalık grafikte maliyeti aşan yön bilgisi vermiyor.
  - Hiçbiri gelecek 30 dakikanın trend mi yatay mı olacağını öngörmüyor.
  - Hiçbiri beklenen hareket tahminini iyileştirmiyor.
  - Bu yüzden panele eklenmediler. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 6.

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Ayarlar → **Maliyet** bölümünde borsanızın maker ve taker komisyonlarını ve girişte kullandığınız emir tipini seçin. Bu bilgiler yalnızca "Hareket / maliyet" satırı için kullanılır.
4. Ayarlar → **Piyasa koşulu** bölümünde şunları seçin:
   - Paritenizin fonlama aralığını (8, 4 ya da 1 saat).
   - Beklenen hareket ufkunu (dakika; varsayılan 15).
5. Paneli işlem kararlarınızda bilgi olarak kullanın:
   - **Kırmızı DURUM:** Piyasa o an işlem için elverişsiz.
   - **"Hareket / maliyet" 1'in altında:** Fiyat, komisyonu karşılayacak kadar oynamıyor.
   - **Kovalama uyarısı:** O yönde yeni giriş ortalamada dezavantajlı başlar.
   - **Beklenen hareket kutusu:** Fiyatın tipik oynama payını gösterir.
6. Alarmlar: Koşul VSP → "Sert alış akışı", "Sert satış akışı" ya da "Koşullar düzeldi".

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- 22 parite ve 21 aylık testlere göre 1 dakikalık grafikte hiçbir gösterge, maliyeti aşan yön bilgisi vermiyor. VSP de yön söylemez; piyasanın durumunu, hareketin büyüklüğünü ve maliyetle ilişkisini gösterir.
- Tahmini delta, gerçek taker deltasıyla yaklaşık 0,67 korelasyonludur; birebir aynı değildir.
