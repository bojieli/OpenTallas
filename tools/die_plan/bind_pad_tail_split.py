"""KV-PAD-TAIL-SPLIT (FABLE-FIX-KV-HG-CHAIN 11-18): per-consumer-core tail copies of a landing pad.

A landing pad (bind.py emit_type, "landing pad: as-built relative timing") is ONE ot_dp_dly #(.W(1), .D(pad)) per
(in-bus bit, pad) and every consumer pin reads its q.  When the consumers are pins of several hard cores far apart, the
last pad flop drives all of them in one hop and no site reaches every core (measured on kv3_pv_v12: 768 pad chains x 8
kv3_pv_pair pins 644..1,761 um apart, register-to-core -1,197 ps at placement; chain re-spacing made it worse).

Opt-in asbuilt key (absent = byte-identical bind output):

    "land_pad_tail_split": {"types": ["kv3_pv.*"], "min_spread_um": 400, "hop_um": 380}

For a (bus bit, pad) of a selected partition type whose consumer pins sit on two or more plan hard cores with a
pin-to-pin Manhattan spread S over min_spread_um, the pad becomes a shared trunk ot_dp_dly D = pad - K (omitted when 0)
and one ot_dp_dly D = K per consumer hard core; every consumer pin reads the copy of its own core.

    K = min(pad, max(1, ceil((S / 2) / hop_um)))

S / 2 is the longest branch when the trunk ends at the L1 centre of the consumer pins (plan pin xy = core origin +
track_offset + orient(pin)), hop_um the register reach.  The depth per sink stays `pad`: only the emitted instances
change, the sink descriptors (R8 table, bind_latency / lane as-built records, LATCHECK input) are untouched.

Pipes (KV-D23-REACH 11-18, opt-in sub-key "pipes": true; absent or false = byte-identical): the same rule for an
INTRA-partition kept transport pipe `ot_dp_dly #(.W(W), .D(N)) u_d<N>_<leaf>_<port>` (bind.py "intra-partition kept
transport stages") whose last flop feeds pins of several hard cores (kv3_pv_v12: u_d60_vport_*_out_v_hi.q -> kv3_pv_pair
s1__pv2, 1,447 endpoints, -683 ps at placement).  For a pipe with at least one bit whose consumer pins sit on two or more
plan hard cores more than min_spread_um apart:

    trunk   ot_dp_dly #(.W(W), .D(N - K)) u_d<N>_.._t          shared stages, all bits
    tail    ot_dp_dly #(.W(W), .D(K))     u_d<N>_..            the old name and wire, for readers that are not split
                                                               (absent when every reader of the pipe is split)
    copy    ot_dp_dly_keep #(.W(1), .D(K)) u_pd<K>_d<N>_.._<bit>_<core>_<N>    one per split (bit, consumer core)

    K = min(N - 1, max(1, ceil((S / 2) / hop_um))),  S = the largest spread over the split bits of the pipe

One K per pipe (the trunk is one module); N = 1 pipes are not split (no stage to take the copy from).  The copy lines carry
the pad tail-copy marker and a u_pd<K>_ name, so the siting hook (gen_phys.tail_copy_place, tail_copy_anchor.tcl) lists and
sites them like pad copies.  Only a pin whose sink IS the pipe is split: readers through a re-emitted OR / AND, INNER strap
banks and ports with a declared core-input pipe / lockup keep the shared tail (counted in the record).

A consumer that is a soft leaf (no plan pin xy) holding plan hard cores counts as ONE consumer at the centroid of those
cores (leaf_xy).  Not covered (left as emitted today, counted in bind_pad_tail_split.json): R8 strap-count banks (ot_dp_dly_cnt),
PAD_TREE types, position-bank members, registered-pin hard partitions; consumers that are not plan hard cores (or have
no plan pin xy) keep reading the shared full-depth pad.

BIN-COPY (FABLE-FIX-QC-N N4.1 11-18), optional sub-key "wire_leaves": [as-built leaf module, ..] (absent = nothing below
runs, byte-identical output).  An in-boundary flop bit (u_bin_<bus> q[j], pad 0) whose value reaches the pins of several
far hard cores THROUGH a pure-wiring leaf (QC st_a: u_bin_rs_s0/1 q[513:512] -> u_frs.rs_s_c -> rs_s_c_p of the four station
rows, 1,000 um apart, -272 ps at CTS; a register on the leaf output would add a cycle) gets one kept copy of that flop
per consumer core: `ot_dp_dly_keep #(.W(1), .D(1))` on the bin flop's own d bit, read by that core's pins instead of the
leaf output.  Same split rule (>= 2 plan hard cores, spread over min_spread_um), same site rows (consumer pin centroid),
same `landing pad tail copy for core` marking, 0 added cycles: the copy captures the edge the bin flop captures.  The
leaf must be proven pure wiring from its RTL (bind_wire_leaf.wire_map, fail closed); bind_bin_copies.json lists every
re-pointed sink with the leaf output it bypasses and the leaf input that carries the same bit, and bind_verify proves
the wiring again from the RTL and then requires the sink to see exactly the source and depth of that leaf input.

R8-KEEP (FABLE-FIX-QC-STRAP 11-21), optional sub-key "r8_keep": true (absent or false = byte-identical output).  Every R8
strap site emits its fixed common pad as `ot_dp_dly #(.W(W), .D(base)) u_r8b_<site>_f`.  When several sites of one type
read the SAME source bits with the same base (QC st_a: rs_n_c[3:0] of x_hc1_i into the four station-row cores), the
chains are identical and yosys opt_merge folds them into ONE chain whose last flop drives every core (measured on
slw_st_a_v2__cl9f076a5c: u_r8b_..._u_r1/r2/r3_rs_n_c_p_f have no cell in 1_2_yosys.v, one flop drives four cores stacked
over 1 mm, -169 ps post-hook CTS / -333 ps at GRT RC on 43 endpoints).  With the sub-key, each fixed pad of such a group
(>= 2 sites with equal W, base and d expression) of a selected type is emitted as `ot_dp_dly_keep` (same instance name,
wire, r[] / q register names): every site keeps its own chain, so the placer can run it to its own core pin
(core_input_chain.tcl R8-CORE-SEAT).  The ot_dp_dly_cnt bank and the strap of each site are unchanged; depth per sink =
base + count is unchanged (R8 table, bind_latency, LATCHECK, r8_strap_lec untouched; ot_dp_dly_keep == ot_dp_dly).
bind_pad_tail_split.json records the groups as types.<type>.r8_keep.

REACH (FABLE-FIX-KV-PV class D 11-19), optional sub-keys "route": true and "require_reach": true (absent or false =
byte-identical output).  Measured on kv3_pv_v8 (pv_N_0, the end of the PV command chain: column pads 0 / 1): K is capped
by the pad, so 1,474 copy hops were over 380 um (max 870) and the pad-0 consumers read the in-boundary flop over 2.5 mm.
The pad a (bus bit, pad) needs is a function of geometry alone:

    split pad   need = trunk + tail,  tail = max(1, ceil(R / hop_um)),  trunk = ceil(|src - T|_1 / hop_um)
                T = L1 centre of the consumer pins, R = the longest T -> pin run: S / 2, and with "route" the Manhattan
                route round the plan hard cores (the L / Z rule of tail_copy_anchor.tcl tcs_route) when that is longer
    shared pad  need = ceil(|src - farthest pin|_1 / hop_um) - 1        (pad + 1 hops: bin flop -> pad stages -> pin)
    src         = the in-boundary flop of the bus: its plan relay_sites site (u_bin_<bus>.q[j]), else the centre of the
                  bus clock-landing band (clock.landing_contract.bands.<bus>.rect_um); unknown = trunk 0 / need 0

"route" sizes K from R instead of S / 2 (K = min(pad, tail)).  With either sub-key the bind records, per in bus of a
selected type, `reach.buses.<bus>` = {pads, need, min_pad, short, short_pads} (pad = the landing pad + the lane pad of
the bus; short = need - pad when positive) in bind_pad_tail_split.json; "require_reach" makes a short pad a bind error
(the pad is then raised where its law lives: the R8 owner tables -- KV PV kv_pv_col_pads.py --min-pad /
kv_pv_v_pads.py --e-min-pad -- or lane cycles).  pad_reach_census.py runs the same rule on a bound kit RTL + the plan.
"""
import math
import os
import re
from pathlib import Path

