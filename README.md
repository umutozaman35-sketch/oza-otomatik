# OZA MEDYA – Otomatik Instagram Haber Sistemi

Bu sistem Bakü saatiyle 08:00–22:00 arasında her 2 saatte bir (günde 8 kez) çalışır ve şunları yapar:

1. **Gündem, Spor, Dizi ve Magazin** kategorilerinden sırayla bir haber seçer; bu dört kategori dışında hiçbir şey paylaşılmaz.
2. Claude ile haberin metnini kısa ve özgün bir şekilde yeniden yazar; söylenti ve suçlama içeren riskli haberleri atlar.
3. OZA MEDYA şablonuyla görseli üretir.
4. Görseli kaynak adıyla birlikte Instagram'da paylaşır.

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
- `KATEGORILER`: Kategori renkleri, haber kaynakları ve hashtag'ler.
- Paylaşım saatleri `.github/workflows/paylas.yml` dosyasındaki `cron` satırındadır. Saatler UTC'dir; Bakü saati UTC+4'tür.

## Bakım
- Haftada bir hesaba göz atın.
- GitHub'da Actions sekmesinde kırmızı çarpı görürseniz hatanın ayrıntısına bakın.

## Sorumluluk
Paylaşılan içeriklerden hesap sahibi sorumludur. Sistem riskli haberleri atlamaya ve yalnızca kaynakta geçen bilgileri kullanmaya ayarlıdır, yine de düzenli kontrol önerilir.
