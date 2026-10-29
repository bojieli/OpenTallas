"""DIE-HBM-10 C24 = C23q + (1) the hnx_lane_x hard-child view (HBM-CORES-REBAL-5 ASK, COORD 08:16 accepted) and
(2) the REBAL-6 plan-fixed SRAM arrays + island driver_rects for lanes_plain / programme_store (REBAL-6 ASK default).
usage: apply_c24.py C23Q_DIR OUT_DIR IN_DIR
IN_DIR holds the committed REBAL inputs (claude/hbm-cores-rebal-6-1028@bd8c7c1b54): dr_lp.json, dr_ps.json,
mp3_hnx_n.json, mp3_hnx_s.json (REBAL-4 legal3 SRAM placements), hnx_rp4lp4_leaf_selfcontained_lanecut.sv (REBAL-5 cut
RTL, the hnx_lane_x port list), hnx_lane_cut_estimate.json, and infra_hnx_{n,s}.json (REBAL-4 kit core_infra_plan.json,
island rects of the parents).
What changes:
  * cores/hnx_lane_x__285.12x302.4__c24.json: the child pins in the plan core-pin format (name, layer, x, y; core frame
    R0).  Port list = the cut RTL module (1670 pins = 1669 signal + clk).  Faces: N (top) = shared operand broadcast
    (iv_b ifirst ilast ifp4 itag iwb, 552, M5); S = per-lane x-store data ixb_p (532, M5) toward the xs3 SRAM band;
    W (outer) = the side store sv_f sfirst slast stag swf sxf (531, M4) = the parent W / E face; E (inner) = gather out g
    + the 4 resets (54, M4) on the centre channel; clk = centre entry (M5, interior, 12.8a).
  * c24_side.json core_views: child placement per half (lanes 0-1 W column, lane 2 E column mirrored MY so its outer face
    is the parent E face; operand face at top; lane 1 R0 one gap below lane 0).  Outline 285.12 x 302.4 (33 x 35 units
    of 8.64) = the 289 x 320 estimate snapped down so the S half keeps a >= 10.8 channel over its SRAMs and a 34.56 gap
    for lane 1's operand face (289 x 320 does not fit the S half: 2 x 320 + SRAM top 373.68 + channels > 1036.8).
  * c24_side.json core_arrays: dr_lp / dr_ps macro_placement + islands + driver_rect_um, as REBAL-6 (unchanged values).
  * core_macros.json: hnx_rp3lp3h_n/_s (12 SRAMs + 3 children), lanes_plain (24 SRAMs), programme_store (44 SRAMs)
    UNKNOWN -> KNOWN with basis "plan-fixed (kit --macro-placement)": the EXISTING G0C clock_entry_macro check now tests
    their plan clock entries against these rects.  No new check.
  * die_plan.json: notes only (top + the 128 hnx halves + the lanes_plain / programme_store cores).  Die-level abstract
    (outlines, pins, ports, lanes, clock, reset) unchanged: the children live inside the hard halves.
  * (3, COORD relay of REBAL-10 17:25) lanes__canon pin g_bank_k3_u_bank_write_v moves on its S face (M5, same track
    grid) from the SW corner x 13.656 to x 569.976 under the bank3 SRAMs (IN_DIR/wv3_probe.json: REBAL-10's own
    relay_reg_guide_spec on its m5w1gr macro guides, the other 11 relay boxes kept; free track, 0.048 spacing kept).
Not changed: the C23q PHY split, the xq_pegress view drop, every section 12 rule, every check."""
import json, sys, shutil, os, hashlib, re
from pathlib import Path
SRC, OUT, IN = map(Path, sys.argv[1:4])
G, TRK0, TRK = 8.64, 0.024, 0.048
MIN_CH, HALO = 10.8, 4.32


def r4(v): return round(v, 4)
def trk(v): return round(TRK0 + round((v - TRK0) / TRK) * TRK, 3)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
rep = dict(event="C24 (DIE-HBM-10)", source=str(SRC / "die_plan.json"), source_sha=sha(SRC / "die_plan.json")[:12],
           inputs={f.name: sha(f)[:16] for f in sorted(IN.iterdir())},
           inputs_from="claude/hbm-cores-rebal-6-1028@bd8c7c1b54 results/hbm_cores_rebal_{4,5,6}_1028 + REBAL-4 kits "
                       "core_infra_plan.json (intel2:/srv/opentallas-scratch2/claude/hbm-cores-rebal-4/kits)")
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists():
    shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")

