# OZA BİLGİ otomatik paylaşım ayarları

# Görselin altında görünecek Instagram kullanıcı adı
KULLANICI_ADI = "@oza_bilgi"

# Kategoriler: etiket rengi, konu tarifi (Claude'a gider) ve hashtag'ler.
KATEGORILER = {
    "BİLGİ": {
        "renk": "#2F7BFF",
        "konu": "genel kültür: icatlar, ilginç nesneler, gündelik hayattaki şaşırtıcı gerçekler, rekorlar, yapılar",
        "etiketler": "#bilgi #genelkültür #ilginçbilgiler",
    },
    "TARİH": {
        "renk": "#FF3B3B",
        "konu": "tarih: önemli olaylar, antik uygarlıklar, keşifler, tarihi yapılar, Türk ve dünya tarihi",
        "etiketler": "#tarih #tarihtebugün #bilgi",
    },
    "BİLİM": {
        "renk": "#B347FF",
        "konu": "bilim: uzay, fizik, kimya, insan vücudu, teknoloji, astronomi",
        "etiketler": "#bilim #uzay #bilgi",
    },
    "DOĞA": {
        "renk": "#1FC75A",
        "konu": "doğa: hayvanlar, bitkiler, okyanuslar, doğa olayları, coğrafya harikaları",
        "etiketler": "#doğa #hayvanlar #bilgi",
    },
    "DİL": {
        "renk": "#FFC400",
        "konu": "dil: kelimelerin kökeni, Türkçe, deyimler, dünya dilleri, yazı sistemleri",
        "etiketler": "#dil #türkçe #kelimeler",
    },
}

# Kategorilerin sırası (her paylaşımda bir sonrakine geçer)
SIRA = ["BİLGİ", "TARİH", "BİLİM", "DOĞA", "DİL"]

# Metni yazan Claude modeli
CLAUDE_MODEL = "claude-sonnet-5-5"

# Saat dilimi
SAAT_DILIMI = "Asia/Baku"

# Renk doygunluğu (1.0 = orijinal, 1.4 = daha canlı)
DOYGUNLUK = 1.4

# Kart numarası buradan sonra devam eder (#001 elle paylaşıldı)
BASLANGIC_NO = 1
