# Vadeli Scalp Pusulası (VSP) — Kartlar

## Tanım Kartı (v5.1)

**Ne yapar:** 1 dakikalık kripto vadeli grafikte işlem kararını **siz verirsiniz**. Gösterge AL/SAT sinyali vermez. Karar anında size şu beş soruda bilgi verir:
1. **Bu işlem komisyonu çıkarabilir mi?** Maliyetin riskinize oranını hesaplar.
2. **Piyasa şu an uygun mu?** Fonlama saatini, aşırı mumu ve ince likiditeyi gösterir.
3. **Hangi yön kovalanmamalı?** Sert akış uyarısı verir.
4. **Kaç birim açmalıyım, stop nerede?** Pozisyon büyüklüğünü ve stop seviyesini hesaplar.
5. **Fiyat ne kadar oynar, stopum gürültüyle vurulur mu, kaç isabet gerekir?** Beklenen hareketi, stopun vurulma olasılığını ve başa baş isabet oranını gösterir.

**Panel satırları:**

| Satır | Ne gösterir |
|---|---|
| DURUM | Yeşil: "Koşullar uygun". Sarı: "DİKKAT: maliyet yüksek / likidite ince". Kırmızı: "İŞLEM AÇMAYIN" ve sebebi (fonlama saati, aşırı mum, çok yüksek maliyet, yanlış zaman dilimi, hacim verisi yok). |
| Maliyet / risk (L / S) | Long ve short stop mesafesinde komisyon ve kaymanın riskin kaçta kaçı olduğu. Ayarlardaki sınırın (0,20R) altı yeşil, iki katına kadar sarı, üstü kırmızı. |
| Fonlama | Bir sonraki fonlamaya kalan süre. ±3 dakika içinde "bekleyin". |
| Oynaklık (1 dk ATR) | 1 dakikalık ortalama hareket (%). Mum boyu 4 ATR'yi aşarsa 5 mum "aşırı mum, bekleyin". |
| Likidite (kayma çarpanı) | Amihud ölçüsüne göre piyasa ince mi; kayma kaç kat artmış. |
| Son 15 dk akış | Tahmini delta (%) ve hareketin z-skoru. Sert alış akışıyla yükselişten sonra 15 mum "LONG kovalamayın", sert satış akışıyla düşüşten sonra "SHORT kovalamayın". |
| Bağlam (bilgi, sinyal değil) | 15 dakikalık trend yönü ve fiyatın VWAP'a göre konumu. |
| LONG / SHORT: stop / miktar | Stop fiyatı ve açılacak miktar (coin adedi). |
| LONG / SHORT: büyüklük / kaldıraç | Pozisyon büyüklüğü (USDT) ve gereken en düşük kaldıraç. |
| Stopta kayıp | Stop olursa komisyon dahil kaybedilecek tutar. |
| Beklenen hareket (N dk) | Planlanan tutma süresinde fiyatın %50 ve %80 olasılıkla kalacağı aralık (±%). |
| Stop gürültüyle vurulur mu (N dk) | Long ve short stopun, yön tahmini olmadan, yalnızca sıradan oynaklıkla bu sürede vurulma olasılığı. %25'in altı yeşil, %25–50 sarı, %50 ve üstü kırmızı. |
| Başa baş isabet (hedef xR) | Bu stop, hedef ve komisyonla zarar etmemek için kazanmanız gereken işlem oranı. Parantezdeki "rastgele" değer, kenarsız bir girişin hedefi stoptan önce görme oranıdır. Aradaki fark, seçiminizin rastgeleden ne kadar iyi olması gerektiğini gösterir. |

**Grafikte:**
- VWAP ve ±2σ bantları.
- Önceki gün yüksek/düşük (gri).
- Asya seansı yüksek/düşük (mor).
- Long ve short stop çizgileri (kesikli).
- Beklenen hareket kutusu (mavi): Planlanan süre boyunca fiyatın %80 olasılıkla kalacağı aralık.
- Kovalama uyarısı sırasında turuncu arka plan.

**Pozisyon hesabı:**
- Miktar = (bakiye × risk %) ÷ (giriş ile stop arası fark + giriş ve çıkış komisyonu).
- Böylece stop olursa komisyon dahil tam olarak ayarladığınız tutarı kaybedersiniz.

**Oynaklık hesaplarının dayanağı (22 Binance paritesi, 21 ay):**
- **Beklenen hareket:** 1 dakikalık getirilerin 30 mumluk üstel ortalama varyansından hesaplanır.
  - Gerçek 15 dakikalık hareketlerin %50'si öngörülen oynaklığın 0,61 katı içinde kalır, %80'i 1,23 katı içinde.
  - Bu oranlar 2025 ve 2026'da neredeyse aynıdır.
