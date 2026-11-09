#!/usr/bin/env python3
"""S81 svc_rs TYPE-LOCAL split plan event (DIE-S81-85 11-09; COORD 08:4x ruling (a)/(b); OWNER 11-09 "yes for growth",
svc_lo only, <= +77.76 um Y).

H8 RT2 form (OT_SVC_H8 + OT_SVC_H8_REUSE_RT2): each svc type keeps the 32 attention hcores g_h[0..7] of its four tiles
(rows y 34.56 / 587.52 / 1321.92 / 1874.88) and drops g_h[8..15]; the four freed bands (y 311.04 / 864 / 1598.4 / 2151.36,
x 34.56..1401.84, 8.64 grid and gaps, 4.32 halo) take the provider boxes of claude/s81-svc-7-1108
results/geom_review/svc_r5_provider_1113 (8 SML, 8 H4, 4 SMD) and the MEASURED glue cut into registered GLUE boxes
(svc_hi 7, svc_lo 8; mapped ORFS synth DIE-S81-85 svcglue run_hi / run_lo).  svc_lo also takes the 32 IRG fastpad
hslices u_irg.g_ch[c].u_c.g_s[h].u_s (ot_hdc_v41x_idx_hslice_fp, claude/die-s81-85-irg-fastpad-1109@b9200f3611): u_irg
(dsdv_idx_rg3) is already a sibling of u_rsv in every svc_lo type (contents), so the move is type-local.

Forms
  hi : svc_hi_dsdv_svc_rs__t1..t6, outline unchanged (svc_hi does not grow).
  G  : svc_lo record form.  Each freed band grows 259.2 -> 278.64 (+19.44, four bands = +77.76 um Y, X unchanged).  Inside
       the type every item above a band top moves up by 19.44 per band top below it; W/E/S face pin windows stay where
       they are (svc_lo <-> svc_lo and svc_0 <-> iqf abutments unchanged), N-face items move +77.76.  Die: every
       partition with origin y >= 4104 (svc_hi row and the non-svc partitions above the 11-04 svc band gap) moves up
       77.76, die outline +77.76, the 14 svcband channels at that cut widen 319.68 -> 397.44 (<= 405 reach,
       growth <= +85 bound).  The growth is split 17.28 / 17.28 / 17.28 / 25.92 over bands 0..3 so every moved
       origin stays on the 8.64 lattice (band heights 276.48 x3, 285.12).
  N  : svc_lo labelled fallback, no growth, same boxes in 259.2 bands.

    python3 svc_split_event_1109.py BASE_PLAN OUT_PLAN EVENT_JSON --lo-form {G,N,none}

Only partition_types[svc_hi_dsdv_svc_rs__t*/svc_lo_*].{outline_um (G), hard_cores, clock.taps, clock.tap_um,
clock.landing_contract, clock.edge_clocks, contents, note}, reset.in_sites[svc_lo] and (G) die geometry change."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(ROOT / "physical/die_plan/s81"))


def _style(raw_bytes, P):
    """keep the base file's JSON style (tools/die_plan/type_safe_event.py _style); final_1109 plans are indent=1"""
    from plan_event_1104 import plan_text
    for f in (lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, separators=(",", ":")) + "\n",
              lambda p: json.dumps(p) + "\n", lambda p: json.dumps(p, indent=2) + "\n", plan_text):
        if f(P).encode() == raw_bytes:
            return f
    raise SystemExit("base plan style not reproducible")

