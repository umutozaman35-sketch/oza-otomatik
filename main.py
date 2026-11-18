"""OZA BİLGİ otomatik bilgi kartı paylaşımı.

Kullanım:
  python main.py hazirla   -> bilgiyi yazdırır, kartı üretir (cikti/bekleyen.json)
  python main.py paylas    -> bekleyen kartı Instagram'a yükler
  python main.py kimlik    -> anahtarın bağlı olduğu Instagram hesabını gösterir

Gerekli ortam değişkenleri (GitHub Secrets):
  ANTHROPIC_API_KEY, IG_ACCESS_TOKEN
İsteğe bağlı: IG_USER_ID (yoksa anahtardan otomatik bulunur), DRY_RUN=1 (Instagram'a yüklemeden dener)
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import ayarlar as A

KOK = Path(__file__).resolve().parent
DURUM = KOK / "paylasilanlar.json"
BEKLEYEN = KOK / "cikti" / "bekleyen.json"
FONT = str(KOK / "Inter-%s.otf")
IG = os.environ.get("IG_API_HOST") or "https://graph.facebook.com"
W, H = 1080, 1350
SARI = "#FFC83D"


# ---------------------------------------------------------------- durum
def durum_oku():
    if DURUM.exists():
        return json.loads(DURUM.read_text(encoding="utf-8"))
    return {"paylasilanlar": []}


def durum_yaz(d):
    d["paylasilanlar"] = d["paylasilanlar"][-500:]
    DURUM.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def kimlik(baslik):
    temiz = re.sub(r"\W+", " ", baslik.lower()).strip()
    return hashlib.sha1(temiz.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- Claude
TALIMAT = """Sen OZA BİLGİ adlı Türkçe bir Instagram bilgi sayfasının editörüsün.
Bu sayfa "Biliyor muydunuz?" tarzında eğlenceli, şaşırtıcı, önemli ve DOĞRU bilgi kartları paylaşır.

Kategori: {kategori} ({konu})

Kurallar:
1. Bu kategoriye uyan TEK bir bilgi yaz. Bilgi hem eğlenceli/şaşırtıcı olsun ("vay be!" dedirtsin)
   hem de değerli olsun: insanların arkadaşına anlatmak isteyeceği, öğrenince bir şey kazandığı
   bilgiler seç. Sıkıcı, çok bilinen ya da önemsiz ayrıntılardan kaçın.
2. Bilgi kesinlikle doğru, bilimsel olarak kabul görmüş ve kolayca doğrulanabilir olmalı.
   Emin olmadığın rakam, tarih veya isim kullanma. Tartışmalı, efsane ya da
   "internette dolaşan ama yanlış" bilgileri (ör. "Çin Seddi uzaydan görünür") KULLANMA.
3. Siyaset, din, ölüm/şiddet, sağlık tavsiyesi ve kişileri hedef alan konulardan kaçın.
4. Aşağıdaki daha önce paylaşılmış başlıklara benzeyen bir bilgi YAZMA:
{onceki}

