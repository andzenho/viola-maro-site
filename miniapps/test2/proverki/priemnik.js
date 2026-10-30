// Прогон приёмника таблицы на поддельной таблице: тест 2.0 и то, что старые маршруты не сломаны.
const fs = require('fs'), vm = require('vm');
const code = fs.readFileSync(process.argv[2], 'utf8');

function Sheet(name) { this.name = name; this.rows = []; this.cols = 26; this.bg = {}; }
Sheet.prototype = {
  getName() { return this.name; },
  getLastRow() { return this.rows.length; },
  getMaxColumns() { return this.cols; },
  insertColumnsAfter(a, n) { this.cols += n; },
  setFrozenRows() {},
  appendRow(r) { this.rows.push(r.slice()); },
  deleteRow(i) { this.rows.splice(i - 1, 1); },
  getDataRange() { const self = this; return { getValues() { const w = Math.max(...self.rows.map(r => r.length)); return self.rows.map(r => { const x = r.slice(); while (x.length < w) x.push(''); return x; }); } }; },
  getRange(r, c, nr, nc) {
    const self = this; nr = nr || 1; nc = nc || 1;
    return {
      getValues() { const out = []; for (let i = 0; i < nr; i++) { const row = self.rows[r - 1 + i] || []; const o = []; for (let j = 0; j < nc; j++) o.push(row[c - 1 + j] === undefined ? '' : row[c - 1 + j]); out.push(o); } return out; },
      getDisplayValues() { return this.getValues().map(r => r.map(x => String(x))); },
      setBackground(c) { for (let i = 0; i < nr; i++) self.bg[r - 1 + i] = c; },
      setValues(v) { for (let i = 0; i < nr; i++) { self.rows[r - 1 + i] = self.rows[r - 1 + i] || []; for (let j = 0; j < nc; j++) self.rows[r - 1 + i][c - 1 + j] = v[i][j]; } },
      setValue(v) { self.rows[r - 1] = self.rows[r - 1] || []; self.rows[r - 1][c - 1] = v; }
    };
  }
};
const sheets = {};
const ss = {
  getSheetByName(n) { return sheets[n] || null; },
  insertSheet(n) { sheets[n] = new Sheet(n); return sheets[n]; },
  getSheets() { return Object.values(sheets); }
};
const fetched = [];
const props = { SALEBOT_ENABLED: null, SALEBOT_T2_ENABLED: null, SALEBOT_API_KEY: 'KEY' };
const ctx = {
  SpreadsheetApp: { getActiveSpreadsheet: () => ss, flush() {}, getUi() { throw new Error('no ui'); } },
  ContentService: { MimeType: { JSON: 'json' }, createTextOutput(t) { return { text: t, setMimeType() { return this; } }; } },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] }) },
  Utilities: { formatDate: d => d.toISOString().slice(0, 10) },
  Session: { getScriptTimeZone: () => 'Europe/Moscow' },
  UrlFetchApp: { fetch(url, o) { fetched.push(JSON.parse(o.payload)); return { getResponseCode: () => 200, getContentText: () => 'ok' }; } },
  Logger: { log() {} }, console: { log() {}, error() {} }
};
vm.createContext(ctx);
vm.runInContext(code, ctx);

const get = payload => JSON.parse(ctx.doGet({ parameter: { payload: JSON.stringify(payload) } }).text);
const status = (tg, test) => JSON.parse(ctx.doGet({ parameter: { action: 'status', tg: String(tg), test } }).text);
const row = (name, i) => { const s = sheets[name]; const h = s.rows[0]; const o = {}; h.forEach((k, j) => { o[k] = s.rows[i][j] === undefined ? '' : s.rows[i][j]; }); return o; };
let fails = 0;
function ok(cond, what) { if (!cond) { fails++; console.log('  ✘ ' + what); } else console.log('  ✔ ' + what); }

console.log('— тест 2.0 —');
const base = { form: 'test2', test: 'empat2', pid: 'pAAA', userId: 777, userLogin: '@maria', userName: 'Мария П', istochnik: 'reels' };
let r = get({ type: 'start', test: 'empat2', pid: 'pAAA', userId: 777, istochnik: 'reels' });
ok(r.ok && sheets['Старты теста'].rows.length === 2, 'старт записан в «Старты теста»');
r = get({ type: 'start', test: 'empat2', pid: 'pWEB', userId: '', istochnik: 'share' });
ok(r.ok && sheets['Старты теста'].rows[2][1] === 'pWEB', 'старт без Телеграма пишется по номеру прохождения');
ok(status(777, 'empat2').started === '1' && status(777, 'empat2').passed === '0', 'статус: начал, не прошёл');

