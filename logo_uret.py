"""OZA BİLGİ logolarını üretir: python logo_uret.py  -> logo/ klasörü"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = Path(__file__).resolve().parent
CIKTI = KOK / "logo"
S = 4  # kenar yumuşatma için 4 kat büyük çiz, sonra küçült

LACIVERT_UST = (22, 28, 62)
LACIVERT_ALT = (7, 9, 24)
SARI = (255, 200, 61)
BEYAZ = (255, 255, 255)


def font(agirlik, boyut):
    return ImageFont.truetype(str(KOK / f"Inter-{agirlik}.otf"), boyut)


def yildiz(cx, cy, R, r, aci=-90):
    """4 köşeli parıltı."""
    nok = []
    for i in range(8):
        a = math.radians(aci + i * 45)
        rr = R if i % 2 == 0 else r
        nok.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return nok


def isaret(boyut, halka=BEYAZ, kivilcim=SARI):
    """O harfi halkası + sağ üstte açıklıkta sarı bilgi kıvılcımı. Şeffaf zemin."""
    n = boyut * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = n / 2
    R = n * 0.40           # halkanın dış yarıçapı
    k = n * 0.135          # halka kalınlığı
    # halka: açıklığı sağ üstte (-45°) bırak
    bas, son = -45 + 38, -45 - 38 + 360
    kutu = [cx - R, cy - R, cx + R, cy + R]
    d.arc(kutu, bas, son, fill=halka, width=int(k))
    # halka uçlarını yuvarla
    ro = R - k / 2
    for a in (bas, son):
        x = cx + ro * math.cos(math.radians(a))
        y = cy + ro * math.sin(math.radians(a))
        d.ellipse([x - k / 2, y - k / 2, x + k / 2, y + k / 2], fill=halka)
    # kıvılcım: açıklığın biraz dışında
    kx = cx + ro * 1.02 * math.cos(math.radians(-45))
    ky = cy + ro * 1.02 * math.sin(math.radians(-45))
    d.polygon(yildiz(kx, ky, n * 0.16, n * 0.05), fill=kivilcim)
    return im.resize((boyut, boyut), Image.LANCZOS)


def zemin(w, h, yuvarlak=0):
    grad = Image.linear_gradient("L").resize((w, h))
    im = Image.composite(Image.new("RGB", (w, h), LACIVERT_ALT),
                         Image.new("RGB", (w, h), LACIVERT_UST), grad).convert("RGBA")
    isik = Image.new("L", (w, h), 0)
    ImageDraw.Draw(isik).ellipse([w * 0.45, -h * 0.35, w * 1.35, h * 0.55], fill=70)
    isik = isik.filter(ImageFilter.GaussianBlur(w * 0.14))
    im = Image.composite(Image.new("RGBA", (w, h), (90, 105, 255, 255)), im, isik)
    if yuvarlak:
        maske = Image.new("L", (w * S, h * S), 0)
        ImageDraw.Draw(maske).rounded_rectangle([0, 0, w * S, h * S], yuvarlak * S, fill=255)
        im.putalpha(maske.resize((w, h), Image.LANCZOS))
    return im


def harf_aralikli_genislik(d, metin, f, aralik):
    return sum(d.textlength(c, font=f) for c in metin) + aralik * (len(metin) - 1)


def harf_aralikli(d, x, y, metin, f, renk, aralik):
    for c in metin:
        d.text((x, y), c, font=f, fill=renk)
        x += d.textlength(c, font=f) + aralik


def yazi_logo(yuk, oza_renk, bilgi_renk, halka_renk):
    """Yatay logo: [işaret] OZA | BİLGİ, şeffaf zemin, yükseklik = yuk."""
    H = yuk * S
    f1 = font("ExtraBold", int(H * 0.62))
    f2 = font("Bold", int(H * 0.30))
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w_oza = tmp.textlength("OZA", font=f1)
    ar = int(H * 0.075)
    w_bilgi = harf_aralikli_genislik(tmp, "BİLGİ", f2, ar)
    bosluk = H * 0.22
    W = int(H + bosluk + w_oza + bosluk * 0.9 + H * 0.05 + bosluk * 0.9 + w_bilgi + H * 0.05)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    isr = isaret(H, halka=halka_renk)
    im.alpha_composite(isr, (0, 0))
    d = ImageDraw.Draw(im)
    x = H + bosluk
    ust = d.textbbox((0, 0), "OZA", font=f1)
    y = (H - (ust[3] - ust[1])) / 2 - ust[1]
    d.text((x, y), "OZA", font=f1, fill=oza_renk)
    x += w_oza + bosluk * 0.9
    d.rectangle([x, H * 0.26, x + H * 0.05, H * 0.74], fill=bilgi_renk)
    x += H * 0.05 + bosluk * 0.9
    b = d.textbbox((0, 0), "BİLGİ", font=f2)
    y2 = (H - (b[3] - b[1])) / 2 - b[1] + H * 0.02
    harf_aralikli(d, x, y2, "BİLGİ", f2, bilgi_renk, ar)
    return im.resize((W // S, yuk), Image.LANCZOS)


def main():
    CIKTI.mkdir(exist_ok=True)

    # 1) Instagram profil fotoğrafı (daire kırpmaya uygun)
    p = zemin(1080, 1080)
    p.alpha_composite(isaret(640), (220, 200))
    d = ImageDraw.Draw(p)
    f = font("Bold", 64)
    w = harf_aralikli_genislik(d, "OZA BİLGİ", f, 14)
    harf_aralikli(d, (1080 - w) / 2, 860, "OZA BİLGİ", f, BEYAZ, 14)
    p.convert("RGB").save(CIKTI / "profil_fotografi.png")

    # 2) Uygulama ikonu tarzı yuvarlak köşeli işaret
    ikon = zemin(1024, 1024, yuvarlak=230)
    ikon.alpha_composite(isaret(720), (152, 152))
    ikon.save(CIKTI / "ikon.png")

    # 3) Yatay logo - koyu zemin için (beyaz yazı), şeffaf
    yazi_logo(300, BEYAZ, SARI, BEYAZ).save(CIKTI / "logo_beyaz.png")
    # 4) Yatay logo - açık zemin için (lacivert yazı), şeffaf
    yazi_logo(300, LACIVERT_UST, (230, 160, 20), LACIVERT_UST).save(CIKTI / "logo_lacivert.png")

    # 5) Kapak / önizleme: koyu zeminde yatay logo
    kapak = zemin(1600, 900)
    lg = yazi_logo(260, BEYAZ, SARI, BEYAZ)
    kapak.alpha_composite(lg, ((1600 - lg.width) // 2, (900 - lg.height) // 2 - 40))
    d = ImageDraw.Draw(kapak)
    f = font("Medium", 40)
    t = "Her gün eğlenceli ve önemli bilgiler"
    d.text(((1600 - d.textlength(t, font=f)) / 2, 640), t, font=f, fill=(190, 200, 228))
    kapak.convert("RGB").save(CIKTI / "kapak.png")
    print("ok")


if __name__ == "__main__":
    main()