# ---------------- (1) hnx_lane_x view ----------------
sv = (IN / "hnx_rp4lp4_leaf_selfcontained_lanecut.sv").read_text()
hdr = re.search(r"module hnx_lane_x \((.*?)\);", sv, re.S).group(1)
ports = []
for chunk in re.split(r"\b(?=input\b|output\b)", " ".join(hdr.split())):
    m = re.match(r"(input|output) wire (?:\[(\d+):0\] )?(.*)", chunk.strip())
    if not m:
        continue
    for n in m.group(3).split(","):
        if n.strip():
            ports.append((m.group(1), n.strip(), int(m.group(2)) + 1 if m.group(2) else 1))
PW = {n: w for _, n, w in ports}
assert PW["iwb"] == 532 and PW["ixb_p"] == 532 and PW["swf"] == 256 and PW["g"] == 50, PW
CW, CH = 33 * G, 35 * G                                   # 285.12 x 302.4
FACE = dict(N=["iv_b", "ifirst", "ilast", "ifp4", "itag", "iwb"],
            S=["ixb_p"],
            W=["sv_f", "sfirst", "slast", "stag", "swf", "sxf"],
            E=["r_bdc", "r_tcc", "r_g", "r_x", "g"])
assigned = [p for f in FACE.values() for p in f]
assert sorted(assigned + ["clk"]) == sorted(PW), set(PW) ^ set(assigned + ["clk"])


def bits(names):
    return [f"{n}[{i}]" if PW[n] > 1 else n for n in names for i in range(PW[n])]


pins, dens = [], {}
for f, names in FACE.items():
    b = bits(names)
    L = CW if f in "NS" else CH
    marg = 2.16
    step = (L - 2 * marg) / len(b)
    pos = [trk(marg + (i + 0.5) * step) for i in range(len(b))]
    assert len(set(pos)) == len(pos) and min(pos[i + 1] - pos[i] for i in range(len(pos) - 1)) >= 2 * TRK - 1e-9, f
    lay = "M5" if f in "NS" else "M4"
    for n, p in zip(b, pos):
        x, y = {"N": (p, CH), "S": (p, 0.0), "W": (0.0, p), "E": (CW, p)}[f]
        pins.append(dict(name=n, layer=lay, x=r4(x), y=r4(y)))
    # pins per 10-um window (plan face rule: 6 pins/um over 2 layers -> 60 per window)
    win = max(sum(1 for q in pos if w0 <= q < w0 + 10) for w0 in [k * 0.5 for k in range(int((L - 10) / 0.5) + 1)])
    dens[f] = dict(pins=len(b), layer=lay, face_um=r4(L), per_um=round(len(b) / L, 2), max_per_10um=win)
pins.append(dict(name="clk", layer="M5", x=trk(CW / 2), y=r4(CH / 2)))
assert len(pins) == sum(PW.values()) == 1670
PIN_FILE = f"cores/hnx_lane_x__{CW:g}x{CH:g}__c24.json"
json.dump(pins, open(OUT / PIN_FILE, "w"), indent=0)
rep["hnx_lane_x"] = dict(outline_um=[r4(CW), r4(CH)], pins=len(pins), pins_file=PIN_FILE, faces=dens,
                         clock_entry=[trk(CW / 2), r4(CH / 2)],
                         port_count_note="RTL hnx_lane_x: 1669 signal (1615 data in + 4 resets + 50 out) + clk = 1670; "
                                         "REBAL-5 quoted ~1672 (est.)")

