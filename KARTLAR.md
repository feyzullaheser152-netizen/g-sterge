# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v6.4.2)

**Ne yapar:**
- 1 dakikalık kripto vadeli grafikte **dipten AL, tepeden SAT sinyali**, stop, hedef ve pozisyon büyüklüğü önerir; piyasayı da anlatır.
- Grafikte tablo ya da kutu yoktur. Bilgi dört yoldan verilir: AL/SAT etiketi ve stop/hedef çizgileri, durum satırı, arka plan rengi, seviye çizgileri.
- Sinyal, dip ya da tepe oluştuktan sonra mum kapanışında gelir; geriye dönük değişmez. Dibi önceden bilen (repaint yapmayan) bir gösterge yoktur.
- **Renk kuralı:** Destek niteliğindeki her şey **yeşil**, direnç niteliğindeki her şey **kırmızı**. Çizimler varsayılan olarak **%50 parlaklıkta**.

**AL/SAT (mum kapanışında, geriye dönük değişmez):**

| Etiket | Ne zaman | Beklenti |
|---|---|---|
| **AL** (yeşil, mumun altında) | Dip: son 15 dakikada sert düşüş (z ≤ −3) ve satış akışı; önceki 15 dakikada benzeri yok | Kısa vadeli geri dönüş (yukarı) |
| **SAT** (kırmızı, mumun üstünde) | Tepe: son 15 dakikada sert yükseliş (z ≥ +3) ve alış akışı | Kısa vadeli geri dönüş (aşağı). Testte avantaj yok; izlemede bozuk (aşağıya bakın). Tepeden satış için trend çizgisi SAT oku daha iyi. |

- **Giriş:** Varsayılan piyasa emri, sinyalden sonraki mumun açılışında. Ayarlardan limit emre geçilebilir (limit, fiyat aleyhe giderken dolduğu için brüt sonucu kötüleştirir).
- **Stop:** Girişten 2 × (15 dk oynaklık) uzakta (kırmızı çizgi).
- **Hedef:** Stop mesafesinin 2 katı (yeşil çizgi).
- **Süre:** En fazla 5 dakika; hedef ya da stop gelmezse 5. mumun kapanışında çıkılır.
- **Miktar:** Etiketin altındaki sayı. Stopta kaybedilecek tutar (mesafe + komisyon + kayma), bakiyenizin risk yüzdesi kadar olur. Etiketin üstüne gelince giriş, stop, hedef, pozisyon değeri ve kaldıraç görünür.
- **Sinyal verilmeyen anlar:** Zamanlanmış olay 15 dakika içindeyse ya da sürüyorsa (stop ölçeği o anlarda güvenilmez) ve açık işlem varken. Komisyon ayarları sinyali etkilemez.
- **Veri Penceresi'nde:** Stop, hedef, stop mesafesi %, şimdi girilse önerilen miktar ve pozisyon değeri, grafikteki AL/SAT işlemlerinin sayısı ve ortalama net R'si (maliyet dahil).

**Durum satırı (gösterge adının yanında, soldan sağa):**

| Sıra | Değer | Ne anlatır |
|---|---|---|
| 1 | Hareket / maliyet (kat) | Seçilen ufukta (varsayılan 15 dk) tipik hareketin (%50 dilim), gidiş-dönüş komisyon ve kaymanın kaç katı olduğu. **Yeşil** 2 ve üstü, **sarı** 1–2, **kırmızı** 1'in altı (tipik hareket maliyeti karşılamıyor). |
| 2 | Beklenen hareket ±% (%50) | Fiyatın ufuk sonunda %50 olasılıkla kalacağı aralık. |
| 3 | Beklenen hareket ±% (%80) | Fiyatın ufuk sonunda %80 olasılıkla kalacağı aralık. **Sarı** görünürse aralık olduğundan dardır (aşağıya bakın). |
| 4 | Sıradaki oynaklık anına kalan dk | En yakın zamanlanmış olaya kalan dakika. 15 dk ve altı sarı, olay sırasında mor. |

