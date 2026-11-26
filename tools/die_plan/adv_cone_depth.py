#!/usr/bin/env python3
"""adv_cone_depth.py -- PRE advisory ADV-CONE-DEPTH (class C-CONE-DEPTH, QC-INT-R2-TOOLS 11-26, QC-INT-R2 tools round 2 item 1).

Class: a register-to-register logic cone deeper than one clock period allows.  sle_hc0 cl38badc56 and sle_stm_v2 closed at TT -86 ps / worse after
three ECO attempts (P-ECO-NO-GAIN): the cause is cone depth, which no placement or ECO can repair; it is cheaper to see in the RTL elab than after P&R.

Metadata only, no synthesis: the word-level yosys elaboration the bind writes (bind/asbuilt.json: {"modules": {name: {cells, ports, netnames}}}).
Per module the register-to-register / port cone depth is the longest path of word-level cells between sequential cells ($dff*, $mem*, $dlatch),
module input ports and sub-module instances (instances are boundaries: a module is judged on its own cells).  Each cell costs gate LEVELS by
type and width (LEVELS below: bitwise 1, mux 1, pmux log2 n + 1, compare / eq / reduce log2 w, add / sub / lt prefix 2 log2 w + 2, shift log2 w,
mul 4 log2 w + 2, mem read 3); estimated delay = levels x STAGE_PS.
Budget per stage = clock period (plan die.period_ps) - OVERHEAD_PS (clk->q + setup + uncertainty, as adv_leg_delay) ; STAGE_PS = ASAP7 RVT
logic level incl. local wire at the plan's TT corner (22 ps; $OT_CONE_STAGE_PS).  A module whose deepest cone costs more than the budget is flagged
with its endpoint net, levels, estimated ps and the plan types whose module / contents name it.

Coverage limit (stated, not hidden): the lint sees only RTL that is in the elab json.  Slice cores whose RTL lives outside the bound tree (the
sle_* / slw_* S81-style slices, hard macros) are not in the QC C9 as-built; they are counted as "types without elab RTL".

    findings(raw, plan_path, tree=None, asbuilt=None, yosys_json=None, **kw) -> lines, never raises
    python3 -I tools/die_plan/adv_cone_depth.py PLAN.json YOSYS_ASBUILT.json
"""
import json
import math
import os
import re
import sys
from pathlib import Path

CHECK = "CONE-DEPTH"
OVERHEAD_PS = 130.0
DEFAULT_PERIOD_PS = 833.0
MAX_LINES = 15
SEQ = re.compile(r"^\$(a?dff|sdff|dffe|adffe|sdffe|sdffce|dffsr|dffsre|aldff|aldffe|dlatch|adlatch|dlatchsr|sr|mem|mem_v2|memrd_v2|memwr_v2|fsm)$")
BITWISE = {"$not", "$and", "$or", "$xor", "$xnor", "$logic_not", "$logic_and", "$logic_or", "$pos", "$neg_bit"}
REDUCE = {"$reduce_and", "$reduce_or", "$reduce_xor", "$reduce_xnor", "$reduce_bool"}
COMPARE = {"$eq", "$ne", "$eqx", "$nex"}
ARITH = {"$add", "$sub", "$lt", "$le", "$gt", "$ge", "$neg", "$alu", "$lcu", "$macc"}
SHIFT = {"$shl", "$shr", "$sshl", "$sshr", "$shift", "$shiftx"}


def stage_ps(env=None):
    try:
        return float((env if env is not None else os.environ).get("OT_CONE_STAGE_PS", "22"))
    except ValueError:
        return 22.0


def _w(cell, key, default=1):
    try:
        return max(1, int(str(cell.get("parameters", {}).get(key, default)), 2))
    except (TypeError, ValueError):
        return default


def _lg(n):
    return math.ceil(math.log2(max(2, n)))


def cell_levels(cell):
    """gate levels one word-level cell adds to a path through it"""
    t = cell.get("type", "")
    if t in BITWISE:
        return 1.0
    if t == "$mux" or t == "$bmux":
        return 1.0 if t == "$mux" else float(_lg(_w(cell, "S_WIDTH", 2)) + 1)
    if t == "$pmux":
        return _lg(_w(cell, "S_WIDTH", 2)) + 1.0
    if t in REDUCE or t in COMPARE:
        return float(_lg(max(_w(cell, "A_WIDTH"), _w(cell, "B_WIDTH", 1))) + (1 if t in COMPARE else 0))
    if t in ARITH:
        return 2.0 * _lg(max(_w(cell, "A_WIDTH"), _w(cell, "B_WIDTH", 1))) + 2.0
    if t in SHIFT:
        return float(_lg(_w(cell, "A_WIDTH")))
    if t in ("$mul", "$div", "$mod", "$divfloor", "$modfloor", "$pow"):
        return 4.0 * _lg(max(_w(cell, "A_WIDTH"), _w(cell, "B_WIDTH"))) + 2.0
    if t == "$memrd" or t.startswith("$memrd"):
        return 3.0
    return 1.0