// отметка раньше прохождения — в журнал
r = get(Object.assign({}, base, { type: 't2_event', event: 'scroll', block: 'Тип' }));
ok(r.ok && /журнале/.test(r.note || ''), 'отметка без прохождения уходит в журнал');

r = get(Object.assign({}, base, { type: 't2_result', rank: 'donor', percent: 96, sphere: 'telo',
  scales: { A: 8, P: 9, I: 5, B: 7, C: 12, G: 4, L: 5, F: 1, K: 0 }, spheres: { ya: 5, otn: 5, semya: 1, telo: 6, delo: 1, dengi: 3 },
  age: '45–54', words: '+ хочу научиться отказывать', forks: { bol: 'partner', bol_text: 'Партнёр' }, answers: [3, 3, 2], seconds: 211,
  ryadom_n: 3, ryadom_list: 'отказать, даром, радары' }));
ok(r.ok && r.лист === 'Тест 2.0', 'прохождение легло в «Тест 2.0»');
let t = row('Тест 2.0', 1);
ok(t['Профиль'] === 'Эмпат-донор' && t['Сфера'] === 'Тело и здоровье' && t['Возраст'] === '45–54', 'профиль, сфера, возраст');
ok(t['Считывает людей (A)'] === 8 && t['Чужое заходит внутрь (P)'] === 9 && t['Тело отзывается (B)'] === 7 && t['Отдаёт другим (C)'] === 12, 'четыре шкалы числами, P без переворота');
ok(t['Контроль'] === 0, 'нулевой балл не превращается в пустую ячейку');
ok(t['Утверждений показано'] === 3 && t['Какие утверждения'] === 'отказать, даром, радары', 'блок «Почему пользуются»: сколько утверждений показано и какие');
ok(t['Что изменить (свои слова)'] === "'+ хочу научиться отказывать", 'свои слова с плюсом защищены от формулы');
ok(t['Где съедает'] === 'Партнёр' && t['Источник'] === 'reels' && t['Логин в Телеграме'] === "'@maria", 'вилка, источник, логин');
ok(sheets['Тест 2.0'].rows[0].length === sheets['Тест 2.0'].rows[1].length, 'строка той же ширины, что шапка');
ok(sheets['Тест эмпата'] === undefined, 'в лист первого теста ничего не попало');
ok(fetched.length === 0, 'SaleBot молчит, пока выключатель не включён');

r = get(Object.assign({}, base, { type: 't2_event', event: 'scroll', block: 'Сегодня вечером' }));
r = get(Object.assign({}, base, { type: 't2_event', event: 'scroll', block: 'Что видно по ответам' }));
ok(row('Тест 2.0', 1)['Долистала до'] === 'Сегодня вечером', '«Долистала до» хранит самый дальний блок');
r = get(Object.assign({}, base, { type: 't2_event', event: 'channel' }));
ok(row('Тест 2.0', 1)['Перешла в канал'] === 'открытый канал', 'переход в канал отмечен');
r = get(Object.assign({}, base, { type: 't2_event', event: 'form_open', block: 'Что дальше' }));
t = row('Тест 2.0', 1);
ok(t['Кнопка анкеты'] === 'да, в блоке «Что дальше»' && t['Долистала до'] === 'Что дальше', 'кнопка анкеты отмечена вместе с блоком, где её нажали');
ok(status(777, 'empat2').passed === '1' && status(777, 'empat2').anketa === '0' && status(777, 'empat2').sfera === 'Тело и здоровье', 'статус: прошёл, анкеты нет, сфера отдаётся');

props.SALEBOT_T2_ENABLED = '1';
r = get(Object.assign({}, base, { type: 't2_lead', name: 'Мария', contact: '+7 900 000-00-00', change: 'Отказывать', tried: 'Книги',
  ready: 9, konsultaciya: 'da', leader: '', rank: 'donor', sphere: 'telo', age: '45–54', accept_pd: 'да', accept_ads: '', consent_ts: '2026-10-03T10:00:00Z', doc_version_consent: '2026-08-10' }));
