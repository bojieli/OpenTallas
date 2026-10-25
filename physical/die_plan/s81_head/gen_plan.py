#!/usr/bin/env python3
"""S81 release head die plan (lane S81-HEAD, 2026-10-24): top-down die_plan.json from tools/s81_head_die_model.py.

    python3 physical/die_plan/s81_head/gen_plan.py            # writes die_plan.json next to this file
    python3 tools/die_plan/check.py physical/die_plan/s81_head/die_plan.json --out physical/die_plan/s81_head [--completeness]

Floorplan (die frame, y up; every number from model()["floorplan"]):
  - N / S SerDes rows: 6 SerDes partitions each (= the layer die's 2885.76 x 1226.88 slot, ot_pdie_serdes), N: WN2 WN1
    WN0 WN3 EN0 EN1, S: WS1 WS0 HOST0 HOST1 ES0 ES1 (rack connections_s81.csv names);
  - N / S link rows: 12 layer-die frames (1442.88 x 1226.88) each: the stage-circuit endpoint lep_0N (the layer
    die's s_0N_LP content) and the ctl under WN0 / WN3, 3 TP4-mesh endpoints, the host endpoint, ft station frames;
  - tile array: 6 row-pairs x (W + E chain) x 22 tiles (11 out on the upper row, a turn partition, 11 back on the lower
    row) around a spine column of one node a row-pair; the ctl sits on top of the spine (level 0).
Geometry is declared on a few anchor types (SerDes, tile, spine, turn, station frames, mesh endpoint) and derived for
the partner of every port through the instance transforms; a replicated type that would need two pin tables raises.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import s81_head_die_model as M  # noqa: E402
import schema as S  # noqa: E402

G = 8.64
REACH = 364.5            # PLAN-TOOL5 reach on M4-M7 (405 x 0.9): every station hop <= this
HL, VL = ["M4", "M6"], ["M5", "M7"]
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def r6(x):
    return round(x, 6)


def lat(x):
    return round(round(x / G) * G, 4)


# ------------------------------------------------------------------------------------------------ model -> geometry
MD = M.model()
FP = MD["floorplan"]
W, H = FP["outline_um"]
SEAL = M.SEAL
SW, SH = FP["serdes"]["slot_um"]
FW, FH = FP["link_row"]["frame_um"]
TW, TH = [lat(v) for v in FP["tiles"]["tile_um"]]
NH = FP["tiles"]["per_half_row"]
RP = FP["tiles"]["rowpairs"]
SPW = lat(FP["spine"]["width_um"])
TURNW = lat(FP["turn_um"][0])
Y_SS, Y_SL = SEAL, SEAL + SH
Y_T0 = SEAL + SH + FH
Y_NL = Y_T0 + RP * 2 * TH
Y_NS = Y_NL + FH
assert abs(Y_NS + SH + SEAL - H) < 1e-6, (Y_NS, H)
X_SP = SEAL + TURNW + NH * TW                  # spine column x0
assert abs(X_SP + SPW + NH * TW + TURNW + SEAL - W) < 1e-6


def fx(k):
    return lat(SEAL + k * FW)


def sx(s):
    return lat(SEAL + s * SW)


# ------------------------------------------------------------------------------------------------ plan containers
types, parts, ports, lanes = {}, [], [], []
geo = {}                 # (type, bus) -> (type face, [lo, hi], layers, order)   (bus = name or slot_i / slot_o)
bus_def = {}             # (type, bus) -> dict(dir, width, kind, leaf)
slot_def = {}            # (type, slot) -> dict(width, stations)


def T(name, module, outline, cells, contents=None, note="", **kw):
    w, h = outline
    types[name] = dict(module=module, outline_um=[lat(w), lat(h)], hard=False, cells=int(cells),
                       clock={"tap_um": [lat(w / 2), lat(h / 2)], "layer": "M9", "insertion_ps": 250},
                       reset={"sync_stages": 2}, contents=contents or [], note=note, **kw)


def BUS(t, name, d, width, leaf=None, kind="data"):
    bus_def[(t, name)] = dict(name=name, dir=d, width=width, kind=kind, leaf=leaf or f"u_core.{name}")


def SLOT(t, name, width, stations):
    slot_def[(t, name)] = dict(name=name, width=width, stations=stations)


def P(name, t, x, y, o="R0"):
    parts.append(dict(name=name, type=t, origin_um=[lat(x), lat(y)], orient=o))


def part(name):
    return next(p for p in parts if p["name"] == name)


def width_of(t, bus):
    if (t, bus) in bus_def:
        return bus_def[(t, bus)]["width"]
    return slot_def[(t, bus[:-2])]["width"]


def seed(t, bus, face, lo, layers=None, hi=None, order="lsb_low", per_um=2.5):
    lays = layers or (HL if face in "EW" else VL)
    w = width_of(t, bus) + 1
    if hi is None:
        hi = S.window_for(lo, w, lays, per_um=per_um)
    hi = odd_tracks(lo, hi, w, lays)
    geo[(t, bus)] = (face, [r6(lo), r6(hi)], lays, order)
    return hi


LAYERS = {L["name"]: L for L in S.ASAP7_LAYERS}


def odd_tracks(lo, hi, pins, lays):
    """grow hi until every layer with an odd pin count has an odd usable-track count in [lo, hi]: the even-spread pick
    is then mirror-symmetric (schema.spread), so MX / MY copies of a type keep one pin table."""
    for _ in range(2000):
        ok = True
        for i, ln in enumerate(lays):
            n = len(range(i, pins, len(lays)))
            if n % 2 and S.usable_tracks(LAYERS[ln], ln, lo, hi) % 2 == 0:
                ok = False
        if ok:
            return round(hi, 4)
        hi += 0.016
    raise SystemExit(f"no odd-track window from {lo}")


def win_hi(t, bus, lo, face):
    lays = HL if face in "EW" else VL
    return odd_tracks(lo, S.window_for(lo, width_of(t, bus) + 1, lays, per_um=4.0), width_of(t, bus) + 1, lays)


# transforms (schema.Plan conventions)
def tface(p, df):
    o = p["orient"]
    if o in ("MX", "R180") and df in "NS":
        return OPP[df]
    if o in ("MY", "R180") and df in "EW":
        return OPP[df]
    return df


def to_die(p, g):
    tf, (a, b), lays, order = g
    w, h = types[p["type"]]["outline_um"]
    o = p["orient"]
    df = tface(p, tf)
    if tf in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    if flip:
        a, b = ext - b, ext - a
        order = "lsb_high" if order == "lsb_low" else "lsb_low"
    return df, [r6(base + a), r6(base + b)], list(lays), order


def to_type(p, dg):
    df, (a, b), lays, order = dg
    w, h = types[p["type"]]["outline_um"]
    o = p["orient"]
    tf = tface(p, df)
    if tf in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    a, b = a - base, b - base
    if flip:
        a, b = ext - b, ext - a
        order = "lsb_high" if order == "lsb_low" else "lsb_low"
    return tf, [r6(a), r6(b)], list(lays), order


def PORT(pid, sp, sb, dp, db, kind="data"):
    t = part(sp)["type"]
    ports.append(dict(id=pid, src=dict(part=sp, bus=sb), dst=dict(part=dp, bus=db), width=width_of(t, sb), kind=kind))
    return pid


def PATH(lid, hops, param=None):
    """hops = [(part, out bus), (part, slot), ..., (part, in bus)] -> ports + one lane."""
    ids = []
    for k in range(len(hops) - 1):
        (a, ab), (b, bb) = hops[k], hops[k + 1]
        sb = ab if k == 0 else ab + "_o"
        db = bb if k == len(hops) - 2 else bb + "_i"
        ids.append(PORT(f"{lid}__{k}", a, sb, b, db))
    lane = dict(id=lid, ports=ids)
    if param:
        lane["param"] = param
    lanes.append(lane)


def solve():
    changed = True
    while changed:
        changed = False
        for pr in ports:
            sp, dp = part(pr["src"]["part"]), part(pr["dst"]["part"])
            ks, kd = (sp["type"], pr["src"]["bus"]), (dp["type"], pr["dst"]["bus"])
            gs, gd = geo.get(ks), geo.get(kd)
            if gs:
                df, win, lays, order = to_die(sp, gs)
                want = to_type(dp, (OPP[df], win, lays, order))
                if gd is None:
                    geo[kd] = want
                    changed = True
                elif [gd[0], gd[1], gd[2], gd[3]] != [want[0], want[1], want[2], want[3]]:
                    raise SystemExit(f"geometry conflict on {pr['id']}: dst {kd} has {gd}, src implies {want}")
            elif gd:
                df, win, lays, order = to_die(dp, gd)
                geo[ks] = to_type(sp, (OPP[df], win, lays, order))
                changed = True
    missing = [pr["id"] for pr in ports if (part(pr["src"]["part"])["type"], pr["src"]["bus"]) not in geo]
    if missing:
        raise SystemExit(f"ports without geometry: {missing[:10]} ({len(missing)})")


def stations(t, sl):
    g_i, g_o = geo[(t, sl + "_i")], geo[(t, sl + "_o")]
    w, h = types[t]["outline_um"]

    def pt(g):
        f, (a, b), _, _ = g
        c = (a + b) / 2
        return {"W": (0, c), "E": (w, c), "S": (c, 0), "N": (c, h)}[f]
    (x0, y0), (x1, y1) = pt(g_i), pt(g_o)
    d = abs(x1 - x0) + abs(y1 - y0)
    return max(1, math.ceil(d / (REACH - 20)) - 1)


# =================================================================================================== types
TILE_GLUE = M.TILE_GLUE_CELLS
EA, EB = M.ELEM_VIEW["A"], M.ELEM_VIEW["B"]
SLOT_E = M.ELEM_SLOT


def core(inst, view, cells, x, y, um, orient="R0"):
    v = M.ELEM_VIEW[view[-1]]
    cv = f"ot_s81hd_{view}_cv"
    # pins sit on the 0.048 M4 / M5 tracks (offset 0.024) at a 0.012 core shift in R0; a mirrored axis puts pin p at
    # size - p, so its shift is (0.036 - size) mod 0.048 (elemA 317.672: 0.028)
    def sh(mirrored):
        return round((0.036 - um) % 0.048, 4) if mirrored else 0.012
    track = [sh(orient in ("MY", "R180")), sh(orient in ("MX", "R180"))]
    # 10-24: the rebuilt element views (tools/s81_head/hd_elemA_rebuild.py, SIGNED kits) live in cores/views_rb and
    # replace the legacy closed views once present (same pins; 0.192 clk terminal; +1 output stage, reset relay)
    vd = "views_rb" if (ROOT / f"physical/die_plan/s81_head/cores/views_rb/{cv}/{cv}.lef").exists() else "views"
    return dict(inst=inst, module=cv, origin_um=[lat(x), lat(y)], outline_um=[um, um], orient=orient,
                track_offset_um=track, pins_file=f"cores/{view}_pins.json",
                lef=f"physical/die_plan/s81_head/cores/{vd}/{cv}/{cv}.lef",
                lib=f"physical/die_plan/s81_head/cores/{vd}/{cv}/{cv}_tt.lib",
                note=f"{cells} cells ({v['cells_basis']}); CLOSED SS view {v['job']} (SS +{v['ss_ps']} / FF "
                     f"+{v['ff_ps']} ps; ot_dsrom_head_elem IOREG 1 SAFE 1 CUT 0x1ff SPLIT9 1), renamed {cv} "
                     "(tools/s81_head/hd_cv_views.py, names only). 10-24: the tile is rebased on this parameter point "
                     "(ot_s81hd_tile CUT 0x1ff / SPLIT9 1 / CV 1); ot_s81hd_elem == the closed RTL there "
                     "(tools/s81_head/hd_elem_eq.sh EQ_BENCH_PASS A and B)")


CVA, CVB = "u_core.u_b.g_cv.u_eA", "u_core.u_b.g_cvb.u_eB"     # ot_s81hd_bundle CV = 1 instance paths
# 10-24 G3 floorplan review (die_plan.png + the r2 global placement, results/geom_review s81_head_tile_r2): the 691.2 tile
# put elemB's W face and the bus-i face window in one 8.64-um sliver, the A S-face x pins (130 each) on the tile edge
# and the 20k skew-line flops in one 27.9-um channel.  Now (tile 708.48 x 1036.8):
#   A block: columns at x 17.28 / 371.52 (edge strips 17.28 / 19.29, centre column 36.57), rows at y 8.64 / 380.16
#   (centre row channel 53.85); orientation puts every A S face (130 x pins) on the centre row channel and every A
#   E face (controls + 45 x) on the centre column: bottom-left MX, bottom-right R180, top-left R0, top-right MY.
#   elemB centred in the top band (x 216.0, y 734.4): W region 0..216 for the bus-i face flops / BST / skew lines,
#   E region 493.7..708.5 for the bus-o face flops / merge; B's W-face x (128) faces the skew lines.
AX0, AX1, AY0, AY1 = 2 * G, 43 * G, G, 44 * G
tile_cores = [core(CVA + "0", "elemA", EA["cells"], AX0, AY0, EA["um"], "MX"),
              core(CVA + "1", "elemA", EA["cells"], AX1, AY0, EA["um"], "R180"),
              core(CVA + "2", "elemA", EA["cells"], AX0, AY1, EA["um"], "R0"),
              core(CVA + "3", "elemA", EA["cells"], AX1, AY1, EA["um"], "MY"),
              core(CVB, "elemB", EB["cells"], 25 * G, 85 * G, EB["um"], "R0")]
# CV 1: the 5 elements are the closed views' black boxes (ot_s81hd_elem_cv_bb.v); the element RTL + ROM black box are
# read only so the parser can resolve the bundle's untaken CV 0 branch (pruned by hierarchy -top)
HD_SRC = ["rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_fadd.sv", "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_dsrom_bmul3.sv",
          "physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v",
          "rtl/hdc/ot_hdc_delay.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb.v", "rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv",
          "rtl/dsrom_sys/s81_head/ot_s81hd_bundle.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv",
          "rtl/dsrom_sys/s81_head/ot_s81hd_strap.sv"]
T("hd_tile", "ot_s81hd_tile_p", (TW, TH), MD["tile"]["cells"],
  contents=[dict(inst="u_core", module="ot_s81hd_tile", status="rework", kit="physical/ref_tile/s81hd_tile_m",
                 cells=TILE_GLUE, params={"CV": "1", "A_INPUT_STAGES": "1", "MERGE_HOP": "2", "CMP_STAGES": "3",
                         "A_SKEW_LINES": "2", "BD_HOPS": "2"},
                 bind={"ck": "clk", "rst_n": "rst_n", "row0": "net:row0", "ten": "net:ten"},
                 note="tile glue: bundle BST / skew lines, 2-stage x pass, chain-best merge; elements = the 5 closed "
                      "views (CV 1, CUT 0x1ff / SPLIT9 1)"),
            dict(inst="u_strap", module="ot_s81hd_strap", status="new", cells=18, params={"ROW0": "0", "TEN": "1"},
                 bind={"row0": "net:row0", "ten": "net:ten"},
                 note="per-instance position straps row0 / ten = 18 mask-programmed TIEHI / TIELO cells (same footprint, "
                      "the ROM-code mask-variant class); the kit is built at ROW0 0 / TEN 1, instance k differs only by "
                      "the tie masters (no die ports)")],
  nets=[dict(name="row0", width=17), dict(name="ten", width=1)],
  sources=HD_SRC,
  note=f"LM-head tile = 1 bundle (128 vocab rows, 10 ROM4096) on bus B 565; {MD['tile']['cells_basis']}",
  hard_cores=tile_cores)
BUS("hd_tile", "i", "in", 565, "u_core.i")
BUS("hd_tile", "o", "out", 565, "u_core.o")

T("hd_turn_a", "ot_s81hd_turn_a", (TURNW, TH), 2_000, note="row-pair chain U-turn, out-row half (ft stations only)")
SLOT("hd_turn_a", "t", 565, 0)
T("hd_turn_b", "ot_s81hd_turn_b", (TURNW, TH), 2_000, note="row-pair chain U-turn, back-row half (ft stations only)")
SLOT("hd_turn_b", "t", 565, 0)

SPINE_FT = [("hu", 276), ("hd", 276), ("au", 64), ("ad", 64), ("bu", 64), ("bd", 64)]   # host / mesh0S / mesh7S
for tn, end in (("hd_spn", False), ("hd_spn_end", True)):
    T(tn, "ot_s81hd_spn" + ("_end" if end else ""), (SPW, 2 * TH), 60_000,
      contents=[dict(inst="u_spo", module="ot_s81hd_spo", status="reuse", kit="physical/ref_tile/s81hd_spo_m",
                     note="CLOSED s81hd_spo_m-6398c44bc (TT +19.69 / FF +40.87; historical SS sensitivity -70.45; requires uniform TT setup/FF hold signoff)"),
                dict(inst="u_spr", module="ot_s81hd_spr", status="reuse", kit="physical/ref_tile/s81hd_spr_m4",
                     note="CLOSED s81hd_spr_m4-bb8dd356c")],
      note="spine node of one row-pair: x/go down + W/E chain heads (upper row); chain tails + level below merged "
           "(capture-all-then-fire argmax) up; ft for the S-side host / mesh lanes" + (" (bottom: no level below)" if end else ""))
    BUS(tn, "x_i", "in", 565, "u_spo.i")
    BUS(tn, "b_o", "out", 565, "u_spr.o")
    BUS(tn, "xw_o", "out", 565, "u_spo.ow")
    BUS(tn, "xe_o", "out", 565, "u_spo.oe")
    BUS(tn, "bw_i", "in", 565, "u_spr.iw")
    BUS(tn, "be_i", "in", 565, "u_spr.ie")
    if not end:
        BUS(tn, "x_o", "out", 565, "u_spo.o")
        BUS(tn, "b_i", "in", 565, "u_spr.i")
    for s_, wd in SPINE_FT:
        SLOT(tn, s_, wd, 0)

T("hd_serdes", "ot_s81hd_serdes", (SW, SH), 0,
  contents=[dict(inst="u_phy", module="ot_pdie_serdes", status="reuse",
                 note="same PHY model, slot and bump field as the layer die's serdes partitions")],
  note="SerDes partition: 112G PHY (6 lanes, 512-b TX flit / 514-b RX {st, rx}) + boundary flops; PHY on the separate "
       "VDDPHY domain (die.pg.domains, OWNER 10-24 decision 7) with dedicated bump rows over its window")
BUS("hd_serdes", "coll_i0", "in", 512, "u_phy.tx")
BUS("hd_serdes", "coll_o0", "out", 514, "u_phy.rx")

# station frames (canonical = N link row, R0); u = SerDes -> endpoint (514), d = endpoint -> SerDes (512)
T("hd_st_turn", "ot_s81hd_st_turn", (FW, FH), 6_000, note="ft frame: one SerDes lane pair turning from the SerDes face")
SLOT("hd_st_turn", "u", 514, 0)
SLOT("hd_st_turn", "d", 512, 0)
T("hd_st_str", "ot_s81hd_st_str", (FW, FH), 6_000, note="ft frame: one SerDes lane pair straight through")
SLOT("hd_st_str", "u", 514, 0)
SLOT("hd_st_str", "d", 512, 0)
T("hd_st_n3", "ot_s81hd_st_n3", (FW, FH), 12_000, note="ft frame: WN2 pair straight + WN1 pair turning")
for s_, wd in (("u2", 514), ("d2", 512), ("u1", 514), ("d1", 512)):
    SLOT("hd_st_n3", s_, wd, 0)
T("hd_st_n4", "ot_s81hd_st_n4", (FW, FH), 12_000, note="ft frame: WN2 + WN1 pairs straight")
for s_, wd in (("u2", 514), ("d2", 512), ("u1", 514), ("d1", 512)):
    SLOT("hd_st_n4", s_, wd, 0)
T("hd_st_m", "ot_s81hd_st_m", (FW, FH), 2_000, note="ft frame: one 64-b mesh core lane pair (tx W->E, rx E->W)")
SLOT("hd_st_m", "tx", 64, 0)
SLOT("hd_st_m", "rx", 64, 0)
T("hd_st_k5", "ot_s81hd_st_k5", (FW, FH), 8_000, note="ft frame (S k5): HOST0 pair turning + mesh0S core pair straight")
for s_, wd in (("u", 514), ("d", 512), ("tx", 64), ("rx", 64)):
    SLOT("hd_st_k5", s_, wd, 0)

T("hd_mesh", "ot_s81hd_mesh_ep", (FW, FH), MD["blocks"]["mesh_ep"]["cells"],
  contents=[dict(inst="u_core", module="ot_s81hd_mesh_ep", status="new",
                 note="2 x dsfd_coll_lane_w_safe8_ntf (closed lane sub-children s81hd_lsc_*) + 64-b static adapter")],
  note="TP4 mesh endpoint of one SerDes pair (rank argmax all-gather)")
for k in ("a", "b"):
    BUS("hd_mesh", f"coll_i{k}", "in", 514)
    BUS("hd_mesh", f"coll_o{k}", "out", 512)
BUS("hd_mesh", "m_tx_i", "in", 64)
BUS("hd_mesh", "m_rx_o", "out", 64)

T("hd_lep0N", "ot_s81hd_lep0N", (FW, FH), MD["blocks"]["lep_0N"]["cells"],
  contents=[dict(inst="u_core", module="dsdv_slice_lepw_mu.LP", status="reuse",
                 note="the layer die's s_0N_LP content: the NEXT / PREV stage-circuit protocol is identical")],
  note="stage-circuit endpoint: pair A (WN0/1) TX to the next head group / token return, pair B (WN2/3) RX")
for k in range(4):
    BUS("hd_lep0N", f"coll_i{k}", "in", 514)
    BUS("hd_lep0N", f"coll_o{k}", "out", 512)
BUS("hd_lep0N", "lepk_i0", "in", 1104)
BUS("hd_lep0N", "lepk_o0", "out", 1104)
BUS("hd_lep0N", "lepf_i0", "in", 1, kind="ctl")
BUS("hd_lep0N", "unit_i0", "in", 45, kind="ctl")
BUS("hd_lep0N", "ctrl_o0", "out", 32, kind="ctl")

T("hd_ctl", "ot_s81hd_ctl", (FW, FH), MD["blocks"]["ctl"]["cells"],
  contents=[dict(inst="u_core", module="ot_s81hd_ctl", status="rework",
                 note=MD["blocks"]["ctl"]["content"] + "; " + MD["blocks"]["ctl"]["cells_basis"])],
  note="head controller at the spine root (level 0)")
for b, d, wd in (("lepk_i0", "in", 1104), ("lepk_o0", "out", 1104), ("lepf_o0", "out", 1), ("unit_o0", "out", 45),
                 ("ctrl_i0", "in", 32), ("x_o", "out", 565), ("b_i", "in", 565), ("h_tx_o", "out", 276),
                 ("h_rx_i", "in", 276), ("a_tx_o", "out", 64), ("a_rx_i", "in", 64), ("b7_tx_o", "out", 64),
                 ("b7_rx_i", "in", 64), ("n_tx_o", "out", 64), ("n_rx_i", "in", 64)):
    BUS("hd_ctl", b, d, wd, kind="ctl" if wd <= 64 and b.startswith(("lepf", "unit", "ctrl")) else "data")
SLOT("hd_ctl", "w3u", 514, 0)
SLOT("hd_ctl", "w3d", 512, 0)

T("hd_host", "ot_s81hd_host_ep", (FW, FH), MD["blocks"]["host_ep"]["cells"],
  contents=[dict(inst="u_core", module="ot_s81hd_host_ep", status="new",
                 note="2 x dsfd_coll_lane_w_safe8_ntf + dsdv_hostb_stage_hbc host frame endpoint (S81.HOST)")],
  note="host link endpoint (HOST0/1); ft for the two S-side mesh core lane pairs up to the spine")
for k in ("0", "1"):
    BUS("hd_host", f"coll_i{k}", "in", 514)
    BUS("hd_host", f"coll_o{k}", "out", 512)
BUS("hd_host", "h_tx_i", "in", 276)
BUS("hd_host", "h_rx_o", "out", 276)
for s_, wd in (("au", 64), ("ad", 64), ("bu", 64), ("bd", 64)):
    SLOT("hd_host", s_, wd, 0)

# =================================================================================================== partitions
NS = FP["serdes"]["N"]
SS_ = FP["serdes"]["S"]
for s, nm in enumerate(NS):
    P(f"lk_{nm}", "hd_serdes", sx(s), Y_NS, "R0" if s < 3 else "MY")
for s, nm in enumerate(SS_):
    P(f"lk_{nm}", "hd_serdes", sx(s), Y_SS, "MX" if s < 3 else "R180")
N_ROW = {1: ("nst1", "hd_st_turn", "R0"), 2: ("nst2", "hd_st_str", "R0"), 3: ("nst3", "hd_st_n3", "R0"),
         4: ("nst4", "hd_st_n4", "R0"), 5: ("lep0N", "hd_lep0N", "R0"), 6: ("ctl", "hd_ctl", "R0"),
         7: ("nst7", "hd_st_m", "R0"), 8: ("mesh7N", "hd_mesh", "MY"), 9: ("nst9", "hd_st_str", "MY"),
         10: ("nst10", "hd_st_turn", "MY")}
S_ROW = {1: ("sst1", "hd_st_turn", "MX"), 2: ("sst2", "hd_st_str", "MX"), 3: ("mesh0S", "hd_mesh", "MX"),
         4: ("sst4", "hd_st_m", "R180"), 5: ("sst5", "hd_st_k5", "R0"), 6: ("host", "hd_host", "R0"),
         7: ("sst7", "hd_st_m", "MX"), 8: ("mesh7S", "hd_mesh", "R180"), 9: ("sst9", "hd_st_str", "R180"),
         10: ("sst10", "hd_st_turn", "R180")}
for k, (nm, t, o) in N_ROW.items():
    P(nm, t, fx(k), Y_NL, o)
for k, (nm, t, o) in S_ROW.items():
    P(nm, t, fx(k), Y_SL, o)
X_E0 = X_SP + SPW
for rp in range(RP):
    yb = Y_NL - (rp + 1) * 2 * TH          # row-pair bottom; upper row = out row
    P(f"sp{rp}", "hd_spn_end" if rp == RP - 1 else "hd_spn", X_SP, yb)
    P(f"turnW{rp}a", "hd_turn_a", SEAL, yb + TH, "MY")
    P(f"turnW{rp}b", "hd_turn_b", SEAL, yb, "MY")
    P(f"turnE{rp}a", "hd_turn_a", X_E0 + NH * TW, yb + TH)
    P(f"turnE{rp}b", "hd_turn_b", X_E0 + NH * TW, yb)
    for j in range(NH):
        P(f"tE{rp}o{j}", "hd_tile", X_E0 + j * TW, yb + TH, "R0")          # out: W -> E
        P(f"tE{rp}b{j}", "hd_tile", X_E0 + j * TW, yb, "MY")               # back: E -> W
        P(f"tW{rp}o{j}", "hd_tile", X_SP - (j + 1) * TW, yb + TH, "MY")    # out: E -> W
        P(f"tW{rp}b{j}", "hd_tile", X_SP - (j + 1) * TW, yb, "R0")         # back: W -> E

# =================================================================================================== seeds
TWIN = (SLOT_E + G, SLOT_E + G + 300.0)   # tile chain window (type frame y): 10-24 lowered from the upper third (700..1000) to 354..654 = the A centre row channel + top A row (hd_tile preview review: x_q -> A x pins 600-700 um)
seed("hd_tile", "o", "E", TWIN[0], hi=TWIN[1])
seed("hd_tile", "i", "W", TWIN[0], hi=TWIN[1])
seed("hd_turn_a", "t_i", "W", TWIN[0], hi=TWIN[1])
seed("hd_turn_a", "t_o", "S", 4.32, hi=TURNW - 4.32)
seed("hd_turn_b", "t_o", "W", TWIN[0], hi=TWIN[1])
for tn in ("hd_spn", "hd_spn_end"):
    seed(tn, "xw_o", "W", TH + TWIN[0], hi=TH + TWIN[1])
    seed(tn, "xe_o", "E", TH + TWIN[0], hi=TH + TWIN[1])
    seed(tn, "bw_i", "W", TWIN[0], hi=TWIN[1])
    seed(tn, "be_i", "E", TWIN[0], hi=TWIN[1])
    # N / S faces: every spine N-S bus in the ctl half of the column (type x > die x of the lep0N | ctl seam)
    x = (fx(6) - X_SP) + 24.0
    for b_n, b_s in [("x_i", "x_o"), ("b_o", "b_i")] + [(s_ + ("_i" if s_[1] == "d" else "_o"),
                                                         s_ + ("_o" if s_[1] == "d" else "_i")) for s_, _ in SPINE_FT]:
        hi = win_hi(tn, b_n, x, "N")
        seed(tn, b_n, "N", x, hi=hi)
        if (tn, b_s) in bus_def or (tn, b_s[:-2]) in slot_def:
            seed(tn, b_s, "S", x, hi=hi)
        x = hi + 8.0
    assert x < SPW - 20, x
# SerDes: coll pins on the S face (type frame) over the right-hand frame
x = FW + 160.0
x = seed("hd_serdes", "coll_o0", "S", x) + 16.0
seed("hd_serdes", "coll_i0", "S", x)
# station frames: exit windows on the E face (lower half of the frame: y1 for the straight pair, y2 for the second)
Y1, Y2 = 120.0, 640.0


def pair_seed(t, u, d, face, y0):
    hi = seed(t, u, face, y0)
    seed(t, d, face, hi + 16.0)


pair_seed("hd_st_turn", "u_o", "d_i", "E", Y1)
pair_seed("hd_st_str", "u_o", "d_i", "E", Y1)
pair_seed("hd_st_n3", "u1_o", "d1_i", "E", Y2)
pair_seed("hd_st_n4", "u1_o", "d1_i", "E", Y2)
pair_seed("hd_st_n4", "u2_o", "d2_i", "E", Y1)
YM = 380.0
pair_seed("hd_st_m", "tx_o", "rx_i", "E", YM)
y = 10.0
for b in ("lepk_o0", "lepk_i0", "coll_o3", "coll_i3"):
    y = seed("hd_lep0N", b, "E", y, per_um=4.5, order="lsb_high" if b.endswith("3") else "lsb_low") + 10.0
for b in ("lepf_i0", "unit_i0", "ctrl_o0"):
    y = seed("hd_lep0N", b, "E", y, hi=y + 20.0) + 10.0
assert y < FH - 20
pair_seed("hd_st_n3", "u2_o", "d2_i", "E", Y1)
pair_seed("hd_st_k5", "u_o", "d_i", "E", Y1)
# mesh0S core pair crosses k5 (R0) between two R180 / MX-mirrored neighbours: the MX image of hd_st_m's E windows
for b_k5, b_m in (("tx_i", "tx_o"), ("rx_o", "rx_i")):
    f_, (a_, b_), l_, _ = geo[("hd_st_m", b_m)]
    geo[("hd_st_k5", b_k5)] = (f_, [r6(FH - b_), r6(FH - a_)], l_, "lsb_high")
seed("hd_ctl", "n_tx_o", "E", YM)
seed("hd_ctl", "n_rx_i", "E", YM + 60.0)

# =================================================================================================== lanes
# chains (tile -> tile 1-port lanes; turn = 2-port lane)
for rp in range(RP):
    sp = f"sp{rp}"
    for side in ("E", "W"):
        out = [f"t{side}{rp}o{j}" for j in range(NH)]
        back = [f"t{side}{rp}b{j}" for j in reversed(range(NH))]
        PATH(f"ch{side}{rp}_h", [(sp, f"x{side.lower()}_o"), (out[0], "i")])
        for j in range(NH - 1):
            PATH(f"ch{side}{rp}_o{j}", [(out[j], "o"), (out[j + 1], "i")])
        PATH(f"ch{side}{rp}_t", [(out[-1], "o"), (f"turn{side}{rp}a", "t"), (f"turn{side}{rp}b", "t"), (back[0], "i")])
        for j in range(NH - 1):
            PATH(f"ch{side}{rp}_b{j}", [(back[j], "o"), (back[j + 1], "i")])
        PATH(f"ch{side}{rp}_r", [(back[-1], "o"), (sp, f"b{side.lower()}_i")])
# spine
PATH("sp_x0", [("ctl", "x_o"), ("sp0", "x_i")], "LAT_HD_SPX0")
PATH("sp_b0", [("sp0", "b_o"), ("ctl", "b_i")], "LAT_HD_SPB0")
for rp in range(RP - 1):
    PATH(f"sp_x{rp + 1}", [(f"sp{rp}", "x_o"), (f"sp{rp + 1}", "x_i")])
    PATH(f"sp_b{rp + 1}", [(f"sp{rp + 1}", "b_o"), (f"sp{rp}", "b_i")])
SPX = [f"sp{rp}" for rp in range(RP)]
# host + S-side mesh core lanes through the spine column
PATH("host_tx", [("ctl", "h_tx_o")] + [(s_, "hd") for s_ in SPX] + [("host", "h_tx_i")], "LAT_HD_HOST_TX")
PATH("host_rx", [("host", "h_rx_o")] + [(s_, "hu") for s_ in reversed(SPX)] + [("ctl", "h_rx_i")], "LAT_HD_HOST_RX")
PATH("m0S_tx", [("ctl", "a_tx_o")] + [(s_, "ad") for s_ in SPX] + [("host", "ad"), ("sst5", "tx"), ("sst4", "tx"),
                                                                    ("mesh0S", "m_tx_i")], "LAT_HD_M0S_TX")
PATH("m0S_rx", [("mesh0S", "m_rx_o"), ("sst4", "rx"), ("sst5", "rx"), ("host", "au")] +
     [(s_, "au") for s_ in reversed(SPX)] + [("ctl", "a_rx_i")], "LAT_HD_M0S_RX")
PATH("m7S_tx", [("ctl", "b7_tx_o")] + [(s_, "bd") for s_ in SPX] + [("host", "bd"), ("sst7", "tx"),
                                                                     ("mesh7S", "m_tx_i")], "LAT_HD_M7S_TX")
PATH("m7S_rx", [("mesh7S", "m_rx_o"), ("sst7", "rx"), ("host", "bu")] + [(s_, "bu") for s_ in reversed(SPX)] +
     [("ctl", "b7_rx_i")], "LAT_HD_M7S_RX")
PATH("m7N_tx", [("ctl", "n_tx_o"), ("nst7", "tx"), ("mesh7N", "m_tx_i")], "LAT_HD_M7N_TX")
PATH("m7N_rx", [("mesh7N", "m_rx_o"), ("nst7", "rx"), ("ctl", "n_rx_i")], "LAT_HD_M7N_RX")
# ctl <-> lep0N (as the layer die's s_0N_C <-> s_0N_LP)
PATH("kd", [("ctl", "lepk_o0"), ("lep0N", "lepk_i0")], "LAT_HD_KD")
PATH("ku", [("lep0N", "lepk_o0"), ("ctl", "lepk_i0")], "LAT_HD_KU")
PATH("lepf", [("ctl", "lepf_o0"), ("lep0N", "lepf_i0")])
PATH("unit_lep", [("ctl", "unit_o0"), ("lep0N", "unit_i0")])
PATH("ctrl_lep", [("lep0N", "ctrl_o0"), ("ctl", "ctrl_i0")])
# stage circuit: WN0 abutted, WN1 / WN2 via N k3 / k4 (+ k1 / k2), WN3 through the ctl
PATH("coll_WN0_u", [("lk_WN0", "coll_o0"), ("lep0N", "coll_i0")])
PATH("coll_WN0_d", [("lep0N", "coll_o0"), ("lk_WN0", "coll_i0")])
PATH("coll_WN1_u", [("lk_WN1", "coll_o0"), ("nst3", "u1"), ("nst4", "u1"), ("lep0N", "coll_i1")])
PATH("coll_WN1_d", [("lep0N", "coll_o1"), ("nst4", "d1"), ("nst3", "d1"), ("lk_WN1", "coll_i0")])
PATH("coll_WN2_u", [("lk_WN2", "coll_o0"), ("nst1", "u"), ("nst2", "u"), ("nst3", "u2"), ("nst4", "u2"),
                    ("lep0N", "coll_i2")])
PATH("coll_WN2_d", [("lep0N", "coll_o2"), ("nst4", "d2"), ("nst3", "d2"), ("nst2", "d"), ("nst1", "d"),
                    ("lk_WN2", "coll_i0")])
PATH("coll_WN3_u", [("lk_WN3", "coll_o0"), ("ctl", "w3u"), ("lep0N", "coll_i3")])
PATH("coll_WN3_d", [("lep0N", "coll_o3"), ("ctl", "w3d"), ("lk_WN3", "coll_i0")])
# TP4 mesh pairs: EN (N k8 + k9/k10), WS (S k3 + k1/k2), ES (S k8 + k9/k10)
for ep, a, b, s_turn, s_str in (("mesh7N", "lk_EN0", "lk_EN1", "nst10", "nst9"),
                                ("mesh0S", "lk_WS0", "lk_WS1", "sst1", "sst2"),
                                ("mesh7S", "lk_ES0", "lk_ES1", "sst10", "sst9")):
    PATH(f"coll_{a[3:]}_u", [(a, "coll_o0"), (ep, "coll_ia")])
    PATH(f"coll_{a[3:]}_d", [(ep, "coll_oa"), (a, "coll_i0")])
    PATH(f"coll_{b[3:]}_u", [(b, "coll_o0"), (s_turn, "u"), (s_str, "u"), (ep, "coll_ib")])
    PATH(f"coll_{b[3:]}_d", [(ep, "coll_ob"), (s_str, "d"), (s_turn, "d"), (b, "coll_i0")])
# host pair: HOST1 abutted to the host endpoint (S k6), HOST0 via S k5
PATH("coll_HOST1_u", [("lk_HOST1", "coll_o0"), ("host", "coll_i1")])
PATH("coll_HOST1_d", [("host", "coll_o1"), ("lk_HOST1", "coll_i0")])
PATH("coll_HOST0_u", [("lk_HOST0", "coll_o0"), ("sst5", "u"), ("host", "coll_i0")])
PATH("coll_HOST0_d", [("host", "coll_o0"), ("sst5", "d"), ("lk_HOST0", "coll_i0")])

solve()

# =================================================================================================== emit
turning = set()
for (t, b), d in bus_def.items():
    g = geo.get((t, b))
    e = dict(d)
    if g:
        e.update(face=g[0], window_um=g[1], layers=g[2], order=g[3])
    types[t].setdefault("buses", []).append(e)


def face_pt(t, b):
    f, (a, c), _, _ = geo[(t, b)]
    w, h = types[t]["outline_um"]
    m = (a + c) / 2
    return {"W": (0.0, m), "E": (w, m), "S": (m, 0.0), "N": (m, h)}[f]


def stations_on(p0, p1, step=REACH - 20):
    """register sites every <= step um along the L route p0 -> (p1.x, p0.y) -> p1 (R3-INTERNAL, FIRM)."""
    (x0, y0), (x1, y1) = p0, p1
    L = abs(x1 - x0) + abs(y1 - y0)
    n = max(0, math.ceil(L / step) - 1)
    out = []
    for k in range(1, n + 1):
        d = L * k / (n + 1)
        if d <= abs(x1 - x0):
            out.append([round(x0 + math.copysign(d, x1 - x0), 3), round(y0, 3)])
        else:
            out.append([round(x1, 3), round(y0 + math.copysign(d - abs(x1 - x0), y1 - y0), 3)])
    return out


# spine node internal register-to-register paths (spo forward / spr merge sit at the N-face centre of the node)
for tn in ("hd_spn", "hd_spn_end"):
    ist = []
    conns = [("x_i", "xw_o"), ("x_i", "xe_o"), ("bw_i", "b_o"), ("be_i", "b_o")]
    if (tn, "x_o") in bus_def:
        conns += [("x_i", "x_o"), ("b_i", "b_o")]
    for a, b in conns:
        p0, p1 = face_pt(tn, a), face_pt(tn, b)
        ist.append(dict(conn=f"bus:{b if a in ('x_i',) else a}", from_um=list(p0), to_um=list(p1),
                        regs_um=stations_on(p0, p1), bits=566, note=f"{a} -> {b} (spo / spr registers at the ends)"))
    types[tn]["internal_stations"] = ist
for (t, s_), d in slot_def.items():
    gi, go = geo[(t, s_ + "_i")], geo[(t, s_ + "_o")]
    e = dict(name=s_, in_face=gi[0], out_face=go[0], width=d["width"], stations=stations(t, s_),
             in_window_um=gi[1], out_window_um=go[1], layers=gi[2], order=gi[3])
    if gi[2] != go[2] or gi[3] != go[3]:   # turning slot (H face <-> V face) or bit-order flip: ports carry geometry
        del e["layers"]
        del e["order"]
        turning.add((t, s_ + "_i"))
        turning.add((t, s_ + "_o"))
    types[t].setdefault("ft_slots", []).append(e)

for pr in ports:
    sp, dp = part(pr["src"]["part"]), part(pr["dst"]["part"])
    if (sp["type"], pr["src"]["bus"]) in turning or (dp["type"], pr["dst"]["bus"]) in turning:
        df, win, lays, order = to_die(sp, geo[(sp["type"], pr["src"]["bus"])])
        pr.update(face=df, window_um=win, layers=lays, order=order)
        for side, pp in (("src", sp), ("dst", dp)):       # the bus side keeps no type geometry either
            k = (pp["type"], pr[side]["bus"])
            if k in bus_def:
                turning.add(k)
for t in types.values():
    pass
channels = [dict(rect_um=[0, 0, W, SEAL], reason="seal ring"), dict(rect_um=[0, H - SEAL, W, H], reason="seal ring"),
            dict(rect_um=[0, SEAL, SEAL, H - SEAL], reason="seal ring"),
            dict(rect_um=[W - SEAL, SEAL, W, H - SEAL], reason="seal ring")]
for y in (Y_SL, Y_NL):
    for k in (0, 11):
        channels.append(dict(rect_um=[fx(k), y, fx(k) + FW, y + FH],
                             reason="reserve frame: no ft crosses it (draft fan-out lanes would land here if the "
                                    "owner restores them; corner bump / ESD keep-out of the corner SerDes)"))

plan = dict(
    schema="opentallas.die_plan.v1",
    note="S81 release head die (S81.HEAD), top-down plan from tools/s81_head_die_model.py (results/uarch/"
         "s81_head_die.json); generator physical/die_plan/s81_head/gen_plan.py. LM head 1/4 vocabulary a die "
         "(253 of 264 tile slots active), argmax spine, ctl at the spine root, stage-circuit endpoint = layer-die "
         "s_0N_LP, 3 TP4 mesh pairs, host pair (S81.HOST). "
         "PDN (OWNER 10-24 decision 7): die.pg.domains = one VDDPHY supply + dedicated bump rows per SerDes "
         "window (12); the core VDD/VSS M8/M9 grid does not feed the PHY. TODO (TRIAL/PDN): head PSM / IR with the "
         "VDDPHY domains. Reset (decision 13): reset.release wavefront (tools/die_plan/reset_tree.py).",
    die=dict(name="s81_head", label="DeepSeek ROM S81 release head die (LM head / argmax / MTP / host)", tech="asap7",
             outline_um=[W, H], period_ps=833, reach_um=405.0, rep_um=450.0, grid_um=G,   # DEC12: 405-um M4-M7 hop
             layer_budget=dict(partition_signal_max="M7", die_layers=["M8", "M9"],
                               # DEC12 (ruling 9.3): M8/M9 = clock spine, reset, PG only (no ft_reserved)
                               die_use=["clock_spine", "pg"]),
             pg=dict(partition_pg_max="M7",
                     grid=[dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"]),
                           dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])],
                     # OWNER DECISION 7: die.pg.domains (VDDPHY per SerDes window) are added below from die.io
                     ),

             channels=channels),
    partition_types=types, partitions=parts, ports=ports, lanes=lanes,
    clock=dict(source=dict(part="@die", bus="clk"), insertion_ps=250, common_latency_ps=250, insertion_tol_ps=40,
               neighbour_skew_ps=80, face_xing="budgeted",
               spine=dict(layers=["M8", "M9"], root_um=[lat(W / 2), lat(H / 2)], topology="htree")),
    # DEC12 batch: OWNER DECISION 13 neighbour wavefront (one root sync per die + registered rst_o relays; reset_tree.py)
    reset=dict(source=dict(part="@die", bus="rst_n"), sync_stages=2, data_reset=False, epoch_bit=True,
               release="wavefront"),
    census={"none": "top-down plan of a new die: no bound as-built head-die netlist in this partitioning (the "
                    "bottom-up H10 die chain used a different block split and FAILED STA); census follows the first "
                    "bind (G3)"},
    budgets=dict(face_pins_per_um=6, face_pin_layers=2, face_window_um=10, pin_track_max=0.6, cut_ratio_max=0.6,
                 cut_step_um=250),
    latency=dict(lanes={}),
)
# OWNER DECISION 7 (2026-10-24, IR over SerDes windows): die.io = the die_io.py windows (die_io.json, written by
# `die_io.py plan --out`), and one separate PHY supply per SerDes window (die.pg.domains, same form as HBM B2m
# physical/die_plan/hbm_arch/b2m.py pg_domains): own net VDDPHY with VSS, dense M8/M9 straps over the window + a one-bump
# guard ring, dedicated power/ground C4 rows (45-um array) over the PHY macro; the 26 SerDes signal sites stay at the
# shoreline edge.  check.py rule pg_domain.  TODO TRIAL/PDN: head PSM / IR with the VDDPHY domains.
import copy  # noqa: E402
_io = json.loads((HERE / "die_io.json").read_text()) if (HERE / "die_io.json").exists() else []
if _io:
    plan["die"]["io"] = _io
    _PHY_GRID = [dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"]),
                 dict(layer="M9", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"])]
    _doms = []
    for w in _io:
        if w.get("iface") != "serdes":
            continue
        x0, y0, x1, y1 = w["rect_um"]
        g = 63.64
        _doms.append(dict(name=f"phy_{w['part']}", nets=["VDDPHY", "VSS"], io=[w["name"]],
                          rect_um=[round(max(0.0, x0 - g), 4), round(max(0.0, y0 - g), 4), round(min(W, x1 + g), 4),
                                   round(min(H, y1 + g), 4)],
                          grid=copy.deepcopy(_PHY_GRID),
                          bumps=dict(rect_um=[x0, y0, x1, y1], pitch_um=45.0, use="power_ground",
                                     note="dedicated VDDPHY/VSS C4 rows over the SerDes macro (45-um array); no signal "
                                          "bumps inside except the window's own 26 SerDes sites"),
                          note="OWNER decision 7 (10-24): separate PHY supply + dedicated bump rows over the SerDes "
                               "window; core VDD grid unchanged around it"))
    plan["die"]["pg"]["domains"] = _doms
from early_core_taps import add as add_early_core_taps
add_early_core_taps(types["hd_tile"], root=ROOT)
# core-latency contract for the REBUILT views (10-24, S81-HEAD): the element was signed with clk source latency -early
# (its kit SDC), so its tap is delivered exactly `early` before the common latency; the lib max_clock_tree_path (max
# over all internal flops, 441 / 435 ps) would over-advance it by ~60 ps and break the boundary timing it was signed
# with.  MANIFEST.json (tools/s81_head/hd_views_rb.py) carries the kit early.  Request to CLOCK filed 10-24 20:5x.
for tp in types["hd_tile"]["clock"].get("taps", []):
    man = ROOT / Path(tp.get("budget_owner", "")).parent / "MANIFEST.json"
    if "/views_rb/" in tp.get("budget_owner", "") and man.is_file():
        mf = json.loads(man.read_text())
        tp["insertion_ps"] = round(250.0 + float(mf["early_core_tap_ps"]), 5)
        tp["note"] = (f"CP2 early core tap; core-latency contract = signed kit early {mf['early_core_tap_ps']:g} ps "
                      f"(views_rb MANIFEST; lib max_clock_tree_path {mf['lib_max_clock_tree_path_ps']['tt']:.1f} TT, info)")
from ft_reach import resize as resize_ft_reach
resize_ft_reach(plan, reach_um=405.0, margin=REACH / 405.0)
S.validate  # noqa: B018  (schema import check)
out = HERE / "die_plan.json"
out.write_text(json.dumps(plan, indent=1) + "\n")
print(f"wrote {out}: {len(types)} types, {len(parts)} partitions, {len(ports)} ports, {len(lanes)} lanes, "
      f"die {W} x {H} um")
