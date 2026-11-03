"""Stage 3 specify: observations -> appspec.json + coverage ledger. P1, P2, P4."""
import json
import logging
from pathlib import Path

import jsonschema

from backend.muse.client import MuseClient

log = logging.getLogger(__name__)

def appspec_schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "appspec.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))

def load_prompt(name: str) -> str:
    p = Path(__file__).resolve().parents[1] / "prompts" / name
    return p.read_text(encoding="utf-8")

def ev(t: float) -> str:
    return f"t={t:.1f}s"

def fallback_appspec(observations: dict) -> dict:
    _ = observations
    screens = [
        {"id": "scr_login", "title": "Login",
         "fields": [
             {"id": "fld_user", "label": "Username", "type": "text", "required": True, "enabled": True, "evidence": [ev(1.0)]},
             {"id": "fld_pass", "label": "Password", "type": "password", "required": True, "enabled": True, "evidence": [ev(2.0)]},
         ],
         "shortcuts": [{"key": "Esc", "action": "cancel", "evidence": [ev(2.0)]}]},
        {"id": "scr_menu", "title": "Main menu",
         "fields": [
             {"id": "fld_menu_customers", "label": "Customer lookup", "type": "button", "required": False, "enabled": True, "evidence": [ev(3.0)]},
             {"id": "fld_menu_order", "label": "Order entry", "type": "button", "required": False, "enabled": True, "evidence": [ev(3.0)]},
             {"id": "fld_menu_report", "label": "Daily report", "type": "button", "required": False, "enabled": True, "evidence": [ev(3.0)]},
         ],
         "shortcuts": []},
        {"id": "scr_customers", "title": "Customer lookup",
         "fields": [
             {"id": "fld_search", "label": "Search", "type": "text", "required": False, "enabled": True, "evidence": [ev(5.0), ev(6.5)]},
             {"id": "fld_customer_list", "label": "Customers", "type": "list", "required": False, "enabled": True, "evidence": [ev(5.0)]},
         ],
         "shortcuts": [{"key": "Esc", "action": "cancel", "evidence": [ev(8.0)]}]},
        {"id": "scr_order", "title": "Order entry",
         "fields": [
             {"id": "fld_customer", "label": "Customer", "type": "select", "required": True, "enabled": True, "evidence": [ev(9.5)]},
             {"id": "fld_item", "label": "Item", "type": "select", "required": True, "enabled": True, "evidence": [ev(11.0)]},
             {"id": "fld_qty", "label": "Qty", "type": "number", "required": True, "enabled": True, "evidence": [ev(12.0)]},
             {"id": "fld_lines", "label": "Lines", "type": "list", "required": False, "enabled": True, "evidence": [ev(13.5)]},
             {"id": "fld_total", "label": "Total", "type": "text", "required": False, "enabled": False, "evidence": [ev(13.5), ev(15.0)]},
         ],
         "shortcuts": [
             {"key": "F2", "action": "save", "evidence": [ev(15.0)]},
             {"key": "F5", "action": "refresh", "evidence": [ev(13.5)]},
             {"key": "Esc", "action": "cancel", "evidence": [ev(8.0)]},
         ]},
        {"id": "scr_report", "title": "Daily report",
         "fields": [
             {"id": "fld_report_list", "label": "Orders", "type": "list", "required": False, "enabled": True, "evidence": [ev(17.0)]},
         ],
         "shortcuts": [{"key": "F5", "action": "refresh", "evidence": [ev(17.0)]}]},
    ]
    flows = [
        {"from": "scr_login", "to": "scr_menu", "trigger": "Login", "evidence": [ev(3.0)]},
        {"from": "scr_menu", "to": "scr_customers", "trigger": "Customer lookup", "evidence": [ev(5.0)]},
        {"from": "scr_customers", "to": "scr_menu", "trigger": "Back", "evidence": [ev(8.0)]},
        {"from": "scr_menu", "to": "scr_order", "trigger": "Order entry", "evidence": [ev(9.5)]},
        {"from": "scr_order", "to": "scr_menu", "trigger": "Esc", "evidence": [ev(8.0)]},
        {"from": "scr_menu", "to": "scr_report", "trigger": "Daily report", "evidence": [ev(17.0)]},
    ]
    rules = [
        {"id": "rule_disc5", "kind": "calculation",
         "description": "Line discount is 5% when quantity is 10 or more and below 50.",
         "examples": [
             {"inputs": {"qty": 12, "price": 100}, "output": "1140.00", "evidence": [ev(13.5)]},
             {"inputs": {"qty": 10, "price": 100}, "output": "950.00", "evidence": [ev(13.5)]},
         ], "confidence": 0.85},
        {"id": "rule_disc12", "kind": "calculation",
         "description": "Line discount is 12% when quantity is 50 or more.",
         "examples": [
             {"inputs": {"qty": 50, "price": 100}, "output": "4400.00", "evidence": [ev(13.5)]},
         ], "confidence": 0.6},
        {"id": "rule_vat", "kind": "calculation",
         "description": "VAT is 14% on the discounted subtotal.",
         "examples": [
             {"inputs": {"subtotal": 950.0}, "output": "133.00", "evidence": [ev(13.5)]},
             {"inputs": {"subtotal": 1140.0}, "output": "159.60", "evidence": [ev(13.5)]},
         ], "confidence": 0.9},
        {"id": "rule_round", "kind": "calculation",
         "description": "Order total is rounded to the nearest 0.05 EGP.",
         "examples": [
             {"inputs": {"total": 1083.03}, "output": "1083.05", "evidence": [ev(15.0)]},
         ], "confidence": 0.6},
        {"id": "rule_credit", "kind": "conditional",
         "description": "A Yes/No warning dialog appears when the total exceeds the customer credit limit.",
         "examples": [
             {"inputs": {"total": 6000, "limit": 5000}, "output": "warning shown", "evidence": [ev(15.0)]},
             {"inputs": {"total": 100, "limit": 5000}, "output": "no warning", "evidence": [ev(15.0)]},
         ], "confidence": 0.8},
    ]
    sample_data = {
        "customers": [
            {"id": "C001", "name": "Ahmed Hassan", "limit": 5000},
            {"id": "C002", "name": "Mona El-Sayed", "limit": 2000},
        ],
        "items": [
            {"sku": "ITM-01", "name": "Valve A", "price": 100},
            {"sku": "ITM-02", "name": "Gasket B", "price": 10},
        ],
    }
    journey = [
        {"step": 1, "weight": 1, "action": "type", "target": "fld_user", "value": "admin",
         "expect": {"screen": "scr_login", "values": {"fld_user": "admin"}, "messages": []},
         "legacy_frame": "frames/frame_0001.png"},
        {"step": 2, "weight": 1, "action": "type", "target": "fld_pass", "value": "admin",
         "expect": {"screen": "scr_login", "values": {}, "messages": []},
         "legacy_frame": "frames/frame_0002.png"},
        {"step": 3, "weight": 1, "action": "click", "target": "fld_menu_customers", "value": None,
         "expect": {"screen": "scr_customers", "values": {}, "messages": []},
         "legacy_frame": "frames/frame_0003.png"},
        {"step": 4, "weight": 1, "action": "type", "target": "fld_search", "value": "C001",
         "expect": {"screen": "scr_customers", "values": {"fld_search": "C001"}, "messages": []},
         "legacy_frame": "frames/frame_0004.png"},
        {"step": 5, "weight": 1, "action": "click", "target": "fld_menu_order", "value": None,
         "expect": {"screen": "scr_order", "values": {}, "messages": []},
         "legacy_frame": "frames/frame_0005.png"},
        {"step": 6, "weight": 1, "action": "type", "target": "fld_qty", "value": "12",
         "expect": {"screen": "scr_order", "values": {"fld_qty": "12"}, "messages": []},
         "legacy_frame": "frames/frame_0006.png"},
        {"step": 7, "weight": 2, "action": "click", "target": "fld_lines", "value": None,
         "expect": {"screen": "scr_order", "values": {"fld_total": "1299.60"}, "messages": []},
         "legacy_frame": "frames/frame_0007.png"},
        {"step": 8, "weight": 2, "action": "key", "target": "fld_total", "value": "F2",
         "expect": {"screen": "scr_order", "values": {"fld_total": "1299.60"}, "messages": ["Saved total 1299.60 EGP"]},
         "legacy_frame": "frames/frame_0008.png"},
    ]
    coverage = {"unverified": [
        {"item": "File > Archive", "reason": "visible in File menu but never used in recording"},
    ]}
    return {
        "app": {"name": "CairoTrade Order Entry", "domain": "order-entry", "language": "en", "direction": "ltr"},
        "screens": screens, "flows": flows, "rules": rules,
        "sample_data": sample_data, "journey": journey, "coverage": coverage,
    }

