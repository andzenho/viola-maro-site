#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страница-заявка «Прикладная эмпатия 2.0» для Кабинета: violamaro.ru/kabinet.

Это тот же сайт продукта, только под заявку: все блоки основной страницы
(что такое практикум, шесть сфер, недели, формат ответов, мастер-класс,
тарифы, подарки) и поверх них то, что нужно подписчикам закрытого канала:
блок «после заявки», «как это работает», «кому подойдёт», вопросы и форма
внизу страницы. Оплаты нет, цена Кабинета не пишется нигде: её называет
менеджер. После заявки человек попадает в чат с менеджером.

Как собирается. Сборщик основного сайта делает страницу заявки
(--mode zayavka) в папку site/kabinet, а этот модуль её дорабатывает:
меняет первый экран и карточки тарифов, убирает блоки про оплату,
вставляет свои блоки и форму, перенаправляет все кнопки на форму.

    python3 kabinet.py

Всё, что меняется без правки вёрстки, лежит в CONFIG. Тексты добавленных
блоков стоят дословно по ТЗ от 13.10.2026.
"""

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys

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

def posle():
    # Главное в каждом пункте выделено жирным: блок читается по этим словам.
    items = [
        ("расскажет подробно о программе", " и покажет презентацию практикума;"),
        ("ответит на ваши вопросы", " и поможет выбрать тариф;"),
        ("назовёт цену для Кабинета", " (она ниже, чем на сайте) и закрепит её за вами до %s;" % CONFIG["PRICE_DEADLINE"]),
        ("поможет оплатить,", " в том числе в рассрочку или из-за границы, и получить доступы к «Прикладной эмпатии»."),
    ]
    cards = "".join("<li><p><b>%s</b>%s</p></li>" % (nb(esc(a)), nb(esc(b))) for a, b in items)
    return """
<section class="kb kb-sec kb-posle" aria-label="После заявки">
  <div class="kb-in">
    <h2>После заявки вы&nbsp;попадёте <br>в&nbsp;чат с&nbsp;Дарьей <br>из&nbsp;команды Виолы</h2>
    <p class="kb-esli"><span>Если чат не&nbsp;откроется, Дарья сама напишет вам с&nbsp;аккаунта <b>@%s</b>.</span> <i>Она:</i></p>
    <ol class="kb-ona">%s</ol>
  </div>
</section>""" % (esc(CONFIG["MANAGER_TG"]), cards)


def kak():
    steps = [
        "Оставляете заявку. Это минута.",
        "Сразу открывается чат с Дарьей в Telegram. Она рассказывает о программе, показывает презентацию "
        "и отвечает на вопросы.",
        "Дарья называет цену Кабинета, помогает оплатить (картой РФ, зарубежной картой или в рассрочку) "
        "и выдаёт доступы.",
    ]
    return """
<section class="kb kb-sec" aria-label="Как это работает">
  <div class="kb-in">
    <h2>Как это работает</h2>
    <ol class="kb-steps">%s</ol>
  </div>