OWNER_G = "OWNER 11-09 yes for growth, svc_lo only, <= +77.76 um Y"
GRID, GAP, HALO = 8.64, 8.64, 4.32
BAND_Y = [311.04, 864.0, 1598.4, 2151.36]
BAND_H = 259.2
G_TOTAL = 77.76
G_BANDS = [17.28, 17.28, 17.28, 25.92]   # 8.64-lattice split of +77.76 (19.44 a band is off the lattice: G0C hard_cores)
assert abs(sum(G_BANDS) - G_TOTAL) < 1e-9
X0, XMAX = 34.56, 1401.84
LO_TOP_DIE = 4104.0           # svc_lo row top = svc_hi row origin = hi side of the 14 svcband_ channels (319.68)
CH_REACH, CH_GROW_MAX = 405.0, 85.0
HI_TYPES = [f"svc_hi_dsdv_svc_rs__t{i}" for i in range(1, 7)]
LO_TYPES = [f"svc_lo_dsdv_svc_rs__t{i}" for i in range(1, 8)] + ["svc_lo_dsdv_svc_rs_w__t1"]

# ---- measured inputs -------------------------------------------------------------------------------------------------
GLUE_MEAS = {  # epyc7 /srv/opentallas-scratch2/claude/die-s81-85/svcglue/run_{hi,lo}/run/reports/asap7/*/base/synth_stat.txt
    "hi": dict(cells=664719, area=86301.761, mem_cells=21300, mem_area=500.0, src="svcglue_hi synth_stat.txt (t1)"),
    "lo": dict(cells=674070, area=88421.0, mem_cells=21300, mem_area=500.0, src="svcglue_lo synth_stat.txt (t5)"),
}
# mapped sub-block cells (k) of the glue (dsdv_svc_rs_c minus blackboxed hcore / sx_hrow / sml / smd / merge_x)
SUB = {"u_att_own": 193.0, "tr_x": 41.0, "smc": 100.0, "smr": 66.0, "rs_c": 54.0, "attn_s_local": 30.0,
       "rt2_load": 5.25, "smq": 12.0, "smt": 11.0, "sx_rly": 7.0}
PROVIDER = {  # mapped std area at the box (svc_r5_provider_1113/review.json), fastpad map (irg-fastpad-1109)
    "SML": dict(module="ot_s81_su_sml_fold2", area=11268.96948, w=120.96),
    "H4": dict(module="ot_s81_svc_merge_h4", area=10669.19202, w=103.68),
    "SMD": dict(module="ot_s81_su_smd_fold2", area=6834.84156, w=69.12),
    "IRG": dict(module="ot_hdc_v41x_idx_hslice_fp", area=7389.67, cells=59836, w=60.48),
    "GLUE": dict(module=None, w=120.96),
}


def glue_boxes(side):
    """the glue cut from connectivity: (name, members, mapped k-cells, mem k-cells); u_att own logic is the only new RTL cut
    (A = q/w/k ingest queues + request path, B = issue / run / x-list / rowword), every other member is an existing
    module boundary.  Tile pairs: band 0 sits between tiles 0/1, band 2 between tiles 2/3."""
    misc = (GLUE_MEAS[side]["cells"] / 1000.0) - sum(SUB[k] * (4 if k in ("tr_x", "rt2_load") else 1) for k in SUB)
    half_mem = GLUE_MEAS[side]["mem_cells"] / 2000.0
    T = lambda a, b: [f"u_rsv.u_att.u_eng.g_tr[{a}] (tr_x)", f"u_rsv.u_att.u_eng.g_tr[{b}] (tr_x)",
                      f"u_rsv.u_att.u_eng.g_t[{a}].g_ts.u_t.u_hc.u_expand+u_load_stage", f"u_rsv.u_att.u_eng.g_t[{b}].g_ts.u_t.u_hc.u_expand+u_load_stage",
                      "8 of 16 u_rsv.u_att.u_eng.g_stage2.u_stage{0,1} native memory children"]
    common = [
        ("T01", T(0, 1), 2 * SUB["tr_x"] + 2 * SUB["rt2_load"], half_mem),
        ("T23", T(2, 3), 2 * SUB["tr_x"] + 2 * SUB["rt2_load"], half_mem),
        ("ATT_A", ["u_rsv.u_att own logic part A (q/w/k ingest queues wq/fq, qrq request, rk) [NEW RTL CUT]"], SUB["u_att_own"] / 2, 0),
        ("ATT_B", ["u_rsv.u_att own logic part B (issue/run/go, x-list, rowword, sc) [NEW RTL CUT]"], SUB["u_att_own"] / 2, 0),
        ("SMC", ["u_rsv.u_sms.u_smh.u_smc"], SUB["smc"], 0),
    ]
    if side == "hi":
        return common + [
            ("RSC", ["u_rsv own logic + face registers (rs_c)", "u_rsv misc (job/selq/pc/p_source/den_stamp/up/gx)", "u_rsv.u_att.u_eng own logic (attn_s local)"],
             SUB["rs_c"] + misc + SUB["attn_s_local"], 0),
            ("SMR", ["u_rsv.u_sms.u_smh.u_smr", "u_rsv.u_sms.u_smq", "u_rsv.u_tgt/u_gw/u_sot (SMT)", "u_rsv.u_sx relays (dsdv_sx_rly_in/out)"],
             SUB["smr"] + SUB["smq"] + SUB["smt"] + SUB["sx_rly"], 0),
        ]
    return common + [
        ("RSC", ["u_rsv own logic + face registers (rs_c)", "u_rsv misc (job/selq/pc/p_source/den_stamp/up/gx)"], SUB["rs_c"] + misc, 0),
        ("SMR", ["u_rsv.u_sms.u_smh.u_smr"], SUB["smr"], 0),
        ("SMX", ["u_rsv.u_sms.u_smq", "u_rsv.u_tgt/u_gw/u_sot (SMT)", "u_rsv.u_sx relays", "u_rsv.u_att.u_eng own logic (attn_s local)"],
         SUB["smq"] + SUB["smt"] + SUB["sx_rly"] + SUB["attn_s_local"], 0),
    ]


