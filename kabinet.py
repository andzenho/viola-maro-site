#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страница-заявка «Прикладная эмпатия 2.0» для Кабинета: violamaro.ru/kabinet.

Отдельная страница для подписчиков закрытого канала Виолы. Человек оставляет
заявку и сразу попадает в чат с менеджером. Оплаты на странице нет, цена
Кабинета на ней не пишется нигде: её называет менеджер.

Запуск — после сборки основного сайта, потому что страница берёт оттуда
стили, шрифты и фотографию:

    python3 build.py --theme barhat --noindex
    python3 kabinet.py

Всё, что меняется без правки вёрстки, лежит в CONFIG. Тексты блоков стоят
дословно по ТЗ от 13.10.2026; состав тарифов, недели и бонусы берутся
из сборщика основного сайта, чтобы два сайта не разошлись.
"""

import hashlib
import html
import json
import os
import re
import shutil

import build

CONFIG = {
    "PRICE_SELF": "19 900 ₽",
    "PRICE_VIOLA": "39 900 ₽",
    "PRICE_DEADLINE": "31 октября",
    "MANAGER_TG": "violamaroteam",
    # Куда уводим после заявки. Ссылка вида t.me/m/… открывает чат с уже
    # набранным сообщением; текст задаётся в Telegram, не здесь.
    "MANAGER_CHAT_URL": "https://t.me/m/t7W8mt1mYjdi",
    # Пока пусто, счётчик мест не показывается.
    "SEATS_LEFT": "",
    # Номер счётчика Яндекс Метрики. На violamaro.ru счётчика нет, поэтому
    # пусто: цели начнут уходить, как только сюда впишут номер.
    "METRIKA_ID": "",
    # Каким типом формы заявка уходит в таблицу. «заявка» принимает уже
    # развёрнутый скрипт: строка ложится в общий лист заявок с меткой
    # «Кабинет». «кабинет» — свой лист, приоритет, статус, дубли и бот:
    # ставить после того, как развёрнута новая версия скрипта таблицы.
    "FORM_KIND": "заявка",
}

OUT = os.path.join(build.ROOT, "site", "kabinet")
REVIEWS = os.path.join(build.ROOT, "kabinet", "reviews")
SITE_URL = "https://violamaro.ru"

# Состав тарифов. Те же строки, что в карточках на violamaro.ru; сборка
# сверяет их с собранной главной и предупреждает, если разошлись.
TARIF_COMMON = [
    "18 техник эмпата, по три на неделю",
    "Задание после каждой лекции",
    "Записи лекций с таймкодами",
    "PDF-методички к каждой лекции",
    "Аудиомедитации от Виолы",
    "Доступ навсегда",
]
TARIF_VIOLA = [
    "Вопросы Виоле в чате: команда собирает их каждый день, Виола отвечает аудио",
    "Мастер-класс Виолы с ответами на ваши вопросы",
    "Чат потока",
]

VAZHNO = ["Перестать растворяться в чужих эмоциях", "Отказывать без вины", "Отношения с близкими",
          "Работа и люди с властью", "Силы и время для себя", "Другое"]
KOGDA = ["Сейчас", "До старта 1 ноября", "Сначала хочу задать вопросы"]
TARIFY = ["Самостоятельный", "С Виолой", "Пока не знаю"]


def esc(s):
    return html.escape(s, quote=True)


NBSP = chr(160)


def nb(s):
    """Короткие слова не остаются в конце строки, число не отрывается
    от слова после него («31 октября», «3 техники»)."""
    s = re.sub(r"(?<![\w«])(в|на|и|с|к|о|у|за|из|по|от|до|не|а|для|или|что|как|её|вы|вам)\s+",
               lambda m: m.group(1) + NBSP, s, flags=re.I)
    s = s.replace("из-за", "из" + chr(8209) + "за")      # дефис без переноса
    return re.sub(r"(\d)\s+(?=[а-яё])", lambda m: m.group(1) + NBSP, s)


def tg(s):
    return s.replace("@violamaroteam", "<b>@%s</b>" % CONFIG["MANAGER_TG"])


# ── блоки ──

def hero():
    return """
<header class="kb-hero">
  <div class="kb-hero-top">
    <p class="kb-eyebrow">Только для Кабинета</p>
    <h1>Заявка на<br>«Прикладную<br>эмпатию&nbsp;2.0»</h1>
    <p class="kb-sub">Старт 1&nbsp;ноября. Для тех, кто в&nbsp;Кабинете, цена ниже, чем на&nbsp;сайте. Её назовёт Дарья после заявки.</p>
    <a class="kb-btn kb-btn-white" href="#zayavka" data-cta="">Оставить заявку</a>
    <p class="kb-small">После заявки вы попадёте в&nbsp;чат с&nbsp;Дарьей из&nbsp;команды Виолы.</p>
  </div>
  <div class="kb-hero-photo">
    <img src="/assets/img/viola.webp" alt="Виола Маро" width="901" height="1202" fetchpriority="high" decoding="async">
  </div>
</header>"""


def posle():
    items = [
        "расскажет подробно о программе и покажет презентацию практикума;",
        "ответит на ваши вопросы и поможет выбрать тариф;",
        "назовёт цену для Кабинета (она ниже, чем на сайте) и закрепит её за вами до %s;" % CONFIG["PRICE_DEADLINE"],
        "поможет оплатить, в том числе в рассрочку или из-за границы, и получить доступы к «Прикладной эмпатии».",
    ]
    return """
