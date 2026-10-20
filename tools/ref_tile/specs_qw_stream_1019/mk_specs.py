#!/usr/bin/env python3
"""QW-CLUSTER3/STREAM 2026-10-19: ref_tile specs for qfd_dv_stream_tile (primary + parallel fallback outline)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
WIT = "results/rtl/qw_stream_tile_1019/bench"
MUTS = {2: "BF16 truncation instead of RNE", 21: "no highest-lane priority", 22: "no duplicate-address fault",
        31: "relay group 17 selects on the E valid copy", 32: "table-tap group 5 drops the SID match",
        33: "emit copy of relay group 9 stuck 0", 34: "write-any copy of xb group 3 stuck 0"}

def bench(m):
    b = {"name": f"stream_tile_m{m}", "cmd": f"bash rtl/test/qwen_dv/static_stream/run_tile.sh {{RUN}}/bench/m{m} {m}",
         "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"]}
    if m == 0:
        b.update(expect="pass", pass_regex=r"STREAM_TILE_EQ PASS edges10000", min_count_regex=r"emits(\d+)",
                 pass_witness=f"{WIT}/m0.log")
    else:
        b.update(expect="fail", fail_regex=r"STREAM_TILE_MISMATCH", fail_witness=f"{WIT}/m{m}.log", why=MUTS[m])
    return b

WIDTH = {"sw_lo": 544, "sw_v": 1, "sw_hi": 543, "so_w": 1088, "so_e": 1088, "se_lo": 544, "se_v": 1, "se_hi": 543,
         "tw_data_lo": 512, "xw_we": 8, "xw_addr": 192, "ck": 1, "rst_n": 1, "xw_data": 256, "xt_d_lo": 512,
         "tw_data_hi": 512, "tw_we": 1, "tw_kind": 2, "tw_addr": 24, "sid": 4, "cfg_v": 1, "cfg_dir": 2, "cfg_tag": 28,
         "fault": 1, "xt_v": 1, "xt_a": 24, "xt_bad": 1, "xt_d_hi": 512}
PINS = {"W": ["sw_lo", "sw_v", "sw_hi", "so_w"], "E": ["so_e", "se_lo", "se_v", "se_hi"],
        "S": ["tw_data_lo", "xw_we", "xw_addr", "ck", "rst_n", "xw_data", "xt_d_lo"],
        "N": ["tw_data_hi", "tw_we", "tw_kind", "tw_addr", "sid", "cfg_v", "cfg_dir", "cfg_tag", "fault",
              "xt_v", "xt_a", "xt_bad", "xt_d_hi"]}

def ranges(w, h, edge=4.0):
    """contiguous per-port ranges in face order (bit-aligned W/E relay halves), proportional to the port width"""
    out = {}
    for f, ports in PINS.items():
        L = (h if f in "WE" else w) - 2 * edge
        wt = {p: max(WIDTH[p], 6) for p in ports}   # >= ~1 um per port (narrow 1-bit regions)
        n = sum(wt.values())
        pos = edge
        for p in ports:
            ln = L * wt[p] / n
            out[p] = [round(pos, 3), round(pos + ln, 3)]
            pos += ln
    return out

def spec(name, w, h, tag, why_outline):
    return {
        "name": name, "top": "qfd_dv_stream_tile", "kind": "tile",
        "sources": ["rtl/qwen_dv/qfd_dv_stream_tile.sv"],
        "params": {"MUT": 0},
        "clock_port": "ck", "reset_ports": ["rst_n"],
        "recipe": 4,
        "reset_landing": {"enable": True, "stages": 2, "copies": {"rst_n": 16},
                          "why": "2 registered face stages, last stage 16 kept copies (~470 control reset loads, <=32 each); payload registers carry no reset"},
        "reset_relay_split": {"max_loads": 32},
        "pin_regs": {"enable": False, "reason": (
            "The RTL registers every pin: every input bit is captured at its face in qfd_dv_stream_tile (sw/se payload, "
            "sid, cfg, SU write ports; the valid / tap-hit / write-any / config-enable bits as (* keep *) per-32-bit-group "
            "copies decoded from the pins), every output is driven directly by a register (so_e/so_w relay, tw_*/xt_* tap "
            "output registers after the interior tap relay, fault).  A flow pin stage would add a second edge and fold the "
            "kept select copies into one flop per pin (1,088-load relay select).")},
        "keep_pin_regs": True,
        "io_flop_at_pins": {"cols": 4, "allow_none": True},
        "inhold": False, "outhold": False,
        "outline": {"w": w, "h": h},
        "std_area_um2": 7000,
        "fill_reason": {"pin_bound": (
            "6,946 external pins: W/E 2,176 each (1,088-bit relay in + out), S 1,482 (low tap halves + SU write ports), "
            "N 1,113; <= 6 pins/um needs >= 371 um on W/E, so a 40-60 % outline (~120 x 120 um) cannot carry them. "
            + why_outline + " Pin-bound, waived (low util costs wire only).")},
        "pins": PINS, "pin_ranges": ranges(w, h),
        "layer_cap": "M5", "pg_layer": "M5",
        "route": {"pd": 0.5, "period_ps": 833.333, "threads": 8, "peak_ram_gb": 24, "hold_margin_ns": 0.03,
                  "io_hold_margin_ns": 0.03, "pin_h": "M4", "pin_v": "M3 M5",
                  "pin_balance": {"h": "M4", "v": "M3 M5", "group_max": 1}},
        "structural_change": (
            "QW-CLUSTER3/STREAM 10-19: Q-DV stream face (qfd_dv_stream / static packer 9587da800) as a safe hard tile: "
            "face-registered inputs with kept per-32-bit select copies decoded at the face (closes the cfg2/SU-we/addr "
            "copy demand of the 1195cd50b consumer inside the tile), interior tap relay (+1 edge on tw/xt), control-only "
            "reset with 2-stage landing, static schedule, no backpressure."),
        "job": {
            "owner": "Claude:LEAD2-QW/QW-CLUSTER3-STREAM", "branch": "claude/qw-cluster3-stream-1019", "tag": tag,
            "purpose": "Qwen compute MU die Q-DV slice stream face (Q.SAFE.STREAM): relay + static x packer + table/x taps",
            "record_to": f"results/rtl/ref_tile/{name}", "views_to": f"physical/ref_tile/{name}/views",
            "auto_merge": False,
            "extra_paths": ["rtl/qwen_dv/qfd_dv_stream.sv", "rtl/test/qwen_dv/static_stream/tb_stream_tile.sv",
                            "rtl/test/qwen_dv/static_stream/run_tile.sh", WIT],
            "benches": [bench(m) for m in [0] + sorted(MUTS)]},
    }

S = [spec("qfd_dv_stream_t_1019", 302.4, 380.16, "s1",
          "302.4 x 380.16 (aspect 1.26): W/E 5.85 pins/um, S 5.0, N 3.8; relay W->E 302 um, every tap / packer hop <= ~345 um."),
     spec("qfd_dv_stream_t_fb_1019", 345.6, 440.64, "f1",
          "Fallback 345.6 x 440.64 (aspect 1.27): W/E 5.0 pins/um (pin-access relief), relay W->E 346 um.")]
for s in S:
    (HERE / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + "\n")
    print(HERE / f"{s['name']}.json")
