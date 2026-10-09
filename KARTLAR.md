# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v5.7)

**Ne yapar:**
- 1 dakikalık kripto vadeli grafikte **piyasayı anlatır**.
- AL/SAT sinyali, stop ya da pozisyon önerisi vermez. Nereden alıp satacağınıza ve stopunuza siz karar verirsiniz.
- Grafikte tablo ya da kutu yoktur. Bilgi üç yoldan verilir: durum satırı, arka plan rengi ve çizgiler.

**Durum satırı (gösterge adının yanında, soldan sağa):**

| Sıra | Değer | Ne anlatır |
|---|---|---|
| 1 | Hareket / maliyet (kat) | Seçilen ufukta (varsayılan 15 dk) tipik hareketin (%50 dilim), gidiş-dönüş komisyon ve kaymanın kaç katı olduğu. **Yeşil** 2 ve üstü, **sarı** 1–2, **kırmızı** 1'in altı (tipik hareket maliyeti karşılamıyor). |
| 2 | Beklenen hareket ±% (%50) | Fiyatın ufuk sonunda %50 olasılıkla kalacağı aralık. |
| 3 | Beklenen hareket ±% (%80) | Fiyatın ufuk sonunda %80 olasılıkla kalacağı aralık. **Sarı** görünürse aralık olduğundan dardır (aşağıya bakın). |
| 4 | Sıradaki oynaklık anına kalan dk | En yakın zamanlanmış olaya kalan dakika. 15 dk ve altı sarı, olay sırasında mor. |

- **Beklenen hareket sarıysa:** Ufukta 08:30, 09:30, Pazar 18:00 ya da FOMC var, veya NY açılışının ilk 14 dakikası sürüyor. Bu anlarda %80 aralığı gerçekte yalnızca %64–75 kapsar; gerçek hareket daha geniş olabilir.
- Fareyle geçmiş bir mumun üstüne gelince değerler o anı gösterir.
- **Veri Penceresi'nde ek değerler:** Sıradaki FOMC'ye kalan gün, sıradaki CPI/NFP'ye kalan gün, kullanılan kayma %, son 15 dk hareket (z), tahmini delta (%), 1 dk ATR (%).

**Arka plan:**

| Renk | Anlamı |
|---|---|
| Mor | Olağandışı oynaklık: zamanlanmış olay, aşırı mumdan (> 4 ATR) sonraki 4 mum ya da iki yönde sert akış. Oynaklık normalin yaklaşık 1,5–2,5 katı (olaya göre daha yüksek olabilir). |
| Kırmızı | FOMC açıklamasının ilk 6 dakikası (normalin yaklaşık 4–7 katı) ve CPI / İstihdam Raporu (NFP) günlerinde 08:30 mumu (normalin yaklaşık 6–11 katı). |
| Turuncu | Sert satış akışının hemen ardındaki mum. Bu mumda SHORT açmak ortalamada dezavantajlı başlar. |

**Zamanlanmış oynaklık anları:**

| Olay | ET | TSİ (ABD yaz / kış saati) | Günler | Arka plan | Oynaklık (normalin katı) |
|---|---|---|---|---|---|
| CPI ya da İstihdam Raporu (NFP) | 08:30 | 15:30 / 16:30 | Listedeki günler | 08:30 kırmızı; 08:30–08:38 mor | 08:30'da ×6–11; 08:38'e kadar ×1,6–3,4 |
| Diğer ABD verisi | 08:30 | 15:30 / 16:30 | Diğer Sal–Cum | Yalnızca 08:30 mumu mor | ×1,5–2,0 (çoğu gün sakin; ortalamayı PPI gibi veri günleri yükseltir) |
| NY borsa açılışı | 09:30 | 16:30 / 17:30 | Pzt–Cum | 09:30–09:43 mor | İlk dakikalar ×1,9–2,2; ilk saat ortalaması ×1,6 |
| ABD verisi | 10:00 | 17:00 / 18:00 | Pzt–Cum | 10:00–10:08 mor | ×1,9–2,1 |
| Haftalık vadeli açılışı | Pazar 18:00 | Pazartesi 01:00 / 02:00 | Pazar | 18:00–18:07 mor | ×2,4–4,3 |
| FOMC açıklaması | 14:00 | 21:00 / 22:00 | Yalnızca FOMC günleri | 13:59–14:44 mor; 14:00–14:05 kırmızı | 14:00'te ×7; ilk 6 dk ×3,9; 14:44'e kadar ×2,4–2,6 (14:30 basın toplantısı dahil) |

