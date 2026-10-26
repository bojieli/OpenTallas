"""Cut a two-partition proof plan out of a full die plan (CP1: abutment / planned-channel proof).

    python3 tools/die_plan/pair.py PLAN.json --parts A,B --out DIR [--channel UM] [--name NAME]

- The new die is the bounding box of partitions A and B, translated to (0, 0).
- --channel UM moves the partition with the larger coordinate along the shared axis by UM, which must be a multiple of
  die.grid_um. Every A<->B port is then routed across a planned die.channels entry; types, pins and kits are unchanged.
- Every other port of A or B becomes die IO on the same face window, so pins and pin tables are identical to the full
  plan. A port that runs from the far partition through the near one is still a single pair-die IO port, because both
  faces lie on the pair die edge.
- Partition contents are replaced by one generated proof leaf per type (`<module>_proof_leaf`, written to DIR/leaves.sv).
  It registers every functional in-bus and drives every functional out-bus from a registered XOR fold of the inputs.
  The leaf is a vehicle for the boundary, face and channel proof only. It is not the partition's real logic.
- Without --cores, hard cores (`hard_cores[]`) are dropped with the contents: the proof netlist does not instantiate them.
- Lanes are rebuilt by following ft slots. Latency is left for `gen.py latency`.
- CP2 (hard cores): --cores instantiates every hard_cores[] module in the proof leaf (black box: the kit gets its
  LEF / liberty through gen_phys.type_macros -> ADDITIONAL_LEFS / ADDITIONAL_LIBS), clock pins (liberty
  `clock : true`, else LEF USE CLOCK) on clk, every other core pin driven from / captured by its own stub flop; the
  plan's hard_cores[].inst becomes `u_leaf.<last name>` (the flattened kit instance place_macro finds).
  --core-views DIR fills hard_cores[].lef / .lib (TT) where lib is null (DIR from fetch_core_views.sh).
  --core-taps adds an EARLY clock tap (clock.taps kind core, insertion_ps = TT max_clock_tree_path) for every core
  clock pin whose internal latency > common latency - 40 ps, and sets clock.core_taps = 'early' (gen_phys: port
  clk_c<k>, source latency -(insertion - common) in the kit SDC and the die STA).
- Proof-leaf clock (CLOCK-RESET/CP1-COLH10 10-25): a proof-leaf type gets a clock tap plan derived from ITS OWN
  sinks (proof_clock): clock.tap_mode "density" over the face / ft registers plus the leaf's register inventory
  (leaf_sink_sites), <= PROOF_TAP_MAX_SINKS per tap within PROOF_TAP_RADIUS_UM, no grid, no sink-less tap.  The full
  type's 200-um tap grid was sized for the real contents; on a 0.3%-filled proof partition it left ~51 of 55 taps with
  0-7 sinks and piled the face bands onto 4 taps of 1.5-2.4k sinks (128-178 ps natural trees, 50 ps internal spread),
  which tap_balance could only pad at the roots (r1 post-route FF hold -30.85, r0 post-CTS FF -74.95).  The bound
  pin-register insertion (common latency, R4) is unchanged: the parent spine has no late-tap contract, so the kit
  still delivers it, now on uniform shallow trees.  --clock-only rewrites an existing coreless pair plan's clocks.
- The pair keeps the full die's spine geometry (clock.spine.die_root_um, die_outline_um, part_die_origin_um) for the
  die STA branch model (spine.py); clock.spine.root_um is the pair's own (routing) root.
"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART, OPP  # noqa: E402


def along_axis(face):
    return 1 if face in "EW" else 0     # E/W face: the along-face (window) coordinate is y


def _fold(dst, w, src, n):
    """`dst <= dst ^ fold(src)`: every one of the n src bits reaches some dst bit (K = ceil(n / w) slices of a
    replicated src), so no captured core output is optimised away."""
    if not n:
        return f"    always @(posedge clk) {dst} <= ~{dst};"
    k = max(1, -(-n // w))
    rep = -(-k * w // n)
    lines = [f"    wire [{rep * n - 1}:0] {dst}_x = {{{rep}{{{src}}}}};"]
    terms = " ^ ".join(f"{dst}_x[{i * w} +: {w}]" for i in range(k))
    lines.append(f"    always @(posedge clk) {dst} <= {dst} ^ {terms};")
    return "\n".join(lines)


def core_ports(core, root=None):
    """(inputs, outputs, clocks) of a hard core from its LEF (PIN / DIRECTION / USE) and liberty (clock : true):
    inputs / outputs [(pin, width or 0 for a scalar)], clocks [pin].  Raises when the views are missing."""
    import cores as C
    if not core.get("lef") or not C.resolve(core["lef"], root).is_file():
        raise SystemExit(f"--cores: core {core['inst']} ({core.get('module')}) has no LEF view "
                         f"({core.get('lef')}); pass --core-views")
    pins = C.lef_pins(C.resolve(core["lef"], root), core.get("module"))
    cks = set(C.clock_pins(core, root))
    if not cks:
        raise SystemExit(f"--cores: core {core['inst']}: no clock pin (lib clock : true / LEF USE CLOCK)")
    miss = cks - set(pins)
    if miss:
        raise SystemExit(f"--cores: core {core['inst']}: lib clock pins {sorted(miss)} not in the LEF")
    ins, outs = [], []
    for n, p in sorted(pins.items()):
        if p["use"] in ("POWER", "GROUND") or n in cks:
            continue
        if p["dir"] == "INPUT":
            ins.append((n, p["width"]))
        elif p["dir"] == "OUTPUT":
            outs.append((n, p["width"]))
        else:
            raise SystemExit(f"--cores: core {core['inst']} pin {n}: direction {p['dir']} not supported")
    return ins, outs, sorted(cks)


LEAF_HOP_UM = None   # set from reach.py at use: OWNER_LOCAL_PLAN_UM x MARGIN (405 x 0.9 = 364.5 um per reg-reg hop)


def leaf_hop_um():
    import reach as RCH
    return min(RCH.layer_reach(n) for n in RCH.PARTITION_LAYERS) * RCH.MARGIN


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reach_plan(ins, outs, geo, hop_um):
    """CP1-R10 (12:30): the reach-aware proof-leaf dataflow.  geo {bus: (x, y)} = the bus pin centroid (type frame).
    Every out bus takes its NEAREST in bus; every in bus feeds its NEAREST out bus (so no input is dead).  A pair at
    Manhattan distance d gets ceil(d / hop_um) register hops between the in face flop and the out face flop: the
    leaf's in-register q, its fold register f_s0, s = max(0, hops - 4) pipeline stages, the leaf's out-register (4 hops
    in face flop -> q -> f_s0 -> out reg -> out face flop without stages).
    -> {out: [(in, d_um, stages)]}"""
    srcs = {o: set() for o, _ in outs}
    if not ins:
        return {o: [] for o in srcs}
    for o, _ in outs:
        srcs[o].add(min((i for i, _ in ins), key=lambda i: (_man(geo[i], geo[o]), i)))
    for i, _ in ins:
        if outs:
            srcs[min((o for o, _ in outs), key=lambda o: (_man(geo[i], geo[o]), o))].add(i)
    out = {}
    for o in srcs:
        out[o] = []
        for i in sorted(srcs[o]):
            d = _man(geo[i], geo[o])
            hops = max(1, math.ceil(d / hop_um))
            out[o].append((i, round(d, 1), max(0, hops - 4)))
    return out


def _unique_fold(wi, w, k, used=None):
    """Fold an in bus of wi bits into w out bits: [sorted in-bit indices per out bit], every out bit a DISTINCT,
    non-constant XOR (no two out bits share a term set).
    Why (CLOCK-RESET/cp1 10-25): the old narrow-bus fold q[j % wi] ^ q[(j*7+k+1) % wi] repeats with period wi, so out
    bits j, j+wi, j+2wi, ... were identical functions; Yosys merged their leaf registers (r1 frame_int_o0: 1230 output
    pin registers fed by 384 leaf flops) and ONE leaf flop drove 3-4 face flops 166-254 um apart along the face ->
    post-route D-pin slew 400-436 ps (320 limit) that no ECO repaired.  Every output pin register must have its own
    source register (industry practice: no register sharing across ports)."""
    used = set() if used is None else used     # shared per in bus: out buses of one in bus stay distinct too
    if wi > w:      # wide in bus: disjoint residue classes (distinct within the bus); widen one on a cross-bus clash
        out = []
        for j in range(w):
            ms = set(range(j % wi, wi, w))
            p = (j * 7 + k + 1) % wi
            while frozenset(ms) in used and len(ms) < wi:
                if p not in ms:
                    ms.add(p)
                p = (p + 1) % wi
            used.add(frozenset(ms))
            out.append(sorted(ms))
        return out
    if wi == 1:     # one in bit: only q and ~q exist; distinctness impossible (caller's plan should not do this)
        return [[0] for _ in range(w)]
    out = []
    npairs = wi * (wi - 1) // 2
    for j in range(w):
        a = j % wi
        if len(used) >= npairs:     # pairs exhausted (tiny in bus): triples, still distinct up to C(wi, 3)
            b = (a + 1 + j // wi) % wi
            c = (b + 1 + (j * 7 + k) % max(1, wi - 2)) % wi
            ms = tuple(sorted({a, b, c}))
            out.append(list(ms))
            continue
        p = (j * 7 + k + 1 + 13 * (j // wi)) % wi
        for _ in range(wi):
            if p != a and frozenset((a, p)) not in used:
                break
            p = (p + 1) % wi
        else:       # every partner of a used: take the first free pair anywhere
            a, p = next((x, y) for x in range(wi) for y in range(x + 1, wi) if frozenset((x, y)) not in used)
        used.add(frozenset((a, p)))
        out.append(sorted((a, p)))
    return out


def proof_leaf(module, ins, outs, cores=(), geo=None, hop_um=None):
    """ins/outs: [(bus, width)].  geo {bus: (x, y)} (type frame pin centroids): the reach-aware leaf (reach_plan):
    every out bus is a registered XOR fold of its nearest in bus(es), each pipelined by its own stage count, so no
    leaf path is longer than a reach hop (CP1 reach405 r1, 12:2x: the all-bus XOR fold below made ~1-1.4 mm
    unpipelined face -> leaf paths, TT -241.76 ps, 1234 slew violations, none of them on the seam).  geo None: the
    legacy leaf: every out bit = XOR of a rotated fold of all input bits.
    cores: [(leaf inst, core module, core ins, core outs, clock pins)] (CP2, --cores): each hard core is instantiated
    as a black box (its liberty view in the kit), every clock pin on clk, every input pin driven by its own stub flop
    and every output pin captured by its own stub flop (reg-to-core / core-to-reg paths; the core is a real clock
    sink).  Stub flops are local: core outputs -> capture flops -> XOR fold -> the same core's input flops."""
    name = f"{module}_proof_leaf"
    decl = ["input wire clk"] + [f"input wire [{w - 1}:0] {b}" for b, w in ins] + \
        [f"output reg [{w - 1}:0] {b}" for b, w in outs]
    body = []
    tot = sum(w for _, w in ins)
    if tot:
        body.append(f"    wire [{tot - 1}:0] cat = {{{', '.join(b for b, _ in ins)}}};")
        body.append(f"    reg [{tot - 1}:0] q;")
        body.append("    always @(posedge clk) q <= cat;")
    if geo is not None and tot:
        wid = dict(ins)
        offs, o_ = {}, 0
        for b, w in reversed(ins):          # cat = {ins[0], ..., ins[-1]}: the last bus is the LSBs
            offs[b] = o_
            o_ += w
        plan = reach_plan(ins, outs, geo, hop_um or leaf_hop_um())
        folds = {}
        for k, (b, w) in enumerate(outs):
            terms = []
            for i, d, st in plan[b]:
                wi, base = wid[i], offs[i]
                # fold in bus i into w bits: bit j = XOR of q_i[m] for m = j, j + w, ... (+ a rotated partner when the
                # in bus is narrower), all from ONE in bus (one face window)
                bits = _unique_fold(wi, w, k, folds.setdefault(i, set()))
                bits = [" ^ ".join(f"q[{base + m}]" for m in ms) for ms in bits]
                f = f"f_{b}_{i}"
                body.append(f"    // {b} <- {i}: {d:g} um, {st} pipeline stage(s) (hop <= {hop_um or leaf_hop_um():g} um)")
                body.append(f"    reg [{w - 1}:0] {f}_s0;")
                body.append(f"    always @(posedge clk) {f}_s0 <= {{{', '.join(reversed(bits))}}};")
                for sidx in range(1, st + 1):
                    body.append(f"    reg [{w - 1}:0] {f}_s{sidx};")
                    body.append(f"    always @(posedge clk) {f}_s{sidx} <= {f}_s{sidx - 1};")
                terms.append(f"{f}_s{st}")
            if terms:
                body.append(f"    always @(posedge clk) {b} <= {' ^ '.join(terms)};")
            else:
                body.append(f"    always @(posedge clk) {b} <= ~{b};")
        outs_done = True
    else:
        outs_done = False
    for k, (b, w) in enumerate(outs if not outs_done else []):
        if not tot:
            body.append(f"    always @(posedge clk) {b} <= ~{b};")
            continue
        # fold q into w bits: bit i = q[i % tot] ^ q[(i + k + 1) * 7 % tot]
        terms = ", ".join(f"q[{(i % tot)}] ^ q[{((i + k + 1) * 7) % tot}]" for i in reversed(range(w)))
        body.append(f"    always @(posedge clk) {b} <= {{{terms}}};")
    for inst, cmod, cin, cout, cks in cores:
        ni = sum(max(1, w) for _, w in cin)
        no = sum(max(1, w) for _, w in cout)
        body.append(f"    // hard core {inst} ({cmod}): {ni} input / {no} output pin flops, clocks {' '.join(cks)}")
        if ni:
            body.append(f"    reg [{ni - 1}:0] {inst}_ci;")
        if no:
            body.append(f"    wire [{no - 1}:0] {inst}_cw;")
            body.append(f"    reg [{no - 1}:0] {inst}_co;")
            body.append(f"    always @(posedge clk) {inst}_co <= {inst}_cw;")
        conn = [f".{c}(clk)" for c in cks]
        o = 0
        for n, w in cin:
            conn.append(f".{n}({inst}_ci[{o + max(1, w) - 1}:{o}])" if w else f".{n}({inst}_ci[{o}])")
            o += max(1, w)
        o = 0
        for n, w in cout:
            conn.append(f".{n}({inst}_cw[{o + max(1, w) - 1}:{o}])" if w else f".{n}({inst}_cw[{o}])")
            o += max(1, w)
        # keep: the stub loop (core -> capture flops -> fold -> input flops -> core) reaches no leaf output, so without
        # it Yosys sweeps the core and every stub flop (CP2 probe 10-23: no core left after opt)
        body.append(f"    (* keep *) {cmod} {inst} (\n        " + ",\n        ".join(conn) + "\n    );")
        if ni:
            body.append(_fold(f"{inst}_ci", ni, f"{inst}_co", no))
        elif no:
            # no inputs to fold into: the captured outputs drive a parity flop each cycle (kept, observable)
            body.append(f"    (* keep *) reg {inst}_par;")
            body.append(f"    always @(posedge clk) {inst}_par <= ^{inst}_co;")
    return f"module {name} (\n    " + ",\n    ".join(decl) + "\n);\n" + "\n".join(body) + "\nendmodule\n", name


