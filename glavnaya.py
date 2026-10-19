#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страница заявки violamaro.ru/zayavka/: «Прикладная эмпатия», правки от 19.10.2026.

До 19.10 эта страница была главной; главная теперь страница оплаты
(oplata.py). Ссылка из бота и мини-приложения: /zayavka/?uid=<ID в Телеграме>.

Сайт стоит внутри воронки: оплаты на нём нет, везде одна кнопка «Оставить
заявку». После заявки первой пишет Виола со второго аккаунта.

Страница собирается поверх основного сайта: сначала build.py (шрифты, фото,
стили подвала и cookie, правовые страницы), потом этот модуль переписывает
site/zayavka/index.html. Первый экран берёт из site/index.html, поэтому
идёт сразу после сборки главной и до oplata.py.

    python3 build.py --theme barhat --noindex
    python3 glavnaya.py

Первый экран — прежний первый экран сайта (Виола на арке), его разметку
даёт build.py, здесь меняются только тексты. Регалии отдельным списком
выводятся пунктами в блоке «Обо мне» и плашками на фото первого экрана.

Тексты блоков лежат ниже словарями и списками, по порядку страницы. Длинного
тире в текстах нет: сборка падает, если оно где-то появится, как и «2.0».
"""

import hashlib
import html as html_mod
import os
import re
import shutil
import sys

import build

OUT = os.path.join(build.ROOT, "site")
ASSETS = os.path.join(OUT, "assets")

# Куда уходит заявка. Это то же развёртывание скрипта таблицы, что у теста 2.0
# (таблица «Заявки | Виола Маро», лист «Заявки на продукт» — тот же, что был
# у сайта). Развёртывание из site.js застряло на версии от 17.09 и про uid
# не знает. Скрипт: integrations/google-sheets/Скрипт-таблицы-целиком.gs.
LEAD_ENDPOINT = ("https://script.google.com/macros/s/AKfycbxzJaSclK7FTBSK0X7cAIJcscvwt9qyAGSsYGCrF"
                 "HehtTvYPPEzTloDjCgsDj7v77n9jQ/exec")
FORM_SECRET = "PxlGXL9bQSjc0dHcLoiCZJZWtNdfv9D8yY9SHBuJ"   # SITE_SECRET в скрипте
VIOLA_TG = "https://t.me/violamarohelper"                    # второй аккаунт Виолы
# Номер счётчика Яндекс Метрики. 0 — счётчика нет, цели никуда не уходят.
METRIKA_ID = 0

# Плашка первого экрана. Строки идут по очереди: показывается первая, чей
# срок ещё не наступил. Последняя без срока — что показывать после старта
# (дату следующего потока уточнить у Ильи и вписать сюда).
PLASHKA = [
    ("2026-11-01T00:00:00+03:00", "Старт 1 ноября"),
    ("", "Набор на следующий поток открыт"),
]

TIMER_HOURS = 48
PRICES = {
    # тариф: (цена по заявке, обычная цена, в месяц по заявке, в месяц обычная,
    #         валюта по заявке, валюта обычная)
    "С Виолой": ("29 900", "39 900", "2 492", "3 325", "$360 / €320", "$480 / €430"),
    "Самостоятельный": ("14 900", "19 900", "1 242", "1 659", "$180 / €160", "$240 / €215"),
}

# ───────────────────────────────────────────────────────────── тексты ──

TITLE = "Прикладная эмпатия: шестинедельная программа Виолы Маро"
DESCRIPTION = ("Шесть недель с психологом Виолой Маро: учитесь пользоваться своей эмпатией, "
               "перестаёте спасать всех и терпеть тех, кто вами пользуется. Старт 1 ноября.")

HERO_SUB = "Моя 6-недельная программа для эмпатов"
# Оффер-заголовок первого экрана (правка Ильи 19.10 вместо определения
# «Это шестинедельная программа…»).
HERO_DEF = ("Научитесь вместе со мной пользоваться своей эмпатией, чтобы <b>перестать "
            "спасать всех, уступать и терпеть тех, кто вами пользуется</b>, и <b>начать себя "
            "любить, ценить и уважать</b>")

GOALS = [
    ("сразу видеть манипуляцию", " и не вестись на жалость, вину и сладкие обещания"),
    ("не попадать в токсичные отношения", " ни с партнёром, ни на работе, ни среди близких"),
    ("говорить «нет» без оправданий", " и не винить себя потом весь вечер"),
    ("не уносить с собой чужую боль:", " сочувствовать человеку, но его проблему оставлять ему"),
    ("любить, ценить и уважать себя,", " чтобы рядом были те, кто относится к вам так же"),
]

# Недели: заголовок, что даёт неделя, техники (название, что даёт), сноска.
# Техники недель 4–6 пока прежние, со старого сайта (build.WEEKS): заменить,
# когда придут файлы Виолы. У двух техник недели 3 описание ждёт её файла.
NEDELI = [
    ("Фигура эмпата",
     "Поймёте, почему так остро чувствуете людей, и перестанете считать себя странной. "
     "Научитесь возвращать внимание к себе, а не улетать в чужие эмоции",
     [("«Возврат в свой центр»", "дыхание, «Тёплое одеяло» и «Внутренний пупок». 10–15 минут "
       "в день, чтобы отделить свои чувства от чужих и вернуться в себя"),
      ("«Вижу, но не участвую»", "для моментов, когда тянет починить чужую жизнь или дать совет, "
       "о котором не просили"),
      ("«Растождествление с негативным фоном»", "чтобы отпустить обиду или человека, которого "
       "вы днями прокручиваете в голове")],
     ""),
    ("Эмпат и отношения с людьми",
     "Научитесь сразу видеть манипуляцию: жалость, вину, сладкие обещания. Будете отказывать "
     "партнёру, родным и коллегам коротко и без оправданий и быстро возвращаться в себя после "
     "тяжёлого разговора",
     [("«Карта автономии»", "увидеть, куда на самом деле уходят ваши силы, и вернуть их в свою жизнь"),
      ("«Дезактивация эмпатического крючка»", "найти, за что вас цепляют манипуляторы, и убрать этот крючок"),
      ("«Коммуникация из внутреннего центра»", "пауза в 10 секунд, твёрдое «нет» без оправданий "
       "и ответы на «ты изменилась» и «ты думаешь только о себе»"),
      ("«Шесть столпов самооценки»", "перестать зависеть от чужой похвалы и чужого недовольства")],
     ""),
    ("Эмпат-родители и эмпат-дети",
     "Останетесь рядом с мамой и взрослыми детьми и перестанете жить их жизнью. Спокойно "
     "выдержите «ты изменилась» и «ты думаешь только о себе». Поймёте, что нужно вашему "
     "чувствительному ребёнку",
     [("«Комната во внутреннем доме»", "место внутри себя, где можно отдохнуть даже посреди "
       "тяжёлого разговора"),
      ("«Право передумать»", "сказать «я передумала» после двадцати лет «да» и не оправдываться"),
      ("«Кукла»", "выйти из разговоров с близкими, которые раз за разом забирают ваши силы"),
      ("«Каталог чувств»", "научиться называть, что именно вы чувствуете"),
      ("«Интеллектуальное одиночество и магия масштаба»", ""),   # описание из файла Виолы
      ("«Диалог с миром»", "")],                                    # описание из файла Виолы
     ""),
    ("Психосоматика у эмпата",
     "Поймёте, почему тело болит за всех, а врачи ничего не находят. Научитесь замечать первые "
     "сигналы тела и возвращать с ним контакт",
     None, "Программа не заменяет обследование и лечение у врача"),
    ("Самореализация людей с повышенной чувствительностью",
     "Найдёте, где в вашей жизни вы сами, и дело, в котором не нужно ломать себя. Научитесь "
     "быть среди людей и не выгорать",
     None, ""),
    ("Психология наполненности и деньги",
     "Перестанете отдавать всё и оставаться ни с чем. Научитесь принимать решения о деньгах "
     "из спокойствия, а не из страха",
     None, ""),
]

NEDELI_POD = ("Каждую неделю лекция в записи с таймкодами, техники на конкретные ситуации, "
              "задание и PDF-конспект. Техниками можно пользоваться прямо в тот момент, когда "
              "ситуация происходит. Чат потока, доступ навсегда")

# Карточки тарифов (правка Ильи 19.10): подзаголовок крупно и что входит.
TARIFY = [
    {"name": "С Виолой", "badge": "Рекомендуем", "mest": "50 мест",
     "text": "Вся программа и мои ответы на ваши вопросы",
     "items": [
         "6 моих лекций в записи с таймкодами",
         "Прикладные техники на каждую неделю, задания и PDF-конспекты",
         "<b>Я отвечаю в формате аудио на ваши вопросы в чате потока</b>",
         "<b>Мой большой мастер-класс в финале с разбором вопросов участниц</b>",
         "Чат потока",
         "Мои аудиомедитации",
         "Запись терапевтического уикенда «Неудобные»",
         "Лекция «Любовь и деньги»",
         "Разбор фильма «Догвиль»",
         "Большой мастер-класс на узнавание себя",
         "Доступ ко всем материалам навсегда",
     ]},
    {"name": "Самостоятельный", "badge": "", "mest": "",
     "text": "Вся программа в вашем темпе",
     "items": [
         "6 моих лекций в записи с таймкодами",
         "Прикладные техники на каждую неделю, задания и PDF-конспекты",
         "Мои аудиомедитации",
         "Запись терапевтического уикенда «Неудобные»",
         "Лекция «Любовь и деньги»",
         "Разбор фильма «Догвиль»",
         "Большой мастер-класс на узнавание себя",
         "Доступ ко всем материалам навсегда",
     ]},
]
RASSROCHKA = ("Рассрочка на 3, 6 или 12 месяцев без процентов, первый платёж через месяц. "
              "Рассрочка банка доступна гражданам стран СНГ по паспорту, 18+")
POD_KNOPKOY = ("После заявки я лично напишу вам в Telegram в течение 15 минут. "
               "Если заявка придёт ночью, напишу утром")
# Подпись под кнопкой в тарифах (правка 19.10). Первая фраза — только пока
# идёт таймер: после него закреплять уже нечего.
POD_TARIFY = ('<span data-po-zayavke>Оставьте заявку, пока идёт таймер, и цена закрепится за вами. </span>'
              "Я лично напишу вам в Telegram в течение 15 минут. Если заявка придёт ночью, напишу утром")
# Панель внизу экрана: пока идёт таймер и после него.
PANEL = {
    "small": "Скидка до 10 000 ₽ сгорит через",
    "btn": "Закрепить цену",
    "posle": "Старт 1 ноября. Последний поток в этом году",
    "posle_btn": "Оставить заявку",
}

ISTORII_POD = "Участницы рассказали это сами. Имена остаются между ними и мной"
ISTORII = [
    ("Девушка, которая узнала своего партнёра в видео про нарциссов", "35–44 года",
     "«Я устала от того, что мной манипулируют в отношениях, на работе, выжимают мои силы». "
     "Смотрела ролики на YouTube о нарциссах, и «по всем показателям совпало с моим партнёром». "
     "И ещё: «Я не понимала, как я лезу к людям и навязываю им заботу»",
     "",
     "«Уже сейчас, на третьей неделе, я поняла, что перестраиваю своё поведение, не лезу к людям "
     "и занимаюсь своей жизнью. Я рассталась с партнёром-нарциссом, на работе меньше болтаю о себе, "
     "стало намного лучше». «Я уже сейчас могу не реагировать, ставить блок на чужие эмоции»"),
    ("Женщина, которая всё видела и всё равно оставалась", "45–54 года",
     "«Расставание с партнёром, он ушёл, обвинив меня в ревности. Но до этого я долго закрывала "
     "глаза на многие несовпадения его слов и поступков. Чувствовала многое, но терпела, боялась "
     "потерять, так как люблю». «Дальше так жить невозможно»",
     "Психолога раз в неделю и курсы про любовь к себе",
     "«Я поняла, откуда у меня эта неуверенность, сомнения, постоянные подозрения. Почему я, ясно "
     "видя и понимая всё, всё равно до последнего оставалась в токсичных отношениях. Я чувствую, "
     "что мои мозги встают на место, я становлюсь трезвой, сильной, уверенной»"),
    ("Девушка, которую разбудила подруга-нарцисс", "35–44 года",
     "«Сильное отличие от других людей, болезненность во взаимоотношениях, влияние манипуляторов, "
     "полное непонимание, кто я. Точка отсчёта началась, когда у меня появилась подруга-нарцисс. "
     "Здесь я проснулась»",
     "«Я ничего не пробовала, так как не понимала вообще, с чего начать»",
     "«Я уже сейчас чувствую множество изменений. Снизился индекс тревоги, спасательства, стала "
     "больше направлять фокус на свои интересы, желания, стала замечать проблемы своей семьи, "
     "а не чужих людей»"),
    ("Женщина, которая всю жизнь угождала маме", "45–54 года",
     "«Сложные отношения с матерью. Устала угождать, в ответ одни упрёки. В прошлом году сказала "
     "себе, что с меня хватит»",
     "",
     "«Я хочу быть другой. В первую очередь относиться к себе с трепетом. Любить себя. До встречи "
     "с Виолой думала, что это эгоизм». И после третьей недели: «Я просто в шоке от лекции. "
     "Вы заглянули внутрь моей жизни с токсичной матерью»"),
    ("Женщина, которая уступала и терпела", "55–64 года",
     "«Я всё время либо уступаю и терплю, либо убегаю. Люди мне могут сказать что угодно, типа они "
     "шутят, а если я скажу, обижаются. Я поняла, что всю жизнь не уважала себя. Мне очень горько "
     "и как-то безнадёжно. Мне 60 лет, глупо это всё со стороны смотрится»",
     "«Только читала книги. Всегда боялась выбрать не того специалиста, боялась, что будет ещё хуже»",
     "«Такой конкретики и реальных практичных вещей я ни у кого не слышала! Я не жила, а сейчас, "
     "кажется, начну жить»"),
]

# «О Виоле» пунктами, а не сплошным текстом (правка 19.10). Слова правки те же.
O_VIOLE_IMYA = "Меня зовут Виола Маро."
O_VIOLE_PUNKTY = [
    "Я психолог и психотерапевт, 25 лет веду частную практику в Италии на русском и итальянском",
    "Окончила факультет психологии СПбГУ и римский университет Sapienza",
    "Училась в Риме, Милане, Нью-Йорке, Париже и Сан-Паулу",
    "Выступала спикером на Специальной сессии ООН по вопросам детей и молодёжи",
    "Меня читают и смотрят 713 000 подписчиков в YouTube, TikTok и Instagram",
]
O_VIOLE = ["", "Я объясняю, почему вы так устроены, и показываю, что с этим делать"]

# Регалии на фото первого экрана (правка 19.10): одна прозрачная плашка,
# факты списком сверху вниз, одним шрифтом, важное жирным.
PLASHKI = [
    "<b>25 лет</b> практики психолога и психотерапевта",
    "<b>СПбГУ и Sapienza</b>: психологическое образование, Санкт-Петербург и Рим",
    "Спикер <b>ООН</b> на Специальной сессии по вопросам детей и молодёжи",
    "<b>713 000</b> подписчиков в YouTube, TikTok и Instagram",
]
# Цитаты участниц сверстаны, но скрыты до их согласия: показать — CITATY_VIDNY = True.
CITATY = [
    "«Виола рассказала обо мне, совсем меня не зная»",
    "«Такой конкретики и реальных практичных вещей я ни у кого не слышала»",
    "«Когда слушаешь Виолу, дыхание замирает»",
]
CITATY_VIDNY = False

OPLATA = ("Оплатить можно из любой страны картой любого банка, в рублях, долларах или евро. "
          "Для карт других стран есть отдельные способы оплаты, менеджер пришлёт нужную ссылку. "
          "Деньги принимает ИП Нижевясова А. С., официальный организатор моих программ. "
          "Вопросы по оплате в службу заботы "
          '<a href="https://t.me/violamaroteam" target="_blank" rel="noopener">@violamaroteam</a>')

DLYA_KOGO = [
    "вы всем помогаете, а когда плохо вам, рядом никого",
    "уступаете и терпите, а потом весь вечер прокручиваете разговор в голове",
    "видите, что вами пользуются, и всё равно остаётесь",
    "из одних тяжёлых отношений попадаете в другие",
    "принимаете близко к сердцу каждое слово и каждый взгляд",
    "всю жизнь чувствуете себя белой вороной",
]
DLYA_KOGO_POD = ("Характер тут ни при чём. У вас сильная эмпатия, а пользоваться ей вас "
                 "никто не учил")

KNIGI = [
    "Вы уже читали книги, ходили к психологу, проходили курсы. Становилось понятнее, но "
    "не легче. Никто не объяснил, почему вы так остро чувствуете людей и что делать в ту "
    "минуту, когда на вас давят",
    "С этого программа и начинается. Я объясняю, как вы устроены, и даю техники "
    "на ситуации, которые с вами уже происходят",
]

# «Это дорого»: последнее предложение верно только для цены по заявке,
# после таймера скрипт его убирает (data-po-zayavke).
FAQ = [
    ("А если я не эмпат, а просто очень чувствительная?",
     "Если вы всё пропускаете через себя и после общения с людьми у вас не остаётся сил, "
     "программа про вас. Как это называть, не так важно: техники работают для любого человека, "
     "который чувствует других сильнее, чем хотел бы"),
    ("Я уже читала книги и ходила к психологу. Чем это отличается?",
     "Понимания у вас уже достаточно. Не хватает действия в ту минуту, когда на вас давят. "
     "Здесь каждая техника на конкретную сцену: мама обиделась на ваш отказ, коллега сливает "
     "на вас эмоции, партнёр снова давит на жалость"),
    ("Это дорого",
     'Есть рассрочка без процентов, от <span data-g-mes="Самостоятельный">1 242</span> ₽ в месяц. '
     "Одна личная встреча со мной стоит 200 €."
     '<span data-po-zayavke> Вся программа с моими ответами на ваши вопросы по цене по заявке '
     "стоит дешевле двух таких встреч</span>"),
    ("У меня нет времени: работа, семья",
     "Одна лекция в неделю, всё в записи. Смотрите, когда удобно, хоть по 15 минут. Доступ "
     "навсегда, пропущенное догоните в любой момент"),
    ("У меня совсем нет сил",
     "Программа рассчитана на уставших: одна лекция в неделю и техники маленькими шагами, "
     "по 10–15 минут в день. Первые перемены участницы замечают уже на первой неделе"),
    ("Мне уже поздно что-то менять",
     "В программе есть участницы старше 65 лет. Менять то, как вы реагируете на людей, можно "
     "в любом возрасте"),
    ("Я боюсь стать жёсткой. Близкие скажут, что я изменилась",
     "Вы останетесь такой же доброй. Просто перестанете отдавать себя тем, кто этого не ценит. "
     "Что отвечать на «ты изменилась» и «ты думаешь только о себе», разбираем отдельно, "
     "на третьей неделе"),
    ("Я не умею формулировать вопросы и стесняюсь писать",
     "Пишите общими словами, всю историю рассказывать не нужно. Я вижу, что стоит "
     "за вопросом, и отвечаю на то, что там на самом деле"),
    ("Чем «С Виолой» отличается от «Самостоятельного»?",
     "Программа в обоих тарифах одна. На тарифе «С Виолой» вы пишете вопрос в чат потока, "
     "и я отвечаю вам голосом. Поэтому мест в нём 50"),
    ("Я живу за границей и боюсь платить онлайн",
     "Оплатить можно из любой страны. После заявки я лично пишу вам, оплату проводит "
     "менеджер @violamaroteam, после оплаты приходит чек. Если вам пишет кто-то другой "
     "и просит деньги, это не мы"),
    ("Я не успею к старту или пропущу неделю",
     "Все лекции в записи и остаются у вас навсегда. Можно начать позже и идти в своём темпе"),
    # Два вопроса с прежнего лендинга (source/Лендинг ПЭ 4.0.dc.html), без длинного тире.
    ("У меня Telegram открывается только с VPN. Я смогу участвовать?",
     "Да. Ни одна часть программы не требует быть на связи в конкретную минуту: лекции "
     "в записи, вопросы вы пишете в чат, когда вам удобно"),
    ("А если во время работы станет тяжело?",
     "Так бывает, и об этом лучше знать заранее: когда начинаешь разбирать то, что годами "
     "лежало нетронутым, какое-то время может быть неспокойно. Темп здесь ваш, никто "
     "не подгоняет. Программа не заменяет очную психотерапию: если сейчас у вас острое "
     "состояние, сначала стоит опереться на своего специалиста"),
]

SPASIBO = [
    "Спасибо, я получила вашу заявку и напишу вам в Telegram в течение 15 минут, "
    "если ночью, то утром",
    "Чтобы не ждать, можете написать мне сами",
]


# ──────────────────────────────────────────────────────────── вёрстка ──

def typograf(s):
    """Неразрывный пробел после коротких слов и чисел: предлог не остаётся
    в конце строки. Только в тексте, не в тегах."""
    def fix(text):
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r"(^|[\s«(>])([А-Яа-яЁёA-Za-z]{1,2}|\d+)[ ](?=\S)", "\\1\\2 ", text)
        return text
    parts = re.split(r"(<[^>]+>)", s)
    return "".join(p if p.startswith("<") else fix(p) for p in parts)


def h2(ink, red="", cls="", red_first=False):
    """Заголовок блока в два цвета, как на mentorstvo2025: часть чернилами,
    часть красным. Слова те же, что в правке; меняется только цвет."""
    a = '<span class="g-ink">%s</span>' % ink if ink else ""
    b = '<span class="g-acc">%s</span>' % red if red else ""
    return '<h2 class="g-h2%s">%s</h2>' % (cls, (b + " " + a) if red_first else (a + " " + b).strip())


def btn(label, blok, tarif="", cls="g-btn"):
    return ('<button type="button" class="%s" data-zayavka="%s"%s>%s</button>'
            % (cls, blok, (' data-tarif="%s"' % tarif) if tarif else "", label))


def price_html(name):
    zay, base, mz, mb, vz, vb = PRICES[name]
    return """
        <div class="g-cena" data-g-cena="%(n)s">
          <p class="g-cena-old"><s data-po-zayavke>%(base)s&nbsp;₽</s></p>
          <p class="g-cena-new"><span data-g-sum>%(zay)s</span>&nbsp;₽ <span class="g-po" data-po-zayavke>по заявке</span></p>
          <p class="g-cena-mes">или от <span data-g-mes="%(n)s">%(mz)s</span>&nbsp;₽ в месяц</p>
          <p class="g-cena-val"><s data-po-zayavke>%(vb)s</s> <span data-g-val>%(vz)s</span></p>
        </div>""" % {"n": name, "base": base, "zay": zay, "mz": mz, "vb": vb, "vz": vz}


HERO_SRC = None   # разметка прежнего первого экрана из сборки build.py


def hero_from_build():
    """Первый экран как на прежнем сайте (просьба 19.10): красная сцена,
    название, Виола на арке, карточка с определением. Разметку и стили даёт
    build.py (тема barhat), здесь меняются только тексты и кнопки по правке:
    без «2.0» и длинного тире, новое определение, плашка, «Оставить заявку»."""
    path = os.path.join(OUT, "index.html")
    page = build.read(path)
    if 'data-glavnaya="1"' in page:
        raise SystemExit("главная: site/index.html уже пересобран; сначала "
                         "python3 build.py --theme barhat --noindex")
    i = page.find('aria-label="Первый экран"')
    if i < 0 or "data-h2-title" not in page:
        raise SystemExit("главная: в сборке нет первого экрана темы barhat")
    a = page.rfind("<section", 0, i)
    blk = build.find_block(page, "section", a)
    h = page[blk[0]:blk[3]]
    # Два варианта первого экрана: data-h2 — телефон (Виола на арке),
    # data-hero-stage — широкий экран (Виола в кресле). Показывает нужный
    # сама тема; тексты меняем в обоих.
    k = h.find("<div data-hero-stage")
    sb = build.find_block(h, "div", k)
    stage = h[sb[0]:sb[3]]
    h = h[:sb[0]] + "%%STAGE%%" + h[sb[3]:]

    def sub(pattern, repl, count=1):
        nonlocal h
        h2_, n = re.subn(pattern, repl, h, count=count, flags=re.S)
        if not n:
            raise SystemExit("главная: в первом экране не найдено: " + pattern)
        h = h2_

    def btn_a(m):
        return ('<a class="%s" href="#tarify" role="button" data-zayavka="Первый экран" '
                'data-btn="primary" style="%s">Оставить заявку<span style="display: inline-flex; '
                'align-items: center; justify-content: center; width: 34px; height: 34px; '
                'border-radius: 50%%; background: rgba(140,12,30,.9); color: #F8ECCB; font-size: 16px; '
                'line-height: 1;">→</span></a>' % (m.group(1), m.group(2)))
    BTN_RE = r'<a class="(\w+)" href="#\w+" data-btn="primary"[^>]*?style="([^"]*)">.*?</a>'

    # широкий экран
    full, stage_h = h, stage
    h = stage_h
    sub(r"(<div style=\"font-size: clamp\(10px[^>]*>).*?</div>", lambda m: m.group(1) + HERO_SUB + "</div>")
    sub(r"(<h1[^>]*>).*?</h1>", lambda m: m.group(1) + "Прикладная <br>эмпатия</h1>")
    sub(r'<p style="([^"]*font-size: clamp\(23px[^"]*)">.*?</p>',
        lambda m: '<p data-hero-def="" style="%s">%s</p>' % (
            m.group(1).replace("font-size: clamp(23px, 2.4vw, 34px)", "font-size: clamp(18px, 1.6vw, 22px)")
                      .replace("line-height: 1.25", "line-height: 1.5").replace("max-width: min(60%, 760px)", "max-width: min(48vw, 560px)"),
            HERO_DEF))
    sub(r'<p style="([^"]*backdrop-filter[^"]*)">.*?</p>',
        lambda m: '<p id="plashka" style="%s">%s</p>' % (m.group(1), PLASHKA[0][1]))
    sub(BTN_RE, btn_a)
    # Метка «Старт 1 ноября» рядом с кнопкой повторяла бы плашку: убираем.
    j = h.find("Старт 1 ноября</span>")
    if j > 0:
        d = h.rfind('<div style="display: inline-flex', 0, j)
        db = build.find_block(h, "div", d)
        h = h[:db[0]] + h[db[3]:]
    # Плашки с регалиями на широком экране: столбиком справа от Виолы.
    stage_h = h.replace('<div data-hero-copy=""', plashki_html("g-fakty-stage") + '\n      <div data-hero-copy=""', 1)
    h = full
    sub(r"(<p data-h2-title[^>]*>)(.*?)</p>", lambda m: m.group(1) + "Прикладная <br>эмпатия</p>")
    sub(r"(<p data-h2-sub[^>]*>).*?</p>", lambda m: m.group(1) + HERO_SUB + "</p>")
    sub(BTN_RE, btn_a)
    sub(r"<p data-h2-name[^>]*>.*?</p>", lambda m: "")
    sub(r"<p data-h2-def[^>]*>.*?</p>", lambda m: '<p data-h2-def="" class="g-offer">%s</p>' % HERO_DEF)
    sub(r"<p data-h2-note[^>]*>.*?</p>", lambda m: "")
    # На телефоне и планшете (вариант с аркой, до 900 px) — сеткой 2 × 2 под фото.
    sub(r'(</div>)(\s*<div data-h2-card)', lambda m: plashki_html("g-fakty-h2") + m.group(1) + m.group(2))
    h = h.replace("%%STAGE%%", stage_h)
    h = h.replace('aria-label="Первый экран"', 'aria-label="Первый экран" data-blok="Первый экран"', 1)
    return h


def plashki_html(cls):
    return ('<ul class="g-fakty %s" aria-label="Регалии Виолы Маро">%s</ul>'
            % (cls, "".join("<li>%s</li>" % x for x in PLASHKI)))


# Картинка с планшетом под оффером, над «Целями программы» (правка 19.10).
# Исходник кладётся в build-assets/glavnaya/planshet.png (или .jpg/.webp);
# пока файла нет, блока на странице нет.
PLANSHET_SRC = os.path.join(build.BUILD_ASSETS, "glavnaya")
PLANSHET_ALT = "Программа «Прикладная эмпатия» на планшете: лекции, шесть недель, техники, медитации, ответы и методички"


# Левая колонка панели целей на широком экране (как «Моё менторство —»
# на mentorstvo2025). На телефоне заголовка и текста нет: оффер стоит прямо над ними.
PANEL_LEFT_H = "Прикладная эмпатия"
PANEL_LEFT_T = ("Это шестинедельная программа для эмпатов. Каждую неделю <b>одна сфера жизни</b>: "
                "мои лекции, техники, медитации и <b>мои ответы на ваши вопросы</b>")


def planshet_img():
    from PIL import Image
    src = None
    for ext in ("webp", "png", "jpg", "jpeg"):
        p = os.path.join(PLANSHET_SRC, "planshet." + ext)
        if os.path.isfile(p):
            src = p
            break
    if not src:
        return ""
    im = Image.open(src)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    out = os.path.join(ASSETS, "img")
    os.makedirs(out, exist_ok=True)
    made = []
    for w in (720, 1280):
        if w > im.width and made:
            continue
        r = im.resize((min(w, im.width), round(im.height * min(w, im.width) / im.width)), Image.LANCZOS)
        name = "planshet-%d.webp" % r.width
        r.save(os.path.join(out, name), quality=84, method=6)
        made.append((name, r.width, r.height))
    srcset = ", ".join("/assets/img/%s?v=%s %dw" % (n, file_hash(os.path.join(out, n)), w) for n, w, _h in made)
    n, w, h = made[-1]
    return """
      <div class="g-planshet">
        <img src="/assets/img/%s?v=%s" srcset="%s" sizes="(max-width: 900px) 100vw, 560px"
             alt="%s" width="%d" height="%d" loading="lazy" decoding="async">
        <p class="g-planshet-badge"><span>Старт 1 ноября</span><b>Последний поток в&nbsp;этом году</b></p>
      </div>""" % (n, file_hash(os.path.join(out, n)), srcset, PLANSHET_ALT, w, h)


def sec_goals():
    """Панель под первым экраном по схеме mentorstvo2025: на широком экране
    слева «Прикладная эмпатия —», текст и планшет с плашкой, справа цели
    с меткой в рамке и квадратными галочками. На телефоне — планшет, потом цели."""
    goals = "".join("<li><b>%s</b>%s</li>" % g for g in GOALS)
    return """
