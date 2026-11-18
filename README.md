# OZA BİLGİ – Otomatik Instagram Bilgi Kartı Sistemi

Bu sistem Bakü saatiyle her 3 saatte bir (08:00, 11:00, 14:00, 17:00, 20:00; günde 5 kez) çalışır ve şunları yapar:

1. **Uzay, Tarih, Bilim, Doğa, İnsan, Dünya** konularından sıradakini seçer.
2. Claude ile eğlenceli, önemli ve doğru bir "Biliyor muydunuz?" bilgisi yazar; daha önce paylaşılanları tekrar etmez.
3. OZA BİLGİ şablonuyla kartı üretir.
4. Kartı @oza_bilgi hesabında paylaşır.

## Kurulum
Kurulum adımları sohbette anlatıldı. Kısaca:

1. Instagram'da İşletme hesabı açın.
2. Meta'da bir uygulama ve bir işletme portföyü oluşturun.
3. İşletme ayarlarında bir sistem kullanıcısı açın ve süresiz bir anahtar (token) alın.
4. Claude API anahtarı alın.
5. Herkese açık (Public) bir GitHub deposu açın ve bu dosyaları yükleyin.
6. Secrets bölümüne iki değer ekleyin: `ANTHROPIC_API_KEY` ve `IG_ACCESS_TOKEN`.
7. Actions sekmesinden "Instagram bağlantı testi"ni çalıştırın.
8. `DRY_RUN` = `1` değişkeniyle deneme yapın; her şey yolundaysa bu değişkeni silin.

## Ayarlar (`ayarlar.py`)
- `KULLANICI_ADI`: Görselin altında görünen Instagram adı.
- `SIRA`: Kategorilerin paylaşım sırası.
- `KATEGORILER`: Konu renkleri, konu tarifleri ve hashtag'ler.
- Paylaşım saatleri `.github/workflows/paylas.yml` dosyasındaki `cron` satırındadır. Saatler UTC'dir; Bakü saati UTC+4'tür.

## Bakım
- Haftada bir hesaba göz atın.
- GitHub'da Actions sekmesinde kırmızı çarpı görürseniz hatanın ayrıntısına bakın.

## Sorumluluk
Paylaşılan içeriklerden hesap sahibi sorumludur. Sistem yalnızca doğrulanabilir bilgiler yazmaya ve hassas konulardan kaçınmaya ayarlıdır, yine de düzenli kontrol önerilir.