<section class="kb-sec">
  <div class="kb-in">
    <h2>После заявки вы попадёте в&nbsp;чат с&nbsp;Дарьей из&nbsp;команды Виолы</h2>
    <p class="kb-lead">%s</p>
    <ul class="kb-list">%s</ul>
  </div>
</section>""" % (tg(nb("Если чат не откроется, Дарья сама напишет вам с аккаунта @violamaroteam. Она:")),
                 "".join("<li>%s</li>" % nb(esc(t)) for t in items))


def tarif_card(name, lead, price, extra, key, seats=""):
    weeks = "".join("<li>Неделя %s. %s</li>" % (w["n"], esc(w["title"])) for w in build.WEEKS)
    yes = "".join("<li>%s</li>" % nb(esc(t)) for t in TARIF_COMMON + extra)
    no = "".join("<li>%s</li>" % nb(esc(t)) for t in TARIF_VIOLA) if not extra else ""
    return """
    <article class="kb-tarif%s">
      %s<h3>%s</h3>
      <p class="kb-tarif-lead">%s</p>
      <p class="kb-tag">Программа</p>
      <ul class="kb-weeks">%s</ul>
      <ul class="kb-yes">%s</ul>
      %s
      %s
      <div class="kb-cena"><span>%s</span></div>
      <p class="kb-deshevle">В&nbsp;Кабинете дешевле. Цену назовёт Дарья после заявки</p>
      <a class="kb-btn" href="#zayavka" data-cta="" data-tarif="%s">Оставить заявку на&nbsp;этот тариф</a>
    </article>""" % (" kb-tarif-main" if extra else "",
                     '<span class="kb-rekom">Рекомендуем</span>' if extra else "",
                     esc(name), nb(esc(lead)), weeks, yes,
                     '<ul class="kb-no">%s</ul>' % no if no else "",
                     '<p class="kb-mest">%s</p>' % seats if seats else "",
                     esc(price).replace(" ", "&nbsp;"), esc(key))


def tarify():
    seats = "50&nbsp;мест"
    if CONFIG["SEATS_LEFT"]:
        seats += ", осталось %s" % esc(str(CONFIG["SEATS_LEFT"]))
    return """
<section class="kb-sec kb-red" id="tarify">
  <div class="kb-in kb-wide">
    <h2>Тарифы</h2>
    <div class="kb-tarify">%s%s
    </div>
    <p class="kb-pod">Можно в&nbsp;рассрочку на&nbsp;3, 6 или&nbsp;12&nbsp;месяцев, Дарья всё расскажет</p>
  </div>
</section>""" % (
        tarif_card("Самостоятельный", "Весь метод и все техники. Самостоятельное прохождение.",
                   CONFIG["PRICE_SELF"], [], "Самостоятельный"),
        tarif_card("С Виолой", "Всё то же самое — и Виола отвечает на ваши вопросы.",
                   CONFIG["PRICE_VIOLA"], TARIF_VIOLA, "С Виолой", seats))


def kak():
    steps = [
        "Оставляете заявку. Это минута.",
        "Сразу открывается чат с Дарьей в Telegram. Она рассказывает о программе, показывает презентацию "
        "и отвечает на вопросы.",
        "Дарья называет цену Кабинета, помогает оплатить (картой РФ, зарубежной картой или в рассрочку) "
        "и выдаёт доступы.",
    ]
    return """
<section class="kb-sec">
  <div class="kb-in">
    <h2>Как это работает</h2>
    <ol class="kb-steps">%s</ol>
  </div>
</section>""" % "".join("<li><span>%s</span></li>" % nb(esc(t)) for t in steps)


def programma():
    mods = []
    for w in build.WEEKS:
        tricks = "".join("<li>%s</li>" % nb(esc(it["text"])) for it in w["items"])
        lead = "".join("<p>%s</p>" % nb(esc(p)) for p in w["lead"].split("\n\n"))
        note = '<p class="kb-note">%s</p>' % esc(w["note"]) if w["note"] else ""
        mods.append("""
      <details class="kb-acc">
        <summary><span class="kb-num">0%s</span><span>%s</span></summary>
        <div class="kb-acc-body">
          <p class="kb-q">«%s»</p>
          %s
          <p class="kb-tag">3 техники</p>
          <ul class="kb-list">%s</ul>%s
        </div>
      </details>""" % (w["n"], esc(w["title"]), nb(esc(w["q"])), lead, tricks, note))
    bonus = ", ".join("%s" % t[0].lower() + t[1:] if not t.startswith("«") else t
                      for t, _tail in build.PRE_FOR_EARLY)
    return """
<section class="kb-sec kb-pink">
  <div class="kb-in">
    <h2>Что будет на&nbsp;практикуме</h2>
    <p class="kb-shapka">6&nbsp;модулей, 18&nbsp;техник, финальный мастер-класс</p>
    <div class="kb-accs">%s
    </div>
    <p class="kb-bonus">После оплаты 4&nbsp;бонуса: %s.</p>
  </div>
</section>""" % ("".join(mods), nb(esc(bonus)))


def komu():
    da = [
        "Вы чувствуете чужое настроение раньше, чем человек заговорил, а потом полчаса не можете прийти в себя.",
        "Вам трудно отказать, даже когда сил помогать уже нет.",
        "Для близких всё делается легко и быстро, а для себя ничего не получается начать.",
        "Рядом есть человек, который давит: начальник, мама, взрослый ребёнок. Вы теряетесь и потом долго "
        "прокручиваете разговор.",
        "Вы устали разочаровываться в людях.",
    ]
    net = [
        "Если вы ищете терапию. Практикум учит обращаться со своей чувствительностью, но не заменяет психолога "
        "или врача.",
        "Если вы хотите, чтобы изменился кто-то другой. Техники работают для вас, не для них.",
    ]
    return """