CORE_TAP_MARGIN_PS = 40.0   # a core clock pin hung straight off a tap port still sees ~a buffer + wire (>= ~20-40 ps)


def core_tap_xy(t, core, pin, taken, root=None):
    """type-frame site of an early core tap: the core's clock pin (LEF rect centre, core frame, R0/MX/MY/R180 in the
    core outline) moved off every hard core into a channel (schema.tap_clear)."""
    import cores as C
    p = C.lef_pins(C.resolve(core["lef"], root), core.get("module"))[pin]
    cw, ch = core["outline_um"]
    x, y = p["xy"] or (cw / 2, ch / 2)
    o = core.get("orient", "R0")
    x, y = {"R0": (x, y), "MX": (x, ch - y), "MY": (cw - x, y), "R180": (cw - x, ch - y)}[o]
    ox, oy = core.get("track_offset_um", [0.0, 0.0])
    x, y = core["origin_um"][0] + ox + x, core["origin_um"][1] + oy + y
    return S.tap_clear(t, x, y, taken)


def add_core_taps(P, tn, t, target_ps, root=None):
    """CP2: an EARLY dedicated tap (clock.taps[] kind 'core', insertion_ps = the core's internal clock latency, QC
    convention) for every hard-core clock pin whose internal latency (TT max_clock_tree_path, rise) leaves no room on a
    grid tap: latency > target - CORE_TAP_MARGIN_PS.  The type's clock.core_taps = 'early' switches them on in the
    kit (port clk_c<k>, spine delivers it (latency - target) early).  Returns [(tap name, latency)]."""
    import cores as C
    ck = t.setdefault("clock", {})
    taps = [tp for tp in ck.get("taps", []) if tp.get("kind") != "core"]
    taken = [(x, y) for _, x, y in S.tap_grid(P, tn)]
    added = []
    for c in t.get("hard_cores", []):
        for pin, v in sorted(C.clock_pins(c, root).items()):
            if v["rise"] <= target_ps - CORE_TAP_MARGIN_PS:
                continue
            x, y = core_tap_xy(t, c, pin, taken, root)
            taken.append((x, y))
            nm = f"{c['inst']}.{pin}"
            taps.append(dict(name=nm, xy=[round(x, 4), round(y, 4)], kind="core", orient=c.get("orient", "R0"),
                             insertion_ps=round(v["rise"], 1), insertion_tol_ps=float(P.clock["insertion_tol_ps"]),
                             budget_owner=f"{c.get('module')} TT lib max_clock_tree_path rise ({pin}); pair.py --core-taps"))
            added.append((nm, round(v["rise"], 1)))
    if added:
        ck["taps"] = taps
        ck["core_taps"] = "early"
    return added


