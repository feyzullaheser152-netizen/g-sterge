# Proje: Vadeli Scalp Pusulası (VSP)

TradingView için 1 dakikalık kripto vadeli işlem göstergesi (Pine Script v6).

- Gösterge kodu: `VSP.pine`
- Tanım ve Talimat kartları: `KARTLAR.md`

## Kullanıcının kalıcı talimatları

- Her zaman Türkçe yanıt ver ve Türkçe imla kurallarına uy.
- Yanıtlar kısa ve öz olsun.
- Gösterge geliştirilirken her seferinde internette derin araştırma yap ve yeni bilgileri göstergeye kat.
- **AL/SAT sinyali, stop, hedef ve pozisyon büyüklüğü önerisi göstergede yer alır (kullanıcı Ekim 2026'da v5.x'teki "yalnızca bilgi" kuralını kaldırdı ve bunları geri istedi).** Sinyal kuralı yalnızca ön kayıtlı testle değiştirilir; testte net sonuç ne çıktıysa kartlarda açıkça yazılır.
- Kullanıcı başka göstergelerin kodunu gönderdiğinde: daha önce test edilmişse eski sonucu bildir; edilmemişse aynı yöntemle (22 parite, 2025 keşif / 2026 doğrulama, ön kayıt, maliyet dahil) sına; yalnızca geçeni ekle. Lisanslara uy (kaynak ve lisans notu).
- Kullanıcıya seçenek yığını sunma. En doğru çözümü seç, uygula ve kafa karıştırmayacak kadar işlevsel tut.
- Her sohbetin sonunda, Tanım veya Talimat kartında değişiklik olduysa `KARTLAR.md` dosyasını güncelle ve kartların güncel hâlini yanıtta ver.
- Dürüst ol: Net getiri, komisyon ve kayma etkisi ile sonuçların güvenilirliği hakkında abartma.
- Kodu sohbete yapıştırma. Kullanıcıya GitHub'daki dosyanın **Raw** bağlantısını ver (Yol 1: Raw → Ctrl+A → Ctrl+C → Pine Düzenleyici'de Ctrl+A → Ctrl+V).
- **Gösterge hiçbir zaman "bitti" sayılmaz.** Piyasa zamanla değişir; bu değişim gelişme ya da bozulma biçiminde olur. Göstergenin dayandığı her bulgu yeni veriyle düzenli olarak yeniden sınanmalı:
  - Her yeni geliştirme oturumunun başında, son çalıştırma bir aydan eskiyse `python3 arastirma/izleme.py guncelle` ve `python3 arastirma/izleme.py rapor` komutlarını çalıştır. `arastirma/IZLEME.md` dosyasındaki durum tablosunu kullanıcıya kısaca bildir.
  - "ZAYIFLADI" ya da "BOZULDU" çıkan özelliği ön kayıtlı testle yeniden sına. İki ardışık tam ay penceresinde BOZULDU kalırsa göstergeden çıkar.
  - Göstergede olmayan ama izlenen ölçüler eşiği geçerse (ör. LONG kovalama, fonlama), yeni bir özellik adayı olarak test et.

## Kullanıcının ortamı

- TradingView **ücretsiz plan**:
  - 1 dk grafikte yaklaşık 5.000 mum geçmiş var.
  - Saniye verisi yok, bu yüzden gerçek delta kullanılamaz.
  - Gösterge alarmları büyük olasılıkla kullanılamaz.
  - Göstergeyi bu sınırlara göre tasarla.

## Kod kuralları

- Pine Script v6 kullan. Satır kaydırma kullanma; her ifade tek satırda olsun.
- Girintiler 4 boşluk olsun, sekme karakteri kullanma.
- Sinyaller yalnızca mum kapanışında oluşmalı ve repaint yapmamalı.
- Araştırma betikleri ve bulgular `arastirma/` klasöründedir (`BULGULAR.md`). Yeni bir özellik eklemeden önce mümkünse veriyle test et.
- Kodun son satırı `// VSP SONU ...` işareti olarak kalmalı.
- Her değişiklikte koddaki sürüm numarasını artır.
