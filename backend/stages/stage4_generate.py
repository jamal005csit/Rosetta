"""Stage 4 generate: AppSpec -> runnable generated_app. P1, P2, P4, P5."""
import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

def _appspec(job_dir: Path) -> dict:
    p = Path(job_dir) / "appspec.json"
    return json.loads(p.read_text(encoding="utf-8"))

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    log.info("wrote %s (%d chars)", path, len(text))

def _comp_name(screen_id: str) -> str:
    m = {"scr_login": "Login", "scr_menu": "Menu", "scr_customers": "Customers",
         "scr_order": "Order", "scr_report": "Report"}
    if screen_id in m:
        return m[screen_id]
    return "".join(w.capitalize() for w in screen_id.replace("scr_", "").split("_")) or "Screen"

def rules_ts() -> str:
    return """export function lineDiscountRate(qty: number): number {
  if (qty >= 50) return 0.12;
  if (qty >= 10) return 0.05;
  return 0;
}
export function lineTotal(qty: number, price: number): number {
  const gross = qty * price;
  const net = gross * (1 - lineDiscountRate(qty));
  return Math.round(net * 100) / 100;
}
export function discountedSubtotal(lines: {qty:number;price:number}[]): number {
  return Math.round(lines.reduce((a,l)=>a+lineTotal(l.qty,l.price),0)*100)/100;
}
export function vatAmount(sub: number): number {
  return Math.round(sub * 0.14 * 100) / 100;
}
export function round05(v: number): number {
  return Math.round(v / 0.05) * 0.05;
}
export function orderTotal(lines: {qty:number;price:number}[]): number {
  const sub = discountedSubtotal(lines);
  const vat = vatAmount(sub);
  return Math.round(round05(sub + vat) * 100) / 100;
}
export function exceedsLimit(total: number, limit: number): boolean {
  return total > limit;
}
"""

def _login_tsx() -> str:
    return """import React, { useState } from 'react';
export default function Login(props: { go: (s: string) => void }) {
  const [user, setUser] = useState('admin');
  const [pass, setPass] = useState('admin');
  const [err, setErr] = useState('');
  function doLogin() {
    if (user === 'admin' && pass === 'admin') props.go('scr_menu');
    else setErr('Invalid credentials');
  }
  return (
    <div style={{maxWidth:480,margin:'40px auto',fontFamily:'system-ui'}}>
      <h2>CairoTrade Login</h2>
      <div><label>Username<input data-testid="fld_user" value={user} onChange={e=>setUser(e.target.value)} /></label></div>
      <div><label>Password<input data-testid="fld_pass" type="password" value={pass} onChange={e=>setPass(e.target.value)} /></label></div>
      <button data-testid="btn_login" onClick={doLogin}>Login</button>
      {err && <div role="alert">{err}</div>}
    </div>
  );
}
"""

def _field_testid(screen: dict, keywords: tuple[str, ...], fallback: str) -> str:
    for field in screen.get("fields", []):
        identity = f"{field.get('id', '')} {field.get('label', '')}".lower()
        if any(keyword in identity for keyword in keywords):
            return str(field.get("id") or fallback)
    return fallback


def _menu_tsx(screen: dict) -> str:
    customer_id = _field_testid(screen, ("customer", "client"), "fld_menu_customers")
    order_id = _field_testid(screen, ("order", "sale"), "fld_menu_order")
    report_id = _field_testid(screen, ("report", "summary"), "fld_menu_report")
    return f"""import React from 'react';
export default function Menu(props: {{ go: (s: string) => void }}) {{
  return (
    <div style={{{{maxWidth:480,margin:'40px auto',fontFamily:'system-ui'}}}}>
      <h2>Main menu</h2>
      <div><button data-testid="{customer_id}" onClick={{()=>props.go('scr_customers')}}>Customer lookup</button></div>
      <div><button data-testid="{order_id}" onClick={{()=>props.go('scr_order')}}>Order entry</button></div>
      <div><button data-testid="{report_id}" onClick={{()=>props.go('scr_report')}}>Daily report</button></div>
    </div>
  );
}}
"""