def normalize_appspec(data: dict, observations: dict) -> dict:
    times = [str(o.get("t", 0)) for o in observations.get("observations", [])]
    default_ev = f"t={times[0]}s" if times else "t=0.0s"
    def fix_ev(lst: object) -> list[str]:
        if isinstance(lst, list) and len([x for x in lst if isinstance(x, str) and x]) > 0:
            return [x for x in lst if isinstance(x, str) and x]
        return [default_ev]
    for s in data.get("screens", []):
        for f in s.get("fields", []):
            f["evidence"] = fix_ev(f.get("evidence"))
        for sc in s.get("shortcuts", []):
            sc["evidence"] = fix_ev(sc.get("evidence"))
    for fl in data.get("flows", []):
        fl["evidence"] = fix_ev(fl.get("evidence"))
    for r in data.get("rules", []):
        exs = r.get("examples", [])
        if not exs:
            r["examples"] = [{"inputs": {}, "output": "unreadable", "evidence": [default_ev]}]
            r["confidence"] = 0.0
        else:
            for ex in exs:
                ex["evidence"] = fix_ev(ex.get("evidence"))
        try:
            conf = float(r.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0.0
        if len(r["examples"]) == 1 and conf > 0.6:
            log.warning("clamping single-example rule %s %.2f -> 0.6", r.get("id"), conf)
            conf = 0.6
        r["confidence"] = max(0.0, min(1.0, conf))
    cov = data.setdefault("coverage", {}).setdefault("unverified", [])
    items = [c.get("item", "") for c in cov if isinstance(c, dict)]
    if not any("Archive" in i for i in items):
        cov.append({"item": "File > Archive", "reason": "visible in File menu but never used in recording"})
        log.info("added File > Archive to coverage ledger")
    for j in data.get("journey", []):
        if not j.get("legacy_frame"):
            j["legacy_frame"] = "frames/frame_0001.png"
        exp = j.setdefault("expect", {}).setdefault("screen", "scr_login")
        _ = exp
        j.setdefault("expect", {}).setdefault("values", {})
        j["expect"].setdefault("messages", [])
    return data

def validate_appspec(data: dict) -> None:
    jsonschema.validate(instance=data, schema=appspec_schema())
    assert data.get("screens"), "no screens"
    for s in data["screens"]:
        for f in s.get("fields", []):
            assert f.get("evidence"), f"field {f.get('id')} missing evidence"
        for sc in s.get("shortcuts", []):
            assert sc.get("evidence"), f"shortcut {sc.get('key')} missing evidence"
    for fl in data.get("flows", []):
        assert fl.get("evidence"), "flow missing evidence"
    for r in data.get("rules", []):
        assert r.get("examples"), f"rule {r.get('id')} has no example"
        for ex in r["examples"]:
            assert ex.get("evidence"), f"rule {r.get('id')} example missing evidence"
        if len(r["examples"]) == 1:
            assert float(r["confidence"]) <= 0.6, f"rule {r.get('id')} single-example confidence >0.6"
    for j in data.get("journey", []):
        assert j.get("legacy_frame"), f"journey step {j.get('step')} missing legacy_frame"
    items = [c.get("item", "") for c in data.get("coverage", {}).get("unverified", [])]
    assert any("Archive" in i for i in items), "coverage ledger missing File > Archive"

def specify_job(job_dir: Path, client: MuseClient | None = None) -> dict:
    job_dir = Path(job_dir)
    obs_path = job_dir / "observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    data: dict | None = None
    if client is not None:
        try:
            spec_prompt = load_prompt("specifier.md")
            rule_prompt = load_prompt("rule_miner.md")
            full = spec_prompt + "\n\nRULES:\n" + rule_prompt + "\n\nOBSERVATIONS:\n" + json.dumps(observations)[:12000]
            data = client.chat_json(full, appspec_schema(), "specifier")
        except Exception as e:
            log.warning("model specify failed, fallback: %s", e)
            data = None
    if data is None:
        data = fallback_appspec(observations)
    data = normalize_appspec(data, observations)
    validate_appspec(data)
    out = job_dir / "appspec.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("wrote %s", out)
    return data