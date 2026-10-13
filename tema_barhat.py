# -*- coding: utf-8 -*-
"""Оформление «бархат» (--theme barhat): тёмно-бордовый, золото, антиква.

Работает поверх оформления «море»: сборщик сначала делает всё, что делает
для --theme more (те же блоки, те же слова, те же формы), а потом этот
модуль перекрашивает страницу и добавляет свой слой стилей. Тексты
не меняются.

Правила вида.
  1. Воздух. Между блоками большие отступы, заголовки спокойного размера,
     карточки без теней, с тонкой линией.
  2. Золото только тонкое: линии, цифры, первая строка заголовка. Сплошная
     золотая заливка одна — у главной кнопки.
  3. Тёмный бархат: первый экран, мастер-класс, тарифы, последний призыв.
     Длинный текст стоит на светлом.
  4. Антиква (Prata) только в заголовках и цифрах. Текст — Golos Text.

Картинки вставляются позже. Файлы кладутся в build-assets/tema-barhat/
под именами из SLOTS; пока файла нет, на его месте стоит фон из градиента,
и страница выглядит законченной.
"""

import os
import re

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-assets", "tema-barhat")

# имя в стилях → файл в build-assets/tema-barhat/
SLOTS = {
    "hero-d": "hero-desktop.jpg",   # Виола в сцене, горизонтальная 2400×1400
    "hero-m": "hero-mobile.jpg",    # Виола в сцене, вертикальная 1080×1600
    "lenta":  "lenta.png",          # золотая лента на прозрачном фоне
    "barhat": "barhat.jpg",         # фактура бархата для тёмных блоков
    "mk":     "mk.jpg",             # зал со сценой, мастер-класс
    "final":  "final.jpg",          # приоткрытая дверь, последний призыв
}


def est(name):
    return os.path.exists(os.path.join(DIR, SLOTS[name]))


# ── цвета: «море» → «бархат» ──

HEX = {
    # текст
    "#18213A": "#2B1719", "#2B3550": "#43292B", "#465068": "#5F4A49",
    "#4A546C": "#6A5553", "#5F687E": "#7B6866", "#9AA3B5": "#B3A39B",
    # небо → бархат
    "#0E2A66": "#22070D", "#0F2A66": "#22070D", "#102F73": "#2C0A12",
    "#143A85": "#3D0E1A", "#174592": "#45101D", "#1A4A96": "#4F1322",
    "#1F56A6": "#5A1526", "#2563BA": "#6A1A2D", "#2A6DB8": "#741E33",
    "#3F86DD": "#8E2A43", "#93BBF3": "#D9B36A",
    # синий текст и номера → вино
    "#1F4C97": "#7A1A2C",
    # голубые плашки → тёплая слоновая кость
    "#DCE4F0": "#EADFD2", "#DCE6F5": "#EFE3D3", "#D9E7F9": "#F0E2CF",
    "#EAF2FC": "#F7EEDF", "#EEF3FB": "#F6EEE2", "#EEF4FD": "#F7EFE2",
    # красный → вино
    "#B01E22": "#8E1B2E", "#B3161F": "#7A1626", "#B01920": "#7A1626",
    "#DA352C": "#9C2136", "#D22B2B": "#8E1B2E", "#D2302C": "#8E1B2E",
    "#E5483D": "#A8283E", "#EC5145": "#B4304A", "#F58D82": "#E2C07A",
    # жёлтое золото → приглушённое
    "#F0B13F": "#C9A45C", "#E39A2B": "#B88D45", "#EFA533": "#C39A4E",
    "#F7CB62": "#E3C98C", "#F6CF7A": "#E3C98C", "#FBE3B0": "#EEDDB4",
    "#B07A1E": "#9A7430",
    # персиковые плашки
    "#FDEBD3": "#F3E7D3", "#FFF3DE": "#F8F0E0", "#FCDDC0": "#F0E2CB",
}

