// Возврат в пройденный тест и вход из браузера (правка 19.10).
// Страница отдаётся с violamaro.ru через перехват, Телеграм и приёмник таблицы — заглушки,
// в сеть ничего не уходит. Нужен Playwright с Chromium.
//   node miniapps/test2/proverki/vozvrat.cjs [путь к index.html]
// Снимки экранов кладёт в папку из SHOTS, если она задана.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PAGE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'index.html'));
const OUT = process.env.SHOTS || '';
if (OUT) fs.mkdirSync(OUT, { recursive: true });
const GAS = 'https://script.google.com/macros/s/';

function tgStub(o) {
  const api = 'ready(){},expand(){},close(){window.__closed=true},openTelegramLink(u){window.__opened=u},' +
    'openLink(u){window.__link=u},onEvent(){},setHeaderColor(){},setBackgroundColor(){},disableVerticalSwipes(){}';
  if (!o.inTg) return `window.Telegram={WebApp:{initData:"",initDataUnsafe:{},${api}}};`;
  const user = o.noUser ? '' : `user:{id:${o.userId || 111},username:"tester",first_name:"Тест"},`;
  return `window.Telegram={WebApp:{initData:"user=%7B%7D&hash=x",initDataUnsafe:{${user}start_param:${JSON.stringify(o.sp || '')}},${api}}};`;
}

const results = [];
function check(name, cond, info) {
  results.push({ name, ok: !!cond, info });
  console.log((cond ? 'OK   ' : 'FAIL ') + name + (info !== undefined ? '  ' + JSON.stringify(info) : ''));
}

async function open(browser, o) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const log = { status: [], saves: [], other: [], statusT: [] };
  const base = o.base || 'https://violamaro.ru';
  await ctx.route(base + '/**', r => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: fs.readFileSync(PAGE, 'utf8') }));
  await ctx.route('https://telegram.org/**', r => o.noSdk ? r.abort() : r.fulfill({ status: 200, contentType: 'application/javascript', body: tgStub(o) }));
  await ctx.route(GAS + '**', async r => {
    const u = new URL(r.request().url());
    if (u.searchParams.get('action') === 'status') {
      log.status.push(Object.fromEntries(u.searchParams));
      log.statusT.push(Date.now());
      if (o.statusDelay) await new Promise(res => setTimeout(res, o.statusDelay));
      if (o.statusFail) return r.abort().catch(() => {});
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, passed: o.passed ? '1' : '0' }) }).catch(() => {});
    }
    const p = u.searchParams.get('payload');
    if (p) { const d = JSON.parse(p); (d.type === 't2_result' ? log.saves : log.other).push(d); }
    if (o.saveFail) return r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":false,"error":"x"}' });
    return r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' });
  });
  if (o.state || o.pending) {
    await ctx.addInitScript(([s, b]) => {
      try {
        if (sessionStorage.getItem('__seeded')) return;
        if (s) localStorage.setItem('viola2-state', s);
        if (b) localStorage.setItem('viola2-pending', b);
        sessionStorage.setItem('__seeded', '1');
      } catch (e) {}
    }, [o.state || '', o.pending || '']);
  }
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(base + '/test2/' + (o.query || '') + (o.hash || ''));
  return { ctx, page, log, errors };
}

// Типограф ставит неразрывные пробелы после коротких слов: сравниваем с обычными.
const text = page => page.evaluate(() => (document.getElementById('screen') || document.body).innerText.replace(/ /g, ' '));
async function waitText(page, re, ms) {
  const t0 = Date.now();
  while (Date.now() - t0 < (ms || 15000)) {
    const t = await text(page).catch(() => '');
    if (re.test(t)) return t;
    await page.waitForTimeout(100);
  }
  return await text(page).catch(() => '');
}

