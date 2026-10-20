#!/usr/bin/env python3
"""KV-AHUB5 10-19 (LEAD3-KV, tree K.STA.AHUB): the structurally safe successor of qkd_ahub_g3a / g3b (both gates FAIL
clock_rule).  SAME RTL (qkd_ahub_static_dw_g3_lp, 7 region roots, 15 landings): every g3 die/compiler delta stands
(HUB_RECIP / HUB_PUB +6, am +3 at the ASTK pins, AP_OFS / FR_OFS / fr edge unchanged, reset release +10 once).

Per-flop clock arrivals of the g3a gate (TT, 4_1_cts.odb, placement parasitics; ck_insertion replay with locations,
results/arch/kv_ahub5_1019/README.md) located BOTH failures in the floorplan, not in the region partition:
  ck_c   the whole core band (u_core, 4 c->z write rings, w/e landing halves; 500 x 110 um) arrives 474..526 ps; only the
         N-face pin flops (u_io hs/hf, u_lpr_root at rst_n) 240 um above the band arrive 549..598 (the 154 ps).
         u_recip flops 444..463.  -> the core region must CONTAIN its own N-face pins: one compact core box under the
         hs pins, the reciprocal leaf directly below it (its x inputs face the box).
  ck_z0  the soft region (c->z read ring, z->c write ring, reset forest; 110 x 40 um) arrives 408..434 (26 ps), but
         the 7 u_lprc_u_zh0 reset pads sat in the second fence strip 170 um away (544..546), and the macro tap
         (92 ps, next to the S entry) + 246.5 insertion = 326..355 vs soft 408..434: the soft trunk around the macro was
         repaired AFTER TritonCTS balanced it.  -> ONE fence strip per Z tree (pads inside), clock entry midway between
         the strip and the macro clock pin (no long trunk on either branch).
Three parallel kits (no RTL change):
  qkd_ahub_g4a  Z inputs face the CENTRE (as g3), one inner strip per Z, z entries on the W / E face at mid height.
  qkd_ahub_g4b  Z inputs face the OUTLINE, one outer strip per Z, z entries on the W / E face at mid height.
  qkd_ahub_g4c  g4b geometry with the z entries kept on S / N under the strip centres (g3b positions; no clock-face
                change for the die).
All: core box x 194.4..518.4, y 388.8..537.84 with every core-region N pin above it, u_recip R0 at (259.2, 172.8);
right-column Z trees mirrored (MY / R180) so their clock pins face the E entry.

Usage: python3 tools/qwen_kv_die/ahub5/mk_kits.py   (then tools/ref_tile/ref_tile.py gen on each spec)
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_sp = importlib.util.spec_from_file_location("ahub4_mk", ROOT / "tools/qwen_kv_die/ahub4/mk_kits.py")
A4 = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(A4)

C_BOX = (194.4, 388.8, 518.4, 537.84)
W_BOX = (2.16, 186.0, 43.2, 354.0)
E_BOX = (680.4, 186.0, 732.24, 310.0)
RECIP = ("u_recip", 259.2, 172.8, "R0")
# core-region N pins, all above the core box (x 216..443); widths as g3
N_PINS = {"hs_start": (216.0, 220.32), "hs_ep": (220.32, 248.4), "hs_layer": (248.4, 259.2), "hs_ctx": (259.2, 280.8),
          "hf": (280.8, 302.4), "rst_n": (324.0, 328.0), "ck_c": (356.0, 358.0), "hs_cal_lo": (378.0, 432.0),
          "hs_cal_r": (432.0, 442.8)}
INNER = {"z0": (43.2, 194.4, 194.4, 237.6), "z1": (518.4, 194.4, 669.6, 237.6),
         "z2": (43.2, 302.4, 194.4, 345.6), "z3": (518.4, 302.4, 669.6, 345.6)}
OUTER = {"z0": (43.2, 2.16, 194.4, 43.2), "z1": (518.4, 2.16, 669.6, 43.2),
         "z2": (43.2, 496.8, 194.4, 537.84), "z3": (518.4, 496.8, 669.6, 537.84)}

VARIANTS = {
    "qkd_ahub_g4a": dict(
        # inputs (LEF S face) toward the centre: bottom MX / R180, top R0 / MY; clock pin (LEF W face y 148.4) on the
        # outline-side face: z0 (43.2, 46.0), z1 (669.6, 46.0), z2 (43.2, 494.0), z3 (669.6, 494.0)
        children=[("u_zh0", 43.2, 43.2, "MX"), ("u_zh1", 518.4, 43.2, "R180"), ("u_zh2", 43.2, 345.6, "R0"),
                  ("u_zh3", 518.4, 345.6, "MY"), RECIP],
        ck={"ck_z0": ("left", 130, 132), "ck_z1": ("right", 130, 132), "ck_z2": ("left", 408, 410),
            "ck_z3": ("right", 408, 410)},
        zf=INNER,
        why="variant A: Z inputs toward the centre, one inner strip per Z tree, z entries W/E at mid height"),
    "qkd_ahub_g4b": dict(
        # inputs toward the outline: bottom R0 / MY, top MX / R180; clock pins z0 (43.2, 191.6), z1 (669.6, 191.6),
        # z2 (43.2, 348.4), z3 (669.6, 348.4)
        children=[("u_zh0", 43.2, 43.2, "R0"), ("u_zh1", 518.4, 43.2, "MY"), ("u_zh2", 43.2, 345.6, "MX"),
                  ("u_zh3", 518.4, 345.6, "R180"), RECIP],
        ck={"ck_z0": ("left", 106, 108), "ck_z1": ("right", 106, 108), "ck_z2": ("left", 432, 434),
            "ck_z3": ("right", 432, 434)},
        zf=OUTER,
        why="variant B: Z inputs toward the outline, one outer strip per Z tree, z entries W/E at mid height"),
    "qkd_ahub_g4c": dict(
        children=[("u_zh0", 43.2, 43.2, "R0"), ("u_zh1", 518.4, 43.2, "MY"), ("u_zh2", 43.2, 345.6, "MX"),
                  ("u_zh3", 518.4, 345.6, "R180"), RECIP],
        ck={"ck_z0": ("bottom", 118, 120), "ck_z1": ("bottom", 594, 596), "ck_z2": ("top", 118, 120),
            "ck_z3": ("top", 594, 596)},
        zf=OUTER,
        why="variant C: g4b geometry, z entries S/N under the strip centres (g3b clock faces and positions)"),
}
FACE = {"left": "W", "right": "E", "bottom": "S", "top": "N"}


def kit_spec(kit, v):
    v4 = dict(children=v["children"], ck=v["ck"], why=v["why"],
              fences={"c": [C_BOX], "w": [W_BOX], "e": [E_BOX], **{z: [b] for z, b in v["zf"].items()}})
    s = A4.spec(kit, v4)
    pins = {f: [p for p in s["pins"][f] if not p.startswith("ck_z")] for f in ("N", "S", "W", "E")}
    for p, (face, a, b) in v["ck"].items():
        pins[FACE[face]].append(p)
    s["pins"] = pins
    for p, ab in N_PINS.items():
        s["pin_ranges"][p] = [ab[0], ab[1]]
    j = s["job"]
    j["owner"] = "Claude:KV-AHUB5 10-19"
    j["branch"] = "claude/kv-ahub5-g4-1019"
    j["tag"] = "v1"
    j["purpose"] = ("KV-AHUB5 (LEAD3-KV, K.STA.AHUB): g3 landed hub (same RTL) re-floorplanned from the g3a per-flop clock "
                    "census: compact core box under its own N pins, one fence strip per Z tree; " + v["why"])
    s["floorplan_note"] = s["floorplan_note"].replace("KV-AHUB4", "KV-AHUB5").replace(
        "ck_c N 358-360", "ck_c N 356-358 (core N pins x 216..443 above the core box)")
    s["structural_change"] = (
        "NEW kit (KV-AHUB5 10-19, after qkd_ahub_g3a / g3b gates FAIL clock_rule, ck_c 153.9-155.0 TT and Z roots "
        "81.7-216.8 TT): same RTL as g3; the g3a per-flop census put ck_c's tail on the N-face pin flops 240 um above "
        "the core band (band 474..526 ps, pins 549..598) and each Z root's on reset pads in a second fence strip plus a "
        "trunk repaired after balancing.  (1) the core region is ONE box under its own N pins with the reciprocal leaf "
        "directly below; (2) one fence strip per Z tree (reset pads inside); (3) z clock entries " +
        ("midway between the strip and the macro clock pin (W/E faces)" if FACE[v["ck"]["ck_z0"][0]] == "W" else
         "under the strip centres (S/N, g3b positions)") + "; right-column Z trees mirrored so their clock pins face E.")
    s["cycle_cost"] = ("none vs g3 (same RTL and schedule): HUB_RECIP / HUB_PUB +6, am +3 at the ASTK pins, AP_OFS / "
                       "FR_OFS / fr edge unchanged, reset release +10 once (results/arch/kv_ahub4_1019/README.md).")
    return s, v4


def main():
    pfx = A4.prefixes()
    for kit, v in VARIANTS.items():
        d = ROOT / "physical/ref_tile" / kit
        d.mkdir(parents=True, exist_ok=True)
        s, v4 = kit_spec(kit, v)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        (d / "lp_fences.tcl").write_text(A4.tcl_table(kit, v4, pfx).replace(
            "tools/qwen_kv_die/ahub4/mk_kits.py", "tools/qwen_kv_die/ahub5/mk_kits.py"))
        (d / "lp_fences_release.tcl").write_text(A4.RELEASE_TCL.format(kit=kit).replace(
            "tools/qwen_kv_die/ahub4/mk_kits.py", "tools/qwen_kv_die/ahub5/mk_kits.py"))
        print("wrote", d)


if __name__ == "__main__":
    main()
