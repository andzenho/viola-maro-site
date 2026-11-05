#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страница клуба «Опора» violamaro.ru/opora/: подписка на закрытый клуб
Виолы Маро в Телеграме. ТЗ от 04.11.2026, тексты из
Страницы-к-публикации/opora-teksty.md (раздел «Тексты сайта по экранам»).

Страница собирается поверх основного сайта: сначала build.py (шрифты Golos
и Prata, стили подвала и cookie в /assets/site.css), потом этот модуль
пишет site/opora/ и больше ничего в site/ не трогает.

    python3 build.py --theme barhat --noindex
    python3 glavnaya.py --noindex
    python3 opora.py --noindex

Оформление клуба своё (изумруд, бархат, бордо, тонкое золото) и лежит
отдельно в build-assets/opora/opora.css, другие страницы его не видят.
Картинки кладутся в build-assets/opora/ под именами из IMG ниже, сборка
сама сжимает их в webp. Нет картинки, значит на её месте блок цвета --panel.

Форм, счётчиков и внешних запросов на странице нет: кнопки обычные ссылки
на бота из SSYLKI. Тексты переносятся слово в слово, сборка сверяет их
с файлом текстов и падает, если чего-то не нашла, а также на длинном тире
и «2.0».
"""

import hashlib
import html as html_mod
import os
import re
import shutil
import sys

import build
from glavnaya import typograf, nbsp_tail

# ════════════════════════════════════════════════════════════ конфиг ══
NABOR_OTKRYT = True          # True: кнопки тарифов, False: лист ожидания
MEST_VSEGO = 50              # мест в текущем окне
MEST_OSTALOS = 50            # меняем руками коммитом
NABOR_DO = "12 ноября"       # дата закрытия окна
SLED_NABOR = ""              # дата следующего набора, для закрытого состояния
PERVAYA_VSTRECHA = "17 ноября"
CENY = {"1m": "4 990 ₽", "3m": "11 990 ₽"}
CENY_EUR = {"1m": "", "3m": ""}            # пусто, значит евро не показываем
SSYLKI = {"1m": "", "3m": "", "list": ""}  # куда ведут кнопки
OFERTA = ""                  # оферта клуба, пока её нет
VIDEO = ""                   # видео на 8 минут, пусто, значит блок без видео
# ═══════════════════════════════════════════════════════════════════════

OUT = os.path.join(build.ROOT, "site")
DEST = os.path.join(OUT, "opora")
SRC = os.path.join(build.BUILD_ASSETS, "opora")
TEKSTY = os.path.join(build.LEGAL, "opora-teksty.md")

WARN = []


def otkryt():
    """Набор открыт, только если он открыт в конфиге и места остались."""
    return NABOR_OTKRYT and MEST_OSTALOS > 0


def mest(n):
    """«мест» по числу: 1 место, 2 места, 5 мест, 21 место."""
    if n % 10 == 1 and n % 100 != 11:
        return "место"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "места"
    return "мест"


# ──────────────────────────────────────────────────────────── тексты ──
# Слово в слово из opora-teksty.md.

TITLE = "Опора: закрытый клуб психолога Виолы Маро"

# 1. Первый экран (правки Артёма 04.11.2026, форма как у менторства Пырикова).
HERO_NAD = "закрытый клуб Виолы Маро"                # мелко над словом ОПОРА
HERO_NAZVANIE = "ОПОРА"
# Две плашки сверху, как «Старт: / 14 апреля» у Пырикова: подпись и дата жирным.
PLASHKA_START = "Старт:"                 # дата — PERVAYA_VSTRECHA
PLASHKA_NABOR = "Набор до:"              # дата — NABOR_DO, пока набор открыт
# Набор закрыт: вторая плашка «Следующий набор: <SLED_NABOR>», без даты «Набор: закрыт».
PLASHKA_SLED = ("Следующий набор:", "Набор:", "закрыт")
BTN_KLUB = "Подписаться за %s"          # цена из CENY["1m"] (Артём 05.11.2026)
BTN_LIST = "Встать в лист ожидания"
POD_OTKRYT = "Осталось %(n)d %(mest)s из %(vsego)d"
POD_POLNYY = "В первом наборе %(vsego)d %(mest)s"   # пока не продано ни одного места (MEST_OSTALOS == MEST_VSEGO)
POD_ZAKRYT = "Набор закрыт, следующий откроется %(sled)s, и участники из листа ожидания узнают о нём первыми"

# 1.1. Блок «ОПОРА –»: светлая панель наезжает на низ фото. Слева
# определение, справа задачи с галочками.
HERO_H = ("ОПОРА – это закрытое пространство в Телеграме для чувствительных людей, которые вместе учатся "
          "ценить себя и жить свою жизнь, а не только жизнь других")
HERO_AKCENT = "ценить себя и жить свою жизнь, а не только жизнь других"   # жирным, --wine
DESCRIPTION = HERO_H
ZADACHI_H = "ЗАДАЧИ КЛУБА"
ZADACHI_METKA = "ДЛЯ КАЖДОГО УЧАСТНИКА:"
CELI = [   # часть до первой запятой выводится жирным
    "Понять, почему вы так остро чувствуете людей, и перестать считать себя странной",
    "Научиться отказывать без чувства вины и замечать, когда вашей добротой пользуются",
    "Перестать прокручивать разговоры в голове и за 10–15 минут возвращать себе силы после тяжёлого общения",
    "Оставаться собой рядом с партнёром и близкими, а не растворяться в них",
    "Каждый месяц разбирать одну сферу жизни, где уходят силы, и не оставаться с этим одной",
]

# 2. Отзывы: «Что изменилось у участниц программ» (тексты Артёма 05.11.2026).
# Слова участниц без внешних кавычек; внутренние, где она цитирует себя,
# оставлены. Карточка: номер, сфера, крупная фраза, «было» → «стало».
OTZYVY_H = "ЧТО ИЗМЕНИЛОСЬ У УЧАСТНИКОВ ПРОГРАММ"
OTZYVY_POD = "Их слова без изменений. Имена скрыты"
OTZYVY = [   # (сфера, фраза, было, стало)
    ("Своя ценность", "Это я сильная!",
     "Раньше даже в голову не приходило, что можно сказать себе «Я выбираю себя» или спросить себя "
     "«А где здесь я?»",
     "Очень приятно говорить «нет» без объяснения причины, когда действительно хочется и нужно "
     "сказать «нет»"),
    ("Отношения", "За 3 месяца я «вернула себя себе»!",
     "Бывший муж махровый манипулятор…",
     "…но сейчас общение лучше, чем было в браке. Свекровь ждёт в гости!"),
    ("После тяжёлых отношений", "Помолодела на 20 лет",
     "У меня были очень сложные отношения с нарциссом после чего не верила в себя, считала что со мной "
     "уже ничего хорошего не произойдёт",
     "Я не боюсь больше жить, я сижу за рулём своей собственной жизни… мне кажется я помолодела "
     "на 20 лет"),
    ("Семья", "Живу не их жизнью, а своей",
     "Раньше мне казалось, что когда я среди людей, мои проблемы решаются благодаря окружению",
     "Дети, внуки, я теперь живу не их жизнью, а своей! И я вдруг поняла, что я сама себе нужна!"),
    ("Понять себя", "Я не сумасшедшая",
     "Я теряла и глушила свою интуицию и свой голос годами и пыталась подстроиться к людям что меня "
     "окружают",
     "Я не сумасшедшая, как мне мой собственный муж внушал очень много лет. И да я очень "
     "чувствительная но это не диагноз и не приговор"),
    ("Чувствительность", "Как будто я паровоз, который отцепил старые вагоны",
     "Раньше я стыдилась своей чувствительности. Жизнь была как ад без чёрта",
     "А теперь я чувствую себя нормальной и буду дальше развивать свою эмпатию и креативность"),
]
OTZYVY_METKI = ("было", "стало")

# 3. Для кого (правка Артёма 04.11.2026, форма как «Менторство подходит для:»
# у Пырикова): номера 01–06, жирным выделена боль, справа на компьютере Виола.
DLYA_KOGO_H = "ОПОРА ПОДХОДИТ ВАМ, ЕСЛИ ВЫ"
DLYA_KOGO = [   # (обычным, жирным)
    ("Живёте для других и всем помогаете, ", "а когда плохо вам, рядом никого"),
    ("Уступаете и терпите, ", "а потом весь вечер прокручиваете разговор в голове"),
    ("Видите, что вашей добротой пользуются, ", "и всё равно остаётесь"),
    ("Принимаете всё близко к сердцу ", "и после чужих жалоб и плохих новостей чувствуете себя выжатой"),
    ("Всё понимаете в теории, читали книги и ходили к психологу, ", "а в жизни снова уступаете"),
    ("Проходили программы Виолы и хотите идти дальше: ",
     "снова приходить к ней со своими вопросами и не терять то, что уже получилось"),
]
DLYA_KOGO_POD = ("У вас сильная эмпатия, а пользоваться ей вас никто не учил. В клубе я учу этому "
                 "по одной сфере жизни в месяц")

# 4. Что изменится
IZMENITSYA_H = "Что изменится"
IZMENITSYA = [
    ("Отказывать без вины",
     "Вы отказываете близким и коллегам коротко и спокойно, без долгих оправданий, и потом "
     "не прокручиваете разговор весь вечер"),
    ("Не впитывать чужую тревогу",
     "Когда вокруг паника, вы держитесь за себя, а после тяжёлого разговора или плохих новостей "
     "за 10–15 минут возвращаете себе силы"),
    ("Видеть давление",
     "Вы замечаете, когда на вас давят жалостью или виной, и отвечаете спокойно, без крика "
     "и без молчания"),
    ("Понять себя",
     "Вы понимаете, почему так остро чувствуете людей, и перестаёте считать себя странной"),
]
IZMENITSYA_POD = "Как это происходит, показываю ниже"

# 5. Что такое «Опора»
CHTO_H = "Что такое «Опора»"
VIDEO_PODPIS = "Фрагмент моей встречи, 8 минут"
CHTO_TEXT = ("Закрытый клуб в Телеграме, где каждый месяц я разбираю с участниками одну сферу "
             "жизни и даю техники на ситуации, которые с вами уже происходят")
SFERY = ["Своя опора", "Партнёр и отношения", "Деньги", "Мама", "Дети", "Работа"]

# 6. Как проходит месяц в клубе
MESYAC_H = "Расписание клуба"   # Артём 05.11.2026, было «Как проходит месяц в клубе»
SHAGI = [
    ("Встреча по теме месяца",
     "Я объясняю, почему в этой сфере у вас уходят силы, и даю технику на конкретные ситуации. "
     "После встречи вы знаете, что делать, когда это случится в следующий раз"),
    ("Практика",
     "Между встречами вы пробуете технику в своей жизни по 10–15 минут в день и замечаете, "
     "что после разговоров остаётся больше сил"),
    ("Ответы на вопросы",
     "Раз в неделю я голосом отвечаю на самые частые вопросы участников, и многие слышат в этих "
     "ответах свою ситуацию"),
    ("Кинотерапия",
     "Раз в месяц вы смотрите фильм по теме месяца, а потом я разбираю его с вами на встрече, "
     "потому что на чужой истории проще увидеть свою"),
]
RABOTAET_H = "Почему это работает"
RABOTAET = [
    ("Одна сфера за раз",
     "Всю жизнь сразу менять не нужно, за месяц вы успеваете попробовать технику в настоящих "
     "разговорах"),
    ("Маленькие шаги",
     "Клуб рассчитан на уставших, поэтому техники короткие, а встреч две в месяц"),
    ("Вы не одна",
     "В чате участников люди с похожими историями, и рядом с ними легче"),
    ("Проверено на людях",
     "Эти техники я даю в своей практике, и участники «Прикладной эмпатии» замечали первые "
     "перемены уже на первой неделе"),
]

# 7. Первые три месяца
TRI_H = "Что изменится за первые три месяца"
TRI_POD = "Темы я выбрала по тому, о чём мне чаще всего пишут"
TRI = [
    ("Своя опора",
     "Вы замечаете, где отдаёте себя по привычке, и начинаете отказывать без долгих оправданий. "
     "Чужая тревога и плохие новости выбивают вас меньше, потому что вы знаете, как за 10–15 "
     "минут вернуть себе силы"),
    ("Партнёр и отношения",
     "Вы видите, где вас держат жалостью или виной, и рядом с партнёром остаётесь собой. Его плохое "
     "настроение перестаёт становиться вашим"),
    ("Деньги",
     "Вы принимаете решения о деньгах спокойно, без страха, и перестаёте работать больше, чем "
     "вам платят"),
]
TRI_NIZ = ("Дальше каждый месяц новая сфера, а записи всех встреч остаются у вас, пока вы "
           "в клубе")

# 8. Что входит: экран «Каждый месяц вы получаете» (ТЗ Артёма 04.11.2026):
# светлый фон, семь карточек с золотой обводкой, на компьютере 3 + 3 и чат
# во всю ширину. Стоит сразу после «Опора подходит вам». Подарок «В день
# вступления» остался на прежнем месте отдельным экраном.
POLUCHAETE_H = "КАЖДЫЙ МЕСЯЦ ВЫ ПОЛУЧАЕТЕ"
POLUCHAETE = [   # (название, описание)
    ("2 онлайн-встречи с Виолой",
     "Глубокий разбор темы месяца и ответы на ваши вопросы. В открытом доступе Виола таких встреч "
     "больше не проводит"),
    ("Подкасты", "Голосовые ответы Виолы раз в неделю на самые частые вопросы участников"),
    ("Видео-лекция", "Лекция Виолы по теме месяца в записи, с таймкодами"),
    ("Статьи", "Отдельные материалы Виолы по теме месяца, к которым можно вернуться и перечитать"),
    ("Техники и практические задания",
     "3–4 техники на конкретные ситуации, по 10–15 минут, и задания, чтобы попробовать их в своей жизни"),
    ("Фильм-терапия",
     "Виола выбирает фильм по теме месяца, вы смотрите его сами, а на одной из встреч она разбирает "
     "его вместе с вами"),
    ("Чат сообщества", "Закрытый чат эмпатов со всего мира, за порядком в нём следит команда Виолы"),
]
POLUCHAETE_POD = "Всё это лежит только в закрытом клубе, в открытом доступе этого нет"
POLUCHAETE_IKONKI = ["o-klyuchi", "o-mikrofon", "o-proektor", "o-tetrad", "o-chasy", "o-kino", "o-pismo"]
PODARKI_H = "В день вступления вас уже ждут"
PODARKI = [
    "Техника, которая за 10–15 минут помогает вернуть себе силы после тяжёлого разговора",
    "Мой разбор фильма «Догвиль»",
]

# 9. Почему это удобно
UDOBNO_H = "Почему это удобно"
UDOBNO = [
    ("Всё в Телеграме",
     "Клуб открывается там же, где вы переписываетесь с близкими, ничего устанавливать не нужно"),
    ("Всё в записи",
     "Если вы работаете или ухаживаете за родителями, смотрите встречи, когда удобно, хоть "
     "по 15 минут"),
    ("Никто не подгоняет",
     "Домашних заданий на проверку нет, техники вы пробуете в своей жизни в своём темпе"),
    ("Работает и с VPN",
     "Ни одна часть клуба не требует быть на связи в конкретную минуту"),
]

# 10. Кто ведёт клуб
VIOLA_H = "Меня зовут Виола Маро"
VIOLA = [
    "Я психолог и психотерапевт, 25 лет веду частную практику в Италии на русском и итальянском",
    "Окончила факультет психологии СПбГУ и римский университет Sapienza",
    "Училась в Риме, Милане, Нью-Йорке, Париже и Сан-Паулу",
    "Выступала спикером на Специальной сессии ООН по вопросам детей и молодёжи",
    "Меня читают и смотрят 713 000 подписчиков в YouTube, TikTok и Instagram",
    "Мою программу «Прикладная эмпатия» выбрали больше 100 человек",
]
VIOLA_POD = "Я объясняю, почему вы так устроены, и показываю, что с этим делать"

# 11. Почему вы ничем не рискуете
RISK_H = "Почему вы ничем не рискуете"
RISK = [
    ("Можно начать с одного месяца",
     "Если клуб вам не подойдёт, отмените подписку в боте, и следующего списания не будет"),
    ("Долгих обязательств нет",
     "Подписка оформляется только на месяц или на три"),
    ("Дешевле одной консультации",
     "Личная встреча со мной стоит 200 €, а встречи в клубе групповые, поэтому месяц с двумя "
     "встречами стоит %(1m)s"),
]

# 12. Тарифы
TARIFY_H = "Сколько стоит"
TARIFY = [
    {"id": "1m", "name": "1 месяц",
     "text": "Подписка продлевается раз в месяц автоматически, отменить можно в любой момент",
     "btn": "Вступить на месяц"},
    {"id": "3m", "name": "3 месяца",
     "text": "Меньше 4 000 ₽ в месяц, вы экономите 2 980 ₽ и проходите три темы подряд",
     "btn": "Вступить на три месяца"},
]
TARIFY_POD = ("Оплатить можно из любой страны, российской картой в рублях или зарубежной картой "
              "в евро. Деньги принимает ИП Нижевясова А. С., официальный организатор моих программ")
# Тексты тарифа «3 месяца» и карточки «Дешевле одной консультации» посчитаны
# от этих цен. Поменялась цена, значит сборка напомнит поправить и тексты.
CENY_TEKSTY = {"1m": "4 990 ₽", "3m": "11 990 ₽"}

# 13. Вопросы
VOPROSY_H = "Вопросы"
VOPROSY = [
    ("Как проходят встречи?",
     "Две встречи в месяц идут в прямом эфире в Телеграме. Если не успеваете вживую, запись "
     "остаётся в клубе, и вы смотрите её, когда удобно"),
    ("Можно вступить в середине месяца?",
     "Да, вы начинаете с текущей темы, а записи прошлых встреч уже ждут вас в клубе"),
    ("Я не уверена, что я эмпат. Мне подойдёт?",
     "Если вы всё пропускаете через себя и после общения с людьми у вас не остаётся сил, клуб "
     "про вас. Как это называть, не так важно, техники работают для любого человека, который "
     "чувствует других сильнее, чем хотел бы"),
    ("Я уже проходила «Прикладную эмпатию». Зачем мне клуб?",
     "В программе вы получили основу и техники. В клубе вы каждый месяц применяете их в новой "
     "сфере жизни и приходите с вопросами на встречи со мной"),
    ("Я уже читала книги и ходила к психологу. Чем это отличается?",
     "Понимания у вас уже достаточно, не хватает действия в ту минуту, когда на вас давят. "
     "Поэтому каждая техника в клубе на конкретную сцену, например мама обиделась на ваш отказ "
     "или партнёр снова давит на жалость"),
    ("У меня совсем нет сил",
     "Клуб рассчитан на уставших, в нём две встречи в месяц и техники маленькими шагами, "
     "по 10–15 минут в день"),
    ("Мне уже поздно что-то менять",
     "В моей программе есть участники старше 65 лет. Менять то, как вы реагируете на людей, "
     "можно в любом возрасте"),
    ("Вы будете отвечать мне лично?",
     "Раз в неделю я голосом отвечаю на самые частые вопросы участников, а на встречах разбираю "
     "вопросы из клуба. Личной работы один на один в клубе нет, для неё есть мои консультации"),
    ("Как отменить подписку?",
     "В боте клуба есть кнопка «Управление подпиской». Отменить можно в любой момент, доступ "
     "сохранится до конца оплаченного месяца, и следующего списания не будет"),
    ("Я живу за границей и боюсь платить онлайн",
     "Оплатить можно из любой страны, после оплаты приходит чек. Моя команда пишет только "
     "с аккаунта @violamaroteam, и если кто-то другой просит у вас деньги от моего имени, "
     "это мошенники"),
    ("У меня Telegram открывается только с VPN. Я смогу участвовать?",
     "Да, ни одна часть клуба не требует быть на связи в конкретную минуту. Встречи остаются "
     "в записи, а вопросы вы пишете, когда вам удобно"),
    ("А если станет тяжело?",
     "Когда начинаешь разбирать то, что годами лежало нетронутым, какое-то время может быть "
     "неспокойно, поэтому темп здесь ваш. Клуб не заменяет очную психотерапию, и если сейчас "
     "у вас острое состояние, сначала стоит опереться на своего специалиста"),
    ("Куда писать, если есть вопрос по оплате или доступу?",
     "В службу заботы @violamaroteam"),
]

# 14. Последний экран
FINAL_H = "Первая встреча клуба %s, тема «Своя опора»"
FINAL_TEXT = "Начните с одного месяца, технику на 10–15 минут вы получите в день вступления"
FINAL_BTN = {"1m": "1 месяц за %s", "3m": "3 месяца за %s"}
FINAL_POD = "Осталось %(n)d %(mest)s, отменить подписку можно в любой момент"
FINAL_POD_POLNYY = "В первом наборе %(n)d %(mest)s, отменить подписку можно в любой момент"

# 15. Подвал: документы по тексту клуба, «Договор оферты» ведёт на OFERTA.
PODVAL_DOCS = [
    ("Договор оферты", None),
    ("Политика конфиденциальности", "/privacy"),
    ("Согласие на обработку персональных данных", "/consent"),
    ("Согласие на получение рассылки", "/consent-ads"),
]
TG_ZABOTA = "https://t.me/violamaroteam"

# Картинки: имя файла без расширения, пропорции блока-заглушки.
IMG = {
    "hero-desktop": (2400, 1350), "hero-mobile": (1080, 1620),
    "viola-portret": (1200, 1500),
    "final-desktop": (2400, 1350), "final-mobile": (1080, 1620),
    "o-kino": (800, 800), "o-chashka": (800, 800), "o-pismo": (800, 800),
}


# ─────────────────────────────────────────────────────────── картинки ──

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def esc(s):
    return html_mod.escape(s, quote=True)


def find_src(name):
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = os.path.join(SRC, name + "." + ext)
        if os.path.isfile(p):
            return p
    return None


_made = {}


def webp(name, widths):
    """Сжимает build-assets/opora/<name>.* в webp нужных ширин. Возвращает
    [(путь, ширина, высота)] или [], если картинки нет."""
    if name in _made:
        return _made[name]
    src = find_src(name)
    if not src:
        _made[name] = []
        return []
    from PIL import Image
    im = Image.open(src)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    out = os.path.join(DEST, "img")
    os.makedirs(out, exist_ok=True)
    made = []
    for w in widths:
        w = min(w, im.width)
        if made and made[-1][1] == w:
            continue
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) if w < im.width else im
        fn = "%s-%d.webp" % (name, w)
        r.save(os.path.join(out, fn), quality=82, method=6)
        made.append(("/opora/img/%s?v=%s" % (fn, file_hash(os.path.join(out, fn))), w, r.height))
    _made[name] = made
    return made


def srcset(made):
    return ", ".join("%s %dw" % (u, w) for u, w, _h in made)


def zaglushka(name, cls=""):
    """Блок цвета --panel на месте картинки, которой пока нет."""
    w, h = IMG[name]
    WARN.append("нет картинки build-assets/opora/%s.jpg (или .png): на её месте блок цвета --panel" % name)
    return '<div class="op-ph %s" style="aspect-ratio: %d / %d" aria-hidden="true"></div>' % (cls, w, h)


def img(name, alt, widths, sizes, cls="", lazy=True):
    made = webp(name, widths)
    if not made:
        return zaglushka(name, cls)
    u, w, h = made[-1]
    return ('<img class="%s" src="%s" srcset="%s" sizes="%s" alt="%s" width="%d" height="%d"%s decoding="async">'
            % (cls, u, srcset(made), sizes, esc(alt), w, h, ' loading="lazy"' if lazy else ""))


def fon(prefix, alt, lazy, sizes="100vw"):
    """Фото на всю ширину: телефонный кадр до 759 px, широкий дальше.
    Есть только один из двух кадров, значит он стоит на обоих экранах."""
    d = webp(prefix + "-desktop", (1280, 1920, 2400))
    m = webp(prefix + "-mobile", (720, 1080))
    if not d and not m:
        zaglushka(prefix + "-desktop")
        zaglushka(prefix + "-mobile")
        return '<div class="op-fon op-fon-ph" aria-hidden="true"></div>'
    for net, est in ((d, "mobile"), (m, "desktop")):
        if not net:
            other = "desktop" if est == "mobile" else "mobile"
            WARN.append("нет картинки build-assets/opora/%s-%s.jpg: на обоих экранах стоит %s-%s"
                        % (prefix, other, prefix, est))
    main = d or m
    u, w, h = main[-1]
    src_m = ('<source media="(max-width: 759px)" srcset="%s" sizes="100vw">' % srcset(m)) if (m and d) else ""
    return ('<picture class="op-fon">%s<img src="%s" srcset="%s" sizes="%s" alt="%s" width="%d" height="%d"%s'
            ' decoding="async"%s></picture>'
            % (src_m, u, srcset(main), sizes, esc(alt), w, h, ' loading="lazy"' if lazy else "",
               "" if lazy else ' fetchpriority="high"'))


def nakl(inner, cls=""):
    """Наклеенная карточка с рваным белым краем."""
    return '<div class="op-nakl %s">%s</div>' % (cls, inner)


def predmet(name, alt, cls=""):
    """Предмет на прозрачном фоне в наклеенной карточке."""
    return nakl(img(name, alt, (400, 800), "(max-width: 759px) 50vw, 240px", "op-predmet-img"),
                "op-predmet " + cls)


# ───────────────────────────────────────────────────────────── вёрстка ──

def h2(text, cls=""):
    """Заголовок экрана: Prata прописными. Каллиграфию в заголовках
    Артём убрал 04.11.2026 («плохие шрифты»), хотя её просило ТЗ."""
    return '<h2 class="op-h2%s">%s</h2>' % (cls, esc(text))


def ssylka(key):
    url = SSYLKI.get(key, "")
    if not url:
        WARN.append("пустая ссылка SSYLKI[%r]: кнопка ведёт на #" % key)
        return "#"
    return esc(url)


def btn(label, href, cls=""):
    return '<a class="op-btn%s" href="%s">%s</a>' % (cls, href, label)


def stroka_mest():
    if otkryt():
        if MEST_OSTALOS == MEST_VSEGO:      # до первой продажи «Осталось 50 из 50» звучит пусто
            return POD_POLNYY % {"vsego": MEST_VSEGO, "mest": mest(MEST_VSEGO)}
        return POD_OTKRYT % {"do": NABOR_DO, "n": MEST_OSTALOS, "mest": mest(MEST_OSTALOS), "vsego": MEST_VSEGO}
    return stroka_zakryt()


def stroka_zakryt():
    if not SLED_NABOR:
        WARN.append("набор закрыт, а SLED_NABOR пуст: под кнопкой только «Набор закрыт»")
        return "Набор закрыт"
    return POD_ZAKRYT % {"sled": SLED_NABOR}


def list_btn():
    return btn(BTN_LIST, ssylka("list"))


def sec(blok, inner, cls="", sid="", fon=None):
    """Экран страницы. Светлые экраны лежат листом с аркой сверху, как
    розовые блоки референса, поэтому у них лишняя обёртка."""
    if "op-svetlyy" in cls:
        inner = '\n  <div class="op-arka">\n  <div class="op-in">%s\n  </div>\n  </div>' % inner
    else:
        inner = '\n  <div class="op-in">%s\n  </div>' % inner
    return """