# child placement per half (parent frame = kit DIE_AREA frame, CORE_AREA inset 4.32)
CEN = json.load(open(SRC / "clock_entries.json"))
sram = json.load(open(IN / "mp3_hnx_n.json")), json.load(open(IN / "mp3_hnx_s.json"))
SW, SH = 94.824, 41.04                                    # ot_sram_1r1w_128x256_m1_r2c2 LEF SIZE
views, cm_new, checks = {}, {}, {}
GAP = 4 * G                                               # 34.56 between lane 1 top and lane 0 bottom
for h, mp, Hh in (("n", sram[0], 1209.6), ("s", sram[1], 1036.8)):
    mod = f"hnx_rp3lp3h_{h}"
    Wp = 630.72
    top = Hh - G - CH                                     # lanes 0 / 2 top-aligned one lattice unit below the N edge
    xw, xe = G, Wp - G - CW
    ch = [dict(inst="u_lane0", module="hnx_lane_x", origin_um=[r4(xw), r4(top)], orient="R0", face="W"),
          dict(inst="u_lane1", module="hnx_lane_x", origin_um=[r4(xw), r4(top - GAP - CH)], orient="R0", face="W"),
          dict(inst="u_lane2", module="hnx_lane_x", origin_um=[r4(xe), r4(top)], orient="MY", face="E")]
    for c in ch:
        x, y = c["origin_um"]; c["outline_um"] = [r4(CW), r4(CH)]; c["rect_um"] = [r4(x), r4(y), r4(x + CW), r4(y + CH)]
        c["pins_file"] = PIN_FILE
    srs = [dict(name=m["k"], master=m["macro"], rect_um=[r4(m["origin_um"][0]), r4(m["origin_um"][1]),
                                                         r4(m["origin_um"][0] + SW), r4(m["origin_um"][1] + SH)])
           for m in mp["macro_placement"]]
    # clearance: child vs SRAM (>= MIN_CH body gap, kit_contract channel), child vs child, inside CORE_AREA
    def gap(a, b):
        dx = max(b[0] - a[2], a[0] - b[2], 0.0); dy = max(b[1] - a[3], a[1] - b[3], 0.0)
        return max(dx, dy) if (dx == 0 or dy == 0) else (dx ** 2 + dy ** 2) ** 0.5
    cs = [(c["inst"], s["name"], r4(gap(c["rect_um"], s["rect_um"]))) for c in ch for s in srs]
    cc = [(a["inst"], b["inst"], r4(gap(a["rect_um"], b["rect_um"]))) for i, a in enumerate(ch) for b in ch[i + 1:]]
    inside = all(c["rect_um"][0] >= 4.32 and c["rect_um"][1] >= 4.32 and c["rect_um"][2] <= Wp - 4.32 and
                 c["rect_um"][3] <= Hh - 4.32 for c in ch)
    ents = [e for t in CEN.values() for e in t.values() if e.get("module") == mod]
    eset = sorted({(tuple(e["xy_um"]), tuple(e["island_um"])) for e in ents})
    def ov(a, b): return min(a[2], b[2]) - max(a[0], b[0]) > 1e-3 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-3
    ent_hits = [(xy, isl, c["inst"]) for xy, isl in eset for c in ch if ov(isl, c["rect_um"])]
    infra = json.load(open(IN / f"infra_hnx_{h}.json"))
    isl = sorted({tuple(c["rect_um"]) for c in infra["cells"]})
    isl_in = sorted({i for i in isl for c in ch if ov(i, c["rect_um"])})
    checks[mod] = dict(min_child_sram_gap_um=min(g for *_, g in cs), worst=min(cs, key=lambda t: t[2]),
                       child_child_gap_um=[g for *_, g in cc], children_inside_core_area=inside,
                       parent_clock_entries=[list(e) for e in eset], parent_entry_over_child=ent_hits,
                       centre_channel_um=[r4(xw + CW), r4(xe)], channel_width_um=r4(xe - xw - CW),
                       lane1_top_gap_um=r4(GAP), sram_top_um=max(s["rect_um"][3] for s in srs),
                       rebal4_islands=len(isl), rebal4_islands_inside_children=len(isl_in),
                       pass_=bool(min(g for *_, g in cs) >= MIN_CH - 1e-6 and inside and not ent_hits
                                  and min(g for *_, g in cc) >= 0))
    assert checks[mod]["pass_"], checks[mod]
    views[mod] = dict(rule="REBAL-5 ASK hnx_lane_x (COORD 08:16 accepted): hard-child parent view, C24 (DIE-HBM-10)",
                      outline_um=[Wp, Hh], children=ch,
                      child=dict(module="hnx_lane_x", outline_um=[r4(CW), r4(CH)], pins=len(pins), pins_file=PIN_FILE,
                                 clock_entry="centre (M5 interior pin, 12.8a)", cells_est=226600,
                                 equivalence="yosys equiv 13164/13164 PROVEN (REBAL-5, CHECKED)",
                                 rtl="results/hbm_cores_rebal_5_1028/hnx_rp4lp4_leaf_selfcontained_lanecut.sv"),
                      parent_srams=srs, operand_face="N (top); lane 1's operand face opens into the 34.56 gap",
                      parent_clock_entry=[list(e) for e in eset],
                      notes=["parent clock entry stays in the centre channel (clear of the children)",
                             f"{len(isl_in)} of {len(isl)} REBAL-4 in-core islands fall inside the children: the child "
                             "has its own centre entry; the parent infra plan is regenerated with the hard children (REBAL-11)"],
                      status="plan view; kit + child latency match at the child pin (12.3/12.16e) owed by REBAL-11")
    cm_new[mod] = dict(status="KNOWN", outline_um=[Wp, Hh],
                       basis="plan-fixed (C24): REBAL-4 legal3 SRAMs (kit --macro-placement) + 3 hnx_lane_x hard children",
                       macros=srs + [dict(name=c["inst"], master="hnx_lane_x", rect_um=c["rect_um"]) for c in ch],
                       sources=[dict(file="claude/hbm-cores-rebal-6-1028@bd8c7c1b54:results/hbm_cores_rebal_4_1028/"
                                          f"mp3_hnx_{h}.json", sha256=sha(IN / f"mp3_hnx_{h}.json"))])