KEY = "land_pad_tail_split"

# Tail copies of one pad share D and clk, so synthesis (yosys opt_merge) folds them back into ONE flop (measured: QC st_a
# 140 copies -> 35 survive; KV PV 7,040 -> 3,155).  The copies are therefore a separate delay module whose stage registers
# carry (* keep *); same ports and same r[] / q register names as ot_dp_dly, so the relay siting tools still match them.
KEEP_MODULE = "ot_dp_dly_keep"
KEEP_CELL = """// ot_dp_dly_keep (TAIL-SPLIT): ot_dp_dly with (* keep *) stage registers, for pad tail copies that must not be merged.
module ot_dp_dly_keep #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep *) reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule
"""


R8_FIXED_RE = re.compile(r"^(\s*)ot_dp_dly( #\(\.W\((\d+)\), \.D\((\d+)\)\) (u_r8b_\w+_f) \(\.clk\(clk\), \.d\((.*)\), "
                         r"\.q\(\w+\)\);  // (?:R8|INNER) strap site .*)$")


def r8_keep(body):
    """R8-KEEP: in the emitted body lines of one type, the fixed common pads (u_r8b_<site>_f) of R8 strap sites that share
    width, depth and d expression become ot_dp_dly_keep (in place), so synthesis keeps one chain per site.  Returns the
    record rows [{width, depth, d, insts, extra_flops}] (empty = nothing changed)."""
    groups = {}
    for i, ln in enumerate(body):
        m = R8_FIXED_RE.match(ln)
        if m:
            groups.setdefault((int(m.group(3)), int(m.group(4)), m.group(6)), []).append((i, m))
    rec = []
    for (w, d, src), rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        for i, m in rows:
            body[i] = f"{m.group(1)}{KEEP_MODULE}{m.group(2)}"
        rec.append(dict(width=w, depth=d, d=src, insts=[m.group(5) for _i, m in rows], extra_flops=w * d * (len(rows) - 1)))
    return rec


