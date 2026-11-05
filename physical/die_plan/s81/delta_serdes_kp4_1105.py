#!/usr/bin/env python3
"""S81 serdes cap form (COORD 13:26 (3), 13:40 (1)): u_dec.u_chn becomes the signed KP4 core ot_s81_kp4_dchn, the view
HEAD already uses (kp4_e13a_n: TT +2.48, FF +20.08, LEC EQUIVALENT 4217/4217).  Same module and path, no added cycles.
usage: delta_serdes_kp4_1105.py PLAN_IN PLAN_OUT TYPE[,TYPE...]
Sites per type in SITES."""
import json, re, sys
from pathlib import Path

MODULE = "ot_s81_kp4_dchn"; INST = "u_phy.u_dec.u_chn"; W, H = 276.48, 138.24; GAP = 8.64; CLEAR = 8.64
R = "results/head_core_clockfreeze_release/kp4_e13a_corner/ot_s81_kp4_dchn"


def macros(t):
    out = []
    for c in t.get("contents", []):
        out += [(q["physical_inst"], q["origin_um"], q["outline_um"]) for q in c.get("physical_parts", [])]
    out += [(c["inst"], c["origin_um"], c["outline_um"]) for c in t.get("hard_cores", [])]
    return out


def legal(t, x, y):
    ow_, oh_ = t["outline_um"]
    if x < 8.64 or y < 8.64 or x + W > ow_ - 8.64 or y + H > oh_ - 8.64:
        return False
    for _, (ox, oy), (ow, oh) in macros(t):             # GAP clear of every macro
        if x - GAP < ox + ow and ox < x + W + GAP and y - GAP < oy + oh and oy < y + H + GAP:
            return False
    c = t["clock"]
    for k in c.get("keepouts_um", []):
        if x < k[2] and k[0] < x + W and y < k[3] and k[1] < y + H:
            return False
    taps = [p["xy"] for p in c.get("added_taps", [])] + ([c["tap_um"]] if c.get("tap_um") else [])
    for tx, ty in taps:                                 # schema.TAP_CLEAR_UM: no tap moves
        if x - CLEAR < tx < x + W + CLEAR and y - CLEAR < ty < y + H + CLEAR:
            return False
    return True


# nearest 8.64-grid site to the left of the dmem SRAM clear of macros, keep-outs, clock taps and FT stations
# (searched against check.py check_ft_macro_sites; G0 re-checks them)
SITES = {
    "serdes__t12": [
        864.0,
        673.92
    ],
    "serdes__t13": [
        976.32,
        432.0
    ],
    "serdes__t14": [
        898.56,
        60.48
    ],
    "serdes__t15__cla2127225": [
        967.68,
        319.68
    ],
    "serdes__t15__cla3d02796": [
        967.68,
        319.68
    ],
    "serdes__t16": [
        967.68,
        319.68
    ],
    "serdes__t1__clb45db5be": [
        794.88,
        60.48
    ],
    "serdes__t1__clfe1f0815": [
        794.88,
        60.48
    ],
    "serdes__t2": [
        898.56,
        60.48
    ],
    "serdes__t3": [
        803.52,
        311.04
    ],
    "serdes__t4": [
        967.68,
        535.68
    ]
}


def main():
    src, dst, types = sys.argv[1:4]
    p = json.load(open(src))
    rep = {}
    for n in types.split(","):
        t = p["partition_types"][n]
        if any(c["module"] == MODULE for c in t.get("hard_cores", [])):
            raise SystemExit(f"{n}: already extracted")
        o = SITES[n]
        if not legal(t, *o):
            raise SystemExit(f"{n}: KP4 site {o} not legal")
        t.setdefault("hard_cores", []).append({
            "inst": INST, "module": MODULE, "origin_um": o, "track_offset_um": [0, -2.112], "outline_um": [W, H],
            "orient": "R0", "pins_file": "inputs/core_pins/kp4_276x138_pins.json", "obs_max": "M5", "lef": R + ".lef",
            "lib": R + "_tt.lib",
            "reset_from_master": {"kind": "internal", "content": "u_phy", "pin": "rst_n", "source": "ot_pdie_serdes rn_r -> u_dec.rst_n: bound whole in u_phy, not a die wavefront consumer"},
            "note": "SIGNED view kp4_e13a_n, HEAD plan core; recovered pma_rck clock domain, never parent clk"})
        d = t.setdefault("verilog_defines", [])
        if "OT_KP4_DEC_HARD" not in d:
            d.append("OT_KP4_DEC_HARD")
        for pin in t["clock"]["pad_clock"]["pins"]:
            if pin["name"] == "io_pma_rck":
                sinks = pin["sink_pins"]
                if {"module": MODULE, "pin": "clk"} not in sinks:
                    sinks.insert(0, {"module": MODULE, "pin": "clk"})
        t["note"] = t.get("note", "") + "; KP4 Chien child = signed core ot_s81_kp4_dchn, zero added cycles (DIE-S81-56 11-04, OT_NATIVE_CELL_CAP form)"
        rep[n] = o
    # negotiation legalizer for the family: on t4's 3_4 DB it is legal in 35 s; diamond stalled 47 min (DIE-S81-58 11-05)
    off = p["budgets"].setdefault("dpl_legalizer_off_types", [])
    if "serdes" not in off:
        off.append("serdes")
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import compact_plan as CP
    # changed blocks only, spliced into the source text: the plan diff stays local
    text = open(src).read()
    for key, val, lvl in [(n, p["partition_types"][n], 2) for n in rep] + [("budgets", p["budgets"], 1)]:
        m = re.search("^" + " " * lvl + '"' + re.escape(key) + '": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(val, lvl) + text[j:]
    assert json.loads(text) == p
    open(dst, "w").write(text)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