- **Beklenen hareket sarıysa:** Ufukta 08:30, 09:30, Pazar 18:00 ya da FOMC var, veya NY açılışının ilk 14 dakikası sürüyor. Bu anlarda %80 aralığı gerçekte yalnızca %64–75 kapsar; gerçek hareket daha geniş olabilir.
- Fareyle geçmiş bir mumun üstüne gelince değerler o anı gösterir.
- **Veri Penceresi'nde ek değerler:** Sıradaki FOMC'ye ve CPI/NFP'ye kalan gün (New York takvim günü; olay günü 0), kullanılan kayma %, son 15 dk hareket (z), tahmini delta (%), 1 dk ATR (%).

**Arka plan:**

| Renk | Anlamı |
|---|---|
| Açık mor | Olağandışı oynaklık: zamanlanmış olay, aşırı mumdan (> 4 ATR) sonraki 4 mum ya da iki yönde sert akış. Oynaklık normalin yaklaşık 1,5–2,5 katı (olaya göre daha yüksek olabilir). |
| Koyu mor | FOMC açıklamasının ilk 6 dakikası (normalin yaklaşık 4–7 katı) ve CPI / İstihdam Raporu (NFP) günlerinde 08:30 mumu (normalin yaklaşık 6–11 katı). |
| Turuncu | Sert satış akışının hemen ardındaki mum. Bu mumda SHORT açmak ortalamada dezavantajlı başlar. |

**Zamanlanmış oynaklık anları:**

| Olay | ET | TSİ (ABD yaz / kış saati) | Günler | Arka plan | Oynaklık (normalin katı) |
|---|---|---|---|---|---|
| CPI ya da İstihdam Raporu (NFP) | 08:30 | 15:30 / 16:30 | Listedeki günler | 08:30 koyu mor; 08:30–08:38 açık mor | 08:30'da ×6–11; 08:38'e kadar ×1,6–3,4 |
| Diğer ABD verisi | 08:30 | 15:30 / 16:30 | Diğer Sal–Cum | Yalnızca 08:30 mumu açık mor | ×1,5–2,0 (çoğu gün sakin; ortalamayı PPI gibi veri günleri yükseltir) |
| NY borsa açılışı | 09:30 | 16:30 / 17:30 | Pzt–Cum | 09:30–09:43 açık mor | İlk dakikalar ×1,9–2,2; ilk saat ortalaması ×1,6 |
| ABD verisi | 10:00 | 17:00 / 18:00 | Pzt–Cum | 10:00–10:08 açık mor | ×1,9–2,1 |
| Haftalık vadeli açılışı | Pazar 18:00 | Pazartesi 01:00 / 02:00 | Pazar | 18:00–18:07 açık mor | ×2,4–4,3 |
| FOMC açıklaması | 14:00 | 21:00 / 22:00 | Yalnızca FOMC günleri | 13:59–14:44 açık mor; 14:00–14:05 koyu mor | 14:00'te ×7; ilk 6 dk ×3,9; 14:44'e kadar ×2,4–2,6 (14:30 basın toplantısı dahil) |

- ABD yaz saati Mart'ın ikinci Pazarından Kasım'ın ilk Pazarına kadar sürer. Gösterge bunu otomatik hesaba katar.
- ABD tatilleri (2028 sonuna kadar) ve FOMC tarihleri (2027 sonu, 2028 Ocak) gösterge içinde tanımlıdır.
- **CPI/NFP tarihleri 10 Aralık 2026'ya kadar tanımlıdır.** Sonrasında 08:30 yalnızca açık mor kalır (eski davranış). Resmî 2027 takvimi yayımlanınca liste güncellenecek.

**Çizgiler ve işaretler (destek yeşil, direnç kırmızı):**

| Öğe | Yeşil (destek) | Kırmızı (direnç) | Biçim |
|---|---|---|---|
| VWAP | Fiyatın altında | Fiyatın üstünde | Düz, kalın |
| VWAP ±2σ bantları | Fiyatın altında | Fiyatın üstünde | Kesik, ince |
| SMA20 | Fiyatın altında | Fiyatın üstünde | Düz, ince |
| Önceki gün yüksek / düşük | Fiyatın altında | Fiyatın üstünde | Noktalı, kalın |
| Asya seansı yüksek / düşük | Fiyatın altında | Fiyatın üstünde | Kesik, kalın |
| Trend çizgisi | Yükselen (altta) | Düşen (üstte) | Düz |
| Etiket ve işaretler | AL, pozitif uyumsuzluk, yukarı ok | SAT, negatif uyumsuzluk, aşağı ok | |