def _customers_tsx() -> str:
    return """import React, { useEffect, useState } from 'react';
export default function Customers(props: { go: (s: string) => void }) {
  const [q, setQ] = useState('');
  const [list, setList] = useState<any[]>([]);
  async function load() {
    try {
      const r = await fetch('/api/customers?q=' + encodeURIComponent(q));
      const d = await r.json();
      setList(d);
    } catch { setList([{id:'C001',name:'Ahmed Hassan',limit:5000}]); }
  }
  useEffect(()=>{ load(); },[]);
  useEffect(()=>{
    function h(e: KeyboardEvent){ if(e.key==='Escape') props.go('scr_menu'); if(e.key==='F5'){e.preventDefault();load();} }
    window.addEventListener('keydown',h);
    return ()=>window.removeEventListener('keydown',h);
  });
  const shown = list.filter(c=>!q || (c.id+c.name).toLowerCase().includes(q.toLowerCase()));
  return (
    <div style={{maxWidth:640,margin:'20px auto',fontFamily:'system-ui'}}>
      <h2>Customer lookup</h2>
      <label>Search<input data-testid="fld_search" value={q} onChange={e=>setQ(e.target.value)} /></label>
      <button onClick={load}>Search</button>
      <ul data-testid="fld_customer_list">{shown.map(c=><li key={c.id}>{c.id} {c.name} lim={c.limit}</li>)}</ul>
      <button onClick={()=>props.go('scr_menu')}>Back</button>
    </div>
  );
}
"""

def _order_tsx() -> str:
    return """import React, { useEffect, useState } from 'react';
import { orderTotal, discountedSubtotal, vatAmount } from '../lib/rules';
type Line = { sku: string; qty: number; price: number };
export default function Order(props: { go: (s: string) => void }) {
  const [customer, setCustomer] = useState('C001');
  const [customers, setCustomers] = useState<any[]>([{id:'C001',name:'Ahmed Hassan',limit:5000},{id:'C002',name:'Mona El-Sayed',limit:2000}]);
  const [items, setItems] = useState<any[]>([{sku:'ITM-01',name:'Valve A',price:100},{sku:'ITM-02',name:'Gasket B',price:10}]);
  const [sku, setSku] = useState('ITM-01');
  const [qty, setQty] = useState('1');
  const [lines, setLines] = useState<Line[]>([]);
  const [msg, setMsg] = useState('');
  useEffect(()=>{
    fetch('/api/customers').then(r=>r.json()).then(d=>{ if(d.length) setCustomers(d); }).catch(()=>{});
    fetch('/api/items').then(r=>r.json()).then(d=>{ if(d.length) setItems(d); }).catch(()=>{});
  },[]);
  function totals() {
    const ls = lines.map(l=>({qty:l.qty,price:l.price}));
    return { sub: discountedSubtotal(ls), vat: vatAmount(discountedSubtotal(ls)), tot: orderTotal(ls) };
  }
  function addLine() {
    const q = parseInt(qty, 10);
    if (isNaN(q)) { setMsg('Qty must be integer'); return; }
    const it = items.find(i=>i.sku===sku);
    const price = it ? Number(it.price) : 0;
    setLines([...lines, {sku, qty:q, price}]);
    setMsg('');
  }
  async function saveOrder() {
    if (lines.length===0) { setMsg('No lines'); return; }
    const t = totals();
    const cust = customers.find(c=>c.id===customer);
    const limit = cust ? Number(cust.limit) : Infinity;
    if (t.tot > limit) {
      const ok = window.confirm('Total ' + t.tot + ' exceeds limit ' + limit + '. Continue?');
      if (!ok) return;
    }
    try {
      const r = await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cust:customer,lines,total:t.tot})});
      const j = await r.json();
      setMsg('Saved total ' + (j.total ?? t.tot) + ' EGP');
      setLines([]);
    } catch (error) { const detail = error instanceof Error ? error.message : 'unknown error'; setMsg('Save failed: ' + detail); }
  }
  function refresh(){ setMsg(''); }
  function cancel(){ setLines([]); setMsg(''); props.go('scr_menu'); }
  useEffect(()=>{
    function h(e: KeyboardEvent){
      if(e.key==='F2'){ e.preventDefault(); saveOrder(); }
      if(e.key==='F5'){ e.preventDefault(); refresh(); }
      if(e.key==='Escape'){ cancel(); }
    }
    window.addEventListener('keydown',h);
    return ()=>window.removeEventListener('keydown',h);
  });
  const t = totals();
  return (
    <div style={{maxWidth:640,margin:'20px auto',fontFamily:'system-ui'}}>
      <h2>Order entry (F2 save, F5 refresh, Esc cancel)</h2>
      <div><label>Customer<select data-testid="fld_customer" value={customer} onChange={e=>setCustomer(e.target.value)}>{customers.map(c=><option key={c.id} value={c.id}>{c.id} {c.name}</option>)}</select></label></div>
      <div><label>Item<select data-testid="fld_item" value={sku} onChange={e=>setSku(e.target.value)}>{items.map(i=><option key={i.sku} value={i.sku}>{i.sku} {i.name}</option>)}</select></label></div>
      <div><label>Qty<input data-testid="fld_qty" value={qty} onChange={e=>setQty(e.target.value)} /></label></div>
      <button data-testid="btn_add" onClick={addLine}>Add line</button>
      <ul data-testid="fld_lines">{lines.map((l,i)=><li key={i}>{l.sku} x{l.qty} @ {l.price}</li>)}</ul>
      <div data-testid="fld_total">Sub={t.sub} VAT={t.vat} Total={t.tot} EGP</div>
      {msg && <div role="status">{msg}</div>}
      <button onClick={()=>props.go('scr_menu')}>Back</button>
    </div>
  );
}
"""