RGB = {
    (24, 33, 58): (43, 23, 25), (190, 30, 35): (122, 22, 38),
    (240, 177, 63): (201, 164, 92), (16, 47, 115): (51, 12, 22),
    (13, 36, 92): (42, 10, 18), (15, 42, 102): (45, 11, 20),
    (8, 20, 56): (26, 6, 11), (9, 26, 68): (30, 7, 13),
    (150, 16, 24): (90, 14, 28), (20, 58, 133): (69, 16, 30),
    (214, 140, 30): (170, 130, 60), (26, 74, 150): (87, 21, 38),
    (10, 28, 74): (34, 8, 15), (31, 76, 151): (122, 26, 44),
    (232, 64, 52): (201, 164, 92), (214, 44, 44): (201, 164, 92),
    (227, 154, 43): (184, 141, 69),
}


def colors(text):
    text = re.sub(r"#[0-9A-Fa-f]{6}\b", lambda m: HEX.get(m.group(0).upper(), m.group(0)), text)

    def rgb(m):
        key = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        if key not in RGB:
            return m.group(0)
        return "%s%d,%d,%d" % ((m.group(1),) + RGB[key])
    return re.sub(r"(rgba?\(\s*)(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", rgb, text)


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
        "barhat": ":root { --barhat: linear-gradient(150deg, rgba(30,7,13,.78) 0%, rgba(74,17,32,.6) 55%, "
                  "rgba(100,24,41,.5) 100%), URL; }",
        "mk": "[data-mk-card]::after { opacity: 1; background-image: linear-gradient(90deg, rgba(30,7,13,.94) 0%, "
              "rgba(30,7,13,.74) 46%, rgba(30,7,13,.18) 100%), URL; }",
        "final": "[data-final-card]::after { opacity: 1; background-image: linear-gradient(180deg, "
                 "rgba(30,7,13,.62) 0%, rgba(30,7,13,.86) 100%), URL; }",
        "lenta": "[data-h2-card]::before, [data-final]::before, "
                 "section[aria-label=\"Подарки и условия\"]::before { display: block; background-image: URL; }",
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

def velvet(size, glow=(0.72, 0.42)):
    """Тёмно-бордовый фон с мягким тёплым светом за фигурой."""
    from PIL import Image, ImageFilter
    w, h = size
    base = Image.new("RGB", size, (30, 7, 13))
    # свет за фигурой
    spot = Image.radial_gradient("L").point(lambda v: 255 - v)
    d = int(max(w, h) * 1.7)
    spot = spot.resize((d, d), Image.LANCZOS)
    mask = Image.new("L", size, 0)
    mask.paste(spot, (int(w * glow[0] - d / 2), int(h * glow[1] - d / 2)))
    mask = mask.point(lambda v: int(v * 0.8)).filter(ImageFilter.GaussianBlur(30))
    base = Image.composite(Image.new("RGB", size, (104, 24, 40)), base, mask)
    # золотистый отсвет поменьше
    d2 = int(max(w, h) * 0.62)
    spot2 = Image.radial_gradient("L").point(lambda v: 255 - v).resize((d2, d2), Image.LANCZOS)
    mask2 = Image.new("L", size, 0)
    mask2.paste(spot2, (int(w * glow[0] - d2 / 2), int(h * (glow[1] - 0.08) - d2 / 2)))
    mask2 = mask2.point(lambda v: int(v * 0.24)).filter(ImageFilter.GaussianBlur(30))
    base = Image.composite(Image.new("RGB", size, (214, 160, 110)), base, mask2)
    return base.filter(ImageFilter.GaussianBlur(2))


def scene(name, size):
    """Присланная сцена, обрезанная под кадр. None, если файла нет."""
    if not est(name):
        return None
    from PIL import Image, ImageOps
    im = Image.open(os.path.join(DIR, SLOTS[name])).convert("RGB")
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.4))


