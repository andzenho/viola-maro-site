# -*- coding: utf-8 -*-
"""Оформление --theme barhat: чёрное с золотом.

Имя флага осталось от первой пробы. Нынешний вид собран по образцам, которые
прислал пользователь 13.10.2026 (тёмные лендинги экспертов): вся страница
тёмная, эксперт внизу растворяется в фоне, заголовки антиквой с металлическим
отливом, золотые кнопки и плитки, карточки тёмные с тонкой золотой линией.
Тёмная блуза Виолы на таком фоне уходит в тень, светятся лицо и волосы.

Работает поверх оформления «море»: сборщик сначала делает всё, что делает
для --theme more (те же блоки, те же слова, те же формы), а потом этот
модуль перекрашивает страницу и добавляет свой слой стилей. Тексты
не меняются.

Картинки вставляются позже. Файлы кладутся в build-assets/tema-barhat/
под именами из SLOTS; пока файла нет, на его месте фон из градиента.
"""

import os
import re

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-assets", "tema-barhat")

# имя в стилях → файл в build-assets/tema-barhat/
SLOTS = {
    "hero-d": "hero-desktop.jpg",   # Виола в сцене, горизонтальная 2400×1400
    "hero-m": "hero-mobile.jpg",    # Виола в сцене, вертикальная 1080×1600
    "lenta":  "lenta.png",          # золотая лента на прозрачном фоне
    "barhat": "barhat.jpg",         # красный шёлк для красных блоков
    "mk":     "mk.jpg",             # зал со сценой, мастер-класс
    "final":  "final.jpg",          # приоткрытая дверь, последний призыв
    "fon":    "fon.jpg",            # тёмный интерьер без людей, за фигурой
}


def est(name):
    return os.path.exists(os.path.join(DIR, SLOTS[name]))


# ── цвета: «море» → чёрное с золотом ──
#
# Страница становится тёмной, поэтому один и тот же цвет «моря» переводится
# по-разному: стоит он в фоне (background, border, тень) или в тексте (color).
# Белый фон карточки становится тёмным, а белый текст остаётся белым.

FG = {
    # тёмный текст → светлый
    "#18213A": "#F4EFE7", "#2B3550": "#DED6CB", "#465068": "#BDB3A7",
    "#4A546C": "#B3A99D", "#5F687E": "#A39A8F", "#9AA3B5": "#857C73",
    # синий и красный текст → золото
    "#1F4C97": "#E3C58A", "#143A85": "#E3C58A", "#0F2A66": "#E3C58A",
    "#1F56A6": "#E3C58A", "#102F73": "#E3C58A",
    # красный переводится в то же золото, но другой записью: стили «моря»
    # различают синие галочки и красные метки по цвету в разметке
    "#B01E22": "#E2C489", "#B3161F": "#E2C489", "#8A2B2B": "#F0B9A8",
    "#F0B13F": "#E3C58A", "#E39A2B": "#D9B97A", "#B07A1E": "#D9B97A",
    "#F6CF7A": "#F0D9A6", "#FBE3B0": "#F0D9A6", "#3A2A05": "#1A1410",
}

BG = {
    # белое и бумага → тёмные поверхности
    "#FFFFFF": "#171311", "#FDFAF6": "#171311", "#FFFBF5": "#171311", "#FDF9F3": "#171311",
    "#FBF6EC": "#0D0A09", "#FBF5EC": "#0D0A09", "#FBF6EE": "#0D0A09",
    "#FBF6EF": "#0D0A09", "#FBF7F1": "#0D0A09", "#F7F2EA": "#0A0807",
    "#F7F0E2": "#110E0C", "#F4ECDD": "#110E0C",
    "#F1E8D8": "#2B241F", "#EFE4D2": "#2B241F", "#EBDFCA": "#2B241F",
    "#D9CDB6": "#3B322B", "#E2D3B6": "#3B322B",
    "#FDEBD3": "#2A2118", "#FFF3DE": "#1D1814", "#FCDDC0": "#1D1814",
    "#FDF1D9": "#1D1814", "#F8E6C6": "#1D1814",
    "#EAF2FC": "#1D1814", "#D9E7F9": "#1D1814", "#EEF3FB": "#1D1814",
    "#EEF4FD": "#221B16", "#DCE6F5": "#221B16", "#DCE4F0": "#221B16",
    "#D6E3D1": "#2A3326", "#F3F7F1": "#171C15", "#FDF2F0": "#2A1614", "#EED8D3": "#5A2A24",
    # тёмные кружки и кнопки
    "#18213A": "#2B241F", "#2B3550": "#3B322B", "#5F687E": "#3B322B", "#9AA3B5": "#5A4F45",
    # небо → чёрное
    "#0E2A66": "#080605", "#0F2A66": "#080605", "#102F73": "#0D0A09",
    "#143A85": "#120E0C", "#174592": "#17120F", "#1A4A96": "#17120F",
    "#1F4C97": "#1F1814", "#1F56A6": "#1F1814", "#2563BA": "#2A211A",
    "#2A6DB8": "#2A211A", "#3F86DD": "#3A2E24", "#93BBF3": "#C9A45C",
    # красное → золото
    "#DA352C": "#E3C58A", "#D22B2B": "#D9B97A", "#D2302C": "#D9B97A",
    "#B3161F": "#B8914E", "#B01920": "#B8914E", "#B01E22": "#B8914E",
    "#E5483D": "#F0D9A6", "#EC5145": "#F0D9A6", "#F58D82": "#F6E7C3",
    # золото
    "#F0B13F": "#D9B97A", "#E39A2B": "#C39A4E", "#EFA533": "#C39A4E",
    "#F7CB62": "#F0D9A6", "#F6CF7A": "#F0D9A6", "#FBE3B0": "#F0D9A6", "#B07A1E": "#9A7430",
}

