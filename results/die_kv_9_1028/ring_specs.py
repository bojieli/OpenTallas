#!/usr/bin/env python3
"""DIE-KV-9 10-28 (COORD 07:05 ruling (d)): ref_tile specs for the 8 KV ring hard-core types (template replicas).
All W>=1000 KV landing rings (8 (W,D) classes, 197 instances die-wide, bind_s2 bind_clock_landings.json) become
leaf tiles kv_ring_w<W>d<D> = verbatim ot_dp_clk_landing_cas #(W, DEPTH).  Two related same-frequency CTS roots
(fclk = forwarded sender clock, write side; clk = receiver clock, read side), the same zero-phase relation the soft
kit SDC uses for the fclk_in edge clocks; the actual phase is the die STA count-aligned (CA) check.
Faces: W = sender side (fclk, t_rst_n, d), E = receiver side (clk, rst_n, strap_k, q, ready, fault).
Outline: H from the face pin demand (W+8 pins x 2 M4 tracks / 0.85 fill), width from the measured abc area
(results/die_kv_9_1028/ring_area.json) at util 0.50; both snapped up to the 2.16 lattice.
usage: ring_specs.py  -> writes results/die_kv_9_1028/specs/<name>.json"""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/die_kv_9_1028/specs"
AREA = json.loads((ROOT / "results/die_kv_9_1028/ring_area.json").read_text())
INST = {"kv_ring_w1045d4": 9, "kv_ring_w1057d4": 85, "kv_ring_w1057d8": 27, "kv_ring_w1063d4": 31,
        "kv_ring_w1063d8": 1, "kv_ring_w1119d4": 11, "kv_ring_w1119d8": 1, "kv_ring_w1560d4": 32}
LAT = 2.16
up = lambda v: round(math.ceil(v / LAT - 1e-9) * LAT, 3)
OUT.mkdir(parents=True, exist_ok=True)
for name, a in AREA.items():
    W, D = map(int, name[len("kv_ring_w"):].split("d"))
    H = up((W + 8) * 2 * 0.048 / 0.85 + 2 * 4.32)
    Wd = up(max(a["area_um2"] / 0.50 / H, 21.6))
    s = {
        "name": name, "top": name, "kind": "tile",
        "sources": ["rtl/common/ot_dp_clk_landing_ca.sv", "rtl/common/ot_meso_fifo.sv", "rtl/common/ot_dp_clk_landing.sv",
                    f"rtl/qwen_sys/kv_ring_cores_1028/{name}.sv"],
        "params": {}, "defines": [],
        "clock": "multiple_cts_roots", "clock_port": "clk", "clock_ports": ["clk", "fclk"],
        "clock_data_paths": "related_same_frequency",
        "clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
        "clock_entry_domains": {
            "core": {"ratio": [1, 1], "ports": ["clk"], "inputs": ["rst_n", "strap_k"], "outputs": ["q", "ready", "fault"]},
            "fwd": {"ratio": [1, 1], "ports": ["fclk"], "inputs": ["t_rst_n", "d"], "outputs": []}},
        "reset_ports": ["rst_n", "t_rst_n"],
        "outline": {"w": Wd, "h": H, "exact": True},
        "pins": {"W": ["fclk", "t_rst_n", "d"], "E": ["clk", "rst_n", "strap_k", "q", "ready", "fault"]},
        "recipe": 4,
        "route": {"pd": 0.5, "threads": 8, "peak_ram_gb": 24, "hold_margin_ns": 0.03,
                  "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}, "io_hold_margin_ns": 0.0, "macro_halo_um": 5.4},
        "pin_regs": {"enable": False, "reason": "the ring registers every input in its write slots (s_d, fclk) and every "
                     "output in the read register (RDREG, clk); a recipe pin register would add an unpriced cycle"},
        "io_flop_at_pins": False, "keep_pin_regs": True, "inhold": False, "outhold": False, "hold_budget": "die",
        "reset_landing": {"enable": False, "reason": "the ring has no reset tree of its own: t_rst_n / rst_n are the "
                          "landed sender / receiver starts of the parent"},
        "inter": [], "macros": [], "children": [],
        "structural_change": (f"DIE-KV-9 ring hard core (COORD 07:05 (d)): one count-aligned landing ring "
                              f"ot_dp_clk_landing_cas #(.W({W}), .DEPTH({D})) hardened verbatim; {INST[name]} KV instances "
                              "die-wide become template replicas (K per instance = strap_k tied at the parent). Moves the "
                              "W>=1000 rings out of the partition kits (pv_v4 463k > 400k cap)."),
        "job": {"owner": "Claude:DIE-KV-9", "branch": "claude/die-kv-9-1028", "tag": name,
                "purpose": f"KV landing-ring hard core {name} ({INST[name]} replicas) for the KV partition kits",
                "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}",
                "extra_paths": ["rtl/common", "rtl/qwen_sys/kv_ring_cores_1028", "rtl/test/meso/formal_ca"],
                "no_bench_reason": "verbatim ot_dp_clk_landing_cas (MESO-RECONCILE-1 fv_ca2 proofs A_ALL/A_TMO + strap "
                                   "LEC per used K on the soft ring); the wrapper adds no logic; kit LEC netlist vs RTL"},
    }
    (OUT / f"{name}.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, W, D, "outline", Wd, "x", H, "util", round(a["area_um2"] / (Wd * H), 3), "inst", INST[name])
