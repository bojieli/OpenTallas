#!/usr/bin/env python3
"""FSTART reset leaves as a PLAN DELTA for any die (QC cb / glue 11-16, class "raw reset -> FSTART face flop").

Class: the count-aligned landing emitter gives every FSTART face flop u_cland_fstart_<bus> (and the count origin) of a
type one shared raw reset, cland_start_raw = the first landed input's ring reset relay.  On a tall type that one flop is
1.5 - 2 mm from the far faces: QC glue 32 face flops -492 ps (2,090 um, 27 buffers, no logic), cbf_q01 -1,916, cbf_q01_s2
-3,020 (post-CTS, S4q6d).  Every other QC cb type already carries clock.landing_local_resets rows for these consumers;
these three never got them.  fstart_reset_leaves.py (HEAD hd_spn) makes the same leaves from a KIT; this tool makes
them from the PLAN and the bound type RTL of a strict bind of that plan, as a plan delta:

    python3 -I fstart_reset_delta.py SRC PLAN BIND_DIR OUT_PLAN REPORT.json --types T[,T...] [--span-um 200] [--reach-um 405]

Per type: every landing instance whose reset pin is the shared START raw reset (FSTART face flops; the count origin when
it has a cland_tstart_in pin) is grouped along its face (consumers within --span-um share one leaf, <= 48 loads), and
each group gets one clock.landing_local_resets row: a kept ot_dp_rrelay at the group centre whose D is the bound
rst_rl_<k> relay of the SAME depth as the shared relay's D that is nearest to it (not a relay that drives an rst_o
port).  Depth(raw) + 1 == depth(old reset) is what clock_landings._local_resets checks again at the bind, so every
release edge is unchanged: 0 added cycles, +1 flop per group.  Both hops (relay -> leaf, leaf -> consumer) must be
<= --reach-um, else the tool fails closed (the type then needs reset.local_taps_um first: reach_fix class 5).
clock.reset_tree_anchor is re-recorded on the bound tree (reset_anchor.record), so a later renumbering re-picks by site.
Types that already have a local reset on a consumer keep it; every other type is byte-as-PLAN.
"""
import argparse
import json
import re
import sys
from pathlib import Path

INST = re.compile(r"\b(ot_dp_landing_\w+)\s+(?:#\([^;]*?\)\s*)?(u_cland_\w+)\s*\(([^;]*?)\);", re.S)
FANOUT_MAX = 48
EDGE_IN_UM = 2.16


class DeltaError(ValueError):
    pass


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def resolve(text, net):
    seen = set()
    while True:
        a = re.search(r"\bassign\s+" + re.escape(net) + r"\s*=\s*(\w+)\s*;", text)
        if not a:
            return net
        if net in seen:
            raise DeltaError(f"alias loop at {net}")
        seen.add(net)
        net = a.group(1)


def bound_rtl(bind_dir, tn, t):
    mod = t.get("module") or tn
    for name in (tn, f"{mod}__{tn}", mod):
        p = Path(bind_dir) / "rtl" / f"{name}.sv"
        if p.is_file():
            return p
    raise DeltaError(f"{tn}: no bound RTL in {bind_dir}/rtl")


def old_depth(sv, relays, net):
    """depth of reset net `net` in the bound body: an annotated wavefront relay, or a plain relay of one (+1)."""
    if net in relays:
        return relays[net]["depth"]
    m = re.search(r"\bot_dp_rrelay\s+\w+\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\(" + re.escape(net) + r"\)\);", sv)
    if not m or m.group(1) not in relays:
        raise DeltaError(f"shared START reset {net}: not a relay of a depth-annotated wavefront relay")
    return relays[m.group(1)]["depth"] + 1


def groups(cons, span):
    """consumers [(inst, (x, y))] -> face groups: sorted along the face, one group per <= span um and <= 48 loads"""
    out = []
    for face in sorted({c[2] for c in cons}):
        row = sorted((c for c in cons if c[2] == face), key=lambda c: (c[1][0] if face in "SN" else c[1][1], c[0]))
        cur = []
        for c in row:
            if cur and (man(cur[0][1], c[1]) > span or len(cur) >= FANOUT_MAX):
                out.append(cur)
                cur = []
            cur.append(c)
        if cur:
            out.append(cur)
    return out


def face_of(xy, w, h):
    d = {"W": xy[0], "E": w - xy[0], "S": xy[1], "N": h - xy[1]}
    return min(sorted(d), key=lambda k: d[k])


