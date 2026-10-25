#!/usr/bin/env python3
"""REGIONAL RESET RELAY COPIES (KV-RELAYGEN 2026-10-19, owner SAFE-DESIGN checklist item 3; audit
results/arch/safe_audit_1019/kv.md: every HOST-cluster child drove ONE reset relay flop per member into 600..7,800 flops).

The RTL generators (tools/qwen_kv_die/host_cluster/gen_prompt_rr.py, tools/ref_tile/face_land.py, the reset landing of
physical/common_flow/ot_pin_regs.tcl) emit a relay with N KEPT, logically identical copies (ot_rst_relay REGIONS N, or the
landing's last stage replicated N times), but a member has one rst_n pin, so every reset flop of the member still hangs off
copy 0.  This pass runs in synthesis (physical/common_flow/ot_rst_copies.tcl, sourced by ot_keep_regs.tcl when
OT_RST_COPIES_MAX is set) on the FLATTENED coarse netlist and re-points the loads of each copy family over its copies:

  * a FAMILY is a multi-bit wire whose name matches --re (or that carries the ot_rst_split attribute of the KV-PEER5
    gen_peer_rr wrappers) and whose every bit is driven by a flip-flop with the same type,
    parameters, clock, D and reset (an identical register copy).  The pass PROVES this per bit and refuses the family
    otherwise -- that structural identity is the whole equivalence argument (re-pointing a load between identical
    registers cannot change the function);
  * a LOAD is a cell input port whose every bit is a bit of the family; its weight is the flop count it stands for (the
    WIDTH of a multi-bit flop cell on a 1-bit reset/enable port, else the bit count).  A port that mixes family and other
    bits stays where it is (counted on its copy);
  * the movable loads are sorted by hierarchical name (members and their sub-blocks stay together, so each copy serves
    one region of the placement: the copy flop has only that group as loads and placement puts it there) and cut into N
    groups of about total/N each;
  * output: a yosys script (add -wire / connect -set / connect -port) and a table.  Copies stay KEPT cells (ot_keep_regs
    keep attribute), so opt_merge cannot fold them back; the gate's textbook_lint high_fanout check on 1_2_yosys.v is the
    independent post-synthesis witness (<= max loads per copy).

  * KV-PC SAFE 2026-10-19 (opt-in, every existing family unchanged): a STRIDED family (* ot_rst_split = W *) with an
    integer value W >= 2 is N kept copies of a W-bit register laid out copy-major (copy k = bits [k*W +: W]); it is W
    families, one per bit position i (bits i, i+W, ...), each proven and split as above;
  * --wide (OT_RST_COPIES_WIDE=1, opt-in): the prep also maps the memories and the coarse non-register cells that read a
    family bit on a 1-bit port into gate-level cells (memory_collect + memory_map of those memories, techmap of those
    cells; the flow maps them the same way later), so a register copy that selects a wide mux / memory read word is
    split per gate (a 288-bit $mux on one select bit is otherwise one indivisible load).  Function unchanged.

  * KV-PC6 2026-10-20 (leaf-equivalent controls): an input bit of a copy may differ from copy 0's if both are driven by
    the same output of KEPT-HIERARCHY leaf cells (a user module that `flatten` left as a cell because of keep_hierarchy)
    of one type and parameters whose module is PURELY COMBINATIONAL (no flop / latch / memory / blackbox, recursively)
    and whose inputs are themselves equivalent (recursively, depth <= LEAF_DEPTH).  Such leaves compute the same
    function of the same nets, so the copies are still identical registers; this is what lets N > 32 copies take their
    set / enable from per-group kept decision leaves (each leaf <= 32 loads) instead of one N-load net.  Primitive
    ($-type) cells are never looked through (opt_merge would fold them back into one net later).

  python3 ot_rst_copies.py --json in.json --max 256 --ys out.ys --tsv out.tsv [--re REGEX] [--top NAME]
exit 0 always when the JSON parses (groups over --max are reported as OVER lines and in the table: the gate judges them);
exit 2 on unusable input.
"""
import argparse
import json
import math
import re
import sys

