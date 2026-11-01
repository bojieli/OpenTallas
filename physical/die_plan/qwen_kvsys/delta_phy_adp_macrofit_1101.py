#!/usr/bin/env python3
"""DIE-KV-60/adp 11-01 plan event: qkd_hr_phy_adp macro fit (native SRAM ot_sram_1r1w_512x128_m4_r2c2, 174.12 x 29.736).

The SRAM does not fit the old 103.68 x 95.04 slot.  Outline re-derived top-down from the parent lot in kv3_hub_Wi
(one-block event, 12.20 freeze: no neighbour moves):
  lot x 164.16 (phy_pad E edge) .. 665.28 (cdc_ci W edge), y 120.96 .. 328.32 (FT stations end at y 109.89 and start
  at y 339.37: both >= 10.8 um away, same as the old two rows).
  Unrotated the macro needs a core >= ~190 um wide -> 2 per row, 4 rows of <= 45 um in 207 um: no logic band.
  Rotated (R270) the macro is 29.736 x 174.12: ONE row of 8 tall cores, H = 207.36 (= old two-row span), W = 51.84
  (variant V1, 8.64 gaps) or 56.16 (variant V2, 4.32 gaps).  The macro sits on the core E edge; its pins (both short
  ends) face the N / S logic gutters and the W logic band holds the core W face pins.
Row order keeps the old x neighbours: old (x, y) order _0 _4 _1 _5 _2 _6 _3 _7; orients unchanged (_2 MX).
Pins: same faces / order / spreading rule (core_pins_resize_v38x.py).  Clock taps follow the new ck[0] pin.

Usage: delta_phy_adp_macrofit_1101.py PLAN_IN PLAN_OUT VARIANT(V1|V2) [MACRO_PLAN_OUT]
       (pins written to <dir of PLAN_OUT>/pins; MACRO_PLAN_OUT = cores/harden/qkd_hr_phy_adp_macro_plan.json)."""
import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD_PINS = "pins/qkd_hr_phy_adp_pins_r26q9.json"
H = 207.36
Y0 = 120.96
# w = core width, gap = core-to-core gap, x0 = first core x in hub_Wi; mx = macro x in the core (E edge, 4.32 um
# boundary keep; x = 0.012 mod 0.048 so the rotated M4 pin centres land on the 0.024 + k 0.048 M5 tracks), my = macro y
VARIANTS = {"V1": dict(w=51.84, gap=8.64, x0=172.8, mx=17.772, my=17.28),
            "V2": dict(w=56.16, gap=4.32, x0=172.8, mx=22.092, my=17.28)}
SRAM = "ot_sram_1r1w_512x128_m4_r2c2"
SRAM_DIR = "physical/asap7_memory_macros_v2/" + SRAM
SRAM_INST = "u_slice.u_body.g_grp[0].u_rb.g_sram.g_t[0].u_m"
SRAM_WH = (174.12, 29.736)
ORDER = [0, 4, 1, 5, 2, 6, 3, 7]
LOT = (164.16, 665.28)


def orient_pt(x, y, w, h, o):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def macro_plan(var):
    """core-level hard-child plan (gen_core_kit_kv.py --hard-children / recipes_kv.json): the one native SRAM, R270
    (PG M4 stripes vertical -> gen_core_kit_kv PDN_MACRO_M4_ROT M6 straps), E edge, pins at its N / S ends."""
    v = VARIANTS[var]
    mw, mh = SRAM_WH[1], SRAM_WH[0]                     # rotated footprint
    assert v["mx"] + mw <= v["w"] - 4.32 + 1e-9 and v["my"] >= 4.32 + 4.32 and v["my"] + mh <= H - 4.32 - 4.32
    assert abs((v["mx"] - 0.012) / 0.048 - round((v["mx"] - 0.012) / 0.048)) < 1e-6
    return dict(source=f"DIE-KV-60/adp 11-01 MACRO-FIT {var}: native SRAM {SRAM} {SRAM_WH[0]} x {SRAM_WH[1]} R270 on the "
                       f"core E edge (rotated footprint {mw} x {mh}); pins (macro short ends) face the N / S logic gutters, "
                       f"W logic band {v['mx'] - 4.32 - 4.32:.2f} um holds the W-face pins; x = 0.012 mod 0.048 (M5 "
                       f"pin phase), y on the 8.64 lattice; PG M4 stripes vertical -> M6 straps + M4-M6 connect",
                module="qkd_hr_phy_adp", outline_um=[v["w"], H], halo_um=4.32, added_cycles=0,
                children={SRAM: SRAM_DIR},
                blocks=[dict(inst=SRAM_INST, master=SRAM, x=v["mx"], y=v["my"], orient="R270")],
                pg_pin_layer="M4", grid_um=8.64, static_rows=True, track_offset_um=[0.012, 0])