- **Stopun vurulma olasılığı:**
  - Klasik formül yerine gerçek veriden çıkan tablo kullanılır. Uzak stoplar kalın kuyruklar nedeniyle formülün öngördüğünden 2–4 kat daha sık vurulur.
  - Tablo 5, 15 ve 30 dakikada ve bütün paritelerde tutarlıdır.

**Kovalama uyarısının kanıtı:** 22 Binance vadeli paritesi, 21 ay:
- Saldırgan akışla gelen sert 15 dakikalık hareketten sonra fiyat 5–15 dakika içinde ortalama 1,4–4,7 baz puan geri dönüyor. Paritelerin %77–95'inde, iki yılda da tutuyor.
- O yönde yeni giren biri ortalamada bu kadar dezavantajla başlar.

## Talimat Kartı

1. Kodu almak için GitHub'da dosyanın **Raw** sayfasını açın. **Ctrl+A** ve **Ctrl+C** ile kopyalayın. Pine Düzenleyici'de **Ctrl+A** ve **Ctrl+V** ile yapıştırın. Son satırda `// VSP SONU` yazısını görmelisiniz.
2. **Kaydet**'e, ardından **Grafiğe ekle**'ye basın. Gösterge alt bölmede açılırsa sağ tıklayıp **Taşı (Move to) → Yukarıdaki mevcut bölme (Existing pane above)** seçeneğini kullanın.
3. Ayarlar → **Hesap ve risk** bölümünde şunları girin:
   - Hesap bakiyeniz (USDT) ve işlem başına risk yüzdeniz (öneri: %0,5 – %1).
   - Stop yöntemi: Son mumların dibi/tepesi ya da ATR katı.
   - Planlanan hedefiniz (R, ör. 1,5) ve planlanan tutma süreniz (dakika, ör. 15).
4. Ayarlar → **Emir ve maliyet** bölümünde şunları girin:
   - Borsanızın maker ve taker komisyonları.
   - Girişte limit mi piyasa emri mi kullandığınız.
5. Ayarlar → **Piyasa koşulu** bölümünde paritenizin fonlama aralığını seçin (8, 4 ya da 1 saat).
6. **İşlem açmadan önce:**
   - DURUM kırmızıysa açmayın.
   - Sarıysa sebebini okuyun.
   - "Son 15 dk akış" satırı bir yönü kovalamamanızı söylüyorsa o yönde girmeyin.
7. Girişe karar verdiğinizde paneldeki **miktarı** ve **stop fiyatını** kullanın. Kendi stop seviyenizi kullanacaksanız, ATR katını o mesafeye göre ayarlayın.
8. **Stop ve hedef kontrolü:**
   - "Stop gürültüyle vurulur mu" satırı kırmızıysa stopunuz çok dar; sıradan oynaklık bile onu vurabilir.
   - "Başa baş isabet" rastgele değerden çok yüksekse, bu işlemin kâr etmesi için girişinizin rastgeleden belirgin şekilde iyi olması gerekir.
9. Alarmlar: Koşul VSP → "Sert alış akışı", "Sert satış akışı" ya da "Koşullar düzeldi".

## Test Kanıtı

Ayrıntılar: `arastirma/BULGULAR.md`.
- **BTC spot verisi:** 21 ay, 917 bin mum.
- **Binance vadeli verisi:** 22 parite, 21 ay, yaklaşık 20 milyon mum, gerçek taker delta, fonlama, OI ve long/short oranı.
- **Bulgu:** Test edilen hiçbir 1 dakikalık yön kalıbı, en düşük komisyonla (maker %0 / taker %0,02) bile iki yılda tutarlı net kâr üretmedi.
- **Tutarlı tek etki:** Akış sonrası kısa dönüş (1–3 baz puan). Gösterge bu etkiyi yalnızca "kovalamayın" uyarısı olarak kullanır.
- AL/SAT sinyalleri bu yüzden kaldırıldı. Kararı siz verirsiniz; gösterge kaçınılabilir maliyetleri ve hataları azaltmak için bilgi verir.

## Dürüst Not

- Hiçbir gösterge kâr garantisi vermez.
- Testlere göre 1 dakikalık işlemde net sonucu en çok komisyon, kayma ve pozisyon büyüklüğü belirler. Bu panel tam olarak bu üçünü yönetmenize yardım eder.
- Tahmini delta, gerçek taker deltasıyla yaklaşık 0,67 korelasyonludur; bire bir aynı değildir.
