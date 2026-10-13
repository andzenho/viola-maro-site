# -*- coding: utf-8 -*-
"""Оформление --theme barhat: красное с белым, чистое.

Имя флага осталось от первой пробы. За 13.10.2026 пользователь отверг
тёмно-бордовое («бледно»), чёрное с золотом («цыганский») и сцены
с шёлком и лентами («дёшево») и оставил красное с белым: «яркий, чистый,
дорогой дизайн и воздух». Поэтому здесь два цвета — красный и белый —
ровными плоскостями, без глянца, металла и золота; антиква в заголовках,
большие отступы, мягкие тени у белых карточек.

Работает поверх оформления «море»: сборщик сначала делает всё, что делает
для --theme more (те же блоки, те же слова, те же формы), а потом этот
модуль перекрашивает страницу и добавляет свой слой стилей. Тексты
не меняются.

Картинки вставляются позже. Файлы кладутся в build-assets/tema-barhat/
под именами из SLOTS; пока файла нет, на его месте ровный фон.
"""

import os
import re

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-assets", "tema-barhat")

# имя в стилях → файл в build-assets/tema-barhat/
SLOTS = {
    "viola":  "viola.png",          # Виола на прозрачном фоне, по пояс
    "hero-d": "hero-desktop.jpg",   # готовая сцена с Виолой, горизонтальная
    "hero-m": "hero-mobile.jpg",    # готовая сцена с Виолой, вертикальная
    # объёмные предметы на прозрачном фоне: встают у края блоков
    "o-18":        "o-18.png",         # блок «18 техник»
    "o-programma": "o-programma.png",  # заголовок «Шесть недель»
    "o-mk":        "o-mk.png",         # мастер-класс
    "o-tarify":    "o-tarify.png",     # заголовок «Тарифы»
    "o-podarki":   "o-podarki.png",    # «Что вы получаете?»
    "o-final":     "o-final.png",      # последний призыв
    # объёмные значки на прозрачном фоне, квадратные
    "n1": "n1.png", "n2": "n2.png", "n3": "n3.png",   # шесть недель
    "n4": "n4.png", "n5": "n5.png", "n6": "n6.png",
    "p1": "p1.png", "p2": "p2.png", "p3": "p3.png",   # «каждую неделю вы получаете»
    "p4": "p4.png", "p5": "p5.png",
    "podarok": "podarok.png",                          # подарки
    "mk":     "mk.jpg",             # фото для фона мастер-класса
    "final":  "final.jpg",          # фото для фона последнего призыва
}


def est(name):
    return os.path.exists(os.path.join(DIR, SLOTS[name]))


# ── цвета: «море» → «бархат» ──

HEX = {
    # текст
    "#18213A": "#1C1A1D", "#2B3550": "#343034", "#465068": "#5A5559",
    "#4A546C": "#666064", "#5F687E": "#7A7478", "#9AA3B5": "#B5B0B2",
    # небо → красный шёлк
    "#0E2A66": "#7E0A1A", "#0F2A66": "#7E0A1A", "#102F73": "#8C0C1E",
    "#143A85": "#A30F23", "#174592": "#AB1025", "#1A4A96": "#B51228",
    "#1F56A6": "#C4142C", "#2563BA": "#CE1A32", "#2A6DB8": "#D6223A",
    "#3F86DD": "#E2475B", "#93BBF3": "#F3D9A6",
    # синий текст и номера → красный
    "#1F4C97": "#C4142C",
    # голубые плашки → светло-серое
    "#DCE4F0": "#E9E7E4", "#DCE6F5": "#EFEDEA", "#D9E7F9": "#EFEDEA",
    "#EAF2FC": "#F6F5F3", "#EEF3FB": "#FFFFFF", "#EEF4FD": "#F6F5F3",
    # красный
    # тот же красный другой записью: стили «моря» различают синие галочки
    # и красные метки по цвету в разметке
    "#B01E22": "#C5142C", "#B3161F": "#A30F23", "#B01920": "#A30F23",
    "#DA352C": "#D6223A", "#D22B2B": "#C4142C", "#D2302C": "#C4142C",
    "#E5483D": "#E2475B", "#EC5145": "#E2475B", "#F58D82": "#F3D9A6",
    # золото → бледное
    "#F0B13F": "#E5BE73", "#E39A2B": "#D6A95A", "#EFA533": "#DDB265",
    "#F7CB62": "#F3DFA9", "#F6CF7A": "#F3DFA9", "#FBE3B0": "#F8ECCB",
    "#B07A1E": "#A8802F",
    # сливочная бумага → белое и светло-серое
    "#F7F2EA": "#F3F2F0", "#FBF6EC": "#FAF9F8", "#FBF5EC": "#FAF9F8",
    "#FBF6EE": "#FAF9F8", "#FBF6EF": "#FAF9F8", "#FBF7F1": "#FAF9F8",
    "#FDF9F3": "#FFFFFF", "#FDFAF6": "#FFFFFF", "#FFFBF5": "#FFFFFF",
    "#F4ECDD": "#F1EFEC", "#F7F0E2": "#F5F4F2", "#EFE4D2": "#ECE9E5",
    "#F1E8D8": "#EEEBE7", "#EBDFCA": "#E6E3DF", "#D9CDB6": "#D8D4CF",
    "#E2D3B6": "#DDD9D3", "#FDEBD3": "#FCE9EA", "#FFF3DE": "#FFFFFF",
    "#FCDDC0": "#F5F4F2", "#FDF1D9": "#FBF3E2", "#F8E6C6": "#F5E6C4",
}