ok(r.ok && r.лист === 'Предзапись с теста 2.0', 'анкета легла в «Предзапись с теста 2.0»');
let a = row('Предзапись с теста 2.0', 1);
ok(a['Статус'] === 'анкета' && a['Разметка'] === 'горячая' && a['Готовность (1–10)'] === 9, 'статус, готовность, разметка');
ok(a['Контакт'] === "'+7 900 000-00-00", 'телефон с плюсом защищён');
ok(a['Написать ей'] === 'да', 'ответ про Дарью записан отдельной колонкой');
ok(a['Профиль'] === 'Эмпат-донор' && a['Сфера'] === 'Тело и здоровье' && a['Источник'] === 'reels', 'профиль, сфера, источник в анкете');
ok(sheets['Предзапись с теста 2.0'].rows[0].length === sheets['Предзапись с теста 2.0'].rows[1].length, 'анкета той же ширины, что шапка');
ok(row('Тест 2.0', 1)['Анкета'] === 'да', 'в прохождении отмечено, что анкета отправлена');
ok(row('Тест 2.0', 1)['Кнопка анкеты'] === 'да, в блоке «Что дальше»', 'анкета не затирает, с какой кнопки в неё пришли');
ok(status(777, 'empat2').anketa === '1', 'статус: анкета есть');
ok(fetched.length === 1 && fetched[0].message === 'empat2_anketa_api' && fetched[0].empat2_anketa === '1', 'SaleBot получил событие анкеты');

// та же анкета досылается из памяти телефона: второй строки нет, бот молчит
const rowsBefore = sheets['Предзапись с теста 2.0'].rows.length, fetchedBefore0 = fetched.length;
r = get(Object.assign({}, base, { type: 't2_lead', name: 'Мария', contact: '+7 900 000-00-00', change: 'Отказывать', tried: 'Книги',
  ready: 9, konsultaciya: 'da', leader: '', rank: 'donor', sphere: 'telo', age: '45–54', accept_pd: 'да', accept_ads: '', consent_ts: '2026-10-03T10:00:00Z', doc_version_consent: '2026-08-10' }));
const sh2 = sheets['Предзапись с теста 2.0'];
ok(r.ok && r.duplicate === true && sh2.rows.length === rowsBefore + 1 && sh2.bg[rowsBefore] === '#FFF2CC' && !sh2.bg[rowsBefore - 1] && fetched.length === fetchedBefore0, 'повтор той же анкеты записан, покрашен, бот молчит');
sh2.rows.splice(rowsBefore, 1); delete sh2.bg[rowsBefore];

// анкета с кнопки бота: результата в браузере нет, pid новый
r = get({ type: 't2_lead', form: 'test2', test: 'empat2', pid: 'pNEW', userId: 777, name: 'Мария', contact: '@maria', ready: 4, konsultaciya: 'net', rank: '', sphere: '', age: '' });
a = row('Предзапись с теста 2.0', 2);
ok(a['Профиль'] === 'Эмпат-донор' && a['Сфера'] === 'Тело и здоровье' && a['Возраст'] === '45–54' && a['Разметка'] === 'холодная', 'анкета с кнопки бота: профиль взят из прохождения');
ok(a['Написать ей'] === 'нет', 'отказ от переписки записан как «нет»');
ok(fetched[fetched.length - 1].empat2_konsultaciya === 'net', 'боту уходит ответ про Дарью');
r = get({ type: 't2_whatever', form: 'test2', test: 'empat2' });
ok(r.ok === false, 'неизвестный тип записи отклонён');

// анкета открыта плавающей кнопкой: место пишется как есть, «Долистала до» не меняется
r = get(Object.assign({}, base, { type: 't2_event', event: 'form_open', block: 'плавающая кнопка' }));
t = row('Тест 2.0', 1);
ok(r.ok && t['Кнопка анкеты'] === 'да, плавающая кнопка' && t['Долистала до'] === 'Что дальше', 'плавающая кнопка: место записано, «Долистала до» не тронуто');

