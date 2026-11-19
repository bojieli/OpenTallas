#!/usr/bin/env python3
"""CBC-RULES-1119 (COORD r713 rule 4, die-agnostic): boundary-register-bank reset relays as a PLAN DELTA.

Class: every boundary / station register bank of a type (ot_dp_st / ot_dp_ste: u_bin_*, u_bout_*, u_ft_*, u_ist_*) takes its
epoch reset from ONE net rst_n.  On a wide type that net spans millimetres:
  * a native HARD wrapper takes the delivered reset (bind: `wire rst_n = arst_n;`): S81 phy__t1, 17 banks over 8.66 mm
    from the reset tap at the N-face centre, recovery TT -2468 ps (S81-TAIL-1118 row);
  * a soft type with a generated reset tree hangs every bank on the leaf tap (`wire rst_n = rst_n_t<k>;`): S81 serdes__t12,
    17 banks (8,206 bits) over 2.9 mm on rst_n_t11, while the tree already has 47 equal-depth taps.
fstart_reset_delta.py only localises FSTART landing flops (u_cland_*); this tool covers the banks, from the plan and the
bound RTL of a bind of that plan:

  python3 -I bank_reset_delta.py PLAN BIND_RTL_DIR OUT_PLAN REPORT.json --types T[,T...] [--reach-um 405] [--leaf-max 32]
                                 [--positions POS.json]

Soft type (generated tree): each bank goes to the NEAREST tree tap rst_n_t<i> with room (<= --leaf-max bank reset pins per
tap) -> plan partition_types[T].reset.bank_taps [{"tap": i, "sinks": [...]}].  reset_tree pads every tap to the same depth K,
so 0 added cycles, 0 flops (bind: reset_port_relays.apply_bank_taps).
Hard type (delivered reset): banks are grouped along the type (one group <= --leaf-max reset pins, span <= --reach-um), each
group gets ONE chain of D synchronous relays (reset.port_relays, u_prl_<g>_<j>) from the reset tap (reset.tap_um) to the group
centroid, D = max over groups of ceil(L / reach) so every group releases on the same edge; relay sites go to relay_sites
(u_prl_<g>_<j>.q, FIRM, evenly along the x-then-y path).  The hard type's reset.depth (wavefront: clocks from its arst_n pin
to release, default 1) rises by D, so the die wavefront schedules the later release; boot holds rst_n >= 64 clk, so the
+D cycles of reset release are legal (owner 10-29).  No data cycle changes.
Bank positions: plan estimate (bus: face-window centre; ft station k of n: regs_um[k] when the plan has n sites, else
k+1 / n+1 along in -> out; internal station u_ist_<bus>_<k>: regs_um[k]); --positions {type: {inst: [x, y]}} overrides
(e.g. from a placed kit).  A bank with no position stays on rst_n and is listed (unplaced).
A type with no bank on rst_n is byte-as-PLAN.  Every other key of the plan stays byte-identical.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_consumers as RC  # noqa: E402
import reset_port_relays as PR  # noqa: E402

REACH_UM = 405.0
LEAF_MAX = 32
HARD_DEPTH = 1          # reset_tree.HARD_DEPTH: a hard partition without reset.depth = its pin register only


class DeltaError(ValueError):
    pass


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def face_point(face, window, w, h):
    c = (float(window[0]) + float(window[1])) / 2.0
    return {"N": (c, h), "S": (c, 0.0), "E": (w, c), "W": (0.0, c)}[face]


def lerp_l(a, b, f):
    """point at fraction f along the x-then-y L path a -> b"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = abs(dx) + abs(dy)
    if L == 0:
        return (a[0], a[1])
    s = f * L
    if s <= abs(dx):
        return (a[0] + math.copysign(s, dx), a[1])
    return (b[0], a[1] + math.copysign(s - abs(dx), dy))


def bank_xy(t, inst):
    """plan estimate of a bank's reset pin site (type frame), None when unknown"""
    w, h = t["outline_um"]
    buses = {b["name"]: b for b in t.get("buses") or []}
    m = re.fullmatch(r"u_b(?:in|out)_(\w+)", inst)
    if m and m.group(1) in buses:
        b = buses[m.group(1)]
        if not (b.get("face") and b.get("window_um")):
            return None                            # a bus sited per port (no type face window): position unknown here
        return face_point(b["face"], b["window_um"], w, h)
    m = re.fullmatch(r"u_ft_(\w+?)_o_(\d+)", inst)
    if m:
        s = next((x for x in t.get("ft_slots") or [] if x.get("name") == m.group(1)), None)
        if s:
            k, n = int(m.group(2)), max(1, int(s.get("stations", 1) or 1))
            regs = s.get("regs_um") or []
            if len(regs) == n:
                return tuple(regs[k])
            if not (s.get("in_window_um") and s.get("out_window_um")):
                return None
            a = face_point(s["in_face"], s["in_window_um"], w, h)
            b = face_point(s["out_face"], s["out_window_um"], w, h)
            return lerp_l(a, b, (k + 1) / (n + 1))
    m = re.fullmatch(r"u_ist_(\w+?)_(\d+)", inst)
    if m:
        k = int(m.group(2))
        for e in t.get("internal_stations") or []:
            if e.get("conn") == f"bus:{m.group(1)}" and len(e.get("regs_um") or []) > k:
                return tuple(e["regs_um"][k])
    return None