- Fiyat bir seviyeyi kırınca rengi kendiliğinden değişir; örneğin kırılan önceki gün yükseği kırmızıdan yeşile döner (direnç desteğe dönüşür).
- **Stop kırmızı, hedef yeşil** kalır ve seviyelerle karışmasın diye noktalı çizilir. Bunlar işlem seviyesidir, destek/direnç değildir; AL işleminde stop altta kırmızı, hedef üstte yeşil görünür.
- **Parlaklık:** Bütün çizimler varsayılan olarak %50 parlaklıkta (Ayarlar → Görünüm → Çizim parlaklığı, %10–100). Arka planlar da aynı oranda soluklaşır. Durum satırındaki sayılar okunabilsin diye tam parlaklıkta; AL/SAT etiketindeki yazı beyaz.
- **SMA20:** Testte mumun SMA20'yi kesmesi (açılış bir yanda, kapanış öbür yanda) iki yılda da küçük ama tutarlı brüt kazanç verdi (+0,2 / +0,2 bp); renk dönüşü bu kesişime yakındır. Bu kazanç VSP AL'ın (+3,8 / +1,4 bp) onda biri kadar; ana sinyal değil. SMA20'nin yön dönüşü (+0,5 / +0,3 bp, iki SMA20 bulgusundan güçlüsü) v6.4.2'den beri gösterilmiyor; izlemede son 12 ayda t ≥ 3 olursa ayrı işaretle geri alınacak. Ayarlar → Görünüm'den kapatılabilir.
- **Uyumsuzluk üçgenleri:** 10 göstergede (MACD, MACD histogram, RSI, Stokastik, CCI, Momentum, OBV, VW-MACD, CMF, MFI) normal uyumsuzluk bulunan ilk mumda; yeşil üçgen mumun altında pozitif, kırmızı üçgen mumun üstünde negatif uyumsuzluk. Testte iki yılda da küçük ama tutarlı brüt kazanç (+0,3 / +0,5 bp). Kazancın tamamı kırmızı üçgende (tepede negatif uyumsuzluk, +1,0 / +0,9 bp); yeşil üçgen ortalamada sıfıra yakın. Uyumsuzluk 5 mumluk pivot onayıyla birkaç mum gecikmeli bilinir; üçgen, bilindiği mumda çizilir. Ayarlar → Görünüm'den kapatılabilir.
- **Trend çizgileri ve kırılım okları (Trend Lines v2):** Son 3 pivottan (20 mum) geçen ve o ana kadar hiçbir kapanışın kırmadığı çizgiler. Yükselen çizgi yeşil, düşen kırmızı; çizgi bir sonraki mumun kırılım seviyesine kadar uzanır. Kapanış yükselen çizginin altına inerse kırmızı **aşağı ok (SAT)**, düşen çizginin üstüne çıkarsa yeşil **yukarı ok (AL)**. Kırılımdan sonra çizgi kaybolur.
  - Testte (piyasa girişi, stop 1σ, hedef 2R, en fazla 30 dk) iki yılda da brüt kazanç: +1,3 / +0,7 bp. 2026'da kazancın tamamı SAT okunda (+1,5 bp). Yani AL etiketinin zayıf kaldığı **tepeden satış** tarafını tamamlar.
  - Parite başına günde yaklaşık 9 AL, 9 SAT oku. AL etiketinden (+3,8 / +1,4 bp) küçük; tek başına işlem değil, yön bilgisi.
  - Canlı mumda çizgi, o mumun kapanışında sınanan seviyeyi gösterir; mum içinde yer değiştirmez.
  - Pivotlar testteki eşitlik kuralıyla hesaplanır (iki eşit tepeden öndeki sayılır, sonraki sayılmaz). TradingView'in yerleşik pivot fonksiyonu eşit tepelerde farklı davranabildiği için, orijinal Trend Lines v2 göstergesiyle birkaç çizgi farklı olabilir. VSP testte ölçülen çizgileri çizer. Uyumsuzluk üçgenleri de aynı kuralı kullanır.
  - Ayarlar → Görünüm'den kapatılabilir.
- Seviye çizgileri (VWAP, önceki gün, Asya) yalnızca bilgi içindir; testlerde hiçbiri rastgele seviyelerden daha iyi tutmadı.

