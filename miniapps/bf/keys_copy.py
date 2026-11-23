#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Копия страницы violamaro.com/keys-of-life для окна «Подробнее о программе» у «Ключей».

    python3 miniapps/bf/keys_copy.py [файл.html]   # скачивает страницу (или берёт файл), пишет miniapps/bf/keys/index.html

Страница Виолы на Тильде не открывается внутри чужих страниц (X-Frame-Options),
поэтому окно показывает её копию с нашего домена (/bf/keys/). Убрано то, чего нет
в записи на чёрной пятнице: верхняя кнопка «Регистрация», кнопки «Стоимость»,
«Бонусы», «Получить ключи», блок бонусов (чат, мастер в чате, лекция), блок цены
(SOLD OUT, «Доступ на 3 месяца»), блок «Служба заботы» (почта и Телеграм третьих лиц),
всплывающее окно Тильды, реклама Google.
"""
import os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://violamaro.com/keys-of-life"
DROP_RECS = ["rec1335415481", "rec1343312821", "rec1335812831", "rec1337671881",
             "rec1335880951", "rec1335916691", "rec1345478371"]
MOVE = [("1758525893908", "top-res-320", "46"),            # «Программа курса» на место «Стоимости» (телефон)
        ("1758525893923", "top", "409")]                       # «Подробная программа» на место «Получить ключи» (ПК)
# первый экран без убранных кнопок: всё ниже меню и кнопок поднимаем, высоту блока уменьшаем
# (брейкпойнт, ниже какой отметки, на сколько поднять; потом «Подробную программу» — на место «Получить ключи»)
HERO = "rec1335498081"
SHIFT = [("320", 60, 77, "1758525893923", 723, 800),       # телефон: 2 убранные строки меню, 940 → 800
         ("640", 70, 52, "1758525893923", 1137, 1256)]     # планшет: 2-я строка меню, 1395 → 1256
DROP_ELEMS = ["1758525893909", "1758525893911", "1758525893922"]   # «Стоимость», «Бонусы», «Получить ключи»


def div_end(s, start):
    """Индекс конца <div …>, начинающегося в start, с учётом вложенных div."""
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", s[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return start + m.end()
    raise ValueError("div не закрыт")


def main():
    import subprocess, sys
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        s = open(src, encoding="utf-8").read()
    else:   # urllib Тильда отдаёт 403, curl — нормально
        s = subprocess.run(["curl", "-sL", URL], capture_output=True, check=True).stdout.decode("utf-8")
    for rid in DROP_RECS:
        a = s.index('<div id="%s"' % rid)
        s = s[:a] + s[div_end(s, a):]
    for eid in DROP_ELEMS:
        m = re.search(r"<div class='t396__elem[^']*'[^>]*data-elem-id='%s'" % eid, s)
        s = s[:m.start()] + s[div_end(s, m.start()):]
    # оставшиеся кнопки ставим на места убранных, чтобы не было пустых мест
    for eid, field, val in MOVE:
        m = re.search(r"<div class='t396__elem[^']*'[^>]*data-elem-id='%s'[^>]*>" % eid, s)
        tag = re.sub(r'data-field-%s-value="[^"]*"' % field, 'data-field-%s-value="%s"' % (field, val), m.group(0))
        s = s[:m.start()] + tag + s[m.end():]
        sel = ".tn-elem[data-elem-id='%s']" % eid
    a = s.index('<div id="%s"' % HERO); b = div_end(s, a); r = s[a:b]
    for bp, below, d, btn, btn_top, h in SHIFT:
        key = 'data-field-top-res-%s-value="' % bp
        def fix(m):
            tag = m.group(0)
            t = re.search(key + r'(-?\d+)"', tag)
            if not t or int(t.group(1)) <= below:
                return tag
            new = btn_top if m.group(1) == btn else int(t.group(1)) - d
            return tag.replace(t.group(0), key + str(new) + '"')
        r = re.sub(r"<div class='t396__elem[^']*'[^>]*data-elem-id='(\d+)'[^>]*>", fix, r)
        old_h = re.search(r'data-artboard-height-res-%s="(\d+)"' % bp, r).group(1)
        r = r.replace('data-artboard-height-res-%s="%s"' % (bp, old_h), 'data-artboard-height-res-%s="%d"' % (bp, h))
        r = r.replace("height:%spx;}" % old_h, "height:%dpx;}" % h)
    s = s[:a] + r + s[b:]
    s = re.sub(r'<script[^>]*adsbygoogle[^>]*>\s*</script>', "", s)
    s = re.sub(r'<script[^>]*>\s*\(adsbygoogle[^<]*</script>', "", s)
    s = s.replace('href="/custom.css', 'href="https://violamaro.com/custom.css')
    s = s.replace("<head>", '<head><meta name="robots" content="noindex, nofollow">', 1)
    for w in ["SOLD", "the_etheric_soul", "pimenova", "Бонус #", "Мастер в чате", "географ", "Доступ на 3"]:
        assert w not in s, w
    os.makedirs(os.path.join(HERE, "keys"), exist_ok=True)
    open(os.path.join(HERE, "keys", "index.html"), "w", encoding="utf-8").write(s)
    print("keys/index.html", len(s))


if __name__ == "__main__":
    main()