rep["hnx_checks"] = checks

# ---------------- (2) REBAL-6 arrays + driver_rects ----------------
arrays = {}
for key, f, master in (("ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526", "dr_lp.json", "ot_sram_1r1w_128x256_m1_r2c2"),
                       ("ot_hgi_sfu_programme_store_r10", "dr_ps.json", "ot_sram_1r1w_512x256_m1_r2c2")):
    d = json.load(open(IN / f)); w, hh = d["macro_wh"]
    outl = next(c["outline_um"] for t in T.values() for c in t.get("hard_cores", []) if c.get("module") == key)
    assert d["fence"][2] <= outl[0] and d["fence"][3] <= outl[1], (key, d["fence"], outl)
    rects = [dict(name=m["inst"], master=master, rect_um=[r4(m["origin_um"][0]), r4(m["origin_um"][1]),
                                                          r4(m["origin_um"][0] + w), r4(m["origin_um"][1] + hh)])
             for m in d["macro_placement"]]
    ents = sorted({(tuple(e["xy_um"]), tuple(e["island_um"])) for t in CEN.values() for e in t.values()
                   if e.get("module") == key})
    hits = [(list(xy), r["name"]) for xy, isl in ents for r in rects
            if min(isl[2], r["rect_um"][2]) - max(isl[0], r["rect_um"][0]) > 1e-3
            and min(isl[3], r["rect_um"][3]) - max(isl[1], r["rect_um"][1]) > 1e-3]
    isl_match = [i["rect_um"] for i in d["islands"] if any(tuple(i["rect_um"]) == isl for _, isl in ents)]
    arrays[key] = dict(source=f"REBAL-6 bd8c7c1b54 {f}", macro_master=master, macro_wh=d["macro_wh"],
                       macro_rules=dict(halo_um=d["halo"], min_channel_um=d["min_channel"],
                                        interior_channel_um=d["interior_channel_um"], basis=d["basis"]),
                       fence=d["fence"], macro_placement=d["macro_placement"],
                       islands=d["islands"], max_detour_um=d["max_detour_um"], max_move_um=d["max_move_um"],
                       plan_clock_entries=[list(e[0]) for e in ents])
    cm_new[key] = dict(status="KNOWN", outline_um=outl, basis="plan-fixed (C24): REBAL-6 array (kit --macro-placement)",
                       macros=rects, sources=[dict(file=f"claude/hbm-cores-rebal-6-1028@bd8c7c1b54:results/"
                                                        f"hbm_cores_rebal_6_1028/{f}", sha256=sha(IN / f))])
    rep.setdefault("arrays", {})[key] = dict(macros=len(rects), islands=len(d["islands"]),
                                             driver_rects=sum(1 for i in d["islands"] if i.get("driver_rect_um")),
                                             max_detour_um=d["max_detour_um"], entry_over_macro=hits,
                                             entry_is_plan_island=bool(isl_match))

