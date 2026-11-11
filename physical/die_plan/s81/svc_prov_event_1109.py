#!/usr/bin/env python3
"""S81 svc_rs provider plan event v2, form A (DIE-S81-85 11-09; COORD "Decision: form A"; supersedes f5675075e3).

Same plan base (final_1109 65648816), same H8 RT2 cut (OT_SVC_H8 + OT_SVC_H8_REUSE_RT2: g_h[8..15] dropped, the four
freed bands take the boxes), same svc_lo form G growth (OWNER 11-09 yes for growth, svc_lo only, <= +77.76 um Y; die
+77.76, 14 svcband channels 319.68 -> 397.44).  What changes against v1:

  hard boxes ONLY on existing module boundaries (no new RTL cut of u_att / rs_c):
    SML x8   u_rsv.u_sms.u_smh.g_l[i].u_sml                       ot_s81_su_sml_fold2
    SMD x4   u_rsv.u_sms.u_smh.g_p[p].u_smd                       ot_s81_su_smd_fold2
    H4  x8   u_rsv.u_att.u_eng.g_m[k].g_real.g_x.u_m.g_h4[h].u_h4 ot_s81_svc_merge_h4 (-DOT_SVC_MERGE_H4, merge_h8_split)
    SMC x1   u_rsv.u_sms.u_smh.u_smc                              ot_s81_su_smc
    SMR x1   u_rsv.u_sms.u_smh.u_smr                              ot_s81_su_smr
    TRX x4   u_rsv.u_att.u_eng.g_tr[k].g_x.u_tr                   ot_hdc_v41x_attn_tr_x (XOFF 0/8/16/24 = 4 masters)
    IRG x32  u_irg.g_ch[c].u_c.g_s[h].u_s (svc_lo)                ot_s81_svc_idx_hslice_fp (fastpad 9b6810c755, census-safe S81 copy)
  everything else (u_att own logic, rs_c, attn_s local, rt2 load stages, smq, smt, gw, sx (its 8 dsdv_svc_sx_hrow
  are already type hard cores, so sx has no box boundary of its own), misc, and in svc_lo the u_irg remainder,
  u_ctrl_a/b, u_etap_a/b) is the type's SOFT parent logic; the v1 GLUE slots that no hard box takes are listed as soft
  parent regions (placement guides in the event; the schema has no soft-region key).  COORD 11-09: no further boxes.

  (3) -DOT_SVC_ATT_MEM_MACRO (0491694789+): u_att sw (8, two-bank lookahead dsdv_svc_mem_la) / wq (18) / qmem (4) as
  ot_sram_1r1w_32x128_m1_r0c0 and u_rsv pbuf as 1 ot_sram_1r1w_160x256_m1_r0c0 = 31 new macros per type, placed
  explicitly as plan contents (R0, obs_max M4 and 4.32 halo = the existing ot_sram contents rule; the LEF pins are all
  on the macro W face on M4, so every site keeps its W face on an open >= 8.64 channel toward the u_att interior):
    svc_hi  two rows above the existing u_att / u_rsv macro rows (y 2561.772 / 2596.332, x lattice 43.2 + 62.64 i of
            the 2527 32x128 row), pbuf at the end of row B;
    svc_lo  (top strip full: N-face attn / attnh windows on M3 and the edge clock taps) the x >= 1233 corner above the
            256x256 row, the x 1304 / 1365 column right of the 2421..2527 rows, and the band-3 soft slot SOFT1.
  box fill <= 0.45 (svc_hi SMD widened to 77.76) except the IRG fastpad hslice: COORD 11-09 (a) first form at
  0.516-0.532 (COORD 08:4x highest fill that routes), ONE IRG kit pilot first; FALLBACK_B = the <= 0.45 lo re-pack.

Measured (mapped ORFS asap7 synth, epyc7, see MEAS_FILE): parent soft cells per type, cells per hard box.

    python3 svc_prov_event_1109.py BASE_PLAN OUT_PLAN EVENT_JSON MEAS_JSON
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svc_split_event_1109 as V1  # noqa: E402  (v1 helpers: geometry, growth, die_grow, validation)

OWNER_G = V1.OWNER_G
HALO = V1.HALO
HCOL = V1.HCOL
HI_TYPES, LO_TYPES = V1.HI_TYPES, V1.LO_TYPES
CORE_CELLS_MAX = 400_000
BOX_CELLS_MAX, BOX_UTIL_MAX = 150_000, 0.45

TRX_XOFF = [0, 8, 16, 24]          # XOFF = (gk*DPT)%32, DPT 8
SMD_W_HI = 77.76                   # svc_hi bands are 259.2 high: SMD at 69.12 maps to fill 0.451 > 0.45; HCOL[7] is 157.68 wide

# ---- (3) the 31 new macros (RTL paths of dsdv_svc_att / dsdv_svc_rs under -DOT_SVC_ATT_MEM_MACRO) -------------------
M32 = dict(module="ot_sram_1r1w_32x128_m1_r0c0", outline_um=[51.432, 20.808])
M160 = dict(module="ot_sram_1r1w_160x256_m1_r0c0", outline_um=[92.04, 39.432])
MEM_DIR = "physical/asap7_memory_macros_v2"


def new_macro_insts():
    sw = [(f"u_rsv.u_att.u_sw_mem.g_b[{b}].g_m[{g}].u_mem", M32, "sw") for b in range(2) for g in range(4)]
    wq = [(f"u_rsv.u_att.g_wqm[{c}].g_pc[{p}].u_wq_mem.g_m[{g}].g_32.u_mem", M32, "wq") for c in range(3) for p in range(2) for g in range(3)]
    qm = [(f"u_rsv.u_att.u_qmem_mem.g_m[{g}].g_32.u_mem", M32, "qmem") for g in range(4)]
    return sw + wq + qm, ("u_rsv.u_pbuf_mem.g_m[0].g_160.u_mem", M160, "pbuf")


def site_candidates(side, band_y, outline):
    """ordered candidate origins (final coordinates) for one macro outline: first fit in this order"""
    X = lambda i: r3(43.2 + 62.64 * i)
    ys = lambda y0, y1: [r3(y0 + 8.64 * k) for k in range(int((y1 - y0) / 8.64) + 1)]
    if side == "hi":    # rows above the existing u_att / u_rsv macro rows (2421 / 2475 / 2527), lattice of the 2527 row
        return [(X(i), y) for y in ys(2561.772, 2690.0) for i in range(22)]
    G = V1.G_TOTAL     # svc_lo: x >= 1233 corner above the 256x256 row, x 1304 / 1365 column, band-3 slot SOFT1
    col = [(x, y) for y in ys(2421.372 + G, 2630.0) for x in (1304.64, 1365.12)]
    corner = [(x, y) for y in ys(2691.372, 2830.0) for x in (1233.36, 1296.0, 1358.64)]
    slot = [(x, y) for y in ys(band_y[3] + 8.64, band_y[3] + 285.12 - 8.64 - outline[1]) for x in (1287.36, 1347.84)]
    far = []
    if LO_PACK == "b":   # TRX3 takes x 1252.8-1313.28 of band 3: the last macros (qmem, then wq) go to band-0 SOFT0
        far = [(1330.56, y) for y in ys(band_y[0] + 8.64, band_y[0] + 276.48 - 8.64 - outline[1])]
    return (corner + col + slot + far) if outline[0] > 60 else (col + corner + slot + far)


def first_fit(t, cands, outline, placed):
    W, H = t["outline_um"]
    occ = [V1.rect(h["origin_um"], h["outline_um"]) for h in t["hard_cores"]] + \
          [V1.rect(c["origin_um"], c["outline_um"]) for c in t["contents"] if "origin_um" in c and "outline_um" in c] + placed
    for x, y in cands:
        r = (x, y, x + outline[0], y + outline[1])
        if r[2] > W - HALO + 1e-6 or r[3] > H - HALO + 1e-6:
            continue
        if any(V1.overlaps(r, o, 2 * HALO - 1e-3) for o in occ):
            continue
        if point_hits(t, [dict(inst="?", origin_um=[x, y], outline_um=outline)]):
            continue
        return [x, y]
    raise SystemExit(f"no site for a {outline} macro")


def add_new_macros(t, side, band_y, band_hs):
    insts, pb = new_macro_insts()
    have = {c["inst"] for c in t["contents"]}
    out, placed = [], []
    for inst, m, grp in [pb] + insts:          # the 160x256 first (largest), then sw / wq / qmem in RTL order
        assert inst not in have, inst
        xy = first_fit(t, site_candidates(side, band_y, m["outline_um"]), m["outline_um"], placed)
        placed.append(V1.rect(xy, m["outline_um"]))
        mod = m["module"]
        c = dict(inst=inst, module=mod, status="new", lef=f"{MEM_DIR}/{mod}/{mod}.lef", lib=f"{MEM_DIR}/{mod}/{mod}_tt.lib",
                 origin_um=[r3(xy[0]), r3(xy[1])], outline_um=list(m["outline_um"]), orient="R0", obs_max="M4",
                 note=f"DIE-S81-85 form A (3) 11-09 {grp} macro (-DOT_SVC_ATT_MEM_MACRO, 0 cycle delta; halo {HALO} (event-validated 2x halo spacing); W-face M4 pins on an "
                      f">= 8.64 channel toward u_att / u_rsv; bound name resolved by bound_macro_paths at kit bind)")
        t["contents"].append(c)
        out.append(dict(inst=inst, group=grp, module=mod, origin_um=c["origin_um"], outline_um=c["outline_um"]))
    return out


def point_hits(t, macros):
    """ft station regs / bit sites, clock pins / taps / relays / collector root, reset sites inside a new macro + halo"""
    R = [(m["inst"], V1.rect(m["origin_um"], m["outline_um"])) for m in macros]
    hits = []

    def chk(path, v):
        for n, r in R:
            if r[0] - HALO < v[0] < r[2] + HALO and r[1] - HALO < v[1] < r[3] + HALO:
                hits.append((path, v, n))

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            if len(o) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in o):
                chk(path, o)
            else:
                for i, v in enumerate(o):
                    walk(v, f"{path}[{i}]")
    for sec in ("clock", "reset", "ft_slots"):
        walk(t.get(sec, {}), sec)
    return hits
PROV = {  # module, width; area/cells: SML/H4/SMD from svc_r5_provider_1113, IRG fastpad map, the rest from MEAS
    "SML": dict(module="ot_s81_su_sml_fold2", w=120.96),
    "H4": dict(module="ot_s81_svc_merge_h4", w=103.68),
    "SMD": dict(module="ot_s81_su_smd_fold2", w=69.12),
    "IRG": dict(module="ot_s81_svc_idx_hslice_fp", w=60.48),
    "SMC": dict(module="ot_s81_su_smc", w=120.96),
    "SMR": dict(module="ot_s81_su_smr", w=120.96),
    "TRX": dict(module="ot_hdc_v41x_attn_tr_x", w=120.96),
}
# svc_hi: boxes at the left edge of the old hcore columns (streets stay free for the ft station bits, v1 G0C finding)
HI_XY = {"TRX0": (0, HCOL[3]), "TRX1": (1, HCOL[3]), "TRX2": (2, HCOL[3]), "TRX3": (3, HCOL[3]),
         "SMR": (2, HCOL[4]), "SMC": (2, HCOL[5])}
HI_SOFT = [(0, HCOL[4]), (0, HCOL[5]), (1, HCOL[4]), (1, HCOL[5]), (3, HCOL[4]), (3, HCOL[5])]
LO_S0, LO_S1 = 1149.12, 1278.72
# COORD 11-09 decision (a): the fastpad IRG hslice keeps the 60.48 box (fill 0.516-0.532) as its FIRST form (COORD 08:4x
# "highest fill that routes"); ONE IRG kit is the pilot before the other lo kits; fallback re-form (b) = FALLBACK_B.
IRG_FILL_MAX = 0.535
PARENT_RISK = dict(  # TT pre-route OpenSTA 833 ps, RVT, reset sync held inactive (meas2/sta q2_hi3 / q2_hi5 / q_hi5)
    note="pre-existing svc parent setup risk: these u_att endpoints already fail in the flop form (hi3, before (3)); "
         "(3) is not the cause.  Address paths of all 31 new macros are >= +154 ps (sta_hi5 / sta_lo5).",
    endpoints={"u_att.sel_held": dict(flop_hi3=-284.6, macro_hi5=-157.2), "u_att.sw_r": dict(flop_hi3=-34.8, macro_hi5=-97.4),
               "u_att.fq_w": dict(flop_hi3=-80.4, macro_hi5=-93.0), "u_att.sw_i": dict(flop_hi3=-48.7, macro_hi5=-26.7),
               "u_att.pres": dict(flop_hi3=-35.1, macro_hi5=35.7), "u_att.qrq (from fq_r)": dict(flop_hi3=-171.5, macro_hi5=-179.3)},
    routed_history="none: no placed / routed svc_rs type kit or attempt exists (searched epyc4 / epyc6 / epyc7 / intel2 kit-wave "
                   "and svc lane scratch 11-09: only gen / bind dirs; the svc types never ran P&R at > 400k), so these "
                   "endpoints never closed",
    rtl_fix_candidates=[
        "scanner (sel_held / sw_r / sw_i / fq_w): retime point with 0 cycle delta: the sw lookahead banks already hold the "
        "words of rp and rp + 1 one cycle early, so register the g_own / f_full / sw_n decode of BOTH candidates and select by "
        "the new pointer parity (the decision moves off the macro clk->q path)",
        "u_att fq_r -> qrq (HBM PC request): +1 pin cycle on the request flops (qrq -> rq face), recorded as a +1 HBM request "
        "latency delta for the svc compiler (OWNER 11-03 pin cycles are a lever)",
        "pres (flop form only): ok in the macro form (+35.7)"])
IRG_NOTE = "IRG fastpad first form at 0.516-0.532 (COORD 08:4x highest-fill-that-routes)"
IRG_NOTE_B = ("IRG fallback (b): 77.76-wide box, fill 0.399 (COORD 11-09: the 60.48 pilot failed the mandatory native census "
              "pre-gate, 482 drivers > 32 loads; census-safe hslice_fp (reset / q_we / pos_r replicated) needs the area)")
FALLBACK_B = dict(note="svc_lo re-pack if the IRG pilot fails route / sign-off: every box <= 0.45 fill, x from 34.56, 8.64 gaps",
                  widths=dict(SML=103.68, H4=103.68, IRG=77.76, SMD=69.12, TRX=60.48, SMC=77.76, SMR=69.12),
                  x=dict(SML=[34.56, 146.88], H4=[259.2, 1062.72], IRG=[round(371.52 + 86.4 * j, 2) for j in range(8)], SMD=1175.04,
                         TRX=1252.8, SMC_SMR=1321.92),
                  fills=dict(SML=0.443, H4=0.419, IRG=0.399, SMD=0.422, TRX=0.26, SMC=0.417, SMR=0.275))
LO_XY = {"TRX0": (0, LO_S0), "TRX1": (1, LO_S0), "TRX2": (2, LO_S0), "TRX3": (3, LO_S0),
         "SMC": (1, LO_S1), "SMR": (2, LO_S1)}
LO_SOFT = [(0, LO_S1), (3, LO_S1)]
# --lo-pack b (COORD 11-09 census decision: fallback (b) is the svc_lo form; the 60.48 IRG box at 0.532 is over 0.45 and
# the census-safe hslice adds flops): FALLBACK_B widths / x, every box <= 0.45 fill.
LO_PACK = "a"
LO_XY_B = {"TRX0": (0, 1252.8), "TRX1": (1, 1252.8), "TRX2": (2, 1252.8), "TRX3": (3, 1252.8),
           "SMC": (1, 1321.92), "SMR": (2, 1321.92)}
LO_SOFT_B = [(0, 1321.92), (3, 1321.92)]


def r3(v):
    return round(v, 3)


def boxes_for(side, band_y, band_hs, M):
    out = []
    pb = side == "lo" and LO_PACK == "b"
    FB = FALLBACK_B
    sml_x = [HCOL[c] for c in V1.HI_FIXED_COL["SML"]] if side == "hi" else (FB["x"]["SML"] if pb else V1.SML_X)
    h4_x = [HCOL[c] for c in V1.HI_FIXED_COL["H4"]] if side == "hi" else (FB["x"]["H4"] if pb else V1.H4_X)
    smd_x = HCOL[V1.HI_FIXED_COL["SMD"]] if side == "hi" else (FB["x"]["SMD"] if pb else V1.SMD_X)
    irg_x = FB["x"]["IRG"] if pb else V1.IRG_X
    box = M["boxes"]
    wid = lambda kind: (FB["widths"][kind] if pb else
                        SMD_W_HI if (kind == "SMD" and side == "hi") else PROV[kind]["w"])

    def add(kind, name, inst, b, x, extra=None):
        p = PROV[kind]
        mm = box[kind if kind != "TRX" else f"TRX{name[-1]}"]
        d = dict(kind=kind, name=name, inst=inst, module=p["module"], band=b, origin_um=[r3(x), band_y[b]],
                 outline_um=[wid(kind), band_hs[b]], cells=int(mm["cells"]), area_um2=float(mm["area"]), basis=mm["basis"])
        if extra:
            d.update(extra)
        out.append(d)
    for b in range(4):
        for j, x in enumerate(sml_x):
            i = 2 * b + j
            add("SML", f"SML{i}", f"u_rsv.u_sms.u_smh.g_l[{i}].u_sml", b, x)
        for j, x in enumerate(h4_x):
            add("H4", f"H4_{b}{j}", f"u_rsv.u_att.u_eng.g_m[{b}].g_real.g_x.u_m.g_h4[{j}].u_h4", b, x)
        add("SMD", f"SMD{b}", f"u_rsv.u_sms.u_smh.g_p[{b}].u_smd", b, smd_x)
        if side == "lo":
            for h, x in enumerate(irg_x):
                add("IRG", f"IRG{b}_{h}", f"u_irg.g_ch[{b}].u_c.g_s[{h}].u_s", b, x)
    xy = HI_XY if side == "hi" else (LO_XY_B if pb else LO_XY)
    for k in range(4):
        b, x = xy[f"TRX{k}"]
        add("TRX", f"TRX{k}", f"u_rsv.u_att.u_eng.g_tr[{k}].g_x.u_tr", b, x,
            dict(params={"XOFF": TRX_XOFF[k]}, physical_master=f"ot_hdc_v41x_attn_tr_x_xoff{TRX_XOFF[k]}"))
    for n in ("SMC", "SMR"):
        b, x = xy[n]
        add(n, n, f"u_rsv.u_sms.u_smh.u_{n.lower()}", b, x)
    for bx in out:
        w, h = bx["outline_um"]
        bx["fill"] = round(bx["area_um2"] / ((w - 2 * HALO) * (h - 2 * HALO)), 3)
    soft = []
    for i, (b, x) in enumerate(HI_SOFT if side == "hi" else (LO_SOFT_B if pb else LO_SOFT)):
        w = 157.68 if side == "hi" else (77.76 if pb else 120.96)
        soft.append(dict(name=f"SOFT{i}", band=b, rect_um=[r3(x), band_y[b], r3(x + w), r3(band_y[b] + band_hs[b])]))
    return out, soft


EDGES = [  # (from, to, note): crossings of a hard-box face (soft endpoint = nearest soft parent region)
    ("SOFT*", "TRX*", "staging fill -> tr_x"), ("TRX*", "TILE*", "tr_x ib -> hcores"),
    ("TILE*", "H4*", "t_y -> merge providers"), ("H4*", "SOFT*", "merged p.v -> u_att"),
    ("SOFT*", "SML*", "scores -> SM lanes"), ("SML*", "SMC", "l_mx / l_e -> smc"), ("SMC", "SMR", "smc -> smr"),
    ("SMR", "SMD*", "smr -> smd"), ("SMD*", "SOFT*", "SM out -> rs faces"), ("SOFT*", "IRG*", "idx key / Q -> hslices (lo)"),
    ("IRG*", "SOFT*", "hslice scores -> irg tail (lo)"),
]


def pin_cycles(boxes, soft, fy):
    cen = {b["name"]: (b["origin_um"][0] + b["outline_um"][0] / 2, b["origin_um"][1] + b["outline_um"][1] / 2) for b in boxes}
    for s in soft:
        r = s["rect_um"]
        cen[s["name"]] = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    for t, y in enumerate(V1.TILE_ROW_Y):
        cen[f"TILE{t}"] = (725.76, fy(y) + 129.6)
    res = {}
    for a, b, note in EDGES:
        A = [k for k in cen if (k.startswith(a[:-1]) if a.endswith("*") else k == a)]
        B = [k for k in cen if (k.startswith(b[:-1]) if b.endswith("*") else k == b)]
        if not A or not B:
            continue
        d = max(min(abs(cen[p][0] - cen[q][0]) + abs(cen[p][1] - cen[q][1]) for q in B) for p in A)
        st = max(0, math.ceil(d / 405.0) - 1)
        res[f"{a}->{b}"] = dict(note=note, worst_um=round(d, 1), relay_stations=st, delta=1 + st)
    return res


def split_type(t, side, grow, M):
    W, H = t["outline_um"]
    fy = V1.make_fy(grow)
    band_y = [fy(y) for y in V1.BAND_Y]
    band_hs = [r3(V1.BAND_H + (g if grow else 0.0)) for g in V1.G_BANDS]
    drop = [h for h in t["hard_cores"] if h["module"] == "ot_s81c_attn_hcore" and int(h["inst"].split("g_h[")[1].split("]")[0]) >= 8]
    assert len(drop) == 32 and sorted({h["origin_um"][1] for h in drop}) == V1.BAND_Y, "unexpected hcore set"
    dn = {h["inst"] for h in drop}
    keep = [h for h in t["hard_cores"] if h["inst"] not in dn]
    assert len(keep) == 40, len(keep)
    ck = t["clock"]
    ck["taps"] = [x for x in ck["taps"] if x["name"].rsplit(".", 1)[0] not in dn]
    assert len(ck["taps"]) == 32
    ct = (ck.get("landing_contract") or {}).get("collector_tree") or {}
    if "core_resets" in ct:
        ct["core_resets"] = [r for r in ct["core_resets"] if r["inst"] not in dn]
    moved = 0
    if grow:
        for h in keep:
            h["origin_um"][1] = fy(h["origin_um"][1])
        for c in t["contents"]:
            if "origin_um" in c:
                c["origin_um"][1] = fy(c["origin_um"][1])
        moved = V1.shift_points(ck, fy, W, H) + V1.shift_points(t.get("reset", {}), fy, W, H) + V1.shift_points(t.get("ft_slots", []), fy, W, H)
        t["outline_um"][1] = r3(H + V1.G_TOTAL)
    boxes, soft = boxes_for(side, band_y, band_hs, M)
    for b in boxes:
        pm = b.get("physical_master", b["module"])
        e = dict(inst=b["inst"], module=b["module"], lef=f"physical/die_plan/s81/cores/svc/prov_1109/{pm}.lef",
                 origin_um=b["origin_um"], outline_um=[b["outline_um"][0], r3(b["outline_um"][1])], orient="R0",
                 track_offset_um=[0.108, 0.012], pins_file=f"inputs/core_pins/{pm}.json", obs_max="M5",
                 lib=f"physical/die_plan/s81/cores/svc/prov_1109/views/{pm}_tt.lib", cells=b["cells"], cells_basis=b["basis"],
                 note=f"DIE-S81-85 svc provider form A 11-09 {b['kind']} {b['name']} fill {b['fill']} (PLANNED provider box on an "
                      f"existing module boundary: LEF/pins/views from the provider kit; registered faces)")
        if "params" in b:
            e["params"] = b["params"]
            e["physical_master"] = pm
            # SVCPROV-PHYSINST-1111: gen_phys.content_physical_identity needs physical_inst with physical_master; the
            # provider box sits at its own logical instance (delta_svcprov_physinst_1111.py fixed the composed plans)
            e["physical_inst"] = b["inst"]
        keep.append(e)
    t["hard_cores"] = keep
    macros = add_new_macros(t, side, band_y, band_hs)
    soft_cells = M["parent_soft"][side]["cells"]
    t["note"] = t.get("note", "") + (f" | DIE-S81-85 svc provider form A 11-09 (H8 RT2, {len(boxes)} hard provider boxes on module "
                                     f"boundaries, parent soft {soft_cells} cells measured" +
                                     (f", {OWNER_G}: 4 bands 259.2 -> 276.48 x3 / 285.12" if grow else ", no growth") +
                                     "; soft regions: " + " ".join(f"{s['name']}={s['rect_um']}" for s in soft) +
                                     f"; (3) {len(macros)} new u_att / u_rsv 1R1W macros (-DOT_SVC_ATT_MEM_MACRO))")
    return boxes, soft, moved, fy, macros


def validate(t, boxes, M, side, macros):
    fails = [f for f in V1.validate_type(t, [dict(b, fill=0.0, cells=0) for b in boxes])]
    fails += [("point under new macro", p, v, n) for p, v, n in point_hits(t, macros)]
    if len(macros) != 31:
        fails.append(("new macro count", len(macros)))
    for b in boxes:
        if b["cells"] > BOX_CELLS_MAX:
            fails.append(("box cells > 150k", b["name"], b["cells"]))
        if b["fill"] > (IRG_FILL_MAX if b["kind"] == "IRG" else BOX_UTIL_MAX):
            fails.append(("box util > limit", b["name"], b["fill"]))
    ps = M["parent_soft"][side]["cells"] + len(t["hard_cores"])
    if ps > CORE_CELLS_MAX:
        fails.append(("parent soft + cores > 400k", ps))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("meas")
    ap.add_argument("--lo-pack", choices=("a", "b"), default="a")
    ap.add_argument("--rdpipe", action="store_true", help="add -DOT_SVC_ATT_RDPIPE (u_att read-data retime, 0 cycle delta)")
    ap.add_argument("--pin-model", choices=("v5", "v6"), default="v5",
                    help="v6 (11-10, svc_prov_pcd_v6_1110.py): pin stages per end (box -> box = 2) + the IRG recipe-4 "
                         "chain edge IRG*->IRG*; default v5 = 1 + relay stations (reproduces the v5 event)")
    a = ap.parse_args()
    global LO_PACK
    LO_PACK = a.lo_pack
    raw = Path(a.base).read_bytes()
    P = json.loads(raw)
    try:
        dump = V1._style(raw, P)
    except SystemExit:
        # a base edited by text splices (main 11-10: T51-SPLIT / CTAP deltas) has no single json.dumps style: write
        # indent=1 (the final_1109 style); the content is unchanged, only the whitespace is normalised
        dump = lambda p: json.dumps(p, indent=1) + "\n"
    M = json.loads(Path(a.meas).read_text())
    pt = P["partition_types"]
    ev = dict(schema="opentallas.s81_svc_split_event.v2", tool="physical/die_plan/s81/svc_prov_event_1109.py",
              supersedes="f5675075e3 (svc_split_event_1109 v1: registered GLUE boxes incl. a new u_att RTL cut)",
              owner=f"COORD 11-09 Decision: form A; {OWNER_G} (form G = svc_lo record)", lane="DIE-S81-85",
              base_plan=a.base, base_plan_sha256=hashlib.sha256(raw).hexdigest(), lo_form="G",
              rtl_defines=["OT_SVC_H8", "OT_SVC_H8_REUSE_RT2", "OT_SVC_MERGE_H4", "OT_SVC_ATT_MEM_MACRO", "OT_IDX_HSLICE_FASTPAD", "OT_IDX_HSLICE_FP_CS",
                           "OT_IDX_HSLICE_HARD"] + (["OT_SVC_ATT_RDPIPE"] if a.rdpipe else []),
              lo_pack=a.lo_pack,
              rtl_defines_svc_lo_only=["OT_IDX_RG3_PRIME"],
              rtl_defines_note="COORD 11-09: OT_IDX_RG3_PRIME in the svc_lo kits only (VERILOG_DEFINES + LEC reference set; "
                               "u_irg on claude/die-s81-85-irg-prime-1109@7b4138bf30; 4 FF per reader, detection only, 0 cycle delta)",
              bind_name_gate=dict(rule="the 31 new contents name their RTL path; each must map to a unique bound instance "
                                       "(tools/die_plan/bound_macro_paths.py) or the event stops (COORD 11-09)",
                                  proxy="svc_prov_bind_gate_1109.json: svc_hi t4 real bound module (codex_svc_hardening_1551 "
                                        "native_smd_c) + the dsdv_svc_mem_la / _ar leaves the bind emits under the define "
                                        "(dsdv_svc_att, dsdv_svc_rs_c are dissolved): 31 / 31 mapped",
                                  real="the first svc kit bind re-checks (kit preflight macro_instances fails the kit before "
                                       "place); the IRG pilot kit bind runs it first"),
              measured=M, types={}, pin_cycle_deltas={}, validation={},
              irg_fastpad=dict(note=IRG_NOTE if a.lo_pack == "a" else IRG_NOTE_B, fill_max=IRG_FILL_MAX if a.lo_pack == "a" else BOX_UTIL_MAX,
                               decision="COORD 11-09 (a)" if a.lo_pack == "a" else "COORD 11-09 native census: option (1), fallback (b) geometry",
                               pilot="build ONE IRG hslice kit first, before the other svc_lo kits; on route / sign-off failure "
                                     "re-form with fallback_b", fallback_b=FALLBACK_B),
              parent_known_setup_risk=PARENT_RISK)
    for side, types, grow in (("hi", HI_TYPES, False), ("lo", LO_TYPES, True)):
        for tn in types:
            t = pt[tn]
            assert t["outline_um"][1] == (2747.52 if side == "hi" else 2773.44), (tn, "not the base outline")
            if side == "lo":
                assert any(c["inst"] == "u_irg" and c["module"] == "dsdv_idx_rg3" for c in t["contents"]), tn
            boxes, soft, moved, fy, macros = split_type(t, side, grow, M)
            if grow and tn in P["reset"]["in_sites"]:
                P["reset"]["in_sites"][tn][1] = fy(P["reset"]["in_sites"][tn][1])
            fails = validate(t, boxes, M, side, macros)
            pc = pin_cycles(boxes, soft, fy)
            if a.pin_model == "v6":
                import svc_prov_pcd_v6_1110 as PCD6
                pc = {e: dict(note=v["note"], worst_um=v["worst_um"],
                              **{k: v[k] for k in ("src_out", "dst_in", "relay_stations", "delta")})
                      for e, v in PCD6.v6_type(dict(pin_cycles=pc, boxes=boxes)).items()}
            ev["types"][tn] = dict(outline_um=t["outline_um"], grow_um=V1.G_TOTAL if grow else 0.0, points_moved=moved,
                                   parent_soft_cells=M["parent_soft"][side]["cells"], hard_core_instances=len(t["hard_cores"]),
                                   parent_run_instances=M["parent_soft"][side]["cells"] + len(t["hard_cores"]),
                                   boxes=[{k: b[k] for k in ("kind", "name", "inst", "module", "origin_um", "outline_um", "cells",
                                                             "area_um2", "fill", "params", "physical_master") if k in b} for b in boxes],
                                   soft_regions=soft, soft_members=M["parent_soft"][side]["members"], pin_cycles=pc,
                                   new_macros=macros,
                                   validation_fails=fails)
            ev["pin_cycle_deltas"][tn] = {k: v["delta"] for k, v in pc.items()}
            assert not fails, (tn, fails[:5])
    ev["validation"]["die"] = V1.die_grow(P, V1.G_TOTAL)
    ev["die_lane_pin_cycle_deltas_note"] = ("0 for every die lane: face windows, face registers and bus widths of all 14 types are "
                                            "unchanged; the cut cycles are type-internal (pin_cycle_deltas) for the svc compiler")
    P["note"] = P["note"] + f" | DIE-S81-85 svc provider form A 11-09 (v2, supersedes f5675075e3): svc_hi + svc_lo, {OWNER_G}"
    txt = dump(P)
    Path(a.out).write_text(txt)
    ev["plan_output"] = a.out
    ev["plan_output_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    Path(a.event).write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps(dict(out_sha=ev["plan_output_sha256"][:16], types=len(ev["types"]),
                          parent={s: M["parent_soft"][s]["cells"] for s in ("hi", "lo")}, die=ev["validation"]["die"]), indent=0))


if __name__ == "__main__":
    main()