**Maliyet:**
- Kayma en az **yarım tick** alınır. Makas 1 tick'in altına inemez; tick'i kaba, ucuz coinlerde yarım tick 2–4 baz puana çıkabilir. Gösterge grafiğin kendi tick'ini okur.
- Büyük paritelerde (BTC, ETH, SOL) gerçek yarım makas 0,005–0,5 baz puan. Varsayılan %0,01 kayma orada makastan çok gecikme ve emir büyüklüğü payıdır.

**Dayanak (22 Binance vadeli paritesi, 21 ay; 2025 keşif, 2026 doğrulama):**
- **AL/SAT (v6.1, komisyonsuz):**
  - Kullanıcı komisyonu önemsemediği için ayarlar aynı 54 ayar arasından komisyonsuz (brüt) 2025 sonucuyla seçildi: piyasa girişi, stop 2σ, hedef 2R, en fazla 5 dk.
  - Brüt kazanç, işlem başına (2025 / 2026): **AL (dipten alış) +3,8 / +1,4 bp**, SAT (tepeden satış) −0,3 / −0,4 bp. Dipten alış iki yılda da kazandırdı; tepeden satışta belirgin bir avantaj yok.
- **AL/SAT (v6.0, ön kayıtlı test, VIP 0 komisyonla):**
  - 54 ayar arasından yalnızca 2025 verisiyle seçilen ayar (limit giriş, stop 2σ, hedef 2R, 5 dk).
  - İşlem başına net sonuç (VIP 0 komisyon: maker %0,02, taker %0,05, kayma %0,01): 2025'te **−8,5 bp (−0,07 R)**, 2026'da **−9,7 bp (−0,08 R)**. Düşük ücretle (maker %0, taker %0,02) −3,5 / −4,7 bp.
  - Brüt (komisyon öncesi): AL +1,8 / −0,9 bp, SAT −2,5 / −2,5 bp. Piyasa girişinde AL tarafı +1 ile +4 bp brüt kazandırıyor, ama bu maliyetin çok altında.
  - Ön kayıtlı başarı kuralı (iki yılda da net kâr ve istatistiksel güven) geçilmedi. 54 ayarın hiçbiri iki yılda da net pozitif değil.
  - Yani her 100 işlemde, işlem başına %0,5 risk alan bir hesap ortalama yaklaşık **%3,5–4** kaybeder (gerçek sonuç bu ortalamanın çevresinde dağılır).
- **Gönderilen topluluk göstergeleri, katkı testi (sinyal, filtre, bilgi; komisyonsuz):** Birinci grupta 11 sinyal adayından yalnızca CM Ultimate MA'nın SMA20 sinyalleri geçti (SMA20 çizgisi olarak eklendi). 31 durumun hiçbiri VSP AL/SAT'ı tutarlı biçimde iyileştirmedi ya da oynaklık tahminine katkı vermedi. İkinci grupta (11 gösterge; sinyal, filtre, oynaklık, yön, seviye ve çıkış katmanları) yalnızca Divergence for Many Indicators geçti (uyumsuzluk üçgenleri olarak eklendi). İzleyen stopların (Supertrend, UT Bot, SuperTrend AI vb.) hiçbiri VSP'nin 5 dakikalık çıkışından iyi değil. Üçüncü grupta (14 gösterge; 12 katman: sinyal, filtre, oynaklık, yön, seviye, çıkış, stop yerleşimi, giriş zamanlaması, uyum, coin seçimi, saat/gün, BTC bağlamı) yalnızca Trend Lines v2'nin çizgi kırılımı geçti (trend çizgileri ve oklar olarak eklendi). Stop yerleşimi, giriş zamanlaması, coin ya da saat seçimi ve BTC teyidi VSP AL/SAT'ı iyileştirmedi; en yakın aday "son 10 mumun dibinin altına stop" (iki yılda biraz iyi, ama güven eşiğinin altında; izleniyor). Literatürden alınan dört filtre adayı da (olay hacmi, BTC gecikmeli teyit, Abdi-Ranaldo makası) geçmedi. Ayrıntı: `arastirma/BULGULAR.md` bölüm 15–17.
- **Gönderilen 13 topluluk göstergesi** (Supertrend, UT Bot, CM MACD, WaveTrend, Squeeze Momentum, Williams Vix Fix, ADX/DI, LuxAlgo S/R Breaks ve Trendlines, MSB-OB, SR Channels, ChartPrime HV Boxes, TFO Killzones) aynı motorla sınandı. Hepsi işlem başına 8–13 bp net zarar verdi; brüt yön bilgisi 1 bp'nin altında. VSP'ye eklenmedi. LuxAlgo SMC daha önce test edilmişti; Sessions [LuxAlgo] sinyal içermiyor.
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
- **Olağandışı oynaklık (açık ve koyu mor):**
  - Zamanlanmış olaylar yukarıdaki tablodaki gibi.
  - CPI/NFP günleri 08:30'daki fazlalığın yarısından çoğunu taşır; ancak 2026'da bu günlerin yaklaşık %17'si sakin geçti. Koyu mor tipik durumu gösterir, her seferinde olacağı garanti değil.
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
  - Hiçbiri 1 dakikalık grafikte maliyeti aşan ya da tutarlı bilgi vermedi. Ayrıntı: `arastirma/BULGULAR.md`, bölüm 6–14.