def banks_on_rst(sv):
    """[(inst, module)] of the banks whose rst_n pin is the type's rst_n net"""
    out = []
    for inst, c in RC._calls(sv).items():
        if c["module"] in PR.BANKS and c["ports"].get("rst_n", (None,))[0] == "rst_n":
            out.append((inst, c["module"]))
    return out


def tree_taps(sv):
    """{tap index: (x, y)} from the generated tree's tap relays (`... .q(rst_n_t<i>));  // ... @ (x, y)`)"""
    taps = {}
    for m in re.finditer(r"\.q\(rst_n_t(\d+)\)\);[^\n]*@ \(([-\d.]+), ([-\d.]+)\)", sv):
        taps[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return taps


def soft_rows(tn, t, sv, pos, reach, leaf_max):
    leaf = PR.LEAF.findall(sv)
    taps = tree_taps(sv)
    if len(leaf) != 1 or not taps:
        raise DeltaError(f"{tn}: no generated reset-tree leaf alias / tap sites in the bound RTL")
    load, by_tap, rep, unplaced = {}, {}, [], []
    for inst, _mod in sorted(banks_on_rst(sv)):
        xy = pos.get(inst) or bank_xy(t, inst)
        if xy is None:
            unplaced.append(inst)
            continue
        order = sorted(taps, key=lambda i: (man(taps[i], xy), i))
        i = next((i for i in order if load.get(i, 0) < leaf_max), None)
        if i is None or man(taps[i], xy) > reach + 1e-6:
            raise DeltaError(f"{tn}: bank {inst} at {tuple(round(v, 1) for v in xy)}: no tree tap with room within {reach} um "
                             f"(nearest {min(man(p, xy) for p in taps.values()):.0f} um): needs reset.local_taps_um")
        load[i] = load.get(i, 0) + 1
        by_tap.setdefault(i, []).append(inst)
        rep.append(dict(inst=inst, xy=[round(v, 1) for v in xy], tap=i, hop_um=round(man(taps[i], xy), 1),
                        was_hop_um=round(man(taps[int(leaf[0])], xy), 1) if int(leaf[0]) in taps else None))
    rows = [dict(tap=i, sinks=by_tap[i]) for i in sorted(by_tap)]
    return rows, rep, unplaced


def hard_groups(cons, reach, leaf_max):
    """cons [(inst, (x, y))] -> groups sorted along the longer axis: span <= reach and <= leaf_max reset pins each"""
    out, cur = [], []
    xs = [c[1][0] for c in cons]
    ys = [c[1][1] for c in cons]
    ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
    for c in sorted(cons, key=lambda c: (c[1][ax], c[1][1 - ax], c[0])):
        if cur and (max(man(c[1], d[1]) for d in cur) > reach or len(cur) >= leaf_max):
            out.append(cur)
            cur = []
        cur.append(c)
    if cur:
        out.append(cur)
    return out


def hard_rows(tn, t, sv, pos, reach, leaf_max, prefix="cbr"):
    if len(PR.DELIVERED.findall(sv)) != 1:
        raise DeltaError(f"{tn}: hard type without the delivered-reset alias `wire rst_n = arst_n;`")
    tap = (t.get("reset") or {}).get("tap_um")
    if not tap:
        raise DeltaError(f"{tn}: hard type without reset.tap_um (the arst_n pin site)")
    tap = (float(tap[0]), float(tap[1]))
    have = {s for r in (t.get("reset") or {}).get("port_relays") or [] for s in r["sinks"]}
    used = {r["name"] for r in (t.get("reset") or {}).get("port_relays") or []}
    cons, unplaced = [], []
    for inst, _mod in sorted(banks_on_rst(sv)):
        if inst in have:
            continue
        xy = pos.get(inst) or bank_xy(t, inst)
        if xy is None:
            unplaced.append(inst)
        else:
            cons.append((inst, tuple(xy)))
    if not cons:
        return [], {}, [], unplaced, 0
    gs = hard_groups(cons, reach, leaf_max)
    cents = [(sum(c[1][0] for c in g) / len(g), sum(c[1][1] for c in g) / len(g)) for g in gs]
    D = max(max(1, math.ceil(man(tap, c) / reach - 1e-9)) for c in cents)
    if D > PR.MAX_DEPTH:
        raise DeltaError(f"{tn}: reset chain depth {D} > {PR.MAX_DEPTH} (tap {tap} to a group {max(man(tap, c) for c in cents):.0f} um)")
    rows, sites, rep = [], {}, []
    k = 0
    for g, c in zip(gs, cents):
        while f"{prefix}{k}" in used:
            k += 1
        name = f"{prefix}{k}"
        used.add(name)
        k += 1
        rows.append(dict(name=name, depth=D, sinks=[x[0] for x in g]))
        for j in range(D):
            p = lerp_l(tap, c, (j + 1) / D)
            sites[f"u_prl_{name}_{j}.q"] = [round(p[0], 3), round(p[1], 3)]
        L = man(tap, c)
        rep.append(dict(name=name, depth=D, sinks=len(g), centroid=[round(c[0], 1), round(c[1], 1)], tap_um=round(L, 1),
                        hop_um=round(L / D, 1), leaf_span_um=round(max(man(c, x[1]) for x in g), 1),
                        was_hop_um=round(max(man(tap, x[1]) for x in g), 1)))
    return rows, sites, rep, unplaced, D


def type_delta(tn, t, sv, pos=None, reach=REACH_UM, leaf_max=LEAF_MAX):
    """mutates t; -> report dict (empty rows when nothing to do)"""
    pos = pos or {}
    if not banks_on_rst(sv):
        return dict(form="none", rows=[], added_reset_cycles=0, flops=0)
    rs = t.setdefault("reset", {})
    if t.get("hard") or PR.DELIVERED.search(sv):
        rows, sites, rep, unplaced, D = hard_rows(tn, t, sv, pos, reach, leaf_max)
        if rows:
            rs.setdefault("port_relays", []).extend(rows)
            t.setdefault("relay_sites", {}).update(sites)
            rs["depth"] = int(rs.get("depth", HARD_DEPTH)) + D
        return dict(form="port_relays", rows=rows, relay_sites=sites, detail=rep, unplaced=unplaced,
                    added_reset_cycles=D, flops=sum(r["depth"] for r in rows), reset_depth=rs.get("depth"))
    rows, rep, unplaced = soft_rows(tn, t, sv, pos, reach, leaf_max)
    if rows:
        rs["bank_taps"] = (rs.get("bank_taps") or []) + rows
    return dict(form="bank_taps", rows=rows, detail=rep, unplaced=unplaced, added_reset_cycles=0, flops=0,
                hop_max_um=max([r["hop_um"] for r in rep], default=0.0),
                was_hop_max_um=max([r["was_hop_um"] or 0 for r in rep], default=0.0))


def bound_rtl(rtl_dir, tn, t):
    d = Path(rtl_dir)
    mod = t.get("module") or tn
    for name in (tn, f"{mod}__{tn}", mod):
        p = d / f"{name}.sv"
        if p.is_file():
            return p
    hits = sorted(p for p in d.glob(f"*{tn}.sv") if re.fullmatch(r"[A-Za-z0-9]+_" + re.escape(tn), p.stem))
    if len(hits) == 1:
        return hits[0]
    raise DeltaError(f"{tn}: no bound RTL in {rtl_dir}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("rtl_dir"); ap.add_argument("out_plan"); ap.add_argument("report")
    ap.add_argument("--types", required=True)
    ap.add_argument("--reach-um", type=float, default=REACH_UM)
    ap.add_argument("--leaf-max", type=int, default=LEAF_MAX)
    ap.add_argument("--positions")
    a = ap.parse_args(argv)
    import fstart_reset_delta as F
    rb = Path(a.plan).read_bytes()
    raw = json.loads(rb)
    dump = F.dumper(rb, raw)
    allpos = json.loads(Path(a.positions).read_text()) if a.positions else {}
    rep = {}
    for tn in a.types.split(","):
        t = raw["partition_types"][tn]
        sv = bound_rtl(a.rtl_dir, tn, t).read_text()
        r = type_delta(tn, t, sv, allpos.get(tn), a.reach_um, a.leaf_max)
        rep[tn] = r
        print(f"{tn}: {r['form']} {len(r['rows'])} rows, +{r['added_reset_cycles']} reset cycles, {r['flops']} flops, "
              f"unplaced {len(r.get('unplaced') or [])}")
    Path(a.out_plan).write_text(dump(raw))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