DEFAULT_RE = r"(^|\.)(u_rst_relay|u_fl_rst_[A-Za-z0-9_]+)\.rst_n$|__ot_rlv$|__ot_rl[0-9]+v$"
FLOP_RE = re.compile(r"^\$(_[A-Z]*DFF[A-Z]*_[NP01_]*|adff|adffe|dff|dffe|sdff|sdffe|sdffce|aldff|aldffe|dffsr|dffsre)$")
SAFE_NAME = re.compile(r"^[^\s;#\"{}]+$")


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def top_module(nl, top=None):
    mods = nl["modules"]
    if top:
        if top not in mods:
            raise SystemExit(f"ot_rst_copies: top {top} not in netlist")
        return top, mods[top]
    for n, m in mods.items():
        a = m.get("attributes") or {}
        if str(a.get("top", "0")).strip("0") != "":
            return n, m
    raise SystemExit("ot_rst_copies: no top module attribute")


def yname(n):
    """JSON name -> yosys command identifier (public names get the backslash, private $ names stay)"""
    return n if n.startswith("$") or n.startswith("\\") else "\\" + n


def flop_width(cell):
    p = cell.get("parameters") or {}
    w = p.get("WIDTH")
    if w is None:
        return 1
    try:
        return int(str(w), 2) if set(str(w)) <= {"0", "1"} else int(w)
    except ValueError:
        return 1


def split_stride(nn):
    """the stride W of a (* ot_rst_split = W *) family (W >= 2), else 1 (a plain marker / regexp family)"""
    v = (nn.get("attributes") or {}).get("ot_rst_split")
    if v is None:
        return 1
    s = str(v).strip()
    try:
        w = int(s, 2) if s and set(s) <= {"0", "1"} and len(s) >= 8 else int(s)
    except ValueError:
        return 1
    return w if w >= 2 else 1


def analyse(nl, max_loads, rx, top=None):
    tname, m = top_module(nl, top)
    cells = m.get("cells") or {}
    drv = {}        # bit -> (cell, port, idx)
    loads = {}      # bit -> set of (cell, port)
    for cn, c in cells.items():
        dirs = c.get("port_directions") or {}
        for p, bits in (c.get("connections") or {}).items():
            d = dirs.get(p, "input")
            for i, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                if d == "output":
                    drv[b] = (cn, p, i)
                else:
                    loads.setdefault(b, set()).add((cn, p))
    rxc = re.compile(rx)
    fams, seen = [], set()
    for wn in sorted(m.get("netnames") or {}, key=natural):
        nn = m["netnames"][wn]
        bits = nn.get("bits") or []
        marked = "ot_rst_split" in (nn.get("attributes") or {})   # KV-PEER5 wrappers: (* keep, ot_rst_split *) <r>_qv
        if len(bits) < 2 or not all(isinstance(b, int) for b in bits) or not (rxc.search(wn) or marked):
            continue
        key = tuple(bits)
        if key in seen or len(set(bits)) != len(bits):
            continue
        seen.add(key)
        w = split_stride(nn) if marked else 1
        if w > 1:
            if len(bits) % w or len(bits) // w < 2:
                fams.append((wn, bits))          # malformed stride: proven (and refused) as one family
                continue
            for i in range(w):
                fams.append((f"{wn}__s{i}", bits[i::w]))
            continue
        fams.append((wn, bits))
    out = []
    canon = leaf_canon(nl, cells, drv)
    for wn, bits in fams:
        out.append(split_family(wn, bits, cells, drv, loads, max_loads, m, canon))
    return tname, out


LEAF_DEPTH = 4
COMB_PRIM = re.compile(r"^\$(_(BUF|NOT|AND|NAND|OR|NOR|XOR|XNOR|ANDNOT|ORNOT|MUX|NMUX|AOI3|OAI3|AOI4|OAI4)_|buf|pos|neg|not|"
                       r"and|or|xor|xnor|reduce_and|reduce_or|reduce_xor|reduce_xnor|reduce_bool|logic_not|logic_and|"
                       r"logic_or|eq|ne|eqx|nex|lt|le|gt|ge|add|sub|mux|pmux|bmux|shl|shr|sshl|sshr|shift|shiftx)$")