console.log('— старые маршруты —');
r = get({ rank: 'filter', percent: 80, scales: { A: 7, P: 8, I: 3, B: 8, C: 6, G: 2, L: 3, F: 0, K: 0 }, forks: { bol: 'semya', zapros: 'sily' }, answers: [1, 2], userId: 555, userName: 'Олег', istochnik: 'kanal' });
ok(r.ok && r.лист === 'Тест эмпата' && sheets['Тест эмпата'].rows[1][3] === 'Эмпат без фильтра', 'первый тест пишется как раньше');
r = get({ type: 'lead', name: 'Олег', contact: '@oleg', ready: 'готов сейчас', rank: 'filter', percent: 80, userId: 555, forks: {} });
ok(r.ok && r.лист === 'Предзапись с теста', 'заявка первого теста пишется как раньше');
ok(status(555, 'empat').passed === '1' && status(555, 'empat').anketa === '1', 'статус первого теста');
ok(status(555, 'empat2').passed === '0' && status(555, 'empat2').anketa === '0', 'заявка первого теста не считается анкетой теста 2.0');
r = get({ test: 'koleso', type: 'lead', name: 'Ира', contact: '@ira', userId: 999 });
ok(r.ok && r.лист === 'Неудобная — заявки', 'заявка «Колеса» пишется как раньше');
r = get({ type: 'start', test: 'empat', userId: '' });
ok(r.ok && r.note === 'без ID не пишем', 'старт первого теста без ID по-прежнему не пишется');
r = get({ form: 'непонятно' });
ok(r.ok === false, 'неизвестная форма по-прежнему отклоняется');
console.log('— главная violamaro.ru (19.10) —');
const post = payload => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(payload) } }).text);
const SECRET = 'PxlGXL9bQSjc0dHcLoiCZJZWtNdfv9D8yY9SHBuJ';
const siteLead = extra => Object.assign({ secret: SECRET, website: '', form: 'заявка', name: 'Анна', phone: '', telegram: '@anna',
  readiness: 'Заявка с главной, без оплаты', plan: 'С Виолой', situation: 'мама обижается на отказы', price: 'по заявке', gifts: 'да',
  deadline: '2026-10-21T08:00:00.000Z', blok: 'Тарифы: С Виолой', accept_pd: true, accept_ads: false, consent_ts: '2026-10-19T08:00:00Z',
  doc_version_consent: '2026-08-10', page: 'https://violamaro.ru/?uid=888' }, extra);
r = post({ form: 'визит', secret: SECRET, uid: '888', first: '2026-10-19T08:00:00.000Z', deadline: '2026-10-21T08:00:00.000Z', page: 'https://violamaro.ru/?uid=888' });
ok(r.ok && r.лист === 'Сайт: цена по заявке' && row('Сайт: цена по заявке', 1)['ID в Телеграме'] === '888', 'заход с uid: срок цены по заявке записан');
r = post({ form: 'визит', secret: SECRET, uid: '888', first: 'x', deadline: 'y' });
ok(r.ok && sheets['Сайт: цена по заявке'].rows.length === 2, 'повторный заход не дублирует строку');
r = post({ form: 'визит', secret: 'нет', uid: '889' });
ok(r.ok === false, 'заход без секрета отклонён');
const anketBefore = sheets['Предзапись с теста 2.0'].rows.length;
const fetchedBefore = fetched.length;
r = post(siteLead({ uid: '' }));
let z = row('Заявки на продукт', sheets['Заявки на продукт'].rows.length - 1);
ok(r.ok && z['Что происходит'] === 'мама обижается на отказы' && z['Тариф'] === 'С Виолой' && z['Цена, которую видел'] === 'по заявке' && z['Подарки'] === 'да', 'заявка с главной без uid: «Заявки на продукт», новые колонки');
ok(sheets['Предзапись с теста 2.0'].rows.length === anketBefore, 'без uid в лист Дарьи не пишется');
r = post(siteLead({ uid: '888' }));
a = row('Предзапись с теста 2.0', sheets['Предзапись с теста 2.0'].rows.length - 1);
ok(r.ok && a['ID в Телеграме'] === '888' && a['Статус'] === 'заявка на /zayavka' && a['Источник'] === 'сайт', 'заявка с uid: строка в «Предзапись с теста 2.0»');
ok(/Тариф: С Виолой/.test(a['Женщина-лидер']) && /Цена по заявке до/.test(a['Женщина-лидер']) && /Подарки: да/.test(a['Женщина-лидер']) && a['Что хочет изменить'] === 'мама обижается на отказы', 'тариф, цена и срок цены в строке Дарьи');
ok(status(888, 'empat2').anketa === '1', 'статус по uid: anketa = 1, бот ставит t2_anketa');
ok(fetched.length === fetchedBefore + 1 && fetched[fetched.length - 1].user_id === '888' && fetched[fetched.length - 1].empat2_anketa === '1', 'SaleBot получил событие заявки с сайта');
r = post(siteLead({ uid: '777', telegram: '', phone: '+7 900 111-22-33' }));
a = row('Предзапись с теста 2.0', sheets['Предзапись с теста 2.0'].rows.length - 1);
ok(a['Профиль'] === 'Эмпат-донор' && a['Сфера'] === 'Тело и здоровье' && a['Контакт'] === "'+7 900 111-22-33", 'заявка с uid прошедшей тест: профиль и сфера из прохождения');
r = post(siteLead({ uid: '889', phone: '+7 900 222-33-44', telegram: '@anna' }));
z = row('Заявки на продукт', sheets['Заявки на продукт'].rows.length - 1);
a = row('Предзапись с теста 2.0', sheets['Предзапись с теста 2.0'].rows.length - 1);
ok(z['Телефон'] === "'+7 900 222-33-44" && z['Телеграм'] === "'@anna" && a['Контакт'] === "'+7 900 222-33-44" && a['Логин в Телеграме'] === "'@anna", 'заявка с телефоном и Telegram: оба в своих колонках');
ok(row('Тест 2.0', 1)['Анкета'] === 'да (сайт)', 'в прохождении отмечено, что заявка пришла с сайта');
r = post(siteLead({ uid: '888', accept_pd: false }));
ok(r.ok === false, 'без согласия на ПД заявка с главной отклоняется');

