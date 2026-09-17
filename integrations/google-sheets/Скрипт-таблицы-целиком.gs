/**
 * Приёмник таблицы: тест «Есть у вас способности эмпата?», тест «Колесо эмпата»
 * и заявки с сайтов.
 *
 * Сервер не нужен: это скрипт внутри самой таблицы, Google сам держит адрес,
 * по которому страницы присылают данные.
 *
 * ⚠ После правок обязательно: Развернуть → Управление развёртываниями →
 * карандаш → Версия: «Новая версия» → Развернуть. Сохранение файла (Ctrl+S)
 * на работающий адрес НЕ влияет: он отдаёт закреплённую версию, а не редактор.
 * Проверить, что развернулось: открыть адрес /exec в браузере — в ответе
 * будет поле «версия». Не совпало с числом ниже — развёртывание старое.
 *
 * ⚠ Этот файл — копия того, что реально развёрнуто в таблице. Правка здесь
 * ничего не меняет в работе, пока её не перенесли в редактор и не развернули
 * новой версией. И наоборот: правку в редакторе надо возвращать сюда, иначе
 * следующая сессия будет чинить не тот код. 19 августа так и вышло.
 */

// Версия для интеграции мини-аппов. SaleBot-callback по-прежнему выключен,
// пока в свойствах скрипта явно не выставлено SALEBOT_ENABLED=1.
var ВЕРСИЯ = '2026-09-17 utm-and-lead-intent';

/* ═══ ИМЕНА ВКЛАДОК — ЕДИНСТВЕННОЕ МЕСТО, ГДЕ ОНИ ЗАДАЮТСЯ ═══════════
   Должны совпадать с именами вкладок в таблице ДОСЛОВНО. Разойдутся хоть
   на пробел — скрипт молча заведёт рядом новую вкладку и будет писать
   в неё, а вы будете ждать заявки в старой. Так уже случилось 18 августа.

   Проверить, что всё сходится: выбрать в списке функций «проверитьЛисты»
   и нажать «Выполнить». Скажет, какие вкладки не найдены. */
var ЛИСТЫ = {
  тест:         'Тест эмпата',           // сырьё теста про способности эмпата
  предзапись:   'Предзапись с теста',    // заявки из приложения того теста
  сайтПред:     'Предзапись с сайта',    // заявки с сайта предзаписи
  сайтОплата:   'Заявки на продукт',     // заявки с сайта оплаты и брони
  тестКолесо:   'Колесо эмпата',         // сырьё теста «Колесо эмпата»
  /* ⚠️ Имя вкладки НЕ переименовывать вслед за продуктом. Продукт стал
     «Неудобные» 28.08, а здесь стоит имя реальной вкладки в таблице.
     Поменяете тут — скрипт заведёт новую пустую вкладку и заявки поедут
     туда, а собранные останутся в старой. Меняется только вместе с ручным
     переименованием вкладки в самой таблице. */
  заявкиКолесо: 'Неудобная — заявки',
  старты: 'Старт теста'
};
/* ════════════════════════════════════════════════════════════════════ */

var SHEET_NAME = ЛИСТЫ.тест;
var LEAD_SHEET = ЛИСТЫ.предзапись;
var START_HEADERS = ['Дата', 'ID в Телеграме', 'Тест', 'Источник', 'Событие'];

var HEADERS = [
  'Дата', 'ID в Телеграме', 'Имя',
  'Ранг', 'Процент',
  'Дар', 'Прилипание', 'История', 'Тело', 'Адресат', 'Гигиена', 'Люди', 'Фон', 'Контроль',
  'Где съедает', 'Что менять первым', 'Что уже делали', 'Давно смотрит',
  'Ответы (1–24)',
  'Секунд', 'Быстро', 'Одна кнопка',
  /* Добавлена 06.09 в конец: откуда человек пришёл на тест (?startapp=…).
     Вставка в середину сдвинула бы уже собранные строки относительно шапки. */
  'Источник'
];

/* ⚠️ Две последние колонки добавлены 03.09, когда на «Прикладную эмпатию»
   стали собирать заявки оба теста сразу. Дописаны в конец намеренно: любая
   вставка в середину сдвигает уже собранные строки относительно шапки.
   «Откуда заявка» приходит полем istochnik_test; у теста «Эмпат ли вы»
   его нет, и там подставляется значение по умолчанию.
   «Просевшие сферы» заполняются только с «Колеса» — у первого теста
   колеса нет, колонка остаётся пустой не по сбою. */