# svc_hi: every box sits at the left edge of one of the 8 old hcore columns (x 34.56 + 172.8 c, 157.68 wide), so the
# 15.12-um vertical streets between the old hcore columns stay free: the svc_hi ft slots site their station bits there
# (G0C geometry: a free-packed layout put 122..480 station bits of t1 ft0/ft1 and t5 ft0/ft2 under SML/H4 boxes).
HCOL = [round(34.56 + 172.8 * c, 2) for c in range(8)]
HI_FIXED_COL = {"SML": (0, 1), "H4": (2, 6), "SMD": 7}
HI_GLUE_XY = {"T01": (0, HCOL[3]), "RSC": (1, HCOL[3]), "ATT_A": (1, HCOL[4]), "ATT_B": (1, HCOL[5]),
              "T23": (2, HCOL[3]), "SMR": (2, HCOL[4]), "SMC": (2, HCOL[5])}
LO_GLUE_XY = {"T01": (0, 1149.12), "RSC": (0, 1278.72), "ATT_A": (1, 1149.12), "SMC": (1, 1278.72),
              "ATT_B": (2, 1149.12), "T23": (2, 1278.72), "SMR": (3, 1149.12), "SMX": (3, 1278.72)}
SML_X, H4_X, SMD_X = (34.56, 164.16), (293.76, 959.04), 1071.36
IRG_X = [round(406.08 + 69.12 * j, 2) for j in range(8)]


def r3(v):
    return round(v, 3)


