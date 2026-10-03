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
const N = 20000, types = {}, spheres = {}, heads = { low: 0, high: 0, plain: 0 }, ry = {};
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
  const A = b.scales.A, F = 9 - b.scales.P;
  heads[A >= 6 && F <= 3 ? 'low' : A >= 6 && F >= 6 ? 'high' : 'plain']++;
  if (['donor', 'filter', 'sleeping', 'awake'].includes(b.key)) {
    const k = vm.runInContext(`ryadomKey(${JSON.stringify(b)})`, newT);
    ry[k] = (ry[k] || 0) + 1;
  }
}
console.log('прохождений:', N, '· расхождений с первым тестом:', mismatch);
console.log('типы:', types);
console.log('сферы:', spheres);
console.log('главная строка портрета:', heads);
console.log('абзац «Кто рядом»:', ry);

// точечные случаи сферы
const flat = Array(24).fill(1);
const sp = (v12, bol) => JSON.parse(run(newT, flat.concat(v12), `Object.keys(forks).forEach(k => delete forks[k]); ${bol ? `forks.bol = "${bol}";` : ''}`)).sphere;
console.log('ничего не проседает →', JSON.stringify(sp([1,1,1,1,1,1, 1,1,1,1,1,1])), '(ожидаем пусто)');
console.log('равенство otn и delo, назвал «работа» →', sp([0,3,0,0,3,0, 0,3,0,0,3,0], 'rabota'), '(ожидаем delo)');
console.log('равенство otn и delo, назвал «партнёр» →', sp([0,3,0,0,3,0, 0,3,0,0,3,0], 'partner'), '(ожидаем otn)');
console.log('равенство ya(3+1) и telo(2+2), без вилки →', sp([3,0,0,2,0,0, 1,0,0,2,0,0]), '(ожидаем ya: больше твёрдых «да»)');
process.exit(mismatch ? 1 : 0);