def _report_tsx(screen: dict) -> str:
    orders_id = _field_testid(screen, ("orders", "transactions", "records"), "fld_report_list")
    return f"""import React, {{ useEffect, useState }} from 'react';
export default function Report(props: {{ go: (s: string) => void }}) {{
  const [orders, setOrders] = useState<any[]>([]);
  async function load() {{
    try {{ const r = await fetch('/api/orders'); setOrders(await r.json()); }}
    catch {{ setOrders([]); }}
  }}
  useEffect(()=>{{ load(); }},[]);
  useEffect(() => {{
    function h(e: KeyboardEvent){{ if(e.key==='F5'){{e.preventDefault();load();}} if(e.key==='Escape') props.go('scr_menu'); }}
    window.addEventListener('keydown',h);
    return ()=>window.removeEventListener('keydown',h);
  }});
  return (
    <div style={{{{maxWidth:640,margin:'20px auto',fontFamily:'system-ui'}}}}>
      <h2>Daily report</h2>
      <button onClick={{load}}>Refresh</button>
      <ul data-testid="{orders_id}">{{orders.length===0 ? <li>(no orders today)</li> : orders.map((o,i)=><li key={{i}}>{{o.cust}} total={{o.total}}</li>)}}</ul>
      <button onClick={{()=>props.go('scr_menu')}}>Back</button>
    </div>
  );
}}
"""

