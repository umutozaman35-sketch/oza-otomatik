# -*- coding: utf-8 -*-
"""HEDEFLERİN YOLUNDA - otomatik Reels üretici ve paylaşıcı.

Kullanım:
  python reels.py hazirla        -> içeriği seç, doğrula, videoyu üret (cikti_reels/)
  python reels.py paylas         -> hazır videoyu Instagram'a Reels olarak yükle
  python reels.py ornek dosya.json [cikti.mp4]  -> verilen senaryodan video üret (test)
"""
import os, sys, json, math, random, re, time, shutil, subprocess, wave, unicodedata
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti_reels")
DURUM = os.path.join(KOK, "reels_durum.json")
W, H, FPS = 1080, 1920, 30
KULLANICI = "@hedeflerinyolunda"
MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-5-5"
IG = os.environ.get("IG_API_HOST") or "https://graph.facebook.com"
IG_SURUM = os.environ.get("IG_API_VERSION") or "v23.0"
SIRA = ["liste", "soz", "mit", "liste", "soz", "egzersiz"]
UA = {"User-Agent": "HedeflerinYolundaBot/1.0 (github.com/umutozaman35-sketch/oza-otomatik)"}

# ----------------------------------------------------------------- yazı tipleri
def _bul(*adlar):
    for a in adlar:
        for d in (KOK, os.path.join(KOK, "fontlar"), "/usr/share/fonts/truetype/google-fonts",
                  "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype"):
            p = os.path.join(d, a)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(adlar[0])
_FC = {}
def pop(s):
    k = ("p", s)
    if k not in _FC: _FC[k] = ImageFont.truetype(_bul("Poppins-Bold.ttf"), s)
    return _FC[k]
def inter(w, s):
    k = (w, s)
    if k not in _FC: _FC[k] = ImageFont.truetype(_bul(f"Inter-{w}.otf"), s)
    return _FC[k]

def tr_buyuk(m): return m.replace("i", "İ").replace("ı", "I").upper()

# ----------------------------------------------------------------- renk ve doku
GOLD = (214, 162, 50); ACIK = (238, 238, 238); SOL = (165, 165, 165); KOYU = (20, 16, 8)
_GD = {}
def altin_doku(w, h):
    k = h
    if k not in _GD:
        stops = [(0, (255, 226, 140)), (.45, (214, 162, 50)), (.6, (255, 238, 175)), (1, (150, 104, 22))]
        col = np.zeros((h, 3))
        for y in range(h):
            v = y / max(1, h - 1)
            for i in range(len(stops) - 1):
                if stops[i][0] <= v <= stops[i + 1][0]:
                    a, b = stops[i][1], stops[i + 1][1]
                    kk = (v - stops[i][0]) / (stops[i + 1][0] - stops[i][0]); break
            col[y] = [a[j] + (b[j] - a[j]) * kk for j in range(3)]
        _GD[k] = Image.fromarray(col.astype(np.uint8)[:, None, :].repeat(1, 1), "RGB")
    return _GD[k].resize((max(1, w), h))

def isaret_maske(boyut, cerceve=True):
    S=4; n=600*S; m=Image.new("L",(n,n),0); d=ImageDraw.Draw(m)
    if cerceve: d.rectangle([40*S,40*S,560*S,560*S],outline=255,width=14*S)
    P=np.array([(130,455),(250,320),(325,395),(440,250)],float)  # yükselen çizgi
    u=P[-1]-P[-2]; u/=np.linalg.norm(u); nn=np.array([-u[1],u[0]])
    hw=23.0                                  # gövde yarı kalınlığı
    tip=P[-1]+u*95; taban=P[-1]+u*5          # ok başı
    Q=np.vstack([P[:-1],taban])
    def nrm(a,b): v=b-a; v/=np.linalg.norm(v); return np.array([-v[1],v[0]])
    sol,sag=[],[]
    for i in range(len(Q)):
        if i==0: k=nrm(Q[0],Q[1]); L=hw
        elif i==len(Q)-1: k=nrm(Q[-2],Q[-1]); L=hw
        else:
            n1=nrm(Q[i-1],Q[i]); n2=nrm(Q[i],Q[i+1]); k=n1+n2; k/=np.linalg.norm(k); L=hw/np.dot(k,n1)
        sol.append(Q[i]+k*L); sag.append(Q[i]-k*L)
    poly=[tuple(p*S) for p in sol+sag[::-1]]
    d.polygon(poly,fill=255)
    ok=[tip, taban+nn*68, taban-nn*68]
    d.polygon([tuple(p*S) for p in ok],fill=255)
    return m.resize((boyut,boyut),Image.LANCZOS)

def isaret(boyut):
    m = isaret_maske(boyut)
    im = altin_doku(boyut, boyut).convert("RGBA"); im.putalpha(m); return im

def zemin():
    im = Image.new("RGB", (W, H), (6, 6, 7))
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([W*.3, -H*.2, W*1.4, H*.4], fill=70)
    g = g.filter(ImageFilter.GaussianBlur(200)); im = Image.composite(Image.new("RGB", (W, H), (78, 56, 18)), im, g)
    g2 = Image.new("L", (W, H), 0); ImageDraw.Draw(g2).ellipse([-W*.4, H*.7, W*.6, H*1.3], fill=40)
    g2 = g2.filter(ImageFilter.GaussianBlur(220)); im = Image.composite(Image.new("RGB", (W, H), (50, 36, 12)), im, g2)
    rng = np.random.default_rng(3); a = np.asarray(im).astype(np.int16)
    a += rng.integers(-5, 6, size=(H, W, 1)); return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def gir(t, t0, d=.4): return ease((t - t0) / d)

