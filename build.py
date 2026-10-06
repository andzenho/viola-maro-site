#!/usr/bin/env python3
# coding: utf-8
"""
Собирает статический сайт из исходников проекта.

Вход:
  source/Лендинг ПЭ 4.0.dc.html   — шаблон DesignCraft (React-разметка)
  source/assets/viola-hero.png    — портрет для первого экрана
  Страницы-к-публикации/*.html    — фрагменты правовых документов (pandoc)
  build-assets/fonts/*.woff2      — подшитые шрифты

Выход: site/ — семь страниц, ноль внешних запросов.

Запуск:
  python3 build.py                          сборка под свой домен
  python3 build.py --base /Viola-Maro       сборка под подпуть (GitHub Pages)
  python3 build.py --noindex                запретить индексацию (превью)
  python3 build.py --mode pre --out site/pre   редирект /pre → /zayavka
  python3 build.py --mode bron --out site/bron страница брони
  python3 build.py --mode zayavka --out site/zayavka   заявка: цены есть,
                                              оплаты на странице нет

Сборка под домен violamaro.ru — оплата в корне, заявка в /zayavka/,
правовые страницы в одном экземпляре:

  python3 build.py --out dist --cname violamaro.ru
  python3 build.py --mode pre --out dist/pre --base /pre --noindex

Куски для вставки в блок T123 Тильды:

  python3 build.py --mode pre --out tilda-src --tilda tilda
"""

import base64
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source")
LEGAL = os.path.join(ROOT, "Страницы-к-публикации")
BUILD_ASSETS = os.path.join(ROOT, "build-assets")
OUT = os.path.join(ROOT, "site")

TG_NAME = "@violamaroteam"          # аккаунт службы заботы
TG = "https://t.me/" + TG_NAME[1:]  # ссылка и подпись — из одного места
EMAIL = "mg.ananizh@gmail.com"
CARE_HOURS = "пн–пт, 10:00–18:00\u00a0МСК"

# Аккаунт отдела заботы. Рядом с ним всегда стоит строка «Пишем только
# с этого аккаунта»: человеку, который платит незнакомой команде, важнее
# знать, с чего ему напишут, чем куда обратиться — поддельные «менеджеры»
# в Telegram после оплаты обычная история.
#
# Список, а не одна строка: если аккаунтов снова станет несколько, блок
# и текст соберутся сами, без правок вёрстки.
CARE_ACCOUNTS = (
    ("Отдел заботы", TG_NAME, TG),
)
CARE_ONLY = ("Пишем только с\u00a0этого аккаунта."
             if len(CARE_ACCOUNTS) == 1 else
             "Пишем только с\u00a0этих аккаунтов.")

# Телефонный кадр режется из того же снимка, что и десктопный: одно фото
# на оба экрана, иначе на десктопе одно выражение лица, а на телефоне другое.
# ── Телефонный кадр: привязка к лицу ────────────────────────────────────
#
# Прежние подходы задавали кадр под один размер экрана и разъезжались на
# всех остальных: где-то Виолу срезало, где-то она уползала под текст.
# Причина в том, что положение считалось от края кадра, а не от неё самой.
#
# Теперь опорная точка — центр лица. Работает так: object-position: P%
# ставит точку P% изображения ровно в P% рамки, и это верно при ЛЮБОМ
# её размере. Значит, достаточно вырезать кадр так, чтобы лицо оказалось
# на нужной доле ширины, и оно там и останется — на любом телефоне.
#
# Вырезка ниже ставит лицо на 74% ширины и 22% высоты. Эти же числа стоят
# в object-position в base.css — менять их нужно парой.
FACE_X, FACE_Y = 1250, 210        # центр лица в исходнике 1672×941
MOBILE_CROP = (368, 0, 1560, 941) # даёт лицо на 74% ширины кадра

DOCS = [
    ("oferta", "offer", "Публичная оферта"),
    ("prilozhenie-1", "offer-prilozhenie", "Приложение № 1 к Публичной оферте"),
    ("politika-pd", "privacy", "Политика обработки персональных данных"),
    ("soglasie-pd", "consent", "Согласие на обработку персональных данных"),
    ("soglasie-rassylki", "consent-ads", "Согласие на рекламные и информационные сообщения"),
    ("polzovatelskoe-soglashenie", "terms", "Пользовательское соглашение"),
]

DOC_URL = {slug: "/" + url for slug, url, _ in DOCS}

# Все адреса внутри страниц пишутся от корня: так требуют правовые документы
# («/offer», «/privacy» — они названы в тексте оферты и в чекбоксах).
# На GitHub Pages сайт живёт в подпапке /Viola-Maro/, поэтому перед выдачей
# адреса получают префикс. На своём домене BASE пустой и ничего не меняется.
BASE = ""
NOINDEX = False

# Правовые страницы должны лежать в одном экземпляре: у документа обязан
# быть постоянный адрес, версии которого вы храните. Когда обе версии сайта
# живут на одном домене, вторая свои копии не строит, а ссылается на первые.
DOCS_ROOT = False

# Своё имя домена для GitHub Pages: без этого файла он обслуживает
# только адрес вида имя.github.io.
CNAME = ""

# Куда положить куски для вставки в блок T123 Тильды.
TILDA_OUT = ""

# Два сайта из одного шаблона. "pay" — продажа с тарифами и оплатой,
# "pre" — служебный редирект со старого адреса /pre на /zayavka
# вместо платежа. Девять экранов из одиннадцати у них общие, поэтому
# копией файлов это делать нельзя: правки разъедутся на первой же неделе.
# "rassrochka" — та же продажа, но по внутренней рассрочке: на странице
# вносится половина стоимости тарифа. "bron" — короткая страница брони.
# "predzapis" — анкета предзаписи: без цен и оплаты, после анкеты
# открывается закрытый канал. Это прежний сайт предзаписи (/pre) в новом
# наполнении; сам адрес /pre остаётся редиректом на заявку.
MODE = "pay"

# ── Оплата: два способа на каждой странице ──────────────────────────────
#
# Денежных страниц три: полная оплата (/), внутренняя рассрочка
# (/rassrochka) и бронь (/bron). На каждой после формы человек выбирает,
# чем платит: российской картой или зарубежной.
#
#   ru   — GetPlatinum, своя ссылка на каждый тариф. На странице полной
#          оплаты там же оформляется рассрочка от банка.
#   intl — Lava, одна ссылка на страницу: тариф человек выбирает уже там,
#          поэтому окно подсказывает, какой именно.
#
# Суммы стоят здесь же и уходят в окно оплаты вместе со ссылками: цена
# на кнопке и цена на платёжной странице не должны расходиться. Перед
# публикацией каждую ссылку открывают и сверяют название и сумму.
_GP = "https://anny-nizh.getplatinum.ru/payment/"
_LAVA = "https://app.lava.top/products/"
PAY = {
    "pay": {
        "intl": _LAVA + "5dc037cd-01c0-4d51-9add-274087367214",
        "plans": {
            "basic": {"name": "Самостоятельный", "ru": _GP + "JQqAJkS",
                      "rub": "19 900", "usd": "240", "eur": "215"},
            "full": {"name": "С Виолой", "ru": _GP + "ppgQJJ7",
                     "rub": "39 900", "usd": "480", "eur": "430"},
        },
    },
    # Внутренняя рассрочка 50/50: два равных платежа, на странице один.
    "rassrochka": {
        "intl": _LAVA + "54645129-e4e3-4c7a-bfc7-bf487407dff7",
        "plans": {
            "basic": {"name": "Самостоятельный", "ru": _GP + "aQT8pYy",
                      "rub": "9 950", "usd": "120", "eur": "108"},
            "full": {"name": "С Виолой", "ru": _GP + "Imsdgni",
                     "rub": "19 950", "usd": "240", "eur": "215"},
        },
    },
    "bron": {
        "intl": _LAVA + "238f0f0a-fbee-4a14-95d4-de951d7843f0",
        "plans": {
            "bron": {"name": "", "ru": _GP + "ASs2MgT",
                     "rub": "5 000", "usd": "60", "eur": "55"},
        },
    },
}

# Что сказано под ценой у каждого способа. Пустая строка — без подписи.
PAY_NOTES = {
    "pay": ("Здесь&nbsp;же можно оформить рассрочку от&nbsp;банка.", ""),
    "rassrochka": ("", ""),
    "bron": ("", ""),
}
# Строка под названием тарифа на шаге оплаты, общая для обоих способов.
PAY_LEAD = {
    "pay": "",
    "rassrochka": "Сейчас вы&nbsp;вносите один платёж из&nbsp;двух равных.",
    "bron": "Бронь засчитывается в&nbsp;стоимость участия.",
}

# ── Страница брони ──────────────────────────────────────────────────────
#
# Отдельная короткая страница, ссылку на которую отправляют лично: человек
# уже поговорил с командой и решает вносить бронь. Продавать заново незачем,
# поэтому экраны с программой на ней не выводятся.
#
# Бронь — это АВАНС, а не задаток. Задаток по ст. 380–381 ГК обязан быть
# прямо назван задатком письменно и тянет за собой штрафные последствия
# для обеих сторон; для потребителя это лишний риск. Аванс засчитывается
# в стоимость и возвращается при отказе, как того и требует ст. 32 ЗоЗПП:
# написать «бронь невозвратна» нельзя, такое условие ничтожно.
#
# Заполняется перед выпуском. Пустые значения роняют сборку намеренно:
# страница про деньги не должна выйти с недописанными цифрами.
BOOKING_AMOUNT = "5 000 ₽"
BOOKING_DEADLINE = "1 ноября"         # день старта потока
# Ссылки на оплату брони и её сумма в валюте — в словаре PAY ниже.

# Формулировка про судьбу брони при неоплате остатка.
#
# Заказчик просил «невозвратная». Так писать нельзя, и запрещает это не
# закон вообще, а п. 8.1 их собственной оферты: «Право Заказчика на отказ
# от Договора не может быть ограничено настоящей Офертой. Условия,
# ущемляющие права потребителя по сравнению с законодательством, ничтожны.»
# Строка «бронь не возвращается» на странице противоречила бы договору,
# на который эта же страница ссылается.
#
# Поэтому то же по сути, но как перенос, а не как утрата: деньги остаются
# у человека, просто в другом потоке.
#
# Строку про порядок возврата с самой страницы заказчик просил снять — это
# его право: рекламировать возврат страница не обязана, раздел 8 оферты
# от этого никуда не девается. Чего на странице быть не может, так это
# обратного утверждения «бронь не возвращается»: оно прямо спорило бы
# с п. 8.1 договора, на который эта же страница ссылается.
BOOKING_CARRY = ("Если не доплатите до старта, бронь переносится "
                 "на следующий поток или на другой продукт Виолы Маро&nbsp;— "
                 "и засчитывается в его стоимость.")

# Заказчик хочет невозвратную бронь, оформленную как отдельная услуга
# «сохранение условий». Переключатель заведён заранее, но включать его
# нельзя, пока юрист не пропишет такую услугу в оферте: сегодня п. 8.1
# даёт безусловное право на отказ, и надпись «невозвратно» спорила бы
# с договором, на который ссылается сама страница.
#
# Запрос юристу — Страницы-к-публикации/_ЗАПРОС-юристу-бронь-как-услуга.md
# Включать только вместе с новой редакцией оферты.
BOOKING_AS_SERVICE = False

CHANNEL_URL = "https://t.me/+iIqJoSn2UBU3Yzky"

# ── Страница события «Неудобные» ────────────────────────────────────────
#
# Отдельный лендинг на три дня, к практикуму отношения не имеет: своя
# разметка (build-assets/neudobnye.html) и свои стили (neudobnye.css).
# Общее с остальным сайтом — шапка, подвал, cookie-полоса, шрифты,
# палитра и портрет на первом экране: правовые ссылки и реквизиты
# обязаны быть теми же самыми, а Виола — той же самой.
#
# Адреса платёжных страниц заказчик присылает отдельно. Пока пусто,
# кнопки никуда не ведут и сборка говорит об этом вслух: страница про
# деньги не должна тихо выйти с мёртвыми кнопками.
NEUD_PAY_RUB = ""    # оплата в рублях (в ней же рассрочка)
NEUD_PAY_INTL = ""   # оплата с зарубежной карты

# 27 сентября в 00:00 МСК цена растёт с 17 900 / 34 900 ₽
# до 19 900 / 39 900 ₽. Таймер относится только к цене; подарки
# после оплаты остаются частью программы без ограничения по сроку.
#
# Правовые документы не трогаются вовсе: в Приложении № 1 свои даты,
# менять их может только юрист.
PRICE_ISO = "2026-09-27T00:00:00+03:00"

ABS_ROOTS = ["assets/"] + [url for _s, url, _t in DOCS]


def apply_base(text):
    """Проставляет префикс подпути всем корневым адресам в готовой странице."""
    if not BASE:
        return text
    text = text.replace('href="/"', 'href="%s/"' % BASE)
    roots = ["assets/"] if DOCS_ROOT else ABS_ROOTS
    for root in roots:
        text = text.replace('"/' + root, '"%s/%s' % (BASE, root))   # href, src
        text = text.replace(" /" + root, " %s/%s" % (BASE, root))   # записи srcset
        text = text.replace("(/" + root, "(%s/%s" % (BASE, root))   # url() в CSS
    return text


# ─────────────────────────────────────────────────────────── данные недель ──
# Перенесено дословно из <script type="text/x-dc"> исходного шаблона.

ICONS = [
    [{"c": [12, 8, 3.4]}, "M5.5 19.5c.9-3.3 3.4-5 6.5-5s5.6 1.7 6.5 5"],
    [{"c": [9, 9, 3]}, {"c": [16.5, 12, 2.4]},
     "M3.5 19c.7-2.8 2.8-4.3 5.5-4.3M13 19c.3-1.9 1.6-2.9 3.5-2.9s3.2 1 3.5 2.9"],
    ["M12 20s-6.5-3.9-6.5-8.4A3.9 3.9 0 0 1 12 9a3.9 3.9 0 0 1 6.5 2.6C18.5 16.1 12 20 12 20z"],
    [{"c": [12, 5, 2.2]}, "M12 8v7M8 10.5h8M9.5 20l2.5-5 2.5 5"],
    ["M12 3.5l2.5 5.2 5.5.8-4 3.9 1 5.6-5-2.7-5 2.7 1-5.6-4-3.9 5.5-.8z"],
    [{"c": [12, 12, 8.2]},
     "M14.5 9.3c-.6-.8-1.5-1.2-2.6-1.2-1.5 0-2.4.8-2.4 1.8 0 2.5 5 1.3 5 3.9 0 1.1-1 2-2.6 2-1.2 0-2.1-.4-2.7-1.2M12 6.6v10.8"],
]

WEEKS = [
    {
        "n": "1", "title": "Фигура эмпата",
        "q": "Кто я такой? Это дар или со мной что-то не так?",
        "lead": "Эмпатия как суперсила. Эмпатия — это природный интеллект, который нужно развивать и использовать. Эмпатия как основа внутренней самоценности. Психология плюс духовность равняется эмпатия.",
        "tricks": "— как отличить эмпатию от слияния и созависимости\n— упражнения на распознавание своего эмпатического канала\n— формирование новой самоидентификации: «Я — эмпат, и это моя сила»",
        "note": "",
    },
    {
        "n": "2", "title": "Эмпат и отношения с людьми",
        "q": "Почему мной пользуются? Как отказать и не чувствовать себя виноватым? Почему на работе больше всех достаётся мне?",
        "lead": "Выход из детской зависимой позиции, позиции жертвы — в созидательную позицию взрослого. Осознанность и личные границы: формирование личного поля защиты от манипуляций эго-зависимых и токсичных людей.",
        "tricks": "— распознавание признаков токсичного взаимодействия\n— техники быстрого возвращения в себя после контакта\n— формирование внутреннего взрослого, который умеет говорить «нет» без чувства вины",
        "note": "",
    },
    {
        "n": "3", "title": "Эмпат-родители и эмпат-дети",
        "q": "Как быть опорой родным и жить при этом свою жизнь? Мой ребёнок эмпат — что ему нужно?",
        "lead": "Как воспитывать своих детей с повышенной чувствительностью и как сепарироваться от опыта детско-родительских отношений. Баланс внутренних и внешних ролей — родители, дети, взрослые.",
        "tricks": "— особенности воспитания высокочувствительных детей\n— практики внутренней сепарации\n— карта внутренних ролей: где я сейчас — Ребёнок, Родитель или Взрослый",
        "note": "",
    },
    {
        "n": "4", "title": "Психосоматика у эмпата",
        "q": "Почему у меня всё время что-то болит, а врачи ничего не находят?",
        "lead": "Формирование психосоматики: этапы и механизмы. Язык психосоматики и как определить её формирование на первых этапах. Области проявления психосоматики.",
        "tricks": "— карта тела: какая эмоция в какую зону уходит\n— признаки начинающейся психосоматики\n— простые телесные практики возвращения контакта с собой",
        "note": "Практикум не заменяет обследование и лечение у врача.",
    },
    {
        "n": "5", "title": "Самореализация людей с повышенной чувствительностью",
        "q": "Как найти своё место? Внутри богато, а снаружи будто всё слишком грубо.",
        "lead": "Как совместить духовное и социальное. Проявленность вовне и раскрытие себя внутри.",
        "tricks": "— поиск своих ниш и форматов самовыражения\n— баланс уединения и социальной активности\n— практики безопасной проявленности",
        "note": "",
    },
    {
        "n": "6", "title": "Психология наполненности и деньги",
        "q": "Почему я не могу удержать деньги? В чём моя ценность?",
        "lead": "Психология наполненности как фундамент жизненного изобилия — в отношениях, в финансах и не только. Состояние наполненности и ресурсности как фундамент благополучия.",
        "tricks": "— диагностика: зарабатываю я из наполненности или из дефицита\n— как отличить денежную мотивацию из пустоты от мотивации из полноты\n— практики возвращения в ресурсность перед финансовыми решениями",
        "note": "",
    },
]


def icon_svg(paths):
    parts = []
    for d in paths:
        if isinstance(d, dict):
            cx, cy, r = d["c"]
            parts.append('<circle cx="%s" cy="%s" r="%s"/>' % (cx, cy, r))
        else:
            parts.append('<path d="%s"/>' % d)
    return ('<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + "".join(parts) + "</svg>")


for i, w in enumerate(WEEKS):
    w["icon"] = icon_svg(ICONS[i])
    w["label"] = "НЕДЕЛЯ " + w["n"]
    w["quote"] = "«" + w["q"] + "»"
    w["items"] = [
        {"i": j + 1, "text": re.sub(r"^—\s*", "", t)}
        for j, t in enumerate(x for x in w["tricks"].split("\n") if x)
    ]


# ─────────────────────────────────────────────── парсинг шаблона .dc.html ──


# ───────────────────────────────────────── тестовое оформление «море» ──
#
# Включается флагом --theme more. Наполнение, формы, цены и скрипты те же:
# сборщик собирает обычную страницу, а в самом конце перекрашивает её,
# перестраивает несколько блоков (_theme_layout) и добавляет слой стилей
# (THEME_CSS). Тексты не меняются. Действующие страницы собираются
# без флага и от этого блока не зависят.
#
# Откуда вид. Тест 2.0: один гротеск, цветные блоки, сообщения, плашки,
# красная кнопка, чернильно-синий текст на сливочной бумаге. Правила вида
# перечислены в начале THEME_CSS.
#
# Фотография на странице одна, на первом экране: настоящий снимок Виолы
# (source/assets/viola-cutout.png, вырезан по контуру) на фоне террасы
# из презентации (build-assets/tema-more/terrasa.jpg). Сгенерированных
# изображений человека на странице нет: они выходят неживыми.

THEME = ""
THEME_DIR = os.path.join(BUILD_ASSETS, "tema-more")
# Высокий узкий шрифт крупных заголовков. Bebas Neue Bold, свободная
# лицензия SIL OFL 1.1 (записана в самом файле), кириллица есть.
THEME_FONT = "BebasNeue-Bold.ttf"

# Первый экран. Настольный кадр 1672×941: Виола справа, слева место под
# карточку с текстом. Телефонный 900×900: лицо в середине кадра.
# масштаб — доля от размера вырезки; лево и верх — куда встаёт её угол.
THEME_HERO = {
    "desktop": {"size": (1672, 941), "centering": (0.5, 0.5), "scale": 0.70, "left": 842, "top": 70},
    "mobile":  {"size": (900, 900),  "centering": (0.62, 0.5), "scale": 0.72, "left": 4,   "top": 8},
}


def _theme_terrace(size, centering):
    """Терраса из презентации, обрезанная под кадр и слегка размытая."""
    from PIL import Image, ImageFilter, ImageOps
    bg = Image.open(os.path.join(THEME_DIR, "terrasa.jpg")).convert("RGB")
    return ImageOps.fit(bg, size, Image.LANCZOS, centering=centering).filter(ImageFilter.GaussianBlur(5))


def _theme_cutout(scale):
    """Снимок Виолы, вырезанный по контуру. Чуть теплится под вечерний свет."""
    from PIL import Image
    cut = Image.open(os.path.join(SRC, "assets", "viola-cutout.png")).convert("RGBA")
    cut = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.LANCZOS)
    r, g, b, a = cut.split()
    rgb = Image.blend(Image.merge("RGB", (r, g, b)), Image.new("RGB", cut.size, (255, 196, 120)), 0.10)
    return Image.merge("RGBA", (*rgb.split(), a))


def theme_hero_image(kind):
    """Кадр первого экрана одним слоем: терраса и на ней Виола."""
    cfg = THEME_HERO[kind]
    bg = _theme_terrace(cfg["size"], cfg["centering"])
    cut = _theme_cutout(cfg["scale"])
    bg.paste(cut, (cfg["left"], cfg["top"]), cut)
    return bg


THEME_HEX = {
    # основной текст и тёмные кружки
    "#2E2521": "#18213A", "#2A211C": "#18213A", "#332B26": "#18213A", "#372B25": "#18213A",
    # тёмные заливки → небо, от глубокого к светлому
    "#211A16": "#0F2A66", "#241C18": "#0F2A66", "#2B211C": "#102F73",
    "#2E2420": "#143A85", "#33271F": "#143A85", "#3B2E28": "#1A4A96",
    "#4A392F": "#1F56A6", "#4E3C31": "#1F56A6", "#46362D": "#1F56A6", "#4A3A31": "#2A6DB8",
    # второстепенный текст
    "#5C5149": "#465068", "#574C44": "#465068", "#6E6158": "#4A546C", "#776B61": "#4A546C",
    "#7D7167": "#4A546C", "#9A9088": "#4A546C", "#B8AA9C": "#9AA3B5", "#C9BCAD": "#B9C2D3",
    # бронза → золото: тёмное для подписей на светлом, яркое для заливок и линий
    "#8A5A2B": "#B01E22", "#A3835F": "#B07A1E", "#6B4E2C": "#B01E22",
    "#C9A87F": "#F0B13F", "#C29A6C": "#E39A2B", "#D9BC92": "#F3C566", "#E9C98F": "#F6CF7A",
    "#F0DCBB": "#FBE3B0", "#EDD9B8": "#FBE3B0", "#F7EBD8": "#FDF1D9", "#F0E2CE": "#F8E6C6",
    # бумага и линии
    "#F6F0E8": "#FBF6EC", "#F6EFE5": "#FBF6EC", "#F3EBE0": "#F4ECDD", "#F5EFE6": "#F7F0E2",
    "#EFE6DA": "#F4ECDD", "#F1EAE0": "#F4ECDD", "#F1E8DA": "#F4ECDD", "#F4EDE3": "#F7F0E2",
    "#EDE4D8": "#F1E8D8", "#E9DFD2": "#EFE4D2", "#E4DACD": "#EBDFCA", "#EBDECB": "#EBDFCA",
    "#E7DAC8": "#EBDFCA", "#DCD1C4": "#D9CDB6", "#DCCFBC": "#D9CDB6",
    "#E6DCCF": "#EEF3FB",                      # светлый текст на тёмном
    # зелёные галочки тарифов → синий
    "#5A7A55": "#1F4C97",
}

THEME_RGB = {
    (60, 48, 40): (24, 33, 58), (60, 45, 32): (24, 33, 58),
    (18, 12, 8): (8, 20, 56), (24, 18, 14): (10, 28, 74),
    (30, 23, 19): (13, 36, 92), (30, 22, 18): (13, 36, 92), (36, 28, 24): (15, 42, 102),
    (43, 33, 28): (16, 47, 115), (42, 33, 28): (16, 47, 115), (59, 46, 40): (26, 74, 150),
    (201, 168, 127): (240, 177, 63), (194, 154, 108): (227, 154, 43),
    (240, 220, 187): (251, 227, 176), (240, 226, 206): (248, 230, 198),
    (120, 90, 50): (154, 100, 16), (120, 86, 50): (154, 100, 16), (138, 90, 43): (154, 100, 16),
    (163, 131, 95): (176, 122, 30),
    (228, 218, 205): (235, 223, 202), (246, 240, 232): (251, 246, 236),
}

# Кнопки. В прежнем виде их три: тёмная, бежевая и светлая «В рассрочку».
# В новом главная кнопка одна — красная, как в тесте 2.0; вторая спокойная.
_BTN_PRIMARY = ("#4A392F", "#4E3C31", "#F0DCBB")
_BTN_QUIET = ("#F7EBD8",)
_BTN_RED = "linear-gradient(135deg, #DA352C 0%, #B3161F 100%)"


