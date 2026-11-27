#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страницы документов чёрной пятницы: /bf/<адрес>/ (список в DOCS).

Две ветки оплаты, документы не пересекаются: рубли — ИП Нижевясова (ru-…),
евро — Viola Maro FZ-LLC (eur-…). Исходники: Страницы-к-публикации/bf-docs/*.md,
рядом .html, сделанные pandoc'ом:

    cd Страницы-к-публикации/bf-docs && for f in *.md; do pandoc "$f" -o "${f%.md}.html"; done


Тексты: Страницы-к-публикации/bf-oferta.md и bf-prilozhenie.md (исходник),
рядом .html, сделанные из них pandoc'ом (как у остальных документов сайта):

    cd Страницы-к-публикации
    pandoc bf-oferta.md -o bf-oferta.html
    pandoc bf-prilozhenie.md -o bf-prilozhenie.html

Оформление и подвал берутся из miniapps/bf/index.html, чтобы документы
выглядели как сама страница и реквизиты жили в одном месте.

    python3 miniapps/bf/dokumenty.py site/bf

Политика, согласия и пользовательское соглашение общие для всего сайта
(/privacy/, /consent/, /consent-ads/, /terms/), здесь не собираются.
"""

import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LEGAL = os.path.join(ROOT, "Страницы-к-публикации", "bf-docs")

# (исходник, адрес /bf/<адрес>/, заголовок страницы, ветка оплаты)
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
    "rub": """<footer class="ft wrap"><p class="ft-h">Продавец</p>
<p>ИП Нижевясова Анна Станиславовна, ОГРНИП 321695200039136, ИНН 690503942107<br>
e-mail: <a href="mailto:mg.ananizh@gmail.com">mg.ananizh@gmail.com</a> · Telegram: <a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a></p></footer>""",
    "eur": """<footer class="ft wrap"><p class="ft-h">Seller</p>
<p>Viola Maro FZ-LLC, Ras Al Khaimah Economic Zone (RAKEZ), United Arab Emirates<br>
License No. 47038543 · Corporate Tax TRN 105638855400001<br>
e-mail: <a href="mailto:violamaropsy@gmail.com">violamaropsy@gmail.com</a> · Telegram: <a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a></p></footer>""",
}

DOC_CSS = """
  body { padding-bottom: 0; }
  .doc-top { border-bottom: 1px solid var(--line); }
  .doc-top a { display: inline-block; padding: 1rem 0; color: var(--muted); text-underline-offset: .18em; }
  .doc { padding-top: 2.2rem; padding-bottom: 3rem; font-size: 1.02rem; }
  .doc h1 { font-size: clamp(1.9rem, 7.5vw, 2.6rem); line-height: 1.15; margin-bottom: 1.4rem; }
  .doc h2 { font-family: var(--golos); font-weight: 650; font-size: 1.2rem; line-height: 1.35; margin: 2.2rem 0 .8rem; }
  .doc h3 { font-family: var(--golos); font-weight: 650; font-size: 1.05rem; line-height: 1.4; margin: 1.6rem 0 .6rem; }
  .doc p, .doc li { text-wrap: pretty; }
  .doc p { margin: 0 0 .8rem; }
  .doc ul, .doc ol { list-style: disc; padding-left: 1.3rem; margin: 0 0 .9rem; }
  .doc li + li { margin-top: .3rem; }
  .doc strong { font-weight: 650; }
  .doc a { color: var(--akcent); text-underline-offset: .18em; }
  .doc hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
  .doc .tw { overflow-x: auto; margin: 0 0 1.2rem; }
  .doc table { border-collapse: collapse; min-width: 100%; font-size: .95rem; }
  .doc th, .doc td { border: 1px solid var(--line); padding: .5rem .65rem; text-align: left; vertical-align: top; }
  .doc th { font-weight: 650; }
  .doc mark.todo { background: #F2D27A; color: #141C15; padding: 0 .2em; border-radius: 2px; }
  .doc code { font-family: inherit; }
  html.embed .doc-top { display: none; }
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
    page = read(os.path.join(HERE, "index.html"))
    style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    for slug, url, title, branch in DOCS:
        footer = FOOTERS[branch]
        src = os.path.join(LEGAL, slug + ".html")
        if not os.path.exists(src):
            # текста ещё нет: страницу не собираем, публикация не падает
            print("  /bf/%s/ пропущена: нет %s" % (url, os.path.relpath(src, ROOT)))
            continue
        frag = read(src)
        # первый заголовок документа становится <h1> страницы
        m = re.search(r"<h([12])[^>]*>(.*?)</h\1>", frag, re.S)
        heading = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", m.group(2))).strip()
        frag = frag[:m.start()] + frag[m.end():]
        # незаполненные места {{...}} подсвечиваем, чтобы их было видно при проверке
        frag = re.sub(r"\{\{(.*?)\}\}", r'<mark class="todo">{{\1}}</mark>', frag, flags=re.S)
        frag = re.sub(r"<table", '<div class="tw"><table', frag)
        frag = re.sub(r"</table>", "</table></div>", frag)
        name = title   # заголовок страницы обычным регистром, подзаголовок документа остаётся

        doc = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#141C15">
<title>%(name)s. Черная пятница от Виолы Маро</title>
<style>%(style)s%(css)s</style>
<script>if (window.top !== window) document.documentElement.classList.add("embed");</script>
</head>
<body>
<header class="doc-top"><div class="wrap"><a href="../">Чёрная пятница от Виолы Маро</a></div></header>
<main class="doc wrap">
<h1>%(name)s</h1>
%(frag)s
</main>
%(footer)s
</body>
</html>
""" % {"name": html.escape(name), "title": html.escape(title), "style": style,
       "css": DOC_CSS, "frag": frag.strip(), "footer": footer}
        write(os.path.join(out, url, "index.html"), doc)
        print("  /bf/%s/ — %s" % (url, name))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site", "bf"))