def _generic_tsx(screen: dict) -> str:
    name = _comp_name(screen.get("id", "scr_x"))
    title = screen.get("title", "Screen").replace("'", "")
    parts: list[str] = []
    for f in screen.get("fields", []):
        fid = f.get("id", "fld_x")
        label = f.get("label", fid).replace("'", "")
        ftype = f.get("type", "text")
        if ftype in ("button",):
            parts.append(f'<button data-testid="{fid}">{label}</button>')
        elif ftype == "select":
            parts.append(f'<label>{label}<select data-testid="{fid}"><option value="">{label}</option></select></label>')
        elif ftype == "list":
            parts.append(f'<ul data-testid="{fid}"><li>{label}</li></ul>')
        elif ftype == "password":
            parts.append(f'<label>{label}<input data-testid="{fid}" type="password" /></label>')
        elif ftype == "number":
            parts.append(f'<label>{label}<input data-testid="{fid}" inputMode="numeric" /></label>')
        else:
            parts.append(f'<label>{label}<input data-testid="{fid}" /></label>')
    inner = "\n      ".join(parts) if parts else "<div>empty</div>"
    return f"""import React from 'react';
export default function {name}(props: {{ go: (s: string) => void }}) {{
  return (
    <div style={{{{maxWidth:640,margin:'20px auto',fontFamily:'system-ui'}}}}>
      <h2>{title}</h2>
      {inner}
      <button onClick={{()=>props.go('scr_menu')}}>Back</button>
    </div>
  );
}}
"""

def fallback_screen(screen: dict) -> tuple[str, str]:
    sid = screen.get("id", "")
    name = _comp_name(sid)
    if sid == "scr_login":
        return (f"client/src/screens/{name}.tsx", _login_tsx())
    if sid == "scr_menu":
        return (f"client/src/screens/{name}.tsx", _menu_tsx(screen))
    if sid == "scr_customers":
        return (f"client/src/screens/{name}.tsx", _customers_tsx())
    if sid == "scr_order":
        return (f"client/src/screens/{name}.tsx", _order_tsx())
    if sid == "scr_report":
        return (f"client/src/screens/{name}.tsx", _report_tsx(screen))
    return (f"client/src/screens/{name}.tsx", _generic_tsx(screen))

def _app_tsx(screens: list[dict]) -> str:
    conds = []
    for s in screens:
        sid = s.get("id", "")
        name = _comp_name(sid)
        conds.append(f"      {{cur==='{sid}' && <{name} go={{go}} />}}")
    imports = "\n".join(f"import {_comp_name(s.get('id',''))} from './screens/{_comp_name(s.get('id',''))}';" for s in screens)
    body = "\n".join(conds)
    return f"""import React, {{ useState }} from 'react';
{imports}
export default function App() {{
  const [cur, setCur] = useState('{screens[0].get('id','scr_login') if screens else 'scr_login'}');
  function go(s: string) {{ setCur(s); }}
  return (
    <div>
      <main data-testid="active-screen" data-screen-id={{cur}}>
{body}
      </main>
    </div>
  );
}}
"""

def _main_tsx() -> str:
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
const el = document.getElementById('root');
if (el) createRoot(el).render(<App />);
"""

def _index_html(app_name: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /><title>{app_name}</title></head>
<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>
"""

def _vite_config() -> str:
    return """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  root: 'client',
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:3000' } },
  build: { outDir: '../dist', emptyOutDir: true }
});
"""

def _tsconfig() -> str:
    return """{"compilerOptions":{"target":"ES2020","module":"ESNext","jsx":"react-jsx","strict":true,"esModuleInterop":true,"skipLibCheck":true,"moduleResolution":"bundler"},"include":["client/src"]}"""

def _package_json(app_name: str) -> str:
    return json.dumps({
        "name": app_name.lower().replace(" ", "-") + "-generated",
        "version": "1.0.0",
        "private": True,
        "scripts": {"start": "npm run build && node server/index.js", "build": "vite build"},
        "dependencies": {"express": "^4.18.2", "better-sqlite3": "^9.4.3"},
        "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-react": "^4.2.0",
            "react": "^18.2.0", "react-dom": "^18.2.0", "typescript": "^5.3.0"}
    }, indent=2)

