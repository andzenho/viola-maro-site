#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Три страницы оплаты по одному простому шаблону (правка 19.10.2026).

    /             полная оплата (и рассрочка банка на странице GetPlatinum)
    /rassrochka/  внутренняя рассрочка, один платёж из двух, noindex
    /bron/        бронь места

На странице только оффер и форма: выбор тарифа плитками, имя, телефон,
Telegram, согласия как были. Кнопка пишет контакты в таблицу (тот же приёмник
и та же запись, что у прежней формы сайта: лист «Заявки на продукт») и
открывает прежнее окно «Способ оплаты»: российская карта или зарубежная,
ссылки и суммы из словаря PAY в build.py. Цена на плитке берётся оттуда же,
поэтому сумма на странице всегда та, что спишет платёжная страница.

Шапку, окно оплаты, подвал, cookie и скрипты даёт обычная сборка build.py
этой страницы; модуль заменяет всё содержимое между ними:

    python3 build.py --theme barhat --noindex
    python3 build.py --mode rassrochka --theme barhat --out site/rassrochka --base /rassrochka --docs-root --noindex
    python3 build.py --mode bron --theme barhat --out site/bron --base /bron --noindex
    python3 oplata.py

Новая главная с таймером, историями и заявкой живёт на /zayavka/ (glavnaya.py).
"""

import html as html_mod
import json
import os
import re

import build

SITE = os.path.join(build.ROOT, "site")

OFFER_TITLE = "Прикладная эмпатия"
OFFER_TEXT = ("Шестинедельная программа, на которой вы вместе с Виолой Маро учитесь пользоваться "
              "своей эмпатией, чтобы перестать спасать всех, уступать и терпеть тех, кто вами "
              "пользуется, и начать себя любить, ценить и уважать")
OFFER_META = "Старт 1 ноября · 6 недель · лекции в записи, доступ навсегда"
ACCOUNTS = ('Пишем только с аккаунта команды Виолы <a href="https://t.me/violamaroteam" '
            'target="_blank" rel="noopener">@violamaroteam</a>')
CHEK = "Оплата и чек от ИП Нижевясова А. С."
FORM_H = "Выберите тариф и оставьте контакты, на них придут доступы"

LINE_FULL = "Вся программа и мои ответы голосом на ваши вопросы"
LINE_BASIC = "Вся программа в вашем темпе"


def rub(v):
    return v.replace(" ", " ") + " ₽"


def full_price(k):
    return rub(build.PAY["pay"]["plans"][k]["rub"])


# Страница: папка в site/, ключ в PAY, тексты. Плитки: (ключ тарифа в PAY
# этой страницы, название, строка, мелкая строка, метка).
PAGES = [
    {
        "dir": "", "pay": "pay",
        "title": "Прикладная эмпатия: оплата участия",
        "desc": "Оплата участия в шестинедельной программе Виолы Маро «Прикладная эмпатия». Старт 1 ноября.",
        "sub": "Оплата участия", "sub2": "", "bron": [],
        "form_h": FORM_H,
        "tiles": [("full", "С Виолой", LINE_FULL, "", "50 мест"),
                  ("basic", "Самостоятельный", LINE_BASIC, "", "")],
        "under": ("Можно оплатить в рассрочку банка на 3, 6 или 12 месяцев без процентов, первый "
                  "платёж через месяц. Для граждан стран СНГ по паспорту, 18+"),
        "btn": "Перейти к оплате", "noindex": False,
    },
    {
        "dir": "rassrochka", "pay": "rassrochka",
        "title": "Прикладная эмпатия: оплата по внутренней рассрочке",
        "desc": "Оплата участия в программе «Прикладная эмпатия» двумя равными платежами.",
        "sub": "Оплата по внутренней рассрочке",
        "sub2": "Стоимость тарифа делится на два равных платежа. Здесь вы вносите первый",
        "bron": [],
        "form_h": FORM_H,
        "tiles": [("full", "С Виолой", "Один платёж из двух", "Полная цена " + full_price("full"), ""),
                  ("basic", "Самостоятельный", "Один платёж из двух", "Полная цена " + full_price("basic"), "")],
        "under": "", "btn": "Внести платёж", "noindex": True,
    },
    {
        "dir": "bron", "pay": "bron",
        "title": "Прикладная эмпатия: бронь места",
        "desc": "Бронь места в программе «Прикладная эмпатия». Старт 1 ноября.",
        "sub": "Бронь места", "sub2": "",
        "bron": [
            "Бронь %s, с зарубежной карты $%s или €%s" % (
                rub(build.PAY["bron"]["plans"]["bron"]["rub"]),
                build.PAY["bron"]["plans"]["bron"]["usd"], build.PAY["bron"]["plans"]["bron"]["eur"]),
            "Засчитывается в стоимость участия, остаток вносится до %s" % build.BOOKING_DEADLINE,
            "Если не доплатите до старта, бронь переносится на следующий поток или другой продукт Виолы",
        ],
        "form_h": "Выберите тариф и оставьте контакты, пришлём доступы",
        # Сумма брони одна на оба тарифа: тариф нужен команде, оплата идёт по брони.
        "tiles": [("bron", "С Виолой", LINE_FULL, "полная цена " + full_price("full"), ""),
                  ("bron", "Самостоятельный", LINE_BASIC, "полная цена " + full_price("basic"), "")],
        "under": "", "noindex": False,
        "btn": "Внести бронь " + rub(build.PAY["bron"]["plans"]["bron"]["rub"]),
    },
]


def site_js_setting(name):
    js = build.read(os.path.join(build.BUILD_ASSETS, "site.js"))
    m = re.search(r"var %s = '([^']*)';" % name, js)
    if not m:
        raise SystemExit("оплата: в site.js нет %s" % name)
    return m.group(1)


def doc_versions():
    js = build.read(os.path.join(build.BUILD_ASSETS, "site.js"))
    return dict(re.findall(r"(doc_version_\w+): '([^']*)'", js))


def block(page, tag, needle):
    i = page.find(needle)
    if i < 0:
        raise SystemExit("оплата: на странице не найдено %s" % needle)
    a = page.rfind("<" + tag, 0, i)
    b = build.find_block(page, tag, a)
    return b[0], b[3]


def checkbox_text(modal, name):
    """Текст согласия из окна сайта, слово в слово: формулировки утверждены юристом."""
    m = re.search(r'name="%s"[^>]*>\s*<span[^>]*>\s*<span[^>]*>(.*?)</span>\s*<span' % name, modal, re.S)
    if not m:
        raise SystemExit("оплата: в окне нет согласия %s" % name)
    t = re.sub(r'\s(?:class|style)="[^"]*"', "", m.group(1))
    return re.sub(r"\s+", " ", t).strip()


def tile_html(p, i, t):
    key, name, line, small, mark = t
    plan = build.PAY[p["pay"]]["plans"][key]
    price = ""
    if p["pay"] != "bron":
        price = ('<span class="op-t-price">%s</span><span class="op-t-val">$%s / €%s</span>'
                 % (rub(plan["rub"]), plan["usd"], plan["eur"]))
    return """
        <label class="op-tile">
          <input type="radio" name="tarif" value="%(name)s" data-pay="%(key)s"%(chk)s>
          <span class="op-t-box">
            <span class="op-t-head"><b class="op-t-name">%(name)s</b>%(mark)s</span>
            <span class="op-t-line">%(line)s</span>
            %(price)s
            %(small)s
          </span>
        </label>""" % {"name": name, "key": key, "chk": " checked" if i == 0 else "", "line": line,
                       "mark": ('<span class="op-t-mark">%s</span>' % mark) if mark else "",
                       "price": price, "small": ('<span class="op-t-small">%s</span>' % small) if small else ""}


def main_html(p, modal):
    offer = ['<p class="op-sub">%s</p>' % p["sub"]]
    if p["sub2"]:
        offer.append('<p class="op-sub2">%s</p>' % p["sub2"])
    offer.append('<p class="op-text">%s</p>' % OFFER_TEXT)
    offer.append('<p class="op-meta">%s</p>' % OFFER_META)
    if p["bron"]:
        offer.append('<ul class="op-bron">%s</ul>' % "".join("<li>%s</li>" % x for x in p["bron"]))
    cb = lambda name, req: """
          <label class="op-cb">
            <input type="checkbox" name="%s"%s>
            <span>%s <em>%s</em></span>
          </label>""" % (name, " required" if req else "", checkbox_text(modal, name),
                         "Обязательно" if req else "По желанию")
    return """
