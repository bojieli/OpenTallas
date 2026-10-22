import json, os, shutil, copy
R = "/home/ubuntu/wt/qko-coll-1021/physical/ref_tile"
src = json.load(open(f"{R}/qfd_coll_split_q8a/spec.json"))
A_W, A_H = 34.584, 41.352     # 256x64
B_W, B_H = 33.72, 27.576      # 128x64
HX, HY = 10.8, 2.16           # pin-face (W/E) halo, top/bottom halo (no pins N/S)
def snap(v, g=0.048): return round(round(v / g) * g, 3)
def snapu(v, g=2.16): import math; return round(math.ceil(v / g - 1e-9) * g, 3)
INST = {  # role -> inst glob (from q8a)
 "sd00": "*u_sd*g_d?0?*g_c?0?*u_m", "sd01": "*u_sd*g_d?0?*g_c?1?*u_m", "sd10": "*u_sd*g_d?1?*g_c?0?*u_m", "sd11": "*u_sd*g_d?1?*g_c?1?*u_m",
 "pr0": "*u_pring*g_b?0?*u_m", "pr1": "*u_pring*g_b?1?*u_m", "rr0": "*u_rring*g_b?0?*u_m", "rr1": "*u_rring*g_b?1?*u_m",
 "x30": "*u_xf*g_st?3?*u_dr*g_b?0?*u_m", "x31": "*u_xf*g_st?3?*u_dr*g_b?1?*u_m", "x20": "*u_xf*g_st?2?*u_dr*g_b?0?*u_m", "x21": "*u_xf*g_st?2?*u_dr*g_b?1?*u_m"}
V256 = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1"; V128 = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1"
def mk(tag, hx, margin, gy, band, bus_um, why, fill=0.3502):
    import math
    sx = lambda v: round(math.floor(v / 0.432 + 1e-9) * 0.432, 3)
    stackA = 2*A_H + gy
    H = snapu(2*margin + 2*stackA + band)
    W = round(math.floor((13159.4 + 10989) / fill / H / 2.16) * 2.16, 3)
    std = (W - (A_W + 2*B_W) - 6*hx) / 4          # equal std-cell width: W strip, two column channels, E strip
    x1 = sx(hx + std); x2 = sx(x1 + A_W + 2*hx + std); x3 = sx(x2 + B_W + 2*hx + std)
    ys = snap(margin, 2.16); yn = snap(H - margin - stackA, 2.16)
    # 128 pairs: same S/N anchors, pair gap = gy + (A_H - B_H) so their tops/bottoms align with the 256 pairs (wider crossings)
    gB = snapu(2*A_H + gy - 2*B_H + B_H) - B_H
    m = []
    def put(role, view, x, y, o): m.append({"view": view, "count": 1, "inst": INST[role], "at": [snap(x, 0.432), snap(y, 2.16)], "at_exact": True, "orient": o})
    put("sd00", V256, x1, ys, "MY"); put("sd01", V256, x1, ys + snapu(A_H + gy), "MY")
    put("sd10", V256, x1, yn, "MY"); put("sd11", V256, x1, yn + snapu(A_H + gy), "MY")
    put("rr0", V128, x2, ys, "R0"); put("rr1", V128, x2, ys + B_H + gB, "R0")
    put("pr0", V128, x2, yn, "R0"); put("pr1", V128, x2, yn + B_H + gB, "R0")
    put("x20", V128, x3, ys, "R0"); put("x21", V128, x3, ys + B_H + gB, "R0")
    put("x30", V128, x3, yn, "R0"); put("x31", V128, x3, yn + B_H + gB, "R0")
    for mm in m:
        for v in mm["at"]: assert abs(v / 0.048 - round(v / 0.048)) < 1e-6, mm
    c = H / 2
    rng = {}
    for i, (w, e) in enumerate([("sx1_data", "up_data"), ("sr1_data", "dp_data"), ("sr2_data", "dr_data"), ("sx2_data", "ur_data")]):
        lo = round(c - 2*bus_um + i*bus_um, 2); rng[w] = [lo, round(lo + bus_um, 2)]; rng[e] = [lo, round(lo + bus_um, 2)]
    s = copy.deepcopy(src); name = f"qfd_coll_split_{tag}"
    s["name"] = name; s["outline"] = {"w": W, "h": H}; s["macros"] = m; s["pin_ranges"] = rng
    s["route"]["macro_halo_um"] = HY; s["route"]["macro_halo_x_um"] = hx
    s["pin_hook_before_flops"] = [f"physical/ref_tile/{name}/native_release_tie.tcl"]
    j = s["job"]; j["tag"] = tag; j["owner"] = "QE3-COLL"
    j["purpose"] = f"QE3-COLL Q leaf {tag}: {why}"
    s["structural_change"] = ("q8a FAIL GRT-0183 net42538 = W-face SerDes capture srr_q2 placed across the W SRAM wall from its xsrc mux; "
        "q8b FAIL GRT-0183 net10846 at SRAM W pin wd59 (M2-M5 full, 24-nm seam to the abutted bank) + clock 115.8/114.3. "
        "Fix = ENLARGE + no abutted macro: " + why)
    os.makedirs(f"{R}/{name}", exist_ok=True)
    for f in os.listdir(f"{R}/qfd_coll_split_q8a"):
        if f in ("gate_result.json", "gate_layout", "source_binding_history", "README.md", "spec.json"): continue
        p = f"{R}/qfd_coll_split_q8a/{f}"
        if os.path.isfile(p): shutil.copy(p, f"{R}/{name}/{f}")
    json.dump(s, open(f"{R}/{name}/spec.json", "w"), indent=1)
    print(name, "std channel", round(std, 2), "E strip", round(W - x3 - B_W - hx, 2), W, H, round(W*H), "fill", round((13159.4 + 10989) / (W*H), 4), "x", x1, x2, x3, "ys/yn", ys, yn, "gB", round(gB, 2))
    print("  ranges", rng)
    for mm in m: print("  ", mm["inst"], mm["at"], mm["orient"])
mk("q9a", hx=10.8, margin=24.0, gy=20.0, band=21.6, bus_um=32.0,
   why="q9a MAIN: 3 macro columns (W sd 4x256 MY | rings 4x128 | E xf 4x128) replace the two 193-um walls; every macro "
       "free-standing (no abutment; 22-um N-S crossing gaps with 2.16-um top/bottom halo -> ~20-um std-cell crossing rows "
       "between every SRAM); pin-face halo 10.8 + ~21.7-um std-cell channel beside every SRAM pin face (W strip, two column "
       "channels, E strip); W/E buses 4 pins/um centred on the mid crossing with the SerDes inputs sr1/sr2 (E: dp/dr) in the "
       "middle so each capture flop sits beside its xsrc mux, no SRAM wall between; fill 35% (owner floor) with zero squeeze "
       "of any channel vs q8 (q8 cut channels had ~1.4 um of rows). RTL/pins/clock/reset unchanged.")
mk("q9b", hx=8.64, margin=24.0, gy=20.0, band=30.24, bus_um=32.0,
   why="q9b FALLBACK: q9a column topology + a 34-um central W-E band (12 um taller), pin-face halo 8.64 so every std-cell "
       "channel/strip is ~22 um; buses 4 pins/um centred on the band.")