def _server_db_js() -> str:
    return """const fs = require('fs');
const path = require('path');
let Database = null;
try { Database = require('better-sqlite3'); } catch (e) { Database = null; }
function seedPath(jobSeed) { return jobSeed; }
function init(seedFile, dbFile) {
  const seed = JSON.parse(fs.readFileSync(seedFile, 'utf-8'));
  if (!Database) {
    return { mode: 'json', seed };
  }
  const db = new Database(dbFile);
  db.exec("CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT, climit REAL);");
  db.exec("CREATE TABLE IF NOT EXISTS items (sku TEXT PRIMARY KEY, name TEXT, price REAL);");
  db.exec("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, cust TEXT, lines TEXT, total REAL);");
  const nc = db.prepare("SELECT COUNT(*) c FROM customers").get().c;
  if (nc === 0) {
    const ic = db.prepare("INSERT INTO customers (id,name,climit) VALUES (?,?,?)");
    for (const c of (seed.customers || [])) ic.run(c.id, c.name, c.limit);
    const ii = db.prepare("INSERT INTO items (sku,name,price) VALUES (?,?,?)");
    for (const i of (seed.items || [])) ii.run(i.sku, i.name, i.price);
  }
  return { mode: 'sqlite', db };
}
module.exports = { init };
"""

def _server_index_js() -> str:
    return """const express = require('express');
const fs = require('fs');
const path = require('path');
const { init } = require('./db');
const ROOT = path.join(__dirname, '..');
const SEED = path.join(ROOT, 'data', 'seed.json');
const DBF = path.join(ROOT, 'data', 'app.db');
const DIST = path.join(ROOT, 'dist');
const store = init(SEED, DBF);
const app = express();
app.use(express.json());
app.get('/api/health', (req, res) => res.json({ ok: true, mode: store.mode }));
app.get('/api/customers', (req, res) => {
  const q = (req.query.q || '').toLowerCase();
  let rows;
  if (store.mode === 'sqlite') rows = store.db.prepare("SELECT id,name,climit as \\"limit\\" FROM customers").all();
  else rows = store.seed.customers || [];
  if (q) rows = rows.filter(c => ((c.id || '') + (c.name || '')).toLowerCase().includes(q));
  res.json(rows);
});
app.get('/api/items', (req, res) => {
  let rows;
  if (store.mode === 'sqlite') rows = store.db.prepare("SELECT sku,name,price FROM items").all();
  else rows = store.seed.items || [];
  res.json(rows);
});
app.get('/api/orders', (req, res) => {
  if (store.mode === 'sqlite') {
    const rows = store.db.prepare("SELECT cust,lines,total FROM orders ORDER BY id DESC").all();
    res.json(rows.map(r => ({ cust: r.cust, lines: JSON.parse(r.lines), total: r.total })));
  } else {
    const f = path.join(ROOT, 'data', 'orders.json');
    res.json(fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : []);
  }
});
app.post('/api/orders', (req, res) => {
  const { cust, lines, total } = req.body || {};
  if (!cust || !Array.isArray(lines) || !Number.isFinite(Number(total))) {
    return res.status(400).json({ error: 'cust, lines, and numeric total are required' });
  }
  if (store.mode === 'sqlite') {
    store.db.prepare("INSERT INTO orders (cust,lines,total) VALUES (?,?,?)").run(cust, JSON.stringify(lines), Number(total));
  } else {
    const f = path.join(ROOT, 'data', 'orders.json');
    const cur = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : [];
    cur.push({ cust, lines, total: Number(total) });
    fs.writeFileSync(f, JSON.stringify(cur, null, 2));
  }
  res.json({ ok: true, total: Number(total) });
});
if (fs.existsSync(DIST)) app.use(express.static(DIST));
app.get('*', (req, res) => {
  const indexFile = path.join(DIST, 'index.html');
  if (fs.existsSync(indexFile)) return res.sendFile(indexFile);
  return res.status(503).send('Generated React frontend is not built. Run npm start to build and launch it.');
});
const PORT = process.env.PORT || 3000;
if (require.main === module) app.listen(PORT, () => console.log('generated app on ' + PORT + ' mode=' + store.mode));
module.exports = app;
"""
def _migration_notes(spec: dict) -> str:
    low = [r for r in spec.get("rules", []) if float(r.get("confidence", 0)) < 0.5]
    lines = ["# MIGRATION_NOTES.md", "", "Rules with confidence < 0.5 were NOT implemented:"]
    if not low:
        lines.append("- none (all rules >= 0.5 implemented)")
    for r in low:
        lines.append(f"- {r.get('id')}: {r.get('description')}")
    lines += ["", "Shortcuts preserved: F2 save, F5 refresh, Esc cancel.", "data-testid equals AppSpec field id."]
    return "\n".join(lines) + "\n"