def apply(raw, pdir, var):
    v = VARIANTS[var]
    w = v["w"]
    pins_rel = f"pins/qkd_hr_phy_adp_pins_mf{var.lower()}.json"
    subprocess.run([sys.executable, str(HERE / "core_pins_resize_v38x.py"), str(pdir / OLD_PINS), str(pdir / pins_rel),
                    f"{w:g}", f"{H:g}"], check=True)
    ck = next(p for p in json.load(open(pdir / pins_rel))["pins"] if p["name"] == "ck[0]")
    p = copy.deepcopy(raw)
    t = p["partition_types"]["kv3_hub_Wi"]
    hcs = {c["inst"]: c for c in t["hard_cores"]}
    taps = {k["name"]: k for k in t["clock"]["taps"]}
    rep = dict(variant=var, outline_um=[w, H], cores={})
    for slot, k in enumerate(ORDER):
        c = hcs[f"host__qkd_hr_phy_adp_{k}"]
        ox, oy = round(v["x0"] + slot * (w + v["gap"]), 4), Y0
        old = dict(origin_um=c["origin_um"], outline_um=c["outline_um"], pins_file=c["pins_file"])
        assert c["outline_um"] == [103.68, 95.04] and c["pins_file"] == OLD_PINS, (k, old)
        c.update(origin_um=[ox, oy], outline_um=[w, H], pins_file=pins_rel)
        c["note"] += (f" | DIE-KV-60/adp 11-01 MACRO-FIT {var}: native SRAM 174.12 x 29.736 R270 on the core E edge; "
                      f"one row of 8 cores in the old two-row lot; was {old['origin_um']} {old['outline_um']}")
        tp = taps[f"host__qkd_hr_phy_adp_{k}.ck[0]"]
        px, py = orient_pt(ck["x"], ck["y"], w, H, c["orient"])
        oldxy = tp["xy"]
        tp["xy"] = [round(ox + px, 4), round(oy + py, 4)]
        tp["note"] += f" | DIE-KV-60/adp 11-01 MACRO-FIT {var}: xy {oldxy} -> {tp['xy']} (core re-placed)"
        rep["cores"][c["inst"]] = dict(old=old, origin_um=[ox, oy], orient=c["orient"], tap=tp["xy"])
    # lot / overlap self-check (no neighbour moves)
    xs = sorted((c["origin_um"][0], c["origin_um"][0] + w) for c in t["hard_cores"] if c["module"] == "qkd_hr_phy_adp")
    assert LOT[0] < xs[0][0] and xs[-1][1] < LOT[1], xs
    others = [c for c in t["hard_cores"] if c["module"] != "qkd_hr_phy_adp"]
    for c in t["hard_cores"]:
        if c["module"] != "qkd_hr_phy_adp":
            continue
        a = (*c["origin_um"], c["origin_um"][0] + w, c["origin_um"][1] + H)
        for o in others:
            b = (*o["origin_um"], o["origin_um"][0] + o["outline_um"][0], o["origin_um"][1] + o["outline_um"][1])
            assert min(a[2], b[2]) - max(a[0], b[0]) <= 1e-6 or min(a[3], b[3]) - max(a[1], b[1]) <= 1e-6, (c["inst"], o["inst"])
    return p, rep


def main(inp, outp, var, mplan=None):
    raw = json.load(open(inp))
    p, rep = apply(raw, Path(outp).resolve().parent, var)
    Path(outp).write_text(json.dumps(p, indent=1) + "\n")
    if mplan:
        Path(mplan).write_text(json.dumps(macro_plan(var), indent=1) + "\n")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
