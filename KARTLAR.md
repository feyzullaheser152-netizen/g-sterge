# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v5.5)

**Ne yapar:**
- 1 dakikalık kripto vadeli grafikte **piyasayı anlatır**.
- AL/SAT sinyali, stop ya da pozisyon önerisi vermez. Nereden alıp satacağınıza ve stopunuza siz karar verirsiniz.

**Beş soruya cevap verir:**
1. Piyasa şu an işlem için uygun mu? (Fonlama saati, aşırı mum, likidite, zamanlanmış olay)
2. Fiyat, komisyonu karşılayacak kadar hareket ediyor mu?
3. Son 15 dakikada sert, saldırgan bir akış oldu mu?
4. Önümüzdeki dakikalarda fiyat tipik olarak ne kadar oynar?
5. Sıradaki zamanlanmış oynaklık anı ne zaman? (ABD verisi, NY borsa açılışı, FOMC, haftalık vadeli açılışı)

**Panel satırları:**

| Satır | Ne gösterir |
|---|---|
| DURUM | **Yeşil:** "Koşullar uygun". **Sarı:** "DİKKAT", sebebiyle birlikte (zamanlanmış oynaklık anı, hareket maliyete yakın, likidite ince, iki yönde sert akış). **Kırmızı:** "UYGUN DEĞİL", sebebiyle birlikte (FOMC açıklaması, fonlama saati, aşırı mum, hareket maliyetten küçük, yanlış zaman dilimi, hacim verisi yok). |
| Hareket / maliyet | Seçilen ufukta tipik hareketin (%50 dilim), gidiş-dönüş komisyon ve kaymanın kaç katı olduğu. 2 kat ve üstü yeşil, 1–2 kat sarı, 1'in altı kırmızı. |
| Beklenen hareket | Seçilen ufukta fiyatın %50 ve %80 olasılıkla kalacağı aralık (±%). |
| Son 15 dk akış | Akış durumu, tahmini delta (%) ve hareketin z-skoru. Sert alış akışıyla yükselişten sonra 15 mum "LONG kovalamayın", sert satış akışıyla düşüşten sonra "SHORT kovalamayın". |
| Sıradaki oynaklık anı | En yakın zamanlanmış olay, TSİ saati, kalan süre ve tipik oynaklık çarpanı. Olay anında "ŞİMDİ". FOMC 7 gün içindeyse ayrıca tarihi gösterilir. |
| Fonlama | Bir sonraki fonlamaya kalan süre. |
| Oynaklık (1 dk ATR) | 1 dakikalık ortalama hareket (%). Mum boyu 4 ATR'yi aşarsa 5 mum boyunca "aşırı mum" uyarısı verir. |
| Likidite (kayma çarpanı) | Amihud ölçüsüne göre piyasanın ince olup olmadığı ve kaymanın kaç kat arttığı. |
| Bağlam (bilgi, sinyal değil) | Fiyatın 15 dakikalık EMA50'ye ve günlük VWAP'a göre konumu. |

**Grafikte:**
- VWAP ve ±2σ bantları.
- Önceki gün yüksek/düşük (gri).
- Asya seansı yüksek/düşük (mor).
- Beklenen hareket kutusu (mavi): Seçilen ufukta fiyatın %80 olasılıkla kalacağı aralık.
- Kovalama uyarısı sırasında turuncu arka plan.
- Zamanlanmış oynaklık anlarında mor arka plan.
- Çizgilerin değerleri durum satırını kalabalıklaştırmaz.

**Dayanak (22 Binance vadeli paritesi, 21 ay):**
- **Beklenen hareket:**
  - 15 dakikalık gerçek hareketlerin %50'si öngörülen oynaklığın 0,61 katı içinde kalır, %80'i 1,23 katı içinde.
  - Bu oranlar 2025 ve 2026'da neredeyse aynıdır.
- **Kovalama uyarısı:** Saldırgan akışla gelen sert 15 dakikalık hareketten sonra fiyat 5–15 dakika içinde ortalama 1,4–4,7 baz puan geri döner. Bu, paritelerin %77–95'inde ve iki yılda da tutar.
- **Zamanlanmış oynaklık anları:** Hafta içi iki yılda da ×1,5'i geçen sıçrama dakikalarının hepsi New York saatine bağlı. Yaz/kış saati otomatik hesaba katılır.

  | Olay | Saat (ET) | Günler | Tipik çarpan | Süre |
  |---|---|---|---|---|
  | ABD verisi | 08:30 | Sal–Cum | Veri gününde ×2–3, veri yoksa ≈×1 | 2–3 dk |
  | NY borsa açılışı | 09:30 | Pzt–Cum | ×2 (zirve 09:31) | İlk saat ×1,6–1,7 |
  | ABD verisi | 10:00 | Pzt–Cum | ×2 | Açılış saatinin içinde |
  | Haftalık vadeli açılışı | Pazar 18:00 | Pazar | ×2–3,5 | Yaklaşık 4 dk |
  | FOMC açıklaması | 14:00 | Yalnızca FOMC günü | ×4–6 (14:30 basın toplantısı ×2–3) | Yaklaşık 45 dk |

  - ABD tatilleri (2028 sonuna kadar) ve FOMC tarihleri (2027 sonu, 2028 Ocak) gösterge içinde tanımlıdır.
  - Fonlama dakikaları, çeyrek saat başları, 16:00 ET ve hafta içi 18:00 ET eşiği iki yılda geçmediği için eklenmedi.