# ----------------------------------------------------------------- metin katmanları
def jetonlar(metin):
    """'*altın*' ile işaretli kelimeleri ayırır -> [(kelime, altin_mi)]"""
    out = []; altin = False
    for parca in re.split(r"(\*)", metin):
        if parca == "*": altin = not altin; continue
        for k in parca.split():
            out.append((k, altin))
    return out

def sar(jet, font, gen):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); sp = d.textlength(" ", font=font)
    satir, cur, w = [], [], 0
    for k, a in jet:
        kw = d.textlength(k, font=font)
        if cur and w + sp + kw > gen:
            satir.append(cur); cur, w = [], 0
        w = w + (sp if cur else 0) + kw; cur.append((k, a))
    if cur: satir.append(cur)
    return satir

def metin_katmani(metin, font, renk=ACIK, hepsi_altin=False, gen=880, aralik=1.18, hiza="orta"):
    jet = jetonlar(metin)
    if hepsi_altin: jet = [(k, True) for k, _ in jet]
    satirlar = sar(jet, font, gen)
    asc, desc = font.getmetrics(); lh = int((asc + desc) * aralik)
    h = lh * len(satirlar) + 8
    kat = Image.new("RGBA", (W, h), (0, 0, 0, 0)); d = ImageDraw.Draw(kat)
    maske = Image.new("L", (W, h), 0); dm = ImageDraw.Draw(maske)
    doku = Image.new("RGB", (W, h), (0, 0, 0)); sp = d.textlength(" ", font=font)
    for i, s in enumerate(satirlar):
        tw = sum(d.textlength(k, font=font) for k, _ in s) + sp * (len(s) - 1)
        x = (W - tw) / 2 if hiza == "orta" else 110; y = i * lh + 4
        if any(a for _, a in s): doku.paste(altin_doku(W, lh), (0, y))
        for k, a in s:
            if a: dm.text((x, y), k, font=font, fill=255)
            else: d.text((x, y), k, font=font, fill=renk + (255,))
            x += d.textlength(k, font=font) + sp
    g = doku.convert("RGBA"); g.putalpha(maske)
    return Image.alpha_composite(kat, g), len(satirlar)

def kelime_say(m): return len(re.sub(r"[*“”\"]", "", m).split())

# ----------------------------------------------------------------- sahne elemanları
STIL = {  # (font fabrikası, renk, altın)
    "ana": (lambda s: inter("SemiBold", int(52 * s)), ACIK, False),
    "yan": (lambda s: inter("Medium", int(40 * s)), SOL, False),
    "vurgu": (lambda s: pop(int(66 * s)), ACIK, True),
    "soz": (lambda s: pop(int(80 * s)), ACIK, False),
    "iddia": (lambda s: pop(int(72 * s)), ACIK, False),
    "buyuk": (lambda s: pop(int(104 * s)), ACIK, False),
}

def el_hazirla(el, s):
    """Elemanın statik katmanını ve yüksekliğini hazırlar."""
    t = el["tip"]
    if t == "metin":
        fab, renk, alt = STIL[el.get("stil", "ana")]
        el["kat"], _ = metin_katmani(el["metin"], fab(s), renk, alt or el.get("altin", False))
        el["h"] = el["kat"].height
    elif t == "kanca":
        el["kat"], _ = metin_katmani(el["metin"], pop(el["boy"]), ACIK, False, gen=940, aralik=1.05)
        el["h"] = el["kat"].height
    elif t == "baslik":
        boy = int(100 * s)
        while boy > 60 and ImageDraw.Draw(Image.new("L", (1, 1))).textlength(el["metin"], font=pop(boy)) > 920: boy -= 4
        el["kat"], _ = metin_katmani(el["metin"], pop(boy), ACIK, True, gen=940, aralik=1.05); el["h"] = el["kat"].height
    elif t == "pill": el["h"] = 84
    elif t == "cizgi": el["h"] = 10
    elif t == "cubuk": el["h"] = 150 * len(el["ogeler"])
    elif t == "damga": el["h"] = 180
    elif t == "halka": el["h"] = 520
    elif t == "logo": el["h"] = 230
    elif t == "kulp": el["kat"], _ = metin_katmani(KULLANICI, pop(64), ACIK, True); el["h"] = el["kat"].height
    elif t == "buton": el["h"] = 110
    else: raise ValueError(t)

def okuma(el):
    t = el["tip"]
    if t in ("metin", "kanca"): return max(.9, kelime_say(el["metin"]) * .32)
    return {"pill": .3, "cizgi": .15, "baslik": .7, "cubuk": 2.6, "damga": 1.2, "halka": 0, "logo": .5, "kulp": .5, "buton": .5}[t]

