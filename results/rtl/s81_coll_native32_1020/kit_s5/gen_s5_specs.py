#!/usr/bin/env python3
"""S81-COLL5 (10-20) COLL v8 lane kits dscoll_lane_{w,e}_s5 (spine clock) and dscoll_lane_{w,e}_s5c (TritonCTS fallback,
parallel per owner 10-19).  Structural successor of the four terminal s4/s4b placement FAILs (GPL-0305 x2, DPL-0033,
DPL negotiation 21,901 illegal + OT_SPINE spread 224->464 ps divergence; ../s4_terminal).

Root cause (geometry): the s4/s4b std-cell region was ONE 28.8-39.6 um band sized at 40-60% of the SYNTHESIS std area
only (9,445 um2) and no rows anywhere else.  (a) The ~2,130 face bus pins (rx/tx 1,027 link, lo_d/li_d 1,106 core) sit on
the full W/E faces, so their landing/driver cells pile into the two band ENDS (rowless face channels): local overflow.
(b) Post-place std is 12.1k um2 (W_s4b report_design_area 74,148 - 62,002 macros) = 60% of the band before CTS, and
OT_SPINE then inserted 4-34k clock cells: no room, legalisation fails and the padded spine diverges.

s5 geometry (both fixed structurally, macros unchanged on the 43.2 lattice):
  * N strip moved up one lattice step (+43.2): ONE full-width band y 259.2..340.2 (81 um, the whole S-top..N-halo gap)
    sized from the BUDGETED std area = synthesis 9,489 + place repair 2,650 (measured W_s4b) + spine/CTS ~4,500
    (W_s4b iter-1/2 14-18k cells) + hold/timing repair ~2,000 = ~18.6k um2 -> 32% of the band, 19.6% at place.
  * two full-height FACE COLUMNS of rows x core..37.8 and 688.0..core (between the core edge and the first/last macro
    column halo), joined to the band (one contiguous region, no islands): the face pin landing cells sit at their pins.
  * outline 725.76 x 583.2 (aspect 1.24): left/right core-edge channels equal (41.0 / 41.0 um) so W and E (column mirror)
    have the same face columns; pins on full faces <= 1.9/um; ck at the band centre.
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STD = 9489.0
W, H = 725.76, 583.2
SHIFT = 43.2
BAND = (259.2, 340.2)
FACE = (37.8, 688.0)       # left column right edge / right column left edge (macro halo 5.4 from 43.2 / 682.584)
BAND_TCL = "physical/dscoll_cx/coll_s5_cell_band.tcl"
V8 = "results/rtl/s81_coll_native32_1020/native_v8"
DEFINES = ["OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF"]
PR = {"rx": [2.16, 288.36], "tx": [290.52, 576.72], "tf": [578.88, 581.04],
      "lo_d": [2.16, 274.32], "lo_v": [276.48, 277.56], "lo_r": [278.64, 279.72], "chb": [280.8, 282.96],
      "ck": [298.08, 300.24], "rs": [302.4, 304.56], "li_v": [306.72, 307.8], "li_r": [308.88, 309.96],
      "flt": [312.12, 315.36], "li_d": [317.52, 581.04]}
KEEP = ["ot_sram_showahead_b64_hit5", "ot_s81ph_kp4_20", "ot_s81ph_kff4_1", "ot_s81ph_kff4_10", "ot_s81ph_rewind4"]


def benches():
    vb = []
    for k, exp, rx in ((0, "pass", None), (1, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]"),
                       (2, "fail", r"COLL_COLLISION_UNSAFE"), (3, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]"),
                       (4, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]")):
        b = {"name": f"lane_miter_v8_m{k}",
             "cmd": f"OT_COLL_NATIVE32=1 OT_COLL_NATIVE32_OFF=1 bash tools/xdie_s81/coll_safe4_boundary.sh {{RUN}}/miter{k} {k}",
             "expect": exp, "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"],
             "pass_regex": r"^COLL_SAFE4_BOUNDARY PASS checks=\d+"}
        if exp == "pass":
            b["pass_witness"] = f"{V8}/bench/m0.log"
        else:
            b.update(fail_regex=rx, fail_witness=f"{V8}/bench/m{k}.log")
        vb.append(b)
    return vb


def spec(side, var):
    base = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_s4b/spec.json").read_text())
    s = copy.deepcopy(base)
    name = f"dscoll_lane_{side}_{var}"
    spine = var == "s5"
    for m in s["macros"]:
        if m["at"][1] >= 302.4 - 1e-6:          # N strip (gearbox + replay) one lattice step up
            m["at"][1] = round(m["at"][1] + SHIFT, 4)
    s.update(name=name, outline={"w": W, "h": H}, std_area_um2=STD, pin_ranges=PR, defines=DEFINES,
             clock="spine" if spine else "cts")
    s["route"].update(synth_keep_modules=KEEP, io_hold_margin_ns=0.03, hold_margin_ns=0.03)
    ck = "OT_SPINE spine clock (macro leaf)" if spine else "TritonCTS sink-clustered tree from the band-centre ck pin"
    s["fill_reason"] = {"pin_bound": (
        "lattice/channel-bound (checklist 6): 55 bank64 SRAMs 62,002 um2 on the 43.2 lattice with >= 20 um channels force "
        f"86.4 um pitch; std region = ONE full-width band y {BAND[0]}..{BAND[1]} + two full-height face columns (x <= "
        f"{FACE[0]}, x >= {FACE[1]}), sized from the BUDGETED std area ~18.6k um2 (synthesis {STD:.0f} + place repair + "
        "spine/CTS + hold repair, measured on W_s4b) = 32% of the band; rows elsewhere removed (no std cell in a macro "
        "channel); the low overall fill is channel area")}
    s["slot_change_request"] = {"reason": f"S81-COLL5 v8 {W}x{H} (s4b 706.32x540 FAIL placement): the die parent re-slots the "
                                "16 lane tiles per die to this outline (same ports; ck/rs/chb at y 276..316)"}
    j = s["job"]
    j.update(owner="Claude:S81-COLL5", branch="claude/s81-coll5-1020", tag=var,
             purpose=(f"S81-COLL v8 (OT_COLL_NATIVE32_OFF: depth 540.1 ps, native max32) {W}x{H}, band 81 um + face columns, "
                      f"{ck}. SAFE checklist in kit README."),
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}", benches=benches())
    ep = [p for p in j["extra_paths"] if "cell_band" not in p] + [BAND_TCL, f"{V8}/bench"]
    j["extra_paths"] = ep
    return name, s


if __name__ == "__main__":
    for var in ("s5", "s5c"):
        for side in ("w", "e"):
            name, s = spec(side, var)
            d = ROOT / "physical/ref_tile" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print("wrote", d / "spec.json")
