#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страницы документов /pe/: оферта и приложение для рублей (ИП) и для евро (Viola Maro FZ-LLC).

Тексты: Страницы-к-публикации/pe-docs/*.md (исходник) и рядом .html, сделанные pandoc'ом.
Комплект собран из комплекта /bf/ под один продукт без акции (см. pe-docs/_ИЗМЕНЕНИЯ.md):

    python3 miniapps/pe/dokumenty.py site/pe

Страницы открываются на отдельных адресах и в окне поверх страницы (iframe, класс embed).
"""

import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LEGAL = os.path.join(ROOT, "Страницы-к-публикации", "pe-docs")

# (исходник, адрес /pe/<адрес>/, заголовок страницы, ветка оплаты)
# rub — продавец ИП Нижевясова, рубли, право РФ; eur — Viola Maro FZ-LLC, евро, право ОАЭ.
DOCS = [
    ("ru-oferta", "oferta", "Публичная оферта", "rub"),
    ("ru-prilozhenie", "prilozhenie", "Приложение № 1 к Публичной оферте", "rub"),
    ("ru-politika", "politika", "Политика обработки персональных данных", "rub"),
    ("ru-soglasie", "soglasie", "Согласие на обработку персональных данных", "rub"),
    ("ru-rassylka", "rassylka", "Согласие на рекламные и информационные сообщения", "rub"),
    ("ru-soglashenie", "soglashenie", "Пользовательское соглашение", "rub"),
    ("eur-oferta", "eur-oferta", "Публичная оферта Viola Maro FZ-LLC", "eur"),
    ("eur-usloviya", "eur-usloviya", "Приложение № 1 к Публичной оферте Viola Maro FZ-LLC", "eur"),
    ("eur-privacy", "eur-privacy", "Политика конфиденциальности Viola Maro FZ-LLC", "eur"),
]

FOOTERS = {
    "rub": """<p class="ft-h">Продавец</p>
<p>ИП Нижевясова Анна Станиславовна, ОГРНИП 321695200039136, ИНН 690503942107<br>
e-mail: <a href="mailto:mg.ananizh@gmail.com">mg.ananizh@gmail.com</a> · Telegram: <a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a></p>""",
    "eur": """<p class="ft-h">Seller</p>
<p>Viola Maro FZ-LLC, Ras Al Khaimah Economic Zone (RAKEZ), United Arab Emirates<br>
License No. 47038543 · Corporate Tax TRN 105638855400001<br>
e-mail: <a href="mailto:violamaropsy@gmail.com">violamaropsy@gmail.com</a> · Telegram: <a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a></p>""",
}

CSS = """
  @font-face { font-family: 'Golos Text'; font-weight: 400 900; font-display: swap; src: url(/assets/fonts/GolosText-cyrillic.woff2) format('woff2'); unicode-range: U+0400-04FF; }
  @font-face { font-family: 'Golos Text'; font-weight: 400 900; font-display: swap; src: url(/assets/fonts/GolosText-latin.woff2) format('woff2'); unicode-range: U+0000-00FF; }
  :root { --ink: #1C1A1D; --muted: #55505A; --line: #E6E1DA; --red: #C4142C; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #fff; color: var(--ink); font-family: 'Golos Text', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; font-size: 17px; line-height: 1.6; -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 820px; margin: 0 auto; padding: 0 20px; }
  .doc-top { border-bottom: 1px solid var(--line); }
  .doc-top a { display: inline-block; padding: 1rem 0; color: var(--muted); text-underline-offset: .18em; }
  .doc { padding-top: 2.2rem; padding-bottom: 3rem; }
  .doc h1 { font-size: clamp(1.9rem, 7.5vw, 2.6rem); line-height: 1.15; margin: 0 0 1.4rem; letter-spacing: -.02em; }
  .doc h2 { font-weight: 700; font-size: 1.2rem; line-height: 1.35; margin: 2.2rem 0 .8rem; }
  .doc h3 { font-weight: 700; font-size: 1.05rem; line-height: 1.4; margin: 1.6rem 0 .6rem; }
  .doc p, .doc li { text-wrap: pretty; }
  .doc p { margin: 0 0 .8rem; }
  .doc ul, .doc ol { padding-left: 1.3rem; margin: 0 0 .9rem; }
  .doc ul { list-style: disc; }
  .doc li + li { margin-top: .3rem; }
  .doc strong { font-weight: 700; }
  .doc a { color: var(--red); text-underline-offset: .18em; word-break: break-word; }
  .doc hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
  .doc blockquote { margin: 0 0 1rem; padding: .8rem 1rem; border-left: 4px solid var(--red); background: #F3F2F0; }
  .doc blockquote p:last-child { margin-bottom: 0; }
  .doc .tw { overflow-x: auto; margin: 0 0 1.2rem; }
  .doc table { border-collapse: collapse; min-width: 100%; font-size: .95rem; }
  .doc th, .doc td { border: 1px solid var(--line); padding: .5rem .65rem; text-align: left; vertical-align: top; }
  .doc th { font-weight: 700; background: #F3F2F0; }
  .doc code { font-family: inherit; }
  .ft { border-top: 1px solid var(--line); padding-top: 1.4rem; padding-bottom: 2rem; font-size: .95rem; color: var(--muted); }
  .ft-h { font-weight: 700; color: var(--ink); margin: 0 0 .4rem; }
  html.embed .doc-top, html.embed .ft { display: none; }
  html.embed .doc { padding-top: 1.2rem; }
"""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main(out):
    for slug, url, title, branch in DOCS:
        src = os.path.join(LEGAL, slug + ".html")
        if not os.path.exists(src):
            print("  /pe/%s/ пропущена: нет %s" % (url, os.path.relpath(src, ROOT)))
            continue
        frag = read(src)
        # первый заголовок документа становится <h1> страницы
        m = re.search(r"<h([12])[^>]*>(.*?)</h\1>", frag, re.S)
        frag = frag[:m.start()] + frag[m.end():]
        frag = re.sub(r"<table", '<div class="tw"><table', frag)
        frag = re.sub(r"</table>", "</table></div>", frag)
        doc = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>%(name)s. Прикладная эмпатия</title>
<style>%(css)s</style>
<script>if (window.top !== window) document.documentElement.classList.add("embed");</script>
</head>
<body>
<header class="doc-top"><div class="wrap"><a href="/pe/">Прикладная эмпатия</a></div></header>
<main class="doc wrap">
<h1>%(name)s</h1>
%(frag)s
</main>
<footer class="ft wrap">%(footer)s</footer>
</body>
</html>
""" % {"name": html.escape(title), "css": CSS, "frag": frag.strip(), "footer": FOOTERS[branch]}
        write(os.path.join(out, url, "index.html"), doc)
        print("  /pe/%s/ — %s" % (url, title))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site", "pe"))