</section>""" % "".join("<li><span>%s</span></li>" % nb(esc(t)) for t in steps)


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
<section class="kb kb-sec" aria-label="Кому подойдёт">
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
<section class="kb kb-sec" aria-label="Отзывы">
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
<section class="kb kb-sec kb-pink" aria-label="Вопросы">
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
<section class="kb kb-sec kb-forma" id="zayavka" aria-label="Заявка">
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
.kb-small-dark { color: #5A5559; font-size: 15px; line-height: 1.4; }
.kb { --red: #C4142C; --red2: #B21028; --ink: #1C1A1D; --grey: #EAE7E2; --line: #DDD8D1; --pink: #FBE4E7;
      --prata: 'Prata', 'Times New Roman', Georgia, serif;
      color: var(--ink); font-size: 18px; line-height: 1.55; }
.kb *, .kb *::before, .kb *::after { box-sizing: border-box; }
.kb h2 { margin: 0; }
.kb p { margin: 0; }
.kb ul, .kb ol { margin: 0; padding: 0; list-style: none; }
.kb a { color: var(--red); }

/* кнопки */
.kb-btn { display: flex; align-items: center; justify-content: center; width: min(100%, 360px); min-height: 66px; margin: 0 auto; padding: 16px 26px; border: 0; border-radius: 16px; background: var(--red); color: #FFFFFF !important; font: inherit; font-size: 16px; font-weight: 700; letter-spacing: .09em; line-height: 1.25; text-align: center; text-decoration: none; text-transform: uppercase; cursor: pointer; box-shadow: 0 16px 30px -16px rgba(196,20,44,.55); -webkit-tap-highlight-color: transparent; }
.kb-btn:hover { filter: brightness(1.06); }
.kb-btn:focus-visible, .kb a:focus-visible, .kb summary:focus-visible, .kb input:focus-visible + span { outline: 3px solid #1C1A1D; outline-offset: 3px; }
.kb-btn-white { background: #FFFFFF; color: var(--red) !important; box-shadow: 0 18px 34px -18px rgba(70,4,14,.6); }
.kb-btn[disabled] { opacity: .6; cursor: default; }

/* блоки */
.kb-in { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 22px; }
.kb-wide { max-width: 1020px; }
.kb-h2b { margin-top: 34px !important; }
.kb-lead { font-size: 18.5px; color: #343034; }
main > section.kb-pink { background: var(--pink) !important; border-radius: clamp(36px, 6vw, 80px); }
.kb-tag { align-self: flex-start; width: fit-content; padding: 6px 14px; border-radius: 999px; background: #FCE9EA; color: var(--red); font-size: 13px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }

.kb-list { display: flex; flex-direction: column; gap: 12px; }
.kb-list li { position: relative; padding-left: 34px; }
.kb-list li::before { content: ""; position: absolute; left: 0; top: .28em; width: 22px; height: 22px; border-radius: 50%; background: var(--red); }
.kb-list li::after { content: ""; position: absolute; left: 8px; top: calc(.28em + 4px); width: 5px; height: 10px; border: solid #FFFFFF; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.kb-sec > .kb-in > .kb-list { padding: 24px 22px; border-radius: 26px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 26px 46px -28px rgba(28,26,29,.34); }

/* тарифы: плашка под ценой и строка под карточками */
.kb-deshevle { margin: 0; padding: 12px 16px; border-radius: 14px; background: #FCE9EA; color: #A30F23; font-size: 16px; font-weight: 700; line-height: 1.35; }
.kb-pod { margin: 0; text-align: center; color: #FFFFFF; font-size: 17px; font-weight: 600; }
.kb-pod-dark { color: #5A5559; }
#tarify a.kb-tarif-btn[data-btn] { display: flex; align-items: center; justify-content: center; width: 100% !important; min-height: 68px; padding: 14px 14px !important; white-space: normal !important; text-align: center; font-size: 15px !important; letter-spacing: .07em !important; line-height: 1.3 !important; text-decoration: none; }

/* «После заявки»: спокойный заголовок, строка про аккаунт плашкой,
   четыре дела менеджера карточками с номерами */
main > section.kb-posle .kb-in { max-width: 860px; gap: 20px; }
main > section.kb-posle h2 { font-size: clamp(27px, 3.5vw, 44px) !important; line-height: 1.18 !important; }
.kb-esli { display: flex; flex-direction: column; gap: 18px; font-size: 17.5px; line-height: 1.45; color: #343034; }
.kb-esli span { padding: 14px 18px; border-radius: 16px; background: #FCE9EA; }
.kb-esli span b { color: #A30F23; white-space: nowrap; }
.kb-esli i { font-family: var(--prata); font-style: normal; font-size: 24px; line-height: 1; color: var(--red); }
.kb-ona { counter-reset: ona; display: grid; grid-template-columns: 1fr; gap: 10px; }
.kb-ona li { counter-increment: ona; display: grid; grid-template-columns: 52px 1fr; gap: 4px; align-items: start; padding: 20px 20px 20px 18px; border-radius: 22px 22px 22px 6px; background: #FFFFFF; box-shadow: 0 0 0 1px var(--line), 0 26px 46px -28px rgba(28,26,29,.34); }
.kb-ona li::before { content: "0" counter(ona); font-family: var(--prata); font-size: 34px; line-height: 1.05; color: var(--red); }
.kb-ona p { font-size: 17.5px; line-height: 1.5; color: #5A5559; }
.kb-ona b { display: block; margin-bottom: 2px; font-size: 19px; font-weight: 700; line-height: 1.3; color: var(--ink); }
@media (min-width: 760px) { .kb-ona { grid-template-columns: 1fr 1fr; gap: 14px; } }

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
.kb-form h2, .kb-sent h2 { font-size: clamp(30px, 4vw, 46px) !important; }
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
  main > section.kb-pink { margin: 0 20px; }
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


def sec_span(page, label):
    """Границы секции с данной подписью: начало <section …> и конец </section>."""
    i = page.find('aria-label="%s"' % label)
    if i < 0:
        raise SystemExit("кабинет: на странице нет блока «%s»" % label)
    a = page.rfind("<section", 0, i)
    blk = build.find_block(page, "section", a)
    return blk[0], blk[3]


def swap(page, old, new, count=1, what=""):
    """Замена с проверкой: если образец пропал, сборка говорит об этом."""
    if page.count(old) < 1:
        print("  кабинет: не найдено для замены: %s" % (what or old[:60]))
        return page
    return page.replace(old, new, count) if count else page.replace(old, new)


TITLE = "Заявка на практикум для Кабинета"
H1 = "Заявка на <br>«Прикладную <br>эмпатию&nbsp;2.0»"
SUB = ("Старт 1&nbsp;ноября. Для тех, кто в&nbsp;Кабинете, цена ниже, чем на&nbsp;сайте. "
       "Её назовёт Дарья после заявки.")
POD = "После заявки вы попадёте в&nbsp;чат с&nbsp;Дарьей из&nbsp;команды Виолы."


def rework(page, files):
    # ── заголовок вкладки и превью ──
    page = re.sub(r"<title>.*?</title>", "<title>%s</title>" % TITLE, page, count=1)
    page = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + TITLE, page, count=1)
    page = swap(page, '<meta property="og:locale"',
                '<meta property="og:image" content="%s/assets/img/hero.jpg">\n'
                '<meta property="og:url" content="%s/kabinet/">\n<meta property="og:locale"'
                % (SITE_URL, SITE_URL), what="og:locale")

    # ── первый экран, телефон: метка, заголовок, подзаголовок, строка под кнопкой ──
    page = re.sub(r'(<p data-h2-title=""[^>]*style="--bukv: )\d+(;">).*?</p>',
                  lambda m: '<span data-h2-tag="">Только для Кабинета</span>' + m.group(1) + "12" + m.group(2) + H1 + "</p>",
                  page, count=1, flags=re.S)
    page = re.sub(r'<p data-h2-sub="">.*?</p>', '<p data-h2-sub="">%s</p>' % SUB, page, count=1, flags=re.S)
    i = page.find('<div data-h2-top="">')
    j = page.find("</a>", i) + 4
    page = page[:j] + '<p data-h2-pod="">%s</p>' % POD + page[j:]

    # ── первый экран, широкий: то же в его разметке ──
    i = page.find('data-hero-card=""')
    j = page.find("<h1", i)
    k = page.rfind(">", i, page.rfind("</div>", i, j)) + 1          # текст надзаголовка
    page = page[:k] + "Только для Кабинета" + page[page.find("</div>", k):]
    page = re.sub(r"(<h1[^>]*>).*?(</h1>)", lambda m: m.group(1) + H1 + m.group(2), page, count=1, flags=re.S)
    i = page.find('data-hero-card=""')
    j = page.find("</a>", i) + 4
    j = page.find("</div>", page.find("</div>", j) + 6) + 6             # за строкой с кнопкой и плашкой старта
    page = page[:j] + ('<p data-hero-pod="" style="margin: 0; font-size: 17px; line-height: 1.45;">%s %s</p>'
                       % (SUB.split(". ", 1)[1], POD)) + page[j:]

    # ── тарифы: цена без валют, плашка, одна кнопка, строка про рассрочку ──
    a, b = sec_span(page, "Тарифы")
    t = page[a:b]
    t = re.sub(r'<div style="[^"]*">\s*\$\d+[^<]*</div>', "", t)                      # $240 €215
    t = re.sub(r'<button\b[^>]*data-btn="quiet"[^>]*>.*?</button>', "", t, flags=re.S)  # «Хочу в рассрочку»
    names = iter(["Самостоятельный", "С Виолой"])

    def card_btn(m):
        style = re.search(r'style="([^"]*)"', m.group(0)).group(1)
        return ('<p class="kb-deshevle">В&nbsp;Кабинете дешевле. Цену назовёт Дарья после заявки</p>'
                '<a class="kb-tarif-btn" href="#zayavka" data-cta="" data-tarif="%s" data-btn="primary" '
                'style="%s">Оставить заявку на&nbsp;этот тариф</a>' % (next(names), style))
    t, n = re.subn(r'<button\b[^>]*data-btn="primary"[^>]*>.*?</button>', card_btn, t, flags=re.S)
    if n != 2:
        print("  кабинет: кнопок тарифа найдено %d, ждали 2" % n)
    if CONFIG["SEATS_LEFT"]:
        t = t.replace("Всего 50&nbsp;мест", "Всего 50&nbsp;мест, осталось %s" % esc(str(CONFIG["SEATS_LEFT"])))
    # строка под карточками — перед подписью про аккаунт
    k = t.rfind('<div style="max-width: 760px;')
    line = '<p class="kb-pod">Можно в&nbsp;рассрочку на&nbsp;3, 6 или&nbsp;12&nbsp;месяцев, Дарья всё расскажет</p>'
    t = t[:k] + line + t[k:] if k > 0 else t + line
    page = page[:a] + t + page[b:]

    # ── блоки про оплату здесь не нужны ──
    for label in ("Проблемы с оплатой", "Рассрочка"):
        a, b = sec_span(page, label)
        page = page[:a] + page[b:]

    # ── подарки: колонка «за саму заявку» обещает закрытый канал, а читатель
    #    уже в нём. Остаются четыре бонуса после оплаты. ──
    a, b = sec_span(page, "Подарки и условия")
    g = page[a:b]
    i = g.find('<div data-za-zayavku=""')
    if i >= 0:
        blk = build.find_block(g, "div", i)
        g = g[:blk[0]] + g[blk[3]:]
    g = g.replace("Что даёт заявка?", "Что вы получаете?").replace('id="zapis"', 'id="podarki"')
    page = page[:a] + g + page[b:]

    # ── все кнопки ведут к форме внизу ──
    page = re.sub(r'(<a\b[^>]*?)href="#(?:tarify|zapis)"([^>]*data-btn="primary")',
                  r'\1href="#zayavka" data-cta=""\2', page)
    page = re.sub(r'\sdata-open-form="[^"]*"', "", page)

    # ── свои блоки ──
    def after(page, label, block):
        _a, b = sec_span(page, label)
        return page[:b] + block + page[b:]

    def before(page, label, block):
        a, _b = sec_span(page, label)
        return page[:a] + block + page[a:]

    page = after(page, "Первый экран", posle())
    page = after(page, "Зачем мне это", komu())
    page = after(page, "Тарифы", kak())
    page = before(page, "Финальный призыв", otzyvy(files) + voprosy())
    page = after(page, "Финальный призыв", forma())
    return page


def build_page():
    # Основа — страница заявки основного сайта, собранная в свою папку.
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    subprocess.run([sys.executable, os.path.join(build.ROOT, "build.py"), "--mode", "zayavka",
                    "--theme", "barhat", "--out", OUT, "--base", "/kabinet", "--docs-root", "--noindex"],
                   check=True, stdout=subprocess.DEVNULL)

    files = []
    if os.path.isdir(REVIEWS):
        files = sorted(f for f in os.listdir(REVIEWS) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
        if files:
            os.makedirs(os.path.join(OUT, "reviews"))
            for f in files:
                shutil.copyfile(os.path.join(REVIEWS, f), os.path.join(OUT, "reviews", f))

    site_js = build.read(os.path.join(build.BUILD_ASSETS, "site.js"))
    cfg = {
        "endpoint": site_js_value("LEAD_ENDPOINT"),
        "secret": site_js_value("FORM_SECRET"),
        "form": CONFIG["FORM_KIND"],
        "chat": CONFIG["MANAGER_CHAT_URL"],
        "metrika": CONFIG["METRIKA_ID"],
        "docConsent": re.search(r"doc_version_consent: '([^']+)'", site_js).group(1),
    }
    metrika = ""
    if CONFIG["METRIKA_ID"]:
        metrika = ("<script>(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};"
                   "m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,"
                   "a.parentNode.insertBefore(k,a)})(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');"
                   "ym(%s,'init',{clickmap:true,trackLinks:true,accurateTrackBounce:true});</script>\n"
                   % int(CONFIG["METRIKA_ID"]))

    path = os.path.join(OUT, "index.html")
    page = rework(build.read(path), files)
    page = page.replace("</head>", "<style>%s</style>\n%s</head>" % (CSS, metrika), 1)
    page = page.replace("</body>", "<script>%s</script>\n</body>" % (JS % {"cfg": json.dumps(cfg, ensure_ascii=False)}), 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    print("Кабинет → %s (%d КБ, отзывов: %d)" % (os.path.relpath(OUT, build.ROOT),
                                                  len(page.encode("utf-8")) // 1024, len(files)))


if __name__ == "__main__":
    build_page()