RGB = {
    (24, 33, 58): (28, 26, 29), (190, 30, 35): (196, 20, 44),
    (240, 177, 63): (229, 190, 115), (16, 47, 115): (140, 12, 30),
    (13, 36, 92): (126, 10, 26), (15, 42, 102): (126, 10, 26),
    (8, 20, 56): (90, 6, 18), (9, 26, 68): (110, 8, 22),
    (150, 16, 24): (163, 15, 35), (20, 58, 133): (163, 15, 35),
    (214, 140, 30): (214, 169, 90), (26, 74, 150): (181, 18, 40),
    (10, 28, 74): (110, 8, 22), (31, 76, 151): (196, 20, 44),
    (232, 64, 52): (226, 71, 91), (214, 44, 44): (196, 20, 44),
    (227, 154, 43): (214, 169, 90), (251, 246, 236): (250, 249, 248),
    (235, 223, 202): (230, 227, 223),
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
    if path.endswith(".html"):
        text = icons(text)
    if path.endswith(os.path.join("assets", "site.css")):
        text += CSS + slots_css()
    return text


_OBJ = {   # предмет → правило, которое его показывает
    "o-18": "[data-tehniki]::after",
    "o-programma": "section[aria-label=\"Программа шесть недель\"]::before",
    "o-mk": "[data-mk]::before",
    "o-tarify": "#tarify::before",
    "o-podarki": "section[aria-label=\"Подарки и условия\"]::before",
    "o-final": "[data-final]::before",
}


def slots_css():
    """Стили для присланных картинок. Пока файла нет, его правил нет."""
    def url(name):
        return "url(/assets/img/b-%s)" % SLOTS[name]
    out = ["%s { display: block; background-image: %s; }" % (sel, url(name))
           for name, sel in sorted(_OBJ.items()) if est(name)]
    if est("mk"):
        out.append("[data-mk-card]::after { opacity: 1; background-image: linear-gradient(90deg, rgba(178,16,40,.96) 0%, "
                   "rgba(178,16,40,.82) 46%, rgba(178,16,40,.25) 100%), %s; }" % url("mk"))
    if est("final"):
        out.append("[data-final-card]::after { opacity: 1; background-image: linear-gradient(180deg, "
                   "rgba(178,16,40,.72) 0%, rgba(178,16,40,.92) 100%), %s; }" % url("final"))
    return "\n" + "\n".join(out) + "\n" if out else ""


def icons(html):
    """Линейные значки заменяются присланными объёмными (PNG)."""
    def img(name):
        return ('<img data-ik="" src="/assets/img/b-%s" alt="" loading="lazy" decoding="async">'
                % SLOTS[name])

    def numbered(pattern, prefix, text):
        n = [0]

        def one(m):
            n[0] += 1
            name = "%s%d" % (prefix, n[0])
            return m.group(1) + img(name) + m.group(2) if name in SLOTS and est(name) else m.group(0)
        return re.sub(pattern, one, text, flags=re.S)

    svg = r"\s*<svg\b.*?</svg>\s*"
    html = numbered(r'(data-week-head=""[^>]*>\s*<div[^>]*>\s*<span[^>]*>)' + svg + r"(</span>)", "n", html)
    i = html.find('data-sfery=""')
    if i >= 0:
        j = html.find("data-tehniki", i)
        j = j if j > 0 else i + 6000
        html = html[:i] + numbered(r'(<span style="display: inline-flex; color: #[0-9A-F]{6};">)' + svg + r"(</span>)",
                                   "n", html[i:j]) + html[j:]
    i = html.find('data-nedelya=""')
    if i >= 0:
        j = html.find("</ul>", i)
        html = html[:i] + numbered(r"(<li[^>]*><span>)" + svg + r"(</span>)", "p", html[i:j]) + html[j:]
    if est("podarok"):
        html = re.sub(r'(<div data-podarok=""[^>]*>\s*<span[^>]*>)' + svg + r"(</span>)",
                      lambda m: m.group(1) + img("podarok") + m.group(2), html, flags=re.S)
    return html


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
    """Чистый фон первого экрана: красное поле слева, светлое справа,
    граница по диагонали. Фигура встаёт на границе."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = size
    grad = Image.linear_gradient("L").resize(size, Image.LANCZOS)
    red = Image.composite(Image.new("RGB", size, (178, 16, 40)), Image.new("RGB", size, (222, 30, 56)), grad)
    light = Image.new("L", size, 0)
    ImageDraw.Draw(light).polygon(
        [(w * (glow[0] + 0.06), 0), (w, 0), (w, h), (w * (glow[0] - 0.20), h)], fill=255)
    light = light.filter(ImageFilter.GaussianBlur(2))
    pale = Image.linear_gradient("L").rotate(90, expand=True).resize(size)
    white = Image.composite(Image.new("RGB", size, (232, 230, 227)), Image.new("RGB", size, (250, 249, 248)), pale)
    return Image.composite(white, red, light)


def scene(name, size):
    """Присланная сцена, обрезанная под кадр. None, если файла нет."""
    if not est(name):
        return None
    from PIL import Image, ImageOps
    im = Image.open(os.path.join(DIR, SLOTS[name])).convert("RGB")
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.4))


CSS = r"""

/* ───────────────────────────── оформление «чисто» (--theme barhat) ── */

:root {
  --vino: #C4142C;
  --noch: #A30F23;
  --zol: #E2B96A;
  --zol-svet: #FFFFFF;
  --kost: #FFFFFF;
  --fon: #F3F2F0;
  --liniya: #E9E6E2;
  --barhat: linear-gradient(150deg, #DE1E38 0%, #C4142C 62%, #B21028 100%);
  --sky: var(--barhat);
  --panel: linear-gradient(160deg, #FFFFFF 0%, #F6F5F3 100%);
  --spot: linear-gradient(160deg, #FFFFFF 0%, #F6F5F3 100%);
  --zoloto: linear-gradient(#FCE9EA, #FCE9EA);
  --tochki: linear-gradient(transparent, transparent);
  --ten: 0 1px 2px rgba(28,26,29,.04), 0 22px 44px -30px rgba(28,26,29,.2);
  --blesk: 0 16px 30px -16px rgba(196,20,44,.55);
  --prata: 'Prata', 'Times New Roman', Georgia, serif;
}

body { background: var(--fon); }

[data-h2], [data-mk-card], [data-final-card], [data-tehniki], [data-n-title], [data-cena] {
  background-image: var(--barhat) !important;
  background-size: cover !important;
  background-position: center !important;
}

/* ── заголовки ── */

main h2,
section[aria-label="Зачем мне это"] > div > p:first-child {
  font-family: var(--prata) !important;
  font-weight: 400 !important;
  font-size: clamp(33px, 4.4vw, 60px) !important;
  line-height: 1.12 !important;
  letter-spacing: .02em !important;
  text-transform: uppercase;
  text-wrap: balance;
  color: #1C1A1D;
}
main h2::first-line,
section[aria-label="Зачем мне это"] > div > p:first-child::first-line { color: var(--vino); }
[data-mk-card] h2, [data-final-card] h2 { color: #FFFFFF !important; }
[data-mk-card] h2::first-line, [data-final-card] h2::first-line { color: var(--zol-svet); }

main.doc h2 { font-family: 'Golos Text', system-ui, sans-serif !important; text-transform: none; letter-spacing: -.015em !important; }
main.doc h2::first-line { color: inherit; }

/* ── блоки: белое и светло-серое чередуются, красное — акцентом ── */

main > section:not([aria-label="Первый экран"]):not([data-mk]):not([data-final]) {
  padding-top: clamp(76px, 10vw, 150px) !important;
  padding-bottom: clamp(76px, 10vw, 150px) !important;
}
main > section:not([aria-label="Первый экран"]) { background: var(--fon) !important; }
main > section[aria-label="Программа шесть недель"],
main > section[aria-label="Рассрочка"],
main > section[aria-label="Контакты команды"] { background: #FFFFFF !important; }
main [style*="border-radius: 14px"], main [style*="border-radius: 16px"] { border-radius: 26px !important; }

/* ── метки ── */

[data-tag],
main [style*="text-transform: uppercase"][style*="color: #C5142C"] {
  background: #FCE9EA;
  padding: 6px 14px;
  border-radius: 999px;
  color: var(--vino) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  letter-spacing: .1em !important;
  text-transform: uppercase !important;
}
[data-tag="siniy"] { background: var(--vino); color: #FFFFFF !important; border-radius: 999px; }
[data-nedelya] [data-tag] { white-space: normal; letter-spacing: .06em !important; font-size: 12.5px !important; border-radius: 12px; }

/* ── кнопки: красная глянцевая на светлом, золотистая на красном ── */

[data-btn] { border-radius: 16px !important; }
[data-btn="primary"] {
  min-height: 70px;
  padding: 18px 42px !important;
  border: 0 !important;
  border-radius: 16px !important;
  background: #C4142C !important;
  box-shadow: var(--blesk) !important;
  color: #FFFFFF !important;
  font-size: 16.5px !important;
  font-weight: 700 !important;
  letter-spacing: .1em !important;
}
[data-btn="primary"]:hover { filter: brightness(1.06); }
[data-h2] [data-btn="primary"], [data-hero-stage] [data-btn="primary"],
[data-mk-card] [data-btn="primary"], [data-final-card] [data-btn="primary"] {
  background: #FFFFFF !important;
  box-shadow: 0 18px 34px -18px rgba(70,4,14,.6) !important;
  color: #C4142C !important;
}
[data-btn="quiet"] {
  min-height: 70px;
  padding: 18px 42px !important;
  border: 1.5px solid var(--vino) !important;
  border-radius: 16px !important;
  background: #FFFFFF !important;
  box-shadow: none !important;
  color: var(--vino) !important;
  font-size: 16.5px !important;
  letter-spacing: .1em !important;
}
[data-btn="quiet"]:hover { background: #FCE9EA !important; filter: none; }
#tarify [data-btn="primary"], #pay-step [data-btn="primary"] { box-shadow: var(--blesk) !important; }
[data-btn="support"]:hover { background: #F6F5F3 !important; }

/* ── первый экран, телефон ── */

@media (max-width: 900px) {
  [data-h2] { background-color: var(--noch); }
  [data-h2-top] { gap: 16px; padding-top: 26px; }
  [data-h2-chips] { gap: 8px; }
  [data-h2-chips] span {
    min-width: 0;
    flex-direction: row;
    gap: 6px;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    font-size: 14.5px;
    white-space: nowrap;
  }
  [data-h2-chips] i { color: rgba(255,255,255,.86); }
  [data-h2-chips] b { font-size: 14.5px; font-weight: 700; color: #FFFFFF; }
  [data-h2-chips] em { display: none; }
  [data-h2-title] {
    margin-top: 12px;
    font-family: var(--prata);
    font-weight: 400;
    font-size: min(calc((100vw - 36px) / (var(--bukv, 10) * .75)), 96px);
    line-height: 1.06;
    letter-spacing: .02em;
    color: #FFFFFF;
    text-shadow: none;
  }
  [data-h2-sub] { font-weight: 500; font-size: 17px; color: rgba(255,255,255,.94); }
  [data-h2-top] a[data-btn] { margin-top: 10px; }
  [data-h2-photo] { margin-top: 14px; }
  [data-h2-fon] { display: none; }
  /* светлый круг за фигурой: она отделяется от красного, как на светлой
     половине широкого экрана */
  [data-h2-photo]::before {
    content: "";
    position: absolute; left: 50%; bottom: -34%;
    width: 132%; aspect-ratio: 1;
    transform: translateX(-50%);
    border-radius: 50%;
    background: linear-gradient(180deg, #FFFFFF 0%, #E9E7E4 70%);

  }
  [data-h2-card] {
    gap: 16px;
    margin-top: -64px;
    padding: 34px 24px 42px;
    border-radius: 34px 34px 0 0;
    background: #FFFFFF;
    box-shadow: 0 -22px 44px -26px rgba(28,26,29,.5);
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
    padding: 14px 18px;
    border-radius: 16px;
    background: var(--fon);
    font-size: 16.5px;
    color: #5A5559;
  }
}
[data-h2-tag] { background: #FFFFFF; color: #C4142C; font-weight: 700; font-size: 14.5px; }
[data-h2-chto] { font-family: var(--prata); font-weight: 400; letter-spacing: .01em; }
[data-h2-list] li { background: var(--fon); box-shadow: none; font-weight: 600; font-size: 18px; }
[data-h2-list] li::before { background: var(--vino); }

/* ── первый экран, широкий ── */

section[aria-label="Первый экран"] { background: var(--noch) !important; color: #FFFFFF !important; }
@media (min-width: 901px) {
  [data-hero-stage] { border-radius: 0 0 44px 44px; }
  [data-hero-stage] [data-hero-copy] > [data-hero-card] {
    max-width: min(620px, 47vw) !important;
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
    letter-spacing: .02em !important;
    color: #FFFFFF !important;
    text-shadow: none !important;
  }
}
@media (min-width: 901px) and (max-width: 1200px) {
  [data-hero-stage] [data-hero-copy] > [data-hero-card] { max-width: 41vw !important; }
  [data-hero-stage] [data-hero-card] h1 { font-size: 4.1vw !important; }
}
[data-hero-card] { background: none; }
[data-hero-stage] [data-hero-card] > div:first-child > div:first-child {
  color: #FFFFFF !important;
  font-size: 14px !important;
  font-weight: 600;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
}
[data-hero-stage] [data-hero-card] > div:last-child > p:first-child { color: #FFFFFF !important; font-weight: 500 !important; }
[data-hero-stage] [data-hero-card] > div:last-child > p:nth-child(2) {
  color: rgba(255,255,255,.92) !important;
  background: rgba(255,255,255,.14) !important;
  border-left: 0 !important;
  border-radius: 16px !important;
  padding: 12px 16px !important;
}
[data-hero-card] > div:last-child > div > div { background: rgba(255,255,255,.16) !important; border: 0 !important; }
[data-hero-stage] [data-hero-card] > div:last-child > div > div > span:last-child { color: #FFFFFF !important; }
[data-hero-stage] [data-hero-card] p[data-hero-pod] { color: rgba(255,255,255,.92) !important; }

/* ── значки: красные глянцевые плитки с белым знаком ── */

[data-nedelya] li > span, [data-n-viola] > span,
[data-week-head] > div:first-child > span:first-child,
[data-podarok] > span {
  border-radius: 16px !important;
  background: #C4142C !important;
  box-shadow: none !important;
  color: #FFFFFF !important;
}
[data-n-viola] > span, [data-podarok] > span { background: #FCE9EA !important; box-shadow: none !important; color: #C4142C !important; }

/* ── «Эмпатия — это способность» ── */

[data-sfery] { border-radius: 26px; background: #FFFFFF; box-shadow: var(--ten); }
[data-sfery] > div { padding: 16px 20px !important; background: none !important; }
[data-sfery] > div:not(:first-child) { border-top: 1px solid var(--liniya) !important; }
[data-sfery] > div > span:first-child,
[data-sfery] > div:not(:first-child) > span:first-child {
  width: 40px !important; height: 40px !important;
  border-radius: 12px !important;
  background: #FCE9EA !important;
  font-family: var(--prata);
  font-size: 22px !important;
  font-weight: 400 !important;
  color: var(--vino) !important;
  padding-top: 0;
}
[data-sfery] > div:first-child > span:first-child { background: var(--vino) !important; color: #FFFFFF !important; }
[data-sfery] > div > span:nth-child(2) { color: var(--vino) !important; }
[data-sfery] > div > span:last-child { font-weight: 600 !important; color: #1C1A1D !important; }

[data-tehniki] { gap: 14px 22px; padding: 34px 28px 34px !important; border-radius: 26px !important; box-shadow: none !important; }
[data-tehniki] > span {
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: clamp(92px, 24vw, 132px) !important;
  line-height: .9 !important;
  color: var(--zol-svet) !important;
  
}
[data-t-lead] { font-family: var(--prata); font-weight: 400; font-size: 23px; line-height: 1.3; }
[data-t-text] { padding-top: 16px; border-top: 1px solid rgba(255,255,255,.3); font-size: 17.5px; color: rgba(255,255,255,.95); }

/* ── программа ── */

[data-cifry] { gap: 12px !important; grid-template-columns: repeat(4, minmax(0, 210px)); }
[data-cifry] > span, [data-cifry] > span:nth-child(n) {
  border-radius: 22px;
  padding: 20px 20px 18px;
  font-size: 16px;
  font-weight: 600;
}
[data-cifry] b, [data-cifry] > span:nth-child(n) b { font-family: var(--prata); font-weight: 400; font-size: 52px !important; line-height: 1 !important; }
[data-cifry] > span:nth-child(odd) { background: var(--barhat); color: #FFFFFF; }
[data-cifry] > span:nth-child(odd) b { color: var(--zol-svet) !important; }
[data-cifry] > span:nth-child(even) { background: #FFFFFF; color: #343034; box-shadow: var(--ten); }
[data-cifry] > span:nth-child(even) b { color: var(--vino) !important; }

[data-nedelya] { border-radius: 26px; background: #FFFFFF; box-shadow: var(--ten); }
[data-n-title] {
  padding: 30px 26px 26px;
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(28px, 3.5vw, 42px);
  line-height: 1.16;
  letter-spacing: .02em;
  color: var(--zol-svet);
}
[data-n-title]::first-line { color: #FFFFFF; }
[data-nedelya] ul { padding: 8px 24px; }
[data-nedelya] li { grid-template-columns: 52px minmax(0, 1fr); padding: 15px 0; font-size: 18.5px; }
[data-nedelya] li > span { width: 52px; height: 52px; }
[data-nedelya] li + li { border-top: 1px solid var(--liniya); }
[data-n-foot] { padding: 18px 26px; background: #FCE9EA; font-weight: 700; font-size: 17.5px; color: #1C1A1D; }
[data-n-foot] span { font-family: var(--prata); font-size: 34px; line-height: .8; color: #C4142C; }

[data-week-card] { border-radius: 26px !important; background: #FFFFFF !important; box-shadow: var(--ten) !important; }
[data-week-head] > div:first-child > span:first-child { width: 52px !important; height: 52px !important; }
[data-week-head] h3 { font-family: var(--prata); font-weight: 400 !important; font-size: clamp(25px, 2.7vw, 32px) !important; line-height: 1.2 !important; }
[data-vopros] {
  align-self: stretch;
  max-width: none;
  margin-top: 4px;
  padding: 16px 18px;
  border-radius: 18px;
  background: #FCE9EA;
  box-shadow: none;
  color: #A30F23;
  font-family: var(--prata);
  font-weight: 400;
  font-size: 19px;
  line-height: 1.4;
  letter-spacing: 0;
}
[data-ava] { background: var(--vino); color: #FFFFFF; font-family: var(--prata); font-weight: 400; }
[data-bubble] { background: var(--fon); border-radius: 18px 18px 18px 6px; padding: 14px 18px 16px; }
[data-who] { color: var(--vino); font-size: 14.5px; }
[data-bubble] p { font-size: 17.5px; line-height: 1.55; }
[data-week-card] [style*="width: 30px; height: 30px"] {
  width: 36px !important; height: 36px !important;
  border-radius: 11px !important;
  background: #FCE9EA !important;
  font-family: var(--prata);
  font-weight: 400 !important;
  font-size: 20px !important;
  color: var(--vino) !important;
}
[data-week-card] [style*="grid-template-columns: 30px 1fr"] { grid-template-columns: 36px 1fr !important; }

/* ── ответы на вопросы ── */

[data-otvety] { padding: 34px 26px 30px; border-radius: 26px; background: #FFFFFF; box-shadow: var(--ten); }
[data-otvety] > [data-tag] { background: #FCE9EA; }
[data-o-title] {
  font-family: var(--prata);
  font-weight: 400;
  font-size: clamp(28px, 3.5vw, 42px);
  line-height: 1.16;
  letter-spacing: .02em;
  color: #1C1A1D;
}
[data-o-title]::first-line { color: #C4142C; }
[data-o-text] { font-size: 18.5px; font-weight: 600; line-height: 1.5; }
[data-audio] { background: var(--fon); }
[data-wave] > span { background: var(--vino); }
[data-wave] > i b { background: var(--vino); opacity: .5; }
[data-o-tegi] { color: var(--vino); }

/* ── мастер-класс ── */

[data-mk] { background: var(--fon) !important; }
[data-mk-card] {
  position: relative;
  overflow: hidden;
  border-radius: 30px;
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
[data-mk-card] > div:first-child { background: rgba(255,255,255,.18) !important; color: #FFFFFF; }

/* ── тарифы ── */

#tarify [style*="top: -14px"] {
  background: #C4142C !important;
  color: #FFFFFF !important;
  box-shadow: none !important;
  letter-spacing: .08em;
  font-size: 13.5px !important;
  text-transform: uppercase !important;
}
#tarify > div > div[style*="grid"] > div { box-shadow: var(--ten) !important; border: 0 !important; }
#tarify > div > div[style*="grid"] > div:last-child { box-shadow: 0 0 0 2px var(--vino), var(--ten) !important; }
#tarify h3 { font-family: var(--prata); font-weight: 400 !important; }
#tarify span[style*="color: #C4142C"] { background: #FCE9EA; color: var(--vino) !important; }
#tarify [style*="height: 1px"] { background: var(--liniya) !important; }
[data-cena] { border-radius: 20px; padding: 22px 22px;  }
[data-cena] [style*="font-size"] { font-family: var(--prata); font-weight: 400 !important; }
[data-mest] { background: #FCE9EA !important; }
[data-mest] > span:first-child { background: var(--vino) !important; }
[data-mest] > span:last-child { color: var(--vino) !important; }

/* ── подарки, контакты ── */

[data-podarok] { background: #FFFFFF; border-radius: 22px; padding: 18px; box-shadow: var(--ten); grid-template-columns: 54px 1fr !important; }
[data-podarok] > span { width: 54px !important; height: 54px !important; }

/* ── последний призыв ── */

[data-final] { background: var(--fon) !important; }
[data-final-card] {
  position: relative; overflow: hidden;
  border-radius: 30px;
  padding: clamp(44px, 5.4vw, 76px) clamp(26px, 4.4vw, 64px);
  
}
[data-final-card] > div:first-child { background: rgba(255,255,255,.18) !important; border: 0 !important; }
[data-final-card] h2 { font-size: clamp(33px, 4.4vw, 60px) !important; }
[data-final-card] [style*="color: #B5B0B2"] { color: rgba(255,255,255,.92) !important; }

/* ── окно заявки и оплата ── */

#lead-modal h2 { font-family: var(--prata) !important; font-weight: 400 !important; text-transform: none; letter-spacing: 0 !important; color: #1C1A1D; }
#lead-modal h2::first-line { color: inherit; }
[data-pay-option] { box-shadow: var(--ten); }
[data-pay-option="ru"], [data-pay-option="intl"] { background: #FFFFFF !important; }
[data-pay-price] { font-family: var(--prata); font-weight: 400 !important; font-size: 40px !important; line-height: 1.1 !important; color: var(--vino) !important; }
#pay-step [data-btn] { letter-spacing: .06em !important; font-size: clamp(14.5px, 4vw, 16px) !important; }

.cookie-bar { border: 1px solid var(--liniya); box-shadow: 0 18px 44px -22px rgba(28,26,29,.5); }
.cookie-bar a { color: var(--vino); }
.cookie-bar button { background: #1C1A1D; border-radius: 12px; }

/* ── телефон ── */

@media (max-width: 760px) {
  main > section:not([aria-label="Первый экран"]) { padding-left: 20px !important; padding-right: 20px !important; }
  main h2 { font-size: 33px !important; }
  section[aria-label="Зачем мне это"] > div > p:first-child { font-size: min(33px, calc((100vw - 40px) / 10.2)) !important; }
  [data-cifry] { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  [data-btn="primary"] { width: min(100%, 330px); }
  [data-sticky-bar] a { letter-spacing: .06em !important; }
}

/* ── фигуры: дуги, кольца, крупные цифры ── */

/* Белые блоки — большими скруглёнными листами на сером. */
main > section[aria-label="Программа шесть недель"],
main > section[aria-label="Рассрочка"],
main > section[aria-label="Контакты команды"] { border-radius: clamp(36px, 6vw, 80px); }

/* Первый экран снизу закрыт дугой. */
@media (min-width: 901px) {
  [data-hero-stage] { border-radius: 0 0 50% 50% / 0 0 70px 70px; }
}

/* Кольца на красных блоках. */
[data-tehniki], [data-mk-card], [data-final-card], [data-cena], [data-n-title] { position: relative; overflow: hidden; }
[data-tehniki]::before, [data-mk-card]::before, [data-final-card]::before, [data-cena]::before, [data-n-title]::before {
  content: "";
  position: absolute;
  right: -90px; top: -110px;
  width: 300px; height: 300px;
  border-radius: 50%;
  box-shadow:
    0 0 0 1.5px rgba(255,255,255,.24),
    0 0 0 44px rgba(255,255,255,.035),
    0 0 0 45.5px rgba(255,255,255,.18),
    0 0 0 92px rgba(255,255,255,.02),
    0 0 0 93.5px rgba(255,255,255,.12);
  pointer-events: none;
}
[data-cena]::before, [data-n-title]::before { width: 150px; height: 150px; right: -50px; top: -70px; }
[data-tehniki] > *, [data-cena] > *, [data-n-title] > * { position: relative; z-index: 1; }
[data-final-card]::before { right: auto; left: -110px; top: auto; bottom: -130px; }

/* Карточка недели: крупный номер тенью в углу, один угол срезан дугой. */
section[aria-label="Программа шесть недель"] { counter-reset: ned; }
[data-week-card] { position: relative; counter-increment: ned; border-radius: 26px 26px 84px 26px !important; }
[data-week-card]::before {
  content: "0" counter(ned);
  position: absolute;
  right: 16px; top: -6px;
  font-family: var(--prata);
  font-size: 104px;
  line-height: 1;
  color: #FCE9EA;
  pointer-events: none;
}
[data-week-card] > * { position: relative; z-index: 1; }
[data-vopros] { border-radius: 4px 22px 22px 22px; }
[data-podarok] { border-radius: 22px 22px 22px 6px; }
[data-sfery] { border-radius: 26px 26px 26px 64px; }
[data-tehniki] { border-radius: 26px 64px 26px 26px !important; }
[data-nedelya] { border-radius: 26px 64px 26px 26px; }
[data-mk-card], [data-final-card] { border-radius: 30px 30px 96px 30px; }
#tarify > div > div[style*="grid"] { gap: 40px 24px !important; }

/* ── присланные картинки ── */

/* Объёмные значки вместо линейных. */
img[data-ik] { display: block; width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 10px 12px rgba(120,10,26,.28)); }
span:has(> img[data-ik]),
[data-week-head] > div:first-child > span:first-child:has(> img[data-ik]),
[data-nedelya] li > span:has(> img[data-ik]),
[data-podarok] > span:has(> img[data-ik]) { background: none !important; box-shadow: none !important; border-radius: 0 !important; }
[data-week-head] > div:first-child > span:has(> img[data-ik]) { width: 76px !important; height: 76px !important; }
[data-nedelya] li:has(img[data-ik]) { grid-template-columns: 64px minmax(0, 1fr); }
[data-nedelya] li > span:has(> img[data-ik]) { width: 64px; height: 64px; }
[data-podarok]:has(img[data-ik]) { grid-template-columns: 68px 1fr !important; }
[data-podarok] > span:has(> img[data-ik]) { width: 68px !important; height: 68px !important; }
[data-sfery] span:has(> img[data-ik]) { width: 34px; height: 34px; }

/* Предметы у края блоков. Появляются, когда пришлют файл. */
[data-tehniki]::after, [data-mk]::before, [data-final]::before, #tarify::before,
section[aria-label="Подарки и условия"]::before, section[aria-label="Программа шесть недель"]::before {
  content: "";
  display: none;
  position: absolute;
  z-index: 2;
  width: clamp(120px, 30vw, 220px);
  aspect-ratio: 1;
  background-position: center;
  background-size: contain;
  background-repeat: no-repeat;
  filter: drop-shadow(0 22px 26px rgba(120,10,26,.3));
  pointer-events: none;
}
[data-mk], [data-final], #tarify, section[aria-label="Подарки и условия"], section[aria-label="Программа шесть недель"] { position: relative; }
[data-tehniki] { overflow: visible; }
[data-tehniki]::before { clip-path: inset(0 round 26px 64px 26px 26px); }
[data-tehniki]::after { right: -8px; bottom: -46px; width: clamp(96px, 24vw, 150px); }
section[aria-label="Программа шесть недель"]::before { right: max(8px, calc(50% - 560px)); top: -56px; width: clamp(110px, 26vw, 200px); }
[data-mk]::before { right: max(6px, calc(50% - 500px)); top: -40px; }
#tarify::before { right: max(6px, calc(50% - 520px)); top: -10px; width: clamp(96px, 22vw, 180px); }
section[aria-label="Подарки и условия"]::before { right: max(6px, calc(50% - 520px)); top: -44px; width: clamp(96px, 22vw, 180px); }
[data-final]::before { right: max(6px, calc(50% - 400px)); top: -30px; }
"""