<section class="op-sec %s"%s data-blok="%s"%s>%s
</section>""" % (cls + ((" op-sfon op-sfon-" + fon) if fon else ""), (' id="%s"' % sid) if sid else "", blok,
                 fon_style("fon-" + fon) if fon else "", inner)


def cards(items, cls="op-cards-4"):
    return '<div class="op-cards %s">%s</div>' % (cls, "".join(
        '<article class="op-card"><h3 class="op-h3">%s</h3><p>%s</p></article>' % (h, nbsp_tail(t))
        for h, t in items))


def zhirno(x):
    """Пункт задач: часть до первой запятой жирным. Где запятой нет,
    жирным часть до первого « и »."""
    if "," in x:
        head, tail = x.split(",", 1)
        return "<b>%s,</b>%s" % (head, nbsp_tail(tail))
    head, tail = x.split(" и ", 1)
    return "<b>%s</b> и %s" % (head, nbsp_tail(tail))


def sec_hero():
    """Первые два экрана по форме менторства Пырикова (egorpyrikov.ru/
    mentorstvo2025), правки Артёма 04.11.2026. Фото готовое, без вырезки.

    Телефон: плашки «Набор до:» и «Старт:», слово ОПОРА над Виолой, под ним
    подпись «клуб Виолы Маро», Виола по центру, кнопка у неё на груди,
    под ней строка мест. Компьютер: Виола справа, над ней ОПОРА; слева
    плашки, оффер («ОПОРА – это закрытый клуб…») и кнопка.

    Второй экран — светлая панель наезжает на низ фото: на телефоне
    определение и задачи, на компьютере только задачи (определение уже
    стоит в оффере слева на первом экране)."""
    on = otkryt()
    # пока набор открыт, сразу в бот на месяц (Артём 05.11.2026)
    knopka = (btn(BTN_KLUB % CENY["1m"], ssylka("1m"), " op-btn-hero") if on
              else btn(BTN_LIST, ssylka("list"), " op-btn-hero"))
    if on:
        vtoraya = (PLASHKA_NABOR, NABOR_DO)
    else:
        vtoraya = (PLASHKA_SLED[0], SLED_NABOR) if SLED_NABOR else (PLASHKA_SLED[1], PLASHKA_SLED[2])
    pl = [vtoraya, (PLASHKA_START, PERVAYA_VSTRECHA)]   # слева направо по времени: набор, потом старт
    plashki = '<span class="op-pl-tochka" aria-hidden="true"></span>'.join(
        '<p class="op-pl"><span>%s</span> <b>%s</b></p>' % x for x in pl)
    plashki = '<div class="op-plashki-verh">%s</div>' % plashki
    cta = '<div class="op-hero-cta %%s">%s<p class="op-mest">%s</p></div>' % (knopka, stroka_mest())

    nazv, ostalnoe = HERO_H.split(" – ", 1)
    akcent = lambda cls: esc(ostalnoe).replace(
        esc(HERO_AKCENT), '<b class="%s">%s</b>' % (cls, esc(HERO_AKCENT)), 1)
    celi = "".join("<li>%s</li>" % zhirno(x) for x in CELI)
    return """
