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

  python3 ot_rst_copies.py --json in.json --max 256 --ys out.ys --tsv out.tsv [--re REGEX] [--top NAME]
exit 0 always when the JSON parses (groups over --max are reported as OVER lines and in the table: the gate judges them);
exit 2 on unusable input.
"""
import argparse
import json
import math
import re
import sys

DEFAULT_RE = r"(^|\.)(u_rst_relay|u_fl_rst_[A-Za-z0-9_]+)\.rst_n$|__ot_rlv$"
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
        fams.append((wn, bits))
    out = []
    for wn, bits in fams:
        out.append(split_family(wn, bits, cells, drv, loads, max_loads, m))
    return tname, out


def bit_signature(cells, d):
    """identity of the flop that drives one bit: type, params (minus WIDTH), and per-bit view of its input ports"""
    cn, p, i = d
    c = cells[cn]
    if not FLOP_RE.match(c["type"]) or p != "Q":
        return None
    w = len(c["connections"]["Q"])
    sig = [c["type"], tuple(sorted((k, str(v)) for k, v in (c.get("parameters") or {}).items() if k != "WIDTH"))]
    for pn in sorted(c["connections"]):
        if pn == "Q":
            continue
        pb = c["connections"][pn]
        sig.append((pn, pb[i] if len(pb) == w and w > 1 else tuple(pb)))
    return tuple(sig)


def split_family(wn, bits, cells, drv, loads, max_loads, m):
    rec = {"family": wn, "copies": len(bits), "status": "", "groups": [], "total": 0, "fixed": 0, "moves": 0, "cmds": []}
    sigs = []
    for b in bits:
        d = drv.get(b)
        if d is None:
            rec["status"] = f"REFUSED bit {b} undriven"
            return rec
        s = bit_signature(cells, d)
        if s is None:
            rec["status"] = f"REFUSED bit {b} not a flop Q ({cells[d[0]]['type']}.{d[1]})"
            return rec
        sigs.append(s)
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
        for cn, pn, L, _, pb in groups[k]:
            if all(x == b for x in pb):
                continue
            expr = w if L == 1 else "{ " + " ".join([w] * L) + " }"
            cmds.append(f"connect -port {yname(cn)} {pn} {expr}")
            rec["moves"] += 1
    rec["cmds"] = cmds
    over = [x for x in gw if x > max_loads]
    rec["status"] = (f"OVER max {max_loads}: {len(over)} copies over (largest {max(over)}): give the relay more copies "
                     f"(REGIONS >= {math.ceil(total / max_loads)})") if over else "OK"
    return rec


def prep(nl, rx, top=None):
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
    lines = [f"cd {yname(tname)}"]
    if pats:
        lines.append("select -set ot_rc_tm " + " ".join(pats))
        lines.append("techmap @ot_rc_tm")
        lines.append("select -clear")
    lines.append("cd ..")
    return len(pats), "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--max", type=int, default=256)
    ap.add_argument("--re", default=DEFAULT_RE)
    ap.add_argument("--top")
    ap.add_argument("--ys", required=True)
    ap.add_argument("--tsv")
    ap.add_argument("--prep", action="store_true", help="only write the per-bit techmap script (--ys)")
    a = ap.parse_args(argv)
    try:
        nl = json.load(open(a.json))
    except (OSError, ValueError) as ex:
        print(f"OT_RST_COPIES ERROR {ex}")
        return 2
    if a.prep:
        n, ys = prep(nl, a.re, a.top)
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
              f"[{','.join(map(str, r['groups']))}] ({r['moves']} ports moved) {r['status']}")
    lines.append("cd ..")
    open(a.ys, "w").write("\n".join(lines) + "\n")
    open(a.tsv, "w").write("\n".join(tsv) + "\n")
    print(f"OT_RST_COPIES {len(recs)} relay copy families (max {a.max} loads a copy); table {a.tsv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
