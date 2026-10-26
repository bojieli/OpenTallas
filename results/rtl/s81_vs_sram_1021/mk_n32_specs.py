# ELEM-XFV/VS: derive s81sl_vs_n32 (MAIN) / s81sl_vs_n32f (FALLBACK) specs from the w2 kit for the SRAM+FP_N32 VS source
import json, sys, copy, os
WT = sys.argv[1]; commit_note = sys.argv[2] if len(sys.argv) > 2 else ""
base = json.load(open(f"{WT}/physical/ref_tile/s81sl_vs_w2/spec.json"))
DEFS = ["OT_S81SL_VS_SRAM", "OT_S81SL_VS_FP_N32"]
ENV = ("S81_VS_DEFS='-DOT_S81SL_VS_SRAM -DOT_S81SL_VS_FP_N32' S81_VS_EXTRA_SOURCES='physical/asap7_memory_macros/"
       "ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/dsrom_sys/s81_dv/slice/ot_s81sl_fp_n32.sv' ")
MV = "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1"
def macros(W, H):
    # 8 ENG h-stash banks (g_hcopy[hj].g_parity[hp].u_hst, 51.408 x 20.79): two columns of four on the (0.432, 2.16)
    # lattice, wide std-cell band between the columns and pin-register bands on the W / E faces; no macro on a face.
    xa = round(round((W * 0.20) / 0.432) * 0.432, 3)
    xb = round(round((W - W * 0.20 - 51.408) / 0.432) * 0.432, 3)
    pitch = 41.04 if H < 216 else 45.36          # >= 20 um N-S channels (2.16 lattice)
    y0 = round(round(((H - (3 * pitch + 20.79)) / 2) / 2.16) * 2.16, 3)
    out = []
    for hj in range(4):
        for hp in range(2):
            x = xa if hj < 2 else xb
            y = round(y0 + pitch * (2 * (hj % 2) + hp), 3)
            out.append({"view": MV, "count": 1, "inst": f"*g_hcopy?{hj}?*g_parity?{hp}?*u_hst", "at": [x, y], "orient": "R0"})
    return out
for tag, W, H, purpose in (("n32", 216.0, 194.4, "MAIN: SRAM h-stash + FP_N32 + native-32 control copies, 216 x 194.4 (leaf column pitch 216)"),
                           ("n32f", 216.0, 237.6, "FALLBACK: same source, 216 x 237.6 (+22% area, lower util)")):
    s = copy.deepcopy(base)
    name = f"s81sl_vs_{tag}"
    s["name"] = name
    s["sources"] = base["sources"] + ["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_fp_n32.sv"]
    s["defines"] = DEFS
    s["macros"] = macros(W, H)
    s["outline"] = {"w": W, "h": H}
    s.pop("util", None)
    s.pop("pin_ranges", None)          # re-derived for the new outline by gen
    s["structural_change"] = (base["structural_change"] + " ELEM-XFV/VS 10-21 " + tag + ": SRAM h-stash (8x ot_sram_1r1w_32x128_m1, "
        "OT_S81SL_VS_SRAM) + FP_N32 leaves (OT_S81SL_VS_FP_N32) + native-32 control copies (kept capture flags, shared ENG prequal, "
        "regional busy/ka copies); no new cycles. " + purpose)
    j = s["job"]
    j["owner"] = "Claude:S81-ELEM/ELEM-XFV-VS"; j["branch"] = "codex/s81-vs-bankmux-1021"; j["tag"] = tag; j["purpose"] = "vs " + purpose
    if MV not in j["extra_paths"]:
        j["extra_paths"].append(MV)
    for b in j["benches"]:
        c = b["cmd"]
        if c.startswith("RAW=1 "):
            b["cmd"] = "RAW=1 " + ENV + c[len("RAW=1 "):]
        else:
            b["cmd"] = ENV + c
        b["peak_ram_gb"] = max(b.get("peak_ram_gb", 6), 8)
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    os.makedirs(f"{WT}/physical/ref_tile/{name}", exist_ok=True)
    json.dump(s, open(f"{WT}/physical/ref_tile/{name}/spec.json", "w"), indent=1)
    print(name, W, H, [m["at"] for m in s["macros"]])