def module_depth(mod):
    """-> (max levels, endpoint net / cell name, n comb cells).  Sequential cells, input ports and instances are path boundaries."""
    cells = mod.get("cells") or {}
    drv = {}
    comb = {}
    for name, c in cells.items():
        t = c.get("type", "")
        if SEQ.match(t) or not t.startswith("$"):
            continue
        comb[name] = c
        pd = c.get("port_directions") or {}
        for port, bits in (c.get("connections") or {}).items():
            if pd.get(port) == "output":
                for b in bits:
                    if isinstance(b, int):
                        drv[b] = name
    depth = {}

    def of(name):
        # iterative post-order, comb loops cut at depth 0
        stack = [(name, False)]
        while stack:
            n, done = stack.pop()
            if n in depth and not done:
                continue
            c = comb[n]
            ins = [drv[b] for p, bits in (c.get("connections") or {}).items() if (c.get("port_directions") or {}).get(p) == "input"
                   for b in bits if isinstance(b, int) and b in drv and drv[b] != n]
            if not done:
                depth.setdefault(n, None)
                stack.append((n, True))
                stack.extend((i, False) for i in ins if i not in depth)
            else:
                depth[n] = cell_levels(c) + max((depth[i] or 0.0 for i in ins), default=0.0)
        return depth[name]

    best, where = 0.0, ""
    for name in comb:
        lv = of(name) if name not in depth or depth[name] is None else depth[name]
        if lv > best:
            best, where = lv, name
    names = {}
    for nn, d in (mod.get("netnames") or {}).items():
        for b in d.get("bits", []):
            if isinstance(b, int):
                names.setdefault(b, nn)
    if where:
        cw, found = comb[where], None
        for p, bits in (cw.get("connections") or {}).items():
            if (cw.get("port_directions") or {}).get(p) == "output":
                found = found or next((names[b] for b in bits if isinstance(b, int) and b in names), None)
        where = found or where
    return best, where, len(comb)


def plan_period(raw):
    d = raw.get("die")
    try:
        return float((d or {}).get("period_ps")) if isinstance(d, dict) else DEFAULT_PERIOD_PS
    except (TypeError, ValueError):
        return DEFAULT_PERIOD_PS


def hdl_name(mname, mod):
    h = ((mod.get("attributes") or {}).get("hdlname")) or mname
    return str(h).split()[-1].lstrip("\\")


def type_index(raw):
    """{module name: [plan types]} from partition_types[*].module / landing_base_type / contents[].module"""
    idx = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        if not isinstance(t, dict):
            continue
        for m in [t.get("module"), t.get("landing_base_type")] + [c.get("module") for c in t.get("contents") or [] if isinstance(c, dict)]:
            if isinstance(m, str):
                idx.setdefault(m, []).append(tn)
    return idx


def judge(raw, yj, ps=None):
    """-> (rows [(module, levels, est_ps, endpoint, ncells, types)], budget_ps, stage_ps); rows over budget only"""
    ps = stage_ps() if ps is None else ps
    budget = plan_period(raw) - OVERHEAD_PS
    idx = type_index(raw)
    rows, seen = [], {}
    for mname, mod in (yj.get("modules") or {}).items():
        hn = hdl_name(mname, mod)
        lv, where, n = module_depth(mod)
        if hn in seen and seen[hn] >= lv:
            continue
        seen[hn] = lv
        rows = [r for r in rows if r[0] != hn]
        if lv * ps > budget:
            rows.append((hn, lv, round(lv * ps, 1), where, n, sorted(set(idx.get(hn, [])))))
    return sorted(rows, key=lambda r: -r[2]), budget, ps, len(seen)


def find_yosys_json(asbuilt=None, yosys_json=None, tree=None, env=None):
    env = os.environ if env is None else env
    cands = [yosys_json, env.get("OT_CONE_YOSYS_JSON")]
    if asbuilt:
        cands += [Path(asbuilt).parent / "asbuilt.json", Path(asbuilt).parent / "bind" / "asbuilt.json"]
    for c in cands:
        if c and Path(c).is_file():
            try:
                with open(c) as f:
                    head = f.read(2000)
                if '"modules"' in head:
                    return Path(c)
            except OSError:
                continue
    return None


def findings(raw, plan_path=None, tree=None, asbuilt=None, yosys_json=None, **kw):
    try:
        p = find_yosys_json(asbuilt, yosys_json, tree)
        if p is None:
            return []                       # no elab json next to this plan: nothing to judge, no line
        yj = json.loads(p.read_text())
        rows, budget, ps, nmod = judge(raw, yj)
        idx = type_index(raw)
        out = [f"WARN ADV-CONE-DEPTH {r[0]}: deepest register/port cone {r[1]:g} levels x {ps:g} ps = {r[2]:g} ps over the {budget:g} ps stage budget "
               f"(period - {OVERHEAD_PS:g}), end {r[3] or '?'}, {r[4]} comb cells; plan types {','.join(r[5][:4]) or '-'} "
               "(fix: pipeline the cone / retime; no P&R or ECO recovers it)" for r in rows]
        n_t = len(raw.get("partition_types") or {})
        have = {hdl_name(k, v) for k, v in (yj.get("modules") or {}).items()}
        covered = {t for m, ts in idx.items() if m in have for t in ts}
        deepest = max(((module_depth(v)[0], hdl_name(k, v)) for k, v in (yj.get("modules") or {}).items()), default=(0.0, "-"))
        out.append(f"LIST CONE-DEPTH deepest {deepest[0]:g} levels ({deepest[1]}); modules judged {nmod} flagged {len(rows)} budget {budget:g} ps stage {ps:g} ps; plan types with elab RTL {len(covered)} of {n_t} "
                   f"(types without elab RTL are not judged); json {p}")
        return out[:MAX_LINES] + out[-1:] if len(out) > MAX_LINES + 1 else out
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [f"WARN ADV-CONE-DEPTH not checked: {type(e).__name__}: {str(e)[:160]}"]


if __name__ == "__main__":
    raw = json.loads(Path(sys.argv[1]).read_text())
    for x in findings(raw, sys.argv[1], yosys_json=sys.argv[2]):
        print(x)