def _theme_buttons(html):
    def fix(m):
        tag, style = m.group(0), m.group(2)
        if "border-radius: 999px" not in style or "linear-gradient" not in style:
            return tag
        kind = ("primary" if any(c in style for c in _BTN_PRIMARY)
                else "quiet" if any(c in style for c in _BTN_QUIET) else "")
        if not kind:
            return tag
        if kind == "primary":
            style = re.sub(r"background:\s*linear-gradient\([^;]*", "background: " + _BTN_RED, style, count=1)
            style = re.sub(r"(?<![-\w])color:\s*#[0-9A-Fa-f]{6}", "color: #FFFFFF", style, count=1)
            style = re.sub(r"box-shadow:[^;]*", "box-shadow: 0 16px 30px -14px rgba(190,30,35,.62)", style, count=1)
        else:
            style = re.sub(r"background:\s*linear-gradient\([^;]*", "background: #F4ECDD", style, count=1)
            style = re.sub(r"(?<![-\w])color:\s*#[0-9A-Fa-f]{6}", "color: #18213A", style, count=1)
        return '%sdata-btn="%s" style="%s"' % (m.group(1), kind, style)
    return re.sub(r'(<(?:a|button)\b[^>]*?)style="([^"]*)"', fix, html)


def _theme_colors(text):
    def hx(m):
        return THEME_HEX.get(m.group(0).upper(), m.group(0))
    text = re.sub(r"#[0-9A-Fa-f]{6}\b", hx, text)

    def rgb(m):
        key = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        if key not in THEME_RGB:
            return m.group(0)
        r, g, b = THEME_RGB[key]
        return "%s%d,%d,%d" % (m.group(1), r, g, b)
    return re.sub(r"(rgba?\(\s*)(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", rgb, text)


THEME_CSS = """

/* ─────────────────────────────── тестовое оформление (--theme more) ── */

/* Правила вида. Те же, что у теста 2.0.
   1. Один гротеск. Заголовки берут весом и размером. Антиквы, курсива
      и подписей прописными нет.
   2. Фотография одна, на первом экране. Дальше страницу держат цвет
      и форма блоков.
   3. У цвета есть смысл. Красный: главное действие, метки, отметки.
      Небо: событие, итог, цена, вопрос человека, номера. Закатная
      плашка: главное внутри блока. Голубая: первое, выбранное.
   4. Длинный текст только тёмным по светлому. На небе стоят короткие
      строки.
   5. Скругления по роли: блок 24, карточка и пузырь 18, кнопка 16,
      метки круглые. Линеек и полосок над заголовками нет.
   6. На телефоне текст для чтения 18–20 px, подписи не мельче 14,5 px,
      поля по бокам 20 px, всё нажимаемое не ниже 48 px. */

:root {
  --sky: linear-gradient(150deg, #143A85 0%, #1F56A6 55%, #2A6DB8 100%);
  --panel: linear-gradient(160deg, #FFF3DE 0%, #FCDDC0 100%);
  --spot: linear-gradient(160deg, #EAF2FC 0%, #D9E7F9 100%);
  --zoloto: linear-gradient(135deg, #F7CB62 0%, #EFA533 100%);
  --tochki: repeating-radial-gradient(circle at 100% 0%, rgba(255,255,255,.09) 0 1.5px, rgba(255,255,255,0) 1.5px 30px);
  --ten: 0 1px 2px rgba(24,33,58,.05), 0 10px 26px -16px rgba(24,33,58,.28);
}

@font-face {
  font-family: 'Bebas Neue';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url(/assets/fonts/BebasNeue-Bold.ttf) format('truetype');
}

/* ── первый экран ── */

section[aria-label="Первый экран"] { background: #FBF6EC !important; color: #18213A !important; }
[data-hero-veil] { display: none !important; }

[data-hero-card] {
  display: flex;
  flex-direction: column;
  gap: clamp(20px, 2.2vw, 28px);
  background: #FBF6EC;
  pointer-events: auto;
}
[data-hero-card] > div { max-width: none !important; }
[data-hero-card] > div:last-child { gap: clamp(18px, 2vw, 24px) !important; }

/* Надзаголовок: обычным регистром, синим — это слова Виолы о практикуме. */
[data-hero-stage] [data-hero-card] > div:first-child > div:first-child {
  color: #1F4C97 !important;
  font-size: 16px !important;
  font-weight: 700;
  line-height: 1.4 !important;
}
[data-hero-stage] [data-hero-card] h1 {
  font-family: 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: -.035em !important;
  line-height: 1.04 !important;
  color: #18213A !important;
  text-shadow: none !important;
  max-width: none !important;
  margin: 10px 0 0 !important;
  font-size: clamp(42px, 4.1vw, 60px) !important;
}
@media (min-width: 901px) {
  [data-hero-stage] [data-hero-card] h1 {
    font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
    font-size: clamp(76px, 7.2vw, 118px) !important;
    line-height: .9 !important;
    letter-spacing: .005em !important;
    text-transform: uppercase;
  }
}
[data-hero-stage] [data-hero-card] p { text-shadow: none !important; max-width: none !important; }
[data-hero-stage] [data-hero-card] > div:last-child > p:first-child {
  color: #18213A !important;
  font-size: clamp(21px, 1.9vw, 26px) !important;
  line-height: 1.3 !important;
}
/* Строка про обновлённую программу — закатной плашкой. */
[data-hero-stage] [data-hero-card] > div:last-child > p:nth-child(2) {
  width: auto !important;
  color: #2B3550 !important;
  font-size: 17px !important;
  line-height: 1.5 !important;
  background: var(--panel) !important;
  -webkit-backdrop-filter: none !important;
  backdrop-filter: none !important;
  border-left: 0 !important;
  border-radius: 16px !important;
  padding: 14px 18px !important;
}
/* «Старт 1 ноября» — синей меткой. */
[data-hero-card] > div:last-child > div > div {
  background: #1F4C97 !important;
  border: 0 !important;
  padding: 9px 16px !important;
  -webkit-backdrop-filter: none !important;
  backdrop-filter: none !important;
}
[data-hero-stage] [data-hero-card] > div:last-child > div > div > span:last-child {
  color: #FFFFFF !important;
  font-size: 15.5px !important;
}

/* Широкий экран: фотография во весь кадр, слева карточка с текстом. */
@media (min-width: 901px) {
  [data-hero-stage] [data-hero-copy] { justify-content: center !important; }
  [data-hero-stage] [data-hero-copy] > [data-hero-card] {
    max-width: min(540px, 47vw) !important;
    background: rgba(251,246,236,.97);
    border-radius: 28px;
    padding: clamp(30px, 3.2vw, 48px);
    box-shadow: 0 34px 70px -34px rgba(24,33,58,.55);
  }
}

/* Телефон и узкий планшет. Порядок как на лендингах запусков: плашки
   со стартом и длительностью, крупное название, кнопка, Виола по центру,
   под ней карточка «что это». Виола — отдельный слой без заливки, терраса
   за ней уходит вверх в небо, на котором стоит название. */
[data-h2] { display: none; }
br[data-tel] { display: none; }
@media (max-width: 900px) {
  [data-hero-stage] { display: none !important; }
  [data-h2] {
    display: block;
    position: relative;
    overflow: hidden;
    background: linear-gradient(180deg, #0E2A66 0%, #143A85 28%, #1F56A6 60%, #2A6DB8 100%);
    color: #FFFFFF;
  }
  [data-h2-top] {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 22px 20px 0;
    text-align: center;
  }
  [data-h2-chips] { display: flex; align-items: center; justify-content: center; }
  [data-h2-chips] span {
    display: flex;
    flex-direction: column;
    min-width: 140px;
    padding: 10px 16px 11px;
    border-radius: 14px;
    background: rgba(255,255,255,.12);
    font-size: 15.5px;
    line-height: 1.3;
  }
  [data-h2-chips] i { font-style: normal; color: rgba(255,255,255,.88); }
  [data-h2-chips] b { font-size: 17px; font-weight: 700; }
  [data-h2-chips] em {
    position: relative;
    z-index: 1;
    flex: none;
    width: 10px; height: 10px;
    margin: 0 -5px;
    border-radius: 50%;
    background: #F0B13F;
    box-shadow: 0 0 0 3px #143A85;
  }
  [data-h2-title] {
    margin: 10px 0 0;
    font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-weight: 700;
    font-size: min(calc((100vw - 40px) / (var(--bukv, 10) * .43)), 150px);
    line-height: .9;
    letter-spacing: .005em;
    text-transform: uppercase;
    color: #FFFFFF;
    text-shadow: 0 6px 30px rgba(9,26,68,.45);
  }
  [data-h2-sub] {
    margin: 0;
    max-width: 330px;
    font-size: 17px;
    font-weight: 600;
    line-height: 1.35;
    color: rgba(255,255,255,.95);
    text-wrap: balance;
  }
  [data-h2-top] a[data-btn] { margin-top: 8px; }
  [data-h2-photo] { position: relative; z-index: 1; height: clamp(380px, 106vw, 620px); margin-top: 10px; }
  [data-h2-fon] {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    top: -190px;
    width: 100%;
    height: calc(100% + 190px);
    object-fit: cover;
    object-position: 50% 40%;
    opacity: .78;
    -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 2%, #000 52%);
    mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 2%, #000 52%);
  }
  [data-h2-viola] {
    position: absolute;
    left: 50%; bottom: 0;
    height: 100%;
    width: auto;
    max-width: none;
    transform: translateX(-50%);
  }
  [data-h2-card] {
    position: relative;
    z-index: 3;
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: -88px;
    padding: 30px 22px 36px;
    border-radius: 28px 28px 0 0;
    background: #FBF6EC;
    color: #18213A;
    box-shadow: 0 -18px 40px -22px rgba(9,26,68,.6);
  }
  [data-h2-name] {
    margin: 0;
    font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-weight: 700;
    font-size: min(calc((100vw - 44px) / 5.4), 92px);
    line-height: .94;
    letter-spacing: .005em;
    text-transform: uppercase;
    color: #18213A;
  }
  [data-h2-def] { margin: 0; font-size: 21px; line-height: 1.42; color: #2B3550; }
  [data-h2-def] b { font-weight: 700; color: #18213A; }
  [data-h2-note] {
    margin: 4px 0 0;
    padding: 14px 18px;
    border-radius: 16px;
    background: var(--panel);
    font-size: 17px;
    line-height: 1.5;
    color: #2B3550;
  }
}

/* Анкета предзаписи: метка над названием и список «что даёт предзапись»
   в карточке под фотографией. */
[data-h2-tag] {
  padding: 7px 16px 8px;
  border-radius: 999px;
  background: var(--zoloto);
  color: #18213A;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
}
[data-h2-tag] + [data-h2-title] { margin-top: 0; }
[data-h2-pod] {
  margin: 0;
  max-width: 320px;
  font-size: 15.5px;
  font-weight: 600;
  line-height: 1.4;
  color: rgba(255,255,255,.95);
  text-wrap: balance;
}
[data-hero-stage] [data-hero-card] p[data-hero-pod] { color: #2B3550 !important; font-size: 16.5px !important; font-weight: 600 !important; }
[data-h2-chto] { margin: 12px 0 0; font-size: 23px; font-weight: 700; line-height: 1.2; letter-spacing: -.02em; color: #18213A; }
[data-h2-list] { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }
[data-h2-list] li {
  position: relative;
  padding: 15px 16px 15px 58px;
  border-radius: 18px;
  background: #FFFFFF;
  box-shadow: var(--ten);
  font-size: 19px;
  font-weight: 700;
  line-height: 1.3;
  color: #18213A;
}
[data-h2-list] li::before {
  content: "";
  position: absolute; left: 16px; top: 50%;
  width: 28px; height: 28px; margin-top: -14px; border-radius: 50%;
  background: #D22B2B;
}
[data-h2-list] li::after {
  content: "";
  position: absolute; left: 26.5px; top: 50%;
  width: 6px; height: 12px; margin-top: -8.5px;
  border: solid #FFFFFF; border-width: 0 2.5px 2.5px 0;
  transform: rotate(45deg);
}

/* ── общее ── */

/* Подписи прописными с разрядкой переводятся в обычный регистр. */
main [style*="text-transform: uppercase"] { text-transform: none !important; letter-spacing: 0 !important; font-weight: 700; }
main [style*="font-size: 11px"], main [style*="font-size: 12px"] { font-size: 14px !important; }

/* Метка: персиковая плашка с красным текстом, как в тесте. */
[data-tag],
main [style*="text-transform: uppercase"][style*="color: #B01E22"] {
  display: inline-block;
  width: fit-content;
  background: #FDEBD3;
  color: #B01E22 !important;
  font-size: 14.5px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
  padding: 5px 12px;
  border-radius: 999px;
  white-space: nowrap;
}
[data-tag="siniy"] { background: #1F4C97; color: #FFFFFF !important; border-radius: 10px; }

/* Сетка карточек «Что входит» просила колонки не уже 400 px и на телефоне
   вылезала за край экрана. */
main [style*="minmax(400px, 1fr)"] { grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)) !important; }

/* Скругления по роли. */
main [style*="border-radius: 14px"], main [style*="border-radius: 16px"] { border-radius: 24px !important; }

/* Заголовки блоков: высокий узкий шрифт прописными. Первая строка синяя,
   остальное чернильное; на небе первая строка золотая. */
main h2,
section[aria-label="Зачем мне это"] > div > p:first-child {
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  font-weight: 700 !important;
  font-size: clamp(56px, 6.4vw, 96px) !important;
  line-height: .98 !important;
  letter-spacing: .005em !important;
  text-transform: uppercase;
}
main h2::first-line,
section[aria-label="Зачем мне это"] > div > p:first-child::first-line { color: #1F4C97; }
[data-mk-card] h2::first-line, [data-final-card] h2::first-line { color: #F6CF7A; }

/* В правовых документах заголовки остаются обычными: высокий шрифт
   прописными там мешает читать. */
main.doc h2 {
  font-family: 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  font-size: clamp(21px, 2.4vw, 26px) !important;
  line-height: 1.25 !important;
  letter-spacing: -.015em !important;
  text-transform: none;
}
main.doc h2::first-line { color: inherit; }

/* Номера и цифры — тем же высоким шрифтом, в скруглённых плитках. */
[data-sfery] > div > span:first-child,
[data-week-card] [style*="width: 30px; height: 30px"] {
  width: 38px !important;
  height: 38px !important;
  border-radius: 11px !important;
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 24px !important;
  font-weight: 700 !important;
  line-height: 1;
  padding-top: 2px;
}
[data-week-card] [style*="grid-template-columns: 30px 1fr"] { grid-template-columns: 38px 1fr !important; align-items: center !important; }
[data-cifry] b { font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 64px !important; line-height: .9 !important; letter-spacing: 0 !important; }

/* Главная кнопка: крупный скруглённый прямоугольник с бликом и свечением,
   подпись прописными, без стрелки. Цвет наш, красный; красная одна. */
[data-btn] { border-radius: 18px !important; }
/* Форма как у кнопки на лендинге менторства: высокая, не во всю ширину,
   углы крупно скруглены, по краю светлая кромка, под кнопкой свечение. */
[data-btn="primary"] {
  justify-content: center !important;
  min-height: 80px;
  padding: 18px 46px !important;
  border: 2px solid #F58D82 !important;
  border-radius: 24px !important;
  background:
    radial-gradient(130% 110% at 14% -10%, rgba(255,255,255,.42) 0%, rgba(255,255,255,0) 55%),
    linear-gradient(180deg, #EC5145 0%, #D2302C 48%, #B01920 100%) !important;
  box-shadow: 0 0 44px -6px rgba(232,64,52,.7), 0 18px 36px -16px rgba(150,16,24,.8),
              inset 0 2px 0 rgba(255,255,255,.4) !important;
  font-size: 20px !important;
  font-weight: 700 !important;
  letter-spacing: .02em !important;
  text-transform: uppercase;
}
[data-btn="primary"] > span { display: none !important; }
[data-btn="primary"]:hover { filter: brightness(1.07); }
/* «В рассрочку» — кнопка того же веса, что «Оплатить», только синяя:
   нам всё равно, как человек платит, обе должны быть заметны. */
[data-btn="quiet"] {
  justify-content: center !important;
  min-height: 80px;
  padding: 18px 46px !important;
  border: 2px solid #93BBF3 !important;
  border-radius: 24px !important;
  background:
    radial-gradient(130% 110% at 14% -10%, rgba(255,255,255,.4) 0%, rgba(255,255,255,0) 55%),
    linear-gradient(180deg, #3F86DD 0%, #2563BA 48%, #174592 100%) !important;
  box-shadow: 0 16px 30px -16px rgba(16,47,115,.85), inset 0 2px 0 rgba(255,255,255,.4) !important;
  color: #FFFFFF !important;
  font-size: 20px !important;
  font-weight: 700 !important;
  letter-spacing: .02em !important;
  text-transform: uppercase;
}
[data-btn="quiet"]:hover { filter: brightness(1.07); }
/* В карточке тарифа свечение красной кнопки не ложится на синюю. */
#tarify [data-btn="primary"] { box-shadow: 0 16px 30px -16px rgba(150,16,24,.85), inset 0 2px 0 rgba(255,255,255,.4) !important; }
#tarify [data-btn] { width: 100% !important; }
#tarify [style*="flex-direction: column; gap: 10px"] { gap: 14px !important; }
/* Полосы про повышение цены больше нет. */
#srok { display: none !important; }
[data-btn="support"] { min-height: 56px; padding: 15px 34px !important; font-size: 18px !important; }
[data-btn="support"]:hover { background: #EEF4FD !important; }

/* ── «Эмпатия — это способность» ── */

section[aria-label="Зачем мне это"] [style*="height: 2px"] { display: none !important; }

/* Шесть сфер одним списком. Первая строка голубая: с неё начинаем. */
[data-sfery] {
  gap: 0 !important;
  background: #FFFFFF;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: var(--ten);
}
[data-sfery] > div { border: 0 !important; border-radius: 0 !important; box-shadow: none !important; padding: 15px 18px !important; }
[data-sfery] > div:not(:first-child) { background: none !important; border-top: 1px solid #F4ECDD !important; }
[data-sfery] > div:not(:first-child) > span:first-child { background: #F4ECDD !important; color: #465068 !important; }
[data-sfery] > div > span:nth-child(2) { color: #1F4C97 !important; }
[data-sfery] > div > span:last-child { font-size: 18px !important; font-weight: 600 !important; }

/* «18 техник»: блок-небо. Число крупно золотом, рядом первая фраза,
   под ними пояснение. */
[data-tehniki] {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 16px 18px;
  padding: 24px 22px 26px !important;
  border-radius: 24px !important;
  background: var(--tochki), var(--sky);
  color: #FFFFFF;
  box-shadow: 0 22px 40px -26px rgba(20,58,133,.75) !important;
}
[data-tehniki] > span {
  width: auto !important;
  height: auto !important;
  border-radius: 0 !important;
  background: none !important;
  box-shadow: none !important;
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: clamp(120px, 34vw, 170px) !important;
  font-weight: 700 !important;
  line-height: .78 !important;
  letter-spacing: 0 !important;
  color: #F6CF7A !important;
}
[data-t-lead] { margin: 0; font-size: 24px; font-weight: 700; line-height: 1.2; color: #FFFFFF; text-wrap: balance; }
[data-t-text] { grid-column: 1 / -1; margin: 0; font-size: 18px; line-height: 1.5; color: rgba(255,255,255,.95); }

/* ── «Что нового» ── */

[data-nov] { background: var(--spot) !important; box-shadow: none !important; }
[data-nov] + [data-nov] { background: var(--panel) !important; }
[data-nov] p, [data-plus] p { color: #2B3550 !important; }

/* Короткие пункты: белая строка с красной галочкой. */
[data-plus] {
  position: relative;
  padding: 17px 18px 17px 60px !important;
  border-radius: 18px !important;
  box-shadow: var(--ten) !important;
}
[data-plus]::before {
  content: "";
  position: absolute; left: 18px; top: 18px;
  width: 28px; height: 28px; border-radius: 50%;
  background: #D22B2B;
}
[data-plus]::after {
  content: "";
  position: absolute; left: 28.5px; top: 23.5px;
  width: 6px; height: 12px;
  border: solid #FFFFFF; border-width: 0 2.5px 2.5px 0;
  transform: rotate(45deg);
}

/* Материалы: блок-небо, каждая строка на тёмной подложке с золотым кругом. */
[data-mat] {
  background: var(--tochki), var(--sky) !important;
  box-shadow: none !important;
  flex-direction: column !important;
  flex-wrap: nowrap !important;
  gap: 16px !important;
  color: #FFFFFF;
}
[data-mat] h3 { flex: none !important; color: #FFFFFF; font-size: clamp(22px, 2.2vw, 26px) !important; }
[data-mat] > div { flex: none !important; gap: 8px !important; color: #FFFFFF !important; font-weight: 600; }
[data-mat] > div > div {
  background: rgba(9,26,68,.34);
  border-radius: 16px;
  padding: 12px 14px;
  gap: 12px !important;
  align-items: center !important;
}
[data-mat] > div > div > span:first-child { width: 36px !important; height: 36px !important; margin-top: 0 !important; font-size: 14px !important; }

/* Новый формат ответов на вопросы: золотой блок с маленькой сценкой —
   вопрос человека и аудиоответ Виолы. */
[data-otvety] {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
  padding: 26px 22px 24px;
  border-radius: 24px;
  background: var(--zoloto);
  color: #18213A;
  box-shadow: 0 24px 44px -28px rgba(214,140,30,.85);
}
[data-otvety] > [data-tag] { background: #FFFFFF; font-style: normal; }
[data-o-title] {
  margin: 0;
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: clamp(44px, 5vw, 66px);
  font-weight: 700;
  line-height: .96;
  letter-spacing: .005em;
  text-transform: uppercase;
  color: #18213A;
}
[data-o-title]::first-line { color: #143A85; }
[data-o-text] { margin: 0; font-size: 20px; font-weight: 600; line-height: 1.4; color: #18213A; }
[data-o-scena] { align-self: stretch; display: flex; flex-direction: column; gap: 10px; margin-top: 6px; }
[data-audio] { background: #FFFFFF; }
[data-wave] { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
[data-wave] > span {
  flex: none;
  display: flex; align-items: center; justify-content: center;
  width: 42px; height: 42px; border-radius: 50%;
  background: var(--sky); color: #FFFFFF;
}
[data-wave] > i { flex: 1; min-width: 0; display: flex; align-items: center; gap: 3px; height: 30px; overflow: hidden; }
[data-wave] > i b { flex: none; width: 3px; border-radius: 2px; background: #1F4C97; opacity: .55; }

/* ── программа ── */

/* Цифры программы: четыре плитки, у каждой свой цвет. */
[data-cifry] { display: grid !important; grid-template-columns: repeat(2, minmax(0, 240px)); gap: 10px !important; }
[data-cifry] > span {
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: normal !important;
  border-radius: 20px;
  padding: 16px 16px 15px;
  font-size: 16.5px;
  font-weight: 600;
  line-height: 1.25;
}
[data-cifry] b { font-size: 42px !important; line-height: 1; letter-spacing: -.03em; }
[data-cifry] > span:nth-child(1) { background: var(--sky); color: #FFFFFF; }
[data-cifry] > span:nth-child(1) b { color: #FFFFFF !important; }
[data-cifry] > span:nth-child(2) { background: var(--panel); color: #2B3550; }
[data-cifry] > span:nth-child(2) b { color: #B01E22 !important; }
[data-cifry] > span:nth-child(3) { background: #FFFFFF; color: #2B3550; box-shadow: var(--ten); }
[data-cifry] > span:nth-child(3) b { color: #1F4C97 !important; }
[data-cifry] > span:nth-child(4) { background: var(--zoloto); color: #3A2A05; }
[data-cifry] > span:nth-child(4) b { color: #143A85 !important; }

/* «Каждую неделю вы получаете»: главный блок программы. Шапка-небо
   с крупным заголовком, пять строк со значками, золотая строка про доступ. */
[data-nedelya] {
  border-radius: 24px;
  overflow: hidden;
  background: #FFFFFF;
  box-shadow: 0 28px 54px -30px rgba(20,58,133,.6), 0 0 0 2px #1F4C97;
}
[data-n-title] {
  margin: 0;
  padding: 24px 22px 20px;
  background: var(--tochki), var(--sky);
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: clamp(46px, 5vw, 64px);
  font-weight: 700;
  line-height: .96;
  letter-spacing: .005em;
  text-transform: uppercase;
  color: #F6CF7A;
}
[data-n-title]::first-line { color: #FFFFFF; }
[data-nedelya] ul { margin: 0; padding: 6px 22px; list-style: none; }
[data-nedelya] li {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  column-gap: 14px;
  align-items: center;
  padding: 14px 0;
  font-size: 19px;
  line-height: 1.3;
  color: #18213A;
}
[data-nedelya] li + li { border-top: 1px solid #F1E8D8; }
[data-nedelya] li > span {
  display: flex; align-items: center; justify-content: center;
  width: 48px; height: 48px;
  border-radius: 14px;
  background: var(--sky);
  color: #FFFFFF;
}
[data-nedelya] li b { font-weight: 700; }
[data-nedelya] li > div { display: flex; flex-direction: column; align-items: flex-start; gap: 7px; }
[data-n-viola] > span { background: linear-gradient(135deg, #E5483D 0%, #B3161F 100%) !important; }
[data-nedelya] em { font-style: normal; }
[data-n-foot] {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  padding: 16px 22px 17px;
  background: var(--zoloto);
  font-size: 18.5px;
  font-weight: 700;
  line-height: 1.3;
  color: #18213A;
}
[data-n-foot] span { font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 40px; line-height: .7; color: #143A85; }

/* Карточка недели: вопрос человека справа на небе, ответ Виолы сообщением,
   три техники с синими номерами. */
[data-week-card] { background: #FFFFFF !important; border: 0 !important; box-shadow: var(--ten) !important; }
[data-week-head] { padding: clamp(22px, 3vw, 34px) clamp(20px, 3vw, 34px) 0; }
[data-week-head] + div { padding: 18px clamp(20px, 3vw, 34px) clamp(22px, 3vw, 34px) !important; }
[data-week-head] h3 { font-size: clamp(23px, 2.4vw, 28px) !important; }
[data-vopros] {
  align-self: flex-end;
  max-width: 94%;
  margin: 2px 0 0;
  background: var(--sky);
  color: #FFFFFF;
  font-size: 19px;
  line-height: 1.28;
  font-weight: 700;
  letter-spacing: -.01em;
  padding: 12px 16px 13px;
  border-radius: 18px 18px 6px 18px;
  box-shadow: 0 10px 18px -12px rgba(31,76,151,.8);
}
[data-msg] { display: grid; grid-template-columns: 34px minmax(0, 1fr); column-gap: 8px; align-items: end; }
[data-ava] {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--sky); color: #FFFFFF;
  font-size: 16px; font-weight: 700; line-height: 1;
}
[data-bubble] { background: #F4ECDD; border-radius: 18px 18px 18px 6px; padding: 12px 16px 14px; }
[data-who] { display: block; margin-bottom: 3px; font-size: 15.5px; font-weight: 700; color: #1F4C97; }
[data-bubble] p { margin: 0; font-size: 18px; line-height: 1.5; color: #18213A; }
@media (min-width: 861px) {
  [data-week-head] { padding-bottom: clamp(22px, 3vw, 34px); }
  [data-week-head] + div { padding-top: clamp(22px, 3vw, 34px) !important; }
}

/* ── мастер-класс ── */

/* Блок-небо на светлом фоне. Кнопки нет: такая же стоит экраном выше,
   сразу за блоком идут тарифы. */
[data-mk] { background: #F7F0E2 !important; padding-top: 0 !important; padding-bottom: clamp(8px, 2vw, 24px) !important; }
[data-mk] a[data-btn] { display: none !important; }
[data-mk-card] {
  background: var(--tochki), var(--sky);
  border-radius: 24px;
  padding: clamp(26px, 3.4vw, 44px) clamp(22px, 3.4vw, 44px);
  color: #FFFFFF;
}
[data-mk-card] > div:first-child {
  background: linear-gradient(135deg, #DA352C 0%, #B3161F 100%) !important;
  border: 0 !important;
  padding: 6px 14px !important;
}
[data-mk-card] > div:first-child > span:first-child { display: none; }

/* ── тарифы ── */

#tarify [style*="top: -14px"] {
  background: linear-gradient(135deg, #DA352C 0%, #B3161F 100%) !important;
  color: #FFFFFF !important;
  font-size: 14.5px !important;
  padding: 6px 16px !important;
  box-shadow: 0 8px 16px -8px rgba(190,30,35,.6) !important;
}
/* Галочка: красная в персиковом круге. Чего нет в тарифе — серым. */
#tarify [style*="grid-template-columns: 22px 1fr"] { grid-template-columns: 26px 1fr !important; }
#tarify span[style*="color: #1F4C97"] {
  width: 26px; height: 26px; border-radius: 50%;
  align-items: center; justify-content: center;
  margin-top: 0 !important;
  background: #FDEBD3;
  color: #B01E22 !important;
}
#tarify span[style*="display: inline-flex"][style*="color: #B01E22"] { color: #9AA3B5 !important; }
#tarify [style*="line-through"] { text-decoration-color: #9AA3B5 !important; }
/* Золотая линейка между списками — тонкой серой чертой. */
#tarify [style*="height: 1px"] { background: #F1E8D8 !important; }
#kontakty > div { border: 0 !important; box-shadow: var(--ten) !important; }
/* Цена на блоке-небе. */
[data-cena] { background: var(--sky); border-radius: 18px; padding: 18px 20px; }
[data-mest] { background: #FDEBD3 !important; box-shadow: none !important; padding: 7px 14px !important; }
[data-mest] > span:first-child { background: #D22B2B !important; box-shadow: none !important; }
[data-mest] > span:last-child { color: #B01E22 !important; font-size: 15.5px !important; }

/* ── подарки ── */

/* Каждый подарок — отдельная карточка с золотым кругом, как посты в тесте. */
[data-podarki] { background: none !important; padding: 0 !important; border-radius: 0 !important; gap: 14px !important; }
[data-podarki] > div:last-of-type { gap: 10px !important; }
[data-podarok] {
  background: #FFFFFF;
  border-radius: 18px;
  padding: 16px;
  box-shadow: var(--ten);
  grid-template-columns: 50px 1fr !important;
}
[data-podarok] > span {
  width: 50px !important; height: 50px !important;
  margin-top: 0 !important;
  box-shadow: 0 8px 16px -8px rgba(214,140,30,.85);
}
[data-podarok] > span svg { width: 22px; height: 22px; }
/* Страница заявки. Колонка «За саму заявку» — голубая плашка: это первое,
   что человек получает. Строки внутри белые, как подарки рядом. */
[data-za-zayavku] { background: var(--spot) !important; border: 0 !important; box-shadow: none !important; }
[data-za-zayavku] [data-podarok] > span { font-size: 19px !important; }
/* Подписи кнопок тарифа у заявки длиннее («Хочу в рассрочку»): шрифт
   чуть меньше, чтобы подпись не ломалась на две строки. */
[data-mode="zayavka"] #tarify [data-btn] {
  padding-left: 12px !important;
  padding-right: 12px !important;
  font-size: clamp(16.5px, 4.7vw, 20px) !important;
  white-space: nowrap;
}

/* ── последний призыв ── */

/* Блок-небо с красной кнопкой, как второй призыв в тесте. */
[data-final] { background: #FBF6EC !important; padding: clamp(24px, 5vw, 64px) clamp(14px, 4vw, 40px) clamp(44px, 6vw, 84px) !important; }
[data-final-card] {
  background: var(--tochki), var(--sky);
  border-radius: 24px;
  padding: clamp(32px, 4.4vw, 56px) clamp(22px, 4.4vw, 56px);
  max-width: 760px !important;
}
[data-final-card] > div:first-child { background: rgba(9,26,68,.34) !important; border: 0 !important; }
[data-final-card] h2 { font-size: clamp(54px, 5.4vw, 80px) !important; }
[data-final-card] [style*="color: #9AA3B5"] { color: #DCE4F0 !important; }
[data-final-card] p b { color: #FFFFFF; font-weight: 700; }

/* ── окно заявки ── */

#lead-modal h2 {
  font-family: 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  font-size: clamp(25px, 3.2vw, 34px) !important;
  line-height: 1.14 !important;
  letter-spacing: -.025em !important;
  text-transform: none;
}
#lead-modal h2::first-line { color: inherit; }
#lead-modal [data-close-form] { min-height: 46px; }
/* Кнопка формы во всю ширину карточки: боковые поля меньше, чтобы
   «Отправить заявку» и «Перейти к оплате» стояли в одну строку. */
#lead-modal #form-submit {
  padding-left: 12px !important;
  padding-right: 12px !important;
  font-size: clamp(16.5px, 4.8vw, 20px) !important;
  white-space: nowrap;
}
#lead-modal > div { -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
/* Подписи полей — обычным жирным текстом, не плашками. */
#lead-modal label [style*="text-transform: uppercase"] {
  display: block;
  width: auto;
  background: none;
  padding: 0;
  border-radius: 0;
  white-space: normal;
  color: #18213A !important;
  font-size: 16px !important;
}
#lead-modal label span span[style*="text-transform: uppercase"] { color: #5F687E !important; font-size: 14.5px !important; font-weight: 600 !important; }

/* Выбор способа оплаты: две плашки одного веса. Российская карта —
   закатная с красной кнопкой, зарубежная — голубая с синей. Сумма крупно,
   тем же высоким шрифтом, что и цифры на странице. */
[data-pay-option] { border: 0 !important; padding: 18px 18px 20px !important; gap: 14px !important; }
[data-pay-option="ru"] { background: var(--panel) !important; }
[data-pay-option="intl"] { background: var(--spot) !important; }
[data-pay-option] > div > span:first-child { color: #2B3550 !important; font-size: 16.5px !important; }
[data-pay-price] {
  font-family: 'Bebas Neue', 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 54px !important;
  line-height: .95 !important;
  letter-spacing: .005em !important;
}
[data-pay-price] i {
  font-family: 'Golos Text', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 19px;
  font-style: normal;
  font-weight: 600;
  letter-spacing: 0;
  vertical-align: .32em;
}
[data-pay-option] p { color: #2B3550 !important; font-size: 16.5px !important; }
#pay-step [data-btn] {
  width: 100% !important;
  min-height: 68px;
  padding: 14px 10px !important;
  font-size: clamp(16px, 4.6vw, 19px) !important;
  white-space: nowrap;
}
#pay-step [data-btn="primary"] { box-shadow: 0 16px 30px -16px rgba(150,16,24,.85), inset 0 2px 0 rgba(255,255,255,.4) !important; }
#pay-title:focus { outline: none; }

/* Подписи к платежу на странице внутренней рассрочки: стоят на небе. */
[data-cena] [data-cena-note] { color: #EEF3FB !important; font-size: 15.5px !important; }
[data-cena] [data-cena-note] b { color: #FFFFFF; }

/* ── подвал ── */

.ft-label { text-transform: none; letter-spacing: 0; font-size: 14.5px; font-weight: 700; }

/* ── полоса про cookie ── */

.cookie-bar {
  background: #FFFFFF;
  border: 1px solid #E2D3B6;
  color: #18213A;
  box-shadow: 0 18px 44px -18px rgba(24,33,58,.45);
}
.cookie-bar a { color: #143A85; }
.cookie-bar button { background: #18213A; color: #FFFFFF; border-radius: 14px; }

/* ── телефон ── */

@media (max-width: 760px) {
  /* Поля по бокам 20 px: текст не упирается в край экрана. */
  main > section:not([aria-label="Первый экран"]) { padding-left: 20px !important; padding-right: 20px !important; }

  main h2 { font-size: 54px !important; }
  /* «Это способность.» — самая длинная строка, она не должна рваться. */
  section[aria-label="Зачем мне это"] > div > p:first-child { font-size: min(54px, calc((100vw - 40px) / 5.95)) !important; }
  br[data-tel] { display: inline; }
  /* Кнопка не во всю ширину: около трёх четвертей экрана, по центру. */
  [data-btn="primary"] { width: min(100%, 320px); margin-left: auto; margin-right: auto; align-self: center !important; }

  /* Вводные абзацы были 17 px при тексте карточек 20 px. */
  main [style*="font-size: clamp(17.1px"] { font-size: 19px !important; }
  main [style*="font-size: clamp(18.9px"] { font-size: 21px !important; }
  main [style*="font-size: clamp(20.7px"] { font-size: 22.5px !important; }
  main [style*="font-size: 13px"] { font-size: 14.5px !important; }

  /* Сетка из шести значков повторяла список сфер выше и карточки ниже. */
  [data-week-rail] { display: none !important; }

  [data-cifry] { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  [data-final-card] { text-align: center; }

  /* Ссылкам на аккаунт команды и «Подробнее» — зона под палец. */
  main p > a[href^="https://t.me"] { display: inline-block; padding: 11px 6px; margin: -11px -6px; }
  .cookie-bar a { padding: 12px 0; }

  /* Пока полоса про cookie на экране, нижняя полоса с ценой скрыта:
     две полосы подряд закрывали треть первого экрана. */
  .cookie-bar { left: 10px; right: 10px; bottom: 10px; padding: 14px 16px; gap: 12px; font-size: 14.5px; line-height: 1.45; }
  .cookie-bar p { flex: 1 1 100%; }
  .cookie-bar button { width: 100%; min-height: 48px; }
  body:has(.cookie-bar:not([hidden])) [data-sticky-bar] { display: none !important; }

  [data-sticky-bar] { box-shadow: 0 -10px 30px -18px rgba(24,33,58,.4); }
  [data-sticky-bar] a {
    width: auto;
    margin: 0;
    border-width: 1px !important;
    min-height: 50px;
    display: inline-flex !important;
    align-items: center;
    padding: 12px 20px !important;
    border-radius: 14px !important;
    font-size: 15px !important;
    letter-spacing: .02em !important;
    box-shadow: 0 10px 22px -10px rgba(214,44,44,.7), inset 0 1px 0 rgba(255,255,255,.35) !important;
  }
}
"""