def comb_module_test(nl):
    """Prove a defined, total combinational DAG, not merely absence of flop cells.

    Every internal/output bit must have exactly one input/cell driver and every
    cell input must reach a known constant or a formal input without a cycle.
    Partial mux/shift operators need a separate selection/width proof; none is
    inferred here. This proves leaf functions only, never equality of flop Qs
    before their caller's common reset/update obligation has been established.
    """
    memo = {}

    def parameters(c, expected):
        actual = c.get("parameters") or {}
        return (isinstance(actual, dict) and isinstance(expected, dict)
                and {k: (type(v), v) for k, v in actual.items()} ==
                    {k: (type(v), v) for k, v in expected.items()})

    def ports(c, mod):
        ps = mod.get("ports") or {}
        con = c.get("connections") or {}
        dirs = {p: v.get("direction") for p, v in ps.items()}
        return (isinstance(con, dict) and set(con) == set(ps)
                and all(isinstance(con[p], list) and len(con[p]) == len(ps[p].get("bits", [])) for p in ps)
                and (not c.get("port_directions") or c["port_directions"] == dirs))

    def primitive(c):
        t = c.get("type", "")
        if not COMB_PRIM.fullmatch(t) or t in {
                "$pmux", "$bmux", "$shiftx", "$shift", "$shl", "$shr", "$sshl", "$sshr"}:
            return None
        if t.startswith("$_"):
            op = t[2:-1]
            ins = ("A",) if op in {"BUF", "NOT"} else (
                ("A", "B", "S") if op in {"MUX", "NMUX"} else
                ("A", "B", "C", "D") if op in {"AOI4", "OAI4"} else
                ("A", "B", "C") if op in {"AOI3", "OAI3"} else ("A", "B"))
        else:
            ins = (("A", "B", "S") if t == "$mux" else ("A",) if
                   t in {"$buf", "$pos", "$neg", "$not", "$logic_not"} or t.startswith("$reduce_")
                   else ("A", "B"))
        con = c.get("connections") or {}
        dirs = {p: "input" for p in ins}; dirs["Y"] = "output"
        if set(con) != set(dirs) or (c.get("port_directions") and c["port_directions"] != dirs):
            return None
        if any(not isinstance(v, list) or not v for v in con.values()):
            return None
        if t.startswith("$_") and (any(len(v) != 1 for v in con.values()) or c.get("parameters")):
            return None
        if t == "$mux" and (len(con["S"]) != 1 or len(con["A"]) != len(con["B"]) or len(con["A"]) != len(con["Y"])):
            return None
        allowed = {"WIDTH"} if t == "$mux" else {"A_WIDTH", "B_WIDTH", "Y_WIDTH", "A_SIGNED", "B_SIGNED"}
        for p, v in (c.get("parameters") or {}).items():
            if p not in allowed or isinstance(v, bool):
                return None
            if isinstance(v, str) and v and set(v) <= {"0", "1"}:
                value = int(v, 2)
            elif type(v) is int:
                value = v
            else:
                return None
            if p.endswith("SIGNED"):
                if value not in (0, 1): return None
            elif value != len(con["Y"] if p == "WIDTH" else con.get(p[0], [])):
                return None
        return ins, ("Y",)

    def ok(name, stack=()):
        if name in memo:
            return memo[name]
        mod = (nl.get("modules") or {}).get(name)
        res = mod is not None and name not in stack
        if res:
            a = mod.get("attributes") or {}
            if any(k in a for k in ("blackbox", "whitebox", "lib_whitebox")) or mod.get("memories") or mod.get("processes"):
                res = False
            elif any(p.get("direction") not in ("input", "output") for p in (mod.get("ports") or {}).values()):
                res = False
            else:
                drivers, deps, outputs = {}, {}, []
                def bit(b): return type(b) is int or b in ("0", "1")
                def drive(b, origin):
                    if type(b) is not int: return False
                    drivers.setdefault(b, []).append(origin)
                    return True
                for pn, port in (mod.get("ports") or {}).items():
                    bs = port.get("bits") or []
                    if not bs or not all(bit(b) for b in bs): res = False; break
                    if port["direction"] == "input":
                        for i, b in enumerate(bs):
                            if not drive(b, ("input", pn, i)): res = False
                    else: outputs.extend(bs)
                for cn, c in (mod.get("cells") or {}).items():
                    t = c.get("type", "")
                    if t.startswith("$"):
                        io = primitive(c)
                    else:
                        sub = (nl.get("modules") or {}).get(t)
                        io = None
                        if sub is not None and ok(t, stack + (name,)) and ports(c, sub) and parameters(c, sub.get("parameter_default_values") or {}):
                            ps = sub.get("ports") or {}
                            io = (tuple(p for p in ps if ps[p]["direction"] == "input"),
                                  tuple(p for p in ps if ps[p]["direction"] == "output"))
                    if io is None:
                        res = False
                        break
                    ins, outs = io
                    con = c["connections"]
                    deps[cn] = tuple(b for p in ins for b in con[p])
                    if not all(bit(b) for b in deps[cn]): res = False; break
                    for pn in outs:
                        for b in con[pn]:
                            if not drive(b, ("cell", cn)): res = False
                seen, active = {}, set()
                def defined(b):
                    if b in ("0", "1"): return True
                    if b in seen: return seen[b]
                    ds = drivers.get(b, [])
                    if b in active or len(ds) != 1: return False
                    if ds[0][0] == "input": return True
                    active.add(b)
                    value = all(defined(x) for x in deps[ds[0][1]])
                    active.remove(b); seen[b] = value
                    return value
                if res:
                    res = bool(outputs) and all(defined(b) for b in outputs + list(drivers))
        memo[name] = res
        return res
    return ok


