// Render each chart of results.html to PNG (light + dark) for the README.
// usage: node render_figures.js   (needs puppeteer-core and Google Chrome; set CHROME to override the path)
const path = require('path'), fs = require('fs');
const R = path.join(__dirname, '..');
let puppeteer;
try { puppeteer = require('puppeteer-core'); } catch { puppeteer = require(path.join(R, '..', 'build', 'node_modules', 'puppeteer-core')); }
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FIGS = [
  ['summary', '#findings'], ['scores', '#dots'], ['effort', '#cost'],
  ['on-screen', '#look'], ['motion', '#motion'], ['timeline', '#timeline'],
];
(async () => {
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">'
    + fs.readFileSync(path.join(R, 'results.html'), 'utf8') + '</body></html>';
  const tmp = path.join(R, '.render.html'); fs.writeFileSync(tmp, html);
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new' });
  const pg = await b.newPage();
  fs.mkdirSync(path.join(R, 'figures'), { recursive: true });
  for (const scheme of ['light', 'dark']) {
    await pg.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: scheme }, { name: 'prefers-reduced-motion', value: 'reduce' }]);
    await pg.setViewport({ width: 1120, height: 1000, deviceScaleFactor: 2 });
    await pg.goto('file://' + tmp, { waitUntil: 'networkidle0' });
    await pg.evaluate(() => document.fonts.ready);
    for (const [name, sel] of FIGS) {
      const box = await pg.evaluate((sel) => {
        let el = document.querySelector(sel); el = el.closest('.panel') || el;
        const r = el.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height };
      }, sel);
      const pad = 16;
      await pg.screenshot({ path: path.join(R, 'figures', `${name}-${scheme}.png`), captureBeyondViewport: true,
        clip: { x: box.x - pad, y: box.y - pad, width: box.w + pad * 2, height: box.h + pad * 2 } });
    }
  }
  await b.close(); fs.unlinkSync(tmp);
  console.log('figures written');
})();