def site_rows(inst, k, xy):
    """plan relay_sites rows (type_relay_sites.py key form) for the k-stage tail copy `inst`, all stages at xy: the
    pre-GPL anchor at the consumer cluster (r[0..k-2] and q)"""
    xy = [round(float(xy[0]), 3), round(float(xy[1]), 3)]
    rows = {f"{inst}.r[{i}]": list(xy) for i in range(k - 1)}
    rows[f"{inst}.q"] = list(xy)
    return rows


def centroids(by_core):
    """{core inst: [(x, y)..]} -> {core inst: centroid}"""
    return {c: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for c, v in by_core.items()}


def config(ab):
    """the checked option, or None when the key is absent"""
    c = (ab or {}).get(KEY)
    if c is None:
        return None
    if not isinstance(c, dict) or not isinstance(c.get("types"), list) or not c["types"] or \
            set(c) - {"types", "min_spread_um", "hop_um", "wire_leaves", "pipes", "route", "require_reach", "r8_keep"} or \
            not all(isinstance(c.get(k, False), bool) for k in ("pipes", "route", "require_reach", "r8_keep")):
        raise ValueError(f"asbuilt.{KEY}: expected {{types: [regex..], min_spread_um, hop_um[, wire_leaves][, pipes: bool]}}")
    wl = c.get("wire_leaves", [])
    if not isinstance(wl, list) or not all(isinstance(x, str) and x for x in wl) or ("wire_leaves" in c and not wl):
        raise ValueError(f"asbuilt.{KEY}.wire_leaves: expected a non-empty list of as-built leaf module names")
    out = dict(types=[re.compile(x) for x in c["types"]], min_spread_um=float(c.get("min_spread_um", 400.0)),
               hop_um=float(c.get("hop_um", 380.0)), wire_leaves=frozenset(wl), pipes=bool(c.get("pipes", False)),
               route=bool(c.get("route", False)), require_reach=bool(c.get("require_reach", False)),
               r8_keep=bool(c.get("r8_keep", False)))
    if out["hop_um"] <= 0 or out["min_spread_um"] < 0:
        raise ValueError(f"asbuilt.{KEY}: hop_um must be > 0 and min_spread_um >= 0")
    return out