(async () => {
  const browser = await chromium.launch();

  // 1. Новый человек в Телеграме проходит тест целиком
  let st = null;
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_reels' });
    await page.locator('#start').click();
    for (let i = 0; i < 36; i++) await page.locator('.ans').nth(i % 4).click();
    await page.locator('.ans').first().click();          // вилка
    await page.locator('#skip').click();                 // свои слова
    await page.locator('.ans').nth(2).click();           // возраст
    const t = await waitText(page, /результат готов/i);
    check('1 новый: экран «Ваш результат готов»', /Ваш результат готов/.test(t));
    check('1 новый: одна запись прохождения с ID 111', log.saves.length === 1 && String(log.saves[0].userId) === '111', log.saves.map(s => s.userId));
    check('1 новый: источник reels, секунды > 0', log.saves[0] && log.saves[0].istochnik === 'reels' && log.saves[0].seconds > 0, log.saves[0] && [log.saves[0].istochnik, log.saves[0].seconds]);
    check('1 новый: статус не спрашивали', log.status.length === 0, log.status.length);
    await page.locator('#to-bot').click();
    const opened = await page.evaluate(() => [window.__opened, window.__closed]);
    await page.waitForTimeout(400);
    const closed = await page.evaluate(() => window.__closed);
    check('1 новый: кнопка ведёт в бот t2_done и закрывает приложение', opened[0] === 'https://t.me/viola_maro_bot?start=t2_done' && closed === true, opened);
    st = await page.evaluate(() => localStorage.getItem('viola2-state'));
    const s = JSON.parse(st);
    check('1 новый: в сохранённом состоянии есть метка src=reels', s.src === 'reels' && !!s.res, { src: s.src, res: s.res && s.res.key });
    check('1 новый: ошибок на странице нет', errors.length === 0, errors);
    await ctx.close();
  }
  const saved = JSON.parse(st);

  // 2. Вернулся, в таблице результат есть
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, passed: true });
    const t = await waitText(page, /результат готов/i);
    check('2 есть в таблице: «готов» без повторной записи', /Ваш результат готов/.test(t) && log.saves.length === 0, { saves: log.saves.length });
    check('2 есть в таблице: один запрос статуса с tg=111', log.status.length === 1 && log.status[0].tg === '111' && log.status[0].test === 'empat2', log.status);
    check('2 ошибок нет', errors.length === 0, errors);
    if (OUT) { await page.waitForTimeout(900); await page.screenshot({ path: path.join(OUT, '2-gotov.png') }); }
    await ctx.close();
  }

  // 3. Вернулся, строки в таблице нет (случай Даши)
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, passed: false });
    const t = await waitText(page, /результат готов/i);
    const p = log.saves[0] || {};
    check('3 нет в таблице: прохождение дослано и потом «готов»', /Ваш результат готов/.test(t) && log.saves.length === 1, { saves: log.saves.length });
    check('3 нет в таблице: дослано с ID 111 и тем же pid', String(p.userId) === '111' && p.pid === saved.pid, [p.userId, p.pid, saved.pid]);
    check('3 нет в таблице: те же ответы и тот же тип', JSON.stringify(p.answers) === JSON.stringify(saved.answers) && p.rank === saved.res.key, [p.rank, saved.res.key]);
    check('3 нет в таблице: источник исходный (reels), не src_bot', p.istochnik === 'reels', p.istochnik);
    check('3 нет в таблице: секунды 0, «быстро» нет', p.seconds === 0 && p.fast === false, [p.seconds, p.fast]);
    check('3 нет в таблице: возраст и вилка на месте', p.age === saved.age && p.forks && p.forks.bol === saved.forks.bol, [p.age, p.forks && p.forks.bol]);
    check('3 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 4. Вход кнопкой бота startapp=rezultat, строки нет
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'rezultat', state: st, passed: false });
    const t = await waitText(page, /результат готов/i);
    check('4 rezultat без строки: дослано и «готов»', /Ваш результат готов/.test(t) && log.saves.length === 1 && log.status.length === 1, { saves: log.saves.length, status: log.status.length });
    check('4 источник исходный', (log.saves[0] || {}).istochnik === 'reels', (log.saves[0] || {}).istochnik);
    check('4 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 5. Таблица не ответила за 6 секунд — досылаем
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, passed: true, statusDelay: 8000 });
    const mid = await waitText(page, /Открываю/, 4000);
    check('5 медленная таблица: пока ждём, «Открываю…»', /Открываю/.test(mid), mid.slice(0, 60));
    const t = await waitText(page, /результат готов/i, 20000);
    check('5 медленная таблица: дослано и «готов»', /Ваш результат готов/.test(t) && log.saves.length === 1, { saves: log.saves.length });
    check('5 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 6. Запрос статуса упал — досылаем
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, statusFail: true });
    const t = await waitText(page, /результат готов/i);
    check('6 статус упал: дослано и «готов»', /Ваш результат готов/.test(t) && log.saves.length === 1, { saves: log.saves.length });
    check('6 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 7. Строки нет и приёмник не сохраняет — экран повтора, а не «готов»
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, passed: false, saveFail: true });
    const t = await waitText(page, /Не получилось сохранить/, 30000);
    check('7 не сохранилось: экран «Не получилось сохранить» с повтором', /Не получилось сохранить/.test(t) && await page.locator('#retry').count() === 1, t.slice(0, 80));
    check('7 три попытки', log.saves.length === 3, log.saves.length);
    check('7 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 8. В очереди лежит неотправленное прохождение — как раньше, без запроса статуса
  {
    const pend = Object.assign({}, { type: 't2_result', form: 'test2', test: 'empat2', pid: saved.pid, userId: 111, istochnik: 'reels', answers: saved.answers, rank: saved.res.key });
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'src_bot', state: st, pending: JSON.stringify([pend]), passed: false });
    const t = await waitText(page, /результат готов/i);
    check('8 очередь: «готов», статус не спрашивали', /Ваш результат готов/.test(t) && log.status.length === 0, { status: log.status.length, saves: log.saves.length });
    check('8 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 9. Телеграм без пользователя в initData — как раньше, сразу «готов»
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, noUser: true, sp: 'src_bot', state: st, passed: false });
    const t = await waitText(page, /результат готов/i);
    check('9 без ID: «готов» без статуса и записи', /Ваш результат готов/.test(t) && log.status.length === 0 && log.saves.length === 0, { status: log.status.length, saves: log.saves.length });
    check('9 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 10. Сброс для команды в Телеграме
  {
    const { ctx, page, log, errors } = await open(browser, { inTg: true, sp: 'reset', state: st });
    const t = await waitText(page, /Какой вы эмпат/);
    const left = await page.evaluate(() => localStorage.getItem('viola2-state'));
    check('10 сброс: первый экран теста, прохождение стёрто', /Начать/.test(t) && !left, { left: !!left });
    check('10 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 11–14. Обычный браузер
  const browserCases = [
    { n: '11 браузер ?src=insta', o: { query: '?src=insta' }, link: 'https://t.me/viola_maro_bot/test2?startapp=src_insta' },
    { n: '12 браузер ?startapp=rezultat', o: { query: '?startapp=rezultat' }, link: 'https://t.me/viola_maro_bot/test2?startapp=rezultat' },
    { n: '13 браузер без метки', o: {}, link: 'https://t.me/viola_maro_bot/test2' },
    { n: '14 браузер, скрипт Телеграма не загрузился', o: { noSdk: true, query: '?src=web' }, link: 'https://t.me/viola_maro_bot/test2?startapp=src_web' },
    { n: '15 браузер с пройденным тестом', o: { state: st, query: '?src=insta' }, link: 'https://t.me/viola_maro_bot/test2?startapp=src_insta' },
    { n: '16 браузер, метка с мусором', o: { query: '?src=' + encodeURIComponent('ig"><b>x') }, link: 'https://t.me/viola_maro_bot/test2?startapp=src_igbx' }
  ];
  for (const c of browserCases) {
    const { ctx, page, log, errors } = await open(browser, Object.assign({ inTg: false }, c.o));
    const t = await waitText(page, /открывается в Telegram/, 8000);
    const href = await page.locator('#to-app').getAttribute('href').catch(() => null);
    const qs = await page.locator('.ans, #start').count();
    check(c.n + ': экран «Открыть в Telegram», ссылка с меткой', /Тест открывается в Telegram/.test(t) && href === c.link && qs === 0, { href, qs });
    check(c.n + ': ни статуса, ни записей', log.status.length === 0 && log.saves.length === 0, { status: log.status.length, saves: log.saves.length });
    check(c.n + ': ошибок нет', errors.length === 0, errors);
    if (OUT && c.n.startsWith('11')) { await page.waitForTimeout(900); await page.screenshot({ path: path.join(OUT, '11-brauzer.png') }); }
    await ctx.close();
  }

  // 17. Телеграм, но его скрипт опоздал: в адресе tgWebAppData — экран браузера НЕ показываем
  {
    const { ctx, page, errors } = await open(browser, { noSdk: true, hash: '#tgWebAppData=user%3D%257B%257D&tgWebAppVersion=7.10&tgWebAppPlatform=ios' });
    const t = await waitText(page, /Какой вы эмпат|открывается в Telegram/, 8000);
    check('17 Телеграм без скрипта: обычный старт теста, не экран браузера', /Начать/.test(t) && !/открывается в Telegram/.test(t), t.slice(0, 60));
    check('17 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  // 18. Локальный просмотр на 127.0.0.1 — тест как раньше
  {
    const { ctx, page, errors } = await open(browser, { inTg: false, base: 'http://127.0.0.1:8791' });
    const t = await waitText(page, /Какой вы эмпат|открывается в Telegram/, 8000);
    check('18 локально: обычный старт теста', /Начать/.test(t) && !/открывается в Telegram/.test(t), t.slice(0, 60));
    check('18 ошибок нет', errors.length === 0, errors);
    await ctx.close();
  }

  await browser.close();
  const bad = results.filter(r => !r.ok);
  console.log('\nИтого: ' + (results.length - bad.length) + ' из ' + results.length + ' прошли');
  process.exit(bad.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