BG_RGB = {
    (251, 246, 236): (13, 10, 9), (255, 251, 245): (23, 19, 17),
    (235, 223, 202): (43, 36, 31), (248, 230, 198): (29, 24, 20),
    (24, 33, 58): (0, 0, 0), (16, 47, 115): (0, 0, 0), (13, 36, 92): (0, 0, 0),
    (15, 42, 102): (0, 0, 0), (8, 20, 56): (0, 0, 0), (9, 26, 68): (0, 0, 0),
    (20, 58, 133): (0, 0, 0), (26, 74, 150): (0, 0, 0), (10, 28, 74): (0, 0, 0),
    (31, 76, 151): (0, 0, 0),
    (190, 30, 35): (201, 164, 92), (150, 16, 24): (201, 164, 92),
    (232, 64, 52): (201, 164, 92), (214, 44, 44): (201, 164, 92),
    (240, 177, 63): (217, 185, 122), (214, 140, 30): (201, 164, 92),
    (227, 154, 43): (201, 164, 92),
}

_BG_PROPS = ("background", "border", "box-shadow", "text-shadow", "outline")
_FG_PROPS = ("color", "fill", "stroke", "caret-color", "-webkit-text-fill-color", "text-decoration-color")


def colors(text):
    def decl(m):
        prop = m.group(1).lower()
        if prop.startswith(_BG_PROPS):
            hx, rg = BG, BG_RGB
        elif prop in _FG_PROPS:
            hx, rg = FG, {}
        else:
            return m.group(0)
        val = re.sub(r"#[0-9A-Fa-f]{6}\b", lambda c: hx.get(c.group(0).upper(), c.group(0)), m.group(3))

        def rgb(c):
            key = (int(c.group(2)), int(c.group(3)), int(c.group(4)))
            return "%s%d,%d,%d" % ((c.group(1),) + rg[key]) if key in rg else c.group(0)
        val = re.sub(r"(rgba?\(\s*)(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", rgb, val)
        return m.group(1) + m.group(2) + val
    return re.sub(r'([\w-]+)(\s*:\s*)([^;{}"]+)', decl, text)


def apply(text, path):
    """Вызывается после оформления «море»: перекраска, антиква вместо
    высокого гротеска и свой слой стилей в конце site.css."""
    text = colors(text)
    text = text.replace("'Bebas Neue'", "'Prata'")
    if path.endswith(os.path.join("assets", "site.css")):
        text += CSS + slots_css()
    return text


def slots_css():
    """Стили для присланных картинок. Пока файла нет, его правил нет."""
    rules = {
        "barhat": ":root { --barhat: linear-gradient(140deg, rgba(10,8,7,.78) 0%, rgba(10,8,7,.9) 100%), URL; }",
        "mk": "[data-mk-card]::after { opacity: 1; background-image: linear-gradient(90deg, rgba(10,8,7,.96) 0%, "
              "rgba(10,8,7,.8) 46%, rgba(10,8,7,.25) 100%), URL; }",
        "final": "[data-final-card]::after { opacity: 1; background-image: linear-gradient(180deg, "
                 "rgba(10,8,7,.6) 0%, rgba(10,8,7,.9) 100%), URL; }",
        "lenta": "[data-h2-card]::before, [data-final]::before, section[aria-label=\"Подарки и условия\"]::before, "
                 "section[aria-label=\"Программа шесть недель\"]::before { display: block; background-image: URL; }",
        # В присланной сцене Виола уже есть: вырезанный снимок убирается.
        "hero-m": "@media (max-width: 900px) { [data-h2-fon] { display: block; top: 0; height: 100%; opacity: 1; "
                  "object-position: 50% 30%; -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0%, #000 16%); "
                  "mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 0%, #000 16%); } "
                  "[data-h2-viola], [data-h2-photo]::before { display: none; } }",
    }
    out = [rules[name].replace("URL", "url(/assets/img/b-%s)" % SLOTS[name])
           for name in sorted(rules) if est(name)]
    return "\n" + "\n".join(out) + "\n" if out else ""


