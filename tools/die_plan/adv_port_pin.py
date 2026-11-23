#!/usr/bin/env python3
"""adv_port_pin.py -- PRECHECK-R2 static advisory ADV-PORT-PIN (owner 11-19: an estimator, never a gate).

Every port of a partition wrapper the strict bind EMITS must have a planned pin, else the kit fails at place:
port_bind_gate.py compares the synthesized top's port bits with port_bind_pins.json (gen_phys.port_bind_pin_records)
and an unplanned wrapper port is "PORT_BIND FAIL extra N" (FAIL_PREFLOOR port_bind).  Real cases:
  - KV D28 kv3_pv_v3e (OPUS-FIX-KV-PV-R7 11-22, v3/v3e split): PORT_BIND extra 1 = ri_pv_u_g1_j_rst_n[0]; the bind
    gives each split piece its own reset-spine wrapper port, type_split._reset_spine_pins moved only the parent pin;
  - KV D26 kv3_hub_Wi (FABLE-FIX-KV-HUB-R3 11-21): extra io_pad_die_id[2:0], a bound-only die IO pin with no pads[] row.

Inputs (read only):
  - the strict bind OUT dir: rtl/<module>.sv wrappers (module = bind_report.json types.<T>.module, plus the bind's
    param variants rtl/<module>__pv<hex>.sv), bind_report.json bump_ports[] (part_port per partition),
    bind_parent_id_straps.json types.<T> (bound strap_* pins the kit projects into the plan: r8pad / parent-ID straps).
    kw bind_out=<dir>, else found next to the plan / under the tree (bind_of_record, native_bind/out, <plan dir>_bound).
  - the plan type's pin sources, the same as port_bind_pin_records: buses[].name, ft_slots <name>_i/_o, id_straps /
    count_straps, pads[], infra_ports[], clock.landing_contract.pins[], clock.edge_clocks[].port, reset_spine_pins[]
    (name + width); tap / reset-tree pins by construction: clk*, arst_n, rst_n, start_i, rst_o_<k>, start_o_<k>.
Compared by NAME (bus widths carry the bind's epoch bit), plus the width of reset_spine_pins / pads / straps.

WARN per type: wrapper ports with no planned pin (the PORT_BIND "extra"), and reset_spine_pins / pads rows whose port
the wrapper lacks or whose width differs ("missing").  When the bind out is from another plan (provenance plan sha !=
this plan), the summary says so: a candidate is then judged against the ports the last bind emitted, and types the
bind never emitted (new split pieces) are counted as unbound.

    findings(raw, plan_path, tree=None, bind_out=None, **kw) -> ["WARN ADV-PORT-PIN ..."]
"""
import glob
import hashlib
import json
import os
import re