<section class="kb-sec">
  <div class="kb-in">
    <h2>Кому подойдёт</h2>
    <ul class="kb-cards kb-da">%s</ul>
    <h2 class="kb-h2b">Кому не&nbsp;подойдёт</h2>
    <ul class="kb-cards kb-net">%s</ul>
  </div>
</section>""" % ("".join("<li>%s</li>" % nb(esc(t)) for t in da),
                 "".join("<li>%s</li>" % nb(esc(t)) for t in net))


def otzyvy(files):
    if not files:
        return ""
    pics = "".join('<button type="button" class="kb-otz" data-otz="/kabinet/reviews/%s">'
                   '<img src="/kabinet/reviews/%s" alt="Отзыв участницы" loading="lazy" decoding="async"></button>'
                   % (esc(f), esc(f)) for f in files)
    return """
<section class="kb-sec">
  <div class="kb-in kb-wide">
    <h2>Отзывы</h2>
    <div class="kb-otzyvy">%s</div>
    <p class="kb-pod kb-pod-dark">Участницы первого потока, октябрь 2026</p>
  </div>
  <div class="kb-zoom" hidden><button type="button" aria-label="Закрыть">×</button><img alt="Отзыв участницы"></div>
</section>""" % pics


def voprosy():
    qa = [
        ("Что будет после заявки?",
         "Откроется чат с Дарьей из команды Виолы или она напишет вам сама с аккаунта @violamaroteam. Дарья "
         "расскажет о программе, ответит на вопросы, назовёт цену для Кабинета, поможет оплатить и получить доступы."),
        ("Сколько стоит для Кабинета?",
         "Ниже, чем на сайте. Дарья назовёт цену сразу, как вы ей напишете. Это цена для тех, кто в Кабинете "
         "и пришёл раньше открытого набора."),
        ("До какого числа держится цена?",
         "До %s или пока есть места." % CONFIG["PRICE_DEADLINE"]),
        ("Я живу не в России.",
         "Можно оплатить зарубежной картой, цену в долларах или евро назовёт Дарья."),
        ("Не знаю, какой тариф выбрать.",
         "Поставьте в заявке «Пока не знаю», Дарья поможет."),
    ]
    return """
<section class="kb-sec kb-pink">
  <div class="kb-in">
    <h2>Вопросы</h2>
    <div class="kb-accs">%s
    </div>
  </div>
</section>""" % "".join("""
      <details class="kb-acc">
        <summary><span>%s</span></summary>
        <div class="kb-acc-body"><p>%s</p></div>
      </details>""" % (nb(esc(q)), tg(nb(esc(a)))) for q, a in qa)


def radios(name, options, required=False):
    return "".join(
        '<label class="kb-pill"><input type="radio" name="%s" value="%s"%s><span>%s</span></label>'
        % (name, esc(o), " required" if required else "", nb(esc(o))) for o in options)


def forma():
    return """
<section class="kb-sec kb-forma" id="zayavka">
  <div class="kb-in">
    <form class="kb-form" novalidate>
      <h2>Оставить заявку</h2>
      <p class="kb-lead">После заявки вы попадёте в&nbsp;чат с&nbsp;Дарьей из&nbsp;команды Виолы. Она расскажет о&nbsp;программе, ответит на&nbsp;вопросы, закрепит за&nbsp;вами цену Кабинета и&nbsp;поможет оплатить.</p>

      <div class="kb-hp" aria-hidden="true"><label>Сайт<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>

      <div class="kb-field" data-field="name">
        <label for="kb-name">Имя</label>
        <input id="kb-name" name="name" type="text" autocomplete="given-name" placeholder="Как к вам обращаться">
        <p class="kb-err" hidden></p>
      </div>

      <div class="kb-field" data-field="telegram">
        <label for="kb-tg">Telegram</label>
        <input id="kb-tg" name="telegram" type="text" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="@username">
        <p class="kb-err" hidden></p>
      </div>

      <div class="kb-field" data-field="phone">
        <label for="kb-phone">Телефон <i>необязательно</i></label>
        <input id="kb-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+7 900 000-00-00">
        <p class="kb-hint">если Telegram скрыт, Дарья напишет по&nbsp;номеру</p>
        <p class="kb-err" hidden></p>
      </div>

      <fieldset class="kb-field" data-field="tarif">
        <legend>Тариф</legend>
        <div class="kb-pills">%(tarif)s</div>
        <p class="kb-err" hidden></p>
      </fieldset>

      <fieldset class="kb-field" data-field="vazhno">
        <legend>Что сейчас важнее всего <i>необязательно</i></legend>
        <div class="kb-pills">%(vazhno)s</div>
      </fieldset>

      <fieldset class="kb-field" data-field="kogda">
        <legend>Когда готовы решать <i>необязательно</i></legend>
        <div class="kb-pills">%(kogda)s</div>
      </fieldset>

      <div class="kb-field kb-check" data-field="accept_pd">
        <label><input type="checkbox" name="accept_pd"><span>Я&nbsp;даю <a href="%(consent)s" target="_blank" rel="noopener">согласие</a> на&nbsp;обработку моих персональных данных и&nbsp;ознакомлен(а) с&nbsp;<a href="%(privacy)s" target="_blank" rel="noopener">Политикой обработки персональных данных</a>.</span></label>
        <p class="kb-err" hidden></p>
      </div>

      <div class="kb-field kb-check" data-field="accept_ads">
        <label><input type="checkbox" name="accept_ads"><span>Я&nbsp;хочу получать письма и&nbsp;сообщения о&nbsp;программах и&nbsp;эфирах. Отписаться можно в&nbsp;один клик. <a href="%(ads)s" target="_blank" rel="noopener">Условия рассылки</a></span></label>
      </div>

      <p class="kb-err kb-err-form" hidden></p>
      <button class="kb-btn kb-submit" type="submit">Отправить заявку</button>
    </form>

    <div class="kb-sent" hidden tabindex="-1">
      <h2>Заявка у&nbsp;Дарьи, открываем чат…</h2>
      <a class="kb-btn" href="%(chat)s" data-tg="">Открыть чат с&nbsp;Дарьей</a>
      <p class="kb-small kb-small-dark">Если не&nbsp;получилось, Дарья сама напишет вам с&nbsp;@%(mgr)s</p>
    </div>
  </div>
