"""adv_rst_sidecar.py -- PRECHECK ADV-RST-SIDECAR (COORD 11-25, QC-SLECTL-RRL class; report only).

Landing collector sources and children name their reset relay by TAP INDEX in the landed sidecar
(zz_sidecar_*.json collector.types[<t>].local_sources[] / children[]: node, else rst_n_t<tap>); bind and kit gen read
those indices, but the reset tree they index is the PLAN's clock.landing_contract.collector_tree.  When the plan tree is
re-numbered (reset solve / tap re-grid) and collector_reattach --sidecar is not re-run, u_cland_collect_<node> and the raw
copy u_cland_rst_<bus> are seated at a far relay (QC C1m: 104 raw hops > 300 um, 20 > 405 um, worst 1463 um).

Measured against the plan tree, per type with a (soft) collector_tree and a sidecar row, the same way as the
QC-RST-SRCTAP builder (hub lanes/handoff/QC-SLECTL-RRL-srctap2.py):
  RAW     local source: seat = the sidecar node's relay; RTL raw parent = the parent ("d") of the ring tap rst_n_t<i>
          nearest the source pin; |seat - raw parent| > RAW_UM (300)       -> reset copy too far
  STATUS  local source: max |status pin - seat| > REACH_UM (405)           -> collector too far
  CHILD   collector child (by order): max |status pin - sidecar node relay| > REACH_UM (405)
  MISSING the sidecar node is not a relay of the plan tree (nor rst_root_n)
Fix: python3 QC-SLECTL-RRL-srctap2.py (re-node to the RTL ring tap) or collector_reattach --sidecar.
Sidecar: kw sidecar= / env OT_ADV_RST_SIDECAR / OT_ADV_COLSYNC_SIDECAR, else adv_colsync's search under the tree.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_colsync as _CS  # noqa: E402

CHECK = "ADV-RST-SIDECAR"
RAW_UM = 300.0
REACH_UM = 405.0
MAX_LINES = 25
_TAP = re.compile(r"rst_n_t\d+")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _node(s):
    return s.get("node") or f"rst_n_t{s.get('tap', 0)}"


def judge_type(lc, st):
    """lc = plan landing_contract, st = sidecar collector.types[t] -> dict(raw, status, child, missing, rows, worst, sample)"""
    tr = lc.get("collector_tree") or {}
    rel = {r.get("q"): r for r in tr.get("relays") or []}
    res = dict(raw=0, status=0, child=0, missing=0, rows=0, worst=0.0, sample=None)
    if not rel:
        return res
    xy = {q: r.get("xy") for q, r in rel.items()}
    if tr.get("root"):
        xy["rst_root_n"] = tr["root"]
    taps = {q: r for q, r in rel.items() if _TAP.fullmatch(str(q)) and r.get("xy")}

    def bad(msg, um):
        res["worst"] = max(res["worst"], um)
        if res["sample"] is None:
            res["sample"] = msg

    sby = {s.get("name"): s for s in st.get("local_sources") or []}
    for s in lc.get("collector_local_sources") or []:
        ss = sby.get(s.get("name"))
        if ss is None or (ss.get("tap") is None and ss.get("node") and not _TAP.fullmatch(ss["node"])):
            continue
        res["rows"] += 1
        node = _node(ss)
        seat = xy.get(node)
        if not seat:
            res["missing"] += 1
            bad(f"source {s.get('name')} sidecar node {node} not in the plan tree", 0.0)
            continue
        pin = s.get("pin_xy_um") or s.get("xy_um")
        pts = s.get("status_pins_xy_um") or ([s["xy_um"]] if s.get("xy_um") else [])
        if pin and taps:
            rt = min(taps, key=lambda q: man(taps[q]["xy"], pin))
            pxy = xy.get(rel[rt].get("d"))
            if pxy:
                a = man(seat, pxy)
                if a > RAW_UM:
                    res["raw"] += 1
                    bad(f"source {s.get('name')} raw copy at {node} {a:.0f} um from its RTL raw parent (ring tap {rt})", a)
        if pts:
            b = max(man(p, seat) for p in pts)
            if b > REACH_UM:
                res["status"] += 1
                bad(f"source {s.get('name')} collector {node} {b:.0f} um from its status pins", b)
    for c, cs in zip(lc.get("collector_children") or [], st.get("children") or []):
        res["rows"] += 1
        node = _node(cs)
        seat = xy.get(node)
        if not seat:
            res["missing"] += 1
            bad(f"child {c.get('index', '?')} sidecar node {node} not in the plan tree", 0.0)
            continue
        pts = c.get("status_pins_xy_um") or ([c["xy_um"]] if c.get("xy_um") else [])
        if pts:
            h = max(man(p, seat) for p in pts)
            if h > REACH_UM:
                res["child"] += 1
                bad(f"child {c.get('index', '?')} collector {node} {h:.0f} um from its status pins", h)
    return res


def _sidecar_path(tree, kw):
    p = kw.get("sidecar") or os.environ.get("OT_ADV_RST_SIDECAR")
    if p:
        return str(p)
    return _CS._find_sidecar(tree, kw) if tree or os.environ.get("OT_ADV_COLSYNC_SIDECAR") else None


def _findings(raw, plan_path, tree=None, **kw):
    sc = kw.get("sidecar_obj")
    path = None
    if sc is None:
        path = _sidecar_path(tree, kw)
        if not path:
            return [_w("NOT-RUN: no landed sidecar with a collector section found (pass sidecar= / OT_ADV_RST_SIDECAR)")]
        sc = json.loads(Path(path).read_text())
    S = ((sc.get("collector") or {}).get("types")) or {}
    out, nt, nbad = [], 0, 0
    tot = dict(raw=0, status=0, child=0, missing=0, rows=0)
    worst = 0.0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        lc = ((t or {}).get("clock") or {}).get("landing_contract") if isinstance(t, dict) else None
        if not isinstance(lc, dict) or not isinstance(lc.get("collector_tree"), dict) or lc["collector_tree"].get("hard") or tn not in S:
            continue
        nt += 1
        r = judge_type(lc, S[tn])
        for k in tot:
            tot[k] += r[k]
        n = r["raw"] + r["status"] + r["child"] + r["missing"]
        if n:
            nbad += 1
            worst = max(worst, r["worst"])
            out.append((n, _w(f"{tn}: {r['raw']} reset copy hop(s) > {RAW_UM:g} um, {r['status']} source collector(s) and {r['child']} child collector(s) "
                              f"> {REACH_UM:g} um, {r['missing']} sidecar node(s) not in the plan tree, of {r['rows']} rows (worst {r['worst']:.0f} um); "
                              f"first: {r['sample']}; bind/gen read the sidecar tap, the tree is the plan's: re-run collector_reattach --sidecar "
                              f"(or QC-SLECTL-RRL srctap2)")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nbad} of {nt} types with a collector sidecar row: {tot['raw']} RAW > {RAW_UM:g} um, {tot['status']} STATUS + "
                               f"{tot['child']} CHILD > {REACH_UM:g} um, {tot['missing']} MISSING of {tot['rows']} rows (worst {worst:.0f} um); "
                               f"sidecar {path or '<given>'}"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None,
                       sidecar=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