<section class="op-hero" data-blok="Первый экран">
  <div class="op-hero-l">
    %(plashki)s
    <p class="op-hero-offer"><span class="op-hero-offer-nazv">%(nazv)s –</span> <span class="op-eto">%(eto)s</span>%(offer)s</p>
    %(cta_pk)s
  </div>
  <div class="op-hero-r">
    <div class="op-slovo"><p class="op-nad">%(nad)s</p><p class="op-nazvanie">%(slovo)s</p></div>
    <div class="op-hero-foto">
      %(fon)s
      %(cta_tel)s
    </div>
  </div>
</section>
<section class="op-celi" data-blok="Блок «ОПОРА –»">
  <div class="op-in">
    <div class="op-celi-panel">
      <div class="op-celi-l">
        <h1 class="op-celi-h"><span class="op-h2 op-celi-nazv">%(nazv)s –</span> <span class="op-offer">%(h)s</span></h1>
      </div>
      <div class="op-celi-r">
        <h2 class="op-h2 op-zadachi-h">%(zh)s</h2>
        <p class="op-metka">%(metka)s</p>
        <ul class="op-kvadraty">%(celi)s</ul>
      </div>
    </div>
    <span class="op-strelka" aria-hidden="true"></span>
  </div>
</section>""" % {"plashki": plashki, "nazv": nazv, "eto": akcent("op-hero-akcent").split(" ", 1)[0], "offer": " " + akcent("op-hero-akcent").split(" ", 1)[1],
                 "cta_pk": cta % "op-cta-pk", "cta_tel": cta % "op-cta-tel",
                 "slovo": HERO_NAZVANIE, "nad": HERO_NAD,
                 "fon": fon("hero", "Виола Маро на диване у изумрудной стены", lazy=False, sizes="125vw"),
                 "h": akcent("op-akcent-slova"), "celi": celi, "zh": ZADACHI_H, "metka": ZADACHI_METKA}


def sec_otzyvy():
    """«Что изменилось у участниц программ»: номер, сфера, крупная фраза,
    внизу «было» на бежевом и «стало» на изумрудном (на компьютере рядом
    через золотую стрелку). Вариант 2, выбран Артёмом 05.11.2026."""
    b, st = OTZYVY_METKI
    items = "".join("""
      <article class="op-iz">
        <p class="op-iz-top"><span class="op-iz-n">%02d</span><span class="op-iz-sf">%s</span></p>
        <h3 class="op-iz-h">%s</h3>
        <div class="op-iz-ba">
          <div class="op-iz-bylo"><small>%s</small>%s</div>
          <span class="op-iz-ar" aria-hidden="true">→</span>
          <div class="op-iz-stalo"><small>%s</small>%s</div>
        </div>
      </article>""" % (i + 1, sf, nbsp_tail(fr), b, nbsp_tail(by), st, nbsp_tail(sta))
                    for i, (sf, fr, by, sta) in enumerate(OTZYVY))
    return sec("Отзывы", """
    %s
    <p class="op-lead op-iz-lead">%s</p>
    <div class="op-iz-cards">%s
    </div>""" % (h2(OTZYVY_H, " op-center"), OTZYVY_POD, items), "op-svetlyy", "otzyvy", "bumaga")


def sec_dlya_kogo():
    """«Опора подходит вам, если вы»: карточки «сначала картинка, под ней текст»
    (Артём 05.11.2026). Картинки — ситуации dk-1…dk-6 из листа, сгенерированного
    Артёмом. Боль жирным бордовым. На компьютере три в ряд. Фон — дубовые панели."""
    def kart(i, a, b):
        k = "dk-%d" % (i + 1)
        pic = img(k, "", (400, 640), "(max-width: 759px) 100vw, (max-width: 1023px) 50vw, 360px", "op-dk-img") \
            if find_src(k) else ""
        return ('<li class="op-dk-card">%s<div class="op-dk-t"><span class="op-dk-num" aria-hidden="true">%02d</span>'
                '<p>%s<b>%s</b></p></div></li>' % (pic, i + 1, a, nbsp_tail(b)))
    items = "".join(kart(i, a, b) for i, (a, b) in enumerate(DLYA_KOGO))
    zag = DLYA_KOGO_H.replace("ОПОРА", '<span class="op-h2-akc">ОПОРА</span>', 1)
    return sec("Для кого", """
    <h2 class="op-h2 op-dk-h">%s</h2>
    <ol class="op-dk-cards">%s</ol>
    <p class="op-dk-itog">%s</p>""" % (zag, items, nbsp_tail(DLYA_KOGO_POD)), fon="derevo")


def fon_style(name):
    """Фон экрана картинкой из build-assets/opora/<name>: в CSS переменная --fon."""
    made = webp(name, (1600,))
    if not made:
        WARN.append("нет картинки build-assets/opora/%s.jpg: экран без фона-картинки" % name)
        return ""
    return ' style="--fon: url(%s)"' % made[-1][0]


def sec_izmenitsya():
    return sec("Что изменится", """
    %s
    %s
    <p class="op-niz">%s</p>""" % (h2(IZMENITSYA_H), cards(IZMENITSYA), IZMENITSYA_POD), "op-barhat", fon="barhat")


def video_html():
    if not VIDEO:
        WARN.append("VIDEO пуст: блок «Что такое «Опора»» собран без видео")
        return ""
    if VIDEO.startswith(("http://", "https://")):
        src = VIDEO
        WARN.append("VIDEO ведёт на внешний адрес: видео грузится только по нажатию, но это внешний запрос")
    else:
        p = os.path.join(SRC, VIDEO)
        if not os.path.isfile(p):
            raise SystemExit("опора: VIDEO = %r, а файла build-assets/opora/%s нет" % (VIDEO, VIDEO))
        shutil.copy2(p, os.path.join(DEST, VIDEO))
        src = "/opora/%s?v=%s" % (VIDEO, file_hash(p))
    return """
    <figure class="op-video">%s
      <figcaption>%s</figcaption>
    </figure>""" % (nakl('<video controls preload="none" playsinline src="%s"></video>' % esc(src)), VIDEO_PODPIS)


def sec_chto():
    chips = "".join('<li class="op-chip">%s</li>' % s for s in SFERY)
    return sec("Что такое «Опора»", """
    %s%s
    <p class="op-bolshoy">%s</p>
    <ul class="op-chips">%s</ul>""" % (h2(CHTO_H), video_html(), nbsp_tail(CHTO_TEXT), chips), "op-narrow")


def sec_mesyac():
    shagi = []
    for i, (h, t) in enumerate(SHAGI):
        dop = predmet("o-kino", "Кинолента и билет") if i == len(SHAGI) - 1 else ""
        shagi.append("""
      <li class="op-shag%s"><span class="op-num" aria-hidden="true">%d</span>
        <div><h3 class="op-h3">%s</h3><p>%s</p></div>%s
      </li>""" % (" op-shag-pr" if dop else "", i + 1, h, nbsp_tail(t), dop))
    return sec("Как проходит месяц", """
    %s
    <ol class="op-shagi">%s
    </ol>
    <h3 class="op-h2 op-h2-sm">%s</h3>
    %s""" % (h2(MESYAC_H), "".join(shagi), RABOTAET_H, cards(RABOTAET)), "op-barhat", fon="derevo")


def sec_tri():
    items = "".join("""
      <article class="op-card op-mes"><span class="op-num" aria-hidden="true">%d</span>
        <h3 class="op-h3">%s</h3><p>%s</p></article>""" % (i + 1, h, nbsp_tail(t))
                    for i, (h, t) in enumerate(TRI))
    return sec("Первые три месяца", """
    %s
    <p class="op-lead">%s</p>
    <div class="op-cards op-cards-3">%s
    </div>
    <p class="op-niz">%s</p>""" % (h2(TRI_H), TRI_POD, items, nbsp_tail(TRI_NIZ)))


def bloknot_style():
    """Картинка блокнота разрезана на части в build-assets/opora/bloknot/
    (страницы, корешок, кольца): блокнот тянется под любой текст, а кольца
    и золотые уголки не искажаются. Части уходят в CSS переменными."""
    d = os.path.join(SRC, "bloknot")
    if not os.path.isdir(d):
        WARN.append("нет build-assets/opora/bloknot/: блокнот нарисован стилями")
        return ""
    out = os.path.join(DEST, "bloknot")
    os.makedirs(out, exist_ok=True)
    var = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".webp"):
            shutil.copy2(os.path.join(d, f), os.path.join(out, f))
            var.append("--bl-%s: url(/opora/bloknot/%s?v=%s)" % (f[:-5], f, file_hash(os.path.join(d, f))))
    return ' style="%s"' % "; ".join(var)


def sec_poluchaete():
    """«Каждый месяц вы получаете» раскрытым блокнотом на кольцах в бордовом
    переплёте (вариант Артёма 05.11.2026, по референсу «Гранд Будапешт»).
    Все семь пунктов оформлены одинаково: название и описание, без картинок.
    Слева заголовок и первые пункты, справа остальные, итог в самом конце."""
    def punkt(i, t, d):
        pic = ""   # картинки в карточках убраны (Артём 05.11.2026)
        t = re.sub(r"(\w+-\w+)", r'<span class="g-nw">\1</span>', t)   # «онлайн-встречи» не рвётся
        return '<li>%s<div><h3>%s</h3><p>%s</p></div></li>' % (pic, t, nbsp_tail(d))
    pp = [punkt(i, t, d) for i, (t, d) in enumerate(POLUCHAETE)]
    polov = 3
    kolca = '<i></i>' * 14
    kolca_tel = ''   # на телефоне кольца в картинке tel-top
    return """