<section class="g-planshet-mob" data-blok="Планшет">
  <div class="g-in">%(img)s
  </div>
</section>
<section class="g-goals-sec" data-blok="Цели программы">
  <div class="g-in">
    <div class="g-panel">
      <div class="g-panel-l">
        <h2 class="g-h2 g-panel-lh"><span class="g-acc">%(lh)s</span></h2>
        <p class="g-panel-lt">%(lt)s</p>
        %(img)s
      </div>
      <div class="g-panel-r">
        %(gh)s
        <p class="g-label">Для каждого участника:</p>
        <ul class="g-checks g-goals">%(goals)s</ul>
        %(btn)s
      </div>
    </div>
  </div>
</section>""" % {"goals": goals, "gh": h2("программы", "Цели", red_first=True),
                 "lh": PANEL_LEFT_H, "lt": PANEL_LEFT_T, "img": planshet_img(),
                 "btn": btn("Оставить заявку", "Цели программы")}


def sec_nedeli():
    """Недели — этапами, как «Этап 1.» на mentorstvo2025: метка в рамке,
    название красным, текст, техники с квадратными галочками, линия между
    неделями."""
    cards = []
    for i, (title, text, tricks, note) in enumerate(NEDELI):
        if tricks is None:
            tricks = [(line.lstrip("— ").strip(), "") for line in
                      build.WEEKS[i]["tricks"].split("\n") if line.strip()]
            tricks = [(t[0][:1].upper() + t[0][1:], "") for t in tricks]
        # Только названия техник, без описаний и без кавычек (просьба Ильи 19.10).
        items = "".join("<li>%s</li>" % t.strip("«»") for t, _d in tricks)
        cards.append("""
    <article class="g-week">
      <p class="g-week-n">Неделя %(k)d.</p>
      <h3 class="g-week-h">%(title)s</h3>
      <p class="g-week-t">%(text)s</p>
      <div class="g-week-box">
        <p class="g-week-tr">Техники недели</p>
        <ul class="g-checks g-checks-sm">%(items)s</ul>
      </div>
      %(note)s
    </article>""" % {"k": i + 1, "title": title, "text": text, "items": items,
                     "note": ('<p class="g-week-note">%s</p>' % note) if note else ""})
    return """