CSS = r"""

/* ───────────────────────────── оформление «бархат» (--theme barhat) ── */

:root {
  --vino: #7A1A2C;
  --noch: #1E070D;
  --zol: #C9A45C;
  --zol-svet: #E7CE94;
  --kost: #F8F2E7;
  --liniya: #E6D9C4;
  --barhat:
    radial-gradient(120% 90% at 82% -10%, rgba(231,206,148,.16) 0%, rgba(231,206,148,0) 55%),
    radial-gradient(90% 120% at 0% 100%, rgba(0,0,0,.38) 0%, rgba(0,0,0,0) 60%),
    linear-gradient(150deg, #2C0A12 0%, #4A1120 52%, #641829 100%);
  --sky: var(--barhat);
  --panel: linear-gradient(160deg, #F9F1E2 0%, #F2E5D0 100%);
  --spot: linear-gradient(160deg, #F8F0E2 0%, #F3E8D6 100%);
  --zoloto: linear-gradient(135deg, #EFDDAE 0%, #D2B06A 55%, #BE9750 100%);
  --tochki: linear-gradient(transparent, transparent);
  --ten: 0 0 0 1px var(--liniya);
  --prata: 'Prata', 'Times New Roman', Georgia, serif;
}

body { background: var(--kost); }

/* Фактура бархата ложится под тёмные блоки, когда её пришлют. */
[data-h2], [data-mk-card], [data-final-card], #tarify, [data-tehniki], [data-n-title], [data-cena] {
  background-image: var(--barhat) !important;
  background-size: cover !important;
  background-position: center !important;
}

/* ── заголовки ── */

main h2,
section[aria-label="Зачем мне это"] > div > p:first-child {
  font-family: var(--prata) !important;
  font-weight: 400 !important;
  font-size: clamp(31px, 4.1vw, 54px) !important;
  line-height: 1.14 !important;
  letter-spacing: .015em !important;
  text-transform: uppercase;
  text-wrap: balance;
}
main h2::first-line,
section[aria-label="Зачем мне это"] > div > p:first-child::first-line { color: var(--vino); }
[data-mk-card] h2::first-line, [data-final-card] h2::first-line, #tarify > div > h2::first-line { color: var(--zol-svet); }
main h3 { letter-spacing: -.01em; }

main.doc h2 { font-family: 'Golos Text', system-ui, sans-serif !important; text-transform: none; letter-spacing: -.015em !important; }
main.doc h2::first-line { color: inherit; }

/* ── воздух ── */

main > section:not([aria-label="Первый экран"]):not([data-mk]):not([data-final]) {
  padding-top: clamp(64px, 9vw, 132px) !important;
  padding-bottom: clamp(64px, 9vw, 132px) !important;
}
main [style*="border-radius: 14px"], main [style*="border-radius: 16px"] { border-radius: 20px !important; }

/* ── метки ── */

[data-tag],
main [style*="text-transform: uppercase"][style*="color: #8E1B2E"] {
  background: none;
  padding: 0;
  border-radius: 0;
  color: #9A7430 !important;
  font-size: 13.5px !important;
  font-weight: 700 !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
}
[data-tag="siniy"] { background: none; color: #9A7430 !important; border-radius: 0; }
[data-nedelya] [data-tag] { white-space: normal; letter-spacing: .08em !important; font-size: 12.5px !important; }

/* ── кнопки ── */

[data-btn] { border-radius: 14px !important; }
[data-btn="primary"] {
  min-height: 66px;
  padding: 16px 40px !important;
  border: 0 !important;
  border-radius: 14px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,.5) 0%, rgba(255,255,255,0) 46%),
    linear-gradient(135deg, #F0DEB0 0%, #D4B26C 52%, #B9914A 100%) !important;
  box-shadow: 0 18px 36px -20px rgba(201,164,92,.9), inset 0 0 0 1px rgba(255,255,255,.35) !important;
  color: #2B1719 !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: .12em !important;
}
[data-btn="primary"]:hover { filter: brightness(1.05); }
[data-btn="quiet"] {
  min-height: 66px;
  padding: 16px 40px !important;
  border: 1px solid var(--vino) !important;
  border-radius: 14px !important;
  background: none !important;
  box-shadow: none !important;
  color: var(--vino) !important;
  font-size: 16px !important;
  letter-spacing: .12em !important;
}
[data-btn="quiet"]:hover { background: rgba(122,26,44,.06) !important; filter: none; }
#tarify [data-btn="primary"], #pay-step [data-btn="primary"] { box-shadow: inset 0 0 0 1px rgba(255,255,255,.35) !important; }
[data-btn="support"]:hover { background: #F7EFE2 !important; }

/* ── первый экран, телефон ── */

@media (max-width: 900px) {
  [data-h2] { background-color: var(--noch); }
  [data-h2-top] { gap: 16px; padding-top: 28px; }
  [data-h2-chips] { gap: 10px; }
  [data-h2-chips] span {
    min-width: 0;
    flex-direction: row;
    gap: 6px;
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid rgba(231,206,148,.45);
    background: none;
    font-size: 14.5px;
    white-space: nowrap;
  }
  [data-h2-chips] i { color: rgba(248,242,231,.8); }
  [data-h2-chips] b { font-size: 14.5px; font-weight: 600; color: var(--zol-svet); }
  [data-h2-chips] em { display: none; }
  [data-h2-title] {
    margin-top: 14px;
    font-family: var(--prata);
    font-weight: 400;
    font-size: min(calc((100vw - 40px) / (var(--bukv, 10) * .76)), 92px);
    line-height: 1.08;
    letter-spacing: .02em;
    color: var(--zol-svet);
    background: linear-gradient(180deg, #F6E7BF 0%, #E2C788 45%, #BE9750 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: none;
  }
  [data-h2-sub] { font-weight: 400; font-size: 17px; color: rgba(248,242,231,.9); }
  [data-h2-top] a[data-btn] { margin-top: 12px; }
  [data-h2-photo] { margin-top: 18px; }
  [data-h2-fon] { display: none; }
  [data-h2-photo]::before {
    content: "";
    position: absolute; left: 50%; top: 6%;
    width: 120%; height: 86%;
    transform: translateX(-50%);
    background: radial-gradient(closest-side, rgba(226,170,120,.42) 0%, rgba(150,40,60,.3) 46%, rgba(30,7,13,0) 100%);
  }
  [data-h2-card] {
    gap: 16px;
    padding: 36px 24px 44px;
    background: var(--kost);
    box-shadow: 0 -24px 50px -26px rgba(0,0,0,.7);
  }
  [data-h2-name] {
    font-family: var(--prata);
    font-weight: 400;
    font-size: min(calc((100vw - 48px) / 11.4), 44px);
    line-height: 1.15;
    letter-spacing: .015em;
    color: var(--vino);
  }
  [data-h2-def] { font-size: 20px; line-height: 1.5; }
  [data-h2-note] {
    padding: 0 0 0 16px;
    border-radius: 0;
    border-left: 1px solid var(--zol);
    background: none;
    font-size: 16.5px;
    color: #5F4A49;
  }
}
[data-h2-tag] { background: none; border: 1px solid rgba(231,206,148,.6); color: var(--zol-svet); font-weight: 600; font-size: 14.5px; }
[data-h2-chto] { font-family: var(--prata); font-weight: 400; letter-spacing: .01em; }
[data-h2-list] li { box-shadow: var(--ten); font-weight: 600; font-size: 18px; }
[data-h2-list] li::before { background: none; box-shadow: inset 0 0 0 1px var(--zol); }
[data-h2-list] li::after { border-color: #9A7430; border-width: 0 1.5px 1.5px 0; }

/* ── первый экран, широкий ── */

section[aria-label="Первый экран"] { background: var(--noch) !important; color: var(--kost) !important; }
@media (min-width: 901px) {
  [data-hero-stage] [data-hero-copy] > [data-hero-card] {
    max-width: min(640px, 50vw) !important;
    background: none;
    border-radius: 0;
    padding: 0;
    box-shadow: none;
  }
  [data-hero-stage] [data-hero-card] h1 {
    font-family: var(--prata) !important;
    font-weight: 400 !important;
    font-size: clamp(42px, 4.6vw, 72px) !important;
    line-height: 1.1 !important;
    padding-bottom: .08em;
    letter-spacing: .02em !important;
    background: linear-gradient(180deg, #F6E7BF 0%, #E2C788 45%, #BE9750 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
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
[data-hero-stage] [data-hero-card] > div:last-child > p:first-child { color: var(--kost) !important; font-weight: 400 !important; }
[data-hero-stage] [data-hero-card] > div:last-child > p:nth-child(2) {
  color: rgba(248,242,231,.82) !important;
  background: none !important;
  border-left: 1px solid var(--zol) !important;
  border-radius: 0 !important;
  padding: 2px 0 2px 16px !important;
}
[data-hero-card] > div:last-child > div > div { background: none !important; border: 1px solid rgba(231,206,148,.45) !important; }
[data-hero-stage] [data-hero-card] > div:last-child > div > div > span:last-child { color: var(--zol-svet) !important; }
[data-hero-stage] [data-hero-card] p[data-hero-pod] { color: rgba(248,242,231,.82) !important; }

/* ── «Эмпатия — это способность» ── */

[data-sfery] { border-radius: 20px; background: #FFFDF9; }
[data-sfery] > div { padding: 17px 20px !important; background: none !important; }
[data-sfery] > div:not(:first-child) { border-top: 1px solid var(--liniya) !important; }
[data-sfery] > div > span:first-child,
[data-sfery] > div:not(:first-child) > span:first-child {
  width: 34px !important; height: auto !important;
  border-radius: 0 !important;
  background: none !important;
  font-family: var(--prata);
  font-size: 24px !important;
  font-weight: 400 !important;
  color: #B88D45 !important;
  padding-top: 0;
}
[data-sfery] > div > span:nth-child(2) { color: var(--vino) !important; }
[data-sfery] > div > span:last-child { font-weight: 500 !important; color: #2B1719 !important; }

[data-tehniki] { gap: 14px 22px; padding: 34px 26px 34px !important; border-radius: 20px !important; box-shadow: none !important; }
[data-tehniki] > span {
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: clamp(84px, 22vw, 124px) !important;
  line-height: .9 !important;
  color: transparent !important;
  background: linear-gradient(180deg, #F6E7BF 0%, #E2C788 45%, #BE9750 100%) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
}
[data-t-lead] { font-family: var(--prata); font-weight: 400; font-size: 23px; line-height: 1.3; }
[data-t-text] { padding-top: 16px; border-top: 1px solid rgba(231,206,148,.3); font-size: 17.5px; color: rgba(248,242,231,.9); }

/* ── программа ── */

[data-cifry] { gap: 0 !important; grid-template-columns: repeat(4, minmax(0, 200px)); border-top: 1px solid var(--liniya); border-bottom: 1px solid var(--liniya); }
[data-cifry] > span,
[data-cifry] > span:nth-child(n) {
  background: none;
  box-shadow: none;
  border-radius: 0;
  padding: 22px 12px 20px 0;
  color: #5F4A49;
  font-size: 15.5px;
  font-weight: 500;
}
[data-cifry] b,
[data-cifry] > span:nth-child(n) b {
  font-family: var(--prata);
  font-weight: 400;
  font-size: 46px !important;
  line-height: 1 !important;
  color: var(--vino) !important;
}

[data-nedelya] { border-radius: 20px; background: #FFFDF9; box-shadow: var(--ten); }
[data-n-title] {
  padding: 30px 26px 26px;
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(27px, 3.4vw, 40px);
  line-height: 1.16;
  letter-spacing: .015em;
  color: var(--zol-svet);
}
[data-n-title]::first-line { color: var(--kost); }
[data-nedelya] ul { padding: 8px 26px; }
[data-nedelya] li { padding: 17px 0; font-size: 18.5px; }
[data-nedelya] li + li { border-top: 1px solid var(--liniya); }
[data-nedelya] li > span,
[data-n-viola] > span {
  background: none !important;
  box-shadow: inset 0 0 0 1px var(--zol);
  border-radius: 50%;
  color: var(--vino);
}
[data-nedelya] li b { font-weight: 600; }
[data-n-foot] { padding: 18px 26px; background: #F6EDDC; border-top: 1px solid var(--liniya); font-weight: 600; font-size: 17.5px; }
[data-n-foot] span { font-family: var(--prata); font-size: 34px; line-height: .8; color: #B88D45; }

[data-week-card] { border-radius: 20px !important; background: #FFFDF9 !important; }
[data-week-head] > div:first-child > span:first-child { background: none !important; box-shadow: inset 0 0 0 1px var(--zol); color: var(--vino) !important; }
[data-week-head] h3 { font-family: var(--prata); font-weight: 400 !important; font-size: clamp(24px, 2.6vw, 30px) !important; line-height: 1.22 !important; }
[data-vopros] {
  align-self: stretch;
  max-width: none;
  margin-top: 6px;
  padding: 2px 0 2px 18px;
  border-radius: 0;
  border-left: 1px solid var(--zol);
  background: none;
  box-shadow: none;
  color: var(--vino);
  font-family: var(--prata);
  font-weight: 400;
  font-size: 19px;
  line-height: 1.42;
  letter-spacing: 0;
}
[data-ava] { background: none; box-shadow: inset 0 0 0 1px var(--zol); color: var(--vino); font-family: var(--prata); font-weight: 400; }
[data-bubble] { background: #F6EDDC; border-radius: 16px 16px 16px 4px; padding: 14px 18px 16px; }
[data-who] { color: #9A7430; font-size: 14.5px; letter-spacing: .04em; }
[data-bubble] p { font-size: 17.5px; line-height: 1.55; }
[data-week-card] [style*="width: 30px; height: 30px"] {
  border-radius: 0 !important;
  background: none !important;
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: 22px !important;
  color: #B88D45 !important;
}

/* ── ответы на вопросы ── */

[data-otvety] { padding: 34px 26px 30px; border-radius: 20px; background: #F6EDDC; box-shadow: var(--ten); }
[data-otvety] > [data-tag] { background: none; }
[data-o-title] {
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(27px, 3.4vw, 40px);
  line-height: 1.16;
  letter-spacing: .015em;
}
[data-o-title]::first-line { color: var(--vino); }
[data-o-text] { font-size: 18.5px; font-weight: 500; line-height: 1.5; }
[data-o-primer] { font-weight: 600; color: #5F4A49; }
[data-audio] { background: #FFFDF9; }
[data-wave] > span { background: var(--vino); }
[data-wave] > i b { background: var(--vino); opacity: .45; }
[data-o-tegi] { color: #9A7430; font-weight: 500; }

/* ── мастер-класс ── */

[data-mk] { background: var(--kost) !important; }
[data-mk-card] {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: clamp(40px, 5vw, 72px) clamp(26px, 4.4vw, 64px);
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

/* Лента. Появляется, когда пришлют файл: на первом экране у края светлой
   карточки, у блока подарков и у последнего призыва. */
[data-h2-card]::before, [data-final]::before, section[aria-label="Подарки и условия"]::before {
  content: "";
  display: none;
  position: absolute;
  right: -40px; top: -58px;
  width: min(300px, 62vw); height: 120px;
  background-position: center;
  background-size: contain;
  background-repeat: no-repeat;
  pointer-events: none;
}
[data-final], section[aria-label="Подарки и условия"] { position: relative; overflow: hidden; }
[data-final]::before, section[aria-label="Подарки и условия"]::before { top: 8px; right: -30px; }
[data-mk-card] > div:first-child {
  background: none !important;
  padding: 0 !important;
  color: var(--zol-svet);
}

/* ── тарифы ── */

#tarify { background-color: var(--noch) !important; }
#tarify > div > h2 { color: var(--kost) !important; }
#tarify > div > p, #tarify > div > div:last-child:not([style*="grid"]) p { color: rgba(248,242,231,.8) !important; }
#tarify > div > div:last-child:not([style*="grid"]) b { color: var(--kost) !important; }
#tarify > div > div:last-child:not([style*="grid"]) a { color: var(--zol-svet) !important; }
#tarify [style*="top: -14px"] {
  background: var(--zoloto) !important;
  color: #2B1719 !important;
  box-shadow: none !important;
  letter-spacing: .08em;
  font-size: 13.5px !important;
  text-transform: uppercase !important;
}
#tarify h3 { font-family: var(--prata); font-weight: 400 !important; }
#tarify span[style*="color: #7A1A2C"] { background: none; box-shadow: inset 0 0 0 1px var(--zol); color: #9A7430 !important; }
#tarify [style*="height: 1px"] { background: var(--liniya) !important; }
[data-cena] { border-radius: 16px; padding: 22px 22px; }
[data-cena] [style*="font-size"] { font-family: var(--prata); font-weight: 400 !important; }
[data-mest] { background: none !important; padding: 0 !important; }
[data-mest] > span:first-child { background: var(--zol) !important; }
[data-mest] > span:last-child { color: #9A7430 !important; }

/* ── подарки, контакты ── */

[data-podarok] { background: #FFFDF9; border-radius: 16px; padding: 18px; }
[data-podarok] > span { background: none !important; box-shadow: inset 0 0 0 1px var(--zol) !important; color: var(--vino) !important; }

/* ── последний призыв ── */

[data-final] { background: var(--kost) !important; }
[data-final-card] { position: relative; overflow: hidden; border-radius: 20px; padding: clamp(44px, 5.4vw, 76px) clamp(26px, 4.4vw, 64px); }
[data-final-card] > div:first-child { background: none !important; border: 1px solid rgba(231,206,148,.45) !important; }
[data-final-card] h2 { font-size: clamp(31px, 4.1vw, 54px) !important; }
[data-final-card] [style*="color: #B3A39B"] { color: rgba(248,242,231,.82) !important; }

/* ── окно заявки и оплата ── */

#lead-modal h2 { font-family: var(--prata) !important; font-weight: 400 !important; text-transform: none; letter-spacing: 0 !important; }
#lead-modal h2::first-line { color: inherit; }
[data-pay-option] { box-shadow: var(--ten); }
[data-pay-option="ru"], [data-pay-option="intl"] { background: #FFFDF9 !important; }
[data-pay-price] { font-family: var(--prata); font-weight: 400 !important; font-size: 40px !important; line-height: 1.1 !important; color: var(--vino) !important; }
#pay-step [data-btn] { letter-spacing: .08em !important; font-size: clamp(14.5px, 4vw, 16px) !important; }

.cookie-bar { border: 1px solid var(--liniya); box-shadow: 0 18px 44px -22px rgba(43,23,25,.5); }
.cookie-bar a { color: var(--vino); }
.cookie-bar button { background: #2B1719; border-radius: 12px; }

/* ── телефон ── */

@media (max-width: 760px) {
  main > section:not([aria-label="Первый экран"]) { padding-left: 22px !important; padding-right: 22px !important; }
  main h2 { font-size: 31px !important; }
  section[aria-label="Зачем мне это"] > div > p:first-child { font-size: min(31px, calc((100vw - 44px) / 10.6)) !important; }
  [data-cifry] { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  [data-cifry] > span:nth-child(n+3) { border-top: 1px solid var(--liniya); }
  [data-btn="primary"] { width: min(100%, 330px); }
  [data-sticky-bar] a { letter-spacing: .08em !important; box-shadow: none !important; }
}
"""
