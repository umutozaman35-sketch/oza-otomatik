# OZA MEDYA otomatik paylaşım ayarları
# Bu dosyadaki değerleri değiştirerek sistemi kendinize göre ayarlayabilirsiniz.

# Görselin altında görünecek Instagram kullanıcı adınız
KULLANICI_ADI = "@ozamedya"

# Kategoriler: etiket rengi ve haber kaynağı (RSS).
# Google Haberler RSS adresleri kullanılıyor; "q=" kısmındaki kelimeyi değiştirerek
# konuyu daraltabilirsiniz (ör. q=süper+lig). "when:1d" = son 24 saat.
KATEGORILER = {
    "GÜNDEM": {
        "renk": "#1E5BFF",
        "rss": "https://news.google.com/rss/search?q=g%C3%BCndem+when:1d&hl=tr&gl=TR&ceid=TR:tr",
        "etiketler": "#gündem #sondakika #haber",
    },
    "SPOR": {
        "renk": "#10B981",
        "rss": "https://news.google.com/rss/search?q=spor+when:1d&hl=tr&gl=TR&ceid=TR:tr",
        "etiketler": "#spor #futbol #süperlig",
    },
    "DİZİ": {
        "renk": "#8B5CF6",
        "rss": "https://news.google.com/rss/search?q=dizi+when:1d&hl=tr&gl=TR&ceid=TR:tr",
        "etiketler": "#dizi #televizyon #reyting",
    },
    "MAGAZİN": {
        "renk": "#EC4899",
        "rss": "https://news.google.com/rss/search?q=magazin+when:1d&hl=tr&gl=TR&ceid=TR:tr",
        "etiketler": "#magazin #ünlüler #gündem",
    },
}

# Kategorilerin sırası: her çalışmada sıradaki kategoriden bir haber paylaşılır.
# Sadece bu 4 kategori paylaşılır; sırayla döner (günde 8 gönderi = her kategoriden 2).
SIRA = ["GÜNDEM", "SPOR", "DİZİ", "MAGAZİN"]

# Metni yazan Claude modeli
CLAUDE_MODEL = "claude-sonnet-5-5"

# Bir haberin en fazla kaç saatlik olabileceği
EN_ESKI_SAAT = 8

# Görseldeki tarih için saat dilimi
SAAT_DILIMI = "Asia/Baku"