Yalnızca şu JSON'u döndür, başka hiçbir şey yazma:
{{"baslik": "<en fazla 65 karakter, çarpıcı bilgi cümlesi>",
"detay": "<en fazla 190 karakter, bilgiyi 1-2 cümleyle açıklayan kısım>",
"aciklama": "<Instagram açıklaması: 2-4 cümle, bilgiyi biraz daha açan ve takipçiye soru soran samimi metin>"}}
"""


def claude_yazdir(kategori, onceki):
    k = A.KATEGORILER[kategori]
    liste = "\n".join(f"- {b}" for b in onceki[-80:]) or "- (henüz yok)"
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": A.CLAUDE_MODEL, "max_tokens": 800,
              "messages": [{"role": "user", "content":
                            TALIMAT.format(kategori=kategori, konu=k["konu"], onceki=liste)}]},
        timeout=120)
    r.raise_for_status()
    metin = "".join(p.get("text", "") for p in r.json()["content"])
    m = re.search(r"\{.*\}", metin, re.S)
    if not m:
        raise RuntimeError("Claude JSON döndürmedi: " + metin[:300])
    return json.loads(m.group(0))


# ---------------------------------------------------------------- tasarım
def font(agirlik, boyut):
    return ImageFont.truetype(FONT % agirlik, boyut)


def satirlara_bol(d, metin, f, genislik):
    kelimeler, satirlar, cur = metin.split(), [], ""
    for k in kelimeler:
        t = (cur + " " + k).strip()
        if d.textlength(t, font=f) <= genislik:
            cur = t
        else:
            if cur:
                satirlar.append(cur)
            cur = k
    satirlar.append(cur)
    return satirlar


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def arka_plan(renk):
    # koyu lacivert dikey geçiş
    ust, alt = (16, 20, 44), (6, 8, 20)
    grad = Image.linear_gradient("L").resize((W, H))
    im = Image.composite(Image.new("RGB", (W, H), alt), Image.new("RGB", (W, H), ust), grad)
    # kategori renginde yumuşak ışık
    isik = Image.new("L", (W, H), 0)
    ImageDraw.Draw(isik).ellipse([520, -260, 1420, 640], fill=90)
    ImageDraw.Draw(isik).ellipse([-420, 900, 380, 1700], fill=45)
    isik = isik.filter(ImageFilter.GaussianBlur(170))
    im = Image.composite(Image.new("RGB", (W, H), hex_rgb(renk)), im, isik)
    # silik büyük soru işareti
    iz = Image.new("L", (W, H), 0)
    ImageDraw.Draw(iz).text((640, 120), "?", font=font("ExtraBold", 760), fill=16)
    im = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), im, iz)
    return im


def harf_aralikli(d, xy, metin, f, renk, aralik):
    x, y = xy
    for c in metin:
        d.text((x, y), c, font=f, fill=renk)
        x += d.textlength(c, font=f) + aralik
    return x


def gorsel_uret(kategori, baslik, detay, cikti, no=None):
    renk = A.KATEGORILER[kategori]["renk"]
    im = arka_plan(renk)
    d = ImageDraw.Draw(im)

    # logo: OZA | BİLGİ
    d.text((70, 62), "OZA", font=font("ExtraBold", 66), fill="white")
    lx = 70 + d.textlength("OZA", font=font("ExtraBold", 66)) + 22
    d.rectangle([lx, 74, lx + 5, 124], fill=SARI)
    harf_aralikli(d, (lx + 24, 80), "BİLGİ", font("Bold", 34), SARI, 7)
    if no is not None:
        nf = font("SemiBold", 26)
        t = f"BİLGİ KARTI  #{no:03d}"
        d.text((1010 - d.textlength(t, font=nf), 84), t, font=nf, fill="#9AA6C8")
    d.line([70, 165, 1010, 165], fill=(70, 78, 112), width=2)

    # başlık boyutu: en fazla 4 satır
    for boyut in (82, 74, 66, 60, 54):
        hf = font("ExtraBold", boyut)
        hs = satirlara_bol(d, baslik, hf, 930)
        if len(hs) <= 4:
            break
    satir_h = int(boyut * 1.2)
    sf = font("Medium", 40)
    ss = satirlara_bol(d, detay, sf, 920)[:5]

    blok = 44 + 40 + 58 + 50 + len(hs) * satir_h + 44 + len(ss) * 58 + 40
    y = int(200 + (1180 - 200 - blok) / 2)

    # "BİLİYOR MUYDUNUZ?"
    harf_aralikli(d, (70, y), "BİLİYOR MUYDUNUZ?", font("Bold", 30), SARI, 5)
    y += 44 + 40
    # kategori etiketi
    cf = font("Bold", 28)
    tw = d.textlength(kategori, font=cf) + 6 * len(kategori)
    d.rounded_rectangle([70, y, 70 + tw + 44, y + 54], 27, fill=renk)
    harf_aralikli(d, (92, y + 11), kategori, cf, "white", 6)
    y += 58 + 50
    # başlık
    for s in hs:
        d.text((70, y), s, font=hf, fill="white")
        y += satir_h
    y += 18
    # detay kutusu: solda renkli çizgi
    ust = y + 26
    for s in ss:
        d.text((104, y + 26), s, font=sf, fill="#D3DAEE")
        y += 58
    d.rounded_rectangle([70, ust + 4, 78, y + 26 - 10], 4, fill=renk)

    # alt bant
    d.rectangle([0, 1218, W, H], fill=(5, 7, 18))
    d.rectangle([0, 1218, W, 1221], fill=renk)
    d.text((70, 1262), A.KULLANICI_ADI, font=font("SemiBold", 34), fill="white")
    kf = font("Bold", 24)
    harf_aralikli(d, (742, 1270), "KAYDET • PAYLAŞ", kf, SARI, 3)
    im.save(cikti, "JPEG", quality=93)


# ---------------------------------------------------------------- adımlar
def hazirla():
    durum = durum_oku()
    gecmis = durum["paylasilanlar"]
    goruldu = {p["id"] for p in gecmis}
    n = len(gecmis)
    kategori = A.SIRA[n % len(A.SIRA)]
    onceki = [p["baslik"] for p in gecmis if p.get("kategori") == kategori]
    for deneme in range(3):
        sonuc = claude_yazdir(kategori, onceki)
        if kimlik(sonuc["baslik"]) not in goruldu:
            break
        onceki.append(sonuc["baslik"])
    else:
        print("Yeni bilgi üretilemedi, bu çalışma atlandı.")
        return
    dosya = f"cikti/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.jpg"
    gorsel_uret(kategori, sonuc["baslik"], sonuc["detay"], KOK / dosya, no=n + 1)
    etiket = A.KATEGORILER[kategori]["etiketler"]
    aciklama = (f"{sonuc['baslik']}\n\n{sonuc['aciklama']}\n\n"
                f"Daha fazla bilgi için {A.KULLANICI_ADI} takip et, kaydet ve paylaş!\n\n"
                f"{etiket} #ozabilgi #biliyormuydunuz #ilginçbilgiler")
    BEKLEYEN.write_text(json.dumps({
        "id": kimlik(sonuc["baslik"]), "kategori": kategori, "dosya": dosya,
        "aciklama": aciklama, "orijinal": sonuc["baslik"]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{kategori}] hazır: {sonuc['baslik']} -> {dosya}")


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
            durum = ig_istek("GET", kap["id"], fields="status_code").get("status_code")
            if durum == "FINISHED":
                break
            if durum == "ERROR":
                raise RuntimeError("Instagram görseli işleyemedi")
            time.sleep(5)
        sonuc = ig_istek("POST", f"{kullanici}/media_publish", creation_id=kap["id"])
        print("Paylaşıldı, gönderi kimliği:", sonuc.get("id"))
    d = durum_oku()
    d["paylasilanlar"].append({"id": b["id"], "kategori": b["kategori"], "dosya": b["dosya"],
                               "baslik": b["orijinal"], "zaman": datetime.now(timezone.utc).isoformat()})
    durum_yaz(d)
    BEKLEYEN.unlink()


def ig_hesap_kimligi():
    """Instagram profesyonel hesap kimliği: IG_USER_ID yoksa anahtarın izinlerinden bulunur."""
    if os.environ.get("IG_USER_ID", "").strip():
        return os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{IG}/debug_token", params={"input_token": token, "access_token": token}, timeout=30)
    if r.ok:
        for kapsam in r.json().get("data", {}).get("granular_scopes", []):
            if kapsam.get("scope") in ("instagram_content_publish", "instagram_basic") and kapsam.get("target_ids"):
                return kapsam["target_ids"][0]
    r = requests.get(f"{IG}/me/accounts", params={"fields": "instagram_business_account",
                                                   "access_token": token}, timeout=30)
    if r.ok:
        for sayfa in r.json().get("data", []):
            if sayfa.get("instagram_business_account"):
                return sayfa["instagram_business_account"]["id"]
    raise RuntimeError("Instagram hesap kimliği bulunamadı. IG_USER_ID secret'ını elle ekleyin.")


def kimlik_goster():
    kid = ig_hesap_kimligi()
    bilgi = ig_istek("GET", kid, fields="username")
    print(f"Bağlı Instagram hesabı: @{bilgi.get('username')}  (kimlik: {kid})")


if __name__ == "__main__":
    {"hazirla": hazirla, "paylas": paylas, "kimlik": kimlik_goster}[sys.argv[1]]()
