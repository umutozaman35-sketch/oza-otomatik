"""OZA BİLGİ otomatik bilgi kartı paylaşımı.

Kullanım:
  python main.py hazirla   -> konuyu seçer, Vikipedi'den doğrular, kartı üretir (cikti/bekleyen.json)
  python main.py paylas    -> bekleyen kartı Instagram'a yükler
  python main.py kimlik    -> anahtarın bağlı olduğu Instagram hesabını gösterir
  python main.py ornek     -> internet olmadan örnek kart üretir (deneme için)

Gerekli GitHub Secrets: ANTHROPIC_API_KEY, IG_ACCESS_TOKEN, IG_USER_ID
İsteğe bağlı değişken: DRY_RUN=1 (Instagram'a yüklemeden dener)

Doğruluk: Claude yalnızca konu başlığı önerir. Kartın metni, o başlığın Türkçe
Vikipedi özetinden yazılır; Vikipedi'de bulunmayan konu paylaşılmaz.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

import ayarlar as A

KOK = Path(__file__).resolve().parent
DURUM = KOK / "paylasilanlar.json"
BEKLEYEN = KOK / "cikti" / "bekleyen.json"
FONT = str(KOK / "Inter-%s.otf")
IG = os.environ.get("IG_API_HOST") or "https://graph.facebook.com"
UA = {"User-Agent": "OZA-BILGI-bot/1.0 (Instagram bilgi karti; github.com)"}

W, H = 1080, 1350
ZEMIN = "#0B1F3A"
CIZGI = "#3A46A0"
ALTIN = "#FFB800"
SOLUK = "#A3B1E8"
METIN2 = "#D6DEFF"
MAVI = "#2F7DE1"


# ---------------------------------------------------------------- durum
def durum_oku():
    if DURUM.exists():
        d = json.loads(DURUM.read_text(encoding="utf-8"))
        d.setdefault("paylasilanlar", [])
        d.setdefault("sayac", 0)
        return d
    return {"paylasilanlar": [], "sayac": 0}


def durum_yaz(d):
    d["paylasilanlar"] = d["paylasilanlar"][-1000:]
    DURUM.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- Claude
def claude(istem, max_tokens=4000):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": A.CLAUDE_MODEL, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": istem}]},
        timeout=180)
    r.raise_for_status()
    j = r.json()
    metin = "".join(p.get("text", "") for p in j["content"] if p.get("type") == "text")
    for i, ch in enumerate(metin):
        if ch in "[{":
            try:
                return json.JSONDecoder().raw_decode(metin[i:])[0]
            except ValueError:
                continue
    raise RuntimeError(f"Claude JSON döndürmedi ({j.get('stop_reason')}): " + metin[:300])


KONU_ISTEMI = """Türkçe bir Instagram bilgi sayfası için konu öneriyorsun.
Kategori: {kategori} ({konu}).

Bu kategoride, çoğu insanın bilmediği, ilginç ve öğretici bilgiler içeren
8 farklı Türkçe Vikipedi madde başlığı öner. Başlık, tr.wikipedia.org'daki
maddenin TAM adı olmalı (ör. "Ahtapot", "Rosetta Taşı", "Işık hızı").

Şunları ÖNERME: yaşayan kişiler, siyasi partiler ve tartışmalı siyasi konular,
din tartışmaları, savaş ve şiddet ağırlıklı konular, hastalık ve ölüm, markalar,
diziler, filmler, şarkılar, sporcular, kulüpler.

Daha önce kullanılan başlıklar (bunları tekrar önerme):
{kullanilan}

Yalnızca JSON listesi döndür: ["Başlık 1", "Başlık 2", ...]"""

KART_ISTEMI = """Türkçe bir Instagram bilgi kartı yazıyorsun. Kategori: {kategori}.
Aşağıda "{baslik}" adlı Vikipedi maddesinin özeti var.

KURALLAR:
- YALNIZCA bu metindeki bilgileri kullan. Metinde olmayan hiçbir rakam, tarih,
  isim veya ayrıntı EKLEME. Emin değilsen o bilgiyi kullanma.
- Metindeki en ilginç ve şaşırtıcı bilgiyi seç.
- Metni kopyalama; kendi sade cümlelerinle yaz. Abartma, "inanılmaz" gibi
  süslü kelimeler kullanma.
- Metin karta uygun ilginç bir bilgi içermiyorsa {{"atla": true}} döndür.