def _one_screen(screen: dict, client: Any | None) -> tuple[str, str]:
    if client is not None:
        try:
            import json as _j
            schema = _j.loads((Path(__file__).resolve().parents[1] / "schemas" / "screen_gen.schema.json").read_text(encoding="utf-8"))
            prompt = open(Path(__file__).resolve().parents[1] / "prompts" / "generator.md", encoding="utf-8").read()
            prompt += "\n\nSCREEN:\n" + _j.dumps(screen)
            out = client.chat_json(prompt, schema, f"generate:{screen.get('id')}")
            if isinstance(out, dict) and out.get("content"):
                return (out.get("file") or f"client/src/screens/{_comp_name(screen.get('id',''))}.tsx", out["content"])
        except Exception as e:
            # A configured model failure must not silently downgrade the screen to
            # a handcrafted template and present it as a successful AI migration.
            raise RuntimeError(
                f"Muse screen generation failed for {screen.get('id')}: {e}"
            ) from e
        raise RuntimeError(
            f"Muse returned no usable component for screen {screen.get('id')}"
        )
    # Deterministic templates are an explicit offline/dev mode only.
    return fallback_screen(screen)

def generate_job(job_dir: Path, client: Any | None = None) -> dict:
    job_dir = Path(job_dir)
    spec = _appspec(job_dir)
    screens: list[dict] = spec.get("screens", [])
    if not screens:
        raise ValueError("AppSpec has no screens; refusing to generate an empty application")
    gdir = job_dir / "generated_app"

    # Generate React components independently, then integrate them into one Vite app.
    results: list[tuple[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(screens))) as executor:
        futures = {executor.submit(_one_screen, screen, client): screen for screen in screens}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item[0])
    for relative_path, source in results:
        _write(gdir / relative_path, source)

    _write(gdir / "client/src/lib/rules.ts", rules_ts())
    _write(gdir / "client/src/App.tsx", _app_tsx(screens))
    _write(gdir / "client/src/main.tsx", _main_tsx())
    _write(gdir / "client/index.html", _index_html(spec.get("app", {}).get("name", "App")))
    _write(gdir / "vite.config.ts", _vite_config())
    _write(gdir / "tsconfig.json", _tsconfig())
    _write(gdir / "package.json", _package_json(spec.get("app", {}).get("name", "App")))
    _write(gdir / "server/db.js", _server_db_js())
    _write(gdir / "server/index.js", _server_index_js())
    _write(gdir / "data/seed.json", json.dumps(spec.get("sample_data", {}), indent=2))
    _write(gdir / "data/orders.json", "[]")
    _write(gdir / "MIGRATION_NOTES.md", _migration_notes(spec))
    _write(
        gdir / "README.md",
        "# Generated app\n\nRun `npm install`, then `npm start`. The start script builds the Vite React app and launches the Express server on PORT or 3000.\n",
    )

    # Verify generated React source, not a separately fabricated static HTML page.
    all_tsx = "".join((gdir / relative_path).read_text(encoding="utf-8") for relative_path, _ in results)
    all_tsx += (gdir / "client/src/App.tsx").read_text(encoding="utf-8")
    missing = [
        field.get("id", "")
        for screen in screens
        for field in screen.get("fields", [])
        if field.get("id", "") not in all_tsx
    ]
    if missing:
        raise ValueError(f"React integration failed, missing testids: {missing}")

    log.info("generate done screens=%d source_files=%d", len(screens), len(results) + 10)
    return {
        "generated_app": str(gdir),
        "screens": len(screens),
        "files": len(results) + 10,
        "build_required": True,
    }