# ---------------- (3) lanes__canon bank3 write_v pin ----------------
WVF = "cores/ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__760.32x725.76__canon.json"
WV = "g_bank_k3_u_bank_write_v"
probe = json.load(open(IN / "wv3_probe.json"))
hop, X_NEW = probe["best"][0][0], probe["best"][0][1]
wp = json.load(open(OUT / WVF))
row = next(r for r in wp if r["name"] == WV)
others = [r["x"] for r in wp if r["name"] != WV and r["layer"] == row["layer"] and abs(r["y"] - row["y"]) < 1e-6]
assert min(abs(X_NEW - x) for x in others) >= 0.048 - 1e-6 and abs((X_NEW - TRK0) / TRK - round((X_NEW - TRK0) / TRK)) < 1e-6
old = dict(row); row["x"] = X_NEW
json.dump(wp, open(OUT / WVF, "w"), indent=0)
rep["bank3_write_v"] = dict(pins_file=WVF, pin=WV, before=old, after=dict(row),
                            hop_before_um=max(probe["base"]["hop_pins_um"], probe["base"]["hop_sinks_um"]),
                            pin_hop_before_um=probe["base"]["hop_pins_um"], relay_before_um=probe["base"]["point_um"],
                            hop_after_um=hop, pin_hop_after_um=probe["best"][0][3], relay_after_um=probe["best"][0][2],
                            model="REBAL-10 gen_core_kit_hbm.relay_reg_guide_spec (L1, 5-um grid), kit _c20ek2m_m5w1gr guides")

# ---------------- write ----------------
CM = json.load(open(SRC / "core_macros.json"))
for k, v in cm_new.items():
    rep.setdefault("core_macros", {})[k] = [CM["cores"].get(k, {}).get("status"), "KNOWN"]
    CM["cores"][k] = v
CM["note"] = CM.get("note", "") + " | C24 (DIE-HBM-10): hnx halves + lanes_plain + programme_store plan-fixed (KNOWN)"
json.dump(CM, open(OUT / "core_macros.json", "w"), indent=1)
side = dict(core_views=views, core_arrays=arrays,
            note="C24 side data (non-schema): hard children inside hard halves and plan-fixed core macro arrays")
json.dump(side, open(OUT / "c24_side.json", "w"), indent=1)
n_note = 0
for t in T.values():
    for c in t.get("hard_cores", []):
        m = c.get("module")
        if m in views:
            c["note"] = (c.get("note") or "") + f" | C24: 3 hard children hnx_lane_x ({PIN_FILE}; c24_side.json core_views)"
            n_note += 1
        elif m == "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77":
            c["note"] = (c.get("note") or "") + f" | C24: {WV} pin x 13.656 -> {X_NEW} (S face, under bank3; REBAL-10 hop)"
            n_note += 1
        elif m in arrays:
            c["note"] = (c.get("note") or "") + " | C24: plan-fixed SRAM array + island driver_rects (c24_side.json core_arrays)"
            n_note += 1
P["note"] = (P.get("note") or "") + (" | C24 (DIE-HBM-10 10-28): hnx_lane_x hard-child view (3 per half) + REBAL-6 "
                                     "arrays/driver_rects; core_macros KNOWN for hnx halves, lanes_plain, programme_store")
rep["notes_updated"] = n_note
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
rep["plan_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:8]
for f in os.listdir(SRC):
    if f.endswith(".json") and not (OUT / f).exists():
        shutil.copy2(SRC / f, OUT / f)
json.dump(rep, open(OUT / "c24_event_report.json", "w"), indent=1, default=str)
print(json.dumps(dict(plan_sha=rep["plan_sha"], hnx_lane_x={k: v for k, v in rep["hnx_lane_x"].items() if k != "faces"},
                      faces=dens, checks={k: {a: b for a, b in v.items() if a != "parent_clock_entries"} for k, v in checks.items()},
                      arrays=rep["arrays"], bank3_write_v=rep["bank3_write_v"], core_macros=rep["core_macros"], notes=n_note), indent=1, default=str))
