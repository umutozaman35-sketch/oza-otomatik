"""OZA MEDYA otomatik haber paylaşımı.

Kullanım:
  python main.py hazirla   -> haberi seçer, metni yazdırır, görseli üretir (cikti/bekleyen.json)
  python main.py paylas    -> bekleyen görseli Instagram'a yükler
  python main.py kimlik    -> anahtarın bağlı olduğu Instagram hesap kimliğini gösterir

Gerekli ortam değişkenleri (GitHub Secrets):
  ANTHROPIC_API_KEY, IG_ACCESS_TOKEN
İsteğe bağlı: IG_USER_ID (yoksa anahtardan otomatik bulunur), DRY_RUN=1 (Instagram'a yüklemeden dener)
Meta "Unified login" sistem kullanıcısı anahtarı kullanılır; süresi dolmaz.
"""
import hashlib
import json
import os
import re
import sys
import time
import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

import ayarlar as A

KOK = Path(__file__).resolve().parent
DURUM = KOK / "paylasilanlar.json"
BEKLEYEN = KOK / "cikti" / "bekleyen.json"
FONT = str(KOK / "Inter-%s.otf")
IG = os.environ.get("IG_API_HOST") or "https://graph.facebook.com"
AYLAR = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ",
         "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]


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


# ---------------------------------------------------------------- haberler
def haberleri_getir(kategori):
    url = A.KATEGORILER[kategori]["rss"]
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 OZA-MEDYA-bot"})
    r.raise_for_status()
    kok = ET.fromstring(r.content)
    sinir = datetime.now(timezone.utc) - timedelta(hours=A.EN_ESKI_SAAT)
    sonuc = []
    for it in kok.iter("item"):
        baslik = (it.findtext("title") or "").strip()
        kaynak = (it.findtext("source") or "").strip()
        if kaynak and baslik.endswith(" - " + kaynak):
            baslik = baslik[: -len(" - " + kaynak)]
        aciklama = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")
        aciklama = re.sub(r"\s+", " ", aciklama).strip()
        tarih = it.findtext("pubDate")
        try:
            t = email.utils.parsedate_to_datetime(tarih)
            if t < sinir:
                continue
        except Exception:
            pass
        if baslik:
            sonuc.append({"baslik": baslik, "kaynak": kaynak or "Basın",
                          "aciklama": aciklama[:400], "link": it.findtext("link") or ""})
    return sonuc


# ---------------------------------------------------------------- Claude
TALIMAT = """Sen OZA MEDYA adlı Türkçe bir Instagram haber sayfasının editörüsün.
Aşağıda "{kategori}" kategorisinde numaralı haber başlıkları var. Görevin:

1. Instagram'da paylaşmaya en uygun TEK haberi seç. Haber MUTLAKA "{kategori}"
   kategorisine ait olmalı (GÜNDEM = Türkiye gündemi, SPOR = spor haberleri,
   DİZİ = TV dizileri, MAGAZİN = ünlüler ve magazin). Kategoriye uymayan haberleri seçme.
2. Şunları ATLA: doğrulanmamış iddia ve söylentiler, ölüm/hastalık söylentileri,
   suç isnadı içeren ve kişileri hedef gösteren haberler, şiddet ve intihar haberleri,
   çocukları içeren hassas olaylar, siyasi taraf tutan veya kışkırtıcı içerikler.
3. SADECE verilen bilgileri kullan. Başlıkta veya açıklamada olmayan hiçbir rakam,
   isim, tarih ya da ayrıntı EKLEME. Yorum katma, tarafsız ol.
4. Metni kaynaktan kopyalama; kendi cümlelerinle yaz.

Hiçbiri uygun değilse {{"atla": true}} döndür.
Yoksa yalnızca şu JSON'u döndür, başka hiçbir şey yazma:
{{"secim": <numara>, "baslik": "<en fazla 70 karakter, çarpıcı ama abartısız başlık>",
"ozet": "<en fazla 170 karakter, 1-2 cümle özet>",
"aciklama": "<Instagram açıklaması: 2-4 cümle, yalnızca verilen bilgiler>"}}

Haberler:
{liste}
"""


def claude_yazdir(kategori, haberler):
    liste = "\n".join(
        f"{i}. {h['baslik']} (Kaynak: {h['kaynak']}) {h['aciklama'][:200]}"
        for i, h in enumerate(haberler))
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": A.CLAUDE_MODEL, "max_tokens": 800,
              "messages": [{"role": "user", "content":
                            TALIMAT.format(kategori=kategori, liste=liste)}]},
        timeout=120)
    r.raise_for_status()
    metin = "".join(p.get("text", "") for p in r.json()["content"])
    m = re.search(r"\{.*\}", metin, re.S)
    if not m:
        raise RuntimeError("Claude JSON döndürmedi: " + metin[:300])
    return json.loads(m.group(0))


