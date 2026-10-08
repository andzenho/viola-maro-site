/**
 * Приёмник анкеты участниц «Прикладной эмпатии».
 *
 * Отдельный скрипт при отдельной таблице «Анкета участниц Прикладной эмпатии».
 * С таблицей заявок и её скриптом (integrations/google-sheets) никак не связан.
 * Страница анкеты: violamaro.ru/anketa/ (miniapps/anketa/index.html).
 *
 * Что делает: принимает анкету и дописывает одну строку в лист «Ответы».
 * Порядок колонок задан шапкой листа и здесь не меняется:
 *   A  Дата
 *   B  Ник в Телеграме
 *   C  ID в Телеграме
 *   D–AM  вопросы 1–36 по порядку
 *   AN Согласие на ПД
 *   AO Время акцепта
 *   AP Ред. согласия
 *   AQ Статус бонусов — скрипт не заполняет, её ведёт служба заботы
 *
 * ⚠ После правок: Развернуть → Управление развёртываниями → карандаш →
 * Версия: «Новая версия» → Развернуть. Адрес /exec при этом не меняется.
 * Новое развёртывание вместо правки старого даст другой адрес, и анкеты
 * перестанут доходить: адрес вшит в страницу (CONFIG.sheetUrl).
 * Проверить, что развернулось: открыть адрес /exec в браузере, в ответе
 * будет поле «версия».
 */

var ВЕРСИЯ = '2026-10-08 anketa-pe';
var ТАБЛИЦА = '1dYZyoSKwsLMmo2oy2oJB74FuLk7HkihuHPh224S3fAs';
var ЛИСТ = 'Ответы';
var ВОПРОСОВ = 36;
/* Сколько колонок заполняет скрипт: дата, ник, ID, 36 вопросов, согласие,
   время акцепта, редакция согласия. Сорок третья, «Статус бонусов», не его. */
var КОЛОНОК = 3 + ВОПРОСОВ + 3;

/** Страница шлёт анкету обычным POST с телом в JSON. */
function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    var d = JSON.parse(e.postData.contents);
    /* Две анкеты в одну секунду не должны сесть в одну строку. */
    lock.waitLock(20000);
    return save_(d);
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

/** Открыли адрес в браузере: показываем, что приёмник жив и какая версия. */
function doGet() {
  var sheet = лист_();
  return json_({
    ok: true,
    note: 'Приёмник анкеты участниц жив',
    версия: ВЕРСИЯ,
    лист: sheet ? sheet.getName() : 'НЕ НАЙДЕН: ' + ЛИСТ,
    анкет: sheet ? Math.max(0, sheet.getLastRow() - 1) : 0
  });
}

function save_(d) {
  /* Приманка: человек это поле не видит, заполнить его может только робот.
     Отвечаем «ок», чтобы он не подбирал другие способы, и ничего не пишем. */
  if (d.website) return json_({ ok: true, версия: ВЕРСИЯ });

  var ник = String(d.nick == null ? '' : d.nick).trim();
  if (!ник) return json_({ ok: false, error: 'нет ника в Телеграме' });
  if (d.accept_pd !== true && d.accept_pd !== 'да') {
    return json_({ ok: false, error: 'нет согласия на обработку данных' });
  }

  var sheet = лист_();
  if (!sheet) return json_({ ok: false, error: 'в таблице нет листа «' + ЛИСТ + '»' });

  var ответы = d.answers || {};
  var строка = [
    /* Время по Москве текстом вида 08.10.2026 15:04:05: таблица сама читает
       его как дату, и оно не зависит от часового пояса самой таблицы. */
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

/** Ответ на один вопрос — одной ячейкой. Несколько вариантов идут через запятую. */
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

/**
 * Текст, который не превратится в формулу. Ячейка, начинающаяся с «=», «+»,
 * «-» или «@», иначе стала бы формулой: ник «@anna» дал бы ошибку вместо ника,
 * а ответ, начатый с тире, — #ERROR!. Тот же приём, что в скрипте таблицы заявок.
 */
function какТекст_(v) {
  var s = String(v);
  return /^[=+\-@]/.test(s) ? "'" + s : v;
}

function лист_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet() || SpreadsheetApp.openById(ТАБЛИЦА);
  return ss.getSheetByName(ЛИСТ);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