<main id="main" class="op">
  <section class="op-offer">
    <div class="op-in">
      <h1 class="op-h1">%(title)s</h1>
      %(offer)s
    </div>
  </section>
  <section class="op-form-sec">
    <div class="op-in">
      <form class="op-card" id="op-form" novalidate data-pay-page="%(pay)s">
        <h2 class="op-h2">%(form_h)s</h2>
        <fieldset class="op-tiles">
          <legend class="op-legend">Тариф</legend>%(tiles)s
        </fieldset>
        %(under)s
        <div class="op-hp" aria-hidden="true"><label>Не заполняйте это поле<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
        <label class="op-f">Имя<input type="text" name="name" autocomplete="given-name" placeholder="Как к вам обращаться"></label>
        <label class="op-f">Номер телефона<input type="tel" name="phone" autocomplete="tel" placeholder="+7 900 000-00-00"></label>
        <label class="op-f">Telegram для связи<input type="text" name="tg" placeholder="@username"></label>
        <div class="op-cbs">%(cbs)s
        </div>
        <p class="op-err" id="op-err" role="alert" hidden></p>
        <button type="submit" class="op-btn" id="op-submit">%(btn)s</button>
        <p class="op-fine">Нажимая кнопку, вы подтверждаете отмеченные согласия.</p>
      </form>
      <p class="op-acc">%(acc)s</p>
      <p class="op-acc">%(chek)s</p>
      <div class="op-help">
        <h2 class="op-help-h">Возникли проблемы с оплатой?</h2>
        <p>Напишите <b>в поддержку</b>: подберём другой способ оплаты, в том числе из-за рубежа.</p>
        <a class="op-btn op-btn-quiet" href="https://t.me/violamaroteam" target="_blank" rel="noopener">Поддержка</a>
      </div>
    </div>
  </section>