- ABD yaz saati Mart'ın ikinci Pazarından Kasım'ın ilk Pazarına kadar sürer. Gösterge bunu otomatik hesaba katar.
- ABD tatilleri (2028 sonuna kadar) ve FOMC tarihleri (2027 sonu, 2028 Ocak) gösterge içinde tanımlıdır.
- **CPI/NFP tarihleri 10 Aralık 2026'ya kadar tanımlıdır.** Sonrasında 08:30 yalnızca mor kalır (eski davranış). Resmî 2027 takvimi yayımlanınca liste güncellenecek.

**Çizgiler (en kalın, açık renk):**
- VWAP (sarı, düz) ve ±2σ bantları (açık sarı, kesik).
- Önceki gün yüksek/düşük (beyaz, noktalı).
- Asya seansı yüksek/düşük (açık mor, kesik).
- Bu çizgiler yalnızca bilgi içindir; testlerde hiçbiri rastgele seviyelerden daha iyi tutmadı.

**Maliyet:**
- Kayma en az **yarım tick** alınır. Makas 1 tick'in altına inemez; tick'i kaba, ucuz coinlerde yarım tick 2–4 baz puana çıkabilir. Gösterge grafiğin kendi tick'ini okur.
- Büyük paritelerde (BTC, ETH, SOL) gerçek yarım makas 0,005–0,5 baz puan. Varsayılan %0,01 kayma orada makastan çok gecikme ve emir büyüklüğü payıdır.

**Dayanak (22 Binance vadeli paritesi, 21 ay; 2025 keşif, 2026 doğrulama):**
- **Beklenen hareket:**
  - 15 dakikalık gerçek hareketlerin %50'si öngörülen oynaklığın 0,61 katı içinde kalır, %80'i 1,23 katı içinde.
  - Bu katsayılar 1–240 dk ufukların hepsinde %10'dan az sapar.
  - Sınırlar:
    - Piyasa birden sakinleştiğinde aralık biraz dar kalır (%80 yerine %73). Birden hızlandığında biraz geniş kalır (%87).
    - Zamanlanmış olay ufuktayken aralık dar kalır; bu anlar sarı gösterilir. Olay etkisini modele katma denemesi iki yılda da tutmadı.
    - Kalibrasyon 22 büyük paritede doğrulandı. 20 orta paritede %80 aralığı %77–90 kapsıyor, yani çoğunlukla biraz geniş.
- **Sert satış sonrası (turuncu):**
  - Sert satış akışının ilk mumu kapandıktan sonra SHORT açan, 5 dakika içinde ortalama 3,3–5,3 baz puan geride kalır (paritelerin %95–100'ünde). 15 dakikada 3,4–5,7 baz puan (paritelerin %86–91'inde), ancak bu ufukta istatistiksel olarak zayıf.
  - Etki bir mum sonra kaybolur.
  - Sert alıştan sonra LONG için böyle bir etki yok; bu yüzden o uyarı kaldırıldı.
- **Olağandışı oynaklık (mor ve kırmızı):**
  - Zamanlanmış olaylar yukarıdaki tablodaki gibi.
  - CPI/NFP günleri 08:30'daki fazlalığın yarısından çoğunu taşır; ancak 2026'da bu günlerin yaklaşık %17'si sakin geçti. Kırmızı tipik durumu gösterir, her seferinde olacağı garanti değil.
  - Aşırı mumdan sonraki 4 mum ×1,5–2,6 (mum mum azalarak).
  - İki yönde sert akış ×2,1.
- **v5.6'da veriyle sınanıp kaldırılanlar:**
  - **Fonlama saati:** Oynaklık ×1,0. Ortalama fonlama ödemesi 0,7–0,8 baz puan.
  - **Likidite (kayma çarpanı):** Gelecekteki fiyat etkisini öngörmüyor. "İnce" görünen anlar aslında daha sakin.
  - **Bağlam satırı:** Trend göstergeleri yön bilgisi vermiyor.
  - **LONG kovalama uyarısı:** Desteklenmiyor.