<section class="g-sec g-grey" id="programma" data-blok="Как проходит программа">
  <div class="g-in">
    %s
    <div class="g-weeks">%s
    </div>
    <p class="g-weeks-pod">%s</p>
  </div>
</section>""" % (h2("Как проходит", "программа", " g-center"), "".join(cards), NEDELI_POD)


def sec_tarify():
    cards = []
    for t in TARIFY:
        top = bool(t["badge"])
        cards.append("""
    <article class="g-tarif%(cls)s">
      <div class="g-tarif-head">
        %(badge)s
        <h3 class="g-tarif-h">%(name)s</h3>
        %(mest)s
      </div>
      <p class="g-tarif-t">%(text)s</p>
      <p class="g-tarif-l">Что входит:</p>
      <ul class="g-checks g-checks-sm g-tarif-list">%(items)s</ul>
      %(price)s
      %(btn)s
    </article>""" % {"cls": " g-tarif-top" if top else "",
                     "badge": ('<span class="g-badge">%s</span>' % t["badge"]) if top else "",
                     "name": t["name"], "text": t["text"],
                     "items": "".join("<li>%s</li>" % x for x in t["items"]),
                     "mest": ('<span class="g-mest">%s</span>' % t["mest"]) if t["mest"] else "",
                     "price": price_html(t["name"]),
                     "btn": btn("Оставить заявку", "Тарифы: " + t["name"], t["name"], "g-btn g-btn-red")})
    return """