def selected(cfg, tn):
    return any(x.fullmatch(tn) for x in cfg["types"])


def pin_table(hard_cores, plan_dir):
    """{core inst: {port: {bit ('' = scalar): (x, y)}}} in the partition-type frame"""
    import check as CK
    tab = {}
    for hc in hard_cores or []:
        if not (hc.get("pins") or hc.get("pins_file")):
            continue
        try:
            raw = CK.core_pins(hc, plan_dir)
        except (OSError, ValueError, KeyError):
            continue
        w, h = hc["outline_um"]
        o = hc.get("orient", "R0")
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        t = tab.setdefault(hc["inst"], {})
        for nm, _layer, x, y in raw:
            pn, _, bit = nm.partition("[")
            tx, ty = CK._orient_pt(o, w, h, x, y)
            t.setdefault(pn, {})[bit.rstrip("]")] = (hc["origin_um"][0] + dx + tx, hc["origin_um"][1] + dy + ty)
    return tab


NO_PINS_ENV = "OT_BIND_ALLOW_NO_PINS"


def require_pin_tables(hard_cores, plan_dir, tn, environ=None):
    """PINS-GUARD (KV-OWN-PV-R2 11-25, COORD: a silent mis-bind is a correctness gate, not a new rule).  A selected type whose
    hard cores declare pins_file, none of which resolves under plan_dir (a private plan copied outside plan_of_record, no
    pins/ beside it), makes pin_table() return {} and the bind split 0 landing pads: every pad then drives all its cores from
    one flop and the kit timing is not representative (kv3_pv_v1n/v12/v3n private binds 11-24/25: split_pads 0 of 1374).
    Raises ValueError naming the folder unless OT_BIND_ALLOW_NO_PINS=1.  Returns the unresolved paths (empty = fine)."""
    env = os.environ if environ is None else environ
    decl = [hc["pins_file"] for hc in hard_cores or [] if hc.get("pins_file") and not hc.get("pins")]
    if not decl:
        return []
    base = Path(plan_dir or ".")
    miss = [f for f in decl if not (base / f).is_file()]
    if len(miss) < len(decl) or env.get(NO_PINS_ENV) == "1":
        return miss
    raise ValueError(f"{KEY} {tn}: {len(decl)} hard core(s) declare pins_file but none resolves under {base} "
                     f"(first: {base / miss[0]}); the bind would load 0 pin tables and split 0 landing pads. "
                     f"Bind a plan that sits in plan_of_record with pins/ beside it, or set {NO_PINS_ENV}=1 to accept")


def leaf_table(hard_cores):
    """{core inst: (cx, cy)} (box centres) for the leaf fallback"""
    return {h["inst"]: (h["origin_um"][0] + h["outline_um"][0] / 2.0, h["origin_um"][1] + h["outline_um"][1] / 2.0)
            for h in hard_cores or []}