def bus_centroids(P, tn):
    """{bus: (x, y)}: the pin centroid of every bus of type tn in the type frame (gen_phys.type_pins)."""
    import gen_phys
    acc = {}
    for bn, _b, _l, x, y, _f in gen_phys.type_pins(P, tn):
        a = acc.setdefault(bn, [0.0, 0.0, 0])
        a[0] += x
        a[1] += y
        a[2] += 1
    return {k: (v[0] / v[2], v[1] / v[2]) for k, v in acc.items()}


# CLOCK-RESET/CP1-COLH10 10-25: proof-leaf clock plan.  Shallow face-band trees: <= 500 sinks within 100 um of the tap
# (S81 type: ~1.5-2.4k sinks per 330-um band on 4 grid taps -> 128-178 ps trees, 50 ps internal spread).
PROOF_TAP_MAX_SINKS = 500
PROOF_TAP_RADIUS_UM = 100.0
PROOF_SINK_BIN_UM = 10.8


def leaf_sink_sites(P, tn, leaf="reach", hop_um=None, bin_um=PROOF_SINK_BIN_UM):
    """[[x, y, n]] (type frame, binned at bin_um) of the proof leaf's OWN registers, as proof_leaf builds them: q (one
    per in bit) at its in pin, the out register (one per out bit) at its out pin, and the reach leaf's fold / pipeline
    stages f_s0..f_s<st> of out bus b from in bus i spread evenly on the line from i's pin centroid to b's pin (stage j
    at (j + 1) / (st + 2)).  The face registers and ft stations are schema-planned sinks (taps.planned_sinks) and are
    not repeated here."""
    import collections
    import gen_phys
    t = P.types[tn]
    ins = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "in"]
    outs = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "out"]
    at = {}
    for bn, bit, _l, x, y, _f in gen_phys.type_pins(P, tn):
        at.setdefault(bn, {})[bit] = (x, y)
    c = collections.Counter()

    def put(x, y, n=1):
        c[(int(x // bin_um), int(y // bin_um))] += n
    for b, _w in ins:
        for x, y in at.get(b, {}).values():
            put(x, y)
    for b, _w in outs:
        for x, y in at.get(b, {}).values():
            put(x, y)
    if leaf == "reach" and ins:
        geo = bus_centroids(P, tn)
        plan = reach_plan(ins, outs, geo, hop_um or leaf_hop_um())
        for b, _w in outs:
            for i, _d, st in plan[b]:
                gx, gy = geo[i]
                for x, y in at.get(b, {}).values():
                    for j in range(st + 1):
                        f = (j + 1) / (st + 2)
                        put(gx + f * (x - gx), gy + f * (y - gy))
    return [[round((i + 0.5) * bin_um, 3), round((j + 0.5) * bin_um, 3), n] for (i, j), n in sorted(c.items())]


PROOF_RESET_ITERS = 6


def reset_sink_sites(P, tn, bin_um=PROOF_SINK_BIN_UM):
    """[[x, y, n]] binned sites of the type's generated reset relays (reset_tree.for_type: wire relays, per-tap
    synchronisers and pads) -- clocked flops the kit places at those sites.  [] when the plan builds no tree."""
    import collections
    import reset_tree as RT
    try:
        T = RT.for_type(P, tn)
    except Exception:       # noqa: BLE001 -- a plan without a generated reset tree: no reset sinks
        return []
    c = collections.Counter()
    for r in T.get("relays", []):
        x, y = r["xy"]
        c[(int(x // bin_um), int(y // bin_um))] += 1
    return [[round((i + 0.5) * bin_um, 3), round((j + 0.5) * bin_um, 3), n] for (i, j), n in sorted(c.items())]


def _merge_bins(a, b):
    acc = {}
    for x, y, n in list(a) + list(b):
        acc[(x, y)] = acc.get((x, y), 0) + n
    return [[x, y, n] for (x, y), n in sorted(acc.items())]


def is_proof_type(t):
    c = t.get("contents", [])
    return len(c) == 1 and c[0]["module"] == f"{t['module']}_proof_leaf" and not t.get("hard_cores")


def proof_clock(raw, leaf="reach", max_sinks=PROOF_TAP_MAX_SINKS, radius_um=PROOF_TAP_RADIUS_UM, hop_um=None):
    """In place on a pair plan: every coreless proof-leaf type gets a density clock plan from its own sinks (see the
    module docstring).  Keeps tap_um / layer / bound insertion keys; drops the grid pitch and every non-core tap.
    -> {type: taps.report summary (n taps, max planned sinks, max radius)}."""
    import taps as TP
    P = S.Plan(raw)
    done = {}
    for tn, t in raw["partition_types"].items():
        if not is_proof_type(t):
            continue
        ck = t.setdefault("clock", {})
        for k in ("tap_pitch_um", "sink_bins_file", "tap_target_sinks", "tap_min_sinks"):
            ck.pop(k, None)
        ck["taps"] = [tp for tp in ck.get("taps", []) if tp.get("kind") == "core"]
        if not ck["taps"]:
            ck.pop("taps")
        base = leaf_sink_sites(P, tn, leaf, hop_um)
        ck.update(tap_mode="density", tap_max_sinks=int(max_sinks), tap_radius_um=float(radius_um),
                  sink_sites_um=base)
        # the plan's reset relays / per-tap synchronisers are clock sinks too, and their tree is built over the taps:
        # iterate taps <-> reset tree until the relay sites are stable, so a remote relay gets a tap within the radius
        # instead of a long arm on a band tap (S81 t7 density CTS 10-25: sparse controls dragged band trees)
        extra = []
        for _ in range(PROOF_RESET_ITERS):
            rel = reset_sink_sites(S.Plan(raw), tn)
            if rel == extra:
                break
            extra = rel
            ck["sink_sites_um"] = _merge_bins(base, extra)
        note = " [pair.py proof_clock: density taps from the proof leaf's own sinks]"
        if note not in t.get("note", ""):
            t["note"] = (t.get("note", "") + note).strip()
    Q = S.Plan(raw)
    for tn, t in raw["partition_types"].items():
        if not is_proof_type(t):
            continue
        rep = TP.report(Q, tn)
        rel = reset_sink_sites(Q, tn)
        tp = [(n, x, y) for n, x, y, _, _ in TP.density_taps(Q, tn)]
        far = max((min(abs(r[0] - x) + abs(r[1] - y) for _, x, y in tp) for r in rel), default=0.0)
        done[tn] = dict(n=rep["n"], empty=rep["empty"], max_sinks=max(x["planned_sinks"] for x in rep["taps"]),
                        min_sinks=min(x["planned_sinks"] for x in rep["taps"]),
                        sinks=sum(x["planned_sinks"] for x in rep["taps"]),
                        max_radius_um=max(x["radius_um"] for x in rep["taps"]),
                        reset_relays=sum(r[2] for r in rel), reset_relay_max_tap_um=round(far, 1))
    return done


def leaves_for(raw, leaf="reach", hop_um=None):
    """regenerate leaves.sv for an existing coreless pair plan (its types' buses and pins unchanged), e.g. after
    kit_ft_resize: -> verilog text.  Only proof-leaf types (contents == one u_leaf <module>_proof_leaf) are written."""
    P = S.Plan(raw)
    out = ["`timescale 1ns/1ps", "`default_nettype none",
           f"// GENERATED by tools/die_plan/pair.py --leaves-only ({leaf} leaf) for the pair plan {P.name}.",
           "// Vehicle for the boundary / face / channel proof only; not the partitions' real logic."]
    for tn, t in P.types.items():
        c = t.get("contents", [])
        if len(c) != 1 or c[0]["module"] != f"{t['module']}_proof_leaf":
            raise SystemExit(f"type {tn}: not a pair.py proof-leaf type")
        if t.get("hard_cores"):
            raise SystemExit(f"type {tn}: has hard_cores (--cores pair): regenerate with extract")
        ins = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "in"]
        outs = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "out"]
        geo = bus_centroids(P, tn) if leaf == "reach" else None
        out.append(proof_leaf(t["module"], ins, outs, (), geo=geo, hop_um=hop_um)[0])
    out.append("`default_nettype wire")
    return "\n".join(out) + "\n"


def extract(raw, parts, channel_um=0.0, name=None, cores=False, core_taps=False, plan_dir=None, root=None,
            leaf="reach", proof_taps=True):
    """cores: instantiate every hard core of each type in its proof leaf (CP2); core_taps: early core taps
    (add_core_taps); plan_dir: the source plan's directory (relative hard_cores[].pins_file become absolute)."""
    P = S.Plan(raw)
    A, B = parts
    ra, rb = P.rect(A), P.rect(B)
    # shared face / axis
    if abs(ra[2] - rb[0]) < 1e-6 or abs(rb[2] - ra[0]) < 1e-6:
        ax = 0
    elif abs(ra[3] - rb[1]) < 1e-6 or abs(rb[3] - ra[1]) < 1e-6:
        ax = 1
    else:
        raise SystemExit(f"{A} and {B} do not abut")
    far = B if (rb[ax] > ra[ax]) else A
    g = P.grid
    if channel_um and abs(channel_um / g - round(channel_um / g)) > 1e-6:
        raise SystemExit(f"--channel {channel_um} is not a multiple of the die lattice {g}")
    x0, y0 = min(ra[0], rb[0]), min(ra[1], rb[1])
    x1, y1 = max(ra[2], rb[2]), max(ra[3], rb[3])
    shift = {A: [0.0, 0.0], B: [0.0, 0.0]}
    shift[far][ax] = channel_um
    W = x1 - x0 + (channel_um if ax == 0 else 0.0)
    H = y1 - y0 + (channel_um if ax == 1 else 0.0)
    die = copy.deepcopy(P.die)
    die["name"] = name or f"pair_{A}_{B}"
    die["label"] = f"CP1 pair {A} | {B} from {P.name}" + (f", planned channel {channel_um:g} um" if channel_um
                                                         else ", abutted")
    die["outline_um"] = [round(W, 4), round(H, 4)]
    die["channels"] = []
    types = {}
    leaves = ["`timescale 1ns/1ps", "`default_nettype none",
              f"// GENERATED by tools/die_plan/pair.py: proof leaves for the CP1 pair {A}/{B} of {P.name}.",
              "// Vehicle for the boundary / face / channel proof only; not the partitions' real logic."]
    for p in (A, B):
        tn = P.parts[p]["type"]
        if tn in types:
            continue
        t = copy.deepcopy(P.types[tn])
        ins = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "in"]
        outs = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "out"]
        lcores = []
        if cores:
            seen = set()
            for c in t.get("hard_cores", []):
                li = re.sub(r"[^A-Za-z0-9_]", "_", c["inst"].split(".")[-1])
                if li in seen or li == "q" or li == "cat":
                    raise SystemExit(f"type {tn}: hard core leaf instance name {li} not unique")
                seen.add(li)
                cin, cout, cks = core_ports(c, root)
                lcores.append((li, c.get("module", c["inst"]), cin, cout, cks))
                c["note"] = (c.get("note", "") + f" CP2 proof leaf core (was {c['inst']})").strip()
                c["inst"] = f"u_leaf.{li}"
        elif t.get("hard_cores"):
            print(f"pair.py: WARNING type {tn} has {len(t['hard_cores'])} hard_cores but --cores is off: the kit "
                  "places macros the proof leaf does not instantiate", file=sys.stderr)
        for c in t.get("hard_cores", []):
            if c.get("pins_file") and plan_dir and not Path(c["pins_file"]).is_absolute():
                c["pins_file"] = str((Path(plan_dir) / c["pins_file"]).resolve())
        geo = None
        if leaf == "reach":
            geo = bus_centroids(P, tn)
            miss = [b for b, _ in ins + outs if b not in geo]
            if miss:
                raise SystemExit(f"type {tn}: buses without pins {miss} (reach leaf needs every bus's geometry)")
        v, lname = proof_leaf(t["module"], ins, outs, lcores, geo=geo)
        leaves.append(v)
        for b in t.get("buses", []):
            b["leaf"] = f"u_leaf.{b['name']}"
        t["contents"] = [{"inst": "u_leaf", "module": lname, "status": "new", "bind": {"clk": "clk"},
                          "note": "CP1 proof leaf (pair.py)"}]
        t["sources"] = ["leaves.sv"]
        t.pop("kit", None)
        # CP1-R10 (10-24): the proof leaf replaces ALL contents, hard cores included.  S81 v4.7+ types carry
        # hard_cores[] with LEF views; kept, the kit's macro_place.tcl places instances the proof netlist does not
        # have (ORFS stops in floorplan).  Dropped with a note, so the pair kit is the seam vehicle only.
        hc = None if cores else t.pop("hard_cores", None)      # CP2 --cores keeps them (black boxes in the leaf)
        if not cores:
            # Dedicated early taps refer to the hard cores removed from this proof leaf.
            ck = t.get("clock", {})
            if "taps" in ck:
                ck["taps"] = [tap for tap in ck["taps"] if tap.get("kind") != "core"]
            ck.pop("core_taps", None)
        if hc:
            t["note"] = (t.get("note", "") + f" [pair.py: {len(hc)} hard_cores dropped, proof leaf only]").strip()
        types[tn] = t
    leaves.append("`default_nettype wire")
    newparts = []
    for p in (A, B):
        q = copy.deepcopy(P.parts[p])
        ox, oy = q["origin_um"]
        q["origin_um"] = [round(ox - x0 + shift[p][0], 4), round(oy - y0 + shift[p][1], 4)]
        newparts.append(q)
    # ports
    ports, xing = [], []
    off = {p: (x0 - shift[p][0], y0 - shift[p][1]) for p in (A, B)}
    for pid, pr in P.ports.items():
        ends = {pr["src"]["part"], pr["dst"]["part"]}
        if not ends & {A, B}:
            continue
        q = {k: copy.deepcopy(pr[k]) for k in ("id", "width", "face", "layers", "window_um", "order", "epoch", "note")
             if k in pr}
        q["src"], q["dst"] = dict(pr["src"]), dict(pr["dst"])
        inside = [e for e in ("src", "dst") if pr[e]["part"] in (A, B)]
        ref = pr[inside[0]]["part"]
        a = along_axis(pr["face"])
        q["window_um"] = [round(v - off[ref][a], 4) for v in pr["window_um"]]
        if len(inside) == 1:
            o = "dst" if inside[0] == "src" else "src"
            if pr[o]["part"] != DIE_PART:
                q[o] = {"part": DIE_PART, "bus": f"io_{pid}"}
                if o == "src":                       # @die src: face = the dst's die-edge face
                    q["face"] = OPP[pr["face"]]
                q["epoch"] = False
                q["note"] = f"pair.py: was {pr[o]['part']}.{pr[o]['bus']}"
        elif channel_um:
            xing.append(pid)
        q.pop("geom_from", None)
        ports.append(q)
    if channel_um and xing:
        lay = sorted({ln for q in ports if q["id"] in xing for ln in q["layers"]}, key=lambda s: int(s[1:]))
        die["channels"].append({"name": f"ch_{A}_{B}", "between": [A, B], "width_um": channel_um, "layers": lay,
                                "ports": xing, "reason": "CP1-B planned channel: A<->B buses routed at die level"})
    # lanes: follow ft slots (port dst = slot _i -> the port whose src is the same slot's _o on that partition)
    by_src = {(q["src"]["part"], q["src"]["bus"]): q["id"] for q in ports}
    slot_in = {}
    for q in ports:
        d = q["dst"]
        if d["part"] != DIE_PART and d["bus"].endswith("_i"):
            sn = d["bus"][:-2]
            if any(s["name"] == sn for s in types[P.parts[d["part"]]["type"]].get("ft_slots", [])):
                slot_in[q["id"]] = (d["part"], sn + "_o")
    feeds = {by_src[v] for v in slot_in.values() if v in by_src}
    lanes = []
    for q in ports:
        if q["id"] in feeds:
            continue
        chain = [q["id"]]
        while chain[-1] in slot_in and slot_in[chain[-1]] in by_src:
            chain.append(by_src[slot_in[chain[-1]]])
        lanes.append({"id": chain[0], "ports": chain})
    out = {"schema": raw["schema"], "note": f"CP1 pair cut from {P.name} by tools/die_plan/pair.py",
           "die": die, "partition_types": types, "partitions": newparts, "ports": ports, "lanes": lanes,
           "clock": copy.deepcopy(raw["clock"]), "reset": copy.deepcopy(raw["reset"]),
           "census": {"none": f"CP1 proof pair cut from {P.name}: census coverage is checked on the full plan"}}
    if "budgets" in raw:
        out["budgets"] = copy.deepcopy(raw["budgets"])
    sp = out["clock"].setdefault("spine", {})
    # CP2 spine branch model (spine.py): keep the FULL die's spine geometry, so the pair die STA can model each
    # partition tap's branch from the real die root (the pair's own root below only routes the pair die)
    sp["die_root_um"] = list(sp.get("die_root_um") or sp.get("root_um") or [P.W / 2, P.H / 2])
    sp["die_outline_um"] = list(sp.get("die_outline_um") or [P.W, P.H])
    prev = sp.get("part_die_origin_um", {})
    sp["part_die_origin_um"] = {p: list(prev.get(p, P.parts[p]["origin_um"])) for p in (A, B)}
    sp["root_um"] = [round(math.floor(W / 2 / g) * g, 4), round(math.floor(H / 2 / g) * g, 4)]
    if proof_taps and not cores:
        out["proof_clock"] = proof_clock(out, leaf)
    if core_taps:
        Q = S.Plan(out)
        out["core_taps_added"] = {tn: add_core_taps(Q, tn, t, float(Q.clock["insertion_ps"]), root)
                                  for tn, t in out["partition_types"].items()}
    return out, "\n".join(leaves) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--parts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--channel", type=float, default=0.0)
    ap.add_argument("--name")
    ap.add_argument("--cores", action="store_true",
                    help="CP2: the proof leaf instantiates every hard core (black box, clock pins on clk, stub flops "
                         "on every core pin); kits place them from hard_cores[].lef/.lib")
    ap.add_argument("--core-views", metavar="DIR",
                    help="fill hard_cores[].lef/.lib (TT) from DIR/<tile>/views/<module>/ where lib is null "
                         "(fetch_core_views.sh writes this layout)")
    ap.add_argument("--core-taps", action="store_true",
                    help="early dedicated clock taps (clock.taps kind core) for core clock pins whose internal "
                         "latency leaves no room under the common latency")
    ap.add_argument("--leaf", choices=("reach", "fold"), default="reach",
                    help="proof leaf dataflow: reach (default, CP1-R10: nearest in bus per out bus, pipelined per "
                         "reach hop) or fold (legacy all-bus XOR fold: unpipelined cross-partition paths)")
    ap.add_argument("--leaves-only", action="store_true",
                    help="PLAN is an existing coreless pair plan: only rewrite OUT/leaves.sv with the --leaf dataflow")
    ap.add_argument("--clock-only", action="store_true",
                    help="PLAN is an existing coreless pair plan: rewrite OUT/pair_plan.json with the proof-leaf "
                         "density clock plan (proof_clock) only")
    ap.add_argument("--grid-taps", action="store_true",
                    help="keep the full type's tap grid on proof-leaf types (legacy; no proof_clock)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    if a.clock_only:
        rep = proof_clock(raw, a.leaf)
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "pair_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
        errs = S.validate(raw)
        for tn, r in rep.items():
            print(f"proof clock {tn}: {r}")
        print(f"{Path(a.out) / 'pair_plan.json'}: schema " + ("PASS" if not errs else "FAIL\n  " + "\n  ".join(errs[:20])))
        return 1 if errs else 0
    if a.leaves_only:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "leaves.sv").write_text(leaves_for(raw, a.leaf))
        print(f"{Path(a.out) / 'leaves.sv'}: {a.leaf} proof leaves for {len(raw['partition_types'])} types")
        return 0
    if a.core_views:
        import cores as C
        done, miss = C.fill_views(raw, a.core_views)
        print(f"core views: {len(done)} hard_cores filled from {a.core_views}" +
              (f"; MISSING {miss[:8]}" if miss else ""))
        if miss and a.cores:
            want = {P_["type"] for P_ in raw["partitions"] if P_["name"] in a.parts.split(",")}
            bad = [m for m in miss if m[0] in want]
            if bad:
                print(f"--cores: no views for {bad}")
                return 1
    errs = S.validate(raw)
    if errs:
        print("plan invalid:\n  " + "\n  ".join(errs[:20]))
        return 1
    plan, leaves = extract(raw, a.parts.split(","), a.channel, a.name, cores=a.cores, core_taps=a.core_taps,
                           plan_dir=str(Path(a.plan).resolve().parent), leaf=a.leaf, proof_taps=not a.grid_taps)
    for tn, r in (plan.pop("proof_clock", None) or {}).items():
        print(f"proof clock {tn}: {r}")
    added = plan.pop("core_taps_added", None)
    if added:
        for tn, lst in added.items():
            print(f"core taps {tn}: " + (", ".join(f"{n} ({ps:g} ps)" for n, ps in lst) or "none"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in plan["partition_types"].values():        # absolute: the kit generators resolve sources under --rtl-root
        t["sources"] = [str((out / "leaves.sv").resolve())]
    (out / "pair_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    (out / "leaves.sv").write_text(leaves)
    errs = S.validate(plan)
    print(f"{out / 'pair_plan.json'}: {len(plan['ports'])} ports, {len(plan['lanes'])} lanes, "
          f"die {plan['die']['outline_um']}, channels {len(plan['die']['channels'])}; schema "
          + ("PASS" if not errs else "FAIL\n  " + "\n  ".join(errs[:20])))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