- **Haftalık pivot (v5.5'te kaldırıldı):**
  - v5.3'te, rastgele seviyelerden daha iyi tuttuğu sonucuyla eklenmişti.
  - Daha sıkı testte pivot, aynı haftada hemen yanındaki (%0,3–0,75) sahte seviyelerden farksız çıktı: 2025'te +0,1, 2026'da +1,9 baz puan; ikisi de anlamsız.
  - Eski test, pivotu haftanın açılışına yakın rastgele seviyelerle kıyaslıyordu; bu kontrol farkı abartıyordu. Bağımsız doğrulama da aynı sonucu buldu.
- **Haftalık ve aylık seviyeler (R1, S1, R2, S2, aylık pivot, önceki hafta ve ay yüksek/düşük):**
  - Hiçbiri yakınındaki sahte seviyelerden daha iyi tutmuyor.
  - Önceki hafta ve önceki gün uçları ilk temasta biraz daha sık kırılıyor (2–8 baz puan). Bu fark maliyetin altında.
  - Bu yüzden panele eklenmedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 9.
- **Topluluk göstergelerindeki seviyeler (SMC/ICT, Volume Profile, pivotlar):**
  - FVG, rastgele seviyeden daha sık kırılır.
  - Order Block, gün açılışı, VWAP ve 4 saatlik pivot rastgele seviyeden farksızdır.
  - Önceki günün POC seviyesi yalnızca zayıf bir fark gösterir.
  - Bu yüzden bu seviyeler panele eklenmedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 7.
- **OI (açık pozisyon):**
  - Oynaklık tahminine katkısı yok: örneklem dışı R² artışı 0,0003, eşik 0,005.
  - Basit testte görünen katkı, Binance OI verisindeki 5 dakikalık zaman kaymasından geliyordu.
  - Bu yüzden eklenmedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 9.
- **"Hareket coine mi özel, piyasa geneli mi?" ayrımı:** 21 altcoinde test edildi; sert hareket sonrası dönüşü iki yılda tutarlı biçimde ayırmıyor. Eklenmedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 8.
- **TradingView'in yerleşik göstergeleri (48 gösterge test edildi):**
  - Hiçbiri 1 dakikalık grafikte maliyeti aşan yön bilgisi vermiyor.
  - Hiçbiri gelecek 30 dakikanın trend mi yatay mı olacağını öngörmüyor.
  - Hiçbiri beklenen hareket tahminini iyileştirmiyor.
  - Bu yüzden panele eklenmediler. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 6.

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın. Panel son mumları kapatırsa grafiği fareyle biraz sola sürükleyin ya da Ayarlar → **Görünüm** → **Panel konumu**'nu değiştirin.
3. Ayarlar → **Maliyet** bölümünde borsanızın maker ve taker komisyonlarını ve girişte kullandığınız emir tipini seçin. Bu bilgiler yalnızca "Hareket / maliyet" satırı için kullanılır.
4. Ayarlar → **Piyasa koşulu** bölümünde şunları seçin:
   - Paritenizin fonlama aralığını (8, 4 ya da 1 saat).
   - Beklenen hareket ufkunu (dakika; varsayılan 15).
5. Paneli işlem kararlarınızda bilgi olarak kullanın:
   - **Kırmızı DURUM:** Piyasa o an işlem için elverişsiz.
   - **"Hareket / maliyet" 1'in altında:** Fiyat, komisyonu karşılayacak kadar oynamıyor.
   - **Kovalama uyarısı:** O yönde yeni giriş ortalamada dezavantajlı başlar.
   - **Beklenen hareket kutusu:** Fiyatın tipik oynama payını gösterir.
6. **Zamanlanmış olaylar:**
   - "Sıradaki oynaklık anı" satırı yaklaşan olayı TSİ saatiyle gösterir.
   - Olay anında arka plan mor olur ve DURUM sarıya döner; FOMC sırasında kırmızıya.
   - Bu dakikalarda kayma ve makas genişler.
7. Alarmlar: Koşul VSP → "Sert alış akışı", "Sert satış akışı" ya da "Koşullar düzeldi". Alarmlar yalnızca mum kapanışında tetiklenir. **Not:** TradingView ücretsiz planında gösterge alarmları büyük olasılıkla kullanılamaz; bu durumda uyarılar yalnızca grafikte görünür.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- 22 parite ve 21 aylık testlere göre 1 dakikalık grafikte hiçbir gösterge, maliyeti aşan yön bilgisi vermiyor. VSP de yön söylemez; piyasanın durumunu, hareketin büyüklüğünü ve maliyetle ilişkisini gösterir.
- Tahmini delta, gerçek taker deltasıyla yaklaşık 0,67 korelasyonludur; birebir aynı değildir.
- Zamanlanmış oynaklık çarpanları ortalamadır. ABD veri etkisi, takvimde önemli veri olan günlerde yoğunlaşır; gösterge veri takvimini bilmez.
- Ücretsiz planda 1 dakikalık grafikte yaklaşık 5.000 mum (3,5 gün) yüklenir. Hesapların ilk 1–1,5 günü ısınma dönemidir.
- Grafikteki seviyeler (VWAP, önceki gün, Asya) yalnızca bilgi içindir. Hiçbiri testlerde rastgele seviyelerden daha iyi tutmadı.
- v5.3'te eklenen haftalık pivotun kanıtı, daha sıkı testte tutmadı. Bu yüzden v5.5'te kaldırıldı.