var LEAD_HEADERS = [
  'Дата', 'Имя', 'Телеграм', 'ID в Телеграме',
  'Тип', 'Процент', 'Что менять первым', 'Где съедает', 'Готовность',
  'Согласие на ПД', 'Реклама', 'Время акцепта', 'Ред. согласия',
  'Откуда заявка', 'Просевшие сферы',
  /* Добавлена 06.09, тоже в конец: метка трафика с самого теста (?startapp=…).
     «Откуда заявка» говорит, с какого теста человек пришёл, «Источник» — по
     какой ссылке он на этот тест попал. */
  'Источник'
];

/* ─── «Колесо эмпата» ───────────────────────────────────────────────
   Шесть сфер в том же порядке, что на самом колесе. Порядок здесь
   задаёт порядок колонок: поменяете тут — разъедется шапка листа. */
var KL_SPHERES = [
  ['partner', 'Партнёр'],
  ['semya',   'Семья'],
  ['rabota',  'Работа'],
  ['dengi',   'Деньги'],
  ['telo',    'Тело и силы'],
  ['delo',    'Своё дело']
];

/* Шапка листа «Колесо эмпата». Логин в Телеграме отдельной колонкой:
   по нему команда пишет человеку первой, а имя из профиля для этого
   не годится — тёзок много, и фамилия у половины не заполнена. */
var KL_HEADERS = ['Дата', 'ID в Телеграме', 'Логин в Телеграме', 'Имя', 'Отдаю', 'Остаётся', 'Зазор']
  .concat(KL_SPHERES.map(function (s) { return s[1] + ' отдаю'; }))
  .concat(KL_SPHERES.map(function (s) { return s[1] + ' остаётся'; }))
  .concat(['Самые тяжёлые', 'Где тяжелее', 'Давно смотрит',
           'Ответы (1–24)', 'Секунд', 'Быстро', 'Одна кнопка']);

var KL_LEAD_HEADERS = [
  'Дата', 'Имя', 'Телеграм', 'ID в Телеграме', 'Логин в Телеграме', 'Имя в Телеграме',
  'Отдаю', 'Остаётся', 'Самые тяжёлые', 'Где тяжелее',
  'Согласие на ПД', 'Реклама', 'Время акцепта', 'Ред. согласия',
  /* Способ оплаты и источник стоят последними намеренно: колонку, дописанную
     в конец, getSheet2_ добавит к уже существующему листу, не сдвигая старые
     строки. saveKlWay_ ищет «Способ оплаты» по имени, а не по номеру, поэтому
     колонка после него ничего не ломает. */
  'Способ оплаты', 'Источник'
];

/* Какая форма в какой лист. «Заявка» и «оплата» делят один лист намеренно:
   в обоих случаях человек уже выбрал тариф, и держать их в разных вкладках
   значит дважды смотреть один и тот же список. Отличает их колонка
   «Готовность»: у заявки там «Заявка с канала, без оплаты». */
var SITE_SHEETS = {
  'предзапись': ЛИСТЫ.сайтПред,
  'оплата': ЛИСТЫ.сайтОплата,
  'заявка': ЛИСТЫ.сайтОплата
};

/** Общая строка с сайтом. Совпадает с FORM_SECRET в site.js. */
var SITE_SECRET = 'PxlGXL9bQSjc0dHcLoiCZJZWtNdfv9D8yY9SHBuJ';

var SITE_FIELDS = [
  ['received_at',         'Дата'],
  ['name',                'Имя'],
  ['phone',               'Телефон'],
  ['telegram',            'Телеграм'],
  ['readiness',           'Готовность'],     // предзапись и заявка
  ['plan',                'Тариф'],          // оплата, бронь и заявка
  ['accept_offer',        'Оферта'],
  ['accept_pd',           'Согласие на ПД'],
  ['accept_ads',          'Реклама'],
  ['consent_ts',          'Время акцепта'],
  ['doc_version_offer',   'Ред. оферты'],
  ['doc_version_annex',   'Ред. приложения'],
  ['doc_version_consent', 'Ред. согласия'],
  ['page',                'Страница'],
  ['ua',                  'User-Agent'],
  ['utm_source',          'Источник'],
  ['utm_medium',          'Канал'],
  ['utm_campaign',        'Кампания'],
  ['utm_content',         'Объявление'],
  ['src',                 'Метка'],
  ['referrer',            'Откуда пришёл']
];

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    return route_(d);
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/**
 * Страница теста присылает данные обычным GET с параметром payload.
 * Так надёжнее: POST на веб-приложение Apps Script упирается в редирект,
 * который у анонимных запросов отдаёт «Page Not Found».
 */