<section class="op-sec op-sfon op-sfon-derevo op-blk" data-blok="Каждый месяц вы получаете"%s>
  <div class="op-in">
    <div class="op-bl"%s>
      <div class="op-bl-kolca-tel" aria-hidden="true">%s</div>
      <div class="op-bl-str">
        <h2 class="op-bl-h">%s</h2>
        <ul class="op-bl-list">%s</ul>
      </div>
      <div class="op-bl-kolca" aria-hidden="true">%s</div>
      <div class="op-bl-str">
        <ul class="op-bl-list">%s</ul>
        <p class="op-bl-pod">%s</p>
      </div>
    </div>
  </div>
</section>""" % (fon_style("fon-derevo"), bloknot_style(), kolca_tel, POLUCHAETE_H, "".join(pp[:polov]), kolca, "".join(pp[polov:]),
                 nbsp_tail(POLUCHAETE_POD))


def sec_vhodit():
    """Подарок «В день вступления вас уже ждут» отдельным экраном."""
    podarki = "".join("<li>%s</li>" % nbsp_tail(x) for x in PODARKI)
    return sec("В день вступления", """
    <div class="op-podarok">
      <div class="op-podarok-t">
        <p class="op-podarok-h">%s</p>
        <ul class="op-podarok-list">%s</ul>
      </div>
      %s
    </div>""" % (PODARKI_H, podarki, predmet("o-chashka", "Чашка чая")), "op-barhat op-narrow", fon="derevo")


def sec_udobno():
    return sec("Почему это удобно", "\n    %s\n    %s" % (h2(UDOBNO_H), cards(UDOBNO)), fon="barhat")


def sec_viola():
    if find_src("viola-portret"):
        foto = img("viola-portret", "Виола Маро", (600, 1200), "(max-width: 759px) 80vw, 420px")
    else:
        # Пока портрета нет, стоит вырезка Виолы из темы barhat (по ТЗ).
        p = os.path.join(build.BUILD_ASSETS, "tema-barhat", "viola.png")
        WARN.append("нет build-assets/opora/viola-portret.jpg: в «Кто ведёт клуб» стоит viola.png из темы barhat")
        if os.path.isfile(p):
            made = webp_from(p, "viola", (600, 900))
            u, w, h = made[-1]
            foto = ('<img class="op-viola-png" src="%s" srcset="%s" sizes="(max-width: 759px) 80vw, 420px" '
                    'alt="Виола Маро" width="%d" height="%d" loading="lazy" decoding="async">'
                    % (u, srcset(made), w, h))
        else:
            foto = zaglushka("viola-portret")
    items = "".join("<li>%s</li>" % nbsp_tail(x) for x in VIOLA)
    return sec("Кто ведёт клуб", """
    <div class="op-viola">
      <div class="op-viola-t">
        %s
        <ul class="op-galki">%s</ul>
        <p class="op-akcent">%s</p>
      </div>
      <div class="op-viola-foto">%s</div>
    </div>""" % (h2(VIOLA_H), items, VIOLA_POD, nakl(foto, "op-portret")), "op-barhat")


def webp_from(path, name, widths):
    """webp из файла вне build-assets/opora (вырезка Виолы из темы barhat)."""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    out = os.path.join(DEST, "img")
    os.makedirs(out, exist_ok=True)
    made = []
    for w in widths:
        w = min(w, im.width)
        if made and made[-1][1] == w:
            continue
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        fn = "%s-%d.webp" % (name, w)
        r.save(os.path.join(out, fn), quality=82, method=6)
        made.append(("/opora/img/%s?v=%s" % (fn, file_hash(os.path.join(out, fn))), w, r.height))
    return made


def sec_risk():
    items = [(h, t % CENY if "%(" in t else t) for h, t in RISK]
    return sec("Почему вы ничем не рискуете", "\n    %s\n    %s" % (h2(RISK_H), cards(items, "op-cards-3")))


def sec_tarify():
    on = otkryt()
    kartochki = []
    for t in TARIFY:
        eur = CENY_EUR.get(t["id"], "")
        kartochki.append("""
      <article class="op-tarif">
        <span class="op-tarif-dyrka" aria-hidden="true"></span>
        <h3 class="op-tarif-h">%(name)s</h3>
        <p class="op-cena">%(cena)s</p>%(eur)s
        <p class="op-tarif-t">%(text)s</p>%(btn)s
      </article>""" % {"name": t["name"], "cena": CENY[t["id"]],
                       "eur": ('\n        <p class="op-cena-eur">%s</p>' % eur) if eur else "",
                       "text": nbsp_tail(t["text"]),
                       "btn": ("\n        " + btn(t["btn"], ssylka(t["id"]))) if on else ""})
    if not any(CENY_EUR.values()):
        WARN.append("CENY_EUR пуст: цены в евро на странице не показаны")
    niz = "" if on else """
    <div class="op-zakryt">%s
      <p class="op-mest">%s</p>
    </div>""" % (list_btn(), stroka_zakryt())
    return sec("Тарифы", """
    %s
    <div class="op-tarify">%s
    </div>%s
    <p class="op-oplata">%s</p>""" % (h2(TARIFY_H, " op-center"), "".join(kartochki), niz, nbsp_tail(TARIFY_POD)),
               "op-barhat", "stoimost", "koridor")


def sec_voprosy():
    items = "".join("""
      <details class="op-faq-i">
        <summary>%s</summary>
        <p>%s</p>
      </details>""" % (nbsp_tail(q), nbsp_tail(a)) for q, a in VOPROSY)
    return sec("Вопросы", """
    <div class="op-voprosy-head">%s%s</div>
    <div class="op-faq">%s
    </div>""" % (h2(VOPROSY_H), predmet("o-pismo", "Письмо с сургучной печатью", "op-pismo"), items),
               "op-svetlyy op-narrow", "voprosy", "bumaga")


def sec_final():
    if otkryt():
        knopki = (btn(FINAL_BTN["1m"] % CENY["1m"], ssylka("1m"))
                  + btn(FINAL_BTN["3m"] % CENY["3m"], ssylka("3m")))
        pod = (FINAL_POD_POLNYY if MEST_OSTALOS == MEST_VSEGO else FINAL_POD) % {"n": MEST_OSTALOS, "mest": mest(MEST_OSTALOS)}
    else:
        knopki, pod = list_btn(), stroka_zakryt()
    return """