def sahne_kur(els, bekle=1.6, ust_sinir=400, alt_sinir=1560, sabit_sure=None, boslik=38):
    s = 1.0
    while True:
        for el in els: el_hazirla(el, s)
        top = sum(e["h"] for e in els) + boslik * (len(els) - 1)
        if top <= alt_sinir - ust_sinir or s < .62: break
        s *= .92
    y = ust_sinir + max(0, (alt_sinir - ust_sinir - top) // 2)
    t = .15
    for i, el in enumerate(els):
        el["y"] = y; y += el["h"] + boslik
        el["t0"] = el.get("t0", t)
        t = el["t0"] + max(el.get("bekle", .35), okuma(el) if el["tip"] not in ("kanca",) else .45)
    son = els[-1]
    sure = sabit_sure or (son["t0"] + okuma(son) + bekle)
    return {"els": els, "sure": min(sure, 22)}

def el_ciz(im, d, el, t):
    a = gir(t, el["t0"])
    if a <= 0: return
    tip = el["tip"]; y = el["y"]; cx = W // 2
    if "kat" in el:
        kat = el["kat"]
        if a < .999:
            al = kat.getchannel("A").point(lambda v: int(v * a)); kat = kat.copy(); kat.putalpha(al)
        im.paste(kat, (0, int(y + (1 - a) * 30)), kat); return
    if tip == "pill":
        f = inter("ExtraBold", 36); tw = d.textlength(el["metin"], font=f) + 90
        d.rounded_rectangle([cx - tw/2, y, cx + tw/2, y + 76], 38, outline=GOLD, width=4)
        _altin_tek(im, (cx, y + 38), el["metin"], f, a)
    elif tip == "cizgi":
        w = 60 * a; d.rectangle([cx - w, y, cx + w, y + 6], fill=GOLD)
    elif tip == "cubuk":
        bx, bw = 150, W - 300
        for i, o in enumerate(el["ogeler"]):
            yy = y + i * 150; k = ease((t - el["t0"] - i * .5) / 1.4)
            if k <= 0: continue
            _yaz(im, (bx, yy + 22), tr_buyuk(o["ad"]), inter("Bold", 32), SOL, min(1, k * 2), "lm")
            v = max(0, min(100, float(o["deger"]))) / 100
            d.rounded_rectangle([bx, yy + 52, bx + bw, yy + 116], 16, fill=(40, 40, 40))
            if v * k > 0: d.rounded_rectangle([bx, yy + 52, bx + max(34, bw * v * k), yy + 116], 16, fill=GOLD if i == len(el["ogeler"]) - 1 or len(el["ogeler"]) == 1 else (120, 96, 50))
            _yaz(im, (bx + bw, yy + 22), o.get("etiket") or f"%{int(o['deger'])}", inter("ExtraBold", 34), ACIK, min(1, k * 2), "rm")
    elif tip == "damga":
        k = ease((t - el["t0"]) / .35); olcek = 1.6 - .6 * k
        dogru = el["metin"] in ("GERÇEK", "DOĞRU")
        renk = GOLD if dogru else (205, 70, 60)
        f = pop(int(92 * olcek)); tw = d.textlength(el["metin"], font=f)
        x0, x1 = cx - tw/2 - 50*olcek, cx + tw/2 + 50*olcek; yc = y + 90
        d.rounded_rectangle([x0, yc - 75*olcek, x1, yc + 75*olcek], int(26*olcek), outline=renk, width=int(10*olcek))
        _yaz(im, (cx, yc), el["metin"], f, renk, k, "mm")
    elif tip == "halka":
        sure = el["sure"]; gecen = max(0, t - el["t0"]); k = min(1, gecen / sure)
        r = 230; yc = y + 260
        d.ellipse([cx - r, yc - r, cx + r, yc + r], outline=(45, 45, 45), width=22)
        if k > 0: d.arc([cx - r, yc - r, cx + r, yc + r], -90, -90 + 360 * k, fill=GOLD, width=22)
        kalan = max(1, math.ceil(sure - gecen)) if gecen < sure else 0
        _altin_tek(im, (cx, yc), str(kalan), pop(200), 1)
    elif tip == "logo":
        m = LOGO; im.paste(m, (cx - m.width // 2, y), m)
    elif tip == "buton":
        k = a; d.rounded_rectangle([cx - 210, y, cx + 210, y + 100], 50, fill=GOLD)
        _yaz(im, (cx, y + 50), "TAKİP ET", pop(54), KOYU, k, "mm")

def _yaz(im, xy, text, font, fill, alpha=1.0, anchor="mm"):
    if alpha >= .999: ImageDraw.Draw(im).text(xy, text, font=font, fill=fill, anchor=anchor); return
    d = ImageDraw.Draw(im); bb = [int(v) for v in d.textbbox(xy, text, font=font, anchor=anchor)]
    bb = [bb[0] - 2, bb[1] - 2, bb[2] + 2, bb[3] + 2]
    m = Image.new("L", (bb[2] - bb[0], bb[3] - bb[1]), 0)
    ImageDraw.Draw(m).text((xy[0] - bb[0], xy[1] - bb[1]), text, font=font, fill=int(255 * max(0, alpha)), anchor=anchor)
    im.paste(Image.new("RGB", m.size, fill), (bb[0], bb[1]), m)

def _altin_tek(im, xy, text, font, alpha=1.0, anchor="mm"):
    d = ImageDraw.Draw(im); bb = d.textbbox(xy, text, font=font, anchor=anchor)
    bb = [int(math.floor(bb[0])), int(math.floor(bb[1])), int(math.ceil(bb[2])), int(math.ceil(bb[3]))]
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    if w <= 0 or h <= 0: return
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((xy[0] - bb[0], xy[1] - bb[1]), text, font=font, fill=int(255 * alpha), anchor=anchor)
    im.paste(altin_doku(w, h), (bb[0], bb[1]), m)

# ----------------------------------------------------------------- şablonlar
def kanca_sahnesi(satirlar):
    satirlar = [tr_buyuk(s) for s in satirlar][:6]
    d = ImageDraw.Draw(Image.new("L", (1, 1))); boy = 120
    while boy > 72 and max(d.textlength(s.replace("*", ""), font=pop(boy)) for s in satirlar) > 940: boy -= 4
    els = [{"tip": "kanca", "metin": s, "boy": boy, "t0": .2 + i * .55} for i, s in enumerate(satirlar)]
    sh = sahne_kur(els, boslik=26, ust_sinir=430, alt_sinir=1500)
    sh["sure"] = max(4.2, .2 + .55 * len(satirlar) + 2.2); return sh

def kapanis_sahnesi(soru, alt):
    els = [{"tip": "kanca", "metin": tr_buyuk(soru), "boy": 96},
           {"tip": "metin", "metin": alt, "stil": "yan"},
           {"tip": "logo", "t0": 1.6}, {"tip": "kulp", "t0": 2.0}, {"tip": "buton", "t0": 2.6}]
    return sahne_kur(els, sabit_sure=7.0, ust_sinir=420)

def sahneler_olustur(s):
    sab = s["sablon"]; out = [kanca_sahnesi(s["kanca"])]
    if sab == "liste":
        et = tr_buyuk(s.get("etiket", "KURAL"))
        for i, m in enumerate(s["maddeler"], 1):
            els = [{"tip": "pill", "metin": f"{et} {i}"}, {"tip": "baslik", "metin": tr_buyuk(m["baslik"])}, {"tip": "cizgi"}]
            if m.get("alinti"):
                al = m["alinti"]; els.append({"tip": "metin", "metin": "“" + al["metin"].strip("“”\" ") + "”", "stil": "soz", "altin": True})
                els.append({"tip": "metin", "metin": al.get("kisi", ""), "stil": "yan"})
            if m.get("cubuk"): els.append({"tip": "cubuk", "ogeler": m["cubuk"][:3]})
            for st in m.get("satirlar", [])[:3]: els.append({"tip": "metin", "metin": st, "stil": "ana"})
            if m.get("vurgu"): els.append({"tip": "metin", "metin": tr_buyuk(m["vurgu"]), "stil": "vurgu"})
            out.append(sahne_kur(els))
    elif sab == "soz":
        els = [{"tip": "pill", "metin": "GÜNÜN SÖZÜ"},
               {"tip": "metin", "metin": "“" + s["soz"].strip("“”\" ") + "”", "stil": "soz", "t0": .7},
               {"tip": "metin", "metin": "— " + tr_buyuk(s["kisi"]), "stil": "yan", "bekle": .3}]
        out.append(sahne_kur(els, bekle=2.2))
        els = [{"tip": "pill", "metin": "KİMDİR?"}, {"tip": "baslik", "metin": tr_buyuk(s["kisi"])}, {"tip": "cizgi"}]
        els += [{"tip": "metin", "metin": x, "stil": "ana"} for x in s["hikaye"][:4]]
        out.append(sahne_kur(els))
        els = [{"tip": "pill", "metin": "BUGÜN İÇİN"}]
        els += [{"tip": "metin", "metin": tr_buyuk(x), "stil": "vurgu"} for x in s["ders"][:1]]
        els += [{"tip": "metin", "metin": x, "stil": "ana"} for x in s["ders"][1:3]]
        out.append(sahne_kur(els, bekle=2.0))
    elif sab == "mit":
        for i, m in enumerate(s["maddeler"], 1):
            els = [{"tip": "pill", "metin": f"İDDİA {i}"},
                   {"tip": "metin", "metin": "“" + m["iddia"].strip("“”\" ") + "”", "stil": "iddia"},
                   {"tip": "damga", "metin": "GERÇEK" if m["sonuc"].upper().startswith("G") or m["sonuc"].upper().startswith("D") else "MİT", "bekle": 1.2}]
            els += [{"tip": "metin", "metin": x, "stil": "ana"} for x in m["aciklama"][:3]]
            out.append(sahne_kur(els))
    elif sab == "egzersiz":
        els = [{"tip": "pill", "metin": "1 DAKİKALIK UYGULAMA"}, {"tip": "baslik", "metin": tr_buyuk(s["ad"])}, {"tip": "cizgi"}]
        els += [{"tip": "metin", "metin": x, "stil": "ana"} for x in s["giris"][:3]]
        els.append({"tip": "metin", "metin": "Şimdi benimle birlikte yap.", "stil": "vurgu"})
        out.append(sahne_kur(els))
        adimlar = s["adimlar"][:4]; tur = max(1, min(3, int(s.get("tur", 2))))
        for k in range(tur):
            for j, ad in enumerate(adimlar, 1):
                sure = max(2, min(8, float(ad["sure"])))
                els = [{"tip": "pill", "metin": f"TUR {k+1}/{tur} · ADIM {j}", "t0": 0},
                       {"tip": "metin", "metin": tr_buyuk(ad["metin"]), "stil": "buyuk", "altin": True, "t0": 0.05},
                       {"tip": "halka", "sure": sure, "t0": .3}]
                out.append(sahne_kur(els, sabit_sure=sure + .5))
        els = [{"tip": "pill", "metin": "NEDEN İŞE YARAR?"}]
        els += [{"tip": "metin", "metin": x, "stil": "ana"} for x in s["fayda"][:3]]
        out.append(sahne_kur(els))
    else:
        raise ValueError("bilinmeyen şablon " + sab)
    k = s.get("kapanis") or {}
    out.append(kapanis_sahnesi(k.get("soru", "Sen hangisini *uyguluyorsun?*"), k.get("alt", "Yorumlara yaz, birlikte büyüyelim.")))
    t = 0
    for sh in out: sh["bas"] = t; t += sh["sure"]
    return out, t

# ----------------------------------------------------------------- kare çizimi
Z = None; LOGO = None; ISARET = None; TOZ = None; SAHNELER = None; TOPLAM = 0
def _hazir():
    global Z, LOGO, ISARET, TOZ
    if Z is None:
        Z = zemin(); LOGO = isaret(220); ISARET = isaret(84)
        r = random.Random(5); TOZ = [(r.random(), r.random(), r.uniform(1, 3), r.uniform(.01, .04), r.uniform(.2, .7)) for _ in range(55)]

def kare(i):
    t = i / FPS
    sh = SAHNELER[-1]
    for s in SAHNELER:
        if s["bas"] <= t < s["bas"] + s["sure"]: sh = s; break
    ts = t - sh["bas"]
    im = Z.copy(); d = ImageDraw.Draw(im)
    for el in sh["els"]: el_ciz(im, d, el, ts)
    f = min(1, ts / .25, max(0, (sh["sure"] - ts) / .3)) if sh is not SAHNELER[-1] else min(1, ts / .25)
    if f < 1: im = Image.blend(Z, im, max(0, f)); d = ImageDraw.Draw(im)
    for x, y, r, v, a in TOZ:
        yy = (y - t * v) % 1; c = int(200 * a); d.ellipse([x*W - r, yy*H - r, x*W + r, yy*H + r], fill=(c, int(c*.8), int(c*.4)))
    im.paste(ISARET, (70, 110), ISARET)
    d.text((170, 124), "HEDEFLERİN", font=inter("ExtraBold", 30), fill=(240, 240, 240))
    _altin_tek(im, (170, 166), "Y O L U N D A", inter("SemiBold", 24), 1, "lm")
    d.rounded_rectangle([70, 70, W - 70, 76], 3, fill=(40, 40, 40))
    d.rounded_rectangle([70, 70, 70 + (W - 140) * min(1, t / TOPLAM), 76], 3, fill=GOLD)
    return im

def _kare_bayt(i): return kare(i).tobytes()

# ----------------------------------------------------------------- müzik
def muzik(sure, yol, gecisler, tohum):
    SR = 44100; rng = np.random.default_rng(tohum); n = int(SR * (sure + .5)); out = np.zeros((n, 2))
    bpm = int(rng.integers(84, 101)); beat = 60 / bpm; olcu = beat * 4
    ilerlemeler = [[0, 8, 3, 10], [0, 5, 8, 7], [0, 3, 8, 10], [0, 8, 5, 10], [0, 10, 8, 7]]
    il = ilerlemeler[int(rng.integers(len(ilerlemeler)))]; kok = 220 * 2 ** (int(rng.integers(-4, 3)) / 12)
    def akor(adim):
        f0 = kok * 2 ** (adim / 12); minor = adim in (0, 5)
        return [f0, f0 * 2 ** ((3 if minor else 4) / 12), f0 * 2 ** (7 / 12)]
    for i in range(int(sure / (olcu * 2)) + 2):
        a = akor(il[i % 4]); s = int(i * olcu * 2 * SR); L = min(int(olcu * 2 * SR), n - s)
        if L <= 0: break
        tt = np.arange(L) / SR; pad = np.zeros(L)
        for f in a:
            for det in (-.6, .6): pad += np.sin(2*np.pi*(f/2 + det)*tt) + .3*np.sin(2*np.pi*(f + det)*tt)
        e = np.minimum(1, tt / 1.2) * np.minimum(1, (L / SR - tt) / .8); pad *= e * .05
        out[s:s+L, 0] += pad; out[s:s+L, 1] += np.roll(pad, 120)
        out[s:s+L] += (np.sin(2*np.pi*a[0]/4*tt) * .22 * e)[:, None]
    gur = rng.standard_normal(SR); gur = np.diff(gur, prepend=0); gur /= np.abs(gur).max()
    bas = min(6.0, gecisler[1] if len(gecisler) > 1 else 6.0); k = 0
    while True:
        tm = bas + k * beat
        if tm > sure - 4: break
        s = int(tm * SR); L = int(.45 * SR); tt = np.arange(L) / SR; L = min(L, n - s)
        if k % 2 == 0: out[s:s+L] += (np.sin(2*np.pi*(45 + 90*np.exp(-tt*30))*tt) * np.exp(-tt*7) * .55)[:L, None]
        else:
            L2 = min(int(.25 * SR), n - s); out[s:s+L2] += (gur[:L2] * np.exp(-np.arange(L2)/SR*18) * .12)[:, None]
        for h in (0, .5):
            s2 = int((tm + h * beat) * SR); L3 = int(.06 * SR)
            if s2 + L3 < n:
                hh = gur[1000:1000+L3] * np.exp(-np.arange(L3)/SR*60) * .05; out[s2:s2+L3, 0] += hh; out[s2:s2+L3, 1] += hh * .7
        k += 1
    for tm in gecisler[1:]:
        s = int((tm - .5) * SR); L = int(.6 * SR)
        if 0 <= s and s + L < n: out[s:s+L] += (gur[:L] * np.sin(np.linspace(0, np.pi, L)) * .08)[:, None]
    f = np.ones(n); f[:SR*2] = np.linspace(0, 1, SR*2); f[-SR*3:] = np.linspace(1, 0, SR*3); out *= f[:, None]
    out = np.tanh(out * 1.2); out /= np.abs(out).max(); out *= .85
    with wave.open(yol, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype("<i2").tobytes())
    return bpm

# ----------------------------------------------------------------- video
def ffmpeg_yolu():
    p = shutil.which("ffmpeg")
    if p: return p
    import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()

def video_uret(senaryo, cikti, onizleme=None):
    global SAHNELER, TOPLAM
    _hazir(); SAHNELER, TOPLAM = sahneler_olustur(senaryo)
    os.makedirs(os.path.dirname(os.path.abspath(cikti)), exist_ok=True)
    wav = cikti + ".wav"
    muzik(TOPLAM, wav, [s["bas"] for s in SAHNELER], abs(hash(json.dumps(senaryo, ensure_ascii=False))) % 10**6)
    if onizleme:
        anlar = [s["bas"] + s["sure"] * .8 for s in SAHNELER]
        kucuk = [kare(int(a * FPS)).resize((270, 480)) for a in anlar]
        m = Image.new("RGB", (276 * len(kucuk), 480), "gray")
        for i, k in enumerate(kucuk): m.paste(k, (i * 276, 0))
        m.save(onizleme)
    n = int(TOPLAM * FPS)
    cmd = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cikti]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import multiprocessing as mp
    with mp.get_context("fork").Pool(os.cpu_count() or 2) as havuz:
        for b in havuz.imap(_kare_bayt, range(n), chunksize=8): p.stdin.write(b)
    p.stdin.close(); p.wait(); os.remove(wav)
    if p.returncode: raise RuntimeError("ffmpeg hata verdi")
    return TOPLAM

# ----------------------------------------------------------------- kaynaklar (Vikipedi / Vikisöz)
def _get(url, params):
    import requests
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.ok: return r.json()
        except Exception as e:
            print("istek hatası:", e)
        time.sleep(2)
    return None

def vikipedi_metin(baslik):
    j = _get("https://tr.wikipedia.org/w/api.php", {"action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1,
                                                     "titles": baslik, "format": "json", "formatversion": 2})
    try:
        p = j["query"]["pages"][0]
        if p.get("missing"): return None, None
        return p["title"], p.get("extract", "")
    except Exception:
        return None, None

def vikisoz_metin(baslik):
    j = _get("https://tr.wikiquote.org/w/api.php", {"action": "parse", "page": baslik, "prop": "wikitext", "redirects": 1,
                                                     "format": "json", "formatversion": 2})
    try:
        wt = j["parse"]["wikitext"]; ad = j["parse"]["title"]
    except Exception:
        return None, None
    wt = re.sub(r"\{\{[^{}]*\}\}", "", wt); wt = re.sub(r"\{\{[^{}]*\}\}", "", wt)
    wt = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", wt); wt = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", wt)
    wt = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", wt, flags=re.S); wt = re.sub(r"<[^>]+>", "", wt)
    wt = wt.replace("'''", "").replace("''", "")
    return ad, wt

def norm(m):
    m = m.replace("İ", "i").replace("I", "ı").lower()
    m = unicodedata.normalize("NFC", m)
    m = re.sub(r"[^\w\s%]", " ", m); return re.sub(r"\s+", " ", m).strip()

def sayilar(m): return set(re.findall(r"\d+(?:[.,]\d+)?", m.replace("*", "")))

# ----------------------------------------------------------------- Claude
def claude(istem, max_tokens=4000):
    import requests
    for deneme in range(3):
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=180, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": istem}]})
        if not r.ok:
            print("Claude hata:", r.status_code, r.text[:300]); time.sleep(5); continue
        metin = "".join(b.get("text", "") for b in r.json().get("content", []))
        dec = json.JSONDecoder()
        for i, ch in enumerate(metin):
            if ch in "[{":
                try: return dec.raw_decode(metin[i:])[0]
                except ValueError: continue
        print("JSON bulunamadı:", metin[:300])
    raise RuntimeError("Claude yanıtı alınamadı")

KITLE = ("Instagram hesabı: HEDEFLERİN YOLUNDA (@hedeflerinyolunda). Hedef kitle: 16-28 yaş, hırslı Türk gençleri. "
         "Ton: kısa, güçlü, 'milyarder zihniyeti' havasında ama gerçekçi. Yasak: hızlı zengin olma vaadi, kumar/kripto/yatırım tavsiyesi, "
         "tıbbi teşhis/tedavi iddiası, siyaset, din tartışması, yaşayan siyasetçiler. Dil: doğal, akıcı, kusursuz Türkçe.")

def aday_iste(sablon, kullanilan):
    ne = {"liste": "Ortak bir temaya bağlanabilecek 3 psikoloji / verimlilik / davranış bilimi kavramı (ör. tema 'Zamanını yöneten 3 yasa': Pareto ilkesi, Parkinson yasası, Eisenhower matrisi). Her aday için 'tema' ve 3 Vikipedi madde başlığından oluşan 'sayfalar' ver.",
          "mit": "Gençler arasında yaygın 3 yanlış inanç ya da şaşırtıcı psikoloji gerçeği; her biri bir Türkçe Vikipedi maddesiyle doğrulanabilmeli. Her aday için 'tema' ve 3 madde başlığından oluşan 'sayfalar' ver.",
          "soz": "Disiplin, azim, odak veya başarı üzerine güçlü sözleri olan, tr.wikiquote.org'da (Vikisöz) sayfası OLAN tanınmış kişiler (filozof, bilim insanı, yazar, sporcu, girişimci; yaşayan siyasetçi değil). Her aday için 'sayfalar': [kişinin Vikisöz sayfa başlığı].",
          "egzersiz": "Bilimsel temeli olan, 1 dakikada uygulanabilecek nefes, odak veya zihin teknikleri (ör. Kutu nefesi, Diyafram nefesi, Pomodoro tekniği). Her aday için 'tema' ve 'sayfalar': [Vikipedi madde başlığı]."}[sablon]
    istem = (f"{KITLE}\n\nGörev: {ne}\nSadece tr.wikipedia.org / tr.wikiquote.org'da GERÇEKTEN VAR OLAN tam başlıkları kullan. "
             f"Daha önce kullanılanları seçme: {json.dumps(kullanilan[-80:], ensure_ascii=False)}\n"
             "8 aday ver. Sadece JSON dizi döndür: [{\"tema\": \"...\", \"sayfalar\": [\"...\"]}]")
    return claude(istem, 2000)

SEMA = {
 "liste": '{"sablon":"liste","konu":"tema adı","etiket":"YASA|KURAL|TAKTİK|ETKİ","kanca":["4-6 kısa satır, her biri en fazla 16 karakter; vurgu kelimeleri *yıldızla*"],'
          '"maddeler":[{"baslik":"en fazla 20 karakter","kaynak":"Vikipedi başlığı","alinti":{"metin":"isteğe bağlı, kaynakta geçen kısa ifade","kisi":"kim, yıl"} veya null,'
          '"cubuk":[{"ad":"ÇABA","deger":20},{"ad":"SONUÇ","deger":80}] veya null (yalnız kaynakta açıkça sayı varsa),'
          '"satirlar":["2-3 cümle, her biri en fazla 80 karakter; *vurgu* olabilir"],"vurgu":"en fazla 36 karakter, uygulanabilir eylem"} x3],'
          '"kapanis":{"soru":"en fazla 26 karakter, *vurgu*","alt":"yorum çağrısı, en fazla 45 karakter"},"aciklama":"Instagram açıklaması: 2-3 cümle + soru","etiketler":["#..." 6-8 adet]}',
 "mit": '{"sablon":"mit","konu":"tema","kanca":["4-6 kısa satır, en fazla 16 karakter, *vurgu*"],"maddeler":[{"iddia":"en fazla 60 karakter","sonuc":"MİT|GERÇEK","kaynak":"Vikipedi başlığı",'
        '"aciklama":["2-3 cümle, her biri en fazla 80 karakter"]} x3],"kapanis":{...},"aciklama":"...","etiketler":[...]}',
 "soz": '{"sablon":"soz","konu":"kişi adı","kaynak":"Vikisöz sayfa başlığı","kanca":["4-6 kısa satır"],"soz":"VİKİSÖZ METNİNDEN KELİMESİ KELİMESİNE kopyalanmış söz (en fazla 160 karakter); en güçlü 1-3 kelimeyi *yıldızla*",'
        '"kisi":"kişinin adı","hikaye":["kişinin hayatından 3-4 kısa gerçek, her biri en fazla 80 karakter, yalnız Vikipedi metninden"],'
        '"ders":["en fazla 36 karakterlik güçlü ders cümlesi","1-2 açıklama cümlesi"],"kapanis":{...},"aciklama":"...","etiketler":[...]}',
 "egzersiz": '{"sablon":"egzersiz","konu":"teknik adı","kaynak":"Vikipedi başlığı","ad":"en fazla 20 karakter","kanca":["4-6 kısa satır"],"giris":["2-3 cümle, en fazla 80 karakter"],'
             '"adimlar":[{"metin":"en fazla 18 karakter, ör. Nefes al","sure":4}] (2-4 adım, süre 2-8 sn),"tur":2,"fayda":["2-3 cümle, yalnız kaynakta yazanlar, tıbbi iddia yok"],"kapanis":{...},"aciklama":"...","etiketler":[...]}',
}

def senaryo_iste(sablon, kaynaklar):
    metinler = "\n\n".join(f"=== KAYNAK: {ad} ({tur}) ===\n{m[:9000]}" for ad, tur, m in kaynaklar)
    istem = (f"{KITLE}\n\n1-1,5 dakikalık özgün bir Reels videosunun ekran metinlerini yaz. Şablon: {sablon}.\n"
             "KURALLAR:\n- Her bilgi, sayı, tarih ve isim YALNIZCA aşağıdaki kaynak metinlerde açıkça yazanlardan gelsin. Kaynakta olmayan hiçbir şeyi ekleme.\n"
             "- Söz varsa, kaynak metinde nasıl yazıyorsa öyle kopyala (kelimeler aynı).\n"
             "- Başka bir hesabın içeriğini kopyalama; cümleler özgün olsun.\n- Kanca ilk 2 saniyede merak uyandırsın.\n"
             f"- Sadece şu yapıda JSON döndür:\n{SEMA[sablon]}\n\n{metinler}")
    return claude(istem, 4000)

def denetle(senaryo, kaynaklar):
    """Kaynaklarda olmayan iddia var mı? Sayılar ve söz kelimesi kelimesine kontrol + Claude denetimi."""
    kaynak_birlesik = " ".join(m for _, _, m in kaynaklar)
    nk = norm(kaynak_birlesik)
    if senaryo.get("sablon") == "soz":
        soz = norm(senaryo["soz"].replace("*", ""))
        if len(soz) < 12 or soz not in nk:
            return False, "söz Vikisöz metninde birebir bulunamadı"
    ekran = json.dumps({k: v for k, v in senaryo.items() if k not in ("aciklama", "etiketler")}, ensure_ascii=False)
    serbest = {str(i) for i in range(0, 11)} | {"24", "60", "100", "1000"}
    for s in sayilar(ekran) - serbest:
        if s not in kaynak_birlesik and s.replace(",", ".") not in kaynak_birlesik and s.replace(".", ",") not in kaynak_birlesik:
            return False, f"kaynakta olmayan sayı: {s}"
    sonuc = claude("Aşağıdaki video metnindeki HER bilgi iddiasını kaynak metinlerle karşılaştır. Motivasyon cümleleri ve öneriler serbesttir; "
                   "ama olgu iddiaları (tarih, isim, sayı, bilimsel sonuç, kim ne dedi) kaynaklarda açıkça desteklenmeli. Ayrıca yasaklı içerik "
                   f"(hızlı zenginlik vaadi, tıbbi iddia, siyaset) var mı bak. Türkçe dil hatası var mı bak.\n\nVİDEO:\n{ekran}\n\nKAYNAKLAR:\n" +
                   "\n\n".join(f"=== {a} ===\n{m[:9000]}" for a, _, m in kaynaklar) +
                   '\n\nSadece JSON döndür: {"gecerli": true/false, "sorunlar": ["..."]}', 1500)
    if not sonuc.get("gecerli"):
        return False, "; ".join(sonuc.get("sorunlar", []))[:300]
    return True, ""

def bicim_denetle(s):
    try:
        assert 3 <= len(s["kanca"]) <= 6
        if s["sablon"] in ("liste", "mit"): assert len(s["maddeler"]) == 3
        if s["sablon"] == "egzersiz": assert 2 <= len(s["adimlar"]) <= 4
        if s["sablon"] == "soz": assert s["soz"] and s["hikaye"] and s["ders"]
        assert s.get("aciklama")
    except Exception as e:
        return False
    return True

# ----------------------------------------------------------------- durum
def durum_oku():
    if os.path.exists(DURUM):
        with open(DURUM, encoding="utf-8") as f: return json.load(f)
    return {"sayac": 0, "paylasilanlar": []}
def durum_yaz(d):
    with open(DURUM, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

def hazirla():
    d = durum_oku(); sablon = SIRA[d["sayac"] % len(SIRA)]
    kullanilan = [p["konu"] for p in d["paylasilanlar"]] + [k for p in d["paylasilanlar"] for k in p.get("kaynaklar", [])]
    print("Şablon:", sablon)
    for tur in range(2):
        adaylar = aday_iste(sablon, kullanilan)
        for aday in adaylar[:8]:
            kaynaklar = []
            for b in aday.get("sayfalar", [])[:3]:
                if b in kullanilan: kaynaklar = []; break
                if sablon == "soz":
                    ad, m = vikisoz_metin(b)
                    if not m or len(m) < 400: kaynaklar = []; break
                    kaynaklar.append((ad, "Vikisöz", m))
                    ad2, m2 = vikipedi_metin(b)
                    if m2: kaynaklar.append((ad2, "Vikipedi", m2))
                else:
                    ad, m = vikipedi_metin(b)
                    if not m or len(m) < 800: kaynaklar = []; break
                    kaynaklar.append((ad, "Vikipedi", m))
            if not kaynaklar: print("aday atlandı:", aday); continue
            try:
                s = senaryo_iste(sablon, kaynaklar)
            except Exception as e:
                print("senaryo hatası:", e); continue
            s["sablon"] = sablon
            if not bicim_denetle(s): print("biçim hatalı"); continue
            ok, neden = denetle(s, kaynaklar)
            if not ok: print("DOĞRULAMA REDDETTİ:", aday.get("tema"), "-", neden); continue
            s["_kaynaklar"] = [(a, t) for a, t, _ in kaynaklar]
            os.makedirs(CIKTI, exist_ok=True)
            sure = video_uret(s, os.path.join(CIKTI, "reels.mp4"), os.path.join(CIKTI, "onizleme.jpg"))
            with open(os.path.join(CIKTI, "bekleyen.json"), "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False, indent=2)
            print(f"Hazır: {s.get('konu')} ({sure:.1f} sn)"); return True
    print("Uygun içerik bulunamadı; bu tur paylaşım yok."); return False

def aciklama_yap(s):
    kay = []
    for ad, tur in s.get("_kaynaklar", []):
        site = "tr.wikiquote.org" if tur == "Vikisöz" else "tr.wikipedia.org"
        kay.append(f"{tur}: https://{site}/wiki/{quote(ad.replace(' ', '_'))}")
    et = " ".join(s.get("etiketler", [])[:8])
    return (s["aciklama"].strip() + "\n\n📌 Kaydet, sonra tekrar izle.\n👉 " + KULLANICI + " ile her gün bir adım ileri.\n\n"
            "Kaynak: " + " | ".join(kay) + "\n\n" + et)[:2150]

# ----------------------------------------------------------------- Instagram
def paylas():
    import requests
    yol = os.path.join(CIKTI, "bekleyen.json"); vid = os.path.join(CIKTI, "reels.mp4")
    if not os.path.exists(yol): print("Bekleyen video yok."); return
    s = json.load(open(yol, encoding="utf-8")); aciklama = aciklama_yap(s)
    if str(os.environ.get("DRY_RUN", "")).lower() in ("1", "true", "evet"):
        print("DRY_RUN: paylaşılmadı.\n" + aciklama); return
    tok = os.environ["IG_ACCESS_TOKEN"]; uid = os.environ["IG_USER_ID"]
    r = requests.post(f"{IG}/{IG_SURUM}/{uid}/media", data={"media_type": "REELS", "upload_type": "resumable", "caption": aciklama,
                      "share_to_feed": "true", "thumb_offset": "3000", "access_token": tok}, timeout=60)
    j = r.json(); print("kap:", j)
    if "id" not in j: raise RuntimeError(j)
    cid = j["id"]; uri = j.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{IG_SURUM}/{cid}"
    boyut = os.path.getsize(vid)
    with open(vid, "rb") as f:
        r = requests.post(uri, data=f, timeout=600, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(boyut)})
    print("yükleme:", r.status_code, r.text[:300])
    if not r.ok: raise RuntimeError("video yüklenemedi")
    for _ in range(60):
        time.sleep(10)
        st = requests.get(f"{IG}/{IG_SURUM}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30).json()
        print("durum:", st)
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") in ("ERROR", "EXPIRED"): raise RuntimeError(st)
    else:
        raise RuntimeError("işleme zaman aşımı")
    p = requests.post(f"{IG}/{IG_SURUM}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60).json()
    print("yayın:", p)
    if "id" not in p: raise RuntimeError(p)
    link = ""
    try:
        link = requests.get(f"{IG}/{IG_SURUM}/{p['id']}", params={"fields": "permalink", "access_token": tok}, timeout=30).json().get("permalink", "")
    except Exception: pass
    d = durum_oku(); d["sayac"] += 1
    d["paylasilanlar"].append({"tarih": datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M"), "sablon": s["sablon"],
                               "konu": s.get("konu", ""), "kaynaklar": [a for a, _ in s.get("_kaynaklar", [])], "id": p["id"], "link": link})
    durum_yaz(d); os.remove(yol); print("Paylaşıldı:", link)

if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 else ""
    if k == "hazirla": sys.exit(0 if hazirla() else 0)
    elif k == "paylas": paylas()
    elif k == "ornek":
        s = json.load(open(sys.argv[2], encoding="utf-8"))
        out = sys.argv[3] if len(sys.argv) > 3 else "ornek.mp4"
        print("süre:", video_uret(s, out, out.replace(".mp4", "_onizleme.jpg")))
    else: print(__doc__)