# ---------------------------------------------------------------- tasarım
def satirlara_bol(d, metin, font, genislik):
    kelimeler, satirlar, cur = metin.split(), [], ""
    for k in kelimeler:
        t = (cur + " " + k).strip()
        if d.textlength(t, font=font) <= genislik:
            cur = t
        else:
            if cur:
                satirlar.append(cur)
            cur = k
    satirlar.append(cur)
    return satirlar


def gorsel_uret(kategori, baslik, ozet, cikti):
    renk = A.KATEGORILER[kategori]["renk"]
    im = Image.open(KOK / "arka_plan.png").convert("RGB")
    d = ImageDraw.Draw(im)
    # başlık uzunsa yazıyı küçült (en fazla 4 satır)
    for boyut in (84, 76, 68, 60, 54):
        hf = ImageFont.truetype(str(FONT % "ExtraBold"), boyut)
        hs = satirlara_bol(d, baslik, hf, 940)
        if len(hs) <= 4:
            break
    satir_h = int(boyut * 1.19)
    sf = ImageFont.truetype(str(FONT % "Medium"), 38)
    ss = satirlara_bol(d, ozet, sf, 940)[:4]
    blok = 58 + 52 + len(hs) * satir_h + 30 + 6 + 40 + len(ss) * 54
    x, y = 70, int(170 + (1220 - 170 - blok) / 2)
    # kategori etiketi
    cf = ImageFont.truetype(str(FONT % "Bold"), 30)
    tw = d.textlength(kategori, font=cf)
    d.rounded_rectangle([x, y, x + tw + 48, y + 58], 29, fill=renk)
    d.text((x + 24, y + 11), kategori, font=cf, fill="white")
    ty = y + 110
    for s in hs:
        d.text((70, ty), s, font=hf, fill="white")
        ty += satir_h
    ty += 30
    d.rectangle([70, ty, 160, ty + 6], fill=renk)
    ty += 40
    for s in ss:
        d.text((70, ty), s, font=sf, fill="#C9D3EA")
        ty += 54
    # tarih ve kullanıcı adı
    simdi = datetime.now(ZoneInfo(A.SAAT_DILIMI))
    tarih = f"{simdi.day} {AYLAR[simdi.month - 1]} {simdi.year}"
    df = ImageFont.truetype(str(FONT % "Medium"), 26)
    d.text((1010 - d.textlength(tarih, font=df), 75), tarih, font=df, fill="#AEB9D6")
    ff = ImageFont.truetype(str(FONT % "SemiBold"), 32)
    d.text((70, 1265), A.KULLANICI_ADI, font=ff, fill="white")
    im.save(cikti, "JPEG", quality=93)


# ---------------------------------------------------------------- adımlar
def hazirla():
    durum = durum_oku()
    goruldu = {p["id"] for p in durum["paylasilanlar"]}
    n = len(durum["paylasilanlar"])
    sira = A.SIRA[n % len(A.SIRA):] + A.SIRA[: n % len(A.SIRA)]
    for kategori in dict.fromkeys(sira):  # sıradaki kategoriden başla, olmazsa diğerleri
        try:
            haberler = [h for h in haberleri_getir(kategori) if kimlik(h["baslik"]) not in goruldu][:12]
        except Exception as e:
            print(f"[{kategori}] haberler alınamadı: {e}")
            continue
        if not haberler:
            print(f"[{kategori}] yeni haber yok")
            continue
        sonuc = claude_yazdir(kategori, haberler)
        if sonuc.get("atla"):
            print(f"[{kategori}] uygun haber bulunamadı, atlandı")
            continue
        h = haberler[int(sonuc["secim"])]
        dosya = f"cikti/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.jpg"
        gorsel_uret(kategori, sonuc["baslik"], sonuc["ozet"], KOK / dosya)
        etiket = A.KATEGORILER[kategori]["etiketler"]
        aciklama = (f"{sonuc['baslik']}\n\n{sonuc['aciklama']}\n\n"
                    f"Kaynak: {h['kaynak']}\n\n{etiket} #ozamedya")
        BEKLEYEN.write_text(json.dumps({
            "id": kimlik(h["baslik"]), "kategori": kategori, "dosya": dosya,
            "aciklama": aciklama, "orijinal": h["baslik"], "kaynak": h["kaynak"]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{kategori}] hazır: {sonuc['baslik']} -> {dosya}")
        return
    print("Bu çalışmada paylaşılacak haber yok.")


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