Yoksa yalnızca şu JSON'u döndür:
{{"etiket": "<konunun 1-2 kelimelik etiketi, BÜYÜK HARF, en fazla 14 karakter; ör. UZAY, ANTİK MISIR, OKYANUS>",
"baslik": "<kartın ana bilgisi, tek çarpıcı cümle, en fazla 75 karakter>",
"ozet": "<bilgiyi tamamlayan, nasıl bilindiğini ya da nedenini anlatan 1-2 cümle, en fazla 170 karakter>",
"aciklama": "<Instagram açıklaması: 3-4 kısa cümle, yalnızca metindeki bilgiler>"}}

Vikipedi özeti:
{ozet}"""


# ---------------------------------------------------------------- Vikipedi
def vikipedi_ozet(baslik):
    url = "https://tr.wikipedia.org/api/rest_v1/page/summary/" + quote(baslik.replace(" ", "_"), safe="")
    r = requests.get(url, headers=UA, timeout=30)
    if r.status_code != 200:
        return None
    j = r.json()
    if j.get("type") != "standard":
        return None
    metin = (j.get("extract") or "").strip()
    if len(metin) < 250:
        return None
    return {"baslik": j.get("title") or baslik, "metin": metin,
            "link": j.get("content_urls", {}).get("desktop", {}).get("page", "")}


# ---------------------------------------------------------------- çizim
def f(agirlik, boyut):
    return ImageFont.truetype(FONT % agirlik, boyut)


def aralikli_yaz(d, xy, metin, font, renk, aralik):
    x, y = xy
    for harf in metin:
        d.text((x, y), harf, font=font, fill=renk)
        x += d.textlength(harf, font=font) + aralik
    return x - aralik


def aralikli_genislik(d, metin, font, aralik):
    return sum(d.textlength(h, font=font) for h in metin) + aralik * (len(metin) - 1)


def satirlara_bol(d, metin, font, genislik):
    satirlar, cur = [], ""
    for k in metin.split():
        t = (cur + " " + k).strip()
        if d.textlength(t, font=font) <= genislik:
            cur = t
        else:
            if cur:
                satirlar.append(cur)
            cur = k
    if cur:
        satirlar.append(cur)
    return satirlar


def zemin(w=W, h=H):
    """Logodaki gibi sağ üstten açılan lacivert degrade."""
    import math
    kucuk = Image.new("RGB", (64, 64))
    px = kucuk.load()
    a, b = (44, 52, 178), (9, 12, 52)
    for j in range(64):
        for i in range(64):
            t = min(1.0, math.hypot(63 - i, j) / 80)
            px[i, j] = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    return kucuk.resize((w, h), Image.BICUBIC)


def isaret(boyut):
    """OZA BİLGİ işareti: açık halka + altın yıldız. Şeffaf PNG döner."""
    import math
    S = 4
    n = 1000 * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, rm, k = 470 * S, 530 * S, 213 * S, 86 * S
    d.arc([cx - rm - k / 2, cy - rm - k / 2, cx + rm + k / 2, cy + rm + k / 2], -15, 281, fill="white", width=k)
    for aci in (-15, 281):
        ux, uy = cx + rm * math.cos(math.radians(aci)), cy + rm * math.sin(math.radians(aci))
        d.ellipse([ux - k / 2, uy - k / 2, ux + k / 2, uy + k / 2], fill="white")
    sx, sy = 623 * S, 376 * S
    pts = []
    for i in range(16):
        aci = math.radians(i * 22.5 - 90)
        rr = (108 if i % 4 == 0 else 40 if i % 2 == 0 else 25) * S
        pts.append((sx + rr * math.cos(aci), sy + rr * math.sin(aci)))
    d.polygon(pts, fill=ALTIN)
    im = im.crop((175 * S, 238 * S, 765 * S, 828 * S))
    return im.resize((boyut, boyut), Image.LANCZOS)


def logo_ciz(d, x, y, olcek=1.0):
    """İşaret + OZA BİLGİ yazısı (kartların üst şeridi)."""
    im = d._image
    m = isaret(int(64 * olcek))
    im.paste(m, (int(x), int(y + 2 * olcek)), m)
    r = 26 * olcek
    cx = x + r + 4 * olcek
    tx = cx + r + 30 * olcek
    d.text((tx, y + 4 * olcek), "OZA", font=f("ExtraBold", int(50 * olcek)), fill="white")
    bx = tx + d.textlength("OZA", font=f("ExtraBold", int(50 * olcek))) + 16 * olcek
    aralikli_yaz(d, (bx, y + 17 * olcek), "BİLGİ", f("SemiBold", int(30 * olcek)), SOLUK, 7 * olcek)


def renk_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tema(renk):
    """Kategori renginden kart teması üretir (zemin ışığı, koyu ton, vurgu)."""
    r = renk_rgb(renk)
    karis = lambda a, b, t: tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    siyah = (4, 5, 14)
    return {"koyu": karis(siyah, r, 0.05), "acik": karis(siyah, r, 0.42),
            "alt": karis(siyah, r, 0.20), "serit": karis(siyah, r, 0.02), "vurgu": r}


def zemin2(w=W, h=H, t=None):
    """Referans gönderideki zemin: sağ üstte mor-lacivert ışık, sol altta hafif parıltı."""
    import math
    n = 72
    k = Image.new("RGB", (n, int(n * h / w)))
    px = k.load()
    t = t or {"koyu": (7, 9, 24), "acik": (58, 66, 142), "alt": (24, 29, 64)}
    koyu, acik, alt = t["koyu"], t["acik"], t["alt"]
    kh = k.size[1]
    for j in range(kh):
        for i in range(n):
            u, v = i / (n - 1), j / (kh - 1)
            t1 = max(0.0, 1 - math.hypot(1 - u, v * 0.85) / 0.98) ** 1.15
            t2 = max(0.0, 1 - math.hypot(u, 1 - v) / 0.55) ** 1.5
            px[i, j] = tuple(int(koyu[c] + (acik[c] - koyu[c]) * t1 + (alt[c] - koyu[c]) * t2 * 0.8) for c in range(3))
    return k.resize((w, h), Image.BICUBIC)


INDIGO = (108, 124, 255)
ALTIN2 = (255, 200, 51)


def kart_ciz(kategori, baslik, ozet, numara, cikti, etiket=None, ust="BİLİYOR MUYDUNUZ?",
             renk=None, sag_ust=None, liste=None, zemin_renk=None):
    from PIL import ImageEnhance
    renk = renk or A.KATEGORILER[kategori]["renk"]
    etiket = (etiket or kategori).upper()
    T = tema(zemin_renk or renk)
    vurgu = renk_rgb(renk)
    im = zemin2(t=T)
    X = 72

    # arkadaki büyük soru işareti
    kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    kd = ImageDraw.Draw(kat)
    qf = f("ExtraBold", 640)
    kd.text((W - 50, 170), "?", font=qf, fill=(255, 255, 255, 20), anchor="ra")
    im.paste(kat, (0, 0), kat)
    d = ImageDraw.Draw(im)

    # üst şerit: işaret + OZA | BİLGİ, sağda kart numarası
    m = isaret(68)
    im.paste(m, (X - 6, 64), m)
    of = f("ExtraBold", 56)
    d.text((X + 72, 98), "OZA", font=of, fill="white", anchor="lm")
    bx = X + 72 + d.textlength("OZA", font=of) + 16
    d.rectangle([bx, 78, bx + 4, 118], fill=ALTIN2)
    aralikli_yaz(d, (bx + 18, 78), "BİLGİ", f("SemiBold", 38), ALTIN2, 6)
    nf = f("Medium", 23)
    no = sag_ust or "BİLGİ KARTI"
    nw = aralikli_genislik(d, no, nf, 2)
    aralikli_yaz(d, (W - X - nw, 88), no, nf, (120, 132, 182), 2)
    d.rectangle([X, 162, W - X, 163], fill=tuple(int(c * 0.55) + 18 for c in T["acik"]))

    # üst başlık ve etiket hapı
    y = 292
    aralikli_yaz(d, (X, y), ust, f("Bold", 27), ALTIN2, 5)
    y += 82
    pf = f("Bold", 27)
    pw = aralikli_genislik(d, etiket, pf, 5)
    d.rounded_rectangle([X, y, X + pw + 52, y + 52], 26, fill=vurgu)
    acik_renk = sum(vurgu) / 3 > 150 and vurgu[2] < 120
    aralikli_yaz(d, (X + 26, y + 10), etiket, pf, (20, 16, 4) if acik_renk else "white", 5)
    y += 52 + 50

    # başlık
    for boyut in (84, 78, 72, 66, 60, 56):
        hf = f("ExtraBold", boyut)
        hs = satirlara_bol(d, baslik, hf, W - 2 * X - 40)
        if len(hs) <= 4:
            break
    satir_h = int(boyut * 1.17)
    for s in hs:
        d.text((X, y), s, font=hf, fill="white")
        y += satir_h
    y += 44

    # gövde: renkli liste (tanıtım kartı) ya da çizgili alıntı bloğu
    if liste:
        lf = f("SemiBold", 38)
        for metin, lrenk in liste:
            d.rounded_rectangle([X, y + 12, X + 26, y + 38], 6, fill=lrenk)
            d.text((X + 48, y), metin, font=lf, fill=(232, 236, 250))
            y += 62
        ozet = ""
    bf = f("Medium", 38)
    bs = satirlara_bol(d, ozet, bf, W - X - 104 - 40)[:5]
    blok_h = len(bs) * 56
    if bs:
        d.rectangle([X, y + 4, X + 7, y + blok_h - 4], fill=vurgu)
    for s in bs:
        d.text((X + 32, y), s, font=bf, fill=(220, 224, 242))
        y += 56

    # alt şerit
    d.rectangle([0, 1222, W, 1350], fill=T["serit"])
    d.rectangle([0, 1222, W, 1226], fill=vurgu)
    d.text((X, 1288), A.KULLANICI_ADI, font=f("Bold", 31), fill="white", anchor="lm")
    sf = f("Bold", 25)
    sag = "KAYDET • PAYLAŞ"
    sw = aralikli_genislik(d, sag, sf, 4)
    aralikli_yaz(d, (W - X - sw, 1274), sag, sf, ALTIN2, 4)

    im = ImageEnhance.Color(im).enhance(getattr(A, "DOYGUNLUK", 1.0))
    im.save(cikti, "JPEG", quality=95)


# ---------------------------------------------------------------- adımlar
KUYRUK = KOK / "kuyruk.json"


def kuyruktan_hazirla():
    """kuyruk.json'da bekleyen hazır gönderi varsa sıradakini hazırlar."""
    if not KUYRUK.exists():
        return False
    liste = json.loads(KUYRUK.read_text(encoding="utf-8"))
    if not liste:
        return False
    g = liste[0]
    dosya = f"cikti/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.jpg"
    kart_ciz(g.get("kategori", "BİLGİ"), g["baslik"], g.get("ozet", ""), g.get("numara") or 0, KOK / dosya,
             etiket=g.get("etiket"), ust=g.get("ust", "BİLİYOR MUYDUNUZ?"), renk=g.get("renk"),
             sag_ust=g.get("sag_ust"), zemin_renk=g.get("zemin"), liste=[tuple(x) for x in g["liste"]] if g.get("liste") else None)
    BEKLEYEN.write_text(json.dumps({
        "konu": g.get("konu", g["baslik"]), "kategori": g.get("kategori", "BİLGİ"), "dosya": dosya,
        "aciklama": g["aciklama"], "link": "", "numara": g.get("numara"), "kuyruk": True},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[KUYRUK] hazır: {g['baslik']} -> {dosya}")
    return True


def hazirla():
    if kuyruktan_hazirla():
        return
    durum = durum_oku()
    kullanilan = [p["konu"] for p in durum["paylasilanlar"] if p.get("konu")]
    kullanilan_k = {k.lower() for k in kullanilan}
    n = durum["sayac"]
    sira = A.SIRA[n % len(A.SIRA):] + A.SIRA[: n % len(A.SIRA)]

    for kategori in sira:
        try:
            oneriler = claude(KONU_ISTEMI.format(
                kategori=kategori, konu=A.KATEGORILER[kategori]["konu"],
                kullanilan=", ".join(kullanilan[-300:]) or "(yok)"))
        except Exception as e:
            print(f"[{kategori}] konu önerisi alınamadı: {e}")
            continue
        for baslik in oneriler:
            if not isinstance(baslik, str) or baslik.lower() in kullanilan_k:
                continue
            try:
                vp = vikipedi_ozet(baslik)
            except Exception as e:
                print(f"[{kategori}] Vikipedi hatası ({baslik}): {e}")
                continue
            if not vp or vp["baslik"].lower() in kullanilan_k:
                print(f"[{kategori}] Vikipedi'de uygun madde yok: {baslik}")
                continue
            sonuc = claude(KART_ISTEMI.format(kategori=kategori, baslik=vp["baslik"], ozet=vp["metin"][:2500]))
            if sonuc.get("atla"):
                print(f"[{kategori}] {vp['baslik']}: uygun bilgi yok, atlandı")
                continue
            numara = max(n, getattr(A, "BASLANGIC_NO", 0)) + 1
            dosya = f"cikti/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.jpg"
            kart_ciz(kategori, sonuc["baslik"], sonuc["ozet"], numara, KOK / dosya, etiket=sonuc.get("etiket"))
            etiket = A.KATEGORILER[kategori]["etiketler"]
            aciklama = (f"{sonuc['baslik']}\n\n{sonuc['aciklama']}\n\n"
                        f"Kaynak: Vikipedi, \"{vp['baslik']}\" maddesi\n\n"
                        f"Daha fazla bilgi için {A.KULLANICI_ADI} takip et, kaydet ve paylaş!\n\n"
                        f"{etiket} #ozabilgi")
            BEKLEYEN.write_text(json.dumps({
                "konu": vp["baslik"], "kategori": kategori, "dosya": dosya,
                "aciklama": aciklama, "link": vp["link"], "numara": numara},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{kategori}] hazır: {sonuc['baslik']} ({vp['baslik']}) -> {dosya}")
            return
    print("Bu çalışmada paylaşılacak kart bulunamadı.")


def ig_istek(yontem, yol, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(yontem, f"{IG}/{yol}", params=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Instagram hatası {r.status_code}: {r.text}")
    return r.json()


def paylas():
    if not BEKLEYEN.exists():
        print("Bekleyen gönderi yok.")
        return
    b = json.loads(BEKLEYEN.read_text(encoding="utf-8"))
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GORSEL_SHA") or os.environ.get("GITHUB_SHA")
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{b['dosya']}"
    if os.environ.get("DRY_RUN") == "1" or not os.environ.get("IG_ACCESS_TOKEN"):
        print("DRY_RUN: Instagram'a yüklenmedi. Görsel:", url)
    else:
        kullanici = ig_hesap_kimligi()
        kap = ig_istek("POST", f"{kullanici}/media", image_url=url, caption=b["aciklama"])
        for _ in range(20):
            st = ig_istek("GET", kap["id"], fields="status_code").get("status_code")
            if st == "FINISHED":
                break
            if st == "ERROR":
                raise RuntimeError("Instagram görseli işleyemedi")
            time.sleep(5)
        sonuc = ig_istek("POST", f"{kullanici}/media_publish", creation_id=kap["id"])
        print("Paylaşıldı, gönderi kimliği:", sonuc.get("id"))
    d = durum_oku()
    d["sayac"] = max(d["sayac"], b.get("numara") or 0)
    if b.get("kuyruk") and KUYRUK.exists():
        liste = json.loads(KUYRUK.read_text(encoding="utf-8"))
        KUYRUK.write_text(json.dumps(liste[1:], ensure_ascii=False, indent=1), encoding="utf-8")
    d["paylasilanlar"].append({"konu": b["konu"], "kategori": b["kategori"], "dosya": b["dosya"],
                               "zaman": datetime.now(timezone.utc).isoformat()})
    durum_yaz(d)
    BEKLEYEN.unlink()


def ig_hesap_kimligi():
    if os.environ.get("IG_USER_ID", "").strip():
        return os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{IG}/debug_token", params={"input_token": token, "access_token": token}, timeout=30)
    if r.ok:
        for kapsam in r.json().get("data", {}).get("granular_scopes", []):
            if kapsam.get("scope") in ("instagram_content_publish", "instagram_basic") and kapsam.get("target_ids"):
                return kapsam["target_ids"][0]
    raise RuntimeError("Instagram hesap kimliği bulunamadı. IG_USER_ID secret'ını ekleyin.")


def kimlik_goster():
    kid = ig_hesap_kimligi()
    bilgi = ig_istek("GET", kid, fields="username")
    print(f"Bağlı Instagram hesabı: @{bilgi.get('username')}  (kimlik: {kid})")


def ornek():
    (KOK / "cikti").mkdir(exist_ok=True)
    ornekler = [
        ("DOĞA", "Ahtapotların üç kalbi vardır", "Kalplerden ikisi solungaçlara kan pompalar, üçüncüsü ise vücudun geri kalanına."),
        ("TARİH", "Rosetta Taşı, Mısır hiyerogliflerinin çözülmesini sağladı", "Taşta aynı metin üç farklı yazıyla yer alıyordu."),
        ("DİL", "Türkçe, sondan eklemeli bir dildir", "Kelimelerin sonuna eklenen ekler anlamı adım adım değiştirir."),
    ]
    for i, (k, b, o) in enumerate(ornekler, 1):
        kart_ciz(k, b, o, i, KOK / "cikti" / f"ornek_{i}.jpg")
    print("Örnekler cikti/ klasöründe.")


if __name__ == "__main__":
    {"hazirla": hazirla, "paylas": paylas, "kimlik": kimlik_goster, "ornek": ornek}[sys.argv[1]]()
