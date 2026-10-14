#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сайт практикума внутри теста 2.0: violamaro.ru/test2/programma/.

Под результатом теста человек видит тот же сайт, что на violamaro.ru: первый
экран, «Эмпатия — это способность», шесть недель, формат ответов,
мастер-класс и тарифы, в том же оформлении. Тест вставляет эту страницу
рамкой (iframe) и подгоняет её высоту под содержимое.

Заявка остаётся в тесте: по ней бот узнаёт, что заявка есть. Поэтому кнопки
этой страницы не открывают ничего своего, а просят тест открыть его форму
(postMessage {type: "t2-cta", tarif}), а остальные кнопки «Принять участие»
ведут к тарифам ({type: "t2-tarify"}). Оплаты, рассрочки, подарков, контактов
и подвала здесь нет.

Как собирается. Сборщик сайта делает страницу заявки (--mode zayavka)
в папку site/test2/programma, этот модуль её урезает:

    python3 programma.py

Неделя под сферу человека подсвечивается по адресу: …/programma/#nedelya=3.
"""

import os
import re
import shutil
import subprocess
import sys

import build

OUT = os.path.join(build.ROOT, "site", "test2", "programma")
MINE_TAG = "Самая важная для вас неделя на основе теста"

DROP = ("Проблемы с оплатой", "Рассрочка", "Подарки и условия", "Контакты команды", "Финальный призыв")

CSS = r"""
/* Страница живёт внутри теста: прокручивает её сам тест, у рамки нет
   своей полосы прокрутки и нижней плашки. */