</section>""" % {
        "tarif": radios("tarif", TARIFY), "vazhno": radios("vazhno", VAZHNO), "kogda": radios("kogda", KOGDA),
        "consent": "/consent", "privacy": "/privacy", "ads": "/consent-ads",
        "chat": esc(CONFIG["MANAGER_CHAT_URL"]), "mgr": esc(CONFIG["MANAGER_TG"]),
    }


CSS = r"""
.kb { --red: #C4142C; --red2: #B21028; --ink: #1C1A1D; --grey: #EAE7E2; --line: #DDD8D1; --pink: #FBE4E7;
      --prata: 'Prata', 'Times New Roman', Georgia, serif;
      background: var(--grey); color: var(--ink); font-size: 18px; line-height: 1.55; overflow-x: hidden; }
.kb *, .kb *::before, .kb *::after { box-sizing: border-box; }
.kb h1, .kb h2, .kb h3 { font-family: var(--prata); font-weight: 400; margin: 0; text-wrap: balance; }
.kb p { margin: 0; }
.kb ul, .kb ol { margin: 0; padding: 0; list-style: none; }
.kb a { color: var(--red); }

/* первый экран */
.kb-hero { background: linear-gradient(150deg, #DE1E38 0%, #C4142C 62%, #B21028 100%); color: #FFFFFF; text-align: center; overflow: hidden; }
.kb-hero-top { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 26px 20px 0; }
.kb-eyebrow { padding: 8px 16px; border-radius: 999px; background: rgba(255,255,255,.16); font-size: 14.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.kb-hero h1 { font-size: min(9.6vw, 62px); line-height: 1.1; letter-spacing: .01em; text-transform: uppercase; }
.kb-sub { max-width: 520px; font-size: 17.5px; line-height: 1.45; }
.kb-small { max-width: 360px; font-size: 15px; line-height: 1.4; color: rgba(255,255,255,.92); }
.kb-small-dark { color: #5A5559; }
.kb-hero-photo { position: relative; height: clamp(340px, 96vw, 560px); margin-top: 10px; }
.kb-hero-photo::before { content: ""; position: absolute; left: 50%; bottom: -34%; width: 132%; aspect-ratio: 1; transform: translateX(-50%); border-radius: 50%; background: linear-gradient(180deg, #FFFFFF 0%, #E9E7E4 70%); }
.kb-hero-photo img { position: absolute; left: 50%; bottom: 0; height: 100%; width: auto; max-width: none; transform: translateX(-50%); }

/* кнопки */
.kb-btn { display: flex; align-items: center; justify-content: center; width: min(100%, 360px); min-height: 66px; margin: 0 auto; padding: 16px 26px; border: 0; border-radius: 16px; background: var(--red); color: #FFFFFF !important; font: inherit; font-size: 16px; font-weight: 700; letter-spacing: .09em; line-height: 1.25; text-align: center; text-decoration: none; text-transform: uppercase; cursor: pointer; box-shadow: 0 16px 30px -16px rgba(196,20,44,.55); -webkit-tap-highlight-color: transparent; }
.kb-btn:hover { filter: brightness(1.06); }
.kb-btn:focus-visible, .kb a:focus-visible, .kb summary:focus-visible, .kb input:focus-visible + span { outline: 3px solid #1C1A1D; outline-offset: 3px; }
.kb-btn-white { background: #FFFFFF; color: var(--red) !important; box-shadow: 0 18px 34px -18px rgba(70,4,14,.6); }
.kb-btn[disabled] { opacity: .6; cursor: default; }

/* блоки */
.kb-sec { padding: clamp(64px, 9vw, 120px) 20px; }
.kb-in { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 22px; }
.kb-wide { max-width: 1020px; }
.kb h2 { font-size: clamp(30px, 4.2vw, 50px); line-height: 1.14; letter-spacing: .015em; text-transform: uppercase; }
.kb h2::first-line { color: var(--red); }
.kb-h2b { margin-top: 34px !important; }
.kb-lead { font-size: 18.5px; color: #343034; }
.kb-pink { background: var(--pink); border-radius: clamp(36px, 6vw, 80px); }
.kb-red { background: linear-gradient(150deg, #DE1E38 0%, #C4142C 62%, #B21028 100%); }
.kb-red > .kb-in > h2, .kb-red > .kb-in > h2::first-line { color: #FFFFFF; text-align: center; }
.kb-tag { align-self: flex-start; width: fit-content; padding: 6px 14px; border-radius: 999px; background: #FCE9EA; color: var(--red); font-size: 13px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }

.kb-list { display: flex; flex-direction: column; gap: 12px; }
.kb-list li { position: relative; padding-left: 34px; }
.kb-list li::before { content: ""; position: absolute; left: 0; top: .28em; width: 22px; height: 22px; border-radius: 50%; background: var(--red); }
.kb-list li::after { content: ""; position: absolute; left: 8px; top: calc(.28em + 4px); width: 5px; height: 10px; border: solid #FFFFFF; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.kb-sec > .kb-in > .kb-list { padding: 24px 22px; border-radius: 26px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 26px 46px -28px rgba(28,26,29,.34); }

/* тарифы */
.kb-tarify { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 40px 24px; align-items: start; }
.kb-tarif { position: relative; display: flex; flex-direction: column; gap: 16px; padding: 30px 24px 26px; border-radius: 26px; background: #FFFFFF; box-shadow: 0 30px 50px -30px rgba(70,4,14,.7); }
.kb-tarif-main { box-shadow: 0 0 0 5px rgba(255,255,255,.4), 0 30px 50px -30px rgba(70,4,14,.7); }
.kb-rekom { position: absolute; left: 50%; top: -14px; transform: translateX(-50%); padding: 6px 16px; border-radius: 999px; background: #1C1A1D; color: #FFFFFF; font-size: 13.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; white-space: nowrap; }
.kb-tarif h3 { font-size: 30px; line-height: 1.15; }
.kb-tarif-lead { padding-bottom: 16px; border-bottom: 1px solid var(--line); color: #5A5559; }
.kb-weeks, .kb-yes, .kb-no { display: flex; flex-direction: column; gap: 8px; font-size: 16.5px; line-height: 1.4; }
.kb-weeks li, .kb-yes li, .kb-no li { position: relative; padding-left: 34px; }
.kb-weeks li { color: #5A5559; }
.kb-weeks li::before { content: "—"; position: absolute; left: 2px; color: var(--red); }
.kb-yes li::before { content: ""; position: absolute; left: 0; top: .1em; width: 22px; height: 22px; border-radius: 50%; background: #FCE9EA; }
.kb-yes li::after { content: ""; position: absolute; left: 8px; top: calc(.1em + 4px); width: 5px; height: 10px; border: solid var(--red); border-width: 0 2px 2px 0; transform: rotate(45deg); }
.kb-no { padding-top: 14px; border-top: 1px solid var(--line); color: #9A9498; text-decoration: line-through; }
.kb-no li::before { content: "×"; position: absolute; left: 5px; text-decoration: none; display: inline-block; }
.kb-mest { align-self: flex-start; padding: 7px 14px; border-radius: 999px; background: #FCE9EA; color: var(--red); font-size: 15.5px; font-weight: 700; }
.kb-cena { padding: 20px 22px; border-radius: 20px; background: linear-gradient(150deg, #DE1E38 0%, #C4142C 62%, #B21028 100%); color: #FFFFFF; }
.kb-cena span { font-family: var(--prata); font-size: 40px; line-height: 1; }
.kb-deshevle { padding: 12px 16px; border-radius: 14px; background: #FCE9EA; color: #A30F23; font-size: 16px; font-weight: 700; line-height: 1.35; }
.kb-tarif .kb-btn { width: 100%; }
.kb-pod { text-align: center; color: #FFFFFF; font-size: 17px; font-weight: 600; }
.kb-pod-dark { color: #5A5559; }

/* шаги */
.kb-steps { counter-reset: shag; display: flex; flex-direction: column; gap: 12px; }
.kb-steps li { counter-increment: shag; display: grid; grid-template-columns: 58px 1fr; gap: 6px; align-items: start; padding: 22px 22px 22px 20px; border-radius: 22px 22px 22px 6px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 26px 46px -28px rgba(28,26,29,.34); }
.kb-steps li::before { content: "0" counter(shag); font-family: var(--prata); font-size: 38px; line-height: 1; color: var(--red); }

/* аккордеон */
.kb-shapka { font-family: var(--prata); font-size: 22px; line-height: 1.3; color: #A30F23; }
.kb-accs { display: flex; flex-direction: column; gap: 10px; }
.kb-acc { border-radius: 20px; background: #FFFFFF; box-shadow: 0 0 0 1px #F1CDD2; }
.kb-acc summary { display: grid; grid-template-columns: auto 1fr 24px; gap: 14px; align-items: center; min-height: 64px; padding: 16px 20px; font-size: 18px; font-weight: 700; line-height: 1.3; cursor: pointer; list-style: none; -webkit-tap-highlight-color: transparent; }
.kb-acc summary > span:only-of-type { grid-column: 1 / 3; }
.kb-acc summary::-webkit-details-marker { display: none; }
.kb-acc summary::after { content: ""; grid-column: 3; width: 11px; height: 11px; margin: 0 auto; border: solid var(--red); border-width: 0 2.5px 2.5px 0; transform: translateY(-3px) rotate(45deg); transition: transform .2s; }
.kb-acc[open] summary::after { transform: translateY(3px) rotate(-135deg); }
.kb-num { font-family: var(--prata); font-size: 30px; font-weight: 400; line-height: 1; color: var(--red); }
.kb-acc-body { display: flex; flex-direction: column; gap: 14px; padding: 0 20px 22px; font-size: 17.5px; }
.kb-q { padding: 14px 16px; border-radius: 4px 18px 18px 18px; background: var(--pink); color: #A30F23; font-family: var(--prata); font-size: 18.5px; line-height: 1.4; }
.kb-note { font-size: 15.5px; font-style: italic; color: #5A5559; }
.kb-bonus { padding: 20px 22px; border-radius: 20px; background: #FFFFFF; box-shadow: 0 0 0 1px #F1CDD2; font-size: 17.5px; }

/* кому подойдёт */
.kb-cards { display: flex; flex-direction: column; gap: 10px; }
.kb-cards li { position: relative; padding: 18px 20px 18px 58px; border-radius: 20px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 26px 46px -28px rgba(28,26,29,.34); }
.kb-cards li::before { content: ""; position: absolute; left: 18px; top: 19px; width: 26px; height: 26px; border-radius: 50%; background: var(--red); }
.kb-da li::after { content: ""; position: absolute; left: 27.5px; top: 24px; width: 6px; height: 12px; border: solid #FFFFFF; border-width: 0 2.5px 2.5px 0; transform: rotate(45deg); }
.kb-net li::before { background: #1C1A1D; }
.kb-net li::after { content: "×"; position: absolute; left: 18px; top: 19px; width: 26px; height: 26px; color: #FFFFFF; font-size: 21px; font-weight: 700; line-height: 25px; text-align: center; }

/* отзывы */
.kb-otzyvy { display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px 2px 14px; -webkit-overflow-scrolling: touch; }
.kb-otz { flex: none; width: min(78vw, 300px); padding: 0; border: 0; border-radius: 18px; overflow: hidden; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line); scroll-snap-align: center; cursor: zoom-in; }
.kb-otz img { display: block; width: 100%; height: auto; }
@media (min-width: 900px) { .kb-otzyvy { display: grid; grid-template-columns: repeat(3, 1fr); overflow: visible; } .kb-otz { width: auto; } }
.kb-zoom { position: fixed; inset: 0; z-index: 60; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(28,26,29,.92); }
.kb-zoom[hidden] { display: none; }
.kb-zoom img { max-width: 100%; max-height: 100%; border-radius: 12px; }
.kb-zoom button { position: absolute; right: 12px; top: 12px; width: 48px; height: 48px; border: 0; border-radius: 50%; background: #FFFFFF; color: #1C1A1D; font-size: 28px; line-height: 1; cursor: pointer; }

/* форма */
.kb-forma { background: var(--grey); }
.kb-form, .kb-sent { display: flex; flex-direction: column; gap: 22px; padding: 30px 22px 28px; border-radius: 28px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 30px 54px -30px rgba(28,26,29,.4); }
.kb-sent { align-items: center; text-align: center; padding: 44px 22px; }
.kb-sent[hidden], .kb-form[hidden] { display: none; }
.kb-hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
.kb-field { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; border: 0; min-width: 0; }
.kb-field > label, .kb-field > legend { padding: 0; font-size: 16.5px; font-weight: 700; }
.kb-field i { font-style: normal; font-weight: 500; font-size: 14.5px; color: #7A7478; }
.kb-field legend { margin-bottom: 8px; }
.kb-field input[type="text"], .kb-field input[type="tel"] { width: 100%; min-height: 58px; padding: 14px 16px; border: 1.5px solid #CFC9C1; border-radius: 14px; background: #FFFFFF; color: var(--ink); font: inherit; font-size: 18px; -webkit-appearance: none; appearance: none; }
.kb-field input[type="text"]:focus, .kb-field input[type="tel"]:focus { outline: none; border-color: var(--red); box-shadow: 0 0 0 3px rgba(196,20,44,.16); }
.kb-hint { font-size: 14.5px; color: #7A7478; }
.kb-pills { display: flex; flex-wrap: wrap; gap: 8px; }
.kb-pill { position: relative; display: block; }
.kb-pill input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.kb-pill span { display: flex; align-items: center; min-height: 50px; padding: 11px 16px; border: 1.5px solid #CFC9C1; border-radius: 14px; background: #FFFFFF; font-size: 16.5px; font-weight: 600; line-height: 1.25; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.kb-pill input:checked + span { border-color: var(--red); background: var(--red); color: #FFFFFF; }
.kb-check label { display: grid; grid-template-columns: 26px 1fr; gap: 12px; align-items: start; font-size: 15.5px; font-weight: 400; line-height: 1.45; cursor: pointer; }
.kb-check input { width: 22px; height: 22px; margin: 2px 0 0; accent-color: var(--red); }
.kb-err { padding: 10px 14px; border-radius: 12px; background: #FDF2F0; border: 1px solid #EED8D3; color: #8A2B2B; font-size: 15.5px; line-height: 1.4; }
.kb-field.kb-bad input[type="text"], .kb-field.kb-bad input[type="tel"] { border-color: #B3261E; }
.kb-form .kb-submit { width: 100%; }

@media (min-width: 900px) {
  .kb-hero { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr); align-items: end; text-align: left; padding: 0 max(40px, calc(50% - 560px)); }
  .kb-hero-top { align-items: flex-start; padding: 70px 0 80px; }
  .kb-hero .kb-btn { margin: 0; }
  .kb-hero h1 { font-size: clamp(44px, 4.6vw, 66px); }
  .kb-hero-photo { height: 600px; margin: 0; }
  .kb-hero-photo::before { width: 120%; bottom: -46%; }
  .kb-pink { margin: 0 20px; }
}
"""

JS = r"""
(function () {
  var CFG = %(cfg)s;
  var form = document.querySelector('.kb-form');
  var sent = document.querySelector('.kb-sent');
  if (!form) return;

  /* ── метки: живут всю сессию, чтобы не потеряться при повторных заходах ── */
  var UTM = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'];
  var utm = {};
  try { utm = JSON.parse(sessionStorage.getItem('kabinet-utm') || '{}') || {}; } catch (e) { utm = {}; }
  try {
    var q = new URLSearchParams(window.location.search);
    UTM.forEach(function (k) { if (q.get(k)) utm[k] = q.get(k).slice(0, 200); });
    sessionStorage.setItem('kabinet-utm', JSON.stringify(utm));
  } catch (e) {}

  function goal(name) {
    try { if (CFG.metrika && window.ym) window.ym(Number(CFG.metrika), 'reachGoal', name); } catch (e) {}
  }

  /* ── кнопки «Оставить заявку»: цель и выбор тарифа ── */
  document.querySelectorAll('[data-cta]').forEach(function (a) {
    a.addEventListener('click', function () {
      goal('kabinet_cta');
      var t = a.getAttribute('data-tarif');
      if (t) {
        form.querySelectorAll('[name="tarif"]').forEach(function (r) { r.checked = (r.value === t); });
        clearErr('tarif');
      }
    });
  });

  /* ── поля ── */
  function field(name) { return form.querySelector('[data-field="' + name + '"]'); }
  function setErr(name, text) {
    var f = field(name); if (!f) return;
    var e = f.querySelector('.kb-err');
    f.classList.add('kb-bad'); e.textContent = text; e.hidden = false;
  }
  function clearErr(name) {
    var f = field(name); if (!f) return;
    var e = f.querySelector('.kb-err');
    f.classList.remove('kb-bad'); if (e) e.hidden = true;
  }
  ['name', 'telegram', 'phone', 'tarif', 'accept_pd'].forEach(function (n) {
    var f = field(n); if (!f) return;
    f.addEventListener('input', function () { clearErr(n); });
    f.addEventListener('change', function () { clearErr(n); });
  });

  /* ник: принимаем @ник, ник, t.me/ник, https://t.me/ник */
  function nick(v) {
    v = String(v || '').trim().replace(/^https?:\/\//i, '').replace(/^(www\.)?(t|telegram)\.me\//i, '');
    return v.replace(/^@+/, '').replace(/[\/?#].*$/, '').trim();
  }

  /* телефон: российский номер собирается в +7 XXX XXX-XX-XX, остальные как введены */
  var phone = form.querySelector('[name="phone"]');
  phone.addEventListener('input', function () {
    var raw = phone.value;
    if (/^\s*\+(?!7)/.test(raw)) { phone.value = raw.replace(/[^\d+\s()\-]/g, ''); return; }
    var d = raw.replace(/\D/g, '');
    if (!d) { phone.value = raw.indexOf('+') === 0 ? '+' : ''; return; }
    if (d.charAt(0) === '8' || d.charAt(0) === '7') d = d.slice(1);
    d = d.slice(0, 10);
    var out = '+7';
    if (d.length) out += ' ' + d.slice(0, 3);
    if (d.length > 3) out += ' ' + d.slice(3, 6);
    if (d.length > 6) out += '-' + d.slice(6, 8);
    if (d.length > 8) out += '-' + d.slice(8, 10);
    phone.value = out;
  });

  function picked(name) {
    var r = form.querySelector('[name="' + name + '"]:checked');
    return r ? r.value : '';
  }

  var busy = false;
  var formErr = form.querySelector('.kb-err-form');
  var btn = form.querySelector('.kb-submit');

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (busy) return;
    formErr.hidden = true;

    var name = form.querySelector('[name="name"]').value.trim();
    var tgNick = nick(form.querySelector('[name="telegram"]').value);
    var tel = phone.value.trim();
    var tarif = picked('tarif');
    var pd = form.querySelector('[name="accept_pd"]').checked;
    var first = null;
    function bad(n, text) { setErr(n, text); if (!first) first = n; }

    if (!name) bad('name', 'Напишите, как к вам обращаться.');
    if (!tgNick) bad('telegram', 'Напишите ваш ник в Telegram, например @anna.');
    else if (!/^[A-Za-z0-9_]{4,32}$/.test(tgNick)) bad('telegram', 'Ник в Telegram пишется латиницей, например @anna.');
    if (tel && tel !== '+7' && tel.replace(/\D/g, '').length < 10) bad('phone', 'В номере не хватает цифр. Поле можно оставить пустым.');
    if (!tarif) bad('tarif', 'Выберите тариф. Если не решили, нажмите «Пока не знаю».');
    if (!pd) bad('accept_pd', 'Без согласия на обработку данных мы не можем принять заявку.');
    if (first) {
      var f = field(first);
      f.scrollIntoView({ block: 'center', behavior: 'smooth' });
      var inp = f.querySelector('input'); if (inp) { try { inp.focus({ preventScroll: true }); } catch (e) {} }
      return;
    }
    if (tel === '+7') tel = '';

    var vazhno = picked('vazhno'), kogda = picked('kogda');
    var hot = (tarif === 'Самостоятельный' || tarif === 'С Виолой') && kogda === 'Сейчас';
    var prio = hot ? 'горячая' : 'тёплая';
    var now = new Date();
    var payload = {
      secret: CFG.secret,
      website: form.querySelector('[name="website"]').value,
      form: CFG.form,
      source: 'kabinet',
      name: name,
      telegram: tgNick,
      phone: tel,
      plan: 'Кабинет: ' + tarif,
      readiness: 'Кабинет · ' + prio + (vazhno ? ' · важно: ' + vazhno : '') + (kogda ? ' · когда: ' + kogda : ''),
      tarif: tarif,
      vazhno: vazhno,
      kogda: kogda,
      priority: prio,
      accept_offer: false,
      accept_pd: true,
      accept_ads: form.querySelector('[name="accept_ads"]').checked,
      consent_ts: now.toISOString(),
      sent_at: now.toISOString(),
      doc_version_consent: CFG.docConsent,
      page: window.location.href,
      ua: navigator.userAgent,
      src: 'kabinet',
      referrer: document.referrer || ''
    };
    UTM.forEach(function (k) { payload[k] = utm[k] || ''; });

    busy = true; btn.disabled = true; btn.textContent = 'Отправляем…';

    /* text/plain и redirect: 'manual' — как на основном сайте: Apps Script
       отвечает переадресацией, и следовать за ней браузеру не нужно. */
    fetch(CFG.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(payload),
      redirect: 'manual'
    }).then(function (res) {
      if (res.type !== 'opaqueredirect' && !res.ok) throw new Error('HTTP ' + res.status);
      done();
    }).catch(function () {
      busy = false; btn.disabled = false; btn.textContent = 'Отправить заявку';
      formErr.textContent = 'Заявка не отправилась. Проверьте интернет и нажмите кнопку ещё раз. Всё, что вы ввели, осталось на месте.';
      formErr.hidden = false;
    });
  });

  function done() {
    goal('kabinet_submit');
    form.hidden = true; sent.hidden = false;
    sent.scrollIntoView({ block: 'center' });
    try { sent.focus({ preventScroll: true }); } catch (e) {}
    setTimeout(function () { goal('kabinet_tg'); window.location.href = CFG.chat; }, 1500);
  }
  var manual = document.querySelector('[data-tg]');
  if (manual) manual.addEventListener('click', function () { goal('kabinet_tg'); });

  /* ── отзывы: скрин на весь экран ── */
  var zoom = document.querySelector('.kb-zoom');
  if (zoom) {
    document.querySelectorAll('[data-otz]').forEach(function (b) {
      b.addEventListener('click', function () { zoom.querySelector('img').src = b.getAttribute('data-otz'); zoom.hidden = false; });
    });
    zoom.addEventListener('click', function () { zoom.hidden = true; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') zoom.hidden = true; });
  }
})();
"""


def site_js_value(name):
    """Адрес приёмника и общий секрет берутся из site.js основного сайта."""
    src = build.read(os.path.join(build.BUILD_ASSETS, "site.js"))
    m = re.search(r"var %s = '([^']+)'" % name, src)
    if not m:
        raise SystemExit("в site.js не найдено %s" % name)
    return m.group(1)


def check_tarify():
    """Состав тарифов должен совпадать с главной страницей."""
    p = os.path.join(build.ROOT, "site", "index.html")
    if not os.path.exists(p):
        raise SystemExit("сначала соберите основной сайт: python3 build.py --theme barhat --noindex")
    text = re.sub(r"<[^>]+>", " ", build.read(p))
    text = re.sub(r"\s+", " ", html.unescape(text).replace(NBSP, " "))
    for line in TARIF_COMMON + TARIF_VIOLA:
        if line not in text:
            print("  кабинет: строки тарифа нет на главной, сверьте: %s" % line)


def build_page():
    check_tarify()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    files = []
    if os.path.isdir(REVIEWS):
        files = sorted(f for f in os.listdir(REVIEWS) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
        if files:
            os.makedirs(os.path.join(OUT, "reviews"))
            for f in files:
                shutil.copyfile(os.path.join(REVIEWS, f), os.path.join(OUT, "reviews", f))

    cfg = {
        "endpoint": site_js_value("LEAD_ENDPOINT"),
        "secret": site_js_value("FORM_SECRET"),
        "form": CONFIG["FORM_KIND"],
        "chat": CONFIG["MANAGER_CHAT_URL"],
        "metrika": CONFIG["METRIKA_ID"],
        "docConsent": re.search(r"doc_version_consent: '([^']+)'",
                                build.read(os.path.join(build.BUILD_ASSETS, "site.js"))).group(1),
    }
    css_file = os.path.join(build.ROOT, "site", "assets", "site.css")
    ver = hashlib.md5(open(css_file, "rb").read()).hexdigest()[:8]
    metrika = ""
    if CONFIG["METRIKA_ID"]:
        metrika = ("<script>(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};"
                   "m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,"
                   "a.parentNode.insertBefore(k,a)})(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');"
                   "ym(%s,'init',{clickmap:true,trackLinks:true,accurateTrackBounce:true});</script>\n"
                   % int(CONFIG["METRIKA_ID"]))

    title = "Заявка на практикум для Кабинета"
    desc = "Заявка на «Прикладную эмпатию 2.0» для подписчиков Кабинета Виолы Маро. Старт 1 ноября."
    page = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="theme-color" content="#C4142C">
<meta property="og:type" content="website">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:image" content="%(site)s/assets/img/hero.jpg">
<meta property="og:url" content="%(site)s/kabinet/">
<meta property="og:locale" content="ru_RU">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css?v=%(ver)s">
<style>%(css)s</style>
%(metrika)s</head>
<body>
<a class="skip" href="#main">К основному содержанию</a>
<div id="main" class="kb" role="main">%(body)s
</div>
%(footer)s
%(cookie)s
<script>%(js)s</script>
<script>%(cookiejs)s</script>
</body>
</html>
""" % {
        "title": esc(title), "desc": esc(desc), "site": SITE_URL, "ver": ver, "css": CSS, "metrika": metrika,
        "body": hero() + posle() + tarify() + kak() + programma() + komu() + otzyvy(files) + voprosy() + forma(),
        "footer": build.footer_html(), "cookie": build.COOKIE_HTML, "cookiejs": build.COOKIE_JS,
        "js": JS % {"cfg": json.dumps(cfg, ensure_ascii=False)},
    }
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("Кабинет → %s (%d КБ, отзывов: %d)" % (os.path.relpath(OUT, build.ROOT),
                                                  len(page.encode("utf-8")) // 1024, len(files)))


if __name__ == "__main__":
    build_page()
