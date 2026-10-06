# Proje: Vadeli Scalp Pusulası (VSP)

TradingView için 1 dakikalık kripto vadeli işlem göstergesi (Pine Script v6).

- Gösterge kodu: `VSP.pine`
- Tanım ve Talimat kartları: `KARTLAR.md`

## Kullanıcının kalıcı talimatları

- Her zaman Türkçe yanıt ver ve Türkçe imla kurallarına uy.
- Yanıtlar kısa ve öz olsun.
- Gösterge geliştirilirken her seferinde internette derin araştırma yap ve yeni bilgileri göstergeye kat.
- **Kullanıcı strateji değil gösterge istiyor. Nereden alıp satacağına ve stopunu nereye koyacağına kendisi karar verir. Göstergeye AL/SAT sinyali, stop çizgisi, stop önerisi ya da pozisyon büyüklüğü hesabı ekleme; yalnızca piyasayı anlatan bilgi ver.**
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
