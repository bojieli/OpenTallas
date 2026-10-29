"""DIE-HBM-10 C25b = C25a + (1) KITS-2/KITS-3 macro placements into core_macros.json, (2) vp4_banks_cp +34.56 um and
host_cp_rxs +48 um height (R-SRAM-ENTRY fit, parent slot checked), (5) TOK-HBM-1 fused root: ot_hnx_fused_hub_n4ext
(u_mu_fused_root) + ot_hnx_fused_host_program (u_mu_fused_program) in partition root between the two hub n4 outputs,
n4 -> root up/down lanes as plan buses (widths from the RTL), per-role reset-delivery side table.
Items (3) family collapse and (4) cxport re-cut are estimate-only (c25b_estimates.json, not applied).
usage: apply_c25b.py C25A_DIR OUT_DIR IN_DIR SHADOW_DIR MAINSNAP_TOOLS_DIE_PLAN
No check, no section-12 rule, no other outline changes."""
import json, sys, shutil, os, hashlib, re, math
from pathlib import Path
SRC, OUT, IN, SH, TOOLS = map(Path, sys.argv[1:6])
G, TRK0, TRK, EDGE = 8.64, 0.024, 0.048, 0.096
SMAX = 360.0                                   # planned hop (relay_um 405 - legalisation margin, QUAD-7 practice)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def r4(v): return round(v, 4)
def trk(v): return r4(TRK0 + round((v - TRK0) / TRK) * TRK)
def face_of(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
def on_lat(v): return abs(v / G - round(v / G)) < 1e-6


P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists():
    shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
for f in os.listdir(SRC):
    if f.endswith(".json") and f != "die_plan.json" and not (OUT / f).exists():
        shutil.copy2(SRC / f, OUT / f)
rep = dict(event="C25b (DIE-HBM-10)", source=str(SRC / "die_plan.json"), source_sha=sha(SRC / "die_plan.json")[:8])
CM = json.load(open(OUT / "core_macros.json"))
CC = json.load(open(OUT / "core_conns.json"))
CE = json.load(open(OUT / "clock_entries.json"))

# ------------------------------------------------------------------ (1) core_macros: KITS-2 delta + KITS-3 FEASIBLE
d2 = json.load(open(IN / "kits2_core_macros_delta.json"))
it1 = {}
for mod, v in d2["cores"].items():
    old = CM["cores"].get(mod, {})
    assert [round(x, 3) for x in old["outline_um"]] == [round(x, 3) for x in v["outline_um"]], mod
    CM["cores"][mod] = dict(v, note="C25b: KITS-2 core_macros_delta (origin/claude/hbm-cores-kits-2-1028)")
    it1[mod] = dict(source="KITS-2 delta", was=old.get("status"), now=v["status"], macros=len(v["macros"]))
K3 = IN / "results/hbm_cores_kits_3/mp"


def from_k3(mod, est_f, mp_f, status, src_note):
    est = json.load(open(est_f)); mp = json.load(open(mp_f))
    ms = est["masters"]
    macros = []
    for m in mp["macro_placement"]:
        w, h = ms[m["macro"]]["w"], ms[m["macro"]]["h"]
        x, y = m["origin_um"]; assert m["orient"] == "R0"
        macros.append(dict(name=m["k"], master=m["macro"], rect_um=[r4(x), r4(y), r4(x + w), r4(y + h)], orient="R0"))
    return dict(status=status, outline_um=est["outline_um"], basis="rule", rule=est["rule"],
                verdict=est["verdict"], macros=macros, recipe_macros=sorted(ms),
                sources=[dict(file=str(mp_f), sha256=sha(mp_f)), dict(file=str(est_f), sha256=sha(est_f))],
                note=src_note + "; macro names are k below the kit face shell (macro_placement.v1)")


for mod in ("ot_hbm_idx_topk_link_static", "ot_hbm_svc_sm_group_rel_id", "ot_pdie_serdes"):
    old = CM["cores"][mod]
    v = from_k3(mod, K3 / f"{mod}.est.json", K3 / f"{mod}.json", "KNOWN",
                "C25b: HBM-CORES-KITS-3 FEASIBLE R-SRAM-ENTRY placement (claude/hbm-cores-kits-3-1028@b0ae51516f)")
    assert [round(x, 3) for x in old["outline_um"]] == [round(x, 3) for x in v["outline_um"]], mod
    CM["cores"][mod] = v
    it1[mod] = dict(source="KITS-3 mp", was=old["status"], now="KNOWN", macros=len(v["macros"]), verdict=v["verdict"])
it1["pending"] = {"ot_hgi_sfu_core_split3__opstore_b / ot_hbm_svc_wb_kport_q": "KITS-3 placements exist but the "
                  "directive keeps these outlines unchanged; not in the FEASIBLE adopt list (left as in C25a)"}
rep["item1_core_macros"] = it1

# ------------------------------------------------------------------ (2) outline growth with parent slot checks
GROW = {  # module: (new H, kit shadow est/mp, status, parent placement rule)
    "ot_hgi_dma_back_static_vp4_banks_cp": dict(H=275.4, shadow="vp4e_120.96", status="PLAN-TRIAL", move="keep_top"),
    "ot_hbm_host_cp_rxs": dict(H=480.0, shadow="hcpe_216.0", status="KNOWN", move="root_slot"),
}


def boxes_of(t, skip):
    out = []
    for c in t["hard_cores"]:
        if c["inst"] in skip:
            continue
        dx, dy = c.get("track_offset_um", [0, 0])
        x, y = c["origin_um"][0] + dx, c["origin_um"][1] + dy
        out.append((c["inst"], x, y, x + c["outline_um"][0], y + c["outline_um"][1]))
    return out


def overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


it2 = {}
for mod, g in GROW.items():
    users = [(tn, c) for tn, t in T.items() for c in t.get("hard_cores", []) if c["module"] == mod]
    pfs = {c["pins_file"] for _, c in users}; assert len(pfs) == 1, pfs
    W, H0 = [round(v, 3) for v in users[0][1]["outline_um"]]
    H1 = g["H"]; dH = r4(H1 - H0)
    old_pf = pfs.pop()
    pins = json.load(open(OUT / old_pf))
    nN = 0
    for p in pins:                                   # core frame grows at the top: N-face pins follow the new edge
        if face_of(p["x"], p["y"], W, H0) == "N" and abs(p["y"] - H0) < 0.5:
            p["y"] = r4(p["y"] + dH); nN += 1
    new_pf = f"cores/{mod}__{W:g}x{H1:g}__c25b.json"
    json.dump(pins, open(OUT / new_pf, "w"), indent=0)
    est = json.load(open(SH / f"{g['shadow']}.est.json"))
    rows = []
    for tn, c in users:
        t = T[tn]
        ox, oy = c["origin_um"]
        dx, dy = c.get("track_offset_um", [0, 0])
        if g["move"] == "keep_top":                  # parent: top edge fixed (calendar abuts above), grow downward
            ny = r4(oy - dH)
            if not on_lat(ny):
                ny = r4(math.floor(ny / G) * G)
        else:                                        # root: lowest lattice origin above u_hb_idx__link that fits
            ny = None
            for k in range(int((oy - 60) / G), int((oy + 60) / G) + 1):
                cand = r4(k * G)
                box = (ox + dx, cand + dy, ox + dx + W, cand + dy + H1)
                if not any(overlap(box, b[1:]) for b in boxes_of(t, {c["inst"]})):
                    ny = cand; break
        assert ny is not None and on_lat(ny), (tn, c["inst"])
        box = (ox + dx, ny + dy, ox + dx + W, ny + dy + H1)
        hits = [b[0] for b in boxes_of(t, {c["inst"]}) if overlap(box, b[1:])]
        assert not hits, (tn, c["inst"], hits)
        assert box[1] >= -1e-6 and box[3] <= t["outline_um"][1] + 1e-6
        d_or = r4(ny - oy)                           # die shift of W/E/S pins + clock entry; N pins: d_or + dH
        old_top = oy + dy + H0
        c.update(origin_um=[ox, ny], outline_um=[W, H1], pins_file=new_pf)
        dropped = [k for k in ("lef", "lib") if c.pop(k, None)]
        c["note"] = (c.get("note") or "") + (f" | C25b: +{dH:g} um height (R-SRAM-ENTRY {est['verdict']} C="
                                             f"{est.get('columns')}, KITS-3 rule on a shadow kit), entry kept at the "
                                             f"core-frame island; origin y {oy:g} -> {ny:g}" +
                                             (f"; stale views {dropped} dropped (PENDING-VIEW)" if dropped else ""))
        for ct in t.get("contents", []):
            if ct["inst"] == c["inst"]:
                ct.update(origin_um=[ox, ny], outline_um=[W, H1])
        ntap = 0
        for tp in t.get("clock", {}).get("taps", []):
            if tp["name"].split(".")[0] == c["inst"]:
                tp["xy"] = [tp["xy"][0], r4(tp["xy"][1] + d_or)]; ntap += 1
        nst = 0
        obox = (ox + dx - 1, oy + dy - 1, ox + dx + W + 1, old_top + 1)
        for st in t.get("internal_stations", []):
            if c["inst"] in (str(st.get("capture", "")).split(".")[0], str(st.get("launch", "")).split(".")[0]) \
                    or st.get("conn", "").startswith(f"core:{c['inst']}."):
                for key in ("to_um", "from_um"):
                    x, y = st[key]
                    if obox[0] <= x <= obox[2] and obox[1] <= y <= obox[3]:
                        st[key] = [x, r4(y + d_or + (dH if abs(y - old_top) < 1.0 else 0.0))]; nst += 1
        rows.append(dict(type=tn, inst=c["inst"], origin_y=[oy, ny], box=[r4(v) for v in box], taps_moved=ntap,
                         station_ends_moved=nst, views_dropped=dropped))
    mp = json.load(open(SH / f"{g['shadow']}.mp.json"))
    mm = from_k3(mod, SH / f"{g['shadow']}.est.json", SH / f"{g['shadow']}.mp.json", g["status"],
                 f"C25b: R-SRAM-ENTRY at the C25b outline {W:g}x{H1:g} (KITS-3 mp_rule_c.py on a shadow kit "
                 f"{g['shadow']}: DIE/CORE_AREA grown, entry island unchanged)")
    assert [round(x, 3) for x in mm["outline_um"]] == [W, H1]
    CM["cores"][mod] = mm
    it2[mod] = dict(outline=[[W, H0], [W, H1]], pins_file=new_pf, n_face_pins_moved=nN, verdict=est["verdict"],
                    columns=est.get("columns"), channel_um=est.get("channel_um"),
                    escape_use=[e.get("use") for e in est.get("escape", [])], instances=rows)
rep["item2_outlines"] = it2

# ------------------------------------------------------------------ (5) fused root + programme in partition root
R_T = T["root"]; HUBS = ("q_hub_nw", "q_hub_ne")
UPW, DNW = 271, 173                                   # ot_hnx_fused_tree.sv UW/DW == n4ext up_*/down_* ports
N4W, N4H, PGW, PGH = 216.0, 207.36, 207.36, 129.6
N4O, PGO = [734.4, 5503.68], [734.4, 5356.8]
for o in N4O + PGO:
    assert on_lat(o)
# die windows on the hub E (NW) / root W and hub W (NE, MY) / root E faces: free span above L156_0 (8761-9856)
UPWIN, DNWIN = [9873.0, 9923.2], [9933.0, 9965.04]
hub_y0 = 6065.28; root_y0 = 4337.28


def spread(n, a, b):
    if n == 1:
        return [trk((a + b) / 2)]
    out = [trk(a + i * (b - a) / (n - 1)) for i in range(n)]
    assert all(out[i + 1] - out[i] >= 0.096 - 1e-9 for i in range(n - 1)), (n, a, b)
    return out


def side_pins(names, face, a, b, W_, H_):
    lay = "M4" if face in "WE" else "M5"
    cs = spread(len(names), a, b)
    if face == "W": return [dict(name=n, layer=lay, x=EDGE, y=c) for n, c in zip(names, cs)]
    if face == "E": return [dict(name=n, layer=lay, x=r4(W_ - EDGE), y=c) for n, c in zip(names, cs)]
    if face == "S": return [dict(name=n, layer=lay, x=c, y=EDGE) for n, c in zip(names, cs)]
    return [dict(name=n, layer=lay, x=c, y=r4(H_ - EDGE)) for n, c in zip(names, cs)]


def bits(n, w): return [f"{n}[{i}]" for i in range(w)] if w > 1 else [n]


up_lo, up_hi = UPWIN[0] - root_y0 - N4O[1], UPWIN[1] - root_y0 - N4O[1]
dn_lo, dn_hi = DNWIN[0] - root_y0 - N4O[1], DNWIN[1] - root_y0 - N4O[1]
JOB = bits("job_v", 1) + bits("job", 217) + bits("wsc", 8) + bits("pk5", 6) + bits("pb5", 1)
STAT = ["done", "fault", "busy"]
n4p = (side_pins(bits("up_nw", UPW), "W", up_lo, up_hi, N4W, N4H) + side_pins(bits("down_nw", DNW), "W", dn_lo, dn_hi, N4W, N4H)
       + side_pins(bits("up_ne", UPW), "E", up_lo, up_hi, N4W, N4H) + side_pins(bits("down_ne", DNW), "E", dn_lo, dn_hi, N4W, N4H)
       + side_pins(JOB + STAT, "S", 4.32, 202.0, N4W, N4H)
       + [dict(name="clk", layer="M5", x=trk(N4W / 2 - 0.02), y=r4(N4H / 2), w=0.048, h=0.48),
          dict(name="rst_n", layer="M5", x=trk(N4W / 2 + 0.07), y=r4(N4H - EDGE))])
CFG = (bits("cfg_v", 1) + bits("cfg_target", 8) + bits("cfg_addr", 12) + bits("cfg_data", 256) + bits("desc_v", 1)
       + bits("desc_base", 12) + bits("desc_limit", 13) + bits("desc_loops", 16) + bits("launch_v", 1)
       + ["ready", "active", "done", "fault", "rst_n"])
pgp = (side_pins(JOB + ["root_done", "root_fault", "root_busy"], "N", 4.32, 202.0, PGW, PGH)
       + side_pins(CFG, "S", 4.32, 203.04, PGW, PGH)
       + [dict(name="clk", layer="M5", x=trk(PGW / 2 - 0.02), y=r4(PGH / 2), w=0.048, h=0.48)])
for pl, Wc, Hc in ((n4p, N4W, N4H), (pgp, PGW, PGH)):
    assert len({p["name"] for p in pl}) == len(pl)
N4PF, PGPF = "cores/ot_hnx_fused_hub_n4ext__216x207.36__c25b.json", "cores/ot_hnx_fused_host_program__207.36x129.6__c25b.json"
json.dump(n4p, open(OUT / N4PF, "w"), indent=0); json.dump(pgp, open(OUT / PGPF, "w"), indent=0)
assert len(n4p) == 2 + 2 * UPW + 2 * DNW + 217 + 1 + 8 + 6 + 1 + 3      # == RTL port bits
assert len(pgp) == 2 + 1 + 8 + 12 + 256 + 1 + 12 + 13 + 16 + 1 + 4 + 1 + 217 + 8 + 6 + 1 + 3
for c in R_T["hard_cores"]:
    for b in ((N4O[0], N4O[1], N4O[0] + N4W, N4O[1] + N4H), (PGO[0], PGO[1], PGO[0] + PGW, PGO[1] + PGH)):
        dx, dy = c.get("track_offset_um", [0, 0])
        assert not overlap(b, (c["origin_um"][0] + dx, c["origin_um"][1] + dy, c["origin_um"][0] + dx + c["outline_um"][0],
                               c["origin_um"][1] + dy + c["outline_um"][1])), c["inst"]
SRC_RTL = ("rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv (ports), ot_hnx_fused_tree.sv UW=271/DW=173; yosys 0.x ASAP7 "
           "RVT TT abc map (c25b_ys): n4ext 144300 cells 15826 um2 + 2 x ot_sram_1r1w_128x256_m1_r2c2 + 1 x "
           "ot_sram_1r1w2c_32x64_m1; host_program 2154 cells 316 um2 + 2 x ot_sram_1r1w_256x256_m2_r2c2")
R_T["hard_cores"] += [
    dict(inst="u_mu_fused_root", module="ot_hnx_fused_hub_n4ext", origin_um=N4O, outline_um=[N4W, N4H],
         track_offset_um=[0.0, 0.0], pins_file=N4PF, obs_max="M5",
         note="C25b TOK-HBM-1: fused root (t5, N4EXT=1, DELIVERED_RESET=1) between the NW/NE hub n4 outputs; W face up_nw/down_nw, E face "
              "up_ne/down_ne, S face job/straps/status to u_mu_fused_program; fill est (15826 std + 8342 macro) / 44790 "
              "= 0.54 | " + SRC_RTL),
    dict(inst="u_mu_fused_program", module="ot_hnx_fused_host_program", origin_um=PGO, outline_um=[PGW, PGH],
         track_offset_um=[0.0, 0.0], pins_file=PGPF, obs_max="M5",
         note="C25b TOK-HBM-1 (DELIVERED_RESET=1): fused provider/programme under u_mu_fused_root (N face job -> root S face, 17.28 um); "
              "S face boot ingress cfg/desc/launch = PENDING source (provider_contract boot_ingress_missing); fill est "
              "(316 + 14194 macro) / 26874 = 0.54")]
R_T["contents"] += [
    dict(inst="u_mu_fused_root", module="ot_hnx_fused_hub_n4ext", status="new", cells=144300,
         note="C25b fused root (yosys ASAP7 map)", origin_um=N4O, outline_um=[N4W, N4H]),
    dict(inst="u_mu_fused_program", module="ot_hnx_fused_host_program", status="new", cells=2154,
         note="C25b fused programme (yosys ASAP7 map)", origin_um=PGO, outline_um=[PGW, PGH])]
R_T["cells"] = int(R_T["cells"]) + 144300 + 2154
for inst, o, w, h, mod in (("u_mu_fused_root", N4O, N4W, N4H, "ot_hnx_fused_hub_n4ext"),
                           ("u_mu_fused_program", PGO, PGW, PGH, "ot_hnx_fused_host_program")):
    ex, ey = r4(round(w / 2 / 4.32) * 4.32), r4(round(h / 2 / 4.32) * 4.32)
    CE.setdefault("root", {})[inst] = dict(xy_um=[ex, ey], island_um=[r4(ex - 4.32), r4(ey - 4.32), r4(ex + 4.32), r4(ey + 4.32)],
                                           port="clk", merged_clock_ports=[], tap=f"{inst}.clk",
                                           source="C25b plan centre entry on the 4.32 PG lattice (12.8a)", stack=["M9", "M5"],
                                           latency_target_tt_ps=250.0, latency_target_ff_ps=202.5, module=mod)
    R_T["clock"]["taps"].append(dict(name=f"{inst}.clk", kind="core", xy=[r4(o[0] + ex), r4(o[1] + ey)],
                                     insertion_ps=250.0, insertion_ff_ps=202.5, budget_owner=mod,
                                     note="C25b: plan centre clock entry; insertion = plan latency target (no view yet, "
                                          "UNCHECKED until the core kit reports it)"))
    CM["cores"][mod] = dict(status="UNKNOWN", outline_um=[w, h], why="C25b new core: no kit yet", rejected=[],
                            recipe_macros=(["ot_sram_1r1w2c_32x64_m1", "ot_sram_1r1w_128x256_m1_r2c2"] if "n4ext" in mod
                                           else ["ot_sram_1r1w_256x256_m2_r2c2"]))
J = {f"{n}": [f"core:u_mu_fused_program.{n}"] for n in ("job_v", "job", "wsc", "pk5", "pb5")}
CC.setdefault("root", {})["u_mu_fused_root"] = dict(
    clk=["tap:u_mu_fused_root.clk"], up_nw=["bus:n4x_up_nw_i"], up_ne=["bus:n4x_up_ne_i"],
    down_nw=["bus:n4x_dn_nw_o"], down_ne=["bus:n4x_dn_ne_o"], done=["core:u_mu_fused_program.root_done"],
    fault=["core:u_mu_fused_program.root_fault"], busy=["core:u_mu_fused_program.root_busy"], **J)
CC["root"]["u_mu_fused_program"] = dict(
    clk=["tap:u_mu_fused_program.clk"], root_done=["core:u_mu_fused_root.done"],
    root_fault=["core:u_mu_fused_root.fault"], root_busy=["core:u_mu_fused_root.busy"],
    **{n: [f"core:u_mu_fused_root.{n}"] for n in ("job_v", "job", "wsc", "pk5", "pb5")})

# buses, ports, lanes
R_T["buses"] += [dict(name="n4x_up_nw_i", dir="in", width=UPW, kind="data", leaf="u_mu_fused_root.up_nw"),
                 dict(name="n4x_up_ne_i", dir="in", width=UPW, kind="data", leaf="u_mu_fused_root.up_ne"),
                 dict(name="n4x_dn_nw_o", dir="out", width=DNW, kind="data", leaf="u_mu_fused_root.down_nw"),
                 dict(name="n4x_dn_ne_o", dir="out", width=DNW, kind="data", leaf="u_mu_fused_root.down_ne")]
for hn in HUBS:
    T[hn]["buses"] += [dict(name="n4x_up_o", dir="out", width=UPW, kind="data", leaf="u_mu_fused_n4.uo"),
                       dict(name="n4x_dn_i", dir="in", width=DNW, kind="data", leaf="u_mu_fused_n4.dn")]
NEWP = [dict(id="N4U_NW_0", src=dict(part="NW_hub", bus="n4x_up_o"), dst=dict(part="root", bus="n4x_up_nw_i"), face="E", win=UPWIN, w=UPW),
        dict(id="N4D_NW_0", src=dict(part="root", bus="n4x_dn_nw_o"), dst=dict(part="NW_hub", bus="n4x_dn_i"), face="W", win=DNWIN, w=DNW),
        dict(id="N4U_NE_0", src=dict(part="NE_hub", bus="n4x_up_o"), dst=dict(part="root", bus="n4x_up_ne_i"), face="W", win=UPWIN, w=UPW),
        dict(id="N4D_NE_0", src=dict(part="root", bus="n4x_dn_ne_o"), dst=dict(part="NE_hub", bus="n4x_dn_i"), face="E", win=DNWIN, w=DNW)]
for p in NEWP:
    P["ports"].append(dict(id=p["id"], src=p["src"], dst=p["dst"], width=p["w"], kind="data", face=p["face"],
                           layers=["M6", "M4"], window_um=p["win"]))
    P["lanes"].append(dict(id=p["id"][:-2], ports=[p["id"]],
                           note=f"C25b TOK-HBM-1 fused tree n4 -> root ({'up' if 'U' in p['id'] else 'down'}, "
                                f"{p['w']} b = ot_hnx_fused_tree UW/DW)"))


def path_regs(pts, smax=SMAX):
    """registers along a rectilinear polyline so that every hop (incl. the end legs) is <= smax."""
    L = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    n = max(0, math.ceil(L / smax) - 1)
    regs = []
    for k in range(1, n + 1):
        s = L * k / (n + 1)
        for a, b in zip(pts, pts[1:]):
            seg = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if s <= seg + 1e-9:
                f = s / seg if seg else 0
                regs.append([r4(a[0] + (b[0] - a[0]) * f), r4(a[1] + (b[1] - a[1]) * f)]); break
            s -= seg
    return regs, L


def hops_ok(pts, regs, smax=405.0):
    q = [pts[0]] + regs + [pts[-1]]
    return max(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(q, q[1:])) <= smax + 1e-6


ST = {}
HW = T["q_hub_nw"]["outline_um"][0]
n4 = next(c for c in T["q_hub_nw"]["hard_cores"] if c["inst"] == "u_mu_fused_n4")
nx, ny_ = n4["origin_um"]
uo_pin = [r4(nx + 172.704), r4(ny_ + (8.76 + 76.824) / 2)]
dn_pin = [r4(nx + 0.096), r4(ny_ + (126.648 + 164.04) / 2)]
yu, yd = r4((UPWIN[0] + UPWIN[1]) / 2 - hub_y0), r4((DNWIN[0] + DNWIN[1]) / 2 - hub_y0)
X_DROP = 8121.6                                       # free column between u_ctl_Q_p06/07 (x <= 8049) and the E face
up_path = [[HW, yu], [X_DROP, yu], [X_DROP, 3507.84], [uo_pin[0] + 20.0, 3507.84], [uo_pin[0] + 20.0, uo_pin[1]], uo_pin]
dn_path = [[HW, yd], [X_DROP, yd], [X_DROP, 3538.08], [5045.76, 3538.08], [5045.76, 3503.52], [4830.48, 3503.52],
           [4830.48, dn_pin[1]], dn_pin]
for hn in HUBS:
    for conn, cap, path in (("bus:n4x_up_o", "u_mu_fused_n4.uo", up_path), ("bus:n4x_dn_i", "u_mu_fused_n4.dn", dn_path)):
        if conn.endswith("dn_i"):                     # last register at the corner west of the core (n4 dn = W face)
            regs, L = path_regs(path[:-1]); regs.append(path[-2]); L += abs(path[-1][0] - path[-2][0])
        else:
            regs, L = path_regs(path)
        assert hops_ok(path, regs), (hn, conn)
        T[hn]["internal_stations"].append(dict(
            conn=conn, launch=f"face bus {conn[4:]}", capture=cap, from_um=path[0], to_um=path[-1], regs_um=regs,
            bits=UPW if "up" in conn else DNW,
            note=f"C25b TOK-HBM-1: n4 <-> E-face (type frame) leg {L:.0f} um, {len(regs)} st, hops <= {SMAX:g} um "
                 "(street y 3481.92-3551.04 below the u_svg/xq row, drop column x 8121.6)"))
        ST[(hn, conn)] = dict(length_um=round(L, 1), regs=len(regs), route=path)
RW = R_T["outline_um"][0]
for conn, cap, face_x, wy, pin_x in (("bus:n4x_up_nw_i", "u_mu_fused_root.up_nw", 0.0, UPWIN, N4O[0]),
                                     ("bus:n4x_dn_nw_o", "u_mu_fused_root.down_nw", 0.0, DNWIN, N4O[0]),
                                     ("bus:n4x_up_ne_i", "u_mu_fused_root.up_ne", RW, UPWIN, N4O[0] + N4W),
                                     ("bus:n4x_dn_ne_o", "u_mu_fused_root.down_ne", RW, DNWIN, N4O[0] + N4W)):
    y = r4((wy[0] + wy[1]) / 2 - root_y0)
    path = [[face_x, y], [pin_x, y]]
    regs, L = path_regs(path)
    assert hops_ok(path, regs)
    R_T["internal_stations"].append(dict(conn=conn, launch=f"face bus {conn[4:]}", capture=cap, from_um=path[0],
                                         to_um=path[1], regs_um=regs, bits=UPW if "up" in conn else DNW,
                                         note=f"C25b TOK-HBM-1: root face <-> fused root leg {L:.0f} um, {len(regs)} st"))
    ST[("root", conn)] = dict(length_um=round(L, 1), regs=len(regs))

# latency table for the 4 new lanes (shared schema model)
sys.path.insert(0, str(TOOLS))
import schema as S  # noqa: E402
PL = S.Plan(json.loads(json.dumps(P)))
lat = {}
for p in NEWP:
    lid = p["id"][:-2]
    v = PL.lane_latency(lid)
    P["latency"]["lanes"][lid] = dict(v, param="LAT_" + lid.upper())
    lat[lid] = v["cycles"]
rep["item5_fused_root"] = dict(
    cores={"u_mu_fused_root": dict(module="ot_hnx_fused_hub_n4ext", origin=N4O, outline=[N4W, N4H], pins=len(n4p)),
           "u_mu_fused_program": dict(module="ot_hnx_fused_host_program", origin=PGO, outline=[PGW, PGH], pins=len(pgp))},
    lanes=lat, stations={f"{k[0]}:{k[1]}": v for k, v in ST.items()}, windows_die_y=dict(up=UPWIN, down=DNWIN))

# ------------------------------------------------------------------ write
P["note"] = (P.get("note") or "") + (" | C25b (DIE-HBM-10 10-28): KITS-2/3 macro placements; vp4_banks_cp 275.4 / "
                                     "host_cp_rxs 480 um high; fused root + programme in root with n4->root lanes "
                                     "N4U/N4D_NW/NE (271/173 b) + reset-delivery side table")
json.dump(CM, open(OUT / "core_macros.json", "w"), indent=1)
json.dump(CC, open(OUT / "core_conns.json", "w"), indent=1)
json.dump(CE, open(OUT / "clock_entries.json", "w"), indent=1)
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
rep["plan_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:8]
json.dump(rep, open(OUT / "c25b_event_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1)[:6000])
