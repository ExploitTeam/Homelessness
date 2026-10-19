/* Резервная сборка для сред без нативного модуля rolldown.
 * Требует только Node.js и пакеты node_modules, присутствующие после npm ci.
 * Использует самостоятельные ESM-модули без внешних CDN.
 */
const fs = require('fs');
const path = require('path');
const ts = require('typescript');
const root = __dirname;
const src = path.join(root, 'src');
const dist = path.join(root, 'dist');
const RELEASE = 'v5-20261019';
const BASE = `/releases/${RELEASE}`;
const vendor = path.join(dist, 'releases', RELEASE, 'vendor');

function read(name) { return fs.readFileSync(path.join(root, 'node_modules', name), 'utf8'); }
function write(relative, content) {
  const filename = path.join(dist, relative === 'index.html' ? relative : path.join('releases', RELEASE, relative));
  fs.mkdirSync(path.dirname(filename), { recursive: true });
  fs.writeFileSync(filename, content);
}

// JS версия интерфейса react + react-dom и JSX runtime;
// все зависимости локальные и входят в distribution.
const modules = [
  ['react', 'react/cjs/react.production.js'],
  ['scheduler', 'scheduler/cjs/scheduler.production.js'],
  ['react-dom', 'react-dom/cjs/react-dom.production.js'],
  ['react-dom/client', 'react-dom/cjs/react-dom-client.production.js'],
  ['react/jsx-runtime', 'react/cjs/react-jsx-runtime.production.js'],
];
let browserVendor = `/* React runtime (MIT). Self-contained ESM wrapper. */\nconst registry = Object.create(null);\n`;
for (const [name, filename] of modules) {
  browserVendor += `// ${filename}\nregistry[${JSON.stringify(name)}] = (() => {\n`;
  browserVendor += `const module = { exports: {} }; const exports = module.exports;\n`;
  browserVendor += `const require = (name) => { if (!registry[name]) throw new Error('Missing dependency: '+name); return registry[name]; };\n`;
  browserVendor += `(function(require, module, exports) {\n${read(filename)}\n})(require, module, exports);\nreturn module.exports; })();\n`;
}
browserVendor += `const React = registry['react']; const JSX = registry['react/jsx-runtime']; const DOM = registry['react-dom']; const Client = registry['react-dom/client'];\n`;
for (const key of ['StrictMode','useEffect','useMemo','useCallback','useRef','useState','useId','Fragment']) {
  browserVendor += `export const ${key} = React.${key};\n`;
}
browserVendor += `export const createRoot = Client.createRoot;\nexport const createPortal = DOM.createPortal;\nexport const jsx = JSX.jsx;\nexport const jsxs = JSX.jsxs;\nexport default React;\n`;

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(vendor, { recursive: true });
write('vendor/react-vendor.mjs', browserVendor);
for (const f of ['maplibre-gl.mjs', 'maplibre-gl-shared.mjs', 'maplibre-gl.css']) {
  fs.copyFileSync(path.join(root, 'node_modules/maplibre-gl/dist', f), path.join(vendor, f));
}
for (const f of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  const dest = path.join(dist, 'maplibre', f);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(path.join(root, 'node_modules/maplibre-gl/dist', f), dest);
}
for (const f of ['favicon.svg','icons.svg']) {
  const source = path.join(root, 'public', f);
  if (fs.existsSync(source)) fs.copyFileSync(source, path.join(dist, f));
}
for (const f of ['App.css', 'index.css']) fs.copyFileSync(path.join(src, f), path.join(dist, 'releases', RELEASE, f));

function adjustImports(js) {
  // Удаление CSS imports (стили подключены в index.html).
  js = js.replace(/^[ \t]*import\s+["'][^"']+\.css["'];?\s*$/gm, '');
  // Bare packages resolved to bundled ESM vendor.
  js = js.replace(/((?:\bfrom\s*|\bimport\s*)["'])(react|react-dom|react-dom\/client|react\/jsx-runtime|maplibre-gl)(["'])/g,
    (_, begin, name, end) => `${begin}${BASE}${name === 'maplibre-gl' ? '/vendor/maplibre-gl.mjs' : '/vendor/react-vendor.mjs'}${end}`);
  // Native browser imports always need explicit file extensions.
  js = js.replace(/((?:\bfrom\s*|\bimport\s*)["'])(\.{1,2}\/[^"']+)(["'])/g,
    (_, begin, name, end) => `${begin}${name.replace(/\.(tsx?|jsx?)$/, '')}.js${end}`);
  return js;
}
function processDir(source) {
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const filename = path.join(source, entry.name);
    if (entry.isDirectory()) { processDir(filename); continue; }
    if (!/\.(tsx?|jsx?)$/.test(filename) || filename.endsWith('.d.ts')) continue;
    const content = fs.readFileSync(filename, 'utf8');
    const compiled = ts.transpileModule(content, {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, isolatedModules: true },
      fileName: filename,
    }).outputText;
    const relative = path.relative(src, filename).replace(/\.(tsx?|jsx?)$/, '.js');
    write(path.join('src', relative), adjustImports(compiled));
  }
}
processDir(src);
write('index.html', `<!doctype html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Пункты помощи на карте</title><meta name="max-miniapp-version" content="${RELEASE}">
<meta name="max-api-base-url" content=""><link rel="icon" href="/favicon.svg">
<link rel="stylesheet" href="${BASE}/vendor/maplibre-gl.css"><link rel="stylesheet" href="${BASE}/index.css"><link rel="stylesheet" href="${BASE}/App.css">
<script src="https://st.max.ru/js/max-web-app.js"></script></head>
<body><div id="root"></div><script type="module" src="${BASE}/src/main.js"></script></body></html>`);
console.log('Self-contained dist generated:', dist);