def leaf_canon(nl, cells, drv):
    """bit -> canonical identity: the bit itself, or (leaf type, params, output port/index, canonical inputs) when the
    bit is an output of a kept-hierarchy purely combinational leaf (see the module docstring)"""
    ok = comb_module_test(nl)
    memo = {}
    counts = {}
    for c in cells.values():
        for p, bs in (c.get("connections") or {}).items():
            if (c.get("port_directions") or {}).get(p) == "output":
                for b in bs: counts[b] = counts.get(b, 0) + 1

    def canon(b, depth=0):
        if not isinstance(b, int):
            return b
        key = (b, depth)
        if key in memo:
            return memo[key]
        r = b
        d = drv.get(b)
        if d is not None and depth < LEAF_DEPTH:
            cn, p, i = d
            c = cells[cn]
            t = c.get("type", "")
            mod = (nl.get("modules") or {}).get(t) or {}
            kept = (mod.get("attributes") or {}).get("keep_hierarchy")
            if isinstance(kept, str):
                kept = kept in {"yes", "true"} or bool(kept and set(kept) <= {"0", "1"} and int(kept, 2))
            ps = mod.get("ports") or {}
            con = c.get("connections") or {}
            expected = {pn: v.get("direction") for pn, v in ps.items()}
            params = c.get("parameters") or {}
            defaults = mod.get("parameter_default_values") or {}
            same_params = ({k: (type(v), v) for k, v in params.items()} ==
                           {k: (type(v), v) for k, v in defaults.items()})
            if (not t.startswith("$") and kept and counts.get(b) == 1 and ok(t)
                    and same_params and set(con) == set(ps) and c.get("port_directions") == expected
                    and all(len(con[pn]) == len(ps[pn].get("bits", [])) for pn in ps)
                    and p in ps and ps[p]["direction"] == "output"):
                dirs = c.get("port_directions") or {}
                ins = tuple((pn, tuple(canon(x, depth + 1) for x in pb))
                            for pn, pb in sorted((c.get("connections") or {}).items()) if dirs.get(pn) == "input")
                r = ("leaf", t, tuple(sorted((k, str(v)) for k, v in (c.get("parameters") or {}).items())), p, i, ins)
        memo[key] = r
        return r
    return canon


def bit_signature(cells, d, canon=None):
    """identity of the flop that drives one bit: type, params (minus WIDTH), and per-bit view of its input ports
    (input bits through canon(): leaf-equivalent nets compare equal)"""
    cn, p, i = d
    c = cells[cn]
    if not FLOP_RE.match(c["type"]) or p != "Q":
        return None
    cf = canon or (lambda x: x)
    w = len(c["connections"]["Q"])
    sig = [c["type"], tuple(sorted((k, str(v)) for k, v in (c.get("parameters") or {}).items() if k != "WIDTH"))]
    for pn in sorted(c["connections"]):
        if pn == "Q":
            continue
        pb = c["connections"][pn]
        sig.append((pn, cf(pb[i]) if len(pb) == w and w > 1 else tuple(cf(x) for x in pb)))
    return tuple(sig)


