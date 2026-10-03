// Сверка: тип в тесте 2.0 обязан совпадать с типом первого теста на тех же 24 ответах.
const fs = require('fs'), vm = require('vm');
function load(file) {
  const html = fs.readFileSync(file, 'utf8');
  const code = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
  const any = new Proxy(function () {}, {
    get(t, k) {
      // nextNode: обход текста в типографе должен кончаться, иначе скрипт зависнет
      if (k === 'firstChild' || k === 'createTreeWalker') return null;
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === 'length') return 0;
      return any;
    },
    apply() { return any; }, set() { return true; }, construct() { return any; }
  });
  const store = {};
  const ctx = { window: {}, document: any, navigator: {}, location: { search: '' },
    localStorage: { getItem: k => store[k] || null, setItem(k, v) { store[k] = v; }, removeItem(k) { delete store[k]; } },
    setTimeout: () => 0, clearTimeout() {}, fetch: () => ({ then: () => ({ then: () => ({ catch: () => ({ then() {} }) }) }), catch() {} }),
    URLSearchParams, URL, Date, Math, JSON, console, Set };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  return ctx;
}
const oldT = load(process.argv[2]), newT = load(process.argv[3]);
const run = (ctx, v, extra) => vm.runInContext(`answers.length = 0; ${JSON.stringify(v)}.forEach(x => answers.push(x)); ${extra || ''} JSON.stringify(score())`, ctx);

let seed = 20261003;
const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const N = 20000, types = {}, spheres = {}, heads = {}, ry = {};
let mismatch = 0;
for (let n = 0; n < N; n++) {
  // половина выборки — «похожая на эмпата»: ответы смещены к «да»
  const bias = n % 2 ? 0.62 : 0.5;
  const v24 = Array.from({ length: 24 }, () => { const r = rnd(); return r < bias * .5 ? 3 : r < bias ? 2 : r < (1 + bias) / 2 ? 1 : 0; });
  const v12 = Array.from({ length: 12 }, () => Math.floor(rnd() * 4));
  const a = JSON.parse(run(oldT, v24));
  const b = JSON.parse(run(newT, v24.concat(v12), "Object.keys(forks).forEach(k => delete forks[k]);"));
  if (a.key !== b.key || a.pct !== b.pct || JSON.stringify(a.scales) !== JSON.stringify(b.scales) || a.fon !== b.fon) mismatch++;
  types[b.key] = (types[b.key] || 0) + 1;
  spheres[b.sphere || '—'] = (spheres[b.sphere || '—'] || 0) + 1;
  if (['donor', 'filter', 'sleeping', 'awake'].includes(b.key)) {
    // главная фраза блока «Что видно по вашим ответам» — только у типов эмпата
    const h = vm.runInContext(`seenHead(${JSON.stringify(b.scales)})`, newT);
    const name = !h ? 'фразы нет' : /внутрь/.test(h) ? 'чужое заходит внутрь' : 'оставляет снаружи';
    heads[name] = (heads[name] || 0) + 1;
    // сколько своих утверждений человек увидит в блоке «Почему пользуются именно вами?»
    const k = vm.runInContext(`ryadomList().length`, newT);
    ry[k] = (ry[k] || 0) + 1;
  }
}
console.log('прохождений:', N, '· расхождений с первым тестом:', mismatch);
console.log('типы:', types);
console.log('сферы:', spheres);
console.log('главная фраза у типов эмпата:', heads);
console.log('утверждений в блоке «Почему пользуются» у типов эмпата (0 — блока нет):', ry);

// уровни шкал: границы из ТЗ
const lv = (v, max) => vm.runInContext(`level_(${v}, ${max})`, newT);
const got9 = [0,1,2,3,4,5,6,7,8,9].map(v => lv(v, 9)).join('');
const got12 = [0,1,2,3,4,5,6,7,8,9,10,11,12].map(v => lv(v, 12)).join('');
console.log('уровни шкалы 0–9: ', got9, got9 === '1122334455' ? '✔' : '✘ ожидали 1122334455');
console.log('уровни шкалы 0–12:', got12, got12 === '1112233344555' ? '✔' : '✘ ожидали 1112233344555');
if (got9 !== '1122334455' || got12 !== '1112233344555') mismatch++;

// блок «Почему пользуются именно вами?»: порядок и порог
const pick = set => {
  const v = Array(36).fill(0);
  Object.keys(set).forEach(i => { v[i] = set[i]; });
  run(newT, v, "Object.keys(forks).forEach(k => delete forks[k]);");
  return vm.runInContext(`JSON.stringify(ryadomList().map(x => x.i))`, newT);
};
const cases = [
  [{ 15: 2, 8: 3, 16: 3 },               '[8,16,15]', 'сначала ответы с 3 баллами, потом с 2'],
  [{ 15: 3, 8: 3, 16: 3, 13: 3, 14: 3 }, '[15,8,16]', 'не больше трёх, в порядке списка'],
  [{ 7: 3, 13: 2 },                      '[7,13]',    'два ответа — блок есть, в нём два утверждения'],
  [{ 15: 3 },                            '[]',        'один ответ — блока нет'],
  [{ 15: 1, 8: 1, 16: 1, 13: 0 },        '[]',        '«редко» и «нет» не считаются']
];
cases.forEach(c => {
  const got = pick(c[0]);
  console.log('утверждения', got, got === c[1] ? '✔' : '✘ ожидали ' + c[1], '·', c[2]);
  if (got !== c[1]) mismatch++;
});
const st = vm.runInContext(`stmt_(15)`, newT);
console.log('текст утверждения:', st, /^вам трудно отказать.*[^.]$/.test(st) ? '✔' : '✘ ожидали с маленькой буквы и без точки');
if (!/^вам трудно отказать.*[^.]$/.test(st)) mismatch++;

// точечные случаи сферы
const flat = Array(24).fill(1);
const sp = (v12, bol) => JSON.parse(run(newT, flat.concat(v12), `Object.keys(forks).forEach(k => delete forks[k]); ${bol ? `forks.bol = "${bol}";` : ''}`)).sphere;
console.log('ничего не проседает →', JSON.stringify(sp([1,1,1,1,1,1, 1,1,1,1,1,1])), '(ожидаем пусто)');
console.log('равенство otn и delo, назвал «работа» →', sp([0,3,0,0,3,0, 0,3,0,0,3,0], 'rabota'), '(ожидаем delo)');
console.log('равенство otn и delo, назвал «партнёр» →', sp([0,3,0,0,3,0, 0,3,0,0,3,0], 'partner'), '(ожидаем otn)');
console.log('равенство ya(3+1) и telo(2+2), без вилки →', sp([3,0,0,2,0,0, 1,0,0,2,0,0]), '(ожидаем ya: больше твёрдых «да»)');
process.exit(mismatch ? 1 : 0);