<section class="g-sec g-red" id="tarify" data-blok="Тарифы">
  <div class="g-in">
    %(h)s
    <div class="g-tarify">%(cards)s
    </div>
    <p class="g-timer" id="timer" hidden>Скидка до 10 000 ₽ сгорит через <b id="timer-v">48:00:00</b></p>
    <p class="g-rass">%(rass)s</p>
    <p class="g-pod">%(pod)s</p>
  </div>
</section>""" % {"cards": "".join(cards), "rass": RASSROCHKA, "pod": POD_TARIFY,
                 "h": h2("Тарифы", "", " g-center g-light")}


def sec_istorii():
    cards = []
    for name, age, came, tried, changed in ISTORII:
        cards.append("""
    <article class="g-story">
      <h3 class="g-story-h">%(name)s</h3>
      <p class="g-story-age">%(age)s</p>
      <p class="g-tag">С чем пришла:</p>
      <p>%(came)s</p>
      %(tried)s
      <p class="g-tag g-tag-red">Что изменилось:</p>
      <p class="g-story-ch">%(changed)s</p>
    </article>""" % {"name": name, "age": age, "came": came, "changed": changed,
                     "tried": ('<p class="g-tag">Что пробовала:</p>\n      <p>%s</p>' % tried)
                     if tried else ""})
    return """
<section class="g-sec g-grey" id="istorii" data-blok="Истории участниц">
  <div class="g-in">
    %s
    <p class="g-lead">%s</p>
    <div class="g-stories">%s
    </div>
    %s
  </div>
</section>""" % (h2("Истории участниц", "первого потока"), ISTORII_POD, "".join(cards),
                 btn("Оставить заявку", "Истории участниц"))


def sec_o_viole():
    quotes = "".join("<li>%s</li>" % q for q in CITATY)
    return """
<section class="g-sec" id="o-viole" data-blok="Обо мне">
  <div class="g-in g-about">
    <div class="g-about-foto">
      <picture>
        <source type="image/webp" srcset="/assets/img/hero-mob.webp?v=%(h1)s">
        <img src="/assets/img/hero-mob.jpg?v=%(h2)s" alt="Виола Маро" width="900" height="900" loading="lazy" decoding="async">
      </picture>
    </div>
    <div class="g-about-text">
      %(h)s
      <p class="g-about-name">%(imya)s</p>
      <ul class="g-checks g-about-list">%(p1)s</ul>
      <p class="g-accent-p">%(p2)s</p>
      <!-- Цитаты участниц: скрыты до их согласия (CITATY_VIDNY в glavnaya.py). -->
      <ul class="g-quotes"%(hid)s>%(q)s</ul>
      %(btn)s
    </div>
  </div>
</section>""" % {"p1": "".join("<li>%s</li>" % x for x in O_VIOLE_PUNKTY), "p2": O_VIOLE[1], "q": quotes, "h": h2("Обо", "мне"), "imya": O_VIOLE_IMYA,
                 "btn": btn("Оставить заявку", "Обо мне"),
                 "hid": "" if CITATY_VIDNY else " hidden",
                 "h1": file_hash(os.path.join(ASSETS, "img", "hero-mob.webp")),
                 "h2": file_hash(os.path.join(ASSETS, "img", "hero-mob.jpg"))}


def sec_text(head, body, blok, cls=""):
    return """
<section class="g-sec%s" data-blok="%s">
  <div class="g-in g-narrow">
    %s
    %s
  </div>
</section>""" % (cls, blok, head, body)


def sec_dlya_kogo():
    """Нумерованный список 01–06, как «Менторство подходит для» на mentorstvo2025."""
    items = "".join('<li><span class="g-num">%02d</span><span>%s</span></li>' % (i + 1, x)
                    for i, x in enumerate(DLYA_KOGO))
    return sec_text(h2("Программа", "для вас, если"),
                    '<ol class="g-nums">%s</ol>\n    <p class="g-accent-p g-accent-box">%s</p>'
                    % (items, DLYA_KOGO_POD),
                    "Для кого эта программа", " g-grey")


def sec_faq():
    items = "".join("""
      <details class="g-faq-i">
        <summary>%s</summary>
        <p>%s</p>
      </details>""" % qa for qa in FAQ)
    return """
<section class="g-sec" id="voprosy" data-blok="Вопросы">
  <div class="g-in g-narrow">
    %s
    <div class="g-faq">%s
    </div>
    %s
  </div>
</section>""" % (h2("", "Вопросы"), items, btn("Оставить заявку", "Вопросы"))


def form_html():
    return """
<div class="g-bar" id="g-bar" hidden>
  <div class="g-bar-l" data-bar-timer>
    <p class="g-bar-small">%(ps)s</p>
    <p class="g-bar-time" aria-live="off"><span><b id="bar-h">48</b><i>ч</i></span><em>:</em><span><b id="bar-m">00</b><i>мин</i></span><em>:</em><span><b id="bar-s">00</b><i>сек</i></span></p>
  </div>
  <p class="g-bar-posle" data-bar-posle hidden>%(pp)s</p>
  <button type="button" class="g-bar-btn" id="bar-btn">%(pb)s</button>
</div>
<div class="g-modal" id="zayavka" role="dialog" aria-modal="true" aria-labelledby="zayavka-h" hidden>
  <div class="g-modal-box">
    <button type="button" class="g-x" data-g-close aria-label="Закрыть">✕</button>
    <form class="g-form" id="zayavka-form" novalidate>
      <p class="g-modal-h" id="zayavka-h"><span class="g-ink">Заявка</span> <span class="g-acc">на программу</span></p>
      <p class="g-modal-sub">Моя программа «Прикладная эмпатия», 6 недель</p>
      <p class="g-label g-modal-tarif" id="zayavka-tarif" hidden></p>
      <label class="g-hp" aria-hidden="true">Не заполняйте это поле <input type="text" name="website" tabindex="-1" autocomplete="off"></label>
      <label class="g-f">Имя
        <input type="text" name="name" autocomplete="given-name" required>
      </label>
      <label class="g-f">Telegram или телефон
        <input type="text" name="contact" autocomplete="tel" inputmode="text" placeholder="@ник или +7…" required>
      </label>
      <label class="g-f">Что сейчас происходит и в какой сфере тяжелее всего <span class="g-opt">по желанию</span>
        <textarea name="situation" rows="3"></textarea>
      </label>
      <label class="g-cb"><input type="checkbox" name="accept_pd" required>
        <span>Я даю <a href="/consent" target="_blank" rel="noopener">согласие</a> на обработку моих персональных данных и ознакомлен(а) с <a href="/privacy" target="_blank" rel="noopener">Политикой обработки персональных данных</a>. <em>Обязательно</em></span>
      </label>
      <label class="g-cb"><input type="checkbox" name="accept_ads">
        <span>Я хочу получать письма и сообщения о программах и эфирах. Отписаться можно в один клик. <a href="/consent-ads" target="_blank" rel="noopener">Условия рассылки</a> <em>По желанию</em></span>
      </label>
      <p class="g-err" id="zayavka-err" role="alert" hidden></p>
      <button type="submit" class="g-btn g-btn-red" id="zayavka-send">Оставить заявку</button>
      <p class="g-pod-dark">%(pod)s</p>
    </form>
    <div class="g-done" id="zayavka-done" hidden>
      <p class="g-done-t">%(s1)s</p>
      <p>%(s2)s</p>
      <p class="g-done-sign">Виола</p>
      <a class="g-btn g-btn-red" id="napisat-viole" href="%(tg)s" target="_blank" rel="noopener">Написать мне в Telegram</a>
    </div>
  </div>
</div>""" % {"pod": POD_KNOPKOY, "s1": SPASIBO[0], "s2": SPASIBO[1], "tg": VIOLA_TG,
             "ps": PANEL["small"], "pp": PANEL["posle"], "pb": PANEL["btn"]}


CSS = r"""
/* Главная (glavnaya.py). Схема блоков — по mentorstvo2025 (красная сцена
   с названием, белая панель поверх неё, этапы-недели с меткой в рамке,
   нумерованный список, квадратные галочки, заголовки в два цвета),
   цвета и название программы — как на сайтах Виолы.
   Сайт уже несёт assets/site.css: шрифты, подвал, cookie. Его правила для
   main > section и main h2 сюда не дотягиваются: блоки стоят внутри .gl,
   а размеры заголовков заданы с !important. */
@font-face { font-family: 'Bebas Neue'; font-weight: 700; font-display: swap;
  src: url(/assets/fonts/BebasNeue-Bold.ttf) format('truetype'); }