console.log('— анкета для интервью /intervyu/ (30.10) —');
const ksdv = extra => Object.assign({ form: 'ксдв', secret: SECRET, website: '', nick: '@anna_m', tg_id: '',
  answers: { q1: 'Анна', q2: '42', q3: ['YouTube', 'Telegram'], q4: 'Больше года', q5: ['Деньги', 'Дети'],
    q6: 'Мне тяжело, сил почти не осталось', q7: '-', q8: 'До 10 000 ₽', q9: 'Да' },
  accept_pd: true, consent_ts: '2026-10-30T10:00:00Z', doc_version_consent: '2026-08-10', page: 'https://violamaro.ru/intervyu/' }, extra);
r = post(ksdv());
let k = row('Кастдев', 1);
ok(r.ok && r.лист === 'Кастдев' && k['Ник в Телеграме'] === "'@anna_m" && k['Имя'] === 'Анна' && k['Где смотрит'] === 'YouTube, Telegram'
  && k['Что забирает силы'] === 'Деньги, Дети' && k['Интервью'] === 'Да' && k['Согласие на ПД'] === 'да' && k['Статус'] === '',
  'анкета для интервью: строка в «Кастдев», колонки на местах, «Статус» пустой');
ok(sheets['Кастдев'].rows[0].length === 16 && sheets['Кастдев'].rows[1].length === 15, 'в «Кастдев» 16 колонок, «Статус» команда ведёт руками');
r = post(ksdv({ secret: 'нет' }));
ok(r.ok === false && sheets['Кастдев'].rows.length === 2, 'анкета без секрета отклонена');
r = post(ksdv({ accept_pd: false }));
ok(r.ok === false && sheets['Кастдев'].rows.length === 2, 'анкета без согласия на ПД отклонена');
r = post(ksdv({ nick: ' ' }));
ok(r.ok === false && sheets['Кастдев'].rows.length === 2, 'анкета без ника отклонена');
r = post(ksdv({ website: 'spam' }));
ok(r.ok && sheets['Кастдев'].rows.length === 2, 'бот (заполнил скрытое поле) не пишется');

r = JSON.parse(ctx.doGet({ parameter: {} }).text);
ok(r.версия === '2026-10-30 kastdev', 'версия приёмника: ' + r.версия);

console.log(fails ? '\nПРОВАЛОВ: ' + fails : '\nВсе проверки пройдены');
process.exit(fails ? 1 : 0);