def boxes_for(side, band_y, band_hs):
    out = []
    sml_x = [HCOL[c] for c in HI_FIXED_COL["SML"]] if side == "hi" else SML_X
    h4_x = [HCOL[c] for c in HI_FIXED_COL["H4"]] if side == "hi" else H4_X
    smd_x = HCOL[HI_FIXED_COL["SMD"]] if side == "hi" else SMD_X
    for b, y in enumerate(band_y):
        band_h = band_hs[b]
        for j, x in enumerate(sml_x):
            i = 2 * b + j
            out.append(dict(kind="SML", name=f"SML{i}", inst=f"u_rsv.u_sms.u_smh.g_l[{i}].u_sml", module=PROVIDER["SML"]["module"],
                            band=b, origin_um=[x, y], outline_um=[PROVIDER["SML"]["w"], band_h], area_um2=PROVIDER["SML"]["area"]))
        for j, x in enumerate(h4_x):
            out.append(dict(kind="H4", name=f"H4_{b}{j}", inst=f"u_rsv.u_att.u_eng.g_m[{b}].g_real.g_x.u_m.g_h4[{j}].u_h4",
                            module=PROVIDER["H4"]["module"], band=b, origin_um=[x, y], outline_um=[PROVIDER["H4"]["w"], band_h],
                            area_um2=PROVIDER["H4"]["area"]))
        out.append(dict(kind="SMD", name=f"SMD{b}", inst=f"u_rsv.u_sms.u_smh.g_p[{b}].u_smd", module=PROVIDER["SMD"]["module"],
                        band=b, origin_um=[smd_x, y], outline_um=[PROVIDER["SMD"]["w"], band_h], area_um2=PROVIDER["SMD"]["area"]))
        if side == "lo":
            for h, x in enumerate(IRG_X):
                out.append(dict(kind="IRG", name=f"IRG{b}_{h}", inst=f"u_irg.g_ch[{b}].u_c.g_s[{h}].u_s", module=PROVIDER["IRG"]["module"],
                                band=b, origin_um=[x, y], outline_um=[PROVIDER["IRG"]["w"], band_h], area_um2=PROVIDER["IRG"]["area"],
                                cells=PROVIDER["IRG"]["cells"]))
    m = GLUE_MEAS[side]
    a_cell, a_mem = m["area"] / m["cells"], (m["mem_area"] / m["mem_cells"] if m["mem_cells"] else 0)
    xy = HI_GLUE_XY if side == "hi" else LO_GLUE_XY
    for name, members, kc, kmem in glue_boxes(side):
        b, x = xy[name]
        out.append(dict(kind="GLUE", name=f"GLUE_{name}", inst=f"u_rsv.u_glue_{name.lower()}", module=f"dsdv_svc_glue_{side}_{name.lower()}",
                        band=b, origin_um=[x, band_y[b]], outline_um=[PROVIDER["GLUE"]["w"], band_hs[b]], members=members,
                        cells=int(round((kc + kmem) * 1000)), area_um2=round(kc * 1000 * a_cell + kmem * 1000 * a_mem, 1)))
    for bx in out:
        w, h = bx["outline_um"]
        bx["fill"] = round(bx["area_um2"] / ((w - 2 * HALO) * (h - 2 * HALO)), 3)
        bx["origin_um"] = [r3(v) for v in bx["origin_um"]]
    return out


# ---- internal pin cycles: one registered face per box crossing + relay stations every 405 um (Manhattan, box centres) -
EDGES = [  # (from, to, bits note) - glue/provider interfaces created by the cut
    ("GLUE_RSC", "GLUE_ATT_A", "q/w/k words in"), ("GLUE_ATT_A", "GLUE_ATT_B", "att A->B issue"), ("GLUE_ATT_B", "GLUE_ATT_A", "att B->A credit"),
    ("GLUE_ATT_B", "GLUE_T01", "staging fill"), ("GLUE_ATT_B", "GLUE_T23", "staging fill"),
    ("GLUE_T01", "TILE0", "ib to hcores"), ("GLUE_T01", "TILE1", "ib"), ("GLUE_T23", "TILE2", "ib"), ("GLUE_T23", "TILE3", "ib"),
    ("TILE*", "H4*", "t_y to merges"), ("H4*", "GLUE_ATT_B", "merged p.v"), ("GLUE_ATT_B", "SML*", "scores to SM"),
    ("SML*", "GLUE_SMC", "l_mx/l_e"), ("GLUE_SMC", "GLUE_SMR", "smc->smr (u_cv/u_cd SRL)"), ("GLUE_SMR", "SMD*", "smr->smd"),
    ("SMD*", "GLUE_RSC", "SM out to faces"), ("GLUE_RSC", "IRG*", "idx key/Q (lo)"),
]
TILE_ROW_Y = [34.56, 587.52, 1321.92, 1874.88]