body { padding-bottom: 0 !important; background: #fff; }
.gl { --red: #C4142C; --red-d: #A30F23; --ink: #1C1A1D; --soft: #55505A; --pink: #FCE9EA; --grey: #F3F2F0;
  --line: #E6E1DA; --barhat: linear-gradient(150deg, #DE1E38 0%, #C4142C 62%, #B21028 100%);
  --bebas: 'Bebas Neue', 'Arial Narrow', Impact, sans-serif;
  --card: 0 0 0 1px #E6E1DA, 0 24px 44px -30px rgba(28,26,29,.35);
  color: var(--ink); font-size: 18px; line-height: 1.6; }
.gl *, .gl *::before, .gl *::after { box-sizing: border-box; }
.gl p { margin: 0; }
.gl ul, .gl ol { margin: 0; padding: 0; list-style: none; }
.gl b { font-weight: 700; }
.g-in { max-width: 1120px; margin: 0 auto; padding: 0 18px; }
.g-narrow { max-width: 800px; }
.g-sec { padding: 60px 0; background: #fff; }
.g-grey { background: var(--grey); }
.g-red { background: var(--barhat); color: #fff; }

/* заголовки в два цвета */
.gl .g-h2, .gl .g-modal-h { font-family: var(--bebas) !important; font-weight: 700 !important; text-transform: uppercase;
  font-size: 40px !important; line-height: .98; letter-spacing: .01em; margin: 0 0 26px; text-wrap: balance; }
.gl .g-h2::first-line { color: inherit; }
.g-ink { color: var(--ink); }
.g-acc { color: var(--red); }
.g-center { text-align: center; }
.g-light .g-ink, .g-light .g-acc { color: #fff; }
.g-lead { color: var(--soft); margin: -10px 0 26px !important; }
.g-accent-p { font-weight: 700; color: var(--red-d); font-size: 20px; line-height: 1.45; margin-top: 22px !important; }
.g-accent-box { background: #fff; border-left: 5px solid var(--red); border-radius: 0 16px 16px 0; padding: 16px 18px; }

/* метка в рамке, как «Для каждого участника» и «Этап 1.» */
.g-label { display: inline-block; padding: 8px 14px; border: 2px solid var(--red); border-radius: 8px;
  color: var(--red); font-weight: 800; font-size: 15px; letter-spacing: .06em; text-transform: uppercase; line-height: 1.2; }

/* кнопки */
.g-btn { display: flex; align-items: center; justify-content: center; width: 100%; max-width: 440px;
  min-height: 64px; margin: 26px auto 0; padding: 16px 22px; border: 0; border-radius: 18px; cursor: pointer;
  font: 800 16px/1.25 'Golos Text', system-ui, sans-serif; letter-spacing: .08em; text-transform: uppercase;
  text-decoration: none; text-align: center; color: #fff; background: linear-gradient(135deg, #E2283F 0%, #B01027 100%);
  box-shadow: 0 18px 32px -14px rgba(196,20,44,.65), inset 0 1px 0 rgba(255,255,255,.25); transition: transform .15s ease, filter .15s ease; }
.g-btn:hover { filter: brightness(1.06); color: #fff; }
.g-btn:active { transform: scale(.985); }
.g-btn-white { background: #fff; color: var(--red); box-shadow: 0 18px 34px -16px rgba(0,0,0,.45); }
.g-btn-white:hover { color: var(--red); }
.g-btn:focus-visible { outline: 3px solid #1C1A1D; outline-offset: 3px; }
.g-red .g-btn:focus-visible { outline-color: #fff; }

/* квадратные галочки */
.g-checks { display: flex; flex-direction: column; gap: 16px; }
.g-checks li { position: relative; padding-left: 38px; line-height: 1.45; }
.g-checks li::before { content: ""; position: absolute; left: 0; top: .12em; width: 24px; height: 24px; border-radius: 6px;
  background: var(--red); box-shadow: 0 6px 12px -6px rgba(196,20,44,.8); }
.g-checks li::after { content: ""; position: absolute; left: 8.5px; top: calc(.12em + 4.5px); width: 6px; height: 11px;
  border: solid #fff; border-width: 0 2.5px 2.5px 0; transform: rotate(45deg); }
.g-checks li span { display: block; color: var(--soft); font-size: 16px; margin-top: 2px; }
.g-checks-sm { gap: 12px; }

/* 1. первый экран — разметка и стили сайта (build.py, тема barhat). Здесь
   только плашка старта в карточке и белая панель целей под ним. */
[data-hero-stage] [data-hero-card] p[data-hero-def] { max-width: min(46vw, 560px) !important; }
/* Регалии: одна прозрачная плашка на фото, правее центра, поверх Виолы
   ниже лица; факты списком, один шрифт, важное жирным. */
.g-fakty { position: absolute; z-index: 3; margin: 0; padding: 12px 16px; list-style: none; border-radius: 16px;
  background: rgba(255,255,255,.9); box-shadow: 0 8px 24px rgba(28,26,29,.14);
  display: flex; flex-direction: column; gap: 8px; text-align: left; pointer-events: none;
  font-family: 'Golos Text', system-ui, sans-serif; color: #1C1A1D; font-size: 14px; line-height: 1.3; font-weight: 400; }
@supports ((-webkit-backdrop-filter: blur(1px)) or (backdrop-filter: blur(1px))) {
  .g-fakty { background: rgba(255,255,255,.72); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
}
.g-fakty li { position: relative; padding-left: 14px; }
.g-fakty li::before { content: ""; position: absolute; left: 0; top: .5em; width: 6px; height: 6px; border-radius: 50%; background: #C4142C; }
.g-fakty b { font-weight: 800; color: #1C1A1D; }
/* Телефон и планшет (вариант с аркой): внизу фото, правее центра. */
.g-fakty-h2 { right: 8px; bottom: 28px; width: min(67%, 270px); font-size: 12px; line-height: 1.25; gap: 4px; padding: 9px 11px; }
.g-fakty-h2 li { padding-left: 12px; }
/* Карточка с оффером в теме наезжает на низ фото на 64 px; с плашкой — на 20. */
[data-h2] [data-h2-card] { margin-top: -20px !important; }
@media (min-width: 560px) { .g-fakty-h2 { right: calc(50% - 300px); } }
/* Широкий экран: правее Виолы, на уровне руки. */
.g-fakty-stage { right: max(24px, 3vw); bottom: 14%; width: 270px; }
.g-planshet { position: relative; margin: 0 -6px 34px; }
.g-planshet img { display: block; width: 100%; height: auto; filter: drop-shadow(0 22px 26px rgba(28,26,29,.2)); }
/* Плашка на планшете, как «Менторство проходит только раз в год»
   на mentorstvo2025: глянцевая карточка, мелкая строка и крупная. */
.g-planshet-badge { position: absolute; right: 3%; bottom: -10%; width: 40%; max-width: 190px; margin: 0;
  padding: 14px 12px 15px; border-radius: 20px; text-align: center; color: #fff;
  background: radial-gradient(120% 90% at 30% 0%, #F24A5E 0%, rgba(242,74,94,0) 60%), linear-gradient(160deg, #E2283F 0%, #B01027 100%);
  box-shadow: 0 18px 30px -12px rgba(176,16,39,.75), inset 0 1px 0 rgba(255,255,255,.45), inset 0 -2px 0 rgba(0,0,0,.12);
  display: flex; flex-direction: column; align-items: center; gap: 6px; }
.g-planshet-badge span { white-space: nowrap; font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; opacity: .9; line-height: 1.2; }
.g-planshet-badge b { font-family: var(--bebas); font-weight: 700; font-size: 22px; line-height: 1.02; letter-spacing: .02em;
  text-transform: uppercase; text-wrap: balance; }
.g-panel-lh, .g-panel-lt { display: none; }
.g-planshet-mob { background: #fff; padding: 12px 0 26px; }
.g-planshet-mob .g-planshet { margin: 0 -10px 18px; }
.g-panel-l { display: none; }
.g-about-list { margin: 4px 0 4px; }
.g-about-name { font-family: 'Prata', 'Times New Roman', Georgia, serif; font-size: 26px; line-height: 1.2; margin-bottom: 18px !important; }
[data-h2-def].g-offer { margin: 0 !important; font-size: 23px !important; line-height: 1.35 !important; font-weight: 600 !important;
  color: #1C1A1D !important; text-wrap: pretty; }
[data-h2-def].g-offer b { color: #B01027 !important; font-weight: 800 !important; }
.g-goals-sec { background: #fff; padding: 8px 0 8px; }
.g-panel { background: var(--grey); border-radius: 26px; padding: 26px 20px 28px; }
.g-panel .g-h2 { margin-bottom: 16px; }
.g-panel .g-label { margin-bottom: 20px; }

/* 2. недели этапами */
.g-weeks { display: grid; gap: 0; position: relative; }
.g-week { position: relative; padding: 0 0 34px 26px; border-left: 2px dashed rgba(196,20,44,.35); margin-left: 8px; }
.g-week:last-child { border-left-color: transparent; padding-bottom: 6px; }
.g-week::before { content: ""; position: absolute; left: -9px; top: 6px; width: 16px; height: 16px; border-radius: 50%;
  background: var(--red); box-shadow: 0 0 0 5px rgba(196,20,44,.15); }
.gl .g-week-n { display: inline-block; font-family: var(--bebas); font-size: 26px; line-height: 1; padding: 7px 12px 5px; border: 2px solid var(--red);
  border-radius: 8px; color: var(--red); letter-spacing: .02em; }
.gl .g-week-h { font-family: 'Prata', 'Times New Roman', Georgia, serif !important; font-weight: 400; color: var(--red-d); font-size: 26px !important;
  line-height: 1.2; margin: 14px 0 10px; }
.g-week-t { margin-bottom: 16px !important; }
.g-week-box { background: #fff; border-radius: 18px; padding: 18px 16px 20px; box-shadow: var(--card); }
.g-week-tr { font-family: var(--bebas); font-size: 22px; letter-spacing: .03em; color: var(--ink); margin-bottom: 12px !important; }
.g-week-note { margin-top: 12px !important; color: var(--soft); font-size: 15px; font-style: italic; }
.g-weeks-pod { margin-top: 8px !important; background: #fff; border-radius: 18px; padding: 18px; box-shadow: var(--card); font-weight: 600; }

/* 3. тарифы: шапка-плашка, как «Основная группа» и «Личная работа» */
.g-tarify { display: grid; gap: 26px; }
.g-tarify > *, .g-stories > *, .g-weeks > * { min-width: 0; }
.g-tarif { position: relative; background: #fff; color: var(--ink); border-radius: 26px; padding: 14px 14px 22px; box-shadow: 0 30px 50px -30px rgba(0,0,0,.5); }
.g-tarif-head { position: relative; border-radius: 18px; padding: 22px 16px 20px; text-align: center; background: #F6F5F3; box-shadow: inset 0 0 0 1px #E6E1DA; }
.g-tarif-top .g-tarif-head { background: var(--barhat); color: #fff; box-shadow: 0 16px 30px -18px rgba(196,20,44,.8); }
.gl .g-tarif-h { font-family: var(--bebas) !important; font-weight: 700; text-transform: uppercase; font-size: 46px !important; line-height: 1; margin: 0; color: var(--red); }
.g-tarif-top .g-tarif-h { color: #fff; }
.g-badge { display: inline-block; margin-bottom: 10px; padding: 5px 12px; border-radius: 999px; background: #1C1A1D; color: #fff;
  font-weight: 800; font-size: 12.5px; letter-spacing: .12em; text-transform: uppercase; }
.g-mest { position: absolute; right: 10px; bottom: -14px; transform: rotate(-4deg); padding: 6px 14px; border-radius: 8px; background: #fff;
  color: var(--red-d); font-weight: 800; font-size: 15px; box-shadow: 0 8px 18px -8px rgba(0,0,0,.4); }
.g-tarif-t { margin: 22px 6px 0 !important; font-size: 22px; line-height: 1.3; font-weight: 800; color: var(--ink); }
.g-tarif-l { margin: 18px 6px 12px !important; font-weight: 800; font-size: 14px; letter-spacing: .1em; text-transform: uppercase; color: var(--red); }
.g-tarif-list { margin: 0 6px !important; }
.g-tarif-list li { font-size: 17px; }
.g-cena { margin-top: 16px; padding: 16px 16px 14px; border-radius: 18px; background: var(--pink); color: var(--ink); }
.g-cena-old { font-size: 18px; color: var(--soft); min-height: 1em; }
.g-cena-new { font-family: var(--bebas); font-size: 54px; line-height: 1; color: var(--red); }
.g-po { font-family: 'Golos Text', system-ui, sans-serif; font-size: 16px; font-weight: 800; vertical-align: middle; color: var(--red-d); }
.g-cena-mes { margin-top: 6px !important; font-weight: 700; font-size: 17px; }
.g-cena-val { margin-top: 2px !important; font-size: 16px; color: var(--soft); }
.g-cena-val s { margin-right: 6px; }
.g-tarif .g-btn { margin-top: 16px; max-width: none; }
.g-timer { margin-top: 28px !important; text-align: center; font-size: 19px; }
.g-timer b { display: inline-block; font-family: var(--bebas); font-size: 34px; letter-spacing: .04em; vertical-align: -3px;
  padding: 2px 10px 0; border-radius: 8px; background: rgba(0,0,0,.2); }
.gl .g-rass { margin-top: 16px !important; text-align: center; font-size: 16px; opacity: .95; max-width: 640px; margin-left: auto; margin-right: auto; }
.gl .g-pod { margin-top: 14px !important; text-align: center; font-size: 16px; opacity: .95; max-width: 520px; margin-left: auto; margin-right: auto; }
.gl[data-istek] [data-po-zayavke] { display: none !important; }

/* 4. что ещё входит */
.g-box { background: var(--grey); border-radius: 24px; padding: 24px 18px; }
.g-checks-2 { gap: 18px; }

/* 5. истории: метки «С чем пришла» / «Что изменилось», как «До» / «После» */
.g-stories { display: grid; gap: 18px; }
.g-story { background: #fff; border-radius: 22px; padding: 22px 18px 24px; box-shadow: var(--card); }
.gl .g-story-h { font-family: var(--bebas) !important; font-weight: 700; font-size: 30px !important; line-height: 1.02; color: var(--red); margin: 0; text-transform: uppercase; }
.g-story-age { color: var(--soft); font-size: 15px; margin-top: 6px !important; }
.g-tag { display: inline-block; margin: 16px 0 8px !important; padding: 5px 10px; border-radius: 6px; border: 1.5px solid #CFC8BF;
  font-weight: 800; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); }
.g-tag-red { background: var(--red); border-color: var(--red); color: #fff; }
.g-story-ch { font-weight: 600; }

/* 6. о Виоле */
.g-about { display: grid; gap: 26px; align-items: center; }
.g-about-foto img { width: 100%; height: auto; border-radius: 24px; display: block; }
.g-about-text p + p { margin-top: 16px; }
.g-quotes { margin-top: 22px; display: grid; gap: 10px; }
.g-quotes[hidden] { display: none; }
.g-quotes li { padding: 14px 16px; border-radius: 16px; background: var(--pink); font-style: italic; }

/* 8. для кого: номера 01–06 */
.g-nums { display: grid; gap: 14px; }
.g-nums li { display: flex; gap: 14px; align-items: center; line-height: 1.4; }
.g-num { flex: none; display: flex; align-items: center; justify-content: center; width: 46px; height: 46px; border-radius: 12px;
  background: var(--barhat); color: #fff; font-family: var(--bebas); font-size: 26px; padding-top: 3px;
  box-shadow: 0 10px 18px -10px rgba(196,20,44,.9); }

/* 10. вопросы */
.g-faq { border-radius: 20px; background: #fff; box-shadow: var(--card); overflow: hidden; }
.g-faq-i { border-top: 1px solid var(--line); padding: 18px 18px; }
.g-faq-i:first-child { border-top: 0; }
.g-faq-i summary { cursor: pointer; list-style: none; position: relative; padding-right: 40px; font-weight: 700; line-height: 1.4; }
.g-faq-i summary::-webkit-details-marker { display: none; }
.g-faq-i summary::before { content: ""; position: absolute; right: 0; top: -2px; width: 28px; height: 28px; border-radius: 8px; background: var(--pink); }
.g-faq-i summary::after { content: ""; position: absolute; right: 10px; top: 5px; width: 8px; height: 8px;
  border: solid var(--red); border-width: 0 2.5px 2.5px 0; transform: rotate(45deg); transition: transform .2s ease; }
.g-faq-i[open] summary::after { transform: rotate(-135deg); top: 10px; }
.g-faq-i p { margin-top: 10px !important; color: var(--soft); }

/* панель внизу экрана: высота до 80 px плюс полоса «домой» на айфоне */
.g-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 90; display: flex; align-items: center; justify-content: space-between; gap: 12px;
  min-height: 64px; max-height: calc(80px + env(safe-area-inset-bottom, 0px));
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom, 0px)); background: var(--barhat); color: #fff;
  box-shadow: 0 -12px 30px -14px rgba(28,26,29,.55); transform: translateY(0); transition: transform .25s ease; }
.g-bar[hidden] { display: none; }
.g-bar [hidden] { display: none !important; }
.g-bar.g-bar-off { transform: translateY(110%); pointer-events: none; }
.g-bar-small { font-size: 13px; line-height: 1.2; font-weight: 600; opacity: .95; }
.g-bar-time { display: flex; align-items: flex-start; gap: 4px; margin-top: 2px !important; }
.g-bar-time span { display: flex; flex-direction: column; align-items: center; min-width: 30px; }
.g-bar-time b { font-family: var(--bebas); font-weight: 700; font-size: 28px; line-height: 1; letter-spacing: .03em; font-variant-numeric: tabular-nums; }
.g-bar-time i { font-style: normal; font-size: 10.5px; line-height: 1.1; opacity: .85; }
.g-bar-time em { font-style: normal; font-family: var(--bebas); font-size: 24px; line-height: 1.1; opacity: .8; }
.g-bar-posle { font-size: 15px; line-height: 1.3; font-weight: 700; }
.g-bar-btn { flex: none; min-height: 50px; padding: 0 16px; border: 0; border-radius: 14px; background: #fff; color: var(--red);
  font: 800 14px/1.2 'Golos Text', system-ui, sans-serif; letter-spacing: .06em; text-transform: uppercase; cursor: pointer;
  box-shadow: 0 10px 20px -10px rgba(0,0,0,.5); }
.g-bar-btn:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
body.g-has-bar { padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px)) !important; }
body.g-bar-on .cookie-bar { bottom: calc(88px + env(safe-area-inset-bottom, 0px)) !important; }
body.g-lock .g-bar { display: none; }
@media (prefers-reduced-motion: reduce) { .g-bar { transition: none; } }

/* форма */
.g-modal { position: fixed; inset: 0; z-index: 100; background: rgba(28,26,29,.6); display: flex; align-items: flex-end; justify-content: center; }
.g-modal[hidden] { display: none; }
.g-modal-box { position: relative; width: 100%; max-width: 560px; max-height: 100%; overflow-y: auto; background: #fff; color: var(--ink);
  border-radius: 24px 24px 0 0; padding: 26px 20px calc(24px + env(safe-area-inset-bottom, 0px)); font-size: 18px; line-height: 1.5; }
.g-x { position: absolute; right: 10px; top: 10px; width: 44px; height: 44px; border: 0; border-radius: 50%; background: #F3F2F0; font-size: 18px; cursor: pointer; color: var(--ink); }
.gl .g-modal-h { font-size: 40px !important; margin: 0 44px 4px 0; }
.g-modal-sub { color: var(--soft); margin-bottom: 14px !important; }
.g-modal-tarif { margin-bottom: 16px !important; }
.g-hp { position: absolute; left: -9999px; }
.g-f { display: block; font-weight: 700; margin-bottom: 14px; }
.g-f input, .g-f textarea { display: block; width: 100%; margin-top: 6px; padding: 14px 14px; border: 1.5px solid #D9D3CB; border-radius: 14px;
  font: 400 18px/1.4 'Golos Text', system-ui, sans-serif; color: var(--ink); background: #FBFAF9; }
.g-f input:focus, .g-f textarea:focus { outline: none; border-color: var(--red); background: #fff; }
.g-f .g-bad { border-color: var(--red); }
.g-opt { font-weight: 400; color: var(--soft); font-size: 15px; }
.g-cb { display: flex; gap: 12px; align-items: flex-start; font-size: 15.5px; line-height: 1.45; color: var(--soft); margin: 10px 0; cursor: pointer; }
.g-cb input { flex: none; width: 24px; height: 24px; margin: 1px 0 0; accent-color: var(--red); }
.g-cb em { font-style: normal; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: #8A5A2B; white-space: nowrap; }
.g-cb.g-bad span { color: var(--red); }
.g-err { margin-top: 12px !important; color: var(--red); font-weight: 700; }
.g-form .g-btn { max-width: none; margin-top: 18px; }
.g-pod-dark { margin-top: 12px !important; text-align: center; color: var(--soft); font-size: 15.5px; }
.g-done { padding-top: 18px; }
.g-done-t { font-size: 21px; line-height: 1.45; font-weight: 700; margin-bottom: 12px !important; }
.g-done-sign { margin-top: 14px !important; font-family: 'Prata', 'Times New Roman', Georgia, serif; font-size: 26px; color: var(--red); }
.g-done .g-btn { max-width: none; }
body.g-lock { overflow: hidden; }


/* ── Типографика и воздух (правка 19.10) ──────────────────────────────
   Три роли шрифтов и не больше: Bebas — только заголовки блоков, цены
   и метки; Golos — весь читаемый текст и заголовки карточек; Prata —
   только название программы на первом экране и имя в «Обо мне».
   Основной текст 18 px / 1.65, абзацы не жирные, жирным только смысловые
   слова. Между блоками 88 px на телефоне, внутри карточек 24 px. */
.gl { font-size: 18px; line-height: 1.65; letter-spacing: .005em; }
.g-in { padding: 0 20px; }
.g-sec { padding: 88px 0; }
.gl .g-h2, .gl .g-modal-h { font-size: 42px !important; line-height: 1.02; margin-bottom: 32px; letter-spacing: .015em; }
.g-lead { margin: -14px 0 32px !important; font-size: 17px; line-height: 1.6; }
.g-accent-p { font-size: 19px; line-height: 1.5; font-weight: 700; }
.g-checks { gap: 18px; }
.g-checks li { line-height: 1.55; padding-left: 40px; }
.g-checks li b { font-weight: 700; }
/* недели */
.g-week { padding-bottom: 52px; padding-left: 28px; }
.gl .g-week-n { font-size: 22px; padding: 6px 12px 4px; }
.gl .g-week-h { font-family: 'Golos Text', system-ui, sans-serif !important; font-weight: 800; font-size: 23px !important;
  line-height: 1.25; letter-spacing: -.01em; color: var(--ink); margin: 16px 0 12px; text-wrap: balance; }
.g-week-t { margin-bottom: 22px !important; color: #3A363C; }
.g-week-box { padding: 22px 20px 24px; border-radius: 20px; }
.g-week-tr { font-family: 'Golos Text', system-ui, sans-serif; font-size: 13px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;
  color: var(--red); margin-bottom: 16px !important; }
.g-tricks, .g-week-box .g-checks { gap: 14px; }
.g-week-box .g-checks li { font-weight: 400; font-size: 17px; line-height: 1.45; }
.g-weeks-pod { font-weight: 400; padding: 22px 20px; line-height: 1.6; margin-top: 4px !important; }
/* тарифы */
.g-tarify { gap: 36px; }
/* Шапки тарифов одной высоты: у «С Виолой» есть «Рекомендуем», у второго нет. */
.g-tarif-head { min-height: 132px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.g-tarif-head .g-badge { margin-bottom: 10px; }
.g-tarif { padding: 16px 16px 26px; }
.gl .g-tarif-h { font-size: clamp(34px, 10vw, 46px) !important; }
.g-tarif-t { font-size: 21px; line-height: 1.3; margin: 26px 6px 0 !important; }
.g-tarif-l { margin: 22px 6px 14px !important; }
.g-tarif-list li { font-size: 17px; line-height: 1.45; }
.g-cena { margin-top: 24px; padding: 20px 18px 18px; }
.g-timer { margin-top: 40px !important; }
.gl .g-rass, .gl .g-pod { line-height: 1.6; margin-top: 20px !important; }
/* истории: заголовок карточки обычным шрифтом, отзыв без жирного */
.g-stories { gap: 22px; }
.g-story { padding: 26px 22px 28px; }
.gl .g-story-h { font-family: 'Golos Text', system-ui, sans-serif !important; font-weight: 800; font-size: 21px !important; line-height: 1.3;
  text-transform: none; letter-spacing: -.01em; color: var(--ink); text-wrap: balance; }
.g-story-age { margin-top: 8px !important; }
.g-tag { margin: 22px 0 10px !important; }
.g-story p { line-height: 1.6; }
.g-story-ch { font-weight: 400; color: var(--ink); border-left: 3px solid var(--red); padding-left: 14px; }
/* обо мне, для кого, вопросы */
.g-about { gap: 36px; }
.g-about-name { margin-bottom: 24px !important; }
.g-nums { gap: 18px; }
.g-nums li { line-height: 1.5; align-items: flex-start; }
.g-num { margin-top: 2px; }
.g-accent-box { padding: 20px 22px; margin-top: 32px !important; }
.g-box { padding: 26px 22px; line-height: 1.65; }
.g-faq-i { padding: 22px 20px; }
.g-faq-i summary { line-height: 1.45; }
.g-faq-i p { margin-top: 14px !important; line-height: 1.65; }
.g-btn { margin-top: 36px; }
/* цели */
.g-goals-sec { padding-bottom: 32px; }
.g-panel { padding: 30px 22px 32px; }
.g-panel .g-label { margin-bottom: 26px; }
/* первый экран на телефоне: название не упирается в края, регалии читаются */
[data-h2-title] { font-size: clamp(36px, 10.6vw, 64px) !important; padding: 0 12px; }
.g-fakty-h2 { font-size: 13px; line-height: 1.35; gap: 7px; padding: 12px 14px; width: min(72%, 280px); }

@media (min-width: 760px) {
  .gl { font-size: 19px; }
  .gl .g-h2 { font-size: 64px !important; }
  .g-sec { padding: 92px 0; }
  /* Недели столбиком, одна неделя в строке: слева номер и название,
     справа текст и техники (просьба 19.10). */
  .g-weeks { max-width: 1000px; margin: 0 auto; }
  .g-week { display: grid; grid-template-columns: 300px 1fr; column-gap: 36px; align-items: start; padding-bottom: 40px; }
  .g-week > .g-week-n, .g-week > .g-week-h { grid-column: 1; }
  .g-week > .g-week-t, .g-week > .g-week-box, .g-week > .g-week-note { grid-column: 2; }
  .g-week > .g-week-t { grid-row: 1 / span 2; margin-top: 2px !important; }
  .g-week > .g-week-box { grid-row: 3; }
  .g-week > .g-week-note { grid-row: 4; }
  .g-weeks-pod { max-width: 1000px; margin-left: auto !important; margin-right: auto !important; }
  .g-panel { padding: 48px 52px 52px; display: grid; grid-template-columns: 1fr 1fr; column-gap: 56px; align-items: start;
    background: #fff; box-shadow: 0 30px 60px -34px rgba(28,26,29,.45), 0 0 0 1px #EEE9E3; }
  .g-planshet-mob { display: none; }
  .g-panel-l { display: block; }
  .g-panel-lh { display: block; margin-bottom: 14px !important; }
  .g-panel-lt { display: block; margin-bottom: 26px !important; font-size: 18px; line-height: 1.5; }
  .g-panel-lt b { color: var(--red-d); }
  .g-planshet { margin: 0 -10px 0 -20px; }
  .g-planshet-badge { right: 0; bottom: -4%; width: 34%; max-width: 200px; padding: 18px 14px 19px; border-radius: 22px; }
  .g-planshet-badge span { font-size: 12px; }
  .g-planshet-badge b { font-size: 26px; }
  .g-panel-r .g-btn { margin-left: 0; }
  .g-goals-sec { padding-top: 0; background: transparent; position: relative; z-index: 4; }
  .g-panel { margin-top: -56px; }
  /* Панель наезжает на низ первого экрана на 56 px: держим под кнопкой
     запас, чтобы панель её не перекрывала ни при каком размере окна. */
  [data-hero-stage] [data-hero-copy] { padding-bottom: 104px !important; }
  [data-hero-stage] { min-height: max(clamp(600px, 94vh, 960px), var(--g-hero-min, 0px)); height: auto !important; }
  .g-stories, .g-checks-2 { grid-template-columns: 1fr 1fr; display: grid; }
  .g-tarify { grid-template-columns: 1fr 1fr; align-items: start; }
  .g-about { grid-template-columns: 420px 1fr; gap: 56px; }
  .g-modal { align-items: center; }
  .g-bar { justify-content: center; gap: 32px; padding: 8px 24px; }
  .g-bar-l { display: flex; align-items: center; gap: 16px; }
  .g-bar-small { font-size: 16px; }
  .g-bar-time { margin-top: 0 !important; }
  .g-bar-time b { font-size: 32px; }
  .g-bar-posle { font-size: 18px; }
  .g-bar-btn { padding: 0 30px; }
  .g-modal-box { border-radius: 24px; max-height: 92vh; padding: 32px 30px 30px; }
}
@media (prefers-reduced-motion: reduce) { .g-btn, .g-faq-i summary::after { transition: none; } }
@media (min-width: 760px) {
  .g-sec { padding: 120px 0; }
  .gl .g-h2 { font-size: 64px !important; margin-bottom: 44px; }
  .gl .g-week-h { font-size: 26px !important; margin-top: 18px; }
  .g-week { padding-bottom: 56px; }
  .g-stories { gap: 28px; }
  .g-story { padding: 32px 30px 34px; }
  .g-tarify { gap: 32px; align-items: stretch; }
  .g-tarif-head { min-height: 150px; }
  .g-tarif { display: flex; flex-direction: column; }
  .g-tarif-list { margin-bottom: 8px !important; }
  .g-tarif .g-cena { margin-top: auto; }
  .g-faq-i { padding: 24px 28px; }
}
"""

JS = r"""
(function () {
  'use strict';
  var ENDPOINT = %(endpoint)s, SECRET = %(secret)s, METRIKA = %(metrika)s;
  var PLASHKA = %(plashka)s, PRICES = %(prices)s, HOURS = %(hours)s;
  var KEY = 'viola_pe_zayavka';
  var DOC_VERSION_CONSENT = '2026-08-10';

  /* ── аналитика: цели Метрики, если счётчик задан ── */
  var goalsQueue = [];
  function goal(name, params) {
    if (!METRIKA) return;
    if (window.ym) { try { window.ym(METRIKA, 'reachGoal', name, params || {}); } catch (e) {} }
    else goalsQueue.push([name, params]);
  }
  function initMetrika() {
    if (!METRIKA || window.ym) return;
    (function (m, e, t, r, i, k, a) { m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
      m[i].l = 1 * new Date(); k = e.createElement(t), a = e.getElementsByTagName(t)[0]; k.async = 1; k.src = r;
      a.parentNode.insertBefore(k, a); })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
    window.ym(METRIKA, 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true });
    goalsQueue.forEach(function (g) { window.ym(METRIKA, 'reachGoal', g[0], g[1] || {}); });
    goalsQueue = [];
  }
  /* Метрика стартует только после согласия на cookie. */
  (function () {
    var bar = document.getElementById('cookie-bar');
    var ok = null;
    try { ok = localStorage.getItem('cookie_ok'); } catch (e) {}
    if (ok) { initMetrika(); return; }
    if (!bar) return;
    bar.hidden = false;
    document.getElementById('cookie-ok').addEventListener('click', function () {
      try { localStorage.setItem('cookie_ok', new Date().toISOString()); } catch (e) {}
      bar.hidden = true;
      initMetrika();
    });
  })();

  /* ── плашка старта ── */
  (function () {
    var el = document.getElementById('plashka'), now = Date.now();
    if (!el) return;
    for (var i = 0; i < PLASHKA.length; i++) {
      if (!PLASHKA[i][0] || now < Date.parse(PLASHKA[i][0])) { el.textContent = PLASHKA[i][1]; return; }
    }
  })();

  /* ── uid из бота или мини-приложения: ?uid=<ID в Телеграме> ── */
  var uid = '';
  try { uid = (new URLSearchParams(location.search).get('uid') || '').replace(/[^0-9]/g, '').slice(0, 20); } catch (e) {}

  /* ── личный таймер цены по заявке: 48 часов от первого захода ── */
  var st = null, storage = true;
  try {
    st = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (!st || !st.deadline) {
      var first = Date.now();
      st = { first: first, deadline: first + HOURS * 3600e3, uid: uid, sent: '' };
    }
    if (uid && !st.uid) st.uid = uid;
    localStorage.setItem(KEY, JSON.stringify(st));
    if (JSON.parse(localStorage.getItem(KEY)).deadline !== st.deadline) throw 0;
  } catch (e) { storage = false; st = null; }
  if (!uid && st && st.uid) uid = st.uid;

  goal(uid ? 'zahod_uid' : 'zahod_bez_uid');

  /* Заход с uid — в таблицу: Даша видит, до какого времени у человека цена по заявке. */
  if (uid && st && st.sent !== uid) {
    send({ form: 'визит', secret: SECRET, uid: uid, first: new Date(st.first).toISOString(),
           deadline: new Date(st.deadline).toISOString(), page: location.href }, function () {
      try { st.sent = uid; localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {}
    });
  }

  var timerP = document.getElementById('timer'), timerV = document.getElementById('timer-v');
  var expired = false;
  function two(n) { return (n < 10 ? '0' : '') + n; }
  function setPrices(isExpired) {
    expired = isExpired;
    var root = document.querySelector('.gl');
    if (isExpired) root.setAttribute('data-istek', ''); else root.removeAttribute('data-istek');
    Object.keys(PRICES).forEach(function (name) {
      var p = PRICES[name], box = document.querySelector('[data-g-cena="' + name + '"]');
      if (box) {
        box.querySelector('[data-g-sum]').textContent = isExpired ? p[1] : p[0];
        box.querySelector('[data-g-val]').textContent = isExpired ? p[5] : p[4];
      }
      Array.prototype.forEach.call(document.querySelectorAll('[data-g-mes="' + name + '"]'), function (el) {
        el.textContent = isExpired ? p[3] : p[2];
      });
    });
  }
  /* ── панель внизу экрана (правка 19.10) ──
     Пока идёт таймер: «Скидка до 10 000 ₽ сгорит через ч : мин : сек»
     и «Закрепить цену». Таймер вышел (или его нет без localStorage):
     «Старт 1 ноября…» и «Оставить заявку». Кнопка ведёт к выбору тарифа.
     Видна, когда кнопка первого экрана ушла вверх; прячется, пока на экране
     блок тарифов (там свой таймер) и пока открыта форма. */
  var bar = document.getElementById('g-bar');
  var barH = document.getElementById('bar-h'), barM = document.getElementById('bar-m'), barS = document.getElementById('bar-s');
  function barMode(timer) {
    bar.querySelector('[data-bar-timer]').hidden = !timer;
    bar.querySelector('[data-bar-posle]').hidden = timer;
    document.getElementById('bar-btn').textContent = timer ? %(pb)s : %(pa)s;
  }
  (function () {
    var heroBtn = [].filter.call(document.querySelectorAll('section[aria-label="Первый экран"] [data-zayavka]'),
      function (b) { return b.offsetParent; })[0];
    var tar = document.getElementById('tarify');
    var past = false, inTar = false;
    function paint() {
      var on = past && !inTar;
      bar.classList.toggle('g-bar-off', !on);
      document.body.classList.toggle('g-bar-on', on);
    }
    bar.hidden = false;
    document.body.classList.add('g-has-bar');
    if (!('IntersectionObserver' in window) || !heroBtn) { past = true; paint(); return; }
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { past = !e.isIntersecting && e.boundingClientRect.bottom <= 0; }); paint();
    }).observe(heroBtn);
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { inTar = e.isIntersecting; }); paint();
    }).observe(tar);
    paint();
  })();
  document.getElementById('bar-btn').addEventListener('click', function () {
    goal('knopka_paneli');
    document.getElementById('tarify').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  barMode(!!(storage && st && st.deadline > Date.now()));

  function tick() {
    if (!st) return;
    var left = st.deadline - Date.now();
    if (left <= 0) { timerP.hidden = true; barMode(false); if (!expired) setPrices(true); return true; }
    var s = Math.floor(left / 1000);
    var h = two(Math.floor(s / 3600)), m = two(Math.floor(s %% 3600 / 60)), c = two(s %% 60);
    timerV.textContent = h + ':' + m + ':' + c;
    barH.textContent = h; barM.textContent = m; barS.textContent = c;
    timerP.hidden = false;
  }
  if (storage && st) {
    if (!tick()) { var iv = setInterval(function () { if (tick()) clearInterval(iv); }, 1000); }
  }
  /* localStorage недоступен — цены по заявке без таймера (так страница и свёрстана). */

  function seenPrice(tarif) {
    var names = tarif ? [tarif] : Object.keys(PRICES);
    return names.map(function (n) {
      var p = PRICES[n];
      return n + ': ' + (expired ? p[1] + ' ₽' : p[0] + ' ₽ по заявке');
    }).join('; ');
  }

  /* ── отправка: POST text/plain, как у формы сайта (без OPTIONS). Apps Script
     отвечает редиректом; доходим до него и считаем запись сделанной. ── */
  function send(payload, done, fail) {
    if (!ENDPOINT || !window.fetch) { if (fail) fail(); return; }
    var req = fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(payload), redirect: 'manual', keepalive: true })
      .then(function (res) { if (res.type !== 'opaqueredirect' && !res.ok) throw new Error('HTTP ' + res.status); });
    var slow = new Promise(function (r) { setTimeout(r, 1500); });
    Promise.race([req, slow]).then(function () { if (done) done(); }, function () { if (fail) fail(); });
  }

  /* ── форма заявки ── */
  var modal = document.getElementById('zayavka'), form = document.getElementById('zayavka-form');
  var doneBox = document.getElementById('zayavka-done'), errP = document.getElementById('zayavka-err');
  var tarifP = document.getElementById('zayavka-tarif'), sendBtn = document.getElementById('zayavka-send');
  var curTarif = '', curBlok = '', lastFocus = null;

  function open(tarif, blok) {
    curTarif = tarif || ''; curBlok = blok || '';
    tarifP.hidden = !curTarif;
    tarifP.textContent = curTarif ? 'Тариф «' + curTarif + '»' : '';
    lastFocus = document.activeElement;
    modal.hidden = false;
    document.body.classList.add('g-lock');
    var first = form.hidden ? doneBox.querySelector('a') : form.querySelector('[name="name"]');
    setTimeout(function () { try { first.focus(); } catch (e) {} }, 30);
  }
  function close() {
    modal.hidden = true;
    document.body.classList.remove('g-lock');
    if (lastFocus) try { lastFocus.focus(); } catch (e) {}
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-zayavka]'), function (b) {
    /* Форму открывают только кнопки в карточках тарифов (с data-tarif).
       Остальные «Оставить заявку» ведут к выбору тарифа (правка 19.10). */
    b.addEventListener('click', function (e) {
      if (b.tagName === 'A') e.preventDefault();
      goal('knopka_zayavki', { blok: b.getAttribute('data-zayavka') });
      if (b.getAttribute('data-tarif')) open(b.getAttribute('data-tarif'), b.getAttribute('data-zayavka'));
      else document.getElementById('tarify').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  Array.prototype.forEach.call(modal.querySelectorAll('[data-g-close]'), function (b) { b.addEventListener('click', close); });
  modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modal.hidden) close(); });
  document.getElementById('napisat-viole').addEventListener('click', function () { goal('napisat_viole'); });

  function bad(msg, el) {
    errP.textContent = msg; errP.hidden = false;
    if (el) { el.classList.add('g-bad'); try { el.focus(); } catch (e) {} }
  }
  Array.prototype.forEach.call(form.querySelectorAll('input, textarea'), function (el) {
    el.addEventListener('input', function () { el.classList.remove('g-bad'); errP.hidden = true; });
    el.addEventListener('change', function () { var l = el.closest('.g-cb'); if (l) l.classList.remove('g-bad'); errP.hidden = true; });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements;
    var name = f.name.value.trim(), contact = f.contact.value.trim();
    if (!name) return bad('Напишите, как вас зовут.', f.name);
    if (contact.replace(/[^0-9A-Za-zА-Яа-я]/g, '').length < 3) return bad('Оставьте Telegram или телефон, чтобы я могла вам написать.', f.contact);
    if (!f.accept_pd.checked) { f.accept_pd.closest('.g-cb').classList.add('g-bad'); return bad('Отметьте согласие на обработку персональных данных.', f.accept_pd); }

    /* Одно поле на контакт: цифры без букв — телефон, иначе Telegram. */
    var isPhone = /^[+\d\s()\-]{7,}$/.test(contact);
    var payload = {
      secret: SECRET, website: f.website.value, form: 'заявка',
      name: name, phone: isPhone ? contact : '', telegram: isPhone ? '' : contact,
      readiness: 'Заявка с главной, без оплаты', plan: curTarif,
      situation: f.situation.value.trim(),
      uid: uid, deadline: st ? new Date(st.deadline).toISOString() : '',
      price: seenPrice(curTarif), blok: curBlok,
      accept_pd: true, accept_ads: !!f.accept_ads.checked,
      consent_ts: new Date().toISOString(), doc_version_consent: DOC_VERSION_CONSENT,
      page: location.href, ua: navigator.userAgent, referrer: document.referrer || ''
    };
    try {
      var q = new URLSearchParams(location.search);
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'src'].forEach(function (k) { payload[k] = q.get(k) || ''; });
    } catch (err) {}

    sendBtn.disabled = true; sendBtn.textContent = 'Отправляю…'; errP.hidden = true;
    send(payload, function () {
      goal('zayavka_otpravlena', { blok: curBlok, tarif: curTarif });
      form.hidden = true; doneBox.hidden = false;
      try { doneBox.querySelector('a').focus(); } catch (err) {}
    }, function () {
      sendBtn.disabled = false; sendBtn.textContent = 'Оставить заявку';
      errP.innerHTML = 'Не получилось отправить заявку. Попробуйте ещё раз или напишите мне: '
        + '<a href="%(viola)s" target="_blank" rel="noopener">@violamarohelper</a>';
      errP.hidden = false;
    });
  });
})();
"""


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def page():
    import json
    hero = hero_from_build()
    body = "".join([
        sec_goals(), sec_nedeli(), sec_tarify(), sec_istorii(), sec_o_viole(),
        sec_text(h2("Оплата", "из другой страны"), '<div class="g-box"><p>%s</p></div>' % OPLATA,
                 "Оплата из другой страны"),
        sec_dlya_kogo(),
        sec_text(h2("Почему не помогли", "книги и психологи"),
                 "".join("<p%s>%s</p>" % (' class="g-p2"' if i else "", t) for i, t in enumerate(KNIGI)),
                 "Почему не помогли книги и психологи"),
        sec_faq(),
    ])
    body = typograf(body)
    form = typograf(form_html())
    css_v = file_hash(os.path.join(ASSETS, "site.css"))
    head = build.head(TITLE, DESCRIPTION, "/assets/site.css?v=%s" % css_v,
                      '<link rel="canonical" href="https://violamaro.ru/zayavka/">\n'
                      '<style>%s</style>\n' % (CSS + ".g-p2 { margin-top: 16px !important; }"))
    js = JS % {
        "endpoint": json.dumps(LEAD_ENDPOINT), "secret": json.dumps(FORM_SECRET),
        "metrika": int(METRIKA_ID), "plashka": json.dumps(PLASHKA, ensure_ascii=False),
        "prices": json.dumps(PRICES, ensure_ascii=False), "hours": TIMER_HOURS, "viola": VIOLA_TG,
        "pb": json.dumps(PANEL["btn"], ensure_ascii=False), "pa": json.dumps(PANEL["posle_btn"], ensure_ascii=False),
    }
    out = (head
           + '<main id="main" data-glavnaya="1">' + typograf(hero) + '<div class="gl">' + body + form + "</div></main>\n"
           + build.footer_html() + build.COOKIE_HTML
           + "<script>%s</script>\n</body>\n</html>\n" % js)
    return out


def check(text):
    """Ни длинного тире, ни «2.0», ни кнопок оплаты на странице."""
    visible = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text)
    problems = []
    if "—" in visible or "&mdash;" in visible:
        problems.append("длинное тире: " + ", ".join(
            sorted(set(re.findall(r".{0,30}—.{0,30}", visible)))[:5]))
    if "2.0" in visible:
        problems.append("«2.0»: " + ", ".join(set(re.findall(r".{0,30}2\.0.{0,10}", visible))))
    for word in ("Полная оплата", "Оформить рассрочку", "Перейти к оплате", "Принять участие"):
        if word in visible:
            problems.append("на странице есть «%s»" % word)
    if problems:
        raise SystemExit("главная: " + "; ".join(problems))


def main():
    if not os.path.isfile(os.path.join(ASSETS, "site.css")):
        raise SystemExit("главная: сначала соберите сайт: python3 build.py --theme barhat --noindex")
    text = page()
    check(text)
    if "--noindex" in sys.argv or build.NOINDEX:
        text = text.replace("<head>\n", '<head>\n<meta name="robots" content="noindex, nofollow">\n', 1)
    dest = os.path.join(OUT, "zayavka")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)
    print("Заявка → site/zayavka/index.html (%d КБ)" % (len(text.encode("utf-8")) // 1024))


if __name__ == "__main__":
    main()