- **Test edilip eklenmeyenler:**
  - TradingView'in 48 yerleşik göstergesi ve LuxAlgo Smart Money Concepts (BOS, CHoCH, Order Block, FVG, EQH/EQL).
  - Seviyeler: haftalık/aylık/günlük pivotlar, önceki hafta ve ay uçları, Fibonacci, Volume Profile.
  - Mum formasyonları (12 tür).
  - OI, baz/prim, piyasa genişliği ve dominans.
  - "Coine özel / piyasa geneli" ayrımı.
  - v5.7: Mumlardan makas tahmini (EDGE; büyük paritelerde makası 10–14 kat fazla gösteriyor), olay anında makas çarpanı (gerçek makas olay anlarında çoğunlukla yalnızca ×1,0–1,1 açılıyor), Deribit Cuma vadesi (×0,9–1,3), başabaş ufku (hareket / maliyetle aynı bilgi).
  - Hiçbiri 1 dakikalık grafikte maliyeti aşan ya da tutarlı bilgi vermedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 6–13.
- **Sürekli izleme:** Her bulgu ay ay yeniden ölçülür (`arastirma/IZLEME.md`). Ekim 2026 itibarıyla göstergedeki tüm özellikler "TUTUYOR".

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Gösterge yalnızca **1 dakikalık** grafikte çalışır; başka zaman diliminde hata mesajı verir.
4. Ayarlar → **Maliyet** bölümünde borsanızın maker ve taker komisyonlarını, kaymayı ve girişte kullandığınız emir tipini girin.
   - Bu bilgiler yalnızca "Hareket / maliyet" değeri için kullanılır.
   - Girdiğiniz kayma yarım tick'ten küçükse gösterge yarım tick'i kullanır. Kullanılan değeri Veri Penceresi'nde görebilirsiniz.
5. Ayarlar → **Piyasa koşulu** bölümünde beklenen hareket ufkunu seçin (varsayılan 15 dk). 1 dk seçilirse hareket neredeyse her zaman maliyetin altında görünür.
6. **Durum satırı:** Gösterge adının yanındaki dört sayıyı okuyun.
   - Beklenen hareket sayıları **sarıysa** yakında ya da şu anda zamanlanmış bir olay var; gerçek hareket gösterilenden geniş olabilir.
   - Sayılar görünmüyorsa: Grafik ayarları → **Durum satırı** → **Gösterge değerleri** kutusunu işaretleyin.
   - Ek değerler için sağ kenar çubuğundaki **Veri Penceresi**'ni açın.
7. **Arka plan:**
   - Mor: Oynaklık olağandışı; fiyat normalden sert oynar.
   - Kırmızı: FOMC'nin ilk dakikaları ya da CPI/NFP günü 08:30 mumu.
   - Turuncu: O mumda SHORT kovalamak ortalamada dezavantajlı başlar.
   - Arka planlar Ayarlar → **Görünüm** bölümünden kapatılabilir.
8. **Stil:** Çizgiler varsayılan olarak en kalın ve açık renklidir. Ayarlar → **Stil** sekmesinden değiştirebilirsiniz.
9. **Alarmlar:**
   - Koşul VSP → "Sert satış akışı" ya da "Olağandışı oynaklık".
   - Alarmlar yalnızca mum kapanışında tetiklenir.
   - **Not:** TradingView ücretsiz planında gösterge alarmları büyük olasılıkla kullanılamaz.
10. **Güncelleme:** CPI/NFP tarih listesi 10 Aralık 2026'da biter. Yeni sürüm çıktığında 1. adımı tekrarlayın.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- 22 parite ve 21 aylık testlere göre, test edilen hiçbir gösterge 1 dakikalık grafikte maliyeti aşan yön bilgisi vermiyor. VSP de yön söylemez; hareketin büyüklüğünü, maliyetle ilişkisini ve olağandışı anları gösterir.
- Turuncu uyarının etkisi küçüktür ve maliyetin (8–12 baz puan) altındadır. Bir işlem fırsatı değil, "o mumda girersen ortalamada geride başlarsın" bilgisidir.
- Tahmini delta, gerçek taker deltasıyla yaklaşık 0,67 korelasyonludur; birebir aynı değildir.
- Oynaklık çarpanları ortalamadır. Gösterge yalnızca CPI ve NFP tarihlerini bilir; PPI, GSYH gibi diğer 08:30 verilerini ayırt etmez.
- Makas ölçümleri Binance verisinden ve Mart 2024'teki gerçek kotasyonlardandır; OKX doğrudan ölçülemedi. Büyük paritelerde makas maliyeti ihmal edilebilir, maliyetin büyük kısmı komisyondur. Olay anlarında asıl risk makas değil, oynaklıktır.
- Ücretsiz planda 1 dakikalık grafikte yaklaşık 5.000 mum (3,5 gün) yüklenir. Hesapların ilk 1–1,5 günü ısınma dönemidir.