def split_family(wn, bits, cells, drv, loads, max_loads, m, canon=None):
    rec = {"family": wn, "copies": len(bits), "status": "", "groups": [], "total": 0, "fixed": 0, "moves": 0, "cmds": [],
           "leaf_equiv": False}
    sigs, raw = [], []
    for b in bits:
        d = drv.get(b)
        if d is None:
            rec["status"] = f"REFUSED bit {b} undriven"
            return rec
        s = bit_signature(cells, d, canon)
        if s is None:
            rec["status"] = f"REFUSED bit {b} not a flop Q ({cells[d[0]]['type']}.{d[1]})"
            return rec
        sigs.append(s)
        raw.append(bit_signature(cells, d))
    rec["leaf_equiv"] = any(s != raw[0] for s in raw[1:])
    if any(s != sigs[0] for s in sigs[1:]):
        rec["status"] = "REFUSED copies are not identical registers (D / clock / reset / type differ)"
        return rec
    idx = {b: k for k, b in enumerate(bits)}
    bset = set(bits)
    movable, fixed = [], [0] * len(bits)
    pool = set()
    for b in bits:
        pool |= loads.get(b, set())
    for cn, pn in sorted(pool, key=lambda x: (natural(x[0]), x[1])):
        c = cells[cn]
        pb = c["connections"][pn]
        fb = [x for x in pb if x in bset]
        if all(isinstance(x, int) and x in bset for x in pb) and SAFE_NAME.match(cn) and SAFE_NAME.match(pn):
            wgt = flop_width(c) if (FLOP_RE.match(c["type"]) and len(pb) == 1) else len(pb)
            movable.append((cn, pn, len(pb), wgt, pb))
        else:
            for x in fb:
                fixed[idx[x]] += 1
    total = sum(x[3] for x in movable) + sum(fixed)
    rec["total"], rec["fixed"] = total, sum(fixed)
    n = len(bits)
    tgt = max(1, math.ceil(total / n))
    groups = [[] for _ in range(n)]
    gw = list(fixed)
    g = 0
    for it in movable:
        while g < n - 1 and gw[g] > 0 and gw[g] + it[3] > tgt:
            g += 1
        groups[g].append(it)
        gw[g] += it[3]
    rec["groups"] = gw
    # a name for every copy bit (the -set source): a netname without brackets / unsafe characters
    bitname = {}
    for nn, v in sorted((m.get("netnames") or {}).items(), key=lambda x: (x[0].startswith("$"), natural(x[0]))):
        if not SAFE_NAME.match(nn) or "[" in nn or "]" in nn:
            continue
        nb = v.get("bits") or []
        for k, x in enumerate(nb):
            if x in bset and x not in bitname:
                bitname[x] = f"{yname(nn)}[{k}]" if len(nb) > 1 else yname(nn)
    missing = [b for b in bits if b not in bitname]
    if missing:
        rec["status"] = f"REFUSED no addressable name for copy bits {missing[:4]}"
        rec["groups"] = []
        return rec
    tag = re.sub(r"[^A-Za-z0-9_]", "_", wn)[-60:]
    cmds = []
    for k, b in enumerate(bits):
        w = f"\\ot_rrs__{tag}__c{k}"
        cmds.append(f"add -wire {w} 1")
        cmds.append(f"connect -set {w} {bitname[b]}")
        repeated = {}
        for cn, pn, L, _, pb in groups[k]:
            if all(x == b for x in pb):
                continue
            # Yosys script arguments do not consume a spaced RTLIL concat as
            # one port expression. Materialize a named vector of alias bits;
            # every connect expression stays a single token. Wires add no
            # state or logic and preserve the chosen copy on every port bit.
            expr = w
            if L > 1:
                if L not in repeated:
                    repeated[L] = f"{w}__v{L}"
                    cmds.append(f"add -wire {repeated[L]} {L}")
                    for bi in range(L):
                        cmds.append(f"connect -set {repeated[L]}[{bi}] {w}")
                expr = repeated[L]
            cmds.append(f"connect -port {yname(cn)} {pn} {expr}")
            rec["moves"] += 1
    rec["cmds"] = cmds
    over = [x for x in gw if x > max_loads]
    rec["status"] = (f"OVER max {max_loads}: {len(over)} copies over (largest {max(over)}): give the relay more copies "
                     f"(REGIONS >= {math.ceil(total / max_loads)})") if over else "OK"
    return rec


COARSE_RE = re.compile(r"^\$(?!_)(?!mem)(?!(adff|adffe|dff|dffe|sdff|sdffe|sdffce|aldff|aldffe|dffsr|dffsre|dlatch|adlatch|dlatchsr)$)")


