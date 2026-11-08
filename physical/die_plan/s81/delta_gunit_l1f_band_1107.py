#!/usr/bin/env python3
"""S81-GUNIT-FORM-1 11-07 (DIE-S81-78, COORD 19:0x ruling): gunit__t1 OVER-CELLS RE-FORM = the l1f band split made hard.

Measured (kit-wave e9eda32d41c gunit__t1 attempt_12, OT_NATIVE_CELL_CAP actual_std=976402 at pre-floorplan read_db): the four
soft router fronts dsdv_gunit_l1f (u_gunit.g_l1f[q].u_l1f) are ~241k cells / ~24k flops each, 98.7 % of the type; the
parent glue is ~12k.  One front alone is above the 150k conservative form, and the hard front failed 10 variants
(10-20..10-22), so it is never one core.  The RTL front is now the banded parent (rtl/.../dsdv_gunit_l1f.sv, same ports /
edges, lockstep-proved against dsdv_gunit_l1f_flat): three hard row bands per front, each its own small clock tree:
  u_alo  dsdv_gunit_l1f_ba0  432 x 151.2  bias SRAM 0, lanes 0..7 adders / keys / sort8 #0      (~82k cells)
  u_f    dsdv_gunit_l1f_bf   432 x 172.8  W/E pin flops, SC store, select control, gather, merge (~77k cells)
  u_ahi  dsdv_gunit_l1f_ba1  432 x 151.2  bias SRAM 1, lanes 8..15                               (~82k cells)
Each front is one vertical stack A_lo / F / A_hi with 21.6-um channels (496.8 tall): the band crossings are flop-to-flop,
straight N-S hops (F's S / N pins sit at the x of the A bands' N / S pins).  Front 0 sits W of the collector L1c (the
face the L1 / L1c pins point at); fronts 1..3 in the row above L1c / L1 / L2 (every L1 / L1c pin <= ~650 um Manhattan).
The landing collector relays and the added grid taps the soft fronts' area held are NOT keepouts here: they are re-solved
around the new cores by the type's own tools (reset_tree.for_type, added_tap_recentre.py) as the second step of this event.  The bands are hard cores NESTED in the bound leaf
u_bound.u_u_gunit_g_l1f_<q>_u_l1f (physical_inst / physical_master, the DIE-QC-69 form), so the die bind and elab are
unchanged (the leaf master name and ports are the same).  The 8 DIE-S81-66 l1f SRAM contents rows go (the SRAMs are inside
ba0 / ba1 now).  Outline, buses, ft slots, stations, the 10 existing cores, reset and neighbours are unchanged.

Reset: each band's rst_n keeps its bound net (reset_net rst_n, the QC-SLECTL-B form): it is the front leaf's own rst_n
inside u_l1f (each band lands it in its own ot_rst_relay), so the bands are not wavefront targets and the type's reset
contract (taps, core resets, outs) is unchanged; only relay SITES move off the new cores.

Pin tables: ba0 / ba1 from their 10-22 routed views (old-rule CLOSED; ports unchanged since), core_pins_gen rule; bf is
generated here (no view): W face = the L1 side (sa/sb/we/c_*, clk, rst_n), E face = the L1c side (g_*, o_*), S / N = the
A_lo / A_hi crossings aligned bit for bit.  Clock: one early core tap per band clk pin at the ba0 view's boundary-register
insertion (ESTIMATE until each band's own kit measures it).

Step 2 (same tools as the type's other plan events): the added grid taps the new cores cover move to the nearest legal
site (0.864-um Manhattan rings, taps.grid_explicit_sites rule; taps.grid_explicit_taps radius / cap re-validated); the R4
grid taps re-site themselves off the cores (schema._grid_taps); the reset relays are re-solved (reset_tree.for_type) and
mirrored into the plan landing_contract and the landed sidecar (delta_alltap_coll_1103 rule: tap count, core resets, outs,
entry / root unchanged, asserted; local sources take their nearest tap).  The bound reset identity therefore changes: the
event needs the strict die bind (bind step, the elab is unchanged) and the die clock check before kits use it.

usage: delta_gunit_l1f_band_1107.py PLAN_IN PLAN_OUT REPORT.json SIDECAR   (repo root; rewrites SIDECAR in place; a
second run refuses)"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "csite_1105"))
import core_pins_gen as CP  # noqa: E402
import delta_c_macro_sites_1105 as C  # noqa: E402

ID = "S81-GUNIT-FORM-1/PLAN 11-07 l1f band cores (delta_gunit_l1f_band_1107.py)"
TYPE = "gunit__t1"
PINS = "inputs/core_pins"
VIEW = {"dsdv_gunit_l1f_ba0": "physical/ref_tile/s81dv_l1fb_a0/views/dsdv_gunit_l1f_ba0",
        "dsdv_gunit_l1f_ba1": "physical/ref_tile/s81dv_l1fb_a1/views/dsdv_gunit_l1f_ba1"}
BANDS = (("u_alo", "dsdv_gunit_l1f_ba0", 151.2, 0.0), ("u_f", "dsdv_gunit_l1f_bf", 172.8, 172.8),
         ("u_ahi", "dsdv_gunit_l1f_ba1", 151.2, 345.6))
BW, STACK_H = 432.0, 496.8
# front 0 in the W column (beside the L1c / L1 W-face pins); fronts 1..3 in the row above L1c / L1 / L2 (y >= L2 top + halo)
STACKS = [(207.36, 17.28), (17.28, 682.56), (466.56, 682.56), (915.84, 682.56)]
PT_CLEAR = 17.28   # macro edge to a kept clock / station / landing point (u_gunit.u_l2.clk 1365.2: 17.36 from front 3)
# bf has no view: its plan LEF is the KW-PROV-1 contract abstract of this pin table (tools/autopilot/prov_view.py make,
# outline + pins + RTL directions, OBS M1..M5 less pin windows), committed so the core kit and the parent read one contract
BF_LEF = "physical/die_plan/s81/cores/legacy/lef/gf1_1107/dsdv_gunit_l1f_bf.lef"
TOFF = [0.108, 0.012]          # CORE_TRACK_OFFSET (R0 cores of this type: l1c)
CELLS = {"dsdv_gunit_l1f_ba0": 82000, "dsdv_gunit_l1f_bf": 77000, "dsdv_gunit_l1f_ba1": 82000}
CELLS_BASIS = ("ESTIMATE: kit-wave e9eda32d41c gunit__t1 attempt_12 1_2_yosys.v, l1f_0 cells attributed to the band "
               "cut by name / net, scaled to the 976,402 ODB count (worst case ~100k); <= 150k conservative form")
# F's crossing ports and the A-band pin they face: (bf port, A-band port)
F_S = [("sv_lo", "sv"), ("ctl_lo", "ctl"), ("s0a", "qa"), ("s0b", "qb"), ("sf0", "fo"), ("vf_lo", "vf")]
F_N = [("sv_hi", "sv"), ("ctl_hi", "ctl"), ("s1a", "qa"), ("s1b", "qb"), ("vf_hi", "vf")]
F_W = [("clk", 1), ("rst_n", 1), ("sa_r", 6), ("sa_d", 224), ("sb_r", 6), ("sb_d", 224), ("we", 14), ("c_go", 1),
       ("c_fw", 1), ("c_l", 1), ("c_bn", 3), ("c_lvn", 5)]
F_E = [("g_go", 1), ("g_hit", 6), ("g_a", 42), ("o_v", 1), ("o_f", 1), ("o_l", 1), ("o_g", 1), ("o_d", 245),
       ("o_flt", 1)]


def bits(n, w):
    return [n] if w == 1 else [f"{n}[{i}]" for i in range(w)]


def on_track_y(y):
    """nearest M4 track centre (core frame, TOFF applied) to y"""
    p, o = 0.048, 0.024
    k = round((y + TOFF[1] - o) / p)
    return round(o + k * p - TOFF[1], 4)


def face_pins(names, length, fixed, layer, lo=4.32):
    """names spread evenly over [lo, length - lo] of a W / E face at x = fixed (M4, on track)"""
    n = len(names)
    step = (length - 2 * lo) / max(n - 1, 1)
    assert step >= 4 * 0.048, (n, step)          # >= 4 M4 tracks between pins (pin_min_tracks 4)
    return [dict(name=nm, layer=layer, x=fixed, y=on_track_y(lo + i * step)) for i, nm in enumerate(names)]


def bf_table(a0, a1):
    """bf pins: S face at ba0's N pin x (y = 0.042), N face at ba1's S pin x (y = H - 0.042), W / E faces on M4"""
    H = 172.8
    a0x = {p["name"]: p["x"] for p in a0["pins"]}
    a1x = {p["name"]: p["x"] for p in a1["pins"]}
    out = []
    for side, rows, ax, y in (("S", F_S, a0x, 0.042), ("N", F_N, a1x, round(H - 0.042, 3))):
        for fport, aport in rows:
            w = sum(1 for k in ax if re.fullmatch(re.escape(aport) + r"(\[\d+\])?", k))
            assert w, (side, aport)
            for fb, ab in zip(bits(fport, w), bits(aport, w)):
                out.append(dict(name=fb, layer="M5", x=ax[ab], y=y))
    out += face_pins([b for n, w in F_W for b in bits(n, w)], H, 0.042, "M4")
    out += face_pins([b for n, w in F_E for b in bits(n, w)], H, round(BW - 0.042, 3), "M4")
    names = [p["name"] for p in out]
    assert len(names) == len(set(names))
    pins = {p["name"]: (p["layer"], p["x"], p["y"]) for p in out}
    return dict(module="dsdv_gunit_l1f_bf", lef=None,
                source=f"{ID}: generated (no view): S/N crossings at the ba0 N / ba1 S pin x, W = L1 side, E = L1c side",
                pinhash=CP.pinhash(pins), pins=sorted(out, key=lambda p: p["name"]))


def _forms(k, v, lvl):
    """the text forms the plan file uses for key k at depth lvl: compact_plan style, or a list of one-line items"""
    import compact_plan as CPL
    pad, pad1 = " " * lvl, " " * (lvl + 1)
    out = [pad + json.dumps(k) + ": " + CPL._d(v, lvl, k), pad + json.dumps(k) + ": " + json.dumps(v)]
    if isinstance(v, list) and v:
        out.append(pad + json.dumps(k) + ": [\n" + ",\n".join(pad1 + json.dumps(x, separators=(",", ":")) for x in v)
                   + "\n" + pad + "]")
    return out


def splice(text, old_t, new_t):
    """replace only the changed keys of the type block (contents, hard_cores, clock.taps, note) in the file's own text form"""
    head = f'\n  "{TYPE}": {{\n'
    assert text.count(head) == 1
    a = text.index(head)
    b = text.index("\n  }", a + 1)
    blk = text[a:b]
    for path in (("contents",), ("hard_cores",), ("clock", "taps"), ("note",)):
        ov, nv = old_t, new_t
        for k in path:
            ov, nv = ov[k], nv[k]
        lvl = 2 + len(path)
        hits = [f for f in _forms(path[-1], ov, lvl) if blk.count(f) == 1]
        assert hits, (path, "text form")
        f = hits[0]
        if f.endswith("]") and isinstance(ov, list) and f.split(": ", 1)[1].startswith("[\n") and "\n" + " " * (lvl + 1) + "{" not in f:
            pad1 = " " * (lvl + 1)
            new = " " * lvl + json.dumps(path[-1]) + ": [\n" + ",\n".join(pad1 + json.dumps(x, separators=(",", ":")) for x in nv) \
                + "\n" + " " * lvl + "]"
        else:
            new = _forms(path[-1], nv, lvl)[_forms(path[-1], ov, lvl).index(f)]
        blk = blk.replace(f, new)
    return text[:a] + blk + text[b:]