def pin_cycles(boxes, fy):
    cen = {b["name"]: (b["origin_um"][0] + b["outline_um"][0] / 2, b["origin_um"][1] + b["outline_um"][1] / 2) for b in boxes}
    for t, y in enumerate(TILE_ROW_Y):
        cen[f"TILE{t}"] = (725.76, fy(y) + 129.6)
    res = {}
    for a, b, note in EDGES:
        A = [k for k in cen if (k.startswith(a[:-1]) if a.endswith("*") else k == a)]
        B = [k for k in cen if (k.startswith(b[:-1]) if b.endswith("*") else k == b)]
        if not A or not B:
            continue
        # a group edge pairs each source with its nearest sink (H4 per band, SML per band ...); report the worst pair
        d = max(min(abs(cen[p][0] - cen[q][0]) + abs(cen[p][1] - cen[q][1]) for q in B) for p in A) \
            if (a.endswith("*") or b.endswith("*")) else max(abs(cen[p][0] - cen[q][0]) + abs(cen[p][1] - cen[q][1]) for p in A for q in B)
        st = max(0, math.ceil(d / 405.0) - 1)
        res[f"{a}->{b}"] = dict(note=note, worst_um=round(d, 1), relay_stations=st, delta=1 + st)
    return res


# ---- geometry helpers ------------------------------------------------------------------------------------------------
def overlaps(a, b, halo=0.0):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 - halo < bx1 - 1e-6 and bx0 < ax1 + halo - 1e-6 and ay0 - halo < by1 - 1e-6 and by0 < ay1 + halo - 1e-6


def rect(o, s):
    return (o[0], o[1], o[0] + s[0], o[1] + s[1])


def make_fy(grow):
    tops = [y + BAND_H for y in BAND_Y]

    def fy(y):
        return r3(y + (sum(g for c, g in zip(tops, G_BANDS) if y > c + 1e-6) if grow else 0.0))
    return fy


def shift_points(o, fy, W, H):
    """apply fy to every [x, y] / rect_um / xy point under o except points on the W/E faces (pin windows stay)"""
    n = [0]

    def pt(v):
        if v[0] <= 0.01 or v[0] >= W - 0.01:
            return
        ny = fy(v[1])
        if ny != v[1]:
            v[1] = ny
            n[0] += 1

    def pts(v):
        if len(v) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in v):
            pt(v)
        else:
            for q in v:
                pts(q)

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("rect_um", "box_um") and isinstance(v, list) and len(v) == 4 and all(isinstance(a, (int, float)) for a in v):
                    y0, y1 = fy(v[1]), fy(v[3])
                    if (y0, y1) != (v[1], v[3]):
                        v[1], v[3] = y0, y1
                        n[0] += 1
                elif isinstance(v, list) and len(v) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in v) \
                        and k in ("xy", "xy_um", "tap_um", "pin_xy_um", "root", "pin_um", "origin_um"):
                    pt(v)
                elif k in ("regs_um", "bit_sites_um"):      # ft station registers and bit sites (nested point lists)
                    pts(v)
                else:
                    walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
    walk(o)
    return n[0]