def prep(nl, rx, top=None, wide=False):
    """yosys commands that map every MULTI-BIT register reset (or otherwise loaded on a 1-bit port) by a copy family to
    per-bit flops, so the split can place single flops (a 64-bit $adff on one ARST bit is one indivisible load).
    Patterns: the cell names with glob characters replaced by '?' (a wider match only maps more flops per bit:
    function unchanged)."""
    tname, m = top_module(nl, top)
    cells = m.get("cells") or {}
    rxc = re.compile(rx)
    fam = set()
    for wn, nn in (m.get("netnames") or {}).items():
        bits = nn.get("bits") or []
        if len(bits) >= 2 and all(isinstance(b, int) for b in bits) and (
                rxc.search(wn) or "ot_rst_split" in (nn.get("attributes") or {})):
            fam |= set(bits)
    pats = []
    for cn, c in sorted(cells.items(), key=lambda x: natural(x[0])):
        if not FLOP_RE.match(c["type"]) or c["type"].startswith("$_") or flop_width(c) < 2:
            continue
        if any(len(pb) == 1 and pb[0] in fam for pn, pb in (c.get("connections") or {}).items()
               if (c.get("port_directions") or {}).get(pn) == "input"):
            if not SAFE_NAME.match(cn):
                continue
            pats.append(re.sub(r"[\[\]*?\\]", "?", cn))
    fwires, mems = [], set()
    if wide:
        for wn, nn in sorted((m.get("netnames") or {}).items(), key=lambda x: natural(x[0])):
            bits = nn.get("bits") or []
            if (len(bits) >= 2 and all(isinstance(b, int) for b in bits) and set(bits) <= fam and SAFE_NAME.match(wn)
                    and "[" not in wn and "]" not in wn):
                fwires.append(wn)
        for cn, c in cells.items():
            if not c["type"].startswith("$mem"):
                continue
            dirs = c.get("port_directions") or {}
            if any(dirs.get(pn) == "input" and any(isinstance(b, int) and b in fam for b in pb)
                   for pn, pb in (c.get("connections") or {}).items()):
                mems.add(str((c.get("parameters") or {}).get("MEMID", cn)))
    lines = [f"cd {yname(tname)}"]
    if pats:
        lines.append("select -set ot_rc_tm " + " ".join(pats))
        lines.append("techmap @ot_rc_tm")
        lines.append("select -clear")
    if mems:
        lines.append("memory_collect")
        lines.append("memory_map")      # flop arrays only (the flow maps every remaining memory to flops the same way)
    if fwires:
        # every coarse (non-register, non-memory) cell that reads a family wire -> gate-level cells (one load per gate)
        sel = " ".join(f"w:{w}" for w in fwires) + " %u" * (len(fwires) - 1)
        lines.append(f"select -set ot_rc_wm {sel} %co1 t:$* %i t:$_* %d t:$*dff* %d t:$*dlatch* %d t:$mem* %d")
        lines.append("techmap @ot_rc_wm")
        lines.append("select -clear")
    lines.append("cd ..")
    return len(pats) + len(fwires) + len(mems), "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--max", type=int, default=256)
    ap.add_argument("--re", default=DEFAULT_RE)
    ap.add_argument("--top")
    ap.add_argument("--ys", required=True)
    ap.add_argument("--tsv")
    ap.add_argument("--prep", action="store_true", help="only write the per-bit techmap script (--ys)")
    ap.add_argument("--wide", action="store_true", help="prep also maps family-read memories / coarse cells (opt-in)")
    a = ap.parse_args(argv)
    try:
        nl = json.load(open(a.json))
    except (OSError, ValueError) as ex:
        print(f"OT_RST_COPIES ERROR {ex}")
        return 2
    if a.prep:
        n, ys = prep(nl, a.re, a.top, wide=a.wide)
        open(a.ys, "w").write(ys)
        print(f"OT_RST_COPIES: {n} multi-bit registers on relay copies mapped to per-bit flops")
        return 0
    tname, recs = analyse(nl, a.max, a.re, a.top)
    lines = [f"cd {yname(tname)}"]
    tsv = ["family\tcopies\ttotal_loads\tfixed\tmoves\tgroup_loads\tstatus"]
    for r in recs:
        lines += r["cmds"]
        tsv.append(f"{r['family']}\t{r['copies']}\t{r['total']}\t{r['fixed']}\t{r['moves']}\t"
                   f"{','.join(map(str, r['groups']))}\t{r['status']}")
        print(f"OT_RST_COPIES {r['family']}: {r['copies']} copies, {r['total']} loads -> "
              f"[{','.join(map(str, r['groups']))}] ({r['moves']} ports moved) {r['status']}"
              f"{' (controls proven through kept combinational leaves)' if r.get('leaf_equiv') else ''}")
    lines.append("cd ..")
    open(a.ys, "w").write("\n".join(lines) + "\n")
    open(a.tsv, "w").write("\n".join(tsv) + "\n")
    print(f"OT_RST_COPIES {len(recs)} relay copy families (max {a.max} loads a copy); table {a.tsv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