def copy_slots(outdir):
    """Кладёт присланные картинки рядом с остальными. Возвращает пути."""
    import shutil
    made = []
    for name in sorted(SLOTS):
        if est(name):
            p = os.path.join(outdir, "b-" + SLOTS[name])
            shutil.copyfile(os.path.join(DIR, SLOTS[name]), p)
            made.append(p)
    return made


# ── фон первого экрана, пока нет присланной сцены ──

def velvet(size, glow=(0.72, 0.40)):
    """Тёмный фон первого экрана: тёплый бронзовый свет за фигурой, к краям
    чёрное. Если прислан fon.jpg (тёмный интерьер без людей), берётся он."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    w, h = size
    base = Image.new("RGB", size, (10, 8, 7))
    if est("fon"):
        im = Image.open(os.path.join(DIR, SLOTS["fon"])).convert("RGB")
        im = ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.35)).filter(ImageFilter.GaussianBlur(3))
        base = Image.blend(base, ImageEnhance.Brightness(im).enhance(0.75), 0.8)
    d = int(max(w, h) * 1.25)
    spot = Image.radial_gradient("L").point(lambda v: 255 - v).resize((d, d), Image.LANCZOS)
    mask = Image.new("L", size, 0)
    mask.paste(spot, (int(w * glow[0] - d / 2), int(h * glow[1] - d / 2)))
    mask = mask.point(lambda v: int(v * (0.34 if est("fon") else 0.62))).filter(ImageFilter.GaussianBlur(30))
    return Image.composite(Image.new("RGB", size, (150, 104, 62)), base, mask)


def fade_frame(im, part=0.30):
    """Низ кадра уходит в чёрный: фигура растворяется в фоне страницы."""
    from PIL import Image
    w, h = im.size
    g = Image.linear_gradient("L").resize((w, int(h * part)))
    mask = Image.new("L", im.size, 0)
    mask.paste(g, (0, h - g.height))
    return Image.composite(Image.new("RGB", im.size, (10, 8, 7)), im, mask)


def fade_cutout(cut, part=0.26):
    """Вырезанная фигура внизу становится прозрачной."""
    from PIL import Image, ImageChops
    w, h = cut.size
    g = Image.linear_gradient("L").resize((w, int(h * part))).point(lambda v: 255 - v)
    mask = Image.new("L", cut.size, 255)
    mask.paste(g, (0, h - g.height))
    r, gg, b, a = cut.split()
    return Image.merge("RGBA", (r, gg, b, ImageChops.multiply(a, mask)))


def scene(name, size):
    """Присланная сцена, обрезанная под кадр. None, если файла нет."""
    if not est(name):
        return None
    from PIL import Image, ImageOps
    im = Image.open(os.path.join(DIR, SLOTS[name])).convert("RGB")
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.4))


CSS = r"""

/* ───────────────────────── оформление «ночь» (--theme barhat) ── */

