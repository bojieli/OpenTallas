#!/usr/bin/env python3
"""STEWARD-HBMe/HC 10-23: HC root (ot_hbm_hc_root_static) kits r1 (MAIN, tails stacked on the W result face) and r2
(FB, tails side by side, die-slot-like height).  Base = codex root xr4 diag kit (1a59c0d41, tail STAND-IN view, frozen
netlist inst names); die faces of r18h5 (result W, quarter-engine N, cfg/desc S, status E).  Layout only."""
import copy, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RT = ROOT / "physical/ref_tile"
BASE = RT / "hbm_hc_root_xr4_diag"
T = 388.8
BW, BH, BP = 174.744, 70.488, 70.512
SW, SH, SP = 94.824, 41.064, 41.088
FACES = {
    "W": ["tgt", "rst_n", "program_done", "cfg_target", "configured", "fault", "program_active", "cfg_v"],
    "N": ["gathered_mix_data", "qps", "qi_cnt", "qd_wa", "qd_xa", "qi_word", "qd_nv", "gathered_mix_row", "qi_lo", "qi_w",
          "gathered_mix_pos", "result_position", "qi_slot", "gathered_mix_v", "q_fault", "qps_f", "qps_v", "qd_ss", "qd_v",
          "qi_kind", "qi_v", "result_v"],
    "S": ["cfg_data", "desc_loops", "desc_limit", "cfg_addr", "desc_base", "clk", "launch_v", "desc_v"],
    "E": ["result"],
}


def up(v, q):
    return round(math.ceil(v / q - 1e-9) * q, 3)


def mk(name, W, H, tails, big, small, note):
    s = copy.deepcopy(json.loads((BASE / "spec.json").read_text()))
    s["name"] = name
    s["outline"] = {"w": W, "h": H, "exact": True}
    ch = s["children"]
    for c, (x, y, o) in zip(ch, tails):
        c["at"], c["orient"] = [x, y], o
    bigs = [m for m in s["macros"] if "1024x256" in m["view"]]
    smalls = [m for m in s["macros"] if "128x256" in m["view"]]
    for m, (x, y, o) in zip(bigs, big):
        m["at"], m["orient"] = [x, y], o
    for m, (x, y, o) in zip(smalls, small):
        m["at"], m["orient"] = [x, y], o
    s["pins"] = FACES
    s.pop("pin_ranges", None)
    s["child_lattice_um"] = 43.2
    s["low_fill_reason"] = ("hard-child-bound HC root (STEWARD-HBMe/HC 10-23, coordinator ack requested): 2 x 388.8 tails + "
                            "5 SRAMs; the W result face carries 3,072 b (>= 540 um at <= 5.7 pins/um)")
    s["structural_change"] = note
    s["job"] = dict(s.get("job", {}), owner="STEWARD-HBMe/HC", branch="claude/hbme-hc-1023", tag=name.split("_")[-1],
                    purpose=note[:400])
    kd = RT / name
    kd.mkdir(exist_ok=True)
    (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, W, H, round(W * H / 1e3, 1), "k um2")


def g(v):
    return round(round(v / 2.16) * 2.16, 3)


# r1 MAIN: tails R0 stacked on the E result band (result -> E; mixes W -> core strip); SRAM column W, MY (read ports E
# toward the core strip).  (MY tails are off the track lattice: "no origin fixes it" -> result face W -> E = die notice)
y_a, y_b = 43.2, 43.2 + T + 43.2
H1 = up(y_b + T + 43.2, 10.8)
x_s = 43.2
x_t = 259.2
W1 = up(x_t + T + 43.2, 10.8)
mk("hbme_hcroot_r1", W1, H1, [(x_t, y_a, "R0"), (x_t, y_b, "R0")],
   [(x_s, g(y_a + 120.0), "MY"), (x_s, round(g(y_a + 120.0) + BP, 3), "MY")],
   [(x_s, g(y_b + 60.0 + i * (SH + 21.6)), "MY") for i in range(3)],
   f"STEWARD-HBMe/HC 10-23 redesign of the BAD 950.4x777.6 root: {W1} x {H1}; tails R0 stacked on the fenced E result "
   "band (result -> E = die face notice W -> E, no port change), mixes W toward the core strip; SRAM column MY, read "
   "ports toward the core strip; quarter-engine N, cfg/desc S; 0 edges changed.")
# r2 FB: tails R0 side by side (A result -> A/B channel -> N band -> E band; B result -> E), SRAM + core row on top
y_t = 43.2
x_a, x_b = 43.2, 43.2 + T + 43.2
y_r = y_t + T + 21.6
H2 = up(y_r + BH + 24.84, 10.8)
W2 = up(x_b + T + 43.2, 10.8)
xs = [43.2, g(43.2 + BW + 21.6)]
xs_s = [g(xs[1] + BW + 21.6 + i * (SW + 21.6)) for i in range(3)]
mk("hbme_hcroot_r2", W2, H2, [(x_a, y_t, "R0"), (x_b, y_t, "R0")],
   [(x, g(y_r), "R0") for x in xs], [(x, g(y_r + 14.04), "R0") for x in xs_s],
   f"STEWARD-HBMe/HC 10-23 FB redesign of the BAD 950.4x777.6 root: {W2} x {H2} (die-slot-like height); tails R0 side "
   "by side, result -> E band, SRAM + core row on top; 0 edges changed.")