CHECK = "PORT-PIN"
MAX_LINES = 20
INFRA = re.compile(r"clk\w*|arst_n|rst_n|start_i|rst_o_\d+|start_o_\d+")
_HDR = re.compile(r"^\s*(input|output|inout)\s+(?:(?:wire|logic|reg|signed)\s+)*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?"
                  r"\\?([A-Za-z_]\w*)", re.M)


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def _sha12(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()[:12]


def _die_name(raw):
    d = raw.get("die")
    return d.get("name") if isinstance(d, dict) else d


def _is_bind_out(d):
    return bool(d) and os.path.isfile(os.path.join(d, "bind_report.json")) and os.path.isdir(os.path.join(d, "rtl"))


def find_bind_out(raw, plan_path, tree=None, bind_out=None):
    """-> bind OUT dir or None.  Order: kw bind_out; beside the plan; under the tree (same die, newest)."""
    if bind_out:
        for c in (bind_out, os.path.join(bind_out, "bind"), os.path.join(bind_out, "out")):
            if _is_bind_out(c):
                return c
        return None
    pd = os.path.dirname(os.path.abspath(plan_path)) if plan_path else None
    cands = []
    if pd:
        stem = os.path.splitext(os.path.basename(plan_path))[0]
        for c in (os.path.join(pd, "bind_of_record"), os.path.join(pd, "bind"), os.path.join(pd, "native_bind", "out"),
                  pd + "_bound", os.path.join(pd + "_bound", "bind"),
                  os.path.join(pd, stem + "_bound"), os.path.join(pd, stem + "_bound", "bind")):
            if _is_bind_out(c):
                return c
    if tree:
        die = _die_name(raw)
        pats = ["physical/die_plan/*/plan_of_record/bind_of_record", "physical/die_plan/*/plan_of_record/native_bind/out",
                "physical/die_plan/*/plan_of_record/native_bind/*", "physical/die_plan/*/plan_of_record/*/bind_of_record"]
        for pat in pats:
            for c in glob.glob(os.path.join(tree, pat)):
                if _is_bind_out(c):
                    cands.append(c)
        hits = []
        for c in sorted(set(cands)):
            try:
                with open(os.path.join(c, "bind_report.json")) as f:
                    head = f.read(4096)
                m = re.search(r'"die"\s*:\s*"([^"]+)"', head)
                if die and m and m.group(1) != die:
                    continue
                hits.append((os.path.getmtime(os.path.join(c, "bind_report.json")), c))
            except OSError:
                continue
        if hits:
            return max(hits)[1]
    return None


def wrapper_ports(text, module):
    """{port: width} of module's ANSI header in text, or None."""
    m = re.search(r"(?ms)^\s*module\s+" + re.escape(module) + r"\b(.*?)\)\s*;", text)
    if not m:
        return None
    out = {}
    for kind, hi, lo, name in _HDR.findall(m.group(1)):
        out[name] = 1 if hi == "" else abs(int(hi) - int(lo)) + 1
    return out


def planned_pins(t, bound_straps=(), bumps=()):
    """-> ({name: width or None}) of every pin the kit generator plans for a type (port_bind_pin_records sources)."""
    p = {}
    for b in t.get("buses") or []:
        p.setdefault(b.get("name"), None)
    for s in t.get("ft_slots") or []:
        p.setdefault(f"{s.get('name')}_i", None)
        p.setdefault(f"{s.get('name')}_o", None)
    for s in (t.get("id_straps") or []) + (t.get("count_straps") or []):
        p[s.get("name")] = s.get("width")
    for s in t.get("pads") or []:
        p[s.get("name")] = s.get("width")
    for s in t.get("infra_ports") or []:
        p.setdefault(s.get("name"), None)
    ck = t.get("clock") or {}
    for s in (ck.get("landing_contract") or {}).get("pins") or []:
        p.setdefault(s.get("name"), None)
    for e in ck.get("edge_clocks") or []:
        p.setdefault(e.get("port"), None)
    for s in t.get("reset_spine_pins") or []:
        p[s.get("name")] = s.get("width")
    for n in bound_straps:
        p.setdefault(n, None)
    for n in bumps:
        p.setdefault(n, None)
    return p


def _parts(raw):
    ps = raw.get("partitions") or []
    if isinstance(ps, dict):
        return {k: (v or {}).get("type") for k, v in ps.items()}
    return {p.get("name"): p.get("type") for p in ps if isinstance(p, dict)}


def check(raw, B, base=None):
    """-> (lines, stats) against bind out B.  base = the plan the bind was made from when it is not this plan: a type
    whose pin sources differ from base (re-cut / new pins since that bind) is counted as reshaped and skipped (the
    last bind cannot speak for it); a type unchanged since the bind keeps the bind's verdict (carried over)."""
    with open(os.path.join(B, "bind_report.json")) as f:
        rep = json.load(f)
    rtypes = rep.get("types") or {}
    bumps = {}
    for b in rep.get("bump_ports") or []:
        bumps.setdefault(b.get("partition"), set()).add(b.get("part_port"))
    straps = {}
    sp = os.path.join(B, "bind_parent_id_straps.json")
    if os.path.isfile(sp):
        with open(sp) as f:
            straps = (json.load(f).get("types") or {})
    parts = _parts(raw)
    lines, stats = [], dict(types=0, checked=0, unbound=0, extra=0, missing=0, reshaped=0)
    rtl = os.path.join(B, "rtl")
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        stats["types"] += 1
        mod = (rtypes.get(tn) or {}).get("module") or t.get("module") or tn
        files = [os.path.join(rtl, mod + ".sv")] + sorted(glob.glob(os.path.join(rtl, glob.escape(mod) + "__pv*.sv")))
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            stats["unbound"] += 1
            continue
        ports, seen = {}, 0
        for fp in files:
            with open(fp, errors="replace") as f:
                txt = f.read()
            m = re.search(r"(?m)^\s*module\s+(\w+)", txt)
            got = wrapper_ports(txt, m.group(1)) if m else None
            if got is None:
                continue
            seen += 1
            for k, v in got.items():
                ports.setdefault(k, v)
        if not seen:
            stats["unbound"] += 1
            continue
        stats["checked"] += 1
        bmp = set()
        for pn, tt in parts.items():
            if tt == tn:
                bmp |= bumps.get(pn, set())
        plan = planned_pins(t, (straps.get(tn) or {}).keys(), bmp)
        if base is not None:
            bt = (base.get("partition_types") or {}).get(tn)
            if not isinstance(bt, dict) or planned_pins(bt, (straps.get(tn) or {}).keys(), bmp) != plan:
                stats["reshaped"] += 1
                stats["checked"] -= 1
                continue
        extra = sorted(p for p in ports if p not in plan and not INFRA.fullmatch(p))
        exp = {s.get("name"): (s.get("width"), "reset_spine_pins") for s in t.get("reset_spine_pins") or []}
        exp.update({s.get("name"): (s.get("width"), "pads") for s in t.get("pads") or []})
        miss = sorted(n for n in exp if n not in ports)
        wide = sorted(n for n, (w, _) in exp.items() if n in ports and isinstance(w, int) and ports[n] != w)
        if extra:
            stats["extra"] += len(extra)
            kind = ("reset spine pin" if all(re.match(r"r[is]_", x) for x in extra) else "port")
            fix = ("add partition_types.%s.reset_spine_pins row {name, width, layer M7, sites_um one per bit} next to "
                   "the type reset tap (OPUS-FIX-KV-PV-R7 form)" % tn if kind == "reset spine pin" else
                   "add the plan pin (buses / pads / reset_spine_pins / straps row) or stop the bind emitting it")
            lines.append(_w(tn, f"{len(extra)} wrapper {kind}(s) with no planned pin "
                                f"({', '.join(f'{x} ({ports[x]} b)' for x in extra[:6])}{' ...' if len(extra) > 6 else ''}) "
                                f"vs 0 allowed -> PORT_BIND FAIL extra at place. Fix: {fix}"))
        if miss or wide:
            stats["missing"] += len(miss) + len(wide)
            lines.append(_w(tn, "planned pin rows the wrapper does not carry as declared ("
                                + ", ".join([f"{n} ({exp[n][1]}) absent" for n in miss[:4]]
                                            + [f"{n} plan {exp[n][0]} b vs wrapper {ports[n]} b" for n in wide[:4]])
                                + ") -> PORT_BIND FAIL missing. Fix: drop/rename the stale row or fix its width"))
    return lines, stats


def findings(raw, plan_path, tree=None, bind_out=None, **kw):
    try:
        B = find_bind_out(raw, plan_path, tree, bind_out)
        if not B:
            return [_w("not checked", "no strict bind OUT dir (bind_report.json + rtl/) beside the plan or under the "
                                      "tree; pass bind_out=")]
        note, base = "", None
        try:
            with open(os.path.join(B, "provenance_bind.json")) as f:
                pp = (json.load(f).get("provenance") or {}).get("plan")
            cand = [pp] if pp and os.path.isabs(pp) else [os.path.join(x, pp) for x in (tree, os.path.dirname(B)) if x and pp]
            cand = [c for c in cand if os.path.isfile(c)]
            if cand and plan_path and os.path.isfile(plan_path):
                a, b = _sha12(cand[0]), _sha12(plan_path)
                if a == b:
                    note = "same plan"
                else:
                    with open(cand[0]) as f:
                        base = json.load(f)
                    note = f"bind plan {a} != this plan {b}: types unchanged since that bind carry its verdict"
        except Exception:
            base = None
        lines, st = check(raw, B, base)
        if base is not None:
            note += f", {st['reshaped']} reshaped type(s) need a re-bind to be checked"
        out = lines[:MAX_LINES]
        out.append(_w("summary", f"{len(lines)} type(s) flagged; {st['extra']} unplanned wrapper port(s), "
                                 f"{st['missing']} missing/width; {st['checked']}/{st['types']} types compared, "
                                 f"{st['unbound']} with no wrapper in bind out {B}" + (f"; {note}" if note else "")
                                 + (f"; first {MAX_LINES} shown" if len(lines) > MAX_LINES else "")))
        return out
    except Exception as e:  # never raise
        return [_w("not checked", f"{type(e).__name__}: {e}")]


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    p = sys.argv[1]
    with open(p) as f:
        r = json.load(f)
    t1 = time.time()
    kw = {}
    if len(sys.argv) > 3:
        kw["bind_out"] = sys.argv[3]
    for ln in findings(r, p, (sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None), **kw):
        print(ln)
    print(f"# load {t1 - t0:.1f}s check {time.time() - t1:.2f}s")