html, body { overflow: hidden; }
[data-sticky-bar], .cookie-bar, .skip, #lead-modal { display: none !important; }
main { padding-bottom: 0 !important; }
#tarify a.t2-tarif-btn[data-btn] { display: flex; align-items: center; justify-content: center; width: 100% !important; min-height: 68px; padding: 14px 14px !important; white-space: normal !important; text-align: center; font-size: 15px !important; letter-spacing: .07em !important; line-height: 1.3 !important; text-decoration: none; }
[data-week-card].t2-mine { box-shadow: 0 0 0 3px #1F4C97, 0 26px 46px -28px rgba(28,26,29,.34) !important; }
.t2-mine-tag { align-self: flex-start; padding: 6px 14px; border-radius: 999px; background: #1F4C97; color: #FFFFFF; font-size: 13.5px; font-weight: 700; line-height: 1.3; }
"""

JS = r"""
(function () {
  var parentWin = window.parent && window.parent !== window ? window.parent : null;
  function post(msg) { if (parentWin) parentWin.postMessage(msg, location.origin); }

  /* Высота страницы — тесту, чтобы рамка была ровно по содержимому. */
  var last = 0;
  function size() {
    var h = Math.ceil(document.documentElement.scrollHeight);
    if (Math.abs(h - last) > 2) { last = h; post({ type: "t2-height", h: h }); }
  }
  window.addEventListener("load", size);
  window.addEventListener("resize", size);
  if (window.ResizeObserver) new ResizeObserver(size).observe(document.body);
  setInterval(size, 1500);
  size();

  /* Кнопки «Принять участие». В карточке тарифа — открыть форму заявки
     в тесте с этим тарифом. Остальные ведут к тарифам: прокручивает тест,
     у этой страницы своей прокрутки нет. */
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("[data-t2-cta]");
    if (!a) return;
    e.preventDefault();
    var tarif = a.getAttribute("data-tarif") || "";
    post(tarif ? { type: "t2-cta", tarif: tarif } : { type: "t2-tarify" });
  });

  /* Неделя под сферу человека: #nedelya=N. */
  var m = /nedelya=(\d)/.exec(location.hash);
  if (m) {
    var cards = document.querySelectorAll("[data-week-card]");
    var card = cards[Number(m[1]) - 1];
    if (card) {
      card.classList.add("t2-mine");
      var head = card.querySelector("[data-week-head]");
      if (head) head.insertAdjacentHTML("afterbegin", '<span class="t2-mine-tag">%(tag)s</span>');
    }
  }
})();
"""


def sec_span(page, label):
    i = page.find('aria-label="%s"' % label)
    if i < 0:
        raise SystemExit("программа для теста: на странице нет блока «%s»" % label)
    a = page.rfind("<section", 0, i)
    blk = build.find_block(page, "section", a)
    return blk[0], blk[3]


def rework(page):
    for label in DROP:
        a, b = sec_span(page, label)
        page = page[:a] + page[b:]

    # тарифы: без валютной строки не обходимся — она есть на сайте; убираем
    # только кнопку рассрочки, а «Оставить заявку» ведёт к форме теста
    a, b = sec_span(page, "Тарифы")
    t = page[a:b]
    t = re.sub(r'<button\b[^>]*data-btn="quiet"[^>]*>.*?</button>', "", t, flags=re.S)
    names = iter(["Самостоятельный", "С Виолой"])

    def card_btn(m):
        style = re.search(r'style="([^"]*)"', m.group(0)).group(1)
        return ('<a class="t2-tarif-btn" href="#" data-t2-cta="" data-tarif="%s" data-btn="primary" '
                'style="%s">Хочу принять участие в&nbsp;этом тарифе</a>' % (next(names), style))
    t = re.sub(r'<button\b[^>]*data-btn="primary"[^>]*>.*?</button>', card_btn, t, flags=re.S)
    k = t.rfind('<div style="max-width: 760px;')       # «Пишем только с этого аккаунта»
    if k > 0:
        blk = build.find_block(t, "div", k)
        t = t[:blk[0]] + t[blk[3]:]
    page = page[:a] + t + page[b:]

    # остальные кнопки «Оставить заявку» — тоже к форме теста
    page = re.sub(r'(<a\b[^>]*?)href="#(?:tarify|zapis)"([^>]*data-btn="primary")',
                  r'\1href="#" data-t2-cta=""\2', page)
    page = re.sub(r"\sdata-open-form=\"[^\"]*\"", "", page)
    # подпись кнопок как на основном сайте
    page = page.replace(">Оставить заявку<", ">Принять участие<")

    # подвал и полоса cookie не нужны; окно заявки сайта остаётся спрятанным:
    # на него опирается site.js
    page = re.sub(r"<footer\b.*?</footer>", "", page, flags=re.S)
    page = re.sub(r'<div class="cookie-bar".*?</div>\s*', "", page, count=1, flags=re.S)
    # в спрятанном окне заявки сайта есть список подарков — убираем и его
    i = page.find("data-modal-gifts")
    if i >= 0:
        a = page.rfind("<div", 0, i)
        blk = build.find_block(page, "div", a)
        page = page[:blk[0]] + page[blk[3]:]
    return page


def build_page():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    subprocess.run([sys.executable, os.path.join(build.ROOT, "build.py"), "--mode", "zayavka",
                    "--theme", "barhat", "--out", OUT, "--base", "/test2/programma", "--docs-root",
                    "--noindex"], check=True, stdout=subprocess.DEVNULL)
    path = os.path.join(OUT, "index.html")
    page = rework(build.read(path))
    page = page.replace("</head>", "<style>%s</style>\n</head>" % CSS, 1)
    page = page.replace("</body>", "<script>%s</script>\n</body>" % (JS % {"tag": MINE_TAG}), 1)
    # Правовых страниц здесь нет: в тесте свои ссылки на документы сайта.
    for name in os.listdir(OUT):
        full = os.path.join(OUT, name)
        if os.path.isdir(full) and name not in ("assets",):
            shutil.rmtree(full)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", " ", page))
    bad = re.findall(r"\w*(?:подар|бонус|анкет|предзапис)\w*", text, flags=re.I)
    if bad:
        print("  программа для теста: на странице есть слова %s" % ", ".join(sorted(set(bad))))
    print("Программа для теста → %s (%d КБ)" % (os.path.relpath(OUT, build.ROOT),
                                                len(page.encode("utf-8")) // 1024))


if __name__ == "__main__":
    build_page()