:root {
  --noch: #0A0807;
  --karta: #15110F;
  --karta2: #1E1814;
  --zol: #D9B97A;
  --zol-svet: #F0D9A6;
  --tekst: #F4EFE7;
  --liniya: rgba(227,197,138,.22);
  --metall: linear-gradient(180deg, #FFFFFF 0%, #F1E3C6 38%, #C9A870 72%, #9C7C48 100%);
  --zoloto: linear-gradient(180deg, #F9E6B4 0%, #E6C47E 46%, #C99D4C 100%);
  --svet:
    radial-gradient(90% 120% at 86% -10%, rgba(201,150,92,.32) 0%, rgba(201,150,92,0) 58%),
    radial-gradient(70% 90% at 0% 110%, rgba(201,150,92,.14) 0%, rgba(201,150,92,0) 60%),
    linear-gradient(160deg, #1B1512 0%, #110D0B 100%);
  --barhat: var(--svet);
  --sky: var(--svet);
  --panel: linear-gradient(160deg, #1E1814 0%, #17120F 100%);
  --spot: linear-gradient(160deg, #1E1814 0%, #17120F 100%);
  --tochki: linear-gradient(transparent, transparent);
  --ten: inset 0 0 0 1px var(--liniya);
  --knopka: 0 5px 0 #8C6A2E, 0 26px 46px -18px rgba(217,185,122,.55), inset 0 1px 0 rgba(255,255,255,.7);
  --prata: 'Prata', 'Times New Roman', Georgia, serif;
}

body { background: var(--noch); color: var(--tekst); }
main > section:not([aria-label="Первый экран"]) { background: var(--noch) !important; }
main > section[aria-label="Программа шесть недель"],
main > section[aria-label="Подарки и условия"] {
  background:
    radial-gradient(60% 40% at 100% 0%, rgba(201,150,92,.14) 0%, rgba(201,150,92,0) 70%),
    radial-gradient(50% 30% at 0% 60%, rgba(201,150,92,.10) 0%, rgba(201,150,92,0) 70%),
    var(--noch) !important;
}
main > section:not([aria-label="Первый экран"]):not([data-mk]):not([data-final]) {
  padding-top: clamp(60px, 8vw, 116px) !important;
  padding-bottom: clamp(60px, 8vw, 116px) !important;
}
main [style*="border-radius: 14px"], main [style*="border-radius: 16px"] { border-radius: 20px !important; }

[data-mk-card], [data-final-card], [data-tehniki], [data-n-title] {
  background-image: var(--barhat) !important;
  background-size: cover !important;
  background-position: center !important;
}

/* ── заголовки: антиква, первая строка металлом ── */

main h2,
section[aria-label="Зачем мне это"] > div > p:first-child {
  font-family: var(--prata) !important;
  font-weight: 400 !important;
  font-size: clamp(33px, 4.4vw, 60px) !important;
  line-height: 1.12 !important;
  letter-spacing: .03em !important;
  text-transform: uppercase;
  text-wrap: balance;
  color: var(--tekst) !important;
}
main h2::first-line,
section[aria-label="Зачем мне это"] > div > p:first-child::first-line,
[data-mk-card] h2::first-line, [data-final-card] h2::first-line { color: var(--zol-svet); }
main h3 { color: var(--tekst); }

main.doc h2 { font-family: 'Golos Text', system-ui, sans-serif !important; text-transform: none; letter-spacing: -.015em !important; }
main.doc h2::first-line { color: inherit; }

/* ── метки ── */

[data-tag],
main [style*="text-transform: uppercase"][style*="color: #E2C489"] {
  background: none;
  padding: 6px 14px;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(227,197,138,.5);
  color: var(--zol-svet) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  letter-spacing: .12em !important;
  text-transform: uppercase !important;
}
[data-tag="siniy"] { background: var(--zoloto); box-shadow: none; color: #1A1410 !important; font-weight: 700 !important; border-radius: 999px; }
[data-nedelya] [data-tag] { white-space: normal; letter-spacing: .06em !important; font-size: 12.5px !important; border-radius: 12px; }

/* ── кнопки: золотой брусок с кромкой и свечением ── */

[data-btn] { border-radius: 12px !important; }
[data-btn="primary"] {
  min-height: 68px;
  padding: 17px 42px !important;
  border: 0 !important;
  border-radius: 12px !important;
  background: var(--zoloto) !important;
  box-shadow: var(--knopka) !important;
  color: #1A1410 !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: .12em !important;
}
[data-btn="primary"]:hover { filter: brightness(1.07); }
[data-btn="quiet"] {
  min-height: 64px;
  padding: 16px 42px !important;
  border: 1px solid var(--zol) !important;
  border-radius: 12px !important;
  background: none !important;
  box-shadow: none !important;
  color: var(--zol-svet) !important;
  font-size: 16px !important;
  letter-spacing: .12em !important;
}
[data-btn="quiet"]:hover { background: rgba(227,197,138,.1) !important; filter: none; }
#tarify [data-btn="primary"], #pay-step [data-btn="primary"] { box-shadow: var(--knopka) !important; }
[data-btn="support"] { background: none !important; border: 1px solid var(--zol) !important; color: var(--zol-svet) !important; }
[data-btn="support"]:hover { background: rgba(227,197,138,.1) !important; }

/* ── первый экран, телефон: плитки сверху, фигура, название поверх неё ── */

@media (max-width: 900px) {
  [data-h2] {
    display: flex;
    flex-direction: column;
    align-items: center;
    background:
      radial-gradient(120% 46% at 50% 30%, rgba(170,118,70,.5) 0%, rgba(170,118,70,0) 70%),
      var(--noch);
    color: var(--tekst);
  }
  [data-h2-top] { display: contents; }
  [data-h2-chips] { order: 1; position: relative; z-index: 3; width: 100%; justify-content: space-between; padding: 18px 18px 0; }
  [data-h2-chips] span {
    min-width: 0;
    padding: 9px 14px 10px;
    border-radius: 12px;
    background: rgba(10,8,7,.45);
    box-shadow: inset 0 0 0 1px var(--liniya);
    font-size: 13.5px;
    text-align: center;
  }
  [data-h2-chips] i { color: rgba(244,239,231,.7); }
  [data-h2-chips] b { font-size: 15.5px; font-weight: 600; color: var(--zol-svet); }
  [data-h2-chips] em { display: none; }
  [data-h2-tag] { order: 1; position: relative; z-index: 3; margin-top: 12px; }
  [data-h2-photo] { order: 2; width: 100%; height: clamp(400px, 112vw, 640px); margin-top: -34px; }
  [data-h2-fon] { display: none; }
  [data-h2-viola] { -webkit-mask-image: linear-gradient(to bottom, #000 62%, rgba(0,0,0,0) 97%); mask-image: linear-gradient(to bottom, #000 62%, rgba(0,0,0,0) 97%); }
  [data-h2-sub] {
    order: 3; position: relative; z-index: 3;
    margin-top: -112px;
    padding: 0 20px;
    font-family: var(--prata);
    font-weight: 400;
    font-size: 15px;
    letter-spacing: .12em;
    text-transform: uppercase;
    text-align: center;
    color: var(--tekst);
    text-shadow: 0 2px 18px #000;
  }
  [data-h2-title] {
    order: 4; position: relative; z-index: 3;
    margin: 10px 0 0;
    padding: 0 14px .06em;
    font-family: var(--prata);
    font-weight: 400;
    font-size: min(calc((100vw - 28px) / (var(--bukv, 10) * .78)), 96px);
    line-height: 1.06;
    letter-spacing: .03em;
    text-align: center;
    color: var(--zol-svet);
    background: var(--metall);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: none;
    filter: drop-shadow(0 6px 22px rgba(0,0,0,.8));
  }
  [data-h2-top] a[data-btn] { order: 5; position: relative; z-index: 3; margin-top: 26px; }
  [data-h2-pod] { order: 6; position: relative; z-index: 3; margin-top: 18px; padding: 0 20px; text-align: center; }
  [data-h2-card] {
    order: 7;
    align-self: stretch;
    gap: 16px;
    margin: 36px 18px 0;
    padding: 28px 22px 30px;
    border-radius: 20px;
    background: var(--svet);
    box-shadow: var(--ten);
    color: var(--tekst);
  }
  [data-h2-name] {
    font-family: var(--prata);
    font-weight: 400;
    font-size: min(calc((100vw - 84px) / 11.6), 42px);
    line-height: 1.15;
    letter-spacing: .02em;
    color: var(--zol-svet);
  }
  [data-h2-def] { font-size: 19.5px; line-height: 1.5; color: #DED6CB; }
  [data-h2-def] b { color: #FFFFFF; }
  [data-h2-note] {
    padding: 0 0 0 16px;
    border-radius: 0;
    border-left: 1px solid var(--zol);
    background: none;
    font-size: 16.5px;
    color: #BDB3A7;
  }
  section[aria-label="Первый экран"] { padding-bottom: 12px; }
}
[data-h2-tag] { background: var(--zoloto); color: #1A1410; font-weight: 700; font-size: 14.5px; }
[data-h2-chto] { font-family: var(--prata); font-weight: 400; letter-spacing: .01em; color: var(--tekst); }
[data-h2-list] li { background: rgba(10,8,7,.4); box-shadow: var(--ten); font-weight: 600; font-size: 18px; color: var(--tekst); }
[data-h2-list] li::before { background: var(--zoloto); }
[data-h2-list] li::after { border-color: #1A1410; }

/* ── первый экран, широкий ── */

section[aria-label="Первый экран"] { background: var(--noch) !important; color: var(--tekst) !important; }
@media (min-width: 901px) {
  [data-hero-stage] [data-hero-copy] > [data-hero-card] {
    max-width: min(640px, 48vw) !important;
    background: none;
    border-radius: 0;
    padding: 0;
    box-shadow: none;
  }
  [data-hero-stage] [data-hero-card] h1 {
    font-family: var(--prata) !important;
    font-weight: 400 !important;
    font-size: clamp(42px, 4.7vw, 76px) !important;
    line-height: 1.08 !important;
    letter-spacing: .03em !important;
    padding-bottom: .08em;
    background: var(--metall);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: none !important;
  }
}
@media (min-width: 901px) and (max-width: 1200px) {
  [data-hero-stage] [data-hero-copy] > [data-hero-card] { max-width: 41vw !important; }
  [data-hero-stage] [data-hero-card] h1 { font-size: 4.1vw !important; }
}
[data-hero-card] { background: none; }
[data-hero-stage] [data-hero-card] > div:first-child > div:first-child {
  color: var(--zol-svet) !important;
  font-size: 14px !important;
  font-weight: 600;
  letter-spacing: .16em !important;
  text-transform: uppercase !important;
}
[data-hero-stage] [data-hero-card] > div:last-child > p:first-child { color: var(--tekst) !important; font-weight: 400 !important; }
[data-hero-stage] [data-hero-card] > div:last-child > p:nth-child(2) {
  color: #DED6CB !important;
  background: none !important;
  border-left: 1px solid var(--zol) !important;
  border-radius: 0 !important;
  padding: 2px 0 2px 16px !important;
}
[data-hero-card] > div:last-child > div > div { background: none !important; border: 0 !important; box-shadow: inset 0 0 0 1px var(--liniya); }
[data-hero-stage] [data-hero-card] > div:last-child > div > div > span:last-child { color: var(--zol-svet) !important; }
[data-hero-stage] [data-hero-card] p[data-hero-pod] { color: #DED6CB !important; }

/* ── значки: золотые плитки ── */

[data-nedelya] li > span, [data-n-viola] > span,
[data-week-head] > div:first-child > span:first-child,
[data-podarok] > span {
  border-radius: 14px !important;
  background: var(--zoloto) !important;
  box-shadow: 0 3px 0 #8C6A2E, 0 16px 26px -14px rgba(217,185,122,.7), inset 0 1px 0 rgba(255,255,255,.7) !important;
  color: #1A1410 !important;
}

/* ── «Эмпатия — это способность» ── */

section[aria-label="Зачем мне это"] p { color: #DED6CB; }
[data-sfery] { border-radius: 20px; background: var(--karta); box-shadow: var(--ten); }
[data-sfery] > div { padding: 16px 20px !important; background: none !important; }
[data-sfery] > div:not(:first-child) { border-top: 1px solid var(--liniya) !important; }
[data-sfery] > div > span:first-child,
[data-sfery] > div:not(:first-child) > span:first-child {
  width: 36px !important; height: auto !important;
  border-radius: 0 !important;
  background: none !important;
  font-family: var(--prata);
  font-size: 26px !important;
  font-weight: 400 !important;
  color: var(--zol) !important;
  padding-top: 0;
}
[data-sfery] > div > span:nth-child(2) { color: var(--zol-svet) !important; }
[data-sfery] > div > span:last-child { font-weight: 500 !important; color: var(--tekst) !important; }

[data-tehniki] { gap: 14px 22px; padding: 34px 28px 34px !important; border-radius: 20px !important; box-shadow: var(--ten), 0 40px 70px -40px rgba(201,150,92,.5) !important; color: var(--tekst); }
[data-tehniki] > span {
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: clamp(96px, 25vw, 136px) !important;
  line-height: .9 !important;
  color: transparent !important;
  background: var(--metall) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
}
[data-t-lead] { font-family: var(--prata); font-weight: 400; font-size: 23px; line-height: 1.3; color: var(--tekst); }
[data-t-text] { padding-top: 16px; border-top: 1px solid var(--liniya); font-size: 17.5px; color: #DED6CB; }

/* ── программа ── */

[data-cifry] { gap: 12px !important; grid-template-columns: repeat(4, minmax(0, 210px)); }
[data-cifry] > span, [data-cifry] > span:nth-child(n) {
  border-radius: 18px;
  padding: 20px 20px 18px;
  background: var(--karta);
  box-shadow: var(--ten);
  color: #DED6CB;
  font-size: 16px;
  font-weight: 500;
}
[data-cifry] b, [data-cifry] > span:nth-child(n) b {
  font-family: var(--prata); font-weight: 400; font-size: 54px !important; line-height: 1 !important;
  color: transparent !important; background: var(--metall); -webkit-background-clip: text; background-clip: text;
}

[data-nedelya] { border-radius: 20px; background: var(--karta); box-shadow: var(--ten); }
[data-n-title] {
  padding: 30px 26px 26px;
  border-bottom: 1px solid var(--liniya);
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(28px, 3.5vw, 42px);
  line-height: 1.16;
  letter-spacing: .03em;
  color: var(--zol-svet);
}
[data-n-title]::first-line { color: var(--tekst); }
[data-nedelya] ul { padding: 8px 24px; }
[data-nedelya] li { grid-template-columns: 52px minmax(0, 1fr); padding: 16px 0; font-size: 18.5px; color: var(--tekst); }
[data-nedelya] li > span { width: 52px; height: 52px; }
[data-nedelya] li + li { border-top: 1px solid var(--liniya); }
[data-n-foot] { padding: 18px 26px; background: var(--zoloto); font-weight: 700; font-size: 17.5px; color: #1A1410; }
[data-n-foot] span { font-family: var(--prata); font-size: 34px; line-height: .8; color: #1A1410; }

[data-week-card] { border-radius: 20px !important; background: var(--karta) !important; box-shadow: var(--ten) !important; }
[data-week-head] { color: var(--tekst) !important; }
[data-week-head] > div:first-child > span:first-child { width: 52px !important; height: 52px !important; }
[data-week-head] h3 { font-family: var(--prata); font-weight: 400 !important; font-size: clamp(25px, 2.7vw, 32px) !important; line-height: 1.2 !important; }
[data-vopros] {
  align-self: stretch;
  max-width: none;
  margin-top: 4px;
  padding: 2px 0 2px 18px;
  border-radius: 0;
  border-left: 2px solid var(--zol);
  background: none;
  box-shadow: none;
  color: var(--zol-svet);
  font-family: var(--prata);
  font-weight: 400;
  font-size: 19px;
  line-height: 1.42;
  letter-spacing: 0;
}
[data-ava] { background: var(--zoloto); color: #1A1410; font-family: var(--prata); font-weight: 400; }
[data-bubble] { background: var(--karta2); border-radius: 18px 18px 18px 6px; padding: 14px 18px 16px; }
[data-who] { color: var(--zol); font-size: 14.5px; }
[data-bubble] p { font-size: 17.5px; line-height: 1.55; color: var(--tekst); }
[data-week-card] [style*="width: 30px; height: 30px"] {
  border-radius: 0 !important;
  background: none !important;
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: 24px !important;
  color: var(--zol) !important;
}

/* ── ответы на вопросы ── */

[data-otvety] { padding: 34px 26px 30px; border-radius: 20px; background: var(--svet); box-shadow: inset 0 0 0 1px rgba(227,197,138,.6), 0 40px 70px -40px rgba(201,150,92,.5); color: var(--tekst); }
[data-otvety] > [data-tag] { background: none; }
[data-o-title] {
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(28px, 3.5vw, 42px);
  line-height: 1.16;
  letter-spacing: .03em;
  color: var(--tekst);
}
[data-o-title]::first-line { color: var(--zol-svet); }
[data-o-text] { font-size: 18.5px; font-weight: 500; line-height: 1.5; color: var(--tekst); }
[data-o-primer] { color: #BDB3A7; }
[data-audio] { background: var(--karta2); }
[data-o-post] { border-top-color: var(--liniya); }
[data-o-tema], [data-o-kto] { color: var(--tekst); }
[data-o-vopros] { color: #DED6CB; }
[data-o-tegi] { color: var(--zol); }
[data-o-time] { color: #A39A8F; }
[data-wave] > span { background: var(--zoloto); color: #1A1410; }
[data-wave] > i b { background: var(--zol); opacity: .6; }

/* ── мастер-класс ── */

[data-mk] { background: var(--noch) !important; }
[data-mk-card] {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: clamp(40px, 5vw, 72px) clamp(26px, 4.4vw, 64px);
  box-shadow: inset 0 0 0 1px rgba(227,197,138,.6), 0 40px 70px -40px rgba(201,150,92,.5);
  color: var(--tekst);
}
[data-mk-card]::after, [data-final-card]::after {
  content: "";
  position: absolute; inset: 0;
  background-position: right center;
  background-size: cover;
  background-repeat: no-repeat;
  opacity: 0;
}
[data-mk-card] > *, [data-final-card] > * { position: relative; z-index: 1; }
[data-mk-card] > div:first-child { background: none !important; box-shadow: inset 0 0 0 1px rgba(227,197,138,.5); color: var(--zol-svet); }

/* Лента. Появляется, когда пришлют файл. */
[data-h2-card]::before, [data-final]::before, section[aria-label="Подарки и условия"]::before,
section[aria-label="Программа шесть недель"]::before {
  content: "";
  display: none;
  position: absolute;
  right: -40px; top: -58px;
  width: min(320px, 64vw); height: 130px;
  background-position: center;
  background-size: contain;
  background-repeat: no-repeat;
  pointer-events: none;
}
[data-final], section[aria-label="Подарки и условия"], section[aria-label="Программа шесть недель"] { position: relative; overflow: hidden; }
[data-h2-card] { position: relative; }
[data-final]::before, section[aria-label="Подарки и условия"]::before { top: 8px; right: -30px; }
section[aria-label="Программа шесть недель"]::before { top: 10px; right: auto; left: -40px; transform: scaleX(-1); }

/* ── тарифы ── */

#tarify > div > div[style*="grid"] > div { background: var(--karta) !important; border: 0 !important; box-shadow: var(--ten) !important; color: var(--tekst); }
#tarify > div > div[style*="grid"] > div:last-child { background: var(--svet) !important; box-shadow: inset 0 0 0 1.5px var(--zol), 0 44px 80px -44px rgba(201,150,92,.6) !important; }
#tarify [style*="top: -14px"] {
  background: var(--zoloto) !important;
  color: #1A1410 !important;
  box-shadow: 0 12px 22px -12px rgba(217,185,122,.8) !important;
  letter-spacing: .08em;
  font-size: 13.5px !important;
  text-transform: uppercase !important;
}
#tarify h3 { font-family: var(--prata); font-weight: 400 !important; }
#tarify span[style*="color: #E3C58A"] { background: none; box-shadow: inset 0 0 0 1px var(--zol); color: var(--zol-svet) !important; }
#tarify span[style*="display: inline-flex"][style*="color: #E2C489"] { color: #857C73 !important; }
#tarify [style*="line-through"] { text-decoration-color: #857C73 !important; color: #857C73 !important; }
#tarify [style*="height: 1px"] { background: var(--liniya) !important; }
/* Цена — золотой плашкой: самое контрастное место карточки. */
[data-cena] { border-radius: 14px; padding: 20px 22px; background: var(--zoloto) !important; box-shadow: 0 5px 0 #8C6A2E, 0 24px 40px -22px rgba(217,185,122,.6); }
[data-cena], [data-cena] * { color: #1A1410 !important; }
[data-cena] [style*="font-size"] { font-family: var(--prata); font-weight: 400 !important; }
[data-cena] [data-cena-note], [data-cena] [data-cena-note] b { color: #1A1410 !important; }
[data-mest] { background: none !important; padding: 0 !important; }
[data-mest] > span:first-child { background: var(--zol) !important; }
[data-mest] > span:last-child { color: var(--zol-svet) !important; }
#kontakty > div { background: var(--karta) !important; box-shadow: var(--ten) !important; }

/* ── подарки ── */

[data-podarok] { background: var(--karta); border-radius: 18px; padding: 18px; box-shadow: var(--ten); grid-template-columns: 54px 1fr !important; color: var(--tekst); }
[data-podarok] > span { width: 54px !important; height: 54px !important; }
[data-za-zayavku] { background: var(--svet) !important; box-shadow: var(--ten) !important; }

/* ── последний призыв ── */

[data-final] { background: var(--noch) !important; }
[data-final-card] {
  position: relative; overflow: hidden;
  border-radius: 20px;
  padding: clamp(44px, 5.4vw, 76px) clamp(26px, 4.4vw, 64px);
  box-shadow: inset 0 0 0 1px rgba(227,197,138,.6), 0 40px 70px -40px rgba(201,150,92,.5);
  color: var(--tekst);
}
[data-final-card] > div:first-child { background: none !important; border: 0 !important; box-shadow: inset 0 0 0 1px rgba(227,197,138,.5); }
[data-final-card] h2 { font-size: clamp(33px, 4.4vw, 60px) !important; }
[data-final-card] p { color: #DED6CB !important; }
[data-final-card] p b { color: #FFFFFF; }

/* ── окно заявки и оплата ── */

#lead-modal h2 { font-family: var(--prata) !important; font-weight: 400 !important; text-transform: none; letter-spacing: 0 !important; }
#lead-modal h2::first-line { color: inherit; }
#lead-modal input, #lead-modal textarea, #lead-modal select { background: #0D0A09 !important; color: var(--tekst) !important; border-color: #3B322B !important; }
#lead-modal input::placeholder, #lead-modal textarea::placeholder { color: #857C73; }
#lead-modal label [style*="text-transform: uppercase"] { color: var(--tekst) !important; box-shadow: none; padding: 0; letter-spacing: 0 !important; text-transform: none !important; font-size: 16px !important; }
#lead-modal label span span[style*="text-transform: uppercase"] { color: #A39A8F !important; }
/* Плашка с выбранным тарифом: после перекраски вышла полосатой. */
#lead-modal [style*="border-radius: 999px"][style*="linear-gradient(180deg, #1D1814"] { background: rgba(227,197,138,.12) !important; border-color: rgba(227,197,138,.5) !important; }
[data-pay-option] { box-shadow: var(--ten); }
[data-pay-option="ru"], [data-pay-option="intl"] { background: var(--karta2) !important; }
[data-pay-option] > div > span:first-child, [data-pay-option] p { color: #DED6CB !important; }
[data-pay-price] { font-family: var(--prata); font-weight: 400 !important; font-size: 40px !important; line-height: 1.1 !important; color: var(--zol-svet) !important; }
#pay-step [data-btn] { letter-spacing: .06em !important; font-size: clamp(14.5px, 4vw, 16px) !important; }

.ft-label { color: var(--zol); }
.cookie-bar { background: var(--karta2); border: 1px solid var(--liniya); color: var(--tekst); box-shadow: 0 18px 44px -18px #000; }
.cookie-bar a { color: var(--zol-svet); }
.cookie-bar button { background: var(--zoloto); color: #1A1410; border-radius: 10px; }

/* ── телефон ── */

@media (max-width: 760px) {
  main > section:not([aria-label="Первый экран"]) { padding-left: 20px !important; padding-right: 20px !important; }
  main h2 { font-size: 33px !important; }
  section[aria-label="Зачем мне это"] > div > p:first-child { font-size: min(33px, calc((100vw - 40px) / 10.4)) !important; }
  [data-cifry] { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  [data-btn="primary"] { width: min(100%, 330px); }
  [data-sticky-bar] { background: #110E0C !important; box-shadow: 0 -1px 0 var(--liniya) !important; }
  [data-sticky-bar] a { letter-spacing: .06em !important; box-shadow: 0 3px 0 #8C6A2E !important; }
}
"""