def leaf_xy(ltab, rel):
    """(leaf rel, centroid of its hard cores) for a SOFT consumer leaf that holds plan hard cores (QC st_a station rows:
    u_r0..u_r3 hold the SRAM cores `u_bound.u_<rel>.*`), else (None, None).  The leaf's own flops are placed next to
    its cores, so the centroid of those cores stands for the pin position."""
    pre = tuple(f"{b}{rel}." for b in ("u_bound.u_", "u_bound.", "u_", ""))
    pts = [xy for inst, xy in ltab.items() if inst.startswith(pre)]
    if not pts:
        return None, None
    return rel, (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def pin_xy(tab, rel, pn, i, width):
    """(core inst, (x, y)) of leaf `rel` pin pn[i], or (None, None) when the leaf is no plan hard core / has no pin xy"""
    for inst in (rel, rel[2:] if rel.startswith("u_") else rel):
        t = tab.get(inst)
        if t is None:
            continue
        bits = t.get(pn)
        if bits is None:
            return None, None
        xy = bits.get(str(i))
        if xy is None and width == 1:
            xy = bits.get("")
        return (inst, xy) if xy is not None else (None, None)
    return None, None


def spread(pts):
    """largest pin-to-pin Manhattan distance of the points"""
    a = [x + y for x, y in pts]
    b = [x - y for x, y in pts]
    return max(max(a) - min(a), max(b) - min(b))


def tail_depth(pad, by_core, cfg, boxes=None):
    """(K, S) for a pad whose consumer pins are {core inst: [(x, y)..]}, or None when it is not split.  `boxes` (plan
    hard-core boxes, core_boxes()) are used only with the "route" sub-key: K from the routed T -> pin run."""
    if pad < 1 or len(by_core) < 2:
        return None
    s = spread([xy for v in by_core.values() for xy in v])
    if s <= cfg["min_spread_um"]:
        return None
    return min(pad, tail_need(by_core, cfg, boxes)), s


# ---- REACH (class D 11-19): the pad a bus bit needs from geometry ------------------------------------------------------
HALO_UM = 9.0          # tail_copy_anchor.tcl: macro halo of the copy sites and the channel offset of a Z route
PIN_INSET_UM = 3.0     # a pin sits on (or just inside) its core edge: boxes shrink by this for the crossing test


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def l1_centre(pts):
    """the point with the smallest largest Manhattan distance to pts (tail_copy_anchor.tcl tcs_l1_centre)"""
    u = [x + y for x, y in pts]
    v = [x - y for x, y in pts]
    uu, vv = (min(u) + max(u)) / 2.0, (min(v) + max(v)) / 2.0
    return ((uu + vv) / 2.0, (uu - vv) / 2.0)


def core_boxes(hard_cores):
    """[(x0, y0, x1, y1)] of the plan hard cores (outline swapped for the 90-degree orients)"""
    out = []
    for h in hard_cores or []:
        w, hh = h["outline_um"]
        if str(h.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        x, y = h["origin_um"]
        out.append((float(x), float(y), float(x) + float(w), float(y) + float(hh)))
    return out


def _seg_hits(a, b, boxes):
    hit = []
    for bx in boxes:
        x0, y0, x1, y1 = bx[0] + PIN_INSET_UM, bx[1] + PIN_INSET_UM, bx[2] - PIN_INSET_UM, bx[3] - PIN_INSET_UM
        if a[1] == b[1]:
            if y0 < a[1] < y1 and max(a[0], b[0]) > x0 and min(a[0], b[0]) < x1:
                hit.append(bx)
        elif a[0] == b[0]:
            if x0 < a[0] < x1 and max(a[1], b[1]) > y0 and min(a[1], b[1]) < y1:
                hit.append(bx)
    return hit


def _path_hits(pts, boxes):
    hit = []
    for i in range(1, len(pts)):
        for bx in _seg_hits(pts[i - 1], pts[i], boxes):
            if bx not in hit:
                hit.append(bx)
    return hit


def push_out(p, boxes, halo=HALO_UM):
    """p moved to the nearest edge of the (halo-grown) core box it lies in, a few rounds (tcs_push_out)"""
    x, y = p
    for _ in range(8):
        inside = [b for b in boxes if b[0] - halo < x < b[2] + halo and b[1] - halo < y < b[3] + halo]
        if not inside:
            break
        x0, y0, x1, y1 = inside[0][0] - halo, inside[0][1] - halo, inside[0][2] + halo, inside[0][3] + halo
        _d, x, y = min((x - x0, x0, y), (x1 - x, x1, y), (y - y0, x, y0), (y1 - y, x, y1))
    return (x, y)


def route_len(t, l, boxes, step=HALO_UM):
    """(length, cores crossed) of the Manhattan route t -> l round the hard cores: the two L shapes, then a Z through the
    channel beside every core an L crosses; fewest crossings, then shortest (tail_copy_anchor.tcl tcs_route)"""
    cands = [[t, (l[0], t[1]), l], [t, (t[0], l[1]), l]]
    hit = []
    for c in list(cands):
        for bx in _path_hits(c, boxes):
            if bx not in hit:
                hit.append(bx)
    for x0, y0, x1, y1 in hit:
        for xc in (x0 - step, x1 + step):
            cands.append([t, (xc, t[1]), (xc, l[1]), l])
        for yc in (y0 - step, y1 + step):
            cands.append([t, (t[0], yc), (l[0], yc), l])
    best = None
    for c in cands:
        n = len(_path_hits(c, boxes))
        ln = sum(md(c[i - 1], c[i]) for i in range(1, len(c)))
        if best is None or (n, ln) < best:
            best = (n, ln)
    return best[1], best[0]


def hops(d, cfg):
    """register hops a run of d um needs (a run under a quarter hop needs no stage of its own)"""
    return 0 if d <= cfg["hop_um"] / 4.0 else int(math.ceil(d / cfg["hop_um"] - 1e-9))


def tail_need(by_core, cfg, boxes=None):
    """copy stages K the consumer pins {core inst: [(x, y)..]} need: ceil(R / hop_um), R = S / 2, or with the "route"
    sub-key and core boxes the longest routed trunk-end -> pin run when that is longer"""
    pts = [xy for v in by_core.values() for xy in v]
    r = spread(pts) / 2.0
    if cfg.get("route") and boxes:
        t = push_out(l1_centre(pts), boxes)
        r = max(r, max(route_len(t, p, boxes)[0] for p in set(pts)))
    return max(1, int(math.ceil(r / cfg["hop_um"] - 1e-9)))


def src_xy(typ, bus):
    """the plan point of the in-boundary flop of in bus `bus` of partition type dict `typ`: the mean of its relay_sites
    u_bin_<bus>.q[j] rows, else the centre of its clock-landing band, else None"""
    rs = [v for k, v in (typ.get("relay_sites") or {}).items() if k.startswith(f"u_bin_{bus}.q[")]
    if rs:
        return (sum(v[0] for v in rs) / len(rs), sum(v[1] for v in rs) / len(rs))
    band = (((typ.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).get(bus) or {}
    r = band.get("rect_um")
    if r:
        return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)
    return None


def reach(pad, by_core, cfg, src=None, boxes=None):
    """dict(need, trunk, tail, short, split) of a (bus bit, pad) whose consumer pins are {core inst: [(x, y)..]} and whose
    in-boundary flop sits at src (None = unknown: the source run is not priced)"""
    pts = [xy for v in by_core.values() for xy in v]
    split = len(by_core) >= 2 and spread(pts) > cfg["min_spread_um"]
    if split:
        tail = tail_need(by_core, cfg, boxes)
        t = l1_centre(pts) if not boxes else push_out(l1_centre(pts), boxes)
        trunk = 0 if src is None else hops(md(src, t), cfg)
    else:
        tail = 0
        trunk = 0 if src is None else max(0, int(math.ceil(max(md(src, p) for p in pts) / cfg["hop_um"] - 1e-9)) - 1)
    need = trunk + tail
    return dict(need=need, trunk=trunk, tail=tail, short=max(0, need - int(pad)), split=split)


def bin_spread(by_core, cfg):
    """BIN-COPY: the pin spread S of an in-boundary flop bit whose consumer pins are {core inst: [(x, y)..]}, or None
    when it keeps the one flop (fewer than two cores, or inside min_spread_um)"""
    if len(by_core) < 2:
        return None
    s = spread([xy for v in by_core.values() for xy in v])
    return s if s > cfg["min_spread_um"] else None


def pipe_depth(n, spreads, cfg):
    """K (tail-copy stages) of an n-stage intra-partition pipe whose split bits have the consumer pin spreads `spreads`
    (each already over min_spread_um), or 0 when the pipe is not split: one trunk stage always stays"""
    if n < 2 or not spreads:
        return 0
    return min(n - 1, max(1, math.ceil((max(spreads) / 2.0) / cfg["hop_um"])))