<section class="op-final" data-blok="Последний экран">
  <div class="op-in">
    <div class="op-final-card">
      <h2 class="op-h2">%(h)s</h2>
      <p class="op-final-t">%(t)s</p>
      <div class="op-knopki">%(knopki)s</div>
      <p class="op-mest">%(pod)s</p>
    </div>
  </div>
  %(fon)s
</section>""" % {"fon": fon("final", "", lazy=True), "h": nbsp_tail(FINAL_H % PERVAYA_VSTRECHA),
                 "t": nbsp_tail(FINAL_TEXT), "knopki": knopki, "pod": pod}


def podval():
    """Общий подвал сайта (build.footer_html), документы по тексту клуба."""
    ft = build.footer_html()
    if not OFERTA:
        WARN.append("OFERTA пуст: «Договор оферты» в подвале ведёт на #")
    docs = "".join('\n        <a href="%s">%s</a>' % (esc(OFERTA or "#") if u is None else u, t)
                   for t, u in PODVAL_DOCS)
    ft, n = re.subn(r'(<p class="ft-label">Документы</p>).*?(\s*</nav>)',
                    lambda m: m.group(1) + docs + m.group(2), ft, count=1, flags=re.S)
    if not n:
        raise SystemExit("опора: в подвале сайта не найден список документов")
    return ft


# ─────────────────────────────────────────────────────────── сборка ──

def page():
    hero = sec_hero()
    body = "".join([
        sec_poluchaete(), sec_otzyvy(),
        # 05.11.2026 Артём убрал «Для кого» и все блоки после отзывов. Их функции остались, чтобы вернуть:
        # sec_dlya_kogo, sec_izmenitsya, sec_chto, sec_mesyac, sec_tri, sec_vhodit, sec_udobno, sec_viola,
        # sec_risk, sec_tarify, sec_voprosy, sec_final. Тексты в opora-teksty.md, раздел «Убрано со страницы».
    ])
    body = typograf(hero + body)
    # «10–15» и «35–44» не рвутся по короткому тире
    body = re.sub(r"(?<![\w>])(\d+–\d+)(?![\w<])", r'<span class="g-nw">\1</span>', body)
    css_v = file_hash(os.path.join(OUT, "assets", "site.css"))
    op_v = file_hash(os.path.join(DEST, "opora.css"))
    head = build.head(TITLE, DESCRIPTION, "/assets/site.css?v=%s" % css_v,
                      '<link rel="stylesheet" href="/opora/opora.css?v=%s">\n'
                      '<link rel="canonical" href="https://violamaro.ru/opora/">\n' % op_v)
    head = head.replace('content="#241C18"', 'content="#1F3532"', 1).replace("<body>", '<body class="op">', 1)
    return (head
            # не <main>: правила общего site.css вида «main h2 {… !important}» писались
            # для страниц практикума и перекрашивали бы клуб
            + '<div id="main" class="op-main" role="main">' + body + "</div>\n" + podval() + build.COOKIE_HTML
            + "<script>%s</script>\n</body>\n</html>\n" % build.COOKIE_JS)


def check(text):
    """Ни длинного тире, ни «2.0», ни таймеров и зачёркнутых цен, ни форм
    и внешних адресов, кроме ссылок из конфига."""
    visible = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text)
    problems = []
    if "—" in visible or "&mdash;" in visible:
        problems.append("длинное тире: " + ", ".join(sorted(set(re.findall(r".{0,30}—.{0,30}", visible)))[:5]))
    if "2.0" in visible:
        problems.append("«2.0»: " + ", ".join(set(re.findall(r".{0,30}2\.0.{0,10}", visible))))
    for tag in ("<form", "<input", "<s>", "<del", "<iframe"):
        if tag in text:
            problems.append("на странице есть %s" % tag)
    razresheno = {u for u in list(SSYLKI.values()) + [OFERTA, VIDEO, TG_ZABOTA] if u}
    for attr, url in re.findall(r'\b(src|href|srcset)="(https?://[^"\s]+)', text):
        if attr == "href" and (url in razresheno or url.startswith("https://t.me/") or url == "https://violamaro.ru/opora/"):
            continue
        if attr == "src" and url == VIDEO:
            continue
        problems.append("внешний адрес: %s" % url)
    if problems:
        raise SystemExit("опора: " + "; ".join(problems))


# ─────────────────────────────────────────────────────────── сверка ──

def norm(s):
    s = html_mod.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def teksty_iz_fajla():
    """Тексты страницы из opora-teksty.md: (элемент, текст) по порядку."""
    md = build.read(TEKSTY)
    a = md.index("## Тексты сайта по экранам")
    b = md.index("\n## ", a + 5)
    out, elem = [], ""
    for line in md[a:b].splitlines()[1:]:
        line = line.strip()
        if line.startswith("#"):
            elem = ""                          # новый экран: прежний элемент кончился
            continue
        if not line or (line.startswith("*") and line.endswith("*")):
            continue
        if line.startswith("В квадратных скобках"):
            continue
        m = re.match(r"\[([^\]]+)\]\s*(.*)$", line)
        if m:
            elem, line = m.group(1), m.group(2)
            if not line:
                continue
        if line.startswith("- "):
            line = line[2:]
        out.append((elem, line))
    return out


def sverka(text):
    """Каждый текст из файла есть на странице. Пропускает тексты другого
    состояния набора и подпись видео, если видео нет."""
    stranica = norm(text)
    on = otkryt()
    missing, n = [], 0
    for elem, t in teksty_iz_fajla():
        if elem == "Фото Виолы":
            continue
        if elem == "Видео" and not VIDEO:
            continue
        if "когда набор закрыт" in elem and on:
            continue
        polnyy = MEST_OSTALOS == MEST_VSEGO
        if "до первой продажи" in elem and not (on and polnyy):
            continue
        if "после первой продажи" in elem and not (on and not polnyy):
            continue
        if ("пока набор открыт" in elem or elem in ("Кнопка", "Кнопки", "Под кнопками")) and not on:
            continue
        t = (t.replace("[дата]", NABOR_DO if "открыт до" in t else SLED_NABOR or "[дата]")
              .replace("[17 ноября]", PERVAYA_VSTRECHA)
              .replace("[12 ноября]", NABOR_DO)
              .replace("[4 990 ₽]", CENY["1m"])
              .replace("[N] мест из [50]", "%d %s из %d" % (MEST_OSTALOS, mest(MEST_OSTALOS), MEST_VSEGO))
              .replace("[N] мест", "%d %s" % (MEST_OSTALOS, mest(MEST_OSTALOS)))
              .replace("[50] мест", "%d %s" % (MEST_VSEGO, mest(MEST_VSEGO))))
        if not on and elem.startswith("Под кнопкой") and not SLED_NABOR:
            t = "Набор закрыт"
        if not on and elem.startswith("Плашка сверху, когда") and not SLED_NABOR:
            t = "Набор: закрыт"
        kuski = t.split(" · ")
        if re.match(r"^[^,]+, \d+–\d+ года$", t):          # метка сферы и возраст отзыва
            kuski = t.split(", ")
        if "Служба заботы @violamaroteam" in kuski:         # в общем подвале подпись и ник раздельно
            i = kuski.index("Служба заботы @violamaroteam")
            kuski[i:i + 1] = ["Служба заботы", "@violamaroteam"]
        for k in kuski:
            k = norm(k)
            for cena_txt, cena in (("4 990 ₽", CENY["1m"]), ("11 990 ₽", CENY["3m"])):
                if elem in ("Карточка", "Кнопки") and k.endswith(cena_txt):
                    k = k[: -len(cena_txt)] + cena
            n += 1
            if k not in stranica:
                missing.append("[%s] %s" % (elem, k))
    if missing:
        raise SystemExit("опора: на странице нет текстов из opora-teksty.md:\n  " + "\n  ".join(missing))
    return n


def main():
    global NABOR_OTKRYT
    if not os.path.isfile(os.path.join(OUT, "assets", "site.css")):
        raise SystemExit("опора: сначала соберите сайт: python3 build.py --theme barhat --noindex")
    if "--zakryt" in sys.argv:          # для проверки закрытого состояния
        NABOR_OTKRYT = False
    if not 0 <= MEST_OSTALOS <= MEST_VSEGO:
        raise SystemExit("опора: MEST_OSTALOS должно быть от 0 до MEST_VSEGO")
    if CENY != CENY_TEKSTY:
        WARN.append("цены в CENY отличаются от CENY_TEKSTY: проверьте тексты тарифа «3 месяца» "
                    "и карточки «Дешевле одной консультации»")
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    os.makedirs(os.path.join(DEST, "fonts"))
    shutil.copy2(os.path.join(SRC, "opora.css"), os.path.join(DEST, "opora.css"))
    for f in (os.listdir(os.path.join(SRC, "fonts")) if os.path.isdir(os.path.join(SRC, "fonts")) else []):
        if f.endswith(".woff2"):
            shutil.copy2(os.path.join(SRC, "fonts", f), os.path.join(DEST, "fonts", f))
    text = page()
    check(text)
    n = sverka(text)
    if "--noindex" in sys.argv or build.NOINDEX:
        text = text.replace("<head>\n", '<head>\n<meta name="robots" content="noindex, nofollow">\n', 1)
    with open(os.path.join(DEST, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)
    print("Опора → site/opora/index.html (%d КБ), набор %s, текстов сверено: %d"
          % (len(text.encode("utf-8")) // 1024, "открыт" if otkryt() else "закрыт", n))
    for w in dict.fromkeys(WARN):
        print("  предупреждение: " + w)


if __name__ == "__main__":
    main()