def split_type(t, side, grow):
    W, H = t["outline_um"]
    fy = make_fy(grow)
    band_y = [fy(y) for y in BAND_Y]
    band_hs = [r3(BAND_H + (g if grow else 0.0)) for g in G_BANDS]
    drop = [h for h in t["hard_cores"] if h["module"] == "ot_s81c_attn_hcore" and int(h["inst"].split("g_h[")[1].split("]")[0]) >= 8]
    assert len(drop) == 32 and sorted({h["origin_um"][1] for h in drop}) == BAND_Y, "unexpected hcore set"
    dn = {h["inst"] for h in drop}
    keep = [h for h in t["hard_cores"] if h["inst"] not in dn]
    assert len(keep) == 40, len(keep)
    ck = t["clock"]
    ck["taps"] = [x for x in ck["taps"] if x["name"].rsplit(".", 1)[0] not in dn]
    assert len(ck["taps"]) == 32
    lc = ck.get("landing_contract") or {}
    ct = lc.get("collector_tree") or {}
    if "core_resets" in ct:
        ct["core_resets"] = [r for r in ct["core_resets"] if r["inst"] not in dn]
    moved = 0
    if grow:
        for h in keep:
            h["origin_um"][1] = fy(h["origin_um"][1])
        for c in t["contents"]:
            if "origin_um" in c:
                c["origin_um"][1] = fy(c["origin_um"][1])
        moved = shift_points(ck, fy, W, H) + shift_points(t.get("reset", {}), fy, W, H) + shift_points(t.get("ft_slots", []), fy, W, H)
        t["outline_um"][1] = r3(H + G_TOTAL)
    boxes = boxes_for(side, band_y, band_hs)
    for b in boxes:
        e = dict(inst=b["inst"], module=b["module"], lef=f"physical/die_plan/s81/cores/svc/split_1109/{b['module']}.lef",
                 origin_um=b["origin_um"], outline_um=[b["outline_um"][0], r3(b["outline_um"][1])], orient="R0",
                 track_offset_um=[0.108, 0.012], pins_file=f"inputs/core_pins/{b['module']}.json", obs_max="M5",
                 lib=f"physical/die_plan/s81/cores/svc/split_1109/views/{b['module']}_tt.lib",
                 cells=b.get("cells", 0), cells_basis="mapped ORFS synth (DIE-S81-85 11-09)" if b["kind"] in ("GLUE", "IRG") else "mapped at box (svc_r5_provider_1113)",
                 note=f"DIE-S81-85 svc split 11-09 {b['kind']} {b['name']} fill {b['fill']} (PLANNED provider box: LEF/pins/views from the provider kit; registered faces)")
        if b["kind"] == "GLUE":   # schema: no extra hard_cores keys; members ride in the note (full list in the event)
            e["note"] += "; members: " + " + ".join(b["members"])
        keep.append(e)
    t["hard_cores"] = keep
    t["note"] = t.get("note", "") + (f" | DIE-S81-85 svc split 11-09 (H8 RT2, {len(boxes)} provider/glue boxes" +
                                     (f", {OWNER_G}: 4 bands 259.2 -> 276.48 x3 / 285.12" if grow else ", no growth") + ")")
    return boxes, moved, fy


def validate_type(t, boxes):
    W, H = t["outline_um"]
    fails = []
    hard = [(h["inst"], rect(h["origin_um"], h["outline_um"])) for h in t["hard_cores"]]
    macros = [(c["inst"], rect(c["origin_um"], c["outline_um"])) for c in t["contents"] if "origin_um" in c and "outline_um" in c]
    for b in boxes:
        x, y = b["origin_um"]
        if abs(x / GRID - round(x / GRID)) > 1e-6:
            fails.append(("off grid x", b["name"], x))
        if b["fill"] > 0.65:
            fails.append(("fill > 0.65", b["name"], b["fill"]))
        if b.get("cells", 0) > 150000:
            fails.append(("cells > 150k", b["name"], b["cells"]))
    allr = hard + macros
    for i, (n1, r1) in enumerate(allr):
        if r1[0] < -1e-6 or r1[1] < -1e-6 or r1[2] > W + 1e-6 or r1[3] > H + 1e-6:
            fails.append(("outside outline", n1, r1))
        for n2, r2 in allr[i + 1:]:
            # 8.64 gaps = two 4.32 halos: a box must clear every other box/core/macro by >= 2 * HALO - eps
            if overlaps(r1, r2, 2 * HALO - 1e-3):
                fails.append(("overlap/halo", n1, n2))
    # clock bay stays free
    bay = t["clock"]["tap_um"]
    for n, r in hard:
        if r[0] < bay[0] < r[2] and r[1] < bay[1] < r[3]:
            fails.append(("clock bay covered", n))
    # band x budget
    for b in range(4):
        row = sorted((x for x in boxes if x["band"] == b), key=lambda x: x["origin_um"][0])
        used = row[-1]["origin_um"][0] + row[-1]["outline_um"][0] if row else 0
        if used > XMAX + 1e-6:
            fails.append(("band overrun", b, used))
    return fails