- **Sürekli izleme:** Her bulgu ay ay yeniden ölçülür (`arastirma/IZLEME.md`). Ekim 2026 itibarıyla (son 12 tam ay, 2025-10 – 2026-09):
  - Oynaklık, beklenen hareket ve turuncu uyarı: "TUTUYOR".
  - Trend çizgisi kırılımı: "TUTUYOR" (+0,8 bp, t 2,7). SAT oku +1,4 bp (t 3,1).
  - AL etiketi: "ZAYIFLADI". Hâlâ pozitif (+2,1 bp), ama son 12 ayda istatistiksel güven düşük (t 1,3).
  - SMA20 kesişimi (renk dönüşü) ve uyumsuzluk: "ZAYIFLADI" (+0,1 / +0,3 bp, t 1,0–1,3). SMA20 yön dönüşü görünümde yok, izleniyor (+0,3 bp, t 1,5).
  - **SAT etiketi: "BOZULDU"** (0,0 bp; bir önceki pencerede "ZAYIFLADI"). Kurala göre Kasım 2026 kontrolünde de bozuk çıkarsa göstergeden kaldırılacak. Tepeden satış için trend çizgisi SAT okunu kullanın.

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Gösterge yalnızca **1 dakikalık** grafikte çalışır; başka zaman diliminde hata mesajı verir.
4. Ayarlar → **AL/SAT, stop ve pozisyon** bölümünde hesap bakiyenizi (USDT) ve işlem başına risk yüzdesini girin.
   - Etiketteki miktar bu iki değerden hesaplanır: stop gelirse kaybınız, maliyet dahil, bakiye × risk % olur.
   - Stop (oynaklığın katı), hedef (R) ve en uzun tutma süresi de buradan değiştirilebilir. Varsayılanlar testte seçilen değerlerdir; değiştirirseniz kartlardaki test sonuçları geçerli olmaz.
   - Sinyalleri bu bölümdeki **AL/SAT sinyalleri** kutusundan kapatabilirsiniz.
5. Ayarlar → **Maliyet** bölümünde borsanızın maker ve taker komisyonlarını, kaymayı ve girişte kullandığınız emir tipini girin.
   - Bu bilgiler "Hareket / maliyet" değerinde, miktar hesabında ve grafikteki işlemlerin net sonucunda kullanılır.
   - Girdiğiniz kayma yarım tick'ten küçükse gösterge yarım tick'i kullanır. Kullanılan değeri Veri Penceresi'nde görebilirsiniz.
6. Ayarlar → **Piyasa koşulu** bölümünde beklenen hareket ufkunu seçin (varsayılan 15 dk). 1 dk seçilirse hareket neredeyse her zaman maliyetin altında görünür.
7. **AL/SAT etiketi:** Mum kapandığında çıkar. Etiketin üstüne gelin; giriş, stop, hedef, miktar, pozisyon değeri ve kaldıraç görünür. Stop ve hedef çizgileri işlem bitene kadar grafikte kalır.
8. **Durum satırı:** Gösterge adının yanındaki dört sayıyı okuyun.
   - Beklenen hareket sayıları **sarıysa** yakında ya da şu anda zamanlanmış bir olay var; gerçek hareket gösterilenden geniş olabilir.
   - Sayılar görünmüyorsa: Grafik ayarları → **Durum satırı** → **Gösterge değerleri** kutusunu işaretleyin.
   - Ek değerler için sağ kenar çubuğundaki **Veri Penceresi**'ni açın.