def type_delta(tn, t, sv, A, src, span=200.0, reach=405.0, prefix="fstart"):
    bt = A.bound_tree(sv)
    if not bt:
        raise DeltaError(f"{tn}: the bound RTL has no depth-annotated reset relays")
    relays = {r["q"]: r for r in bt["relays"]}
    ported = set(re.findall(r"\bassign\s+rst_o_\w+\s*=\s*(\w+)\s*;", sv))
    ck = t["clock"]
    pins = {p["name"]: p["xy_um"] for p in ck["landing_contract"]["pins"]}
    w, h = t["outline_um"]
    a = re.search(r"\bassign\s+cland_start_raw\s*=\s*(\w+)\s*;", sv)
    if not a:
        raise DeltaError(f"{tn}: no cland_start_raw in the bound RTL")
    shared = resolve(sv, "cland_start_raw")
    depth = old_depth(sv, relays, shared) - 1
    have = {c for r in ck.get("landing_local_resets") or [] for c in r["consumers"]}
    cons = []
    for m in INST.finditer(sv):
        inst = m.group(2)
        rp = re.findall(r"\.(?:rst_n|rst_raw_n)\(\s*(\w+)\s*\)", m.group(3))
        if len(rp) != 1 or resolve(sv, rp[0]) != shared or inst in have:
            continue
        if inst.startswith("u_cland_fstart_"):
            pin = "cland_fstart_out_" + inst[len("u_cland_fstart_"):]
        elif inst == "u_cland_origin":
            pin = "cland_tstart_in"
        else:
            continue
        if pin not in pins:
            raise DeltaError(f"{tn}: {inst} has no landing pin {pin}")
        xy = tuple(pins[pin])
        cons.append((inst, xy, face_of(xy, w, h)))
    if not cons:
        return [], []
    same = {q: r for q, r in relays.items() if r["depth"] == depth and re.fullmatch(r"rst_rl_\d+", q) and q not in ported}
    if not same:
        raise DeltaError(f"{tn}: no depth-{depth} wavefront relay for the START reset leaves")
    used = {r["name"] for r in ck.get("landing_local_resets") or []}
    rows, rep = [], []
    for g in groups(cons, span):
        cx = sum(c[1][0] for c in g) / len(g)
        cy = sum(c[1][1] for c in g) / len(g)
        x = round(min(max(cx, EDGE_IN_UM), w - EDGE_IN_UM), 3)
        y = round(min(max(cy, EDGE_IN_UM), h - EDGE_IN_UM), 3)
        raw = min(sorted(same), key=lambda q: man(same[q]["xy"], (x, y)))
        hop_in = man(same[raw]["xy"], (x, y))
        hop_out = max(man((x, y), c[1]) for c in g)
        if hop_in > reach + 1e-6 or hop_out > reach + 1e-6:
            raise DeltaError(f"{tn}: leaf at ({x}, {y}): nearest depth-{depth} relay {raw} {hop_in:.1f} um, consumers "
                             f"{hop_out:.1f} um > {reach} (add reset.local_taps_um there: reach_fix class 5)")
        k = 0
        while f"{prefix}_{k}" in used:
            k += 1
        name = f"{prefix}_{k}"
        used.add(name)
        rows.append(dict(name=name, raw=raw, xy_um=[x, y], consumers=[c[0] for c in g]))
        rep.append(dict(name=name, raw=raw, raw_xy=same[raw]["xy"], depth=depth + 1, xy_um=[x, y], consumers=len(g),
                        hop_in_um=round(hop_in, 1), hop_out_um=round(hop_out, 1), was=shared))
    ck.setdefault("landing_local_resets", []).extend(rows)
    ck.pop(A.KEY, None)
    ck[A.KEY] = A.record(t, bt, src, reach)
    return rows, rep


def dumper(rb, raw):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, indent=1), lambda p: json.dumps(p, indent=2),
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(raw).encode() == rb:
            return f
    raise DeltaError("plan JSON style not recognised (the delta must leave every other byte unchanged)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("plan"); ap.add_argument("bind_dir"); ap.add_argument("out_plan")
    ap.add_argument("report")
    ap.add_argument("--types", required=True)
    ap.add_argument("--span-um", type=float, default=200.0)
    ap.add_argument("--reach-um", type=float, default=405.0)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.src.rstrip("/") + "/tools/die_plan")
    import reset_anchor as A
    rb = Path(a.plan).read_bytes()
    raw = json.loads(rb)
    dump = dumper(rb, raw)
    rep = {}
    for tn in a.types.split(","):
        t = raw["partition_types"][tn]
        sv = bound_rtl(a.bind_dir, tn, t).read_text()
        rows, r = type_delta(tn, t, sv, A, a.src, a.span_um, a.reach_um)
        rep[tn] = dict(rows=rows, detail=r, flops=len(rows),
                       hop_in_max_um=max([x["hop_in_um"] for x in r], default=0.0),
                       hop_out_max_um=max([x["hop_out_um"] for x in r], default=0.0))
        print(f"{tn}: {len(rows)} leaves for {sum(x['consumers'] for x in r)} consumers, hops in <= "
              f"{rep[tn]['hop_in_max_um']} out <= {rep[tn]['hop_out_max_um']} um")
    Path(a.out_plan).write_text(dump(raw))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