def die_grow(P, G):
    """svc_lo rows +G: every partition with origin y >= LO_TOP_DIE moves up G (svc_hi row + rows above the 11-04 gap)"""
    T = P["partition_types"]
    rep = {}
    for p in P["partitions"]:
        y0 = p["origin_um"][1]
        top = y0 + T[p["type"]]["outline_um"][1]
        assert not (y0 < LO_TOP_DIE - 0.01 and top > LO_TOP_DIE + 0.01) or p["type"] in LO_TYPES, ("straddles cut", p["name"])
    shift = {}
    for p in P["partitions"]:
        if p["origin_um"][1] >= LO_TOP_DIE - 0.01:
            p["origin_um"][1] = r3(p["origin_um"][1] + G)
            shift[p["name"]] = G
    nw = 0
    for q in P["ports"]:
        if q.get("face") in ("W", "E") and "window_um" in q:
            a, b = q["src"]["part"], q["dst"]["part"]
            da, db = shift.get(a, 0.0), shift.get(b, 0.0)
            if "@die" in (a, b):
                d = da or db
            else:
                assert da == db, ("W/E port across the cut", q["id"])
                d = da
            if d:
                q["window_um"] = [r3(v + d) for v in q["window_um"]]
                nw += 1
    die = P["die"]
    dy = lambda y: G if y >= LO_TOP_DIE - 0.01 else 0.0

    def shift_rects(o, keys):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and isinstance(v, list) and v:
                    for r in ([v] if isinstance(v[0], (int, float)) else v):
                        if len(r) == 4:
                            d = dy(r[1])
                            assert dy(r[3] - 0.02) == d, ("rect straddles the cut", k, r)
                            r[1], r[3] = r3(r[1] + d), r3(r[3] + d)
                else:
                    shift_rects(v, keys)
        elif isinstance(o, list):
            for v in o:
                shift_rects(v, keys)
    DOM = {"rect_um", "phy_macro_um", "esd_um", "exclude_um", "bump_exclude_um", "core_strip_um"}
    shift_rects(die["io"], DOM)
    shift_rects(die["pg"]["domains"], DOM)
    Hold = die["outline_um"][1]
    for c in die["channels"]:
        if "rect_um" in c:
            r = c["rect_um"]
            if r[1] < 103.69 and r[3] > Hold - 103.68 - 1:
                r[3] = r3(r[3] + G)
            elif r[1] >= LO_TOP_DIE - 0.01:
                r[1], r[3] = r3(r[1] + G), r3(r[3] + G)
    widened = []
    names = {p["name"]: p for p in P["partitions"]}
    for c in die["channels"]:
        if str(c.get("name", "")).startswith("svcband_") and abs(c["width_um"] - 319.68) < 1e-6:
            lo_p, hi_p = c["between"]
            assert names[hi_p]["origin_um"][1] >= LO_TOP_DIE + G - 0.01, c["name"]
            c["width_um"] = r3(c["width_um"] + G)
            c["reason"] += f" | +{G} DIE-S81-85 svc_lo split 11-09 ({OWNER_G})"
            widened.append(c["name"])
    die["outline_um"][1] = r3(Hold + G)
    r = P["clock"]["spine"]["root_um"]
    r[1] = r3(r[1] + dy(r[1]))
    rep.update(partitions_moved=len(shift), ew_port_windows=nw, channels_widened=len(widened),
               channel_width=[319.68, r3(319.68 + G)], die_outline=die["outline_um"])
    assert len(widened) == 14, widened
    assert 319.68 + G <= CH_REACH + 1e-6 and G <= CH_GROW_MAX, "channel reach / growth bound"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("--lo-form", choices=("G", "N", "none"), default="G")
    a = ap.parse_args()
    raw = Path(a.base).read_bytes()
    P = json.loads(raw)
    dump = _style(raw, P)
    base_sha = hashlib.sha256(raw).hexdigest()
    pt = P["partition_types"]
    ev = dict(schema="opentallas.s81_svc_split_event.v1", tool="physical/die_plan/s81/svc_split_event_1109.py",
              owner="COORD 11-09 08:4x (a) svc_hi now, (b) svc_lo forms G/N; " + (OWNER_G + " (form G = svc_lo record)" if a.lo_form == "G" else
                                                                                 "form N = labelled fallback, no growth" if a.lo_form == "N" else "svc_hi only"),
              lane="DIE-S81-85", base_plan=a.base, base_plan_sha256=base_sha, lo_form=a.lo_form,
              rtl_defines=["OT_SVC_H8", "OT_SVC_H8_REUSE_RT2"] + (["OT_IDX_HSLICE_FASTPAD", "OT_IDX_HSLICE_HARD"] if a.lo_form != "none" else []),
              glue_measured=GLUE_MEAS, glue_subblocks_kcells=SUB, types={}, pin_cycle_deltas={}, die_lane_pin_cycle_deltas={},
              validation={})
    sides = [("hi", HI_TYPES, False)] + ([("lo", LO_TYPES, a.lo_form == "G")] if a.lo_form != "none" else [])
    for side, types, grow in sides:
        for tn in types:
            t = pt[tn]
            assert t["outline_um"][1] == (2747.52 if side == "hi" else 2773.44), (tn, "not the base outline (second run?)")
            if side == "lo":
                assert any(c["inst"] == "u_irg" and c["module"] == "dsdv_idx_rg3" for c in t["contents"]), (tn, "no u_irg: not type-local")
            boxes, moved, fy = split_type(t, side, grow)
            if grow and tn in P["reset"]["in_sites"]:
                P["reset"]["in_sites"][tn][1] = fy(P["reset"]["in_sites"][tn][1])
            fails = validate_type(t, boxes)
            pc = pin_cycles(boxes, fy)
            ev["types"][tn] = dict(outline_um=t["outline_um"], grow_um=G_TOTAL if grow else 0.0, points_moved=moved,
                                   dropped_hcores=[f"u_rsv.u_att.u_eng.g_t[{k}].g_ts.u_t.u_hc.g_h[8..15].u_c" for k in range(4)],
                                   boxes=[{k: b[k] for k in ("kind", "name", "inst", "module", "origin_um", "outline_um", "cells", "area_um2", "fill", "members") if k in b}
                                          for b in boxes], validation_fails=fails)
            ev["pin_cycle_deltas"][tn] = {k: v["delta"] for k, v in pc.items()}
            ev["types"][tn]["pin_cycles"] = pc
            assert not fails, (tn, fails[:5])
    if a.lo_form == "G":
        ev["validation"]["die"] = die_grow(P, G_TOTAL)
    ev["die_lane_pin_cycle_deltas_note"] = ("0 for every die lane: face windows, face registers and bus widths of all 14 types are "
                                            "unchanged; the cut cycles are type-internal engine stages (pin_cycle_deltas) "
                                            "for the svc compiler / token schedule")
    P["note"] = P["note"] + (" | DIE-S81-85 svc split 11-09: svc_hi H8 RT2 split (7 glue)" +
                             (f"; svc_lo split + IRG fastpad (8 glue), form {a.lo_form}" if a.lo_form != "none" else "") +
                             (f", {OWNER_G}" if a.lo_form == "G" else ""))
    txt = dump(P)
    Path(a.out).write_text(txt)
    ev["plan_output"] = a.out
    ev["plan_output_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    Path(a.event).write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps(dict(out_sha=ev["plan_output_sha256"][:16], types=len(ev["types"]), die=ev["validation"].get("die")), indent=0))


if __name__ == "__main__":
    main()
