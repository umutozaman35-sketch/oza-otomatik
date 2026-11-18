# OZA BİLGİ otomatik paylaşım ayarları
# Bu dosyadaki değerleri değiştirerek sistemi kendinize göre ayarlayabilirsiniz.

# Kartın altında görünecek Instagram kullanıcı adı
KULLANICI_ADI = "@oza_bilgi"

# Kategoriler: etiket rengi, Claude'a verilecek konu tarifi ve hashtag'ler.
KATEGORILER = {
    "UZAY": {
        "renk": "#6C7BFF",
        "konu": "uzay, gezegenler, yıldızlar, astronomi",
        "etiketler": "#uzay #astronomi #bilgi",
    },
    "TARİH": {
        "renk": "#E8A33D",
        "konu": "dünya ve Türk tarihi, eski uygarlıklar, ilginç tarihi olaylar",
        "etiketler": "#tarih #tarihbilgisi #bilgi",
    },
    "BİLİM": {
        "renk": "#22C3A6",
        "konu": "fizik, kimya, teknoloji, icatlar",
        "etiketler": "#bilim #teknoloji #bilgi",
    },
    "DOĞA": {
        "renk": "#4CC85A",
        "konu": "hayvanlar, bitkiler, doğa olayları",
        "etiketler": "#doğa #hayvanlar #bilgi",
    },
    "İNSAN": {
        "renk": "#F2607A",
        "konu": "insan vücudu, beyin, psikoloji, sağlık bilgisi (tavsiye değil, bilgi)",
        "etiketler": "#insanvücudu #psikoloji #bilgi",
    },
    "DÜNYA": {
        "renk": "#3BA7F0",
        "konu": "ülkeler, coğrafya, şehirler, kültürler, rekorlar",
        "etiketler": "#dünya #coğrafya #bilgi",
    },
}

# Kategorilerin sırası: her çalışmada sıradaki kategoriden bir bilgi kartı paylaşılır.
SIRA = ["UZAY", "TARİH", "BİLİM", "DOĞA", "İNSAN", "DÜNYA"]

# Metni yazan Claude modeli
CLAUDE_MODEL = "claude-sonnet-5-5"