9. **Arka plan:**
   - Açık mor: Oynaklık olağandışı; fiyat normalden sert oynar.
   - Koyu mor: FOMC'nin ilk dakikaları ya da CPI/NFP günü 08:30 mumu (en sert anlar).
   - Turuncu: O mumda SHORT kovalamak ortalamada dezavantajlı başlar.
   - Arka planlar Ayarlar → **Görünüm** bölümünden kapatılabilir.
10. **Renk ve parlaklık:** Destek yeşil, direnç kırmızı; çizimler varsayılan olarak %50 parlaklıkta. Parlaklığı Ayarlar → **Görünüm** → **Çizim parlaklığı** ile değiştirebilirsiniz. Tek tek çizgileri Ayarlar → **Stil** sekmesinden değiştirmeyin; renkler fiyatın konumuna göre otomatik değişir.
11. **Alarmlar:**
   - Koşul VSP → "AL", "SAT", "Trend çizgisi kırılımı AL", "Trend çizgisi kırılımı SAT", "Sert satış akışı" ya da "Olağandışı oynaklık".
   - Alarmlar yalnızca mum kapanışında tetiklenir.
   - **Not:** TradingView ücretsiz planında gösterge alarmları büyük olasılıkla kullanılamaz.
12. **Zaman aşımı:** TradingView "hesaplama çok uzun sürdü" benzeri bir hata verirse Ayarlar → **Görünüm** bölümünden önce trend çizgilerini, gerekirse uyumsuzluk işaretlerini kapatın. Kapatılan katmanın hesabı da durur (o katmanın alarmı da çalışmaz).
13. **Güncelleme:** CPI/NFP tarih listesi 10 Aralık 2026'da biter. Yeni sürüm çıktığında 1. adımı tekrarlayın.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- AL/SAT komisyonsuz ölçüldüğünde dipten alış (AL) iki yılda da brüt kazandırdı (+3,8 / +1,4 bp); SAT etiketinde avantaj yok. Tepeden satış için en iyi bulunan, trend çizgisi kırılımının SAT okudur (+1,2 / +1,5 bp). Komisyon ödeniyorsa (VIP 0'da gidiş-dönüş 8–12 bp) bunların hepsi net zarara döner.
- SMA20, uyumsuzluk ve trend çizgisi işaretlerinin kazancı işlem başına 1 bp civarında ya da altında. Tutarlı ama küçük; tek tek işlemde rastlantı baskındır.
- 22 parite ve 21 aylık testlere göre, test edilen hiçbir gösterge (48 yerleşik gösterge, LuxAlgo SMC ve gönderilen 13 topluluk göstergesi dahil) 1 dakikalık grafikte maliyeti aşan yön bilgisi vermiyor.
- Veri Penceresi'ndeki "grafikteki işlemlerin ortalama net R'si" yalnızca grafikte yüklü yaklaşık 3,5 günü kapsar (birkaç düzine işlem). Bu kadar az işlemle sonuç çok oynaktır; birkaç günlük kâr ya da zarar kartlardaki uzun dönem sonucunu değiştirmez.
- Gösterge sinyallerin işlem sonucunu mum verisiyle (yüksek/düşük) hesaplar. Aynı mumda stop ve hedef birlikte değmişse önce stop sayılır. Gerçek dolum, makas ve kayma farklı olabilir.
- Turuncu uyarının etkisi küçüktür ve maliyetin (8–12 baz puan) altındadır. Bir işlem fırsatı değil, "o mumda girersen ortalamada geride başlarsın" bilgisidir.
- Tahmini delta, gerçek taker deltasıyla yaklaşık 0,67 korelasyonludur; birebir aynı değildir.
- Oynaklık çarpanları ortalamadır. Gösterge yalnızca CPI ve NFP tarihlerini bilir; PPI, GSYH gibi diğer 08:30 verilerini ayırt etmez.
- Makas ölçümleri Binance verisinden ve Mart 2024'teki gerçek kotasyonlardandır; OKX doğrudan ölçülemedi. Büyük paritelerde makas maliyeti ihmal edilebilir, maliyetin büyük kısmı komisyondur. Olay anlarında asıl risk makas değil, oynaklıktır.
- Ücretsiz planda 1 dakikalık grafikte yaklaşık 5.000 mum (3,5 gün) yüklenir. Hesapların ilk 1–1,5 günü ısınma dönemidir.