def resolve_infra(pp, sidecar):
    """step 2 on the written plan pp: move covered added taps, re-solve the reset relays, mirror plan + sidecar"""
    import copy
    import schema as S
    import taps as TP
    import reset_tree as RT
    import compact_plan as CPL
    from placement_obstacles import placement_boxes
    P = S.Plan(S.load(pp), pp)
    typ = P.types[TYPE]
    clear = S.TAP_CLEAR_UM
    boxes = list(placement_boxes(typ, halo=clear).values())
    w, h = typ["outline_um"]

    def legal(x, y, taken):
        return (clear <= x <= w - clear and clear <= y <= h - clear
                and not any(abs(x - a) < clear and abs(y - b) < clear for a, b in taken)
                and not any(a < x < c and b < y < d for a, b, c, d in boxes))
    taken = [(x, y) for _, x, y in S._grid_taps(P, TYPE)]
    moves = {}
    for p in typ["clock"]["added_taps"]:
        x, y = p["xy"]
        if not legal(x, y, taken):
            best = next(((round(x + dx * 0.864, 4), round(y + dy * 0.864, 4))
                         for r in range(1, 600) for i in range(-r, r + 1)
                         for dx, dy in ((i, r - abs(i)), (i, abs(i) - r))
                         if legal(round(x + dx * 0.864, 4), round(y + dy * 0.864, 4), taken)), None)
            assert best, p["name"]
            moves[p["name"]] = [[x, y], list(best)]
            x, y = best
        taken.append((x, y))
    text = Path(pp).read_text()
    raw = json.loads(text)
    t = raw["partition_types"][TYPE]
    for p in t["clock"]["added_taps"]:
        if p["name"] in moves:
            p["xy"] = moves[p["name"]][1]
    tmp = Path(pp).with_suffix(".step2.json")
    tmp.write_text(json.dumps(raw))
    P2 = S.Plan(S.load(str(tmp)), str(tmp))
    ntaps = len(TP.grid_explicit_taps(P2, TYPE))
    T = json.loads(json.dumps(RT.for_type(P2, TYPE)))
    tmp.unlink()
    lc = t["clock"]["landing_contract"]
    old = lc["collector_tree"]
    guard = ("depth", "own_depth", "outs", "core_resets", "entry", "root", "n_clock_taps", "n_reset_consumers", "taps")
    assert RT.consumer_count(old) == RT.consumer_count(T), "tap count changed"
    for k in guard:
        if k == "core_resets":
            assert [(c["inst"], c["pin"]) for c in old[k]] == [(c["inst"], c["pin"]) for c in T[k]], k
        else:
            assert old.get(k) == T.get(k), k
    txy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in T["relays"] if r["q"].startswith("rst_n_t")}
    near = lambda xy: min(range(RT.consumer_count(T)), key=lambda i: abs(txy[i][0] - xy[0]) + abs(txy[i][1] - xy[1]))
    srcs = []
    for s in lc["collector_local_sources"]:
        s = copy.deepcopy(s)
        pt = s["pin_xy_um"]
        tap = near(pt)
        band = s.get("band") or {}
        xy = pt
        if band.get("rect_um") and abs(txy[tap][0] - pt[0]) + abs(txy[tap][1] - pt[1]) > 405:
            x0, y0, x1, y1 = band["rect_um"]
            xy = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = near(xy)
        s["tap"], s["xy_um"] = tap, xy
        srcs.append(s)
    assert lc["collector_children"] == [] and lc["collector_root_node"] == "rst_root_n"
    src_taps = [[a["tap"], b["tap"]] for a, b in zip(lc["collector_local_sources"], srcs)]
    lc.update(collector_tree=T, collector_local_sources=srcs)
    m = re.search(r'^  "' + re.escape(TYPE) + r'": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    text = text[:m.end()] + CPL._d(t, 2) + text[j:]
    assert json.loads(text) == raw
    Path(pp).write_text(text)
    if sidecar:
        stext = Path(sidecar).read_text()
        side = json.loads(stext)
        assert json.dumps(side, separators=(",", ":")) == stext, "sidecar format"
        ent = side["collector"]["types"][TYPE]
        ent.update(tree=T, local_sources=srcs)
        Path(sidecar).write_text(json.dumps(side, separators=(",", ":")))
    return dict(added_tap_moves=moves, grid_explicit_taps=ntaps, relays=[len(old["relays"]), len(T["relays"])],
                local_source_taps=src_taps, sidecar=bool(sidecar),
                note="reset contract guard keys unchanged (asserted); relay sites re-solved around the band cores")


def main():
    src, dst = sys.argv[1:3]
    rep_path = sys.argv[3] if len(sys.argv) > 3 else None
    sidecar = sys.argv[4] if len(sys.argv) > 4 else None
    text = Path(src).read_text()
    plan = json.loads(text)
    t = plan["partition_types"][TYPE]
    assert not any(c["module"].startswith("dsdv_gunit_l1f") for c in t["hard_cores"]), "second run"
    W, H = t["outline_um"]

    # pin tables
    tabs = {}
    for mod, d in VIEW.items():
        j, size = CP.table(mod, f"{d}/{mod}.lef")
        assert tuple(size) == (BW, 151.2), (mod, size)
        tabs[mod] = j
    tabs["dsdv_gunit_l1f_bf"] = bf_table(tabs["dsdv_gunit_l1f_ba0"], tabs["dsdv_gunit_l1f_ba1"])
    for mod, j in tabs.items():
        (HERE / PINS / f"{mod}.json").write_text(json.dumps(j, indent=0) + "\n")

    # drop the l1f SRAM sites (inside ba0 / ba1 now)
    sram = [c for c in t["contents"] if c["inst"].startswith("u_bound.u_u_gunit_g_l1f_")]
    assert len(sram) == 8 and all(c["module"] == "ot_sram_1r1w_128x256_m1_r2c2" for c in sram), len(sram)
    t["contents"] = [c for c in t["contents"] if c not in sram]

    kt = json.loads(json.dumps(t))          # keepouts without the re-solvable relay / added-tap sites
    kt["clock"]["landing_contract"].pop("collector_tree", None)
    kt["clock"].pop("added_taps", None)
    rects, pts = C.keepouts(kt)
    ins = {}
    for mod in VIEW:
        ins[mod] = json.loads((ROOT / VIEW[mod] / "insertion.json").read_text())
    tt = ins["dsdv_gunit_l1f_ba0"]["tt"]["boundary"]["mean"]
    ff = ins["dsdv_gunit_l1f_ba0"]["ff"]["boundary"]["mean"]
    rows, taps, placed = [], [], []
    for q, (sx, sy) in enumerate(STACKS):
        assert sx >= 17.28 and sy >= 17.28 and sx + BW <= W - 17.28 and sy + STACK_H <= H - 17.28, (q, sx, sy)
        for inst, mod, h, dy in BANDS:
            x, y = sx, round(sy + dy, 4)
            b = (x, y, x + BW, y + h)
            assert not any(b[0] < r[2] and r[0] < b[2] and b[1] < r[3] and r[1] < b[3] for r in rects), (q, inst, b)
            assert not any(b[0] - PT_CLEAR < x < b[2] + PT_CLEAR and b[1] - PT_CLEAR < y < b[3] + PT_CLEAR for x, y in pts), \
                (q, inst, b, [p for p in pts if b[0] - PT_CLEAR < p[0] < b[2] + PT_CLEAR and b[1] - PT_CLEAR < p[1] < b[3] + PT_CLEAR])
            assert all(not (b[0] < o[2] + C.CH and o[0] < b[2] + C.CH and b[1] < o[3] + C.CH and o[1] < b[3] + C.CH)
                       for o in placed if o[4] != q), (q, inst)
            placed.append(b + (q,))
            path = f"u_gunit.g_l1f[{q}].u_l1f.{inst}"
            row = dict(inst=path, module=mod, physical_inst=f"u_bound.u_u_gunit_g_l1f_{q}_u_l1f.{inst}",
                       physical_master=mod, origin_um=[x, y], outline_um=[BW, h], orient="R0",
                       track_offset_um=list(TOFF), pins_file=f"{PINS}/{mod}.json", obs_max="M5", reset_net="rst_n",
                       cells=CELLS[mod], cells_basis=CELLS_BASIS, note=ID)
            row["lef"] = f"{VIEW[mod]}/{mod}.lef" if mod in VIEW else BF_LEF
            rows.append(row)
            clk = next(p for p in tabs[mod]["pins"] if p["name"] == "clk")
            taps.append(dict(name=f"{path}.clk", kind="core", xy=[round(x + clk["x"], 3), round(y + clk["y"], 3)],
                             insertion_ps=tt, insertion_ff_ps=ff,
                             budget_owner=f"parent_budget ESTIMATE pin_register_mean {VIEW['dsdv_gunit_l1f_ba0']}/insertion.json "
                                          "(10-22 old-rule routed ba0; re-measure from each band's own kit)",
                             note=f"{ID}: early core tap at the band clk pin"))
    t["hard_cores"] += rows
    t["clock"]["taps"] += taps
    t["note"] = t.get("note", "") + f" | {ID}: 4 soft l1f fronts -> 12 nested hard band cores (ba0/bf/ba1 x 4)"
    Path(dst).write_text(splice(text, json.loads(text)["partition_types"][TYPE], t))
    assert json.loads(Path(dst).read_text()) == plan, "text splice differs from the edited plan"
    step2 = resolve_infra(dst, sidecar)

    # count dry run: core modules / instances / types before -> after
    before = json.loads(text)["partition_types"]
    def census(pt):
        mods = {}
        for tn, tt_ in pt.items():
            for c in tt_.get("hard_cores", []):
                mods.setdefault(c["module"], []).append(tn)
        return mods
    mb, ma = census(before), census(plan["partition_types"])
    new = sorted(set(ma) - set(mb))
    rep = dict(schema="opentallas.s81.delta_gunit_l1f_band.v1", id=ID, type=TYPE,
               types_before=len(before), types_after=len(plan["partition_types"]),
               core_modules_before=len(mb), core_modules_after=len(ma), new_core_modules=new,
               removed_core_modules=sorted(set(mb) - set(ma)),
               new_core_instances=len(rows), removed_contents=[c["inst"] for c in sram], taps_added=len(taps),
               cells=dict(CELLS, parent_glue_est=12000, basis=CELLS_BASIS),
               count_effect=("+3 core units to sign (ba0, bf, ba1; each signed once, used 4x in gunit__t1); "
                             "gunit__t1 stays 1 type with a new block; no other type or core changes"),
               pins={m: len(j["pins"]) for m, j in tabs.items()},
               stacks=[dict(front=q, origin_um=[sx, sy], size_um=[BW, STACK_H]) for q, (sx, sy) in enumerate(STACKS)])
    rep["step2"] = step2
    plan = json.loads(Path(dst).read_text())
    other = [tn for tn in plan["partition_types"] if tn != TYPE and plan["partition_types"][tn] != before[tn]]
    assert not other, other
    rep["other_types_changed"] = other
    if rep_path:
        Path(rep_path).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
