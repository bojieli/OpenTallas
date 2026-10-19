#!/usr/bin/env python3
"""HBM-NEXT-UNITS IDXQ 2026-10-19: ref_tile specs of the IDXN quad tiles (hnx_idxq_link, hnx_idxq_kb, hnx_idxq_qctl).
Run from the repo root; writes physical/ref_tile/<name>/spec.json, then: tools/ref_tile/ref_tile.py gen <spec>."""
import json
from pathlib import Path
M64 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2'
M256 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
ROUTE = {"pd": 0.5, "period_ps": 833.333, "threads": 8, "peak_ram_gb": 32, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
         "macro_halo_um": 5.4, "pin_balance": {"h": "M4", "v": "M5", "group_max": 1}}
COMMON = {"kind": "tile", "reset_ports": ["rst_n"], "layer_cap": "M5", "recipe": 4, "params": {}, "children": [], "inter": [],
          "io_flop_at_pins": {"cols": 4, "allow_none": True}, "keep_pin_regs": True, "reset_landing": {"enable": True, "stages": 2},
          "clock_data_paths": "related_same_frequency",
          "clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0}}
JOB = lambda tag, purpose: {"owner": "Claude:HBM-NEXT-UNITS", "branch": "claude/hbm-next-units-idxq-1019", "tag": tag,
                           "purpose": purpose, "benches": [], "extra_paths": ["rtl/hbm_next/idxq", "rtl/hbm_next/idxn",
                           "tools/hbm_next/hnx_idxq_bench.sh", "tools/hbm_next/hnx_idxq_vectors.py", "tools/hbm_next/hnx_idxn_calendar.py"]}
specs = []
# ---- idx_link: selector merge + IDXN row-slot link (pin-registered shell); d4g hidx_link_pr macro column, 2 selectors per side
ys = [(69.12, False), (146.928, True), (246.24, False), (324.048, True), (423.36, False), (501.168, True), (600.48, False), (678.288, True)]
link = dict(COMMON, name="hnx_idxq_link", top="ot_hnx_idxq_link",
    sources=["rtl/hbm_next/idxq/ot_hnx_idxq_link.sv", "rtl/hbm_next/idxn/ot_hnx_idxn_link.sv", M64 + "/ot_sram_1r1w_64x512_m1_r2c2_bb.v"],
    clock_port="clk", outline={"w": 388.8, "h": 820.8},
    pins={"N": ["clk", "rst_n", "clear", "row_clear", "in_slot", "flush", "emit_v", "emit_group", "emit_slot", "rank", "gbase",
                "tx_v", "tx", "fault", "selected_count"] + [f"clk_mem"],
          "W": ["sel_v_w", "sel_line_w"], "E": ["sel_v_e", "sel_line_e"], "S": []},
    route=ROUTE, pin_regs={"enable": False, "reason": "the IDXN link is the d4g pin-register shell (ot_hnx_idxn_link: one kept flop per "
        "data bit in and out); the 4-selector merge (OR of one + collision fault) sits before the shell's input flops; a synthesis "
        "wrapper would add an unpriced stage"},
    macros=[{"view": M64, "count": 1, "inst": f"link.core.gm[{i}].mem", "at": [108.0, y], **({"at_exact": True} if ex else {}),
             "clock_entry": {"port": f"clk_mem[{i}]", "pin": "clk", "reference": "raw_liberty_clock_pin"}} for i, (y, ex) in enumerate(ys)],
    clock="hybrid_entries", clock_ports=["clk"] + [f"clk_mem[{i}]" for i in range(8)],
    clock_entry_domains=dict({"core": {"ratio": [1, 1], "ports": ["clk"], "inputs": ["rst_n", "clear", "row_clear", "in_slot", "sel_v_w",
        "sel_line_w", "sel_v_e", "sel_line_e", "flush", "emit_v", "emit_group", "emit_slot", "rank", "gbase"],
        "outputs": ["tx_v", "tx", "fault", "selected_count"]}},
        **{f"mem{i}": {"ratio": [1, 1], "ports": [f"clk_mem[{i}]"], "inputs": [], "outputs": []} for i in range(8)}),
    clock_cts_roots=["clk"], inhold=False, outhold=False, reset_landing={"enable": True, "stages": 2, "clock": "clk"},
    job=JOB("q1", "HBM-NEXT P=4 IDXN quad: idx_link = 4 time-shared selectors merged (2 per W/E face, 2 x 2,368 b) into the IDXN "
            "row-slot link (8 row slots in the d4g 64x512 banks); d4g hidx_link_pr macro column"))
specs.append(link)
# ---- idx_kb<q>: quarter key replay buffer, 4 PC key lines x 1,088 b x 171 beats = 17 macros 256x256 (strap pbase = 4 x half)
KBX = [26.568, 225.288, 424.008, 622.728]
KBY = [(101.52, False), (142.608, True), (207.36, False), (248.448, True)]   # abutted pitch = 41.064 + 0.024
KBM = [{"view": M256, "count": 1, "inst": "gm[0].mem", "at": [KBX[0], 38.88], "at_exact": True}]
for c in range(4):
    for j, (y, ab) in enumerate(KBY):
        KBM.append({"view": M256, "count": 1, "inst": f"gm[{1 + 4 * c + j}].mem", "at": [KBX[c], y], "at_exact": True})
kb = dict(COMMON, name="hnx_idxq_kb", top="ot_hnx_idxn_keybuf", params={"NP": 4, "RS": 1},
    sources=["rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv", M256 + "/ot_sram_1r1w_256x256_m2_r2c2_bb.v"],
    clock_port="clk", outline={"w": 820.8, "h": 388.8},
    pins={"N": ["clk", "rst_n", "clear", "pbase", "live_v", "live_index", "pre_v", "pre_index", "replay_v", "replay_index", "fault",
                "key_in"], "S": ["key_out"], "W": [], "E": []},
    # IDXQ 10-19 (gate: 17 macros in a 4 x 4 + 1 grid unrelated to the key bit order, GPL-0305): 4 columns under their
    # key_in bit spans (column c holds bits 1,280 c .. at ~5.4 pins/um), each 2 abutted N-S pairs (pins on the macro W / E
    # edges, bare N / S faces touch) + the 17th macro below column 0; >= 20 um channels W / E of every column.
    route=ROUTE, macros=KBM,
    pin_regs={"enable": False, "reason": "key_in -> 2:1 replay mux -> key_out feeds the quarter scorer's kept key pin flops "
        "(ot_hbm_idx_score_quarter_static kl_r) on the SAME edge as a live line (IDXN timeline, lockstep-proven); a pin stage "
        "here would add an unpriced edge on the key path (+1 to the scorer beat in the calendar if adopted). RS=1: the mux "
        "select is a registered per-column copy of the PRE strobe (no port -> key_out control path)"},
    fill_reason={"pin_bound": "8,792 key bits (4,396 in N + 4,396 out S) at <= 6 pins/um need >= 733 um faces"},
    job=JOB("q1", "HBM-NEXT P=4 IDXN quad: idx_kb<q> = key replay buffer of one quarter scorer (17 macros 256x256, 4 PC key "
            "lines x 171 beats; row 0 captures the live HBM lines, rows >= 1 replay them; one master, strap pbase)"))
specs.append(kb)
# ---- idx_ctl<q>: IDXN quadrant calendar copy (8 row streams, 1 frame SRAM)
qctl = dict(COMMON, name="hnx_idxq_qctl", top="ot_hnx_idxq_qctl",
    sources=["rtl/hbm_next/idxq/ot_hnx_idxq_qctl.sv", "rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv", "rtl/lib/ot_rst_relay.sv",
             M256 + "/ot_sram_1r1w_256x256_m2_r2c2_bb.v"],
    clock_port="clk_program", reset_ports=["rst_n"], outline={"w": 222.48, "h": 99.36},
    # QCTL 10-19 (gate 2: spread 104 ps > 80 TT; review: macro centred splitting the std cells, macro pins W, clk pin NW
    # corner): the frame SRAM sits against the pin-free N face on the lattice (43.2, 86.4) (its N/S faces are bare; read
    # data / control on its W edge, write mask + half the write data on its E edge -> >= 20 um channels W and E); the std
    # cells form ONE band around it (W strip 43 um, E strip 24 um, full-width S band 86 um); inputs on W, outputs on S,
    # clk_program pin mid-S under the register mass, clk_program_mem on W beside the macro W edge; CW=1 calendar.
    # gate 3 (241.92 x 131.76, macro (43.2, 86.4)): spread 26.4 TT / 24.6 FF PASS, std density 17%, cross-clock
    # rd_out -> stream w1 -19 ps -> shrunk to 222.48 x 99.36 (macro (25.92, 54.0), W strip 24 um, S band 48 um).
    pins={"W": ["clk_program_mem", "rst_n", "slot", "program_we", "program_addr", "program_data", "start", "length", "n_rows",
                "row_pitch", "nkeys"],
          "S": ["clk_program", "weight_slot", "query_slot", "query_index", "query_emit", "query_emit_head", "key_slot", "key_v",
                "key_index", "key_row", "pre_v", "pre_index", "nq", "frame_start", "row_start", "vf", "qf", "scf", "kbf", "fault"],
          "N": [], "E": []},
    pin_ranges={"clk_program": [109.0, 113.0], "clk_program_mem": [72.0, 76.0]},
    route=dict(ROUTE, cts_sink={"size": 16, "diameter_um": 30, "extra": "-balance_levels"}), macros=[{"view": M256, "count": 1, "inst": "*calendar.store",
        "at": [25.92, 54.0], "at_exact": True,
        "clock_entry": {"port": "clk_program_mem", "pin": "clk", "reference": "raw_liberty_clock_pin"}}],
    clock="hybrid_entries", clock_ports=["clk_program", "clk_program_mem"],
    clock_entry_domains={"core": {"ratio": [1, 1], "ports": ["clk_program"], "inputs": ["rst_n", "slot", "program_we", "program_addr",
        "program_data", "start", "length", "n_rows", "row_pitch", "nkeys", "vf", "qf", "scf", "kbf"],
        "outputs": ["weight_slot", "query_slot", "query_index", "query_emit", "query_emit_head", "key_slot", "key_v", "key_index",
                    "key_row", "pre_v", "pre_index", "nq", "frame_start", "row_start", "fault"]},
        "mem": {"ratio": [1, 1], "ports": ["clk_program_mem"], "inputs": [], "outputs": []}},
    clock_cts_roots=["clk_program"], cts_sink_note="9,290 sinks in 259 x 130 um: gate 1 spread 118 / gate 2 104 ps > 80 at TT -> CW=1 windows (~4.4k sinks) + L band",
    reset_landing={"enable": True, "stages": 2, "clock": "clk_program"},
    pin_regs={"enable": False, "reason": "every input lands in a kept pin flop and every output leaves a flop in the RTL (+1/+1 edge, "
        "the d4g ot_hbm_idx_qctl_static pin rule, lockstep-proven); automatic pin registers would add an unpriced edge"},
    job=JOB("q1", "HBM-NEXT P=4 IDXN quad: idx_ctl<q> = IDXN issuer copy (8 pipelined row streams over one frame SRAM, per-class "
            "routing, collision = fault) for the quadrant's operand reader / query / key buffer / quarter scorer"))
specs.append(qctl)
for s in specs:
    d = Path('physical/ref_tile') / s['name']; d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    print(d / 'spec.json')