def _theme_section(html, label, pairs):
    """Замены внутри одного блока страницы. Блок ищется по aria-label;
    если его на странице нет (правовые страницы), ничего не происходит."""
    i = html.find('aria-label="%s"' % label)
    if i < 0:
        return html
    blk = find_block(html, "section", html.rfind("<section", 0, i))
    sec = html[blk[0]:blk[3]]
    for old, new in pairs:
        if old not in sec:
            print("  тема: в блоке «%s» не найдено: %s" % (label, old[:70]))
        sec = sec.replace(old, new)
    return html[:blk[0]] + sec + html[blk[3]:]


# Цветные блоки теста 2.0. Сами градиенты заданы переменными в начале
# THEME_CSS, в разметку подставляется только имя.
_PANEL = "var(--panel)"      # закатная плашка: главное внутри блока
_SPOT = "var(--spot)"        # светло-голубая: первое, выбранное
_SKY = "var(--sky)"          # небо: событие, итог, цена
_GOLD = "var(--zoloto)"      # золотой кружок под значок
_RED = "#B01E22"             # красный текст: метки, отметки, ссылки
_BLUE = "#1F4C97"            # синий: номера, недели, всё, что говорит Виола


def _ikonka(paths):
    return ('<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % paths)


_THEME_NEDELYA = (
    '<div data-nedelya="">'
    '<p data-n-title="">Каждую неделю <br>вы&nbsp;получаете:</p>'
    '<ul>'
    '<li><span>' + _ikonka('<path d="M8.5 5.5v13l10-6.5z" fill="currentColor" stroke="none"/>')
    + '</span><b>лекцию Виолы в&nbsp;записи с&nbsp;таймкодами</b></li>'
    '<li><span>' + _ikonka('<path d="M5 7h14M5 12h14M5 17h14"/>')
    + '</span><b>три прикладных техники недели для&nbsp;эмпатов</b></li>'
    '<li><span>' + _ikonka('<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8.4 12.3l2.6 2.6 4.7-5.5"/>')
    + '</span><b>практические задания</b></li>'
    '<li><span>' + _ikonka('<path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10A.5.5 0 0 1 7 20z"/><path d="M14 3.5V8h4M9.5 13h5M9.5 16.5h5"/>')
    + '</span><b>PDF-конспект к&nbsp;лекции</b></li>'
    '<li data-n-viola=""><span>' + _ikonka('<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M6 11.5a6 6 0 0 0 12 0M12 17.5V21"/>')
    + '</span><div><b>аудиоответы от&nbsp;Виолы в&nbsp;чате</b>'
    '<em data-tag="">Только на&nbsp;тарифе «С&nbsp;Виолой»</em></div></li>'
    '</ul>'
    '<p data-n-foot=""><span aria-hidden="true">∞</span>Доступ ко&nbsp;всему остаётся навсегда.</p>'
    '</div>')


# Новый формат ответов на вопросы. Слова заданы здесь: блок есть только
# в тестовом оформлении. Сценка с вопросом и аудиоответом — украшение,
# читалкам экрана она не озвучивается.
_THEME_OTVETY = (
    '<div data-otvety="">'
    '<em data-tag="">Только на&nbsp;тарифе «С&nbsp;Виолой»</em>'
    '<h3 data-o-title="">Формат ответов на&nbsp;вопросы <br>пересобран полностью</h3>'
    '<p data-o-text="">Чтобы каждый получил ответ на&nbsp;свой вопрос от&nbsp;Виолы в&nbsp;формате аудио.</p>'
    '<div data-o-scena="" aria-hidden="true">'
    '<p data-vopros="">«Почему мной пользуются?»</p>'
    '<div data-msg=""><span data-ava="">В</span><div data-bubble="" data-audio="">'
    '<b data-who="">Виола Маро</b><div data-wave=""><span>'
    + _ikonka('<path d="M9 6v12l9.5-6z" fill="currentColor" stroke="none"/>') + '</span><i>'
    + "".join('<b style="height: %dpx"></b>' % h for h in
              (8, 14, 22, 12, 18, 26, 16, 10, 20, 28, 14, 8, 18, 24, 12, 20, 10, 16, 26, 14, 8, 12, 22, 16, 10, 18, 12, 8))
    + '</i></div></div></div>'
    '</div></div>')


def _theme_section_re(html, label, pattern, repl, flags=0):
    """То же, что _theme_section, но заменой по регулярному выражению."""
    i = html.find('aria-label="%s"' % label)
    if i < 0:
        return html
    blk = find_block(html, "section", html.rfind("<section", 0, i))
    sec, n = re.subn(pattern, repl, html[blk[0]:blk[3]], flags=flags)
    if not n:
        print("  тема: в блоке «%s» не найдено: %s" % (label, pattern[:70]))
    return html[:blk[0]] + sec + html[blk[3]:]


def _theme_hero_phone(html):
    """Первый экран для телефона. Порядок как на лендингах запусков:
    плашки со стартом и длительностью, крупное название, кнопка, эксперт
    по центру, под ним карточка «что это». Слова берутся из той же
    разметки, что и у широкого экрана; широкий экран остаётся прежним."""
    i = html.find('aria-label="Первый экран"')
    k = html.find('<div data-hero-stage=""')
    if i < 0 or k < 0:
        return html
    blk = find_block(html, "section", html.rfind("<section", 0, i))
    sec = html[blk[0]:blk[3]]

    def grab(pattern):
        m = re.search(pattern, sec, re.S)
        return m.group(1).strip() if m else ""
    eyebrow = grab(r'text-transform: uppercase; color: #F0B13F; line-height: 1\.5;">(.*?)</div>')
    title = grab(r"<h1[^>]*>(.*?)</h1>")
    promise = grab(r"text-shadow: 0 2px 22px[^>]*>(.*?)</p>")
    note = grab(r"border-left: 2px solid #F0B13F;[^>]*>(.*?)</p>")
    start = grab(r">Старт(?:\s|&nbsp;|\u00a0)+([^<]+)</span>")
    cta = re.search(r'<a [^>]*data-btn="primary"[^>]*>.*?</a>', sec, re.S)
    if not (title and promise and cta):
        print("  тема: первый экран для телефона не собран, не найдены его части")
        return html
    # На странице предзаписи надзаголовок начинается с плашки «Анкета
    # предзаписи»: на телефоне она встаёт меткой над названием.
    tag = ""
    pill = re.match(r"\s*<b[^>]*>([^<]+)</b>\s*<span>(.*?)</span>\s*$", eyebrow, re.S)
    if pill:
        tag = pill.group(1).strip()
        eyebrow = re.sub(r"^на(?:\s|&nbsp;|\u00a0)+", "", pill.group(2).strip())
    weeks = re.search(r"(\d+)-недельн", eyebrow)
    name = re.sub(r"\s*<br\s*/?>\s*", " ", title)
    # Размер названия считается от самого длинного слова: «Прикладная» —
    # десять букв, «Прикладную» на странице брони с кавычкой — одиннадцать.
    words = re.sub(r"<[^>]+>", " ", title).replace("&nbsp;", " ").replace("\u00a0", " ").split()
    longest = max([len(w) for w in words] + [10])
    # На странице брони заголовок говорит про бронь, а карточка ниже
    # по-прежнему объясняет, что такое сам практикум.
    quoted = re.search(r"«([^»]+)»", name)
    if quoted:
        name = "Прикладная эмпатия 2.0"
    chips = ""
    if start:
        chips = '<span><i>Старт:</i><b>%s</b></span>' % start
        if weeks:
            chips += '<em aria-hidden="true"></em><span><i>Длительность:</i><b>%s&nbsp;недель</b></span>' % weeks.group(1)
        chips = '<div data-h2-chips="">%s</div>' % chips
    # Карточка под фотографией — оффер практикума, на всех страницах.
    card = ('<p data-h2-name="">%s&nbsp;—</p>' % name
            + '<p data-h2-def="">это практикум, на&nbsp;котором вы <b>%s</b></p>'
              % (promise[:1].lower() + promise[1:])
            + ('<p data-h2-note="">%s</p>' % note if note else ""))
    # У анкеты предзаписи ниже оффера стоит ответ на вопрос «что я получу»:
    # три пункта из блока «Что даёт предзапись».
    if MODE == "predzapis":
        card += ('<p data-h2-chto="">Что даёт предзапись?</p>'
                 '<ul data-h2-list="">'
                 + "".join("<li>%s</li>" % t for t, _tail in PRE_BONUSES + PRE_FOR_REQUEST)
                 + "</ul>")
    pod = grab(r'<p data-hero-pod=""[^>]*>(.*?)</p>')
    block = (
        '<div data-h2="">'
        '<div data-h2-top="">' + chips
        + ('<span data-h2-tag="">%s</span>' % tag if tag else "")
        + '<p data-h2-title="" role="heading" aria-level="1" style="--bukv: %d;">%s</p>' % (longest, title)
        + ('<p data-h2-sub="">%s</p>' % eyebrow if eyebrow else "")
        + cta.group(0)
        # Под кнопкой анкеты сразу сказано, что будет после неё.
        + ('<p data-h2-pod="">%s</p>' % pod if pod else "")
        + '</div>'
        '<div data-h2-photo="">'
        '<img data-h2-fon="" src="/assets/img/terrasa.jpg" alt="" width="900" height="1000" decoding="async">'
        '<img data-h2-viola="" src="/assets/img/viola.webp" alt="Виола Маро" width="901" height="1202" '
        'fetchpriority="high" decoding="async">'
        '</div>'
        '<div data-h2-card="">' + card + '</div></div>')
    # Кадр широкого экрана на телефоне скрыт; чтобы он там не скачивался,
    # картинка грузится лениво.
    sec = sec.replace('fetchpriority="high" decoding="async">', 'loading="lazy" decoding="async">', 1)
    k = sec.find('<div data-hero-stage=""')
    sec = sec[:k] + block + sec[k:]
    return html[:blk[0]] + sec + html[blk[3]:]


def _theme_layout(html):
    """Перестройка блоков в язык теста 2.0. Работает по уже перекрашенной
    разметке, поэтому цвета в образцах здесь новые."""
    # Первый экран: надзаголовок, заголовок и нижний текст собираются в одну
    # карточку. На телефоне она становится листом под фотографией.
    html = _theme_hero_phone(html)
    i = html.find('data-hero-copy=""')
    if i >= 0:
        blk = find_block(html, "div", html.rfind("<div", 0, i))
        html = (html[:blk[1]] + '<div data-hero-card="">' + html[blk[1]:blk[2]]
                + "</div>" + html[blk[2]:])

    html = _theme_section(html, "Зачем мне это", [
        # Шесть сфер: были шестью плашками с тенью и выглядели кнопками,
        # хотя не нажимаются. Теперь один список; первая строка подсвечена,
        # с неё практикум начинается.
        ("background: linear-gradient(160deg, #1F56A6, #143A85); border: 1px solid #143A85; "
         "box-shadow: 0 8px 20px -12px rgba(16,47,115,.6), inset 0 1px 0 rgba(255,255,255,.1); "
         "border-radius: 999px; padding: 13px 22px; color: #FBF6EC;",
         "background: " + _SPOT + "; border: 0; box-shadow: none; "
         "border-radius: 999px; padding: 13px 22px; color: #18213A;"),
        ("background: rgba(251,246,236,.14); color: #FBF6EC;", "background: " + _BLUE + "; color: #FFFFFF;"),
        ('<span style="display: inline-flex; color: #F0B13F;">', '<span style="display: inline-flex; color: ' + _BLUE + ';">'),
        ("padding: 13px 22px; color: #1A4A96;", "padding: 13px 22px; color: #18213A;"),
        ('<div style="display: flex; flex-direction: column; gap: 8px;">',
         '<div data-sfery="" style="display: flex; flex-direction: column; gap: 8px;">'),
        # «18 техник»: блок-небо с крупным числом и сеткой 6 × 3
        ('<div style="display: flex; gap: 18px; align-items: flex-start; '
         'background: linear-gradient(165deg, #1F56A6 0%, #102F73 100%); border: 1px solid #143A85;',
         '<div data-tehniki="" style="border: 0;'),
        # на телефоне «это» уходит на вторую строку и не висит в конце первой
        ("Эмпатия&nbsp;— это способность.", 'Эмпатия&nbsp;— <br data-tel="">это способность.'),
        ("box-shadow: 0 18px 40px -22px rgba(16,47,115,.7), inset 0 1px 0 rgba(255,255,255,.1);", "box-shadow: none;"),
        ("background: linear-gradient(180deg, #FBE3B0, #E39A2B); color: #18213A; font-size: 21px;",
         "background: " + _SKY + "; color: #FFFFFF; font-size: 21px;"),
        ('line-height: 1.55; color: #D9CDB6;"><b style="color: #FBF6EC;">',
         'line-height: 1.55; color: #2B3550;"><b style="color: #18213A;">'),
    ])

    # «18 техник»: первая фраза стоит рядом с числом, пояснение под ними.
    html = _theme_section_re(
        html, "Зачем мне это",
        r'(<div data-tehniki=""[^>]*>\s*<span[^>]*>.*?</span>)\s*<p[^>]*><b[^>]*>(.*?)</b>\s*(.*?)</p>',
        r'\1<p data-t-lead="">\2</p><p data-t-text="">\3</p>', re.S)

    html = _theme_section(html, "Что нового", [
        # заголовок вопросом
        ("с&nbsp;прошлыми потоками</h2>", "с&nbsp;прошлыми потоками?</h2>"),
        ("background: radial-gradient(90% 60% at 88% 0%, rgba(240,177,63,.2) 0%, rgba(240,177,63,0) 58%), "
         "linear-gradient(165deg, #1F56A6 0%, #18213A 48%, #0F2A66 100%);",
         "background: linear-gradient(180deg, #FFFFFF 0%, #FBF6EC 100%);"),
        ("color: #FBF6EC", "color: #18213A"),
        ("color: #D9CDB6", "color: #465068"),
        # две большие карточки: голубая и закатная, без золотой полоски сверху
        ('<div style="background: linear-gradient(180deg, rgba(251,246,236,.09) 0%, rgba(251,246,236,.04) 100%); '
         'border: 1px solid rgba(251,246,236,.16); border-top: 3px solid #F0B13F;',
         '<div data-nov="" style="border: 0;'),
        # три короткие: белые строки с красной галочкой
        ('style="background: linear-gradient(180deg, rgba(251,246,236,.08) 0%, rgba(251,246,236,.03) 100%); '
         'border: 1px solid rgba(251,246,236,.14);', 'data-plus="" style="background: #FFFFFF; border: 0;'),
        # материалы: блок-небо со строками, как итог в тесте
        ('<div style="background: linear-gradient(135deg, rgba(240,177,63,.2) 0%, rgba(240,177,63,.08) 100%); '
         'border: 1px solid rgba(240,177,63,.34);', '<div data-mat="" style="background: ' + _SKY + '; border: 0;'),
        ("background: linear-gradient(160deg, #FBE3B0, #E39A2B); color: #18213A; font-size: 12px;",
         "background: " + _GOLD + "; color: #143A85; font-size: 12px;"),
    ])

    # Вводная строка повторяла карточку «Программа собрана заново», а хвост
    # карточки про 18 техник — блок, который стоит экраном выше.
    html = _theme_section_re(
        html, "Что нового", r"\s*<p[^>]*>Практикум пересобран полностью\.[^<]*</p>", "")
    html = _theme_section_re(
        html, "Что нового",
        r"(целиком на(?:&nbsp;|\s)практике): 18(?:&nbsp;|\s)техник, по(?:&nbsp;|\s)три на(?:&nbsp;|\s)каждую неделю\.", r"\1.")

    # Карточка «Ваш вопрос разберут каждую неделю» повторяла блок про новый
    # формат ответов, который стоит ниже. В тестовом оформлении её нет.
    i = html.find('<div data-nov=""')
    j = html.find('<div data-nov=""', i + 10) if i >= 0 else -1
    if j >= 0:
        blk = find_block(html, "div", j)
        html = html[:blk[0]] + html[blk[3]:]

    html = _theme_section(html, "Программа шесть недель", [
        ('<div style="display: flex; flex-wrap: wrap; gap: 12px 26px; font-size: 17px; color: #465068;">',
         '<div data-cifry="" style="display: flex; flex-wrap: wrap; gap: 12px 26px; font-size: 17px; color: #465068;">'),
        # карточка недели: шапка без заливки, значок в золотом круге
        ('<div style="background: linear-gradient(165deg, #1F56A6 0%, #143A85 100%); padding: clamp(24px, 3vw, 34px); '
         'display: flex; flex-direction: column; gap: 14px; color: #FBF6EC;">',
         '<div data-week-head="" style="display: flex; flex-direction: column; gap: 14px; color: #18213A;">'),
        ("background: linear-gradient(180deg, #FBE3B0, #E39A2B); color: #18213A; flex: none;",
         "background: " + _GOLD + "; color: #143A85; flex: none;"),
        ('<span style="font-size: 13px; font-weight: 700; letter-spacing: .14em; color: #F6CF7A; white-space: nowrap;">НЕДЕЛЯ\u00a0',
         '<span data-tag="siniy">Неделя\u00a0'),
        # вопрос недели — сообщением справа, как вопрос человека в тесте
        ('<p style="margin: 0; font-size: 17px; line-height: 1.45; color: #B9C2D3; font-style: italic;">', '<p data-vopros="">'),
        ('<span style="background: linear-gradient(160deg, #1F56A6, #102F73); color: #FBF6EC; border-radius: 999px; '
         'box-shadow: 0 8px 18px -10px rgba(16,47,115,.6); padding: 6px 14px; font-size: 14px; font-weight: 700; '
         'letter-spacing: .04em; white-space: nowrap;">3 ТЕХНИКИ</span>', '<span data-tag="">3 техники</span>'),
        ('<span style="flex: 1; height: 1px; background: #EBDFCA;"></span>', ""),
        (">НЕД.\u00a0", ">Нед.\u00a0"),
        # номера техник — синие круги, как номера шагов в тесте
        ("width: 30px; height: 30px; border-radius: 9px; background: linear-gradient(160deg, #FBF6EC, #EBDFCA); "
         "color: " + _RED + ";", "width: 30px; height: 30px; border-radius: 50%; background: " + _BLUE + "; color: #FFFFFF;"),
    ])
    # «Каждую неделю вы получаете» — главный блок программы, поэтому крупно:
    # шапка-небо, пять строк со значками, внизу золотая строка про доступ.
    # Слова заданы здесь: список на тестовой странице новее, чем в шаблоне.
    html = _theme_section_re(
        html, "Программа шесть недель",
        r'<div style="background: linear-gradient\(160deg, #F4ECDD, #EBDFCA\); border-radius: 10px;[^>]*>\s*Каждую неделю.*?</div>',
        lambda m: _THEME_NEDELYA, re.S)

    # текст лекции — ответом Виолы: имя и пузырь, как её слова в тесте
    html = _theme_section_re(
        html, "Программа шесть недель",
        r'<p style="margin: 0; font-size: 18\.5px; line-height: 1\.5; font-weight: 500;">(.*?)</p>',
        r'<div data-msg=""><span data-ava="" aria-hidden="true">В</span><div data-bubble="">'
        r'<b data-who="">Виола Маро</b><p>\1</p></div></div>', re.S)
    # В плитке подпись должна переноситься: неразрывный пробел в «разборов
    # вопросов» выталкивал её за край на экране 360 px.
    i = html.find('<div data-cifry=""')
    if i >= 0:
        blk = find_block(html, "div", i)
        cifry = html[blk[0]:blk[3]].replace("\u00a0", " ").replace("&nbsp;", " ")
        # Разборов вопросов после лекций больше нет, а про доступ навсегда
        # сказано ниже, в блоке «Каждую неделю вы получаете».
        cifry = re.sub(r"\s*<span[^>]*><b[^>]*>(?:7|∞)</b>[^<]*</span>", "", cifry)
        html = html[:blk[0]] + cifry + html[blk[3]:]

    # Мастер-класс: блок-небо на светлом фоне, без кнопки (она экраном выше).
    html = _theme_section(html, "Финальный мастер-класс", [
        ('aria-label="Финальный мастер-класс"', 'data-mk="" aria-label="Финальный мастер-класс"'),
        ('<div style="max-width: 860px; margin: 0 auto;', '<div data-mk-card="" style="max-width: 860px; margin: 0 auto;'),
        ("Большой мастер-класс в&nbsp;финале",
         'Большой <span style="white-space: nowrap;">мастер-класс</span> в&nbsp;финале'),
    ])

    html = _theme_section(html, "Тарифы", [
        # цена на блоке-небе
        ('<div style="border-top: 1px solid #EBDFCA; padding-top: 16px; display: flex; flex-direction: column; gap: 6px;">',
         '<div data-cena="" style="display: flex; flex-direction: column; gap: 6px;">'),
        ("font-size: 40px; line-height: 1; letter-spacing: -.02em; color: #18213A;",
         "font-size: 40px; line-height: 1; letter-spacing: -.02em; color: #FFFFFF;"),
        ('<div style="font-size: 16px; color: #465068;">$', '<div style="font-size: 16px; color: #DCE6F5;">$'),
        # «Всего 50 мест» — плашкой
        ('<div style="display: inline-flex; align-self: flex-start; align-items: center; gap: 10px; '
         'background: linear-gradient(180deg, #FDF1D9 0%, #FBE3B0 100%); border: 1.5px solid #F0B13F;',
         '<div data-mest="" style="display: inline-flex; align-self: flex-start; align-items: center; gap: 10px; border: 0;'),
    ])

    html = _theme_section(html, "Рассрочка", [
        ("color: #1A4A96; padding-top: 3px;", "color: #2B3550; padding-top: 3px;"),
        ("background: linear-gradient(160deg, #1F56A6, #102F73); color: #FBE3B0; flex: none; "
         "box-shadow: 0 4px 10px -4px rgba(16,47,115,.5);", "background: #D22B2B; color: #FFFFFF; flex: none;"),
    ])

    # Подарки: каждый отдельной карточкой с золотым кругом, как посты в тесте.
    html = _theme_section(html, "Подарки и условия", [
        ('<div style="background: linear-gradient(165deg, #1F56A6 0%, #102F73 100%); border: 1px solid #143A85;',
         '<div data-podarki="" style="border: 0;'),
        ("box-shadow: 0 20px 44px -24px rgba(16,47,115,.7), inset 0 1px 0 rgba(255,255,255,.1);", "box-shadow: none;"),
        ("color: #F6CF7A", "color: " + _RED),
        ("color: #FBF6EC", "color: #18213A"),
        ("color: #D9CDB6", "color: #2B3550"),
        ('<div style="display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start;">',
         '<div data-podarok="" style="display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start;">'),
        ("background: linear-gradient(180deg, #FBE3B0, #E39A2B); color: #18213A; flex: none;",
         "background: " + _GOLD + "; color: #143A85; flex: none;"),
    ])

    # Заголовок блока вопросом: на страницах оплаты он один, у заявки другой.
    html = _theme_section_re(html, "Подарки и условия",
                             r"(Что вы получаете|Что даёт заявка|Что даёт предзапись)</h2>", r"\1?</h2>")

    # «Что входит в практикум» на странице предзаписи — тоже вопросом.
    html = _theme_section_re(html, "Что входит",
                             r"(Что входит в(?:&nbsp;|\s)практикум)</h2>", r"\1?</h2>")

    # Кнопка поддержки была красной, как «Оплатить». Красная на странице
    # одна: участие и оплата. Поддержка спокойная, с синей обводкой.
    html = _theme_section(html, "Проблемы с оплатой", [
        ('data-btn="primary"', 'data-btn="support"'),
        ("background: linear-gradient(135deg, #DA352C 0%, #B3161F 100%); color: #FFFFFF;",
         "background: #FFFFFF; color: #143A85;"),
        ("letter-spacing: .1em; text-transform: uppercase;", "letter-spacing: 0;"),
        ("box-shadow: 0 16px 30px -14px rgba(190,30,35,.62);", "box-shadow: inset 0 0 0 2px #143A85;"),
    ])

    # Повышения цены больше нет: убираем подпись под ценой, строку в блоке
    # подарков и прошедший срок закрытия продаж. Полоса со счётчиком скрыта
    # стилем: скрипт страницы ищет её по номеру.
    html = re.sub(r"\s*<div data-price-note[^>]*>.*?</div>", "", html, flags=re.S)
    html = re.sub(r"\s*<p[^>]*>С(?:\s|&nbsp;|\u00a0)27(?:\s|&nbsp;|\u00a0)сентября цена становится выше\.</p>", "", html)
    html = re.sub(r"\s*<p[^>]*>Продажи закрываются 29(?:\s|&nbsp;|\u00a0)сентября[^<]*</p>", "", html)

    # Последний призыв: блок-небо с красной кнопкой, как второй призыв в тесте.
    html = _theme_section(html, "Финальный призыв", [
        ('aria-label="Финальный призыв"', 'data-final="" aria-label="Финальный призыв"'),
        ('<div style="max-width: 640px; margin: 0 auto;', '<div data-final-card="" style="max-width: 640px; margin: 0 auto;'),
    ])
    # Блок про новый формат ответов на вопросы стоит в программе,
    # сразу после карточек недель.
    i = html.rfind('<div data-week-card=""')
    if i >= 0:
        blk = find_block(html, "div", i)
        html = html[:blk[3]] + _THEME_OTVETY + html[blk[3]:]

    # Раздела «Что нового по сравнению с прошлыми потоками» в тестовом
    # оформлении нет: главное из него (новый формат ответов) перенесено
    # в программу, остальное повторяло соседние блоки.
    i = html.find('aria-label="Что нового"')
    if i >= 0:
        blk = find_block(html, "section", html.rfind("<section", 0, i))
        html = html[:blk[0]] + html[blk[3]:]
    return _theme_modal(html)


def _theme_modal(html):
    """Окно заявки. Шапка с четырьмя подарками занимала первый экран,
    до поля «Имя» на телефоне было больше тысячи пикселей. Подарки
    переезжают под форму отдельной карточкой, шапка становится светлой."""
    a = html.find('<div id="lead-modal"')
    if a < 0:
        return html
    blk = find_block(html, "div", a)
    m = html[blk[0]:blk[3]]
    k = m.find("margin-top: 4px; padding-top: 18px; border-top: 1px solid rgba(251,246,236,.16);")
    w = m.find("max-width: 620px; display: flex; flex-direction: column; gap: 24px;")
    if k >= 0 and w >= 0:
        g = find_block(m, "div", m.rfind("<div", 0, k))
        gifts = m[g[0]:g[3]].replace(
            " margin-top: 4px; padding-top: 18px; border-top: 1px solid rgba(251,246,236,.16);", "")
        m = m[:g[0]] + m[g[3]:]
        wb = find_block(m, "div", m.rfind("<div", 0, w))
        card = ('<div data-modal-gifts="" style="background: ' + _PANEL + '; border: 0; '
                'border-radius: 16px; padding: clamp(20px, 3vw, 28px);">' + gifts + "</div>")
        m = m[:wb[2]] + card + m[wb[2]:]
    elif "После оплаты" in m:
        print("  тема: в окне заявки не найден блок подарков")
    for old, new in [
        ("background: rgba(13,36,92,.74);", "background: rgba(24,33,58,.86);"),
        ("background: rgba(251,246,236,.14); border: 1px solid rgba(251,246,236,.3); color: #FBF6EC;",
         "background: #FFFFFF; border: 1px solid #E2D3B6; color: #18213A;"),
        ("background: linear-gradient(165deg, #1A4A96 0%, #0F2A66 100%); border: 1px solid rgba(251,246,236,.14);",
         "background: #FFFFFF; border: 1px solid #EBDFCA;"),
        ("color: #F0B13F;", "color: " + _RED + ";"),
        ("color: #F6CF7A", "color: " + _RED),
        ("color: #FBF6EC", "color: #18213A"),
        ("color: #EEF3FB", "color: #465068"),
        ("color: #D9CDB6", "color: #2B3550"),
        ("color: #1A4A96", "color: #2B3550"),
        ("background: linear-gradient(180deg, #FBE3B0, #E39A2B); color: #18213A; flex: none;",
         "background: " + _GOLD + "; color: #143A85; flex: none;"),
    ]:
        # Три последние замены относятся к блоку подарков; в окне анкеты
        # предзаписи его нет, и сообщать тут не о чем.
        if old not in m and (k >= 0 or "#F6CF7A" not in old and "#D9CDB6" not in old
                             and "#FBE3B0" not in old):
            print("  тема: в окне заявки не найдено: %s" % old[:70])
        m = m.replace(old, new)
    return html[:blk[0]] + m + html[blk[3]:]


def apply_theme(text, path):
    if path.endswith(".html"):
        text = _theme_buttons(text)
    text = _theme_colors(text)
    # Правовые страницы только перекрашиваются: блоков лендинга на них нет.
    if path.endswith(".html") and 'aria-label="Первый экран"' in text:
        text = _theme_layout(text)
    if path.endswith(os.path.join("assets", "site.css")):
        text += THEME_CSS
    return text


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if THEME and path.endswith((".html", ".css")):
        text = apply_theme(text, path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(apply_base(text))


def find_block(text, tag, start=0):
    """Возвращает (open_start, body_start, body_end, close_end) первого <tag ...>…</tag>
    с учётом вложенности. None, если тега нет."""
    m = re.compile(r"<%s\b[^>]*>" % tag).search(text, start)
    if not m:
        return None
    depth = 1
    pos = m.end()
    pat = re.compile(r"<%s\b[^>]*>|</%s>" % (tag, tag))
    while depth:
        m2 = pat.search(text, pos)
        if not m2:
            raise ValueError("незакрытый <%s>" % tag)
        depth += 1 if m2.group(0)[1] != "/" else -1
        pos = m2.end()
        if depth == 0:
            return m.start(), m.end(), m2.start(), m2.end()
    return None


def subst(text, mapping):
    def rep(m):
        key = m.group(1).strip()
        return mapping.get(key, m.group(0))
    return re.sub(r"\{\{([^}]*)\}\}", rep, text)


def expand_weeks(tpl):
    """Раскрывает <sc-for list="{{ weeks }}"> и вложенные sc-for / sc-if."""
    blk = find_block(tpl, "sc-for")
    if not blk:
        return tpl
    o, bs, be, ce = blk
    body = tpl[bs:be]
    out = []
    for w in WEEKS:
        chunk = body
        # вложенный sc-for по приёмам недели
        inner = find_block(chunk, "sc-for")
        if inner:
            io, ibs, ibe, ice = inner
            item_tpl = chunk[ibs:ibe]
            items = "".join(
                subst(item_tpl, {"t.i": str(it["i"]), "t.text": html_mod.escape(it["text"])})
                for it in w["items"]
            )
            chunk = chunk[:io] + items + chunk[ice:]
        # sc-if по сноске недели
        cond = find_block(chunk, "sc-if")
        if cond:
            co, cbs, cbe, cce = cond
            keep = chunk[cbs:cbe] if w["note"] else ""
            chunk = chunk[:co] + keep + chunk[cce:]
        chunk = subst(chunk, {
            "w.icon": w["icon"],
            "w.label": w["label"],
            "w.title": html_mod.escape(w["title"]),
            "w.quote": html_mod.escape(w["quote"]),
            "w.lead": html_mod.escape(w["lead"]),
            "w.note": html_mod.escape(w["note"]),
        })
        out.append(chunk)
    return tpl[:o] + "".join(out) + tpl[ce:]


# ────────────────────────────────────── style-hover / active / focus → CSS ──

HOVER_RULES = {}   # css-текст → имя класса


def collect_state_styles(tpl):
    """style-hover="…" на элементе → класс + правило в таблице стилей."""
    tag_re = re.compile(r"<([a-zA-Z][\w-]*)((?:\"[^\"]*\"|'[^']*'|[^>\"'])*)>")

    def process(m):
        name, attrs = m.group(1), m.group(2)
        states = {}
        for state, pseudo in (("hover", ":hover"), ("active", ":active"), ("focus", ":focus-visible")):
            am = re.search(r'\sstyle-%s="([^"]*)"' % state, attrs)
            if am:
                states[pseudo] = am.group(1).strip()
                attrs = attrs[:am.start()] + attrs[am.end():]
        if not states:
            return m.group(0)
        key = "|".join("%s{%s}" % (p, c) for p, c in sorted(states.items()))
        cls = HOVER_RULES.get(key)
        if not cls:
            cls = "s" + hashlib.md5(key.encode()).hexdigest()[:7]
            HOVER_RULES[key] = cls
        cm = re.search(r'\sclass="([^"]*)"', attrs)
        if cm:
            attrs = attrs[:cm.start()] + ' class="%s %s"' % (cm.group(1), cls) + attrs[cm.end():]
        else:
            attrs = ' class="%s"' % cls + attrs
        return "<%s%s>" % (name, attrs)

    return tag_re.sub(process, tpl)


def hover_css():
    lines = []
    for key, cls in sorted(HOVER_RULES.items(), key=lambda kv: kv[1]):
        for part in key.split("|"):
            pseudo, decl = part.split("{", 1)
            lines.append(".%s%s{%s}" % (cls, pseudo, decl.rstrip("}")))
    return "\n".join(lines)


# ────────────────────────────────────────────────────── контраст текста ──
#
# Замеры на собранной странице показали четыре пары ниже порога 4.5:1 —
# все на светлых карточках тарифов. Значения сдвинуты внутри той же палитры:
# бронза берётся из тёмного акцента #8A5A2B, серые — на два шага темнее.
#
# Отдельно: зачёркнутые пункты «Самостоятельного» давали 3.0:1. Это ровно та
# ошибка, от которой предостерегал бриф: если зачёркнутое сливается в серый
# шум, аргумент тарифа пропадает. Линия зачёркивания тоже усилена.

CONTRAST_FIXES = [
    ("color: #9A9088", "color: #776B61"),                       # 3.00 → 5.01
    ("color: #7D7167", "color: #6E6158"),                       # 4.37 → 5.60
    ("color: #A3835F", "color: #8A5A2B"),                       # 3.38 → 5.66
    ("text-decoration-color: #C9A87F", "text-decoration-color: #8A5A2B"),
    ("margin-top: 1px; color: #C9A87F", "margin-top: 1px; color: #8A5A2B"),
]


def fix_contrast(tpl):
    for old, new in CONTRAST_FIXES:
        tpl = tpl.replace(old, new)
    return tpl


def drop_field(html, name):
    """Убирает <label> целиком вместе с полем name=... внутри."""
    i = html.index('name="%s"' % name)
    a = html.rindex("<label", 0, i)
    b = html.index("</label>", i) + len("</label>")
    return html[:a] + html[b:]


def screen_span(tpl, label):
    """Границы экрана data-screen-label с учётом вложенных div."""
    m = re.search(r'<div[^>]*data-screen-label="%s"[^>]*>' % re.escape(label), tpl)
    if not m:
        raise ValueError("экран не найден: %s" % label)
    depth, pos = 1, m.end()
    pat = re.compile(r"<div\b[^>]*>|</div>")
    while depth:
        m2 = pat.search(tpl, pos)
        if not m2:
            raise ValueError("незакрытый экран: %s" % label)
        depth += -1 if m2.group(0) == "</div>" else 1
        pos = m2.end()
    return m.start(), pos


def drop_screen(tpl, label):
    a, b = screen_span(tpl, label)
    return tpl[:a] + tpl[b:]


def insert_before_screen(tpl, label, html):
    a, _ = screen_span(tpl, label)
    return tpl[:a] + html + tpl[a:]


# ───────────────────────────────────────────────── превращение div → section ──

def divs_to_sections(tpl):
    """Верхнеуровневые экраны data-screen-label → <section aria-label>."""
    out = tpl
    pos = 0
    while True:
        m = re.compile(r'<div([^>]*?)data-screen-label="([^"]*)"([^>]*)>').search(out, pos)
        if not m:
            break
        label = m.group(2)
        # найти парный </div>
        depth = 1
        p = m.end()
        pat = re.compile(r"<div\b[^>]*>|</div>")
        while depth:
            m2 = pat.search(out, p)
            if not m2:
                raise ValueError("незакрытый экран %s" % label)
            depth += -1 if m2.group(0) == "</div>" else 1
            p = m2.end()
        close_start, close_end = p - len("</div>"), p
        attrs = (m.group(1) + m.group(3)).strip()
        aria = re.sub(r"^\d+\w*\s+", "", label)
        opening = '<section %s aria-label="%s">' % (attrs, html_mod.escape(aria))
        out = out[:m.start()] + opening + out[m.end():close_start] + "</section>" + out[close_end:]
        pos = m.start() + len(opening)
    return out


# ──────────────────────────────────────────────────────── общие фрагменты ──

def footer_html(depth_prefix=""):
    docs = "".join(
        '\n        <a href="%s">%s</a>' % (DOC_URL[slug], title)
        for slug, _, title in DOCS
    )
    return """
<footer class="ft" aria-label="Реквизиты и документы">
  <div class="ft-in">
    <div class="ft-grid">

      <div class="ft-col">
        <p class="ft-org">Организатор программ Виолы&nbsp;Маро</p>
        <p class="ft-legal">
          ИП Нижевясова Анна Станиславовна<br>
          ОГРНИП 321695200039136<br>
          ИНН 690503942107<br>
          Зарегистрирована Межрайонной ИФНС России №&nbsp;10 по&nbsp;Тверской области
        </p>
      </div>

      <div class="ft-col">
        <p class="ft-label"><span class="ft-ico" aria-hidden="true">✉</span>e-mail</p>
        <a href="mailto:%(email)s">%(email)s</a>
      </div>

      <div class="ft-col">
        <p class="ft-label"><span class="ft-ico" aria-hidden="true">✈</span>Служба заботы в&nbsp;Telegram</p>
        <a href="%(tg)s" target="_blank" rel="noopener">%(tgname)s</a>
        <p class="ft-hours">пн–пт, 10:00–18:00&nbsp;МСК</p>
      </div>

      <nav class="ft-col ft-docs" aria-label="Правовые документы">
        <p class="ft-label">Документы</p>%(docs)s
      </nav>

    </div>

    <p class="ft-disclaimer">
      Информация на&nbsp;сайте носит информационно-просветительский характер,
      не&nbsp;является медицинской услугой и&nbsp;не&nbsp;заменяет консультацию специалиста. 18+
    </p>
    <p class="ft-copy">
      © Нижевясова А.&nbsp;С., 2026. Все права защищены. Любое использование или
      копирование материалов сайта, элементов дизайна и&nbsp;оформления допускается
      только с&nbsp;письменного разрешения правообладателя и&nbsp;со&nbsp;ссылкой на&nbsp;источник.
    </p>
    <p class="ft-note" id="meta-note">* Meta признана экстремистской организацией в&nbsp;России</p>
  </div>
</footer>
""" % {"email": EMAIL, "tg": TG, "tgname": TG_NAME, "docs": docs}


COOKIE_HTML = """
<div class="cookie-bar" id="cookie-bar" hidden>
  <p>
    Мы используем файлы cookie, чтобы сайт работал корректно и&nbsp;чтобы понимать,
    какие материалы вам полезны. Продолжая пользоваться сайтом, вы&nbsp;соглашаетесь
    с&nbsp;их&nbsp;использованием.
    <a href="/privacy#cookie">Подробнее</a>
  </p>
  <button type="button" id="cookie-ok">Хорошо</button>
</div>
"""

COOKIE_JS = """
(function () {
  var KEY = 'cookie_ok', bar = document.getElementById('cookie-bar');
  if (!bar) return;
  function initAnalytics() {
    /* Сюда — инициализация Яндекс.Метрики и рекламных пикселей.
       До нажатия «Хорошо» ни один аналитический скрипт стартовать не должен. */
  }
  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (e) {}
  if (stored) { initAnalytics(); return; }
  bar.hidden = false;
  document.getElementById('cookie-ok').addEventListener('click', function () {
    try { localStorage.setItem(KEY, new Date().toISOString()); } catch (e) {}
    bar.hidden = true;
    initAnalytics();
  });
})();
"""


def head(title, description, css_path, extra=""):
    if NOINDEX:
        extra = '<meta name="robots" content="noindex, nofollow">\n' + extra
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="theme-color" content="#241C18">
<meta property="og:type" content="website">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:locale" content="ru_RU">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="%(css)s">
%(extra)s</head>
<body>
<a class="skip" href="#main">К основному содержанию</a>
""" % {"title": html_mod.escape(title), "desc": html_mod.escape(description),
       "css": css_path, "extra": extra}


# ─────────────────────────────────────────────────────────────── картинки ──

def build_images():
    global MOBILE_WIDTHS, DESKTOP_WIDTHS
    from PIL import Image, ImageFilter
    src = os.path.join(SRC, "assets", "viola-hero.png")
    outdir = os.path.join(OUT, "assets", "img")
    os.makedirs(outdir, exist_ok=True)
    im = theme_hero_image("desktop") if THEME else Image.open(src).convert("RGB")
    W, H = im.size

    def save(img, name, widths):
        lo, hi = sorted(widths)
        for w in widths:
            suffix = "-sm" if w == lo else ""
            if img.width == w:
                r = img
            else:
                r = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
                # уменьшение всегда мылит; слабая нерезкая маска возвращает
                # кромку глаз и волос, не давая ореолов на ровном фоне
                r = r.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=3))
            for ext, kw in (("webp", {"quality": 90, "method": 6}),
                            ("jpg", {"quality": 88, "optimize": True, "progressive": True,
                                     "subsampling": 0})):
                p = os.path.join(outdir, "%s%s.%s" % (name, suffix, ext))
                r.save(p, **kw)
                made.append(p)

    made = []
    # десктоп — исходный горизонтальный кадр
    DESKTOP_WIDTHS = (1200, 1672)
    save(im, "hero", DESKTOP_WIDTHS)

    # Телефон. Кадр горизонтальный, а экран вдвое уже, чем высок, поэтому
    # из снимка режется вертикальная часть — от MOBILE_CROP_X до правого края.
    # Слева в ней остаётся полоса пустого фона: на неё ложится текст.
    crop = im.crop(MOBILE_CROP)
    cw = crop.width

    face_x = (FACE_X - MOBILE_CROP[0]) / cw * 100
    face_y = FACE_Y / crop.height * 100
    print("  лицо в кадре: %.0f%% ширины, %.0f%% высоты "
          "(эти доли — в object-position)" % (face_x, face_y))

    mob = crop
    if THEME:
        mob = theme_hero_image("mobile")
        cw = mob.width

    MOBILE_WIDTHS = (620, cw)
    save(mob, "hero-mob", MOBILE_WIDTHS)

    if THEME:
        # Первый экран на телефоне собран из двух слоёв: терраса на фоне
        # и Виола отдельной картинкой с прозрачностью, строго по центру.
        p = os.path.join(outdir, "viola.webp")
        _theme_cutout(0.83).save(p, "WEBP", quality=88, method=6)
        made.append(p)
        p = os.path.join(outdir, "terrasa.jpg")
        _theme_terrace((900, 1000), (0.62, 0.5)).save(p, quality=80, optimize=True, progressive=True)
        made.append(p)

    total = sum(os.path.getsize(p) for p in made)
    print("  картинки: %d файлов, %.0f КБ" % (len(made), total / 1024))


def build_geroy_photo():
    """Портрет на первый экран. Вырезка без фона.

    Лицо на снимке измерено по тону кожи, а не прикинуто на глаз: центр
    на 49% ширины и 17,5% высоты, нижняя граница лица на 31% высоты.
    Эти доли лежат в CSS как --face-x и --face-y — на случай, если кадр
    где-то придётся обрезать: object-position ставит точку лица в ту же
    долю рамки при любом её размере.

    Формат — WebP с альфой. PNG того же качества весит вчетверо больше;
    он остаётся запасным, узким и квантованным.
    """
    from PIL import Image
    src = os.path.join(SRC, "assets", "neudobnye-geroy.png")
    outdir = os.path.join(OUT, "assets", "img")
    os.makedirs(outdir, exist_ok=True)

    # Холст НЕ обрезается по альфе намеренно. Кадрирование задаёт окно
    # [data-figclip] в таблице заказчика, и доли там посчитаны от полного
    # кадра 1122×1402. Обрежешь прозрачные поля — рамка уедет и макушка
    # окажется срезанной.
    im = Image.open(src).convert("RGBA")

    made = []
    for w in GEROY_WIDTHS:
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        path = os.path.join(outdir, "geroy%s.webp" % ("-sm" if w == min(GEROY_WIDTHS) else ""))
        r.save(path, quality=88, method=6)
        made.append(path)

    small = im.resize((GEROY_PNG_WIDTH, round(im.height * GEROY_PNG_WIDTH / im.width)),
                      Image.LANCZOS)
    png = os.path.join(outdir, "geroy-sm.png")
    small.quantize(colors=255, method=Image.FASTOCTREE).save(png, optimize=True)
    made.append(png)

    global GEROY_RATIO
    GEROY_RATIO = im.height / im.width
    print("  портрет первого экрана: %d файлов, %.0f КБ"
          % (len(made), sum(os.path.getsize(x) for x in made) / 1024))


GEROY_WIDTHS = (420, 840)
GEROY_PNG_WIDTH = 420
GEROY_RATIO = 1402 / 1122


def geroy_picture():
    lo, hi = GEROY_WIDTHS
    h = round(GEROY_PNG_WIDTH * GEROY_RATIO)
    return ('<picture>'
            '<source type="image/webp" '
            'srcset="/assets/img/geroy-sm.webp %dw, /assets/img/geroy.webp %dw" '
            'sizes="(max-width: 899px) 78vw, 420px">'
            '<img data-geroy="1" src="/assets/img/geroy-sm.png" alt="Виола Маро" '
            'width="%d" height="%d" fetchpriority="high" decoding="async">'
            '</picture>' % (lo, hi, GEROY_PNG_WIDTH, h))
    # Размеры у <img> оставлены: без них браузер не знает пропорций
    # до загрузки и страница прыгает. Кадрирует картинку окно [data-figclip],
    # ширину и высоту ей задаёт таблица заказчика.


def build_avtor_photo():
    """Портрет для экрана «Кто ведёт». Вырезка на бежевом фоне.

    В исходнике это PNG на 1,6 МБ. Отдаётся WebP, JPEG остаётся запасным:
    прозрачности в кадре нет, фон залит, и PNG тут не нужен никому.
    """
    from PIL import Image
    src = os.path.join(SRC, "assets", "viola-cutout-beige.png")
    outdir = os.path.join(OUT, "assets", "img")
    os.makedirs(outdir, exist_ok=True)

    im = Image.open(src).convert("RGB")
    made = []
    for w in AVTOR_WIDTHS:
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        suffix = "-sm" if w == min(AVTOR_WIDTHS) else ""
        for ext, kw in (("webp", {"quality": 86, "method": 6}),
                        ("jpg", {"quality": 84, "optimize": True, "progressive": True})):
            path = os.path.join(outdir, "avtor%s.%s" % (suffix, ext))
            r.save(path, **kw)
            made.append(path)

    print("  портрет автора: %d файлов, %.0f КБ"
          % (len(made), sum(os.path.getsize(x) for x in made) / 1024))


AVTOR_WIDTHS = (560, 840)


def avtor_picture():
    lo, hi = AVTOR_WIDTHS
    return ('<picture>'
            '<source type="image/webp" '
            'srcset="/assets/img/avtor-sm.webp %dw, /assets/img/avtor.webp %dw" '
            'sizes="(max-width: 899px) 86vw, 420px">'
            '<img data-avtor="1" src="/assets/img/avtor-sm.jpg" alt="Виола Маро" '
            'width="%d" height="%d" loading="lazy" decoding="async">'
            '</picture>' % (lo, hi, lo, round(lo * 1448 / 1086)))


MOBILE_WIDTHS = ()
DESKTOP_WIDTHS = ()


def hero_picture():
    mob_lo, mob_hi = sorted(MOBILE_WIDTHS)
    dsk_lo, dsk_hi = sorted(DESKTOP_WIDTHS)

    def src(name, ext, lo, hi):
        return ('/assets/img/%s-sm.%s %dw, /assets/img/%s.%s %dw'
                % (name, ext, lo, name, ext, hi))

    return """<picture>
          <source media="(max-width: 760px)" type="image/webp"
                  srcset="%s"
                  sizes="100vw">
          <source media="(max-width: 760px)" type="image/jpeg"
                  srcset="%s"
                  sizes="100vw">
          <source type="image/webp"
                  srcset="%s"
                  sizes="100vw">
          <img src="/assets/img/hero.jpg"
               srcset="%s"
               sizes="100vw"
               alt="Виола Маро сидит в кресле"
               width="1672" height="941"
               fetchpriority="high" decoding="async">
        </picture>""" % (
        src("hero-mob", "webp", mob_lo, mob_hi),
        src("hero-mob", "jpg", mob_lo, mob_hi),
        src("hero", "webp", dsk_lo, dsk_hi),
        src("hero", "jpg", dsk_lo, dsk_hi))




# ──────────────────────────────────────────── экраны версии предзаписи ──

CTA_BOOK = ('<a href="#bron" data-open-form="Бронь места" data-pay="bron" '
            'style="align-self: center; display: inline-flex; white-space: nowrap; '
            'align-items: center; gap: 14px; '
            'background: linear-gradient(180deg, #F0DCBB 0%, #D9BC92 52%, #C29A6C 100%); '
            'color: #2A211C; text-decoration: none; font-weight: 700; '
            'font-size: clamp(18px, 1.9vw, 22px); letter-spacing: .01em; '
            'padding: 23px 34px 23px 48px; border-radius: 999px; '
            'box-shadow: 0 18px 40px -14px rgba(60,45,32,.45), 0 0 0 1px rgba(194,154,108,.4), '
            '0 0 0 10px rgba(201,168,127,.12), inset 0 1px 0 rgba(255,255,255,.6); '
            'transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;" '
            'style-hover="transform: translateY(-3px); filter: brightness(1.05);" '
            'style-active="transform: translateY(-1px);">Внести бронь'
            '<span style="display: inline-flex; align-items: center; justify-content: center; '
            'width: 34px; height: 34px; border-radius: 50%; background: rgba(42,33,28,.9); '
            'color: #F0DCBB; font-size: 16px; line-height: 1;">→</span></a>')

CTA_DARK = ('<a href="#zapis" data-open-form="Заявка на участие" style="align-self: center; '
            'display: inline-flex; white-space: nowrap; align-items: center; gap: 14px; '
            'background: linear-gradient(165deg, #4E3C31 0%, #2B211C 100%); color: #F6F0E8; '
            'text-decoration: none; font-weight: 700; font-size: clamp(18px, 1.9vw, 22px); '
            'letter-spacing: .01em; padding: 23px 34px 23px 48px; border-radius: 999px; '
            'box-shadow: 0 16px 34px -12px rgba(43,33,28,.55), 0 0 0 1px rgba(43,33,28,.9), '
            '0 0 0 8px rgba(201,168,127,.22), inset 0 1px 0 rgba(255,255,255,.14); '
            'transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;" '
            'style-hover="transform: translateY(-3px); filter: brightness(1.08);" '
            'style-active="transform: translateY(-1px);">Оставить заявку'
            '<span style="display: inline-flex; align-items: center; justify-content: center; '
            'width: 34px; height: 34px; border-radius: 50%; '
            'background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
            'font-size: 16px; line-height: 1;">→</span></a>')

EYEBROW = ('font-size: 12px; letter-spacing: .18em; text-transform: uppercase; '
           'color: #8A5A2B;')

ICON_DIAMOND = ('<span style="display: inline-flex; align-items: center; justify-content: center; '
                'width: 26px; height: 26px; margin-top: 2px; border-radius: 50%; '
                'background: linear-gradient(160deg, #F0DCBB, #C29A6C); color: #2A211C; '
                'font-size: 13px; line-height: 1; flex: none;">◆</span>')

ICON_GIFT = ('<span style="display: inline-flex; align-items: center; justify-content: center; '
             'width: 30px; height: 30px; margin-top: 1px; border-radius: 50%; '
             'background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
             'flex: none;"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" '
             'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true"><path d="M4 11h16v9.5H4z"/>'
             '<path d="M2.8 7.5h18.4V11H2.8zM12 7.5v13"/>'
             '<path d="M12 7.5S10.7 4 8.4 4a1.9 1.9 0 0 0 0 3.5zM12 7.5S13.3 4 15.6 4'
             'a1.9 1.9 0 0 1 0 3.5z"/></svg></span>')

# Порядок пунктов не тот, что был в присланном тексте: закрытый канал поднят
# на первое место. Он единственный, что человек получает сегодня же; цена
# и разговор с командой работают только если он вообще решит покупать.
PRE_FOR_REQUEST = [
    ("Закрытый канал Виолы",
     "подкасты и материалы, которых нет в открытом доступе. Новое вы видите там первыми."),
    ("Право сказать, что включить в программу",
     "в канале спросим, чего вам не хватает, и соберём из ваших ответов часть программы."),
    ("Разговор с командой Виолы Маро",
     "расскажут, как устроен практикум, какой тариф под вашу задачу, ответят на вопросы "
     "и помогут с оплатой, в том числе в рассрочку."),
]

# Два бонуса, которые человек получает за анкету предзаписи. Названия
# и подписи те же, что в тесте 2.0 (miniapps/test2, блок «Что дальше?»):
# оба лежат в закрепе закрытого канала, куда ведёт анкета. Третьей карточки
# теста, про самую низкую цену, здесь нет: цены на сайте открыты всем.
PRE_BONUSES = [
    ("Медитация «Мне можно»",
     "9 минут. Включаете перед трудным разговором или сразу после него."),
    ("Эфир Виолы в записи",
     "подробный разбор: как понять, где ваше, а где чужое."),
]

PRE_FOR_EARLY = [
    ("«Любовь и деньги»",
     "лекция Виолы о том, почему и любовь, и деньги про одно и то же состояние наполненности."),
    ("Разбор фильма «Догвиль»",
     "как эмпат оказывается в позиции жертвы, как устроена эмоциональная зависимость "
     "и как из неё выходят."),
    ("Большой мастер-класс на узнавание себя",
     "там подробно разобрано то, что тест показал коротко."),
    ("Запись терапевтического уикенда «Неудобные»",
     "три дня, 11–13 сентября. Отдельно запись не продаётся, "
     "у вас она останется навсегда."),
]





# ─────────────────────────────────────────────── экраны страницы брони ──

BOOKING_GIVES = [
    ("Место на потоке",
     "оно закрепляется за вами и не уходит другому, пока идёт набор."),
    ("Цена не изменится",
     "сколько бы ни стоило участие к старту, вы платите по цене, "
     "зафиксированной сегодня."),
    ("Все бонусы остаются вашими",
     "включая те, что действуют только для ранней оплаты."),
]


def booking_screens():
    """Короткая страница под личную отправку.

    Продавать заново незачем: человек уже поговорил с командой и решает
    вносить бронь. Поэтому экранов с программой здесь нет, только условия
    и кнопка.
    """
    rows = "".join(
        '<div style="background: linear-gradient(180deg, #FFFFFF 0%%, #FDFAF6 100%%); '
        'border: 1px solid #E9DFD2; border-radius: 16px; '
        'box-shadow: 0 1px 2px rgba(60,48,40,.04), 0 16px 36px -24px rgba(60,48,40,.34); '
        'padding: clamp(24px, 3vw, 32px); display: flex; flex-direction: column; gap: 12px;">'
        '<span style="display: inline-flex; align-items: center; justify-content: center; '
        'width: 44px; height: 44px; border-radius: 50%%; '
        'background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
        'font-size: 18px; font-weight: 700; flex: none; '
        'box-shadow: inset 0 1px 0 rgba(255,255,255,.5);">%d</span>'
        '<h3 style="margin: 0; font-size: clamp(19px, 2.1vw, 23px); font-weight: 700; '
        'letter-spacing: -.02em; line-height: 1.25; color: #2E2521;">%s</h3>'
        '<p style="margin: 0; font-size: 17px; line-height: 1.55; color: #5C5149;">%s</p>'
        "</div>" % (i + 1, t, tail)
        for i, (t, tail) in enumerate(BOOKING_GIVES))

    return '''
<div id="bron" data-screen-label="06 Что даёт бронь" style="background: linear-gradient(180deg, #F5EFE6 0%%, #EFE6DA 100%%); padding: clamp(56px, 8vw, 100px) clamp(14px, 4vw, 40px);">
  <div style="max-width: 1020px; margin: 0 auto; display: flex; flex-direction: column; gap: clamp(26px, 3.4vw, 38px);">
    <div style="display: flex; flex-direction: column; gap: 12px; align-items: center; text-align: center;">
      <div style="%(eyebrow)s">Что даёт бронь</div>
      <h2 style="font-family: \'Golos Text\', system-ui, sans-serif; font-weight: 700; letter-spacing: -.025em; font-size: clamp(34px, 5vw, 56px); line-height: 1.1; margin: 0; text-wrap: balance;">Три вещи, которые бронь закрепляет за&nbsp;вами</h2>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; align-items: stretch;">%(rows)s</div>

    <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 20px 32px; background: linear-gradient(165deg, #4A392F 0%%, #2B211C 100%%); border: 1px solid #33271F; border-radius: 18px; box-shadow: 0 22px 48px -26px rgba(43,33,28,.75), inset 0 1px 0 rgba(255,255,255,.1); padding: clamp(26px, 3.4vw, 38px);">
      <div style="flex: 0 0 auto; display: flex; flex-direction: column; gap: 4px;">
        <span style="font-size: 12px; letter-spacing: .18em; text-transform: uppercase; color: #E9C98F;">Размер брони</span>
        <span style="font-size: clamp(40px, 6vw, 60px); font-weight: 700; letter-spacing: -.03em; line-height: 1; color: #F6F0E8;">%(amount)s</span>
        <span style="font-size: 17px; line-height: 1.4; color: #DCD1C4;">с&nbsp;зарубежной карты&nbsp;— $%(usd)s или €%(eur)s</span>
      </div>
      <div style="flex: 1 1 300px; display: flex; flex-direction: column; gap: 10px; font-size: 17.5px; line-height: 1.55; color: #DCD1C4;">
        <p style="margin: 0;"><b style="color: #F6F0E8; font-weight: 700;">Засчитывается в&nbsp;стоимость участия.</b> Это не&nbsp;доплата сверху: остаток вы&nbsp;вносите за&nbsp;вычетом брони.</p>
        <p style="margin: 0;">Остаток&nbsp;— до&nbsp;%(deadline)s, дня старта потока.</p>
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px; max-width: 68ch; align-self: center; text-align: center;">
      <p style="margin: 0; font-size: 17px; line-height: 1.55; color: #2E2521;">%(carry)s</p>
    </div>

    %(cta)s
  </div>
</div>
''' % {"eyebrow": EYEBROW, "rows": rows, "cta": CTA_BOOK,
       "amount": BOOKING_AMOUNT, "deadline": BOOKING_DEADLINE,
       "carry": BOOKING_CARRY,
       "usd": PAY["bron"]["plans"]["bron"]["usd"],
       "eur": PAY["bron"]["plans"]["bron"]["eur"]}


def rassrochka_tariffs(tpl):
    """Тарифы страницы внутренней рассрочки.

    Стоимость тарифа делится на два равных платежа, на странице вносится
    один. Поэтому в карточке стоит сумма платежа, а рядом прямо сказано,
    что это половина и какова полная цена: число без подписи читалось бы
    как цена практикума. Кнопка одна: рассрочка от банка здесь не при чём.
    """
    half, whole = PAY["rassrochka"]["plans"], PAY["pay"]["plans"]

    tpl, n = re.subn(r'\s*<button type="button" onClick="\{\{ open(?:Basic|Full)Inst \}\}"'
                     r'[^>]*>В рассрочку</button>', "", tpl)
    if n != 2:
        raise ValueError("рассрочка: ожидалось две кнопки «В рассрочку», найдено %d" % n)
    if tpl.count(">Полная оплата<") != 2:
        raise ValueError("рассрочка: ожидалось две кнопки «Полная оплата»")
    tpl = tpl.replace(">Полная оплата<", ">Внести платёж<")

    note = 'data-cena-note="" style="font-size: 15.5px; line-height: 1.4; color: #5C5149;"'
    keys = iter(("basic", "full"))

    def price(m):
        key = next(keys)
        h, w = half[key], whole[key]
        return ('<div %s><b>Внутренняя рассрочка.</b> Один платёж из&nbsp;двух:</div>' % note
                + m.group(1)
                + '<span %s>%s&nbsp;₽</span>' % (m.group(2), h["rub"].replace(" ", "&nbsp;"))
                + m.group(3)
                + '<div %s>$%s &nbsp;  €%s</div>' % (m.group(4), h["usd"], h["eur"])
                + '<div %s>Полная цена тарифа&nbsp;— %s&nbsp;₽, она делится '
                  'на&nbsp;два равных платежа.</div>' % (note, w["rub"].replace(" ", "&nbsp;")))

    tpl, n = re.subn(
        r'(<div style="display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;">\s*)'
        r'<span data-price-before="[^"]*" data-price-after="[^"]*" (style="font-weight: 700; font-size: 40px;[^"]*")>[^<]*</span>'
        r'(\s*</div>\s*)'
        r'<div (style="font-size: 16px; color: #5C5149;")>\$[^<]*</div>',
        price, tpl)
    if n != 2:
        raise ValueError("рассрочка: ожидалось две цены тарифов, найдено %d" % n)

    # В липкой полосе цена тоже помнит старые значения: скрипт их не трогает,
    # пока нет счётчика, но оставлять «от 19 900» рядом с платежом нельзя.
    tpl = re.sub(r' data-price-before="[^"]*" data-price-after="[^"]*"', "", tpl)

    intro = ('<p style="margin: 0; max-width: 62ch; align-self: center; text-align: center; '
             'font-size: clamp(17.1px, 1.8vw, 19px); line-height: 1.5; color: #5C5149;">'
             'Это страница оплаты по&nbsp;внутренней рассрочке: стоимость тарифа делится '
             'на&nbsp;<b style="color: #2E2521;">два равных платежа</b>, здесь вы&nbsp;вносите один.</p>')
    head_end = ">Тарифы</h2>"
    if tpl.count(head_end) != 1:
        raise ValueError("рассрочка: не найден заголовок тарифов")
    return tpl.replace(head_end, head_end + intro)


def gifts_block():
    """Подарки после оплаты — в шапку формы оплаты.

    Человек видит их в момент, когда решает платить, а не страницей выше,
    где он их уже пролистал. Список тот же, что на странице предзаписи:
    расходиться этим двум местам нельзя.
    """
    rows = "".join(
        '<div style="display: grid; grid-template-columns: auto 1fr; gap: 12px; '
        'align-items: start;">%s<p style="margin: 0; font-size: 16px; line-height: 1.5; '
        'color: #DCD1C4;"><b style="color: #F6F0E8; font-weight: 700;">%s</b>&nbsp;— %s</p>'
        "</div>" % (ICON_GIFT, t, tail)
        for t, tail in PRE_FOR_EARLY)

    return ('<div style="display: flex; flex-direction: column; gap: 13px; margin-top: 4px; '
            'padding-top: 18px; border-top: 1px solid rgba(246,240,232,.16);">'
            '<div style="font-size: 12px; letter-spacing: .18em; text-transform: uppercase; '
            'color: #E9C98F;">После оплаты</div>'
            + rows
            + '<p style="margin: 0; font-size: 15px; line-height: 1.5; color: #DCD1C4;">'
              'Подарки команда отправит вам после оплаты.</p></div>')


# Кнопки шага оплаты повторяют стиль двух кнопок тарифа («Полная оплата»
# и «В рассрочку»): в новом оформлении первая становится красной, вторая
# синей, и разбирает их тот же код, что и остальные кнопки страницы.
PAY_BTN_MAIN = ('display: flex; align-items: center; justify-content: center; width: 100%; '
                'cursor: pointer; font-family: inherit; box-sizing: border-box; text-align: center; '
                'text-decoration: none; border: none; '
                'background: linear-gradient(165deg, #4E3C31 0%, #2B211C 100%); color: #F6F0E8; '
                'box-shadow: 0 16px 34px -12px rgba(43,33,28,.55), inset 0 1px 0 rgba(255,255,255,.14); '
                'font-weight: 700; font-size: 19px; padding: 19px 24px; border-radius: 999px; '
                'transition: transform .2s ease, filter .2s ease;')
PAY_BTN_QUIET = ('display: flex; align-items: center; justify-content: center; width: 100%; '
                 'cursor: pointer; font-family: inherit; box-sizing: border-box; text-align: center; '
                 'text-decoration: none; '
                 'background: linear-gradient(180deg, #F7EBD8 0%, #EDD9B8 100%); color: #3B2E28; '
                 'border: 1.5px solid #C9A87F; '
                 'box-shadow: 0 8px 20px -12px rgba(120,90,50,.45), inset 0 1px 0 rgba(255,255,255,.7); '
                 'font-weight: 700; font-size: 19px; padding: 19px 24px; border-radius: 999px; '
                 'transition: transform .2s ease, filter .2s ease;')


def pay_step_html():
    """Второй шаг окна: человек выбирает, чем платит.

    Появляется после того, как контакты и согласия записаны. Две кнопки
    одного веса: российской картой (GetPlatinum) и зарубежной (Lava).
    Суммы и адреса подставляет скрипт из data-pay-config: кнопка тарифа
    одна и та же, а тарифов два. У зарубежной оплаты страница общая
    на оба тарифа, поэтому рядом стоит подсказка, какой там выбрать.
    """
    cfg = PAY[MODE]
    for key, plan in cfg["plans"].items():
        if not (plan["ru"] and cfg["intl"]):
            raise ValueError("оплата %s/%s: нет ссылки" % (MODE, key))
    config = html_mod.escape(json.dumps(cfg, ensure_ascii=False), quote=True)
    ru_note, intl_note = PAY_NOTES[MODE]

    label = 'style="font-size: 16px; font-weight: 700; line-height: 1.3; color: #5C5149;"'
    price = ('style="font-weight: 700; font-size: 34px; line-height: 1.05; '
             'letter-spacing: -.02em; color: #2E2521;"')
    note = 'style="margin: 0; font-size: 16px; line-height: 1.45; color: #5C5149;"'
    small = 'style="margin: 0; font-size: 15px; line-height: 1.5; color: #7D7167;"'
    box = ('style="display: flex; flex-direction: column; gap: 12px; background: #F6F0E8; '
           'border: 1px solid #E4DACD; border-radius: 16px; padding: 18px;"')
    hover = 'style-hover="transform: translateY(-2px); filter: brightness(1.06);"'

    def option(kind, title, price_id, btn_id, btn_style, btn_text, lines, inner=""):
        return ('<div data-pay-option="%s" %s>' % (kind, box)
                + '<div style="display: flex; flex-direction: column; gap: 4px;">'
                  '<span %s>%s</span>' % (label, title)
                + '<span id="%s" data-pay-price="" %s>%s</span></div>' % (price_id, price, inner)
                + "".join(lines)
                + '<a id="%s" href="%s" rel="noopener" style="%s" %s>%s</a>'
                  % (btn_id, TG, btn_style, hover, btn_text)
                + "</div>")

    ru = option("ru", "Если карта российская", "pay-ru-price", "pay-ru",
                PAY_BTN_MAIN, "Российской картой",
                ['<p %s>%s</p>' % (note, ru_note)] if ru_note else [])
    intl = option("intl", "Если карта другой страны", "pay-intl-price", "pay-intl",
                  PAY_BTN_QUIET, "Зарубежной картой",
                  ['<p id="pay-intl-hint" %s>На&nbsp;странице оплаты выберите тариф '
                   '<b style="color: #2E2521; white-space: nowrap;">«<span id="pay-intl-plan">'
                   '</span>»</b>.</p>' % note]
                  + (['<p %s>%s</p>' % (note, intl_note)] if intl_note else []),
                  # «или» между суммами набрано обычным шрифтом: высокий
                  # шрифт цифр строчных букв не имеет.
                  inner='<span id="pay-intl-usd"></span><i> или </i><span id="pay-intl-eur"></span>')

    after = ("После оплаты брони вам напишут из&nbsp;команды Виолы."
             if MODE == "bron" else
             "После оплаты вам напишут из&nbsp;команды Виолы и&nbsp;выдадут все доступы.")

    return (
        '<div id="pay-step" data-step="pay" data-pay-config="%s" hidden>' % config
        + '<div style="background: linear-gradient(180deg, #FFFFFF 0%, #FDFAF6 100%); '
          'border: 1px solid #E4DACD; border-radius: 18px; '
          'box-shadow: 0 1px 2px rgba(60,48,40,.04), 0 24px 52px -30px rgba(60,48,40,.4); '
          'padding: clamp(22px, 3.4vw, 40px); display: flex; flex-direction: column; gap: 18px;">'
        + '<div style="%s">Способ оплаты</div>' % EYEBROW
        + '<h2 id="pay-title" tabindex="-1" style="margin: 0; font-family: \'Golos Text\', '
          'system-ui, sans-serif; font-weight: 700; letter-spacing: -.025em; '
          'font-size: clamp(27px, 3.4vw, 38px); line-height: 1.1; color: #2E2521; '
          'text-wrap: balance; outline: none;">Как вам удобнее оплатить?</h2>'
        + '<div style="display: inline-flex; align-self: flex-start; align-items: center; gap: 10px; '
          'background: linear-gradient(180deg, #F7EBD8 0%, #EDD9B8 100%); border: 1.5px solid #C9A87F; '
          'border-radius: 999px; padding: 9px 18px;">'
          '<span style="width: 7px; height: 7px; border-radius: 50%; background: #8A5A2B; flex: none;"></span>'
          '<span id="pay-plan" style="font-size: 15.5px; font-weight: 700; color: #3B2E28;"></span></div>'
        + ('<p style="margin: 0; font-size: 17px; line-height: 1.45; color: #5C5149;">%s</p>'
           % PAY_LEAD[MODE] if PAY_LEAD[MODE] else "")
        + '<p id="pay-warn" hidden style="margin: 0; font-size: 16px; line-height: 1.5; color: #8A2B2B; '
          'background: #FDF2F0; border: 1px solid #EED8D3; border-radius: 10px; padding: 12px 16px;">'
          'Не&nbsp;удалось сохранить ваши контакты. Оплатить можно и&nbsp;так, а&nbsp;после оплаты '
          'напишите нам в&nbsp;Telegram: <a href="%s" target="_blank" rel="noopener" '
          'style="color: inherit; font-weight: 600;">%s</a>.</p>' % (TG, TG_NAME)
        + ru + intl
        + care_note()
        + '<p %s>Оплата и&nbsp;чек&nbsp;— от&nbsp;ИП Нижевясова А.&nbsp;С., '
          'продюсера программ Виолы Маро.</p>' % small
        + '<p %s>%s</p>' % (small, after)
        + "</div></div>")


ICON_TG = ('<span style="display: inline-flex; align-items: center; justify-content: center; '
           'width: 40px; height: 40px; border-radius: 50%; '
           'background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
           'font-size: 18px; line-height: 1; flex: none;">\u2708</span>')


def care_rows():
    """Две строки-ссылки: имя, юзернейм, стрелка. Вся строка кликабельна.

    Юзернейм вынесен отдельной строкой и крупным: с телефона его не выделишь
    из текста, а искать вручную никто не станет — поэтому он должен читаться
    и как подпись, и как цель нажатия.
    """
    строки = []
    for i, (имя, ник, url) in enumerate(CARE_ACCOUNTS):
        рамка = "" if i == 0 else "border-top: 1px solid #EFE6DA; "
        строки.append(
            '<a href="' + url + '" target="_blank" rel="noopener" '
            'style="' + рамка + 'display: grid; grid-template-columns: auto 1fr auto; '
            'gap: 14px; align-items: center; padding: 16px 2px; text-decoration: none; '
            'color: inherit;">'
            + ICON_TG +
            '<span style="display: flex; flex-direction: column; gap: 3px; min-width: 0;">'
            '<span style="font-size: 18px; font-weight: 600; line-height: 1.25; '
            'color: #2E2521;">' + имя + '</span>'
            '<span style="font-size: 16.5px; line-height: 1.3; color: #6B4E2C; '
            'overflow-wrap: anywhere;">' + ник + '</span>'
            '</span>'
            '<span aria-hidden="true" style="display: inline-flex; align-items: center; '
            'justify-content: center; width: 34px; height: 34px; border-radius: 50%; '
            'background: rgba(42,33,28,.9); color: #F0DCBB; font-size: 16px; '
            'line-height: 1; flex: none;">\u2192</span>'
            '</a>')
    return "".join(строки)


def contacts_screen():
    """Экран «Задать вопрос команде» — одна полоса на два контакта.

    Стоит перед финальным призывом: человек дочитал, решение ещё не принято,
    и здесь ему дают живого человека вместо кнопки покупки. В подвале
    контакт тоже есть, но подвал не читают.
    """
    return ('\n<div id="kontakty" data-screen-label="10 Контакты команды" '
            'style="background: linear-gradient(180deg, #FFFFFF 0%, #FBF6EF 100%); '
            'border-top: 1px solid #E4DACD; '
            'padding: clamp(48px, 6.5vw, 84px) clamp(14px, 4vw, 40px);">'
            '<div style="max-width: 720px; margin: 0 auto; '
            'background: linear-gradient(180deg, #FFFFFF 0%, #FDFAF6 100%); '
            'border: 1px solid #DCCFBC; border-radius: 16px; '
            'box-shadow: 0 1px 2px rgba(60,48,40,.05), 0 18px 40px -24px rgba(60,48,40,.34); '
            'padding: clamp(22px, 3.2vw, 32px); display: flex; flex-direction: column; '
            'gap: 16px;">'
            '<div style="display: flex; flex-direction: column; gap: 8px;">'
            '<div style="' + EYEBROW + '">Отдел заботы</div>'
            '<h2 style="margin: 0; font-family: \'Golos Text\', system-ui, sans-serif; '
            'font-weight: 700; letter-spacing: -.025em; font-size: clamp(26px, 3.6vw, 40px); '
            'line-height: 1.12; color: #2E2521; text-wrap: balance;">'
            'Задать вопрос команде</h2>'
            '</div>'
            '<div style="display: flex; flex-direction: column;">' + care_rows() + '</div>'
            '<p style="margin: 0; font-size: 16.5px; line-height: 1.5; color: #2E2521; '
            'font-weight: 600;">' + CARE_ONLY + '</p>'
            '<p style="margin: 0; font-size: 15px; line-height: 1.5; color: #7D7167;">'
            + CARE_HOURS + '</p>'
            '</div></div>\n')


def care_note(размер="15px"):
    """Та же мысль одной строкой — для мест, где целый экран не нужен:
    под тарифами и в форме заявки."""
    ссылки = " · ".join(
        '<a href="' + url + '" target="_blank" rel="noopener" '
        'style="color: #6B4E2C; font-weight: 600;">' + ник + '</a>'
        for _имя, ник, url in CARE_ACCOUNTS)
    return ('<p style="margin: 0; font-size: ' + размер + '; line-height: 1.5; '
            'color: #5C5149;"><b style="color: #2E2521;">' + CARE_ONLY + '</b> '
            + ссылки + '</p>')


def benefits_screen(include_request=True, pre=False):
    """Подарки и условия заявки — экран, на котором принимается решение.

    Два яруса нарочно разной плотности: за заявку — светлый, порог нулевой;
    за раннюю оплату — тёмный с бронзой, единственное цветное пятно экрана.
    Разница между ними должна читаться до чтения текста.

    Срок назван словами и один раз. Ни таймера, ни счётчика мест: прямая
    красная линия проекта, правка эксперта была «целевая аудитория получается
    каких-то обиженных и оскорблённых».
    """
    def row(title, tail, icon, title_color, text_color):
        return ('<div style="display: grid; grid-template-columns: auto 1fr; gap: 14px; '
                'align-items: start;">%s<p style="margin: 0; font-size: 17.5px; '
                'line-height: 1.55; color: %s;"><b style="color: %s; font-weight: 700;">%s</b>'
                '&nbsp;— %s</p></div>' % (icon, text_color, title_color, title, tail))

    # У анкеты предзаписи список начинается с бонусов из теста 2.0.
    light = "".join(row(t, x, ICON_DIAMOND, "#2E2521", "#5C5149")
                    for t, x in (PRE_BONUSES if pre else []) + PRE_FOR_REQUEST)
    dark = "".join(row(t, x, ICON_GIFT, "#F6F0E8", "#DCD1C4") for t, x in PRE_FOR_EARLY)

    request_column = '''
      <div data-za-zayavku="" style="background: linear-gradient(180deg, #FFFFFF 0%%, #FDFAF6 100%%); border: 1px solid #E9DFD2; border-radius: 16px; box-shadow: 0 1px 2px rgba(60,48,40,.04), 0 16px 36px -24px rgba(60,48,40,.34); padding: clamp(24px, 3.4vw, 36px); display: flex; flex-direction: column; gap: 18px;">
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <div style="%(eyebrow)s">%(za)s</div>
          <p style="margin: 0; font-size: 19px; font-weight: 600; line-height: 1.35; color: #2E2521;">Ничего платить не&nbsp;нужно</p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 14px;">%(light)s</div>
      </div>
''' % {"eyebrow": EYEBROW, "light": light,
       "za": "За анкету предзаписи" if pre else "За саму заявку"} if include_request else ""

    title = ("Что даёт предзапись" if pre else
             "Что даёт заявка" if include_request else "Что вы получаете")
    posle = "после анкеты" if pre else "после заявки"
    grid_width = "1020px" if include_request else "720px"

    return '''
<div id="zapis" data-screen-label="06 Подарки и условия" style="background: linear-gradient(180deg, #F5EFE6 0%%, #EFE6DA 100%%); padding: clamp(56px, 8vw, 100px) clamp(14px, 4vw, 40px);">
  <div style="max-width: 1020px; margin: 0 auto; display: flex; flex-direction: column; gap: clamp(26px, 3.4vw, 38px);">
    <div style="display: flex; flex-direction: column; gap: 12px; align-items: center; text-align: center;">
      <div style="%(eyebrow)s">Пока идёт набор</div>
      <h2 style="font-family: 'Golos Text', system-ui, sans-serif; font-weight: 700; letter-spacing: -.025em; font-size: clamp(38px, 5.6vw, 64px); line-height: 1.1; margin: 0; text-wrap: balance;">%(title)s</h2>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; align-items: stretch; width: 100%%; max-width: %(grid_width)s; align-self: center;">

      %(request_column)s

      <div style="background: linear-gradient(165deg, #4A392F 0%%, #2B211C 100%%); border: 1px solid #33271F; border-radius: 16px; box-shadow: 0 20px 44px -24px rgba(43,33,28,.7), inset 0 1px 0 rgba(255,255,255,.1); padding: clamp(24px, 3.4vw, 36px); display: flex; flex-direction: column; gap: 18px;">
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <div style="font-size: 12px; letter-spacing: .18em; text-transform: uppercase; color: #E9C98F;">После оплаты</div>
          <p style="margin: 0; font-size: 19px; font-weight: 600; line-height: 1.35; color: #F6F0E8;">Четыре подарка сверх программы</p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 14px;">%(dark)s</div>
        <p style="margin: 0; font-size: 15px; line-height: 1.5; color: #DCD1C4;">Подарки команда отправит вам после оплаты.</p>
      </div>

    </div>

    <div style="align-self: center; max-width: 54ch; text-align: center; display: flex; flex-direction: column; gap: 8px;">
      <p style="margin: 0; font-size: 17px; line-height: 1.55; color: #2E2521;">Оплату оформляет команда: %(posle)s она свяжется с&nbsp;вами.</p>
    </div>

    %(cta)s
  </div>
</div>
''' % {"eyebrow": EYEBROW, "dark": dark, "cta": CTA_DARK,
       "title": title, "request_column": request_column, "grid_width": grid_width,
       "posle": posle,
}


# Состав участия сгруппирован, а не вывален списком из тринадцати галок.
# Четыре группы человек охватывает взглядом; тринадцать равных строк —
# читает по диагонали и не запоминает ни одной.
PRE_GROUPS = [
    ("Программа",
     '<rect x="3" y="4.5" width="18" height="13" rx="1.6"/>'
     '<path d="M8 21h8M12 17.5V21M10.6 8.6l4.4 2.6-4.4 2.6z"/>',
     ["Шесть лекций Виолы в записи с таймкодами, по одной в неделю",
      "18 техник эмпата, по три на неделю",
      "Практические задания после каждой лекции"]),
    ("Внимание Виолы",
     '<rect x="9" y="3" width="6" height="10" rx="3"/>'
     '<path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
     ["Вопросы Виоле в чате: команда собирает их каждый день, Виола отвечает аудио",
      "Мастер-класс Виолы с ответами на ваши вопросы"]),
    ("Материалы",
     '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9.5 12h5M9.5 16h5"/>',
     ["PDF-методички к каждой лекции",
      "Аудиомедитации от Виолы"]),
    ("Люди рядом",
     '<circle cx="9" cy="9" r="3"/><circle cx="16.5" cy="12" r="2.4"/>'
     '<path d="M3.5 19c.7-2.8 2.8-4.3 5.5-4.3M13 19c.3-1.9 1.6-2.9 3.5-2.9s3.2 1 3.5 2.9"/>',
     ["Чат потока"]),
]


def pre_contents_screen():
    """«Что входит в практикум» — четыре карточки вместо списка из галок.

    Тарифы намеренно не показываются: на предзаписи цены нет, а выбор тарифа
    человек делает в разговоре с командой. Показывать урезанный состав раньше
    времени значит отговаривать на пустом месте.
    """
    def card(title, paths, items):
        icon = ('<span style="display: inline-flex; align-items: center; justify-content: center; '
                'width: 46px; height: 46px; border-radius: 50%%; '
                'background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
                'flex: none; box-shadow: inset 0 1px 0 rgba(255,255,255,.5);">'
                '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
                'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
                'aria-hidden="true">%s</svg></span>' % paths)
        rows = "".join(
            '<div style="display: grid; grid-template-columns: 9px 1fr; gap: 12px; '
            'align-items: start;"><span style="width: 5px; height: 5px; margin-top: 10px; '
            'border-radius: 50%%; background: #C9A87F;"></span>'
            '<span style="font-size: 17px; line-height: 1.5; color: #5C5149;">%s</span></div>' % t
            for t in items)
        return ('<div style="background: linear-gradient(180deg, #FFFFFF 0%%, #FDFAF6 100%%); '
                'border: 1px solid #E9DFD2; border-radius: 16px; '
                'box-shadow: 0 1px 2px rgba(60,48,40,.04), 0 16px 36px -24px rgba(60,48,40,.34); '
                'padding: clamp(24px, 3vw, 32px); display: flex; flex-direction: column; '
                'gap: 16px;">%s<h3 style="margin: 0; font-size: clamp(20px, 2.2vw, 24px); '
                'font-weight: 700; letter-spacing: -.02em; line-height: 1.25; color: #2E2521;">'
                '%s</h3><div style="display: flex; flex-direction: column; gap: 11px;">%s</div>'
                "</div>" % (icon, title, rows))

    cards = "".join(card(t, p, i) for t, p, i in PRE_GROUPS)

    return '''
<div data-screen-label="07 Что входит" style="background: linear-gradient(180deg, #FBF7F1 0%%, #F4EDE3 100%%); padding: clamp(56px, 8vw, 100px) clamp(14px, 4vw, 40px);">
  <div style="max-width: 1020px; margin: 0 auto; display: flex; flex-direction: column; gap: clamp(24px, 3vw, 34px);">
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <div style="%(eyebrow)s">По максимуму</div>
      <h2 style="font-family: \'Golos Text\', system-ui, sans-serif; font-weight: 700; letter-spacing: -.025em; font-size: clamp(38px, 5.6vw, 64px); line-height: 1.1; margin: 0; text-wrap: balance;">Что входит в практикум</h2>
      <p style="margin: 0; font-size: clamp(17.1px, 1.89vw, 19.8px); line-height: 1.55; max-width: 60ch; color: #5C5149;">Полный состав участия&nbsp;— всё, что можно получить на&nbsp;практикуме.</p>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 18px; align-items: stretch;">%(cards)s</div>

    <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 16px 22px; background: linear-gradient(165deg, #4A392F 0%%, #2B211C 100%%); border: 1px solid #33271F; border-radius: 16px; box-shadow: 0 18px 40px -24px rgba(43,33,28,.7), inset 0 1px 0 rgba(255,255,255,.1); padding: clamp(22px, 3vw, 28px) clamp(24px, 3vw, 32px);">
      <span style="display: inline-flex; align-items: center; justify-content: center; width: 52px; height: 52px; border-radius: 50%%; background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; font-size: 24px; font-weight: 700; flex: none; box-shadow: inset 0 1px 0 rgba(255,255,255,.5);">∞</span>
      <div style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 4px;">
        <p style="margin: 0; font-size: clamp(19px, 2.1vw, 23px); font-weight: 700; letter-spacing: -.02em; color: #F6F0E8;">Доступ навсегда</p>
        <p style="margin: 0; font-size: 17px; line-height: 1.5; color: #DCD1C4;">Записи лекций, методички и&nbsp;материалы остаются у&nbsp;вас без срока.</p>
      </div>
    </div>

    <p style="margin: 0; font-size: 17px; line-height: 1.55; color: #5C5149;">Тарифы и&nbsp;цены команда разберёт с&nbsp;вами лично: подскажет, какой тариф под&nbsp;вашу задачу, и&nbsp;поможет оформить оплату, в&nbsp;том числе в&nbsp;рассрочку.</p>

    %(cta)s
  </div>
</div>
''' % {"eyebrow": EYEBROW, "cards": cards, "cta": CTA_DARK}



TIMER_SCREEN = """
<div data-screen-label="01b Повышение цены" id="srok" style="background: linear-gradient(180deg, #2B211C 0%, #241C18 100%); border-top: 1px solid rgba(246,240,232,.12); padding: clamp(20px, 3vw, 30px) clamp(14px, 4vw, 40px);">
  <div style="max-width: 1020px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; text-align: center; gap: clamp(12px, 2vw, 16px);">
    <p style="margin: 0; max-width: 34ch; font-size: clamp(15px, 1.7vw, 17px); font-weight: 700; line-height: 1.4; color: #F6F0E8;">До повышения цены</p>
    <div id="countdown" style="display: flex; align-items: flex-start; gap: clamp(10px, 2vw, 18px);" data-deadline="__DEADLINE__">
      <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 54px;"><span data-cd="d" style="font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; line-height: 1; color: #F0DCBB; font-variant-numeric: tabular-nums;">—</span><span style="font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #B8AA9C;">дней</span></div>
      <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 54px;"><span data-cd="h" style="font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; line-height: 1; color: #F0DCBB; font-variant-numeric: tabular-nums;">—</span><span style="font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #B8AA9C;">часов</span></div>
      <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 54px;"><span data-cd="m" style="font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; line-height: 1; color: #F0DCBB; font-variant-numeric: tabular-nums;">—</span><span style="font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #B8AA9C;">минут</span></div>
      <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 54px;"><span data-cd="s" style="font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; line-height: 1; color: #C9A87F; font-variant-numeric: tabular-nums;">—</span><span style="font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #B8AA9C;">секунд</span></div>
    </div>
  </div>
</div>
""".replace("__DEADLINE__", PRICE_ISO)


# ──────────────────────────────────────────────────────────────── лендинг ──

def build_landing():
    raw = read(os.path.join(SRC, "Лендинг ПЭ 4.0.dc.html"))
    tpl = raw[raw.index("</helmet>") + len("</helmet>"):]
    tpl = tpl[:tpl.index('<script type="text/x-dc"')]

    tpl = expand_weeks(tpl)

    # ── первый экран: image-slot → <picture> ────────────────────────────────
    tpl = re.sub(
        r'<div data-hero-photo="" style="[^"]*">.*?</div>',
        lambda m: '<div data-hero-photo="" style="position: absolute; inset: 0;">\n        '
                  + hero_picture() + "\n      </div>",
        tpl, count=1, flags=re.S)

    # ── модальная форма: React-состояние → обычный <dialog>-подобный блок ──
    blk = find_block(tpl, "sc-if")            # первый оставшийся sc-if — это formOpen
    o, bs, be, ce = blk
    form = tpl[bs:be]

    for cond, el_id in (("formError", "form-error"), ("formSent", "form-sent")):
        inner = find_block(form, "sc-if")
        io, ibs, ibe, ice = inner
        body = form[ibs:ibe].strip()
        body = re.sub(r"^<(\w+)", r'<\1 id="%s" hidden' % el_id, body, count=1)
        form = form[:io] + body + form[ice:]

    form = form.replace("{{ formPlan }}", '<span id="form-plan"></span>')
    form = form.replace("{{ formError }}", '<span id="form-error-text"></span>')
    form = re.sub(r'\sonClick="\{\{ closeForm \}\}"', ' data-close-form', form)
    form = re.sub(r'\sonClick="\{\{ submitForm \}\}"', ' id="form-submit"', form)

    fields = {"fName": ("name", "text"), "fPhone": ("phone", "tel"), "fTg": ("tg", "text")}
    for var, (nm, _t) in fields.items():
        form = re.sub(r'\svalue="\{\{ %s \}\}"\s*onInput="\{\{ on\w+ \}\}"' % var,
                      ' name="%s"' % nm, form)

    boxes = {"agreeOffer": ("accept_offer", True), "agreeData": ("accept_pd", True),
             "agreeMail": ("accept_ads", False)}
    for var, (nm, req) in boxes.items():
        form = re.sub(r'\schecked="\{\{ %s \}\}"\s*onChange="\{\{ \w+ \}\}"' % var,
                      ' name="%s"%s' % (nm, " required" if req else ""), form)

    # ссылки на документы вместо href="#"
    doc_links = iter(["/offer", "/offer-prilozhenie", "/consent", "/privacy", "/consent-ads"])
    n_hrefs = form.count('href="#"')
    if n_hrefs != 5:
        raise ValueError("в форме ожидалось 5 ссылок-заглушек, найдено %d" % n_hrefs)
    form = re.sub(r'href="#"',
                  lambda m: 'href="%s" target="_blank" rel="noopener"' % next(doc_links), form)

    # сообщение об ошибке рядом с каждой обязательной галкой (требование правового ТЗ)
    must = ('<span style="font-size: 12px; letter-spacing: .14em; text-transform: uppercase; '
            'color: #8A5A2B;">Обязательно</span>')
    if form.count(must) != 2:
        raise ValueError("ожидалось две обязательные галки, найдено %d" % form.count(must))
    form = form.replace(must, must + '<span class="cb-err" hidden></span>')

    # ── это не заявка, а шаг перед оплатой ────────────────────────────────
    # Контакты и согласия собираются здесь, потому что акцепт оферты должен
    # быть получен и записан до платежа (раздел 3 правового ТЗ). Сразу после
    # записи в таблицу человек уходит на страницу оплаты.
    note = 'style="margin: 0; font-size: 15px; line-height: 1.5; color: #7D7167;"'

    # Исходные подписи шаблона описывают ровно сценарий заявки: человек
    # оставляет контакты, дальше пишет команда. В режиме zayavka их почти
    # не нужно трогать — а вот платёжные, наоборот, все до одной лишние.
    IS_ZAYAVKA = MODE == "zayavka"
    IS_PRE = MODE == "predzapis"
    # Страницы, где принимаются деньги: после формы идёт выбор способа оплаты.
    HAS_PAY_STEP = MODE in PAY
    PAY_NEXT = ("На&nbsp;следующем шаге выберете, как платить: "
                "российской картой или зарубежной.")

    for old, new in () if IS_ZAYAVKA else (
        ("Запись на поток",
         "Оформление участия"),
        ("Оставьте контакты&nbsp;— мы напишем вам",
         "Оставьте контакты&nbsp;— на&nbsp;них придут доступы"),
        ("Ответим в&nbsp;Telegram, поможем оформить оплату или рассрочку.",
         PAY_NEXT),
        ("Отправить заявку",
         "Перейти к оплате"),
        ("Готово. Мы получили заявку и&nbsp;напишем вам в&nbsp;Telegram.",
         "Готово. Открываем страницу оплаты…"),
    ):
        if old not in form:
            raise ValueError("не найдена строка модалки: %s" % old)
        form = form.replace(old, new)

    tail = "Нажимая кнопку, вы&nbsp;подтверждаете отмеченные согласия.</p>"

    if IS_ZAYAVKA:
        # Оплаты на странице нет, значит нет и акцепта оферты: требовать
        # согласие с договором купли-продажи там, где ничего не покупают,
        # юридически неверно и просто лишний барьер. Так же сделано
        # на предзаписи.
        form = drop_field(form, "accept_offer")

        for old, new in (
            ("Запись на поток", "Заявка на участие"),
            ("Оставьте контакты&nbsp;— мы напишем вам",
             "Оставьте контакты&nbsp;— команда напишет вам"),
            ("Ответим в&nbsp;Telegram, поможем оформить оплату или рассрочку.",
             "Сразу после заявки откроется чат с&nbsp;командой Виолы "
             "в&nbsp;Telegram: расскажем, как устроен практикум, ответим "
             "на&nbsp;вопросы и&nbsp;поможем провести оплату безопасно&nbsp;— "
             "целиком или в&nbsp;рассрочку."),
            ("Готово. Мы получили заявку и&nbsp;напишем вам в&nbsp;Telegram.",
             "Готово. Открываем чат с&nbsp;командой…"),
        ):
            if old not in form:
                raise ValueError("не найдена строка модалки заявки: %s" % old)
            form = form.replace(old, new)

        form = form.replace(tail, tail
            + "<p %s>Заявка ничего не&nbsp;списывает и&nbsp;ни&nbsp;к&nbsp;чему "
              "не&nbsp;обязывает: тариф и&nbsp;способ оплаты вы&nbsp;обсудите "
              "с&nbsp;командой.</p>" % note
            + "<p %s>Оплата и&nbsp;чек&nbsp;— от&nbsp;ИП Нижевясова А.&nbsp;С., "
              "продюсера программ Виолы Маро.</p>" % note)
    else:
        form = form.replace(tail, tail
            + "<p %s>Оплата и&nbsp;чек&nbsp;— от&nbsp;ИП Нижевясова А.&nbsp;С., "
              "продюсера программ Виолы Маро.</p>" % note
            + "<p %s>Также вам напишет команда Виолы, если у&nbsp;вас не&nbsp;получится, "
              "и&nbsp;поможет найти варианты оплаты, если вы&nbsp;точно решили идти "
              "на&nbsp;программу.</p>" % note
            + "<p %s>После оплаты вам сразу же напишут из&nbsp;команды Виолы, чтобы выдать "
              "все доступы и&nbsp;показать, как всё работает, чтобы вы&nbsp;с&nbsp;максимальным "
              "комфортом прошли программу.</p>" % note)

    if MODE == "bron":
        # Деньги принимаются, значит акцепт оферты обязателен — галка
        # остаётся, в отличие от предзаписи.
        for old, new in (
            ("Оформление участия", "Бронь места"),
            ("Оставьте контакты&nbsp;— на&nbsp;них придут доступы",
             "Оставьте контакты&nbsp;— пришлём доступы"),
            (PAY_NEXT,
             "На&nbsp;следующем шаге выберете, как внести бронь: российской картой "
             "(%s) или зарубежной ($%s или €%s). Бронь засчитывается в&nbsp;стоимость "
             "участия, остаток вносится до&nbsp;%s."
             % (BOOKING_AMOUNT.replace(" ", "&nbsp;"), PAY["bron"]["plans"]["bron"]["usd"],
                PAY["bron"]["plans"]["bron"]["eur"], BOOKING_DEADLINE)),
            ("Перейти к оплате", "Внести бронь"),
        ):
            if old not in form:
                raise ValueError("не найдена строка модалки брони: %s" % old)
            form = form.replace(old, new)

    if IS_PRE:
        # Предзаписи нечего акцептовать: покупки нет, значит нет и оферты.
        # Требовать её согласие на бесплатной заявке юридически неверно
        # и лишний барьер. Согласие на обработку ПД остаётся — контакты
        # мы всё равно собираем.
        form = drop_field(form, "accept_offer")

        chip = re.search(r'<div style="display: inline-flex; align-self: flex-start;[^>]*>'
                         r'.*?</div>\s*</div>', form, re.S)
        if chip:
            form = form[:chip.start()] + "</div>" + form[chip.end():]

        for old, new in (
            ("Оформление участия", "Анкета предзаписи"),
            ("Оставьте контакты&nbsp;— на&nbsp;них придут доступы",
             "Оставьте контакты&nbsp;— откроем канал"),
            (PAY_NEXT,
             "Сразу после анкеты откроется закрытый канал Виолы. Команда свяжется с&nbsp;вами "
             "в&nbsp;Telegram: расскажет, как устроен практикум, ответит на&nbsp;вопросы "
             "и&nbsp;поможет оформить оплату."),
            ("Перейти к оплате", "Попасть в предзапись"),
            ("Готово. Открываем страницу оплаты…", "Готово. Открываем закрытый канал…"),
        ):
            if old not in form:
                raise ValueError("не найдена строка модалки предзаписи: %s" % old)
            form = form.replace(old, new)

        # вопрос о готовности — между контактами и согласиями
        opts = ("Готов(а) участвовать", "Присматриваюсь", "Пока не готов(а), но интересно")
        radios = "".join(
            '<label style="display: grid; grid-template-columns: 26px 1fr; gap: 14px; '
            'align-items: center; cursor: pointer;">'
            '<input type="radio" name="readiness" value="%s"%s style="appearance: auto; '
            'width: 20px; height: 20px; margin: 0; accent-color: #4A392F; cursor: pointer;">'
            '<span style="font-size: 16.5px; line-height: 1.45; color: #3B2E28;">%s</span>'
            "</label>" % (o, " checked" if i == 0 else "", o)
            for i, o in enumerate(opts))
        block = ('<div style="display: flex; flex-direction: column; gap: 12px;">'
                 '<span style="font-size: 13px; font-weight: 600; letter-spacing: .16em; '
                 'text-transform: uppercase; color: #6B4E2C;">Готовность пойти на программу'
                 "</span>" + radios + "</div>")
        divider = ('<div style="height: 1px; background: linear-gradient(90deg, #C9A87F, '
                   'rgba(228,218,205,.2));"></div>')
        form = form.replace(divider, block + divider, 1)

        # подписи под кнопкой у предзаписи свои: платить пока нечего
        keep = "Нажимая кнопку, вы&nbsp;подтверждаете отмеченные согласия.</p>"
        tail = form.index(keep) + len(keep)
        form = form[:tail] + ('<p style="margin: 0; font-size: 15px; line-height: 1.5; '
                              'color: #7D7167;">Анкета бесплатна и&nbsp;ни&nbsp;к&nbsp;чему '
                              'не&nbsp;обязывает.</p>') + form[form.index("</div>", tail):]

    # Кому писать и с каких аккаунтов ждать ответа — там, где человек
    # оставляет свой Telegram. Вставляется после правок всех режимов:
    # у предзаписи свой блок приписок затирает всё, что стоит раньше.
    маркер = "Нажимая кнопку, вы&nbsp;подтверждаете отмеченные согласия.</p>"
    if маркер not in form:
        raise ValueError("не найдена приписка под кнопкой формы")
    form = form.replace(маркер, маркер + care_note(), 1)

    # приманка для ботов: поле не видно и не читается экранным диктором,
    # заполнить его может только робот, который разбирает форму по разметке
    honeypot = ('<div class="hp" aria-hidden="true">'
                '<label>Не заполняйте это поле'
                '<input type="text" name="website" tabindex="-1" autocomplete="off">'
                "</label></div>")
    form = form.replace('<label style="display: flex; flex-direction: column; gap: 8px;">',
                        honeypot + '<label style="display: flex; flex-direction: column; gap: 8px;">', 1)

    if MODE in ("pay", "rassrochka", "bron", "zayavka"):
        # Подарки идут под плашкой тарифа, внутри тёмной шапки формы:
        # это последний экран перед платежом, и здесь они ещё работают.
        # После id="form-plan" идут два </span> и </div> самой плашки:
        # первый же </div> и есть её закрытие. Следующий закрыл бы тёмную
        # шапку, и блок оказался бы под карточкой, на голой подложке.
        i = form.index('id="form-plan"')
        j = form.index("</div>", i) + len("</div>")
        form = form[:j] + gifts_block() + form[j:]

    # Чем кончается отправка: страница оплаты, закрытый канал или
    # ничего — заявку разбирает команда.
    after = {"predzapis": "channel", "zayavka": "team"}.get(MODE, "pay")

    if HAS_PAY_STEP:
        # Шаг выбора оплаты встаёт первым в колонку окна; шапка и карточка
        # с полями помечены, чтобы скрипт убрал их, когда шаг откроется.
        wrap = '<div style="width: 100%; max-width: 620px; display: flex; flex-direction: column; gap: 24px;">'
        head_card = ('<div style="display: flex; flex-direction: column; gap: 10px; '
                     'background: linear-gradient(165deg, #3B2E28 0%, #241C18 100%);')
        field_card = ('<div style="background: linear-gradient(180deg, #FFFFFF 0%, #FDFAF6 100%); '
                      'border: 1px solid #E4DACD; border-radius: 18px;')
        for piece in (wrap, head_card, field_card):
            if form.count(piece) != 1:
                raise ValueError("окно оплаты: ожидался один блок, найдено %d: %s"
                                 % (form.count(piece), piece[:60]))
        form = form.replace(head_card, head_card.replace("<div ", '<div data-step="form" ', 1))
        form = form.replace(field_card, field_card.replace("<div ", '<div data-step="form" ', 1))
        form = form.replace(wrap, wrap + pay_step_html())
    form = ('<div id="lead-modal" class="modal" role="dialog" aria-modal="true" '
            'aria-labelledby="lead-title" data-after="%s" hidden>' % after + form + "</div>")
    form = form.replace('<h2 style="margin: 0; font-family:', '<h2 id="lead-title" style="margin: 0; font-family:', 1)
    tpl = tpl[:o] + form + tpl[ce:]

    # ── кнопки тарифов открывают форму ─────────────────────────────────────
    # Ссылка на оплату одна на тариф: и прямая оплата, и рассрочка ведут
    # на неё же — способ человек выбирает уже на стороне GetPlatinum.
    # Кнопка при этом помнит, что именно нажали: это уходит в таблицу.
    plans = {"openBasicPay": ("Самостоятельный — оплата целиком", "basic"),
             "openBasicInst": ("Самостоятельный — в рассрочку", "basic"),
             "openFullPay": ("С Виолой — оплата целиком", "full"),
             "openFullInst": ("С Виолой — в рассрочку", "full")}

    if MODE == "rassrochka":
        tpl = rassrochka_tariffs(tpl)
        plans = {"openBasicPay": ("Самостоятельный — внутренняя рассрочка", "basic"),
                 "openFullPay": ("С Виолой — внутренняя рассрочка", "full")}
    for var, (label, key) in plans.items():
        tpl = tpl.replace('onClick="{{ %s }}"' % var,
                          'data-open-form="%s" data-pay="%s"' % (label, key))

    # «Оформить рассрочку» ведёт к тарифам, а не в поддержку: рассрочка
    # оформляется на той же странице оплаты, что и прямой платёж, но сначала
    # человек должен выбрать тариф. Заодно снимаем target="_blank" —
    # это якорь на своей же странице, новая вкладка тут ни к чему.
    inst = re.search(r'<a href="\{\{ contactUrl \}\}"[^>]*>', tpl)
    if not inst:
        raise ValueError("не найдена кнопка «Оформить рассрочку»")
    fixed = (inst.group(0)
             .replace('href="{{ contactUrl }}"', 'href="#tarify"')
             .replace(' target="_blank"', '')
             .replace(' rel="noopener"', ''))
    tpl = tpl[:inst.start()] + fixed + tpl[inst.end():]

    tpl = tpl.replace("{{ contact }}", TG)

    # <br> внутри h1 не даёт пробела при копировании и в выдаче
    tpl = tpl.replace("Прикладная<br>эмпатия", "Прикладная <br>эмпатия", 1)

    # надзаголовок первого экрана: имя не должно разрываться по строкам
    tpl = tpl.replace("от\u00a0Виолы Маро", "от\u00a0Виолы\u00a0Маро")

    if MODE == "bron":
        # Страницу отправляют лично тем, кто уже поговорил с командой.
        # Продавать заново незачем — остаются только первый экран,
        # условия брони и призыв.
        for label in ("02 Зачем мне это", "03 Что нового", "04 Программа шесть недель",
                      "05 Финальный мастер-класс", "06 Тарифы",
                      "06b Проблемы с оплатой", "07 Рассрочка"):
            tpl = drop_screen(tpl, label)

        tpl = insert_before_screen(tpl, "11 Финальный призыв", booking_screens())

        tpl = tpl.replace("Принять участие", "Внести бронь")
        tpl = tpl.replace('href="#tarify"',
                          'href="#bron" data-open-form="Бронь места" data-pay="bron"')

        tpl = tpl.replace("от 19&nbsp;900&nbsp;₽", "Бронь " + BOOKING_AMOUNT)
        tpl = tpl.replace(
            "В «С Виолой» <b>50&nbsp;мест</b>. Оплатить можно сразу или частями&nbsp;— "
            "<b>рассрочка до&nbsp;12&nbsp;месяцев</b> для&nbsp;СНГ.",
            "Бронь %s закрепляет за&nbsp;вами место, цену и&nbsp;бонусы. "
            "Остаток&nbsp;— до&nbsp;%s." % (BOOKING_AMOUNT, BOOKING_DEADLINE))
        tpl = tpl.replace("Продажи закрываются 29&nbsp;сентября в&nbsp;23:59",
                          "Бронь засчитывается в&nbsp;стоимость участия")

        # Заголовок прямо называет, что это за страница.
        tpl = tpl.replace("Прикладная <br>эмпатия 2.0",
                          "Бронь на <br>«Прикладную эмпатию 2.0»", 1)

    if MODE == "rassrochka":
        # Экран про рассрочку от банка здесь лишний: страница про другую,
        # внутреннюю, и два разных «частями» рядом путают.
        tpl = drop_screen(tpl, "07 Рассрочка")

        for old, new in (
            ("от 19&nbsp;900&nbsp;₽",
             "от&nbsp;%s&nbsp;₽"
             % PAY["rassrochka"]["plans"]["basic"]["rub"].replace(" ", "&nbsp;")),
            ('color: #7D7167;">старт 1&nbsp;ноября</span>',
             'color: #7D7167;">один платёж из&nbsp;двух</span>'),
            ("В «С Виолой» <b>50&nbsp;мест</b>. Оплатить можно сразу или частями&nbsp;— "
             "<b>рассрочка до&nbsp;12&nbsp;месяцев</b> для&nbsp;СНГ.",
             "В «С Виолой» <b>50&nbsp;мест</b>. На&nbsp;этой странице оплата идёт "
             "по&nbsp;внутренней рассрочке: <b>двумя равными платежами</b>."),
        ):
            if tpl.count(old) != 1:
                raise ValueError("рассрочка: ожидалась одна строка, найдено %d: %s"
                                 % (tpl.count(old), old[:50]))
            tpl = tpl.replace(old, new)

    if IS_PRE:
        # Уходят все экраны, где есть цена или оплата. Рассрочка тоже: она
        # про деньги, а её содержание сжимается в одну строку про разговор
        # с командой в блоке «что входит».
        for label in ("06 Тарифы", "06b Проблемы с оплатой", "07 Рассрочка"):
            tpl = drop_screen(tpl, label)

        tpl = insert_before_screen(tpl, "11 Финальный призыв",
                                   benefits_screen(True, pre=True) + pre_contents_screen())

        # Кнопки вставленных экранов писались под страницу заявки.
        tpl = tpl.replace("Оставить заявку", "Попасть в предзапись")
        tpl = tpl.replace('data-open-form="Заявка на участие"', 'data-open-form="Предзапись"')

        # Полосы со сроком нет: у предзаписи сейчас нет даты, после которой
        # что-то меняется.

        # Оффер практикума на первом экране остаётся как есть. Под кнопкой
        # добавлена строка о том, что будет сразу после анкеты.
        row = '<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 18px 24px;">'
        i = tpl.find(row)
        if i < 0:
            raise ValueError("предзапись: не найдена строка с кнопкой на первом экране")
        blk = find_block(tpl, "div", i)
        tpl = (tpl[:blk[3]]
               + '<p data-hero-pod="" style="margin: 0; max-width: 46ch; font-size: clamp(14px, 1.5vw, 17px); '
                 'font-weight: 500; line-height: 1.45; color: #F6F0E8;">После анкеты откроется '
                 'закрытый канал Виолы: в&nbsp;нём медитация и&nbsp;эфир для&nbsp;вас.</p>'
               + tpl[blk[3]:])

        # Надзаголовок: первым словом «Предзапись», плашкой, чтобы читалось
        # раньше названия. Дальше — что это за практикум, мелким.
        old_brow = ('<div style="font-size: clamp(10px, 1.7vw, 12.5px); letter-spacing: .2em; '
                    'text-transform: uppercase; color: #C9A87F; line-height: 1.5;">'
                    '6-недельный практикум для\u00a0эмпатов от\u00a0Виолы\u00a0Маро</div>')
        if old_brow not in tpl:
            raise ValueError("не найден надзаголовок первого экрана")
        tpl = tpl.replace(old_brow,
            '<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 10px 12px; '
            'font-size: clamp(10px, 1.7vw, 12.5px); letter-spacing: .2em; '
            'text-transform: uppercase; color: #C9A87F; line-height: 1.5;">'
            '<b style="background: linear-gradient(180deg, #F0DCBB, #C29A6C); color: #2A211C; '
            'font-weight: 700; letter-spacing: .16em; padding: 7px 14px; border-radius: 999px; '
            'box-shadow: inset 0 1px 0 rgba(255,255,255,.5);">Анкета предзаписи</b>'
            '<span>на 6-недельный практикум для\u00a0эмпатов от\u00a0Виолы\u00a0Маро</span>'
            "</div>")

        # Один призыв на все кнопки, как и было в исходном брифе: этой
        # аудитории не надо гадать, куда нажимать.
        tpl = tpl.replace("Принять участие", "Попасть в предзапись")

        # Кнопки вели к тарифам, которых больше нет. Теперь открывают форму,
        # а якорь остаётся запасным путём, если скрипт не отработал.
        tpl = tpl.replace('href="#tarify"',
                          'href="#zapis" data-open-form="Предзапись"')

        # Липкая панель: вместо цены — состояние набора.
        tpl = tpl.replace("от 19&nbsp;900&nbsp;₽", "Предзапись открыта")
        tpl = tpl.replace(
            '<span style="font-size: 17px; font-weight: 600; color: #2E2521;">',
            '<span style="font-size: 16px; font-weight: 700; color: #2E2521;">', 1)

        # Финальный экран говорил про оплату и цену — обоих пока нет.
        tpl = tpl.replace(
            "В «С Виолой» <b>50&nbsp;мест</b>. Оплатить можно сразу или частями&nbsp;— "
            "<b>рассрочка до&nbsp;12&nbsp;месяцев</b> для&nbsp;СНГ.",
            "Предзапись открыта. Заполните анкету: откроется закрытый канал Виолы, "
            "а&nbsp;команда расскажет про программу и&nbsp;ответит на&nbsp;вопросы.")
        tpl = tpl.replace("Продажи закрываются 29&nbsp;сентября в&nbsp;23:59",
                          "Анкета бесплатна и&nbsp;ни&nbsp;к&nbsp;чему не&nbsp;обязывает")

    if MODE == "zayavka":
        # Страницу отправляют тем, кто пришёл из канала и часто платит
        # онлайн впервые. Цены остаются на месте — уходит только сам
        # платёж: кнопки открывают заявку, а оплату человек проводит
        # вместе с командой. Это и есть смысл страницы: не оставить
        # человека один на один с платёжной формой.
        for old, new, expect in (
            ("Принять участие", "Оставить заявку", 7),
            (">Полная оплата", ">Оставить заявку", 2),
            (">В рассрочку", ">Хочу в рассрочку", 2),
        ):
            if tpl.count(old) != expect:
                raise ValueError("кнопка %s: ожидалось %d, найдено %d"
                                 % (old, expect, tpl.count(old)))
            tpl = tpl.replace(old, new)

        tpl = tpl.replace(
            "В «С Виолой» <b>50&nbsp;мест</b>. Оплатить можно сразу или частями&nbsp;— "
            "<b>рассрочка до&nbsp;12&nbsp;месяцев</b> для&nbsp;СНГ.",
            "В «С Виолой» пятьдесят мест. Оставьте заявку&nbsp;— откроется чат "
            "с&nbsp;командой: ответим на&nbsp;вопросы и&nbsp;поможем оплатить безопасно.")

        # Липкая панель обещала переход к оплате — теперь ведёт к заявке.
        tpl = tpl.replace("Продажи закрываются 29&nbsp;сентября в&nbsp;23:59",
                          "Оплату проводим вместе с&nbsp;командой")

        tpl = tpl.replace(
            "В «С Виолой» пятьдесят мест. Оставьте заявку&nbsp;— откроется чат "
            "с&nbsp;командой: ответим на&nbsp;вопросы и&nbsp;поможем оплатить безопасно.",
            "Продажи открыты. После заявки с вами свяжется команда Виолы "
            "и расскажет подробнее про программу.")

    # На странице оплаты стоял прошедший срок закрытия продаж. Новая дата
    # не назначена: строку убираем, а не оставляем неверную.
    tpl = re.sub(r"\s*<p[^>]*>Продажи закрываются 29(?:&nbsp;|\u00a0| )сентября[^<]*</p>", "", tpl)

    if MODE in ("pay", "rassrochka", "zayavka"):
        # Полосы «До повышения цены» со счётчиком больше нет: цена не растёт.
        tpl = insert_before_screen(tpl, "11 Финальный призыв",
                                   benefits_screen(MODE == "zayavka"))

    # Контакты команды — отдельным экраном перед финальным призывом,
    # на всех четырёх версиях страницы.
    tpl = insert_before_screen(tpl, "11 Финальный призыв", contacts_screen())

    if MODE in ("pay", "rassrochka", "zayavka"):
        # Та же мысль под тарифами: это момент, когда человек решается
        # платить, и именно тогда полезно знать, кто ему напишет.
        # Сноски о курсе валют больше нет, заметка встаёт в её контейнер.
        низ_тарифов = ('<div style="max-width: 760px; align-self: center; '
                       'display: flex; flex-direction: column; gap: 12px; '
                       'text-align: center; color: #5C5149;">')
        if низ_тарифов not in tpl:
            raise ValueError("не найден блок под тарифами")
        tpl = tpl.replace(низ_тарифов, низ_тарифов + care_note("16px"), 1)

    # ── сноска про Meta у самого упоминания (требование правового ТЗ) ──────
    # На странице брони экран с этим упоминанием не выводится, и сноска
    # вместе с ним не нужна: ставить её не к чему.
    mentions = tpl.count("Инстаграме")
    if mentions > 1:
        raise ValueError("ожидалось одно упоминание Инстаграма, найдено %d" % mentions)
    HAS_META_NOTE = mentions == 1
    tpl = tpl.replace("Инстаграме",
                      'Инстаграме<a href="#meta-note" class="fn" '
                      'aria-label="Сноска: Meta признана экстремистской организацией в России">*</a>')

    # ── подвал .dc заменяем на правовой ────────────────────────────────────
    m = re.search(r'<div data-screen-label="12 Подвал"', tpl)
    tpl = tpl[:m.start()]

    tpl = fix_contrast(tpl)
    tpl = divs_to_sections(tpl)
    tpl = collect_state_styles(tpl)

    body = ('<main id="main" data-mode="%s">' % MODE + tpl.strip() + "</main>"
            + footer_html() + COOKIE_HTML)

    # Предзагрузки нет намеренно: <link rel="preload" as="image"> не умеет
    # выбирать между <source> по типу и тянет JPEG поверх уже выбранного WebP —
    # лишние 100 КБ на первом экране. Портрет и так первый элемент в DOM,
    # сканер предзагрузки находит его сразу, а приоритет задан fetchpriority.
    extra = ""

    page = head(
        "Прикладная эмпатия 2.0 — 6-недельный практикум Виолы Маро",
        "Шесть недель, шесть сфер жизни и 18 техник для людей с повышенной чувствительностью. "
        "Практикум психолога Виолы Маро. Старт 1 ноября.",
        "/assets/site.css", extra)
    page += body
    page += '\n<script src="/assets/site.js"></script>\n</body>\n</html>\n'
    write(os.path.join(OUT, "index.html"), page)
    return page


# ──────────────────────────────────────────────── страница «Неудобные» ──
#
# Собирается не из шаблона DesignCraft, а из своей разметки: у события
# нет ни недель, ни тарифов, ни формы заявки, и натягивать на него
# лендинг практикума значило бы тащить десять чужих экранов ради двух
# общих. Общими остаются шапка, подвал, cookie-полоса, шрифты и палитра —
# то, что обязано совпадать на всех страницах сайта.


CTA_NEUD = ('<a class="n-btn n-cta" href="#bilet">Приобрести билет'
            '<span class="n-arrow" aria-hidden="true">→</span></a>')


# Обратный отсчёт и липкая панель. В исходнике DesignCraft это состояние
# компонента; здесь то же самое обычным скриптом, без сборки и зависимостей.
#
# Дата стоит в двух местах: здесь и в тексте страницы («до 4 сентября»).
# Меняете срок — меняете оба.
NEUD_JS = """
(function () {
  'use strict';

  var box = document.querySelector('[data-timer]');
  if (box) {
    var end = new Date(2026, 8, 4, 23, 59, 59);
    var cells = {};
    ['d', 'dl', 'h', 'hl', 'm', 'ml'].forEach(function (k) {
      cells[k] = box.querySelector('[data-cd="' + k + '"]');
    });
    var plural = function (n, forms) {
      var a = Math.abs(n) % 100, b = a % 10;
      if (a > 10 && a < 20) return forms[2];
      if (b === 1) return forms[0];
      if (b >= 2 && b <= 4) return forms[1];
      return forms[2];
    };
    var timer;
    var tick = function () {
      var ms = end - new Date();
      /* Срок вышел — полоса убирается целиком. Нули читаются как сломанная
         страница, а подарок к этому моменту и правда закрыт. */
      if (ms <= 0) { box.hidden = true; clearInterval(timer); return; }
      var d = Math.floor(ms / 86400000),
          h = Math.floor(ms / 3600000) % 24,
          m = Math.floor(ms / 60000) % 60;
      cells.d.textContent = d; cells.dl.textContent = plural(d, ['день', 'дня', 'дней']);
      cells.h.textContent = h; cells.hl.textContent = plural(h, ['час', 'часа', 'часов']);
      cells.m.textContent = m; cells.ml.textContent = plural(m, ['минута', 'минуты', 'минут']);
    };
    tick();
    timer = setInterval(tick, 30000);
  }

  var bar = document.querySelector('[data-sticky]');
  if (bar) {
    var on = null;
    var scroll = function () {
      var v = window.scrollY > window.innerHeight * 0.9 ? '1' : '0';
      if (v !== on) { on = v; bar.setAttribute('data-on', v); }
    };
    window.addEventListener('scroll', scroll, { passive: true });
    scroll();
  }
})();
"""

# Стиль лендинга приходит из исходника, а не из build-assets. Заполняется
# в build_neudobnye(), поэтому build_css() обязан идти после сборки страницы.
NEUD_CSS = ""


def build_neudobnye():
    """Страница события. Собирается из исходника DesignCraft.

    Лендинг полностью переработан заказчиком 31.08: своя палитра
    с терракотовым акцентом, засечная Literata, счётчик мест и обратный
    отсчёт. К прежней версии страницы отношения не имеет, поэтому
    build-assets/neudobnye.html и neudobnye.css сняты.

    Сборщик делает четыре вещи и больше ничего: вынимает стиль и разметку,
    снимает внешние ссылки на шрифты, разворачивает шаблонные подстановки
    в обычный скрипт и подставляет настоящие адреса картинок и оплаты.
    Вёрстку заказчика не трогает: правки по ней идут отдельно и осознанно,
    иначе следующий экспорт из DesignCraft их затрёт.
    """
    global NEUD_CSS
    raw = read(os.path.join(SRC, "Лендинг Неудобные v5.dc.html"))

    NEUD_CSS = re.search(r"<style>(.*?)</style>", raw, re.S).group(1).strip()
    # Константы неиспользуемых картинок: объявлены, нигде не читаются.
    NEUD_CSS = re.sub(r'\s*--foto-(geroy|avtor):\s*url\("[^"]*"\);', "", NEUD_CSS)

    body = raw[raw.index("</helmet>") + len("</helmet>"):]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    body = body[:body.index("</x-dc>")]
    body = re.sub(r"</?x-dc[^>]*>", "", body).strip()

    # ── подстановки шаблона → разметка под обычный скрипт ──────────────
    for mark, cell in (("dd", "d"), ("hh", "h"), ("mm", "m"),
                       ("ddLabel", "dl"), ("hhLabel", "hl"), ("mmLabel", "ml")):
        token = "{{ %s }}" % mark
        if token not in body:
            raise ValueError("в исходнике нет метки %s" % token)
        body = body.replace(token, '<span data-cd="%s">—</span>' % cell)
    body = body.replace('data-on="{{ sticky }}"', 'data-on="0"')

    left = re.findall(r"\{\{[^}]*\}\}", body)
    if left:
        raise ValueError("остались нераскрытые подстановки: %s" % left[:3])

    # ── портрет первого экрана ─────────────────────────────────────────
    if body.count('<img data-geroy="1"') != 1:
        raise ValueError("ожидался один портрет первого экрана")
    body = re.sub(r'<img data-geroy="1"[^>]*>', lambda _m: geroy_picture(), body, count=1)

    # ── портрет автора ─────────────────────────────────────────────────
    if body.count('<img data-avtor="1"') != 1:
        raise ValueError("ожидался один портрет автора")
    body = re.sub(r'<img data-avtor="1"[^>]*>', lambda _m: avtor_picture(), body, count=1)

    # ── набор закрыт (11.09): событие идёт, покупка отключена ──────────
    #
    # Кнопки «Занять место» заменяются плашкой «Набор закрыт», счётчики
    # мест, полоса таймера и липкая панель снимаются: считать больше
    # нечего, а цена в панели устарела. Скрипт таймера и панели трогать
    # не нужно — он проверяет наличие элементов. Чтобы снова открыть
    # набор, этот блок заменяется прежним: кнопки вели на форму заявки
    # ('data-btn="1" href="#zapis" data-open-form="Неудобные" '
    # 'data-pay="neudobnye"') — контакты и согласия собираются до денег.
    n_btn = body.count('data-btn="1" href="#"')
    if n_btn < 3:
        raise ValueError("ожидалось не меньше трёх кнопок оплаты, найдено %d" % n_btn)
    body = re.sub(r'<div data-sticky="1".*?</div>\s*', "", body, flags=re.S)
    body = re.sub(r'<a data-btn="1" href="#".*?</a>',
                  '<p style="margin:36px 0 0;font-size:21px;font-weight:600;'
                  'color:var(--ink-soft)">Набор закрыт</p>', body, flags=re.S)
    n_seats = len(re.findall(r'<div data-seats="1"', body))
    if n_seats != 2:
        raise ValueError("ожидалось два счётчика мест, найдено %d" % n_seats)
    body = re.sub(r'<div data-seats="1".*?</div>\s*', "", body, flags=re.S)
    body = re.sub(r'<div data-timer="1".*?</div>\s*', "", body, flags=re.S)

    # Форма заявки при закрытом наборе не подключается: открыть её
    # больше нечем, а мёртвая модалка на странице только путает.

    page = head(
        "Неудобные. Терапевтический уикенд Виолы Маро 11–13 сентября",
        "Три дня 11–13 сентября: лекция о жизненных ролях, авторская медитация "
        "и прямой эфир с Виолой Маро. Записи остаются навсегда. Набор закрыт.",
        "/assets/site.css")
    page += '<main id="main">\n' + body + "\n</main>\n"
    page += footer_html() + COOKIE_HTML
    page += '\n<script src="/assets/site.js"></script>\n</body>\n</html>\n'
    write(os.path.join(OUT, "index.html"), page)

    print("  index.html: страница события «Неудобные», исходник v5")
    print("  набор закрыт: %d кнопок заменены плашкой, форма снята" % n_btn)
    return page


# ────────────────────────────────────────────────────────── правовые страницы ──

def build_docs():
    for slug, url, title in DOCS:
        frag = read(os.path.join(LEGAL, slug + ".html"))

        # первый заголовок становится <h1> страницы и убирается из текста
        m = re.search(r"<h([12])[^>]*>(.*?)</h\1>", frag, re.S)
        heading = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", m.group(2))).strip()
        frag = frag[:m.start()] + frag[m.end():]

        # таблицы — со скроллом внутри своего контейнера
        frag = re.sub(r"<table", '<div class="tw"><table', frag)
        frag = re.sub(r"</table>", "</table></div>", frag)

        # cookie-полоса ссылается на /privacy#cookie — даём разделу короткий якорь
        frag = re.sub(r'(<h[1-6] id="[^"]*cookie[^"]*")',
                      r'<span id="cookie" class="anchor"></span>\1', frag, count=1)

        page = head(heading + " — Прикладная эмпатия 2.0",
                    "%s. ИП Нижевясова А. С., организатор программ Виолы Маро." % heading,
                    "/assets/site.css")
        page += """
<header class="doc-top">
  <div class="doc-top-in">
    <a class="doc-back" href="/">← Прикладная эмпатия 2.0</a>
  </div>
</header>
<main id="main" class="doc">
  <div class="doc-in">
    <h1>%s</h1>
    %s
  </div>
</main>
""" % (html_mod.escape(heading), frag.strip())
        page += footer_html() + COOKIE_HTML
        page += '\n<script src="/assets/site.js"></script>\n</body>\n</html>\n'
        write(os.path.join(OUT, url, "index.html"), page)
        print("  /%s — %s" % (url, heading))


# ───────────────────────────────────────────────────────────────── шрифты ──

FONT_FACES = [
    ("Golos Text", "GolosText-cyrillic-ext.woff2", "400 700",
     "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F"),
    ("Golos Text", "GolosText-cyrillic.woff2", "400 700",
     "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    ("Golos Text", "GolosText-latin-ext.woff2", "400 700",
     "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Golos Text", "GolosText-latin.woff2", "400 700",
     "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Prata", "Prata-cyrillic-ext.woff2", "400",
     "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F"),
    ("Prata", "Prata-cyrillic.woff2", "400",
     "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    ("Prata", "Prata-latin.woff2", "400",
     "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
]


# Literata — засечный шрифт нового лендинга события. У остальных страниц
# сайта его нет, поэтому список отдельный: в общий FONT_FACES он попадать
# не должен, иначе практикум начнёт таскать 250 КБ, которых не использует.
#
# Начертания сняты с Google Fonts и подшиты файлами. Исходник события
# грузил их ссылкой, а на этом сайте внешних запросов не бывает ни одного:
# страница обязана открываться из России без VPN, ради этого из лендинга
# практикума в своё время убрали ровно такую же ссылку.
LITERATA_FACES = [
    ("Literata", "Literata-cyrillic-ext-400-italic.woff2", "400", "italic",
     "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F"),
    ("Literata", "Literata-cyrillic-400-italic.woff2", "400", "italic",
     "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    ("Literata", "Literata-latin-ext-400-italic.woff2", "400", "italic",
     "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Literata", "Literata-latin-400-italic.woff2", "400", "italic",
     "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Literata", "Literata-cyrillic-ext-400.woff2", "400", "normal",
     "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F"),
    ("Literata", "Literata-cyrillic-400.woff2", "400", "normal",
     "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    ("Literata", "Literata-latin-ext-400.woff2", "400", "normal",
     "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Literata", "Literata-latin-400.woff2", "400", "normal",
     "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Literata", "Literata-cyrillic-ext-600.woff2", "600", "normal",
     "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F"),
    ("Literata", "Literata-cyrillic-600.woff2", "600", "normal",
     "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    ("Literata", "Literata-latin-ext-600.woff2", "600", "normal",
     "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Literata", "Literata-latin-600.woff2", "600", "normal",
     "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
]


def font_css():
    out = []
    for fam, fname, weight, urange in FONT_FACES:
        out.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
            "src:url(/assets/fonts/%s) format('woff2');unicode-range:%s}"
            % (fam, weight, fname, urange))
    for fam, fname, weight, style, urange in (LITERATA_FACES if MODE == "neudobnye" else []):
        out.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;"
            "src:url(/assets/fonts/%s) format('woff2');unicode-range:%s}"
            % (fam, style, weight, fname, urange))
    return "\n".join(out)


def copy_fonts():
    dst = os.path.join(OUT, "assets", "fonts")
    os.makedirs(dst, exist_ok=True)
    total = 0
    names = [f[1] for f in FONT_FACES]
    if MODE == "neudobnye":
        names += [f[1] for f in LITERATA_FACES]
    if THEME:
        names.append(THEME_FONT)
    for fname in names:
        s = os.path.join(BUILD_ASSETS, "fonts", fname)
        shutil.copy2(s, os.path.join(dst, fname))
        total += os.path.getsize(s)
    print("  шрифты: %d файлов, %.0f КБ" % (len(names), total / 1024))


# ──────────────────────────────────────────────────────────────────── CSS ──

def build_css():
    css = font_css() + "\n\n" + read(os.path.join(BUILD_ASSETS, "base.css"))
    if MODE == "neudobnye":
        css += "\n\n/* ── событие «Неудобные», стиль из исходника ── */\n" + NEUD_CSS
    css += "\n\n/* состояния наведения и фокуса, перенесённые из инлайновых стилей */\n"
    css += hover_css() + "\n"
    write(os.path.join(OUT, "assets", "site.css"), css)
    print("  site.css: %.0f КБ" % (len(css.encode()) / 1024))


def build_js():
    js = read(os.path.join(BUILD_ASSETS, "site.js")) + "\n" + COOKIE_JS
    if MODE == "neudobnye":
        js += "\n" + NEUD_JS
    write(os.path.join(OUT, "assets", "site.js"), js)


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#2B211C"/>
  <text x="32" y="45" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif"
        font-size="38" fill="#E4C08A">Э</text>
</svg>
"""


def build_favicon():
    write(os.path.join(OUT, "assets", "favicon.svg"), FAVICON)


# ──────────────────────────────────────────────────── версии файлов ──
#
# Имена картинок и стилей не меняются от сборки к сборке, поэтому браузер
# продолжает показывать сохранённую копию — новое фото до человека просто
# не доезжает. К каждой ссылке на файл дописывается короткий хеш его
# содержимого: меняется файл — меняется адрес — кэш обновляется сам.

def add_cache_busting():
    digests = {}
    missing = set()

    def digest(rel):
        if rel not in digests:
            path = os.path.join(OUT, rel.lstrip("/"))
            if not os.path.isfile(path):
                return None
            with open(path, "rb") as f:
                digests[rel] = hashlib.md5(f.read()).hexdigest()[:8]
        return digests[rel]

    ref = re.compile(r"/assets/[\w./-]+\.(?:css|js|webp|jpg|png|svg)")

    def stamp(m):
        rel = m.group(0)
        if BASE and rel.startswith(BASE):
            rel = rel[len(BASE):]
        d = digest(rel)
        if d is None:
            missing.add(rel)          # файла нет — это битая ссылка, не мелочь
            return m.group(0)
        return "%s?v=%s" % (m.group(0), d)

    n = 0
    for dirpath, _dirs, files in os.walk(OUT):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                html = f.read()
            with open(path, "w", encoding="utf-8") as f:
                f.write(ref.sub(stamp, html))
            n += 1
    if missing:
        raise ValueError("страницы ссылаются на несуществующие файлы: %s"
                         % ", ".join(sorted(missing)))
    print("  версии файлов проставлены в %d страницах" % n)


# ──────────────────────────────────────────────── сборка под Тильду ──
#
# Тильда даёт вставить произвольный HTML в блок T123, но страница вокруг
# уже своя: свои стили, свои шрифты, свой контейнер. Поэтому кусок для
# вставки готовится иначе, чем обычная страница.
#
# Три отличия:
#   1. Стили ограничены обёрткой .vm — иначе правила на body, html и *
#      уедут в вёрстку Тильды, а её правила придут в нашу.
#   2. Шрифты и картинки зашиты в сам кусок: путей /assets на Тильде нет.
#   3. Ни <html>, ни <head> — только содержимое. Заголовок страницы
#      и описание заводятся в настройках страницы Тильды.

TILDA_SCOPE = "vm"

VM_WIDTH_JS = """
/* Точная ширина окна без полосы прокрутки — для выхода блока на всю ширину
   изнутри контейнера Тильды. 100vw для этого не годится: она полосу считает. */
(function () {
  var root = document.documentElement;
  function set() { root.style.setProperty('--vm-vw', root.clientWidth + 'px'); }
  set();
  addEventListener('resize', set);
  addEventListener('orientationchange', function () { setTimeout(set, 250); });
})();
"""


def _data_uri(path, mime):
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def _scope_css(css, scope):
    """Приписывает каждому селектору обёртку.

    Правила на html и body становятся правилами на саму обёртку: внутри
    Тильды у нас нет своего body, его роль играет .vm.
    """
    out = []
    i = 0
    while i < len(css):
        if css[i] == "@":
            # @font-face и @media: первый оставляем как есть, во второй заходим
            head_end = css.index("{", i)
            at = css[i:head_end].strip()
            depth, j = 1, head_end + 1
            while depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            body = css[head_end + 1:j - 1]
            if at.startswith("@media") or at.startswith("@supports"):
                out.append("%s{%s}" % (at, _scope_css(body, scope)))
            else:
                out.append("%s{%s}" % (at, body))
            i = j
            continue

        brace = css.find("{", i)
        if brace == -1:
            break
        close = css.index("}", brace)
        sels = css[i:brace].strip()
        decls = css[brace + 1:close].strip()
        i = close + 1
        if not sels:
            continue

        fixed = []
        for sel in sels.split(","):
            sel = sel.strip()
            if not sel:
                continue
            if sel in ("html", "body"):
                fixed.append("." + scope)
            elif sel.startswith("body."):
                fixed.append(".%s%s" % (scope, sel[4:]))
            elif sel.startswith("html "):
                fixed.append(".%s %s" % (scope, sel[5:]))
            elif sel.startswith("*"):
                fixed.append(".%s%s" % (scope, sel[1:]))
                fixed.append(".%s *%s" % (scope, sel[1:]))
            else:
                fixed.append(".%s %s" % (scope, sel))
        out.append("%s{%s}" % (",".join(fixed), decls))
    return "".join(out)


def build_tilda(src_dir, out_dir):
    """Из готовых страниц делает куски для вставки в блок T123."""
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    css = read(os.path.join(src_dir, "assets", "site.css"))
    js = read(os.path.join(src_dir, "assets", "site.js"))

    # шрифты внутрь стилей
    fonts = 0
    for name in sorted(os.listdir(os.path.join(src_dir, "assets", "fonts"))):
        uri = _data_uri(os.path.join(src_dir, "assets", "fonts", name), "font/woff2")
        css = css.replace("url(/assets/fonts/%s)" % name, "url(%s)" % uri)
        fonts += 1

    css = _scope_css(css, TILDA_SCOPE)

    # Блок Тильды может лежать внутри её колонки с ограниченной шириной,
    # и тогда первый экран получает поля по бокам вместо края в край.
    # Приём стандартный: растянуть обёртку на ширину окна и вытянуть её
    # назад отрицательным отступом. Если блок и так во всю ширину,
    # отступ выходит нулевым и ничего не меняется.
    # Правило идёт последним намеренно: body{margin:0} из общих стилей
    # превращается в .vm{margin:0} и обнулило бы отрицательный отступ,
    # стой оно после. Ширина берётся не из 100vw — эта единица считает
    # и полосу прокрутки, давая лишний горизонтальный скролл; точную
    # ширину без полосы подставляет скрипт.
    css = css + (".%s{width:var(--vm-vw,100vw);max-width:var(--vm-vw,100vw);"
                 "margin-left:calc(50%% - var(--vm-vw,100vw)/2);}" % TILDA_SCOPE)

    made = []
    for dirpath, _dirs, files in os.walk(src_dir):
        if "index.html" not in files:
            continue
        rel = os.path.relpath(dirpath, src_dir)
        html = read(os.path.join(dirpath, "index.html"))

        body = html[html.index("<body>") + len("<body>"):html.rindex("</body>")]
        body = re.sub(r'<a class="skip".*?</a>\s*', "", body, flags=re.S)
        body = re.sub(r'<script src="[^"]*"></script>\s*', "", body)

        # Внутрь куска идёт только WebP и только по одному размеру на кадр:
        # JPEG-запаска и мелкие варианты удваивали вес, а base64 и так
        # раздувает файл на треть. WebP понимают все браузеры с 2020 года.
        pic = re.search(r"<picture>.*?</picture>", body, re.S)
        if pic:
            body = body[:pic.start()] + (
                '<picture>'
                '<source media="(max-width: 760px)" type="image/webp" '
                'srcset="/assets/img/hero-mob.webp">'
                '<img src="/assets/img/hero.webp" '
                'alt="Виола Маро сидит в кресле" width="1672" height="941" '
                'fetchpriority="high" decoding="async">'
                '</picture>') + body[pic.end():]

        # картинки внутрь разметки
        def inline(m):
            path = os.path.join(src_dir, m.group(1).lstrip("/").split("?")[0])
            if not os.path.isfile(path):
                return m.group(0)
            mime = "image/webp" if path.endswith(".webp") else "image/jpeg"
            return m.group(0).replace(m.group(1), _data_uri(path, mime))

        body = re.sub(r'(/assets/img/[\w.-]+(?:\?v=[a-f0-9]+)?)', inline, body)

        name = ("index" if rel == "." else rel.replace(os.sep, "-")) + ".html"
        piece = ("<style>" + css + "</style>\n"
                 + '<div class="' + TILDA_SCOPE + '">' + body.strip() + "</div>\n"
                 + "<script>" + VM_WIDTH_JS + js + "</script>\n")
        write(os.path.join(out_dir, name), piece)
        made.append((name, os.path.getsize(os.path.join(out_dir, name)) / 1024))

    print("  куски для Тильды (%d шрифтов внутри):" % fonts)
    for name, kb in sorted(made):
        print("    %-26s %6.0f КБ" % (name, kb))


# ─────────────────────────────────────────────────────────────────── main ──

def build_pre_redirect():
    target = "https://violamaro.ru/zayavka"
    html = '''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="0;url=%(target)s">
  <link rel="canonical" href="%(target)s">
  <title>Переход к заявке</title>
  <script>
    location.replace(%(target_json)s + location.search + location.hash);
  </script>
</head>
<body><a href="%(target)s">Перейти к заявке</a></body>
</html>
''' % {"target": target, "target_json": json.dumps(target)}
    write(os.path.join(OUT, "index.html"), html)


def parse_args(argv):
    global BASE, NOINDEX, MODE, OUT, DOCS_ROOT, CNAME, TILDA_OUT, THEME
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--mode":
            i += 1
            MODE = argv[i]
            if MODE not in ("pay", "rassrochka", "pre", "predzapis", "bron", "zayavka",
                            "neudobnye"):
                sys.exit("режим бывает pay, rassrochka, pre, predzapis, bron, zayavka "
                         "или neudobnye, получено: %s" % MODE)
        elif a == "--out":
            i += 1
            OUT = os.path.join(ROOT, argv[i])
        elif a == "--base":
            i += 1
            BASE = "/" + argv[i].strip("/")
        elif a.startswith("--base="):
            BASE = "/" + a.split("=", 1)[1].strip("/")
        elif a == "--docs-root":
            DOCS_ROOT = True
        elif a == "--cname":
            i += 1
            CNAME = argv[i]
        elif a == "--tilda":
            i += 1
            TILDA_OUT = argv[i]
        elif a == "--noindex":
            NOINDEX = True
        elif a == "--theme":
            i += 1
            THEME = argv[i]
            if THEME != "more":
                sys.exit("оформление бывает только more, получено: %s" % THEME)
        else:
            sys.exit("неизвестный аргумент: %s" % a)
        i += 1


def main():
    parse_args(sys.argv[1:])
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    print("Сборка сайта → %s  (режим: %s)" % (os.path.relpath(OUT, ROOT), MODE))
    if MODE == "pre":
        build_pre_redirect()
        print("Готово. /pre перенаправляет на /zayavka с параметрами адреса")
        return
    if BASE:
        print("  подпуть: %s" % BASE)
    if NOINDEX:
        print("  индексация запрещена")
    if THEME:
        print("  оформление: %s (тестовое)" % THEME)
    copy_fonts()
    if MODE == "neudobnye":
        build_geroy_photo()
        build_avtor_photo()
        build_neudobnye()
    else:
        build_images()
        build_landing()      # заполняет HOVER_RULES
    if DOCS_ROOT:
        print("  правовые страницы не строятся: ссылки ведут в корень домена")
    else:
        build_docs()
    build_css()              # поэтому идёт после
    build_js()
    build_favicon()
    if CNAME:
        write(os.path.join(OUT, "CNAME"), CNAME + "\n")
        print("  CNAME → %s" % CNAME)
    add_cache_busting()

    if TILDA_OUT:
        build_tilda(OUT, os.path.join(ROOT, TILDA_OUT))

    total = 0
    for dirpath, _dirs, files in os.walk(OUT):
        for f in files:
            total += os.path.getsize(os.path.join(dirpath, f))
    print("Готово. Всего %.0f КБ" % (total / 1024))


if __name__ == "__main__":
    main()
