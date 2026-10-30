/**
 * Приёмник анкеты для интервью (кастдевов) Виолы.
 *
 * Скрипт при отдельной таблице «Анкета для интервью». С таблицей заявок
 * (integrations/google-sheets) и анкетой участниц не связан.
 * Страница: violamaro.ru/intervyu/ (miniapps/intervyu/index.html).
 *
 * Что делает: принимает анкету и дописывает строку в лист «Ответы».
 * Листа нет, скрипт заводит его сам вместе с шапкой.
 * Колонку «Статус» скрипт не трогает: её ведёт команда руками.
 *
 * ⚠ После правок: Развернуть → Управление развёртываниями → карандаш →
 * Версия: «Новая версия» → Развернуть. Адрес /exec при этом не меняется.
 */

var ВЕРСИЯ = '2026-10-30 intervyu';
var ЛИСТ = 'Ответы';
var ШАПКА = [
  'Дата', 'Ник в Телеграме', 'ID в Телеграме',
  'Имя', 'Возраст', 'Где смотрит', 'Как давно смотрит', 'Что забирает силы',
  'Где сейчас (минус, ноль, единица)', 'Что проходила у Виолы', 'Готова вложить', 'Интервью',
  'Согласие на ПД', 'Время акцепта', 'Ред. согласия', 'Статус'
];
var ВОПРОСОВ = 9;
var КОЛОНОК = 3 + ВОПРОСОВ + 3;

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    var d = JSON.parse(e.postData.contents);
    lock.waitLock(20000);
    return save_(d);
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

function doGet() {
  var sheet = лист_();
  return json_({
    ok: true,
    note: 'Приёмник анкеты для интервью жив',
    версия: ВЕРСИЯ,
    лист: sheet.getName(),
    анкет: Math.max(0, sheet.getLastRow() - 1)
  });
}

function save_(d) {
  /* Приманка для роботов: отвечаем «ок» и ничего не пишем. */
  if (d.website) return json_({ ok: true, версия: ВЕРСИЯ });

  var ник = String(d.nick == null ? '' : d.nick).trim();
  if (!ник) return json_({ ok: false, error: 'нет ника в Телеграме' });
  if (d.accept_pd !== true && d.accept_pd !== 'да') {
    return json_({ ok: false, error: 'нет согласия на обработку данных' });
  }

  var sheet = лист_();
  var ответы = d.answers || {};
  var строка = [
    Utilities.formatDate(new Date(), 'Europe/Moscow', 'dd.MM.yyyy HH:mm:ss'),
    какТекст_(ник),
    какТекст_(d.tg_id == null ? '' : d.tg_id)
  ];
  for (var i = 1; i <= ВОПРОСОВ; i++) строка.push(ячейка_(ответы['q' + i]));
  строка.push('да', какТекст_(d.consent_ts || ''), какТекст_(d.doc_version_consent || ''));

  if (строка.length !== КОЛОНОК) {
    return json_({ ok: false, error: 'собрано колонок: ' + строка.length + ', нужно ' + КОЛОНОК });
  }
  sheet.appendRow(строка);
  SpreadsheetApp.flush();
  return json_({ ok: true, версия: ВЕРСИЯ, лист: sheet.getName(), строка: sheet.getLastRow() });
}

function ячейка_(v) {
  if (v === undefined || v === null) return '';
  if (Object.prototype.toString.call(v) === '[object Array]') {
    var части = [];
    for (var i = 0; i < v.length; i++) {
      var s = String(v[i] == null ? '' : v[i]).trim();
      if (s) части.push(s);
    }
    return какТекст_(части.join(', '));
  }
  if (v === true) return 'да';
  if (v === false) return '';
  if (typeof v === 'number') return v;
  return какТекст_(String(v));
}

/* Текст, начинающийся с «=», «+», «-» или «@», пишем с апострофом,
   иначе таблица примет его за формулу (прочерк «-» дал бы ошибку). */
function какТекст_(v) {
  var s = String(v);
  return /^[=+\-@]/.test(s) ? "'" + s : v;
}

function лист_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(ЛИСТ);
  if (!sheet) {
    sheet = ss.insertSheet(ЛИСТ);
    sheet.appendRow(ШАПКА);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, ШАПКА.length).setFontWeight('bold');
  }
  return sheet;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