function doGet(e) {
  try {
    var p = (e && e.parameter) || {};

    /* Диагностика: какие вкладки скрипт реально видит и сколько в них строк.
       Нужна снаружи — по содержимому таблицы имена листов не определить,
       и 18 августа мы на этом ошиблись с диагнозом. */
    if (p.diag) {
      if (SITE_SECRET && p.diag !== SITE_SECRET) return json_({ ok: false, error: 'forbidden' });
      return json_({ ok: true, версия: ВЕРСИЯ, вкладки: обзорЛистов_() });
    }

    /* Сколько мест занято. Отдаёт настоящее число строк в листе заявок:
       страница показывает его человеку, поэтому выдумывать здесь нечего.
       Секрет не нужен, число не персональное. */
    if (p.seats) {
      var л = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ЛИСТЫ.заявкиКолесо);
      return json_({ ok: true, версия: ВЕРСИЯ, занято: л ? Math.max(0, л.getLastRow() - 1) : 0 });
    }

    if (p.action === 'status') {
      return json_(статус_(p.tg, p.test, p.login));
    }

    if (!p.payload) {
      return json_({ ok: true, note: 'Приёмник теста эмпата жив', версия: ВЕРСИЯ, лист: LEAD_SHEET });
    }
    return route_(JSON.parse(p.payload));
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function route_(d) {
  try {
    /* Список форм — в SITE_SHEETS, чтобы новая форма подключалась одной
       строкой там, а не двумя правками в разных местах. */
    if (SITE_SHEETS[d.form]) { return saveSite_(d); }
    if (d.type === 'start') return saveStart_(d);
    if (d.type === 'lead_intent') return saveIntent_(d);

    if (d.type === 'contact') return saveContact_(d);

    /* «Колесо» проверяем ДО общего d.type === 'lead': его лид-форма шлёт
       и метку теста, и тип. Поменяете местами — заявки на событие лягут
       в «Предзапись с теста», где под них нет ни одной подходящей колонки. */
    if (d.test === 'koleso') {
      if (d.type === 'lead') return saveKlLead_(d);
      if (d.type === 'pay') return saveKlWay_(d);
      return saveKl_(d);
    }

    if (d.type === 'lead') { return saveLead_(d); }

    /* Дальше — только результат теста эмпата. Если пришла форма, которой
       скрипт ещё не знает (сайт обновили, а скрипт нет), дописывать её сюда
       нельзя: в «Тест эмпата» нет колонок под имя и телефон, строка ляжет
       пустой, а сайт покажет человеку «заявка принята». Контакт исчезнет
       молча. Честная ошибка лучше: она видна и на сайте, и здесь. */
    if (d.form) return json_({ ok: false, error: 'неизвестная форма: ' + d.form });

    var sheet = getSheet_();
    var s = d.scales || {};

    sheet.appendRow([
      new Date(),
      d.userId || '',
      какТекст_(d.userName || ''),
      rankName_(d.rank),
      d.percent || '',
      s.A, s.P, s.I, s.B, s.C, s.G, s.L, s.F, s.K,
      pick_(d.forks, 'bol'), pick_(d.forks, 'zapros'),
      pick_(d.forks, 'opyt'), pick_(d.forks, 'davno'),
      (d.answers || []).join(','),
      d.seconds || '', d.fast ? 'да' : '', d.monotone ? 'да' : '',
      d.istochnik || ''
    ]);

    SpreadsheetApp.flush();
    notifySalebot_(d, 'empat');
    return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/** Заявка на предзапись — отдельным листом, чтобы не мешать сырьё теста и контакты. */
function saveStart_(d) {
  if (!d.userId) return json_({ ok: true, версия: ВЕРСИЯ, note: 'без ID не пишем' });
  var sheet = getSheet2_(ЛИСТЫ.старты, START_HEADERS);
  sheet.appendRow([new Date(), d.userId, d.test || 'empat', d.istochnik || '', 'test_started']);
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

function saveIntent_(d) {
  var id = String(d.userId || '').trim();
  if (!id) return json_({ ok: true, версия: ВЕРСИЯ, note: 'без ID не пишем' });
  var sheet = getSheet2_(ЛИСТЫ.старты, START_HEADERS);
  sheet.appendRow([new Date(), id, d.test || 'empat', d.istochnik || '', 'lead_intent']);
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

/** Нажатие «Написать Артёму». Одна строка на Telegram ID + тест. */
function saveContact_(d) {
  var id = String(d.userId || '').trim();
  if (!id) return json_({ ok: false, error: 'нет Telegram ID' });

  var test = d.test === 'koleso' ? 'koleso' : 'empat';
  var source = test === 'koleso' ? 'Колесо эмпата' : 'Тест «Эмпат ли вы»';
  var sheet = getSheet2_(LEAD_SHEET, LEAD_HEADERS);
  var duplicate = последняяСтрока_(sheet, id, function (r) {
    return String(r['Откуда заявка'] || '') === source &&
           String(r['Готовность'] || '') === 'Нажал «Написать Артёму»';
  });

  if (duplicate) {
    return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName(), duplicate: true });
  }

  var isWheel = test === 'koleso';
  sheet.appendRow([
    new Date(),
    какТекст_(d.userName || ''),
    какТекст_(d.userLogin || ''),
    id,
    isWheel ? 'Колесо эмпата' : rankName_(d.rank),
    isWheel ? '' : (d.percent || ''),
    isWheel ? '' : pick_(d.forks, 'zapros'),
    isWheel ? текст_(d.forks, 'bol') : pick_(d.forks, 'bol'),
    'Нажал «Написать Артёму»',
    '', '', '', '',
    source,
    isWheel ? сферы_(d.worst) : '',
    d.istochnik || ''
  ]);
  SpreadsheetApp.flush();
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName(), duplicate: false });
}

function статус_(tg, test, tgLogin) {
  var id = String(tg || '').trim();
  var login = String(tgLogin || '').trim().replace(/^@/, '').toLowerCase();
  var кол = test === 'koleso' ? 'koleso' : 'empat';
  var из = {
    ok: true, версия: ВЕРСИЯ, test: кол, tg: id,
    started: '0', passed: '0', anketa: '0',
    rank: '', percent: '', chtomenyat: '', sfera: '', passed_at: ''
  };
  if (!id) return из;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var лист = ss.getSheetByName(кол === 'koleso' ? ЛИСТЫ.тестКолесо : ЛИСТЫ.тест);
  var строка = последняяСтрока_(лист, id);
  if (строка) {
    из.passed = '1';
    из.started = '1';
    из.passed_at = дата_(строка['Дата']);
    if (кол === 'koleso') {
      из.sfera = String(строка['Где тяжелее'] || строка['Самые тяжёлые'] || '');
    } else {
      из.rank = String(строка['Ранг'] || '');
      из.percent = String(строка['Процент'] === undefined ? '' : строка['Процент']);
      из.chtomenyat = чтоМенять_(строка['Что менять первым']);
    }
  }
  if (из.started !== '1') {
    var старты = ss.getSheetByName(ЛИСТЫ.старты);
    var пинг = последняяСтрока_(старты, id, function (r) {
      return String(r['Тест'] || 'empat') === кол;
    });
    if (пинг) из.started = '1';
  }
  if (последняяСтрока_(ss.getSheetByName(ЛИСТЫ.предзапись), id)) из.anketa = '1';
  if (из.anketa !== '1' && заявкаССайта_(ss, login)) из.anketa = '1';
  return из;
}

function последняяСтрока_(sheet, id, фильтр) {
  if (!sheet || sheet.getLastRow() < 2) return null;
  var данные = sheet.getDataRange().getValues();
  var шапка = данные[0];
  var колId = шапка.indexOf('ID в Телеграме');
  if (колId === -1) return null;
  for (var i = данные.length - 1; i >= 1; i--) {
    if (String(данные[i][колId]).trim() !== id) continue;
    var r = {};
    for (var j = 0; j < шапка.length; j++) r[шапка[j]] = данные[i][j];
    if (фильтр && !фильтр(r)) continue;
    return r;
  }
  return null;
}

function чтоМенять_(v) {
  var слова = { otn: 'отношения', dengi: 'деньги', sily: 'свои силы', ya: 'себя' };
  var k = String(v || '').trim();
  return слова[k] || k;
}

function заявкаССайта_(ss, login) {
  if (!login) return false;
  var sheet = ss.getSheetByName(ЛИСТЫ.сайтПред);
  if (!sheet || sheet.getLastRow() < 2) return false;
  var данные = sheet.getDataRange().getValues();
  var кол = данные[0].indexOf('Телеграм');
  if (кол === -1) return false;
  for (var i = 1; i < данные.length; i++) {
    var v = String(данные[i][кол] || '').trim().toLowerCase();
    if (!v) continue;
    v = v.replace(/^@/, '').replace(/^https?:\/\//, '').replace(/^t.me\//, '').replace(/\/$/, '');
    if (v === login) return true;
  }
  return false;
}

function дата_(v) {
  if (!(v instanceof Date) || isNaN(v.getTime())) return '';
  return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

function saveLead_(d) {
  var sheet = getSheet2_(LEAD_SHEET, LEAD_HEADERS);
  sheet.appendRow([
    new Date(),
    какТекст_(d.name || ''),
    /* В поле «Телеграм» люди регулярно пишут телефон, в том числе с плюсом.
       Без защиты ячейка превращается в #ERROR!, и перезвонить некому. */
    какТекст_(d.contact || ''),
    d.userId || '',
    rankName_(d.rank),
    d.percent || '',
    pick_(d.forks, 'zapros'),
    pick_(d.forks, 'bol'),
    /* d.talk — из заявок, отправленных до 17.08: там поле называлось иначе,
       а в буфере браузера такие записи могут лежать до сих пор. */
    d.ready || d.talk || '',
    d.accept_pd || '',
    d.accept_ads || '',
    d.consent_ts || '',
    d.doc_version_consent || '',
    /* Заявки на «Прикладную эмпатию» приходят с двух тестов и ложатся в
       один лист: две таблицы на одну очередь продаж — это две очереди,
       и половину команда не обзванивает. Кто откуда — здесь.
       Значение по умолчанию про первый тест: он метку не шлёт, а строка
       без источника хуже, чем строка с угаданным. */
    d.istochnik_test || 'Тест «Эмпат ли вы»',
    сферы_(d.worst),
    d.istochnik || ''
  ]);
  /* Имя листа в ответе: видно, куда легла заявка, без чтения таблицы. */
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

/** Прохождение теста «Колесо эмпата». */
function saveKl_(d) {
  var sheet = getSheet2_(ЛИСТЫ.тестКолесо, KL_HEADERS);

  /* Колесо приходит списком, а не объектом по ключам: разворачиваем в карту,
     иначе порядок сфер зависел бы от того, как страница собрала массив. */
  var by = {};
  (d.wheel || []).forEach(function (c) { if (c && c.k) by[c.k] = c; });

  var строка = [
    new Date(),
    d.userId || '',
    какТекст_(d.userLogin || ''),
    какТекст_(d.userName || ''),
    num_(d.otdayu),
    num_(d.ostaetsya),
    num_(d.zazor)
  ];
  KL_SPHERES.forEach(function (s) { строка.push(by[s[0]] ? num_(by[s[0]].out) : ''); });
  KL_SPHERES.forEach(function (s) { строка.push(by[s[0]] ? num_(by[s[0]].inn) : ''); });
  строка.push(
    сферы_(d.worst),
    текст_(d.forks, 'bol'),
    текст_(d.forks, 'davno'),
    (d.answers || []).join(','),
    num_(d.seconds),
    d.fast ? 'да' : '',
    d.monotone ? 'да' : ''
  );

  sheet.appendRow(строка);
  SpreadsheetApp.flush();
  notifySalebot_(d, 'koleso');
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

/**
 * Лид-форма перед оплатой события «Неудобные».
 *
 * Оферту здесь не принимают: акцепт собирает страница оплаты, там же деньги
 * и там же договор. Поэтому колонок «Оферта» и «Ред. оферты» в этом листе нет,
 * и требовать accept_offer нельзя — иначе форма начнёт отбивать живые заявки.
 */
function saveKlLead_(d) {
  var sheet = getSheet2_(ЛИСТЫ.заявкиКолесо, KL_LEAD_HEADERS);
  sheet.appendRow([
    new Date(),
    какТекст_(d.name || ''),
    /* В поле контакта люди пишут телефон с плюсом. Без защиты ячейка
       превращается в #ERROR!, и написать человеку некуда. */
    какТекст_(d.contact || ''),
    d.userId || '',
    какТекст_(d.userLogin || ''),
    какТекст_(d.userName || ''),
    num_(d.otdayu),
    num_(d.ostaetsya),
    сферы_(d.worst),
    текст_(d.forks, 'bol'),
    d.accept_pd || '',
    d.accept_ads || '',
    d.consent_ts || '',
    d.doc_version_consent || '',
    d.pay || '',
    /* Откуда пришёл человек. «pryamaya-ssylka» значит, что он открыл оффер
       по прямой ссылке и теста не проходил: колонки колеса у такой заявки
       пустые не по сбою, а потому что колеса у неё нет. */
    d.istochnik || 'test'
  ]);
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

/**
 * Способ оплаты, выбранный на экране после лид-формы.
 *
 * Новую строку не заводим: заявка этого человека уже сохранена, и вторая
 * строка выглядела бы как второй лид. Ищем его последнюю заявку по ID
 * в Телеграме и дописываем колонку. Идём снизу: если человек возвращался
 * и оставлял заявку дважды, отметить нужно ту, с которой он пошёл платить.
 */
function saveKlWay_(d) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(ЛИСТЫ.заявкиКолесо);
  if (!sheet || sheet.getLastRow() < 2) {
    return json_({ ok: true, версия: ВЕРСИЯ, note: 'заявок ещё нет' });
  }

  var данные = sheet.getDataRange().getValues();
  var колId = данные[0].indexOf('ID в Телеграме');
  var колСпособ = данные[0].indexOf('Способ оплаты');
  if (колId === -1 || колСпособ === -1) {
    return json_({ ok: false, error: 'нет колонки ID или «Способ оплаты»' });
  }

  var кого = String(d.userId || '');
  for (var i = данные.length - 1; i >= 1; i--) {
    if (кого && String(данные[i][колId]) === кого) {
      sheet.getRange(i + 1, колСпособ + 1).setValue(d.pay || '');
      return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName(), строка: i + 1 });
    }
  }
  return json_({ ok: true, версия: ВЕРСИЯ, note: 'заявка не найдена, способ не записан' });
}

/** Заявка с сайта предзаписи, оплаты, брони или страницы заявки. */
function saveSite_(d) {
  if (SITE_SECRET && d.secret !== SITE_SECRET) {
    return json_({ ok: false, error: 'forbidden' });
  }

  // приманка для ботов: поле скрыто от человека, заполнить может только робот
  if (d.website) return json_({ ok: true });

  if (!String(d.name || '').trim()) {
    return json_({ ok: false, error: 'no name' });
  }
  if (!String(d.phone || '').trim() && !String(d.telegram || '').trim()) {
    return json_({ ok: false, error: 'no contact' });
  }
  // Оферту принимают только там, где платят прямо на сайте. На предзаписи
  // и на странице заявки покупки не происходит: требовать согласие
  // с договором купли-продажи там, где ничего не покупают, юридически
  // неверно. Согласие на обработку данных нужно всегда — контакты мы
  // собираем везде.
  if (d.accept_pd !== true) return json_({ ok: false, error: 'no consent' });
  if (d.form === 'оплата' && d.accept_offer !== true) {
    return json_({ ok: false, error: 'no offer' });
  }

  var name = SITE_SHEETS[d.form];
  if (!name) return json_({ ok: false, error: 'unknown form' });

  d.received_at = new Date();

  var headers = SITE_FIELDS.map(function (f) { return f[1]; });
  var sheet = getSheet2_(name, headers);
  sheet.appendRow(SITE_FIELDS.map(function (f) {
    var v = d[f[0]];
    if (v === true) return 'да';
    if (v === false) return 'нет';
    return (v === undefined || v === null) ? '' : какТекст_(v);
  }));

  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName() });
}

/**
 * Заставляет таблицу считать значение текстом.
 *
 * Телефон люди пишут как «+7 981 875 52 25». Ведущий плюс Google Таблицы
 * читают как начало формулы — и вместо номера в ячейке оказывается
 * #ERROR!. Один живой лид мы так уже потеряли: перезвонить некому.
 *
 * Апостроф впереди — штатный признак «это текст», в самой ячейке
 * он не показывается. Проверяем ещё = - @: с них тоже начинаются формулы.
 */
function какТекст_(v) {
  var s = String(v);
  return /^[=+\-@]/.test(s) ? "'" + s : v;
}

/**
 * Число как есть, включая ноль.
 *
 * Просто `d.otdayu || ''` превратил бы честный ноль в пустую ячейку,
 * а ноль в «Остаётся» — самый важный результат теста: человек не оставил
 * себе ничего. Терять его нельзя.
 */
function num_(v) {
  if (v === 0) return 0;
  return (v === undefined || v === null || v === '') ? '' : v;
}

function getSheet2_(name, headers) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name) || ss.insertSheet(name);

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
    return sheet;
  }

  /* Лист уже с данными, а колонок стало больше — подписываем только пустые
     ячейки шапки. Названия, поставленные руками, не трогаем: если колонку
     переименовали в таблице, это решение человека, а не сбой.
     Строки с данными не трогаем никогда. */
  if (sheet.getMaxColumns() < headers.length) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), headers.length - sheet.getMaxColumns());
  }
  var have = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  var fixed = [];
  var need = false;
  for (var i = 0; i < headers.length; i++) {
    var cur = String(have[i] == null ? '' : have[i]).trim();
    fixed.push(cur ? have[i] : headers[i]);
    if (!cur) need = true;
  }
  if (need) {
    sheet.getRange(1, 1, 1, headers.length).setValues([fixed]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/* Раньше эта функция подписывала шапку только у пустого листа: колонка,
   добавленная в HEADERS позже, получала данные, но оставалась без заголовка.
   На «Источнике» 06.09 это и всплыло. Отдаём работу getSheet2_ — он дописывает
   только пустые ячейки шапки, названия, поставленные руками, не трогает,
   строки с данными не трогает никогда. */
function getSheet_() {
  return getSheet2_(SHEET_NAME, HEADERS);
}

function rankName_(key) {
  var names = {
    donor: 'Эмпат-донор',
    filter: 'Эмпат без фильтра',
    sleeping: 'Спящий эмпат',
    awake: 'Проснувшийся эмпат',
    reader: 'Считывающий',
    caring: 'Сочувствующий',
    other: 'Другая настройка'
  };
  return names[key] || key || '';
}

function pick_(obj, key) {
  return (obj && obj[key]) ? obj[key] : '';
}

/**
 * Читаемый ответ на вопрос-развилку.
 *
 * Страница шлёт два поля: «bol» с машинным ключом (semya) и «bol_text»
 * с тем, что человек видел на кнопке («Семья и близкие»). В таблицу нужен
 * второй: её читают люди, а не скрипт. Ключ оставлен запасным вариантом
 * на случай старых записей из буфера браузера, где _text ещё не было.
 */
function текст_(obj, key) {
  if (!obj) return '';
  return obj[key + '_text'] || obj[key] || '';
}

/** Ключи сфер («partner,telo») — в человеческие имена («Партнёр, Тело и силы»). */
function сферы_(строка) {
  var карта = {};
  KL_SPHERES.forEach(function (s) { карта[s[0]] = s[1]; });
  return String(строка || '').split(',')
    .map(function (k) { k = k.trim(); return карта[k] || k; })
    .filter(function (x) { return x; })
    .join(', ');
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/** Сводка по вкладкам из ЛИСТЫ: что найдено, сколько строк, что есть в таблице. */
function обзорЛистов_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var из = {};
  Object.keys(ЛИСТЫ).forEach(function (ключ) {
    var sheet = ss.getSheetByName(ЛИСТЫ[ключ]);
    из[ключ] = {
      имя: ЛИСТЫ[ключ],
      есть: !!sheet,
      строк: sheet ? Math.max(0, sheet.getLastRow() - 1) : 0
    };
  });
  из['всеВкладки'] = ss.getSheets().map(function (s) { return s.getName(); });
  return из;
}

/* ───────────────────────────── уборка тестовых строк ──
   Запускается вручную из редактора: выбрать в списке функций
   «удалитьТестовыеСтроки» и нажать «Выполнить».

   Удаляет только те строки, где имя начинается с «ТЕСТ» или «ЗОНД».
   Настоящие заявки не трогает: под удаление попадает ровно то, что мы
   сами и пометили. Колонка «Имя» ищется по заголовку, а не по номеру, —
   у листов разный порядок столбцов, и жёсткий индекс однажды снёс бы не то. */

function удалитьТестовыеСтроки() {
  var листы = [ЛИСТЫ.тест, ЛИСТЫ.предзапись, ЛИСТЫ.сайтПред, ЛИСТЫ.сайтОплата,
               ЛИСТЫ.тестКолесо, ЛИСТЫ.заявкиКолесо];
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var отчёт = [];

  листы.forEach(function (имя) {
    var sheet = ss.getSheetByName(имя);
    if (!sheet || sheet.getLastRow() < 2) return;

    var данные = sheet.getDataRange().getValues();
    var колонка = данные[0].indexOf('Имя');
    if (колонка === -1) return;

    /* Идём снизу вверх: при удалении сверху номера оставшихся строк
       съезжают, и половина попала бы мимо. */
    var удалено = 0;
    for (var i = данные.length - 1; i >= 1; i--) {
      var значение = String(данные[i][колонка] || '').trim().toUpperCase();
      if (значение.indexOf('ТЕСТ') === 0 || значение.indexOf('ЗОНД') === 0) {
        sheet.deleteRow(i + 1);
        удалено++;
      }
    }
    if (удалено) отчёт.push(имя + ': ' + удалено);
  });

  var текст = отчёт.length ? ('Удалено — ' + отчёт.join('; ')) : 'Тестовых строк не найдено';
  Logger.log(текст);
  try { SpreadsheetApp.getUi().alert(текст); } catch (e) {}   // из редактора UI недоступен
  return текст;
}

/* ─────────────────────────── проверка имён вкладок ──
   Запускается вручную из редактора. Показывает, какие из имён выше
   действительно существуют в таблице, а какие скрипт не находит
   и создаст заново при первой же заявке. */

function notifySalebot_(d, test) {
  var props = PropertiesService.getScriptProperties();

  if (props.getProperty('SALEBOT_ENABLED') !== '1') return;

  var userId = String(d.userId || '').trim();
  var apiKey = props.getProperty('SALEBOT_API_KEY');

  if (!userId || !apiKey) {
    console.error('SaleBot: отсутствует userId или API-ключ');
    return;
  }

  try {
    var status = статус_(userId, test, d.userLogin || '');
    var prefix = test === 'koleso' ? 'wheel' : 'empat';

    if (status.passed !== '1') {
      console.error('SaleBot: результат не найден в таблице');
      return;
    }

    var payload = {
      user_id: userId,
      group_id: 'viola_maro_bot',
      message: test === 'koleso'
        ? 'wheel_completed_api'
        : 'empat_completed_api'
    };

    payload[prefix + '_started'] = status.started;
    payload[prefix + '_completed'] = status.passed;
    payload[prefix + '_anketa'] = status.anketa;
    payload[prefix + '_passed_at'] = status.passed_at;

    if (test === 'koleso') {
      payload.wheel_sfera = status.sfera;
    } else {
      payload.empat_rank = status.rank;
      payload.empat_percent = status.percent;
      payload.empat_chtomenyat = status.chtomenyat;
    }

    var response = UrlFetchApp.fetch(
      'https://chatter.salebot.pro/api/' + apiKey + '/tg_callback',
      {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      }
    );

    console.log(
      'SaleBot: HTTP ' + response.getResponseCode() +
      '; ответ: ' + response.getContentText()
    );
  } catch (error) {
    console.error('SaleBot: ошибка отправки события');
  }
}

function проверитьЛисты() {
  var обзор = обзорЛистов_();
  var строки = [];

  Object.keys(ЛИСТЫ).forEach(function (ключ) {
    var x = обзор[ключ];
    строки.push((x.есть ? '✔ ' : '✘ ') + ключ + ': «' + x.имя + '»'
                + (x.есть ? ' — строк: ' + x.строк : ' — ВКЛАДКИ НЕТ, будет создана заново'));
  });

  var текст = 'Версия скрипта в редакторе: ' + ВЕРСИЯ + '\n\n'
    + строки.join('\n')
    + '\n\nВкладки в таблице: ' + обзор['всеВкладки'].join(' | ');
  Logger.log(текст);
  try { SpreadsheetApp.getUi().alert(текст); } catch (e) {}
  return текст;
}