""" % {"title": OFFER_TITLE, "offer": "\n      ".join(offer), "pay": p["pay"], "form_h": p["form_h"],
       "tiles": "".join(tile_html(p, i, t) for i, t in enumerate(p["tiles"])),
       "under": ('<p class="op-under">%s</p>' % p["under"]) if p["under"] else "",
       "cbs": cb("accept_offer", True) + cb("accept_pd", True) + cb("accept_ads", False),
       "btn": p["btn"], "acc": ACCOUNTS, "chek": CHEK}


CSS = r"""
/* Страницы оплаты (oplata.py): оффер и форма, без картинок. */
body { background: #FAF9F8 !important; padding-bottom: 0 !important; }
/* Общие правила темы для main > section и main h2 здесь не нужны. */
#main.op > section { background: transparent !important; border: 0 !important; margin: 0 !important; }
.op h2::first-line { color: inherit !important; }
.op { color: #1C1A1D; font-family: 'Golos Text', system-ui, sans-serif; font-size: 18px; line-height: 1.6; }
.op *, .op *::before, .op *::after { box-sizing: border-box; }
.op p { margin: 0; }
.op-in { max-width: 680px; margin: 0 auto; padding: 0 16px; }
#main.op > .op-offer { padding: 56px 0 36px !important; text-align: center; }
.op .op-h1 { margin: 0; font-family: 'Prata', 'Times New Roman', Georgia, serif !important; font-weight: 400 !important;
  font-size: clamp(36px, 9vw, 60px) !important; line-height: 1.05; text-transform: uppercase; letter-spacing: .01em; color: #C4142C; }
.op-sub { margin-top: 14px !important; font-weight: 800; font-size: 20px; color: #1C1A1D; }
.op-sub2 { margin-top: 8px !important; color: #55505A; font-size: 17px; }
.op-text { margin-top: 18px !important; font-size: 18px; line-height: 1.6; }
.op-meta { margin-top: 18px !important; display: inline-block; padding: 8px 14px; border-radius: 999px; background: #FCE9EA;
  color: #A30F23; font-weight: 700; font-size: 15px; line-height: 1.4; }
.op-bron { list-style: none; margin: 22px auto 0; padding: 18px 20px; max-width: 560px; text-align: left; border-radius: 18px;
  background: #fff; box-shadow: 0 0 0 1px #E6E1DA; display: grid; gap: 10px; font-size: 16.5px; line-height: 1.5; }
.op-bron li { position: relative; padding-left: 18px; }
.op-bron li::before { content: ""; position: absolute; left: 0; top: .6em; width: 7px; height: 7px; border-radius: 50%; background: #C4142C; }
#main.op > .op-form-sec { padding: 0 0 72px !important; }
.op-card { background: #fff; border-radius: 24px; padding: 28px 20px 26px; box-shadow: 0 0 0 1px #ECE7E1, 0 30px 60px -36px rgba(28,26,29,.35); }
.op .op-h2 { margin: 0 0 22px; font-family: 'Golos Text', system-ui, sans-serif !important; font-weight: 800 !important;
  font-size: 22px !important; line-height: 1.3; text-transform: none; letter-spacing: -.01em; color: #1C1A1D; }
.op-tiles { border: 0; margin: 0; padding: 0; display: grid; gap: 12px; }
.op-legend { position: absolute; left: -9999px; }
.op-tile { display: block; cursor: pointer; }
.op-tile input { position: absolute; opacity: 0; pointer-events: none; }
.op-t-box { position: relative; display: grid; gap: 4px; padding: 16px 18px 16px 52px; border-radius: 18px;
  border: 2px solid #E3DED7; background: #fff; transition: border-color .15s ease, background .15s ease; }
.op-t-box::before { content: ""; position: absolute; left: 18px; top: 19px; width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid #CFC8BF; background: #fff; }
.op-tile input:checked + .op-t-box { border-color: #C4142C; background: #FFF7F7; }
.op-tile input:checked + .op-t-box::before { border-color: #C4142C; box-shadow: inset 0 0 0 4px #fff; background: #C4142C; }
.op-tile input:focus-visible + .op-t-box { outline: 3px solid #1C1A1D; outline-offset: 2px; }
.op-t-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.op-t-name { font-size: 19px; font-weight: 800; }
.op-t-mark { flex: none; padding: 3px 10px; border-radius: 999px; background: #FCE9EA; color: #A30F23; font-weight: 800; font-size: 13px; }
.op-t-line { color: #55505A; font-size: 16px; line-height: 1.45; }
.op-t-price { margin-top: 6px; font-family: 'Bebas Neue', 'Arial Narrow', Impact, sans-serif; font-size: 34px; line-height: 1; color: #C4142C; }
.op-t-val { color: #55505A; font-size: 15px; }
.op-t-small { margin-top: 4px; color: #55505A; font-size: 14.5px; }
.op-under { margin-top: 14px !important; color: #55505A; font-size: 15.5px; line-height: 1.5; }
.op-hp { position: absolute; left: -9999px; }
.op-f { display: block; margin-top: 18px; font-weight: 700; font-size: 16px; }
.op-f input { display: block; width: 100%; margin-top: 6px; padding: 14px; border: 1.5px solid #D9D3CB; border-radius: 14px;
  font: 400 18px/1.4 'Golos Text', system-ui, sans-serif; color: #1C1A1D; background: #FBFAF9; }
.op-f input:focus { outline: none; border-color: #C4142C; background: #fff; }
.op-f .op-bad { border-color: #C4142C; }
.op-cbs { margin-top: 20px; display: grid; gap: 12px; }
.op-cb { display: flex; gap: 12px; align-items: flex-start; font-size: 15px; line-height: 1.5; color: #55505A; cursor: pointer; }
.op-cb input { flex: none; width: 22px; height: 22px; margin: 2px 0 0; accent-color: #C4142C; }
.op-cb a { color: #C4142C; }
.op-cb em { font-style: normal; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #8A5A2B; white-space: nowrap; }
.op-cb.op-bad span { color: #C4142C; }
.op-err { margin-top: 14px !important; color: #C4142C; font-weight: 700; font-size: 16px; }
.op-err a { color: inherit; }
.op-btn { display: flex; align-items: center; justify-content: center; width: 100%; min-height: 62px; margin-top: 22px; padding: 14px 20px;
  border: 0; border-radius: 16px; cursor: pointer; text-decoration: none; text-align: center;
  font: 800 16px/1.25 'Golos Text', system-ui, sans-serif; letter-spacing: .08em; text-transform: uppercase; color: #fff;
  background: linear-gradient(135deg, #E2283F 0%, #B01027 100%); box-shadow: 0 18px 32px -14px rgba(196,20,44,.6); }
.op-btn:disabled { opacity: .65; cursor: default; }
.op-btn:focus-visible { outline: 3px solid #1C1A1D; outline-offset: 3px; }
.op-btn-quiet { background: #fff; color: #C4142C; box-shadow: 0 0 0 2px #C4142C inset; margin-top: 16px; }
.op-fine { margin-top: 10px !important; text-align: center; color: #7A747C; font-size: 14px; }
.op-acc { margin-top: 18px !important; text-align: center; color: #55505A; font-size: 15.5px; line-height: 1.5; }
.op-acc a { color: #C4142C; }
.op-help { margin-top: 40px; padding: 26px 20px; border-radius: 22px; background: #fff; box-shadow: 0 0 0 1px #ECE7E1; text-align: center; }
.op .op-help-h { margin: 0 0 8px; font-family: 'Golos Text', system-ui, sans-serif !important; font-weight: 800 !important;
  font-size: 20px !important; text-transform: none; letter-spacing: 0; color: #1C1A1D; }
.op-help p { color: #55505A; font-size: 16.5px; }
@media (min-width: 760px) {
  #main.op > .op-offer { padding: 88px 0 44px !important; }
  .op-card { padding: 40px 40px 36px; }
  .op-tiles { grid-template-columns: 1fr 1fr; }
  #main.op > .op-form-sec { padding-bottom: 110px !important; }
}
"""

JS = r"""
(function () {
  'use strict';
  var ENDPOINT = %(endpoint)s, SECRET = %(secret)s, DOCS = %(docs)s;
  var form = document.getElementById('op-form'), err = document.getElementById('op-err');
  var btn = document.getElementById('op-submit'), label = btn.textContent;
  var isBron = form.getAttribute('data-pay-page') === 'bron';

  function attribution() {
    var out = {}, saved = {};
    try { saved = JSON.parse(sessionStorage.getItem('viola_attribution') || '{}'); } catch (e) {}
    var q = new URLSearchParams(location.search);
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'src', 'k'].forEach(function (k) {
      out[k] = saved[k] || q.get(k) || '';
    });
    out.referrer = saved.referrer || document.referrer || '';
    return out;
  }
  function bad(msg, el) {
    err.innerHTML = msg; err.hidden = false;
    if (el) { el.classList.add('op-bad'); try { el.focus(); } catch (e) {} }
  }
  Array.prototype.forEach.call(form.querySelectorAll('input'), function (el) {
    el.addEventListener('input', function () { el.classList.remove('op-bad'); err.hidden = true; });
    el.addEventListener('change', function () { var l = el.closest('.op-cb'); if (l) l.classList.remove('op-bad'); err.hidden = true; });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements;
    var t = form.querySelector('[name="tarif"]:checked');
    var name = f.name.value.trim(), phone = f.phone.value.trim(), tg = f.tg.value.trim();
    if (!t) return bad('Выберите тариф.');
    if (!name) return bad('Укажите имя.', f.name);
    if (!phone && !tg) return bad('Оставьте телефон или Telegram для связи.', f.phone);
    var miss = ['accept_offer', 'accept_pd'].filter(function (k) { return !f[k].checked; });
    if (miss.length) {
      miss.forEach(function (k) { f[k].closest('.op-cb').classList.add('op-bad'); });
      return bad(miss.indexOf('accept_offer') !== -1 ? 'Без принятия оферты оплата невозможна.'
                                                     : 'Без согласия на обработку данных оплата невозможна.', f[miss[0]]);
    }
    var plan = isBron ? 'Бронь места, тариф «' + t.value + '»' : t.value;
    var payKey = t.getAttribute('data-pay');
    var payload = {
      secret: SECRET, website: f.website.value, name: name, phone: phone, telegram: tg,
      plan: plan, form: 'оплата', readiness: '',
      accept_offer: true, accept_pd: true, accept_ads: !!f.accept_ads.checked,
      consent_ts: new Date().toISOString(), page: location.href, ua: navigator.userAgent
    };
    var a = attribution(); Object.keys(a).forEach(function (k) { payload[k] = a[k]; });
    Object.keys(DOCS).forEach(function (k) { payload[k] = DOCS[k]; });

    btn.disabled = true; btn.textContent = 'Отправляем…'; err.hidden = true;
    function go(notSaved) {
      btn.disabled = false; btn.textContent = label;
      if (!(window.violaPay && window.violaPay(plan, payKey, notSaved, btn))) {
        bad('Не нашли страницу оплаты для этого тарифа. Напишите нам в Telegram: '
          + '<a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a>');
      }
    }
    if (!ENDPOINT || !window.fetch) { go(false); return; }
    /* Как у прежней формы сайта: text/plain без предварительного запроса,
       ответ Apps Script — редирект, доходим до него и считаем запись сделанной. */
    var req = fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(payload), redirect: 'manual', keepalive: true })
      .then(function (res) { if (res.type !== 'opaqueredirect' && !res.ok) throw new Error('HTTP ' + res.status); });
    var slow = new Promise(function (r) { setTimeout(r, 1500); });
    Promise.race([req, slow]).then(function () { go(false); }, function () { go(true); });
  });
})();
"""


def rebuild(p):
    path = os.path.join(SITE, p["dir"], "index.html")
    page = build.read(path)
    if 'class="op"' in page:
        raise SystemExit("оплата: %s уже пересобрана; сначала соберите её build.py" % path)
    a, b = block(page, "div", 'id="lead-modal"')
    modal = page[a:b]
    # Подарков на страницах оплаты нет, и в окне тоже.
    if "data-modal-gifts" in modal:
        ga, gb = block(modal, "div", "data-modal-gifts")
        modal = modal[:ga] + modal[gb:]
    # Строка про аккаунты и чек в окне — как под формой; длинного тире нет.
    modal = re.sub(r"<p[^>]*><b[^>]*>Пишем только с этого аккаунта\.</b>.*?</p>",
                   '<p style="margin: 0; font-size: 15px; line-height: 1.5; color: #5A5559;">%s</p>' % ACCOUNTS,
                   modal, flags=re.S)
    modal = modal.replace("Оплата и&nbsp;чек&nbsp;— от&nbsp;ИП", "Оплата и&nbsp;чек от&nbsp;ИП")
    modal = modal.replace("&nbsp;— ", ", ").replace(" — ", ", ")

    head_end = page.index("<body>") + len("<body>")
    head = page[:head_end]
    title = html_mod.escape(p["title"])
    desc = html_mod.escape(p["desc"])
    head = re.sub(r"<title>.*?</title>", "<title>%s</title>" % title, head, flags=re.S)
    head = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*"', r'\g<1>%s"' % desc, head)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*"', r'\g<1>%s"' % title, head)
    if p["noindex"] and 'name="robots"' not in head:
        head = head.replace("<head>\n", '<head>\n<meta name="robots" content="noindex, nofollow">\n', 1)
    head = head.replace("</head>", "<style>%s</style>\n</head>" % CSS, 1)

    main_a = page.index("<main")
    main_b = page.index("</main>") + len("</main>")
    tail = page[main_b:]
    js = JS % {"endpoint": json.dumps(site_js_setting("LEAD_ENDPOINT")),
               "secret": json.dumps(site_js_setting("FORM_SECRET")),
               "docs": json.dumps(doc_versions())}
    tail = tail.replace("</body>", "<script>%s</script>\n</body>" % js, 1)
    body = (page[head_end:main_a] + main_html(p, modal) + modal + "\n</main>" + tail)
    out = head + body
    check(out, path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print("Оплата → %s (%d КБ)" % (os.path.relpath(path, build.ROOT), len(out.encode("utf-8")) // 1024))


def check(text, path):
    visible = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text)
    problems = []
    if "—" in visible or "&mdash;" in visible:
        problems.append("длинное тире: " + ", ".join(sorted(set(re.findall(r".{0,30}—.{0,30}", visible)))[:4]))
    if "2.0" in visible:
        problems.append("«2.0»")
    main = text[text.index("<main"):text.index('id="lead-modal"')]
    if "<img" in main or "<picture" in main:
        problems.append("картинки в оффере или форме")
    for w in ("таймер", "Неделя 1", "Истории участниц", "подар", "Подар"):
        if w in re.sub(r"<[^>]+>", " ", main):
            problems.append("на странице есть «%s»" % w)
    if problems:
        raise SystemExit("оплата %s: %s" % (path, "; ".join(problems)))


def main():
    for p in PAGES:
        rebuild(p)


if __name__ == "__main__":
    main()
