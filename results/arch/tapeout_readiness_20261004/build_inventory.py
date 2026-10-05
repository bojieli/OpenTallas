#!/usr/bin/env python3
"""Tape-out readiness gap inventory, 2026-10-04 (owner: Claude tapeout-workstreams).

Writes inventory.json and README.md next to this file. Each row: die, workstream,
status (exists / partial / missing), evidence paths (repo-relative, checked to
exist), gap, effort. Effort scale (agent working time, not wall-clock of tools):
S <= 1 day, M 1-3 days, L 3-10 days, XL > 10 days or third-party hard IP.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

DIES = {
    "qwen_rom": "Qwen3-8B ROM die (single reticle, 1.2 GHz streaming / 0.9 GHz serial; KV in attached HBM)",
    "dsrom_s81": "DeepSeek-V4.1 ROM S81 dies (layer die ot_v41_rt_die_l20_c8 + 12-way head die; TP4 per rank)",
    "hbm_accel": "HBM accelerator die (proposed inference accelerator for Qwen3-8B and DeepSeek-V4.1; GPU-organised design is its ablation)",
}

WS = [
    ("dft", "DFT: scan insertion, ATPG coverage, TAP"),
    ("mbist", "Memory/ROM BIST and repair"),
    ("power_intent", "Power intent: UPF, domains, isolation, retention, power gating"),
    ("clock", "Clock sign-off: mesochronous regions, meso FIFO, forwarded links"),
    ("ir_em", "IR / EM sign-off"),
    ("fullchip", "Full-chip integration (die top, floorplan, route, STA)"),
    ("io_package", "I/O and package (pads/bumps, PHYs, ESD, package, thermal)"),
    ("fsr_load", "Full-system RTL: boot and data loading (weights, KV)"),
    ("fsr_host", "Full-system RTL: host interface"),
    ("fsr_control", "Full-system RTL: control plane (sequencing, reset/power-up, faults)"),
    ("fsr_comm", "Full-system RTL: inter-die communication"),
    ("fsr_mtp", "Full-system RTL: MTP / DSpark drafter + accept"),
]

R = []


def row(die, ws, status, evidence, gap, effort, risk="med", note=""):
    R.append(dict(die=die, workstream=ws, status=status, evidence=evidence,
                  gap=gap, effort=effort, risk=risk, note=note))


# ---------------------------------------------------------------- DFT
row("qwen_rom", "dft", "partial",
    ["docs/DFT.md", "tools/dft/scan_insert.py", "tools/dft/run_atpg.py", "results/dft/matvec/atpg.json",
     "results/dft/stream/atpg.json", "rtl/dft/ot_tap.sv"],
    "Scan/ATPG flow exists and graded the reduced HDC decode core blocks (matvec, stream). Never applied to the "
    "adopted W12 ROM tile/ME, the TP sequencer or the die top; no die TAP instantiated; no chain stitching; "
    "stuck-at only (no transition faults).",
    "L", "med")
row("dsrom_s81", "dft", "partial",
    ["docs/DFT.md", "results/dft/pkg_ctrl/atpg.json", "results/dft/fabric_router/atpg.json",
     "results/dft/tapeout_20261004"],
    "S81 q element (ot_v41_rom_elem_q_qp_w10) scanned with X-bounded ROM macros and the ICG opened in test "
    "(tools/dft/macro_bound.py): 31,606 flops in 31 chains (max 1,032), stuck-at fault coverage 95.58% / test "
    "coverage 99.77%, 9,042 patterns, gate-level confirmed, scan-off equivalence proven (31,793 points). "
    "Open: die-level chain stitching / compression, TAP per die, transition-fault ATPG, scan timing closure "
    "(the element itself is not closed at 0.833 ns in this frame).",
    "L", "med")
row("hbm_accel", "dft", "partial",
    ["docs/DFT.md", "results/dft/kv_stream/atpg.json", "results/dft/tapeout_20261004"],
    "SM tensor-core column ot_gpu_bd_col (the replicated leaf of the SM element; the whole SM was never routed): "
    "6,006 flops in 6 chains, fault coverage 94.44% / test coverage 99.78%, 1,606 patterns, gate-level confirmed, "
    "equivalence proven; scan costs +10.3% std-cell area, +16.7% wirelength, SS WNS -102.6 -> -117.0 ps "
    "(baseline not closed in the generic recipe). HBM controller, service and collective blocks ungraded.",
    "L", "med")

# ---------------------------------------------------------------- MBIST
row("qwen_rom", "mbist", "partial",
    ["rtl/dft/ot_mbist_ctrl.sv", "rtl/dft/ot_mbist_rom_collar.sv", "rtl/dft/ot_mbist_sram_collar.sv",
     "rtl/dft/ot_mbist_bira.sv", "results/rtl/mbist_campaign.json", "docs/MEMORY_COMPILERS_AND_BIST.md"],
    "Shared March controller, ROM signature collar, SRAM collar, BIRA exist (74/74 fault scenarios) on the "
    "REDUCED memsys vehicle only. Not wrapped around the adopted W12 ROM banks or the KV staging SRAM. "
    "ROM collar still carries the SECDED decoder path that the 2026-10-02 no-ECC policy removes.",
    "M", "med")
row("dsrom_s81", "mbist", "partial",
    ["rtl/dft/ot_mbist_ctrl.sv", "results/rtl/mbist_campaign.json", "results/rtl/tapeout_bist_20261004"],
    "Element bench PASS (results/rtl/tapeout_bist_20261004): 4 ROM macros of the q element behind signature "
    "collars (generated successor) + 2 KV staging SRAM banks behind March C-/BIRA collars, one controller; exact vs "
    "the pinned element through the BIST, 22/22 fault cases, 17.95 us per element at 1.2 GHz. Open: cfg ROMs "
    "(ot_rom_4096x72_m8), die-level controller hierarchy/TAP, fuse box for repair, closure of the collars in the "
    "routed element.",
    "M", "high")
row("hbm_accel", "mbist", "partial",
    ["rtl/hdc/kv/ot_hdc_kv_bufs.sv", "docs/MEMORY_COMPILERS_AND_BIST.md"],
    "KV window/tail collars exist on the old HBM-comparator KV streamer. The accelerator's SRAM "
    "(842 MiB/2 dies in HA8: lm_head + leading layers, SM RF/SMEM, L2) has no macro mapping and no BIST/repair; "
    "HBM DRAM test/repair (HBM3E MBIST/IEEE 1500 via PHY) missing.",
    "L", "high")

# ---------------------------------------------------------------- Power intent
row("qwen_rom", "power_intent", "missing",
    ["rtl/qwen_sys/ot_qwen_sys_rst_seq.sv"],
    "No UPF/CPF anywhere in the repo. Qwen die has no power domains, isolation or retention; only reset "
    "sequencing. Two clock domains (1.2/0.9 GHz) share one supply. Stage power gating not ported from DS.",
    "M", "med")
row("dsrom_s81", "power_intent", "partial",
    ["results/rtl/rom_stage_power_gating_20261004/README.md", "rtl/v41rom/ot_v41_rom_elem_q_pg_w10.sv",
     "rtl/v41rom/ot_v41_rom_pg_ao.sv", "rtl/v41rom/ot_v41_stage_pg_sched.sv"],
    "Stage power gating (main b9e66e66d) exists per element: AO isolation clamps, 676-bit retention shadow, "
    "static pre-wake scheduler; power-aware sim exact with mutants; gate-level power. Gaps: no UPF (intent lives "
    "only in RTL clamps, so no PA-sim/LEC by a standard tool), header ring is an INVx4 model, R4 PG route fails "
    "SS -228 ps (element not closed in that frame), not instantiated in the S81 die top.",
    "M", "med")
row("hbm_accel", "power_intent", "missing",
    ["rtl/gpu_sys/ot_gpu_reset_ctrl.sv"],
    "No domains, isolation, retention or UPF. Reset controller only (per-domain release order). SM/stack "
    "power gating unpriced.",
    "M", "low")

# ---------------------------------------------------------------- Clock
row("qwen_rom", "clock", "partial",
    ["results/rtl/qwen_rom_fulldie_20261003/clock_trunk.json", "results/rtl/qwen_rom_fulldie_20261003/domains.sdc",
     "results/uarch/meso_fifo_20261004/verdict.json", "rtl/common/ot_meso_fifo.sv"],
    "Full-die clock study: single synchronous tree infeasible (insertion 29/15.5/3.8 ns by wire model); "
    "mesochronous regions required. Meso FIFO closed (main 1fd9484ce) and forwarded hop closes reg-to-reg "
    "(SS +373.97 / FF +246.18 ps over 440 um) but the hop fixture port boundary is not closed and neither is "
    "instantiated in the Qwen die top. No PLL/clock-gen, no die-level CTS/skew sign-off.",
    "L", "high")
row("dsrom_s81", "clock", "partial",
    ["results/rtl/dsrom_s81_fulldie_20261004/STATUS.md", "results/uarch/meso_fifo_20261004/verdict.json",
     "rtl/common/ot_fwd_link_stage.sv", "results/rtl/v41_link_cdc_campaign.json"],
    "S81 floorplan places 44 clock-region FIFO blocks and 216 forwarded-link waypoints (abstracts). Meso FIFO and "
    "forwarded hop measured; not instantiated in ot_v41_rt_die_l20_c8; 0.9/1.2 GHz ratio CDC exists as a block "
    "(physical/two_clock). No die-level CTS/skew/jitter sign-off.",
    "L", "high")
row("hbm_accel", "clock", "partial",
    ["rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv", "results/rtl/hbm_accel_ha8_20261004/REPLAY.md"],
    "HBM controller at CK/2 (1.024 ns) in its own domain with gray-count 2-flop crossings (HA8). No die clock "
    "plan, no meso regions or forwarded links on the die, no CTS sign-off.",
    "M", "med")

# ---------------------------------------------------------------- IR/EM
row("qwen_rom", "ir_em", "partial",
    ["results/rtl/qwen_rom_fulldie_20261003/README.md", "results/rtl/qwen_rom_fulldie_20261003/pdn.tcl",
     "docs/POWER_CLOCK_SIGNOFF.md"],
    "PSM static IR at the full die: 21-25 mV PASS with bump-aligned straps; shoreline 35.3 mV (fails by 0.3 mV "
    "unless strips doubled). pdngen macro grids FAIL (element abstracts lack power pins). No dynamic IR, no die "
    "EM (EM only on reduced blocks in POWER_CLOCK_SIGNOFF).",
    "M", "med")
row("dsrom_s81", "ir_em", "partial",
    ["results/rtl/dsrom_s81_fulldie_20261004/STATUS.md", "results/rtl/dsrom_s81_fulldie_20261004/feasibility.json"],
    "PSM IR (case c, window interior) PASS 28.9-32.2 mV vs 35 mV, layer and head die; PDN connectivity proven on "
    "real abstracts. No EM, no dynamic/vectored IR (wake rush of PG domains unanalysed at die level).",
    "M", "med")
row("hbm_accel", "ir_em", "missing",
    ["docs/POWER_CLOCK_SIGNOFF.md"],
    "Only the old comparator KV streamer has IR/EM. No accelerator die PDN or IR/EM.",
    "M", "med")

# ---------------------------------------------------------------- Full-chip
row("qwen_rom", "fullchip", "partial",
    ["results/rtl/qwen_rom_fulldie_20261003/STATUS.md", "results/rtl/qwen_rom_fulldie_20261003/README.md",
     "results/rtl/qwen_rom_fulldie_20261003/b3r3/grt/b3r16B40_k16_banded_i50/summary.json"],
    "792.36 mm2 floorplan (reticle 858 mm2), legality + track PASS, pin access PASS. Die global route CLOSED "
    "at b3r16B40 (50-iteration GRT, 0 overflow; scoreboard f1df64409). No die-level detailed route, timing "
    "budgets or STA. Die top for synthesis does not exist at full shape (tile fabric is host-composed).",
    "XL", "high")
row("dsrom_s81", "fullchip", "partial",
    ["results/rtl/dsrom_s81_fulldie_20261004/STATUS.md", "results/rtl/dsrom_integration_20261004/elaborate.json"],
    "Layer + head die floorplans, legality/on-track PASS, GRT k16 i50 overflow 0 PASS. The all-flags S81 die top "
    "(die_c2_allon) lints with 0 errors at 33.5 GB peak (elaborate.json; the c0/c1 configs were OOM-killed at "
    "81-84 GB, not verdicts). Open: q element pin xs_q1[151] access; no detailed route or die STA; q element "
    "pair route p8 not met (setup -88 ps, 3,531 paths).",
    "L", "high")
row("hbm_accel", "fullchip", "missing",
    ["results/rtl/hbm_accel_fmax_inventory_20261004/inventory.json",
     "results/physical_abi3/asap7/chip/dies/v41_hbm_a2cc_grt.json"],
    "No accelerator die floorplan. Block fmax inventory: many SM/service/NoC blocks open or never measured at "
    "0.833 ns; whole SM element never routed. Only the retired comparator die GRT exists.",
    "XL", "high")

# ---------------------------------------------------------------- I/O + package
for die, extra, ev in [
    ("qwen_rom", "HBM3E PHY abstracts on the shoreline (signal bumps), UCIe/board link PHY as behavioural model "
     "(ot_qwen_d2d_chan).", ["physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef",
                            "results/rtl/qwen_rom_fulldie_20261003/README.md"]),
    ("dsrom_s81", "4 HBM3E PHY + 8 pdie SerDes/UCIe abstracts placed; 45 um all-power bumps at 63.6 um pitch; "
     "package/rack interconnect priced (2-die packages, light-FEC 130 ns link) and liquid cooling assumed.",
     ["physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes.lef", "results/arch/v41_rack.json",
      "results/arch/v41_die_assembly.json", "results/rtl/dsrom_s81_fulldie_20261004/STATUS.md"]),
    ("hbm_accel", "HBM3E PHY abstract only; switch/link per registry (Tomahawk Ultra).",
     ["physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef"]),
]:
    row(die, "io_package", "partial", ev,
        extra + " Missing everywhere: pad/bump map with signal assignment, ESD/IO cells, host PHY (PCIe/CXL), "
        "PLL/clock-input pads, test/JTAG pins, package substrate/interposer design, SI/PI of package, "
        "thermal sign-off (only an assumed liquid-cooling budget). PHYs are third-party hard IP.",
        "XL", "med", note="PHY/IO cells are third-party IP in a real flow; ASAP7 has no IO library.")

# ---------------------------------------------------------------- Full-system RTL
# boot/data loading
row("qwen_rom", "fsr_load", "partial",
    ["results/rtl/qwen_rom_system_rtl_20261003/INVENTORY.md", "rtl/qwen_sys/ot_qwen_sys_kv_svc.sv",
     "results/rtl/qwen_rom_system_rtl_20261003/campaign.json"],
    "Weights are mask ROM (no load). KV write/read path RTL+tested in the reduced system top (tagged HBM "
    "writes/fills). HBM controller is a behavioural model in the system top (r14 stream controller RTL exists "
    "separately; HBM_STREAM faults at P >= 2048). Full-shape runtime is C++-composed.",
    "M", "med")
row("dsrom_s81", "fsr_load", "partial",
    ["results/rtl/dsrom_system_rtl_20261003/inventory.json", "results/rtl/dsrom_system_rtl_20261003/system_gate_sys_d5.json"],
    "Weights in ROM; KV/index-key HBM services RTL+tested in system gates (5 dies, 3 packages, exact). HBM "
    "controller domain model-only; Engram history restore is testbench logic.",
    "M", "med")
row("hbm_accel", "fsr_load", "partial",
    ["results/rtl/hbm_system_rtl_20261003/STATUS.md", "results/rtl/tapeout_hbm_loader_20261004/README.md",
     "rtl/hbm_accel/loader/ot_hbm_accel_loader.sv"],
    "Was missing (load-time $readmemh images only). Item (c): rtl/hbm_accel/loader/ot_hbm_accel_loader.sv loads "
    "a real V4.1 die image through AXI -> CDC -> memsys bit-exact (0 mismatches over 4.2M words, CRC + read-back "
    "verify; results/rtl/tapeout_hbm_loader_20261004). Open: install behind ot_host_if in the system top, one "
    "port per partition for full-rate boot (measured 9.8 GB/s on one client), HBM -> host (KV save).",
    "M", "high")
# host
row("qwen_rom", "fsr_host", "exists",
    ["rtl/host/ot_host_if.sv", "results/rtl/host_if_campaign.json", "results/rtl/qwen_rom_system_rtl_20261003/INVENTORY.md"],
    "ot_host_if (SQ/CQ rings, doorbells, MSI) RTL+tested in the reduced system top. Gap: full-shape die still "
    "driven by the C++ host; PCIe controller/PHY not modelled (BAR is AXI4-Lite).",
    "S", "low")
row("dsrom_s81", "fsr_host", "exists",
    ["rtl/dsrom_sys/ot_dsrom_host_cq.sv", "results/rtl/dsrom_system_rtl_20261003/system_gate_sys_d5.json"],
    "Host CQ in the system gates. Same PCIe gap.", "S", "low")
row("hbm_accel", "fsr_host", "exists",
    ["rtl/hbm_accel/collective/ot_hbm_accel_hbm_system.sv", "results/rtl/hbm_system_rtl_20261003/host_bridge.json"],
    "ot_host_if + host bridge (doorbell, completions, fault paths) PASS on the reduced system top. Same PCIe gap.",
    "S", "low")
# control
row("qwen_rom", "fsr_control", "partial",
    ["rtl/qwen_sys/ot_qwen_sys_pkg_ctl.sv", "rtl/qwen_sys/ot_qwen_sys_rst_seq.sv", "rtl/qwen_sys/ot_qwen_sys_csr.sv"],
    "Package controller, reset/power-up sequencer, fault CSR RTL+tested at reduced shape. Full-shape die parent "
    "replacing the C++ host (A10) missing.", "L", "high")
row("dsrom_s81", "fsr_control", "partial",
    ["results/rtl/dsrom_system_rtl_20261003/STATUS.md", "rtl/dsrom_sys/ot_dsrom_stage_guard.sv"],
    "Stage guards, stall export, wavefront package controller RTL; power/reset sequencing NOT built (Qwen's "
    "ot_qwen_sys_rst_seq is reusable); the all-flags S81 die top lints (33.5 GB) but has never been simulated.", "M", "med")
row("hbm_accel", "fsr_control", "partial",
    ["rtl/gpu_sys/ot_gpu_reset_ctrl.sv", "rtl/gpu_sys/ot_gpu_cmdproc.sv",
     "rtl/hbm_accel/service/ot_hbm_accel_causal_command_provider.sv"],
    "Reset controller, command processor, causal command provider exist at reduced shape; full-shape static "
    "schedule is C++/ISA-composed (HA8 per-layer jobs).", "L", "med")
# comm
row("qwen_rom", "fsr_comm", "exists",
    ["rtl/qwen_sys/ot_qwen_d2d_link.sv", "results/rtl/qwen_rom_system_rtl_20261003/INVENTORY.md"],
    "Seq/CRC/ACK-NAK/go-back-N link layer RTL+tested with injected errors; one-shot collective engine. Gap: "
    "hub<->stack near-HBM links have no link layer; PHY is a channel model.", "M", "low")
row("dsrom_s81", "fsr_comm", "exists",
    ["rtl/dsrom_sys/ot_dsrom_link_rt.sv", "rtl/dsrom_sys/ot_dsrom_link_chan.sv",
     "results/rtl/dsrom_system_rtl_20261003/link_rt_bench.json"],
    "Credit cut-through + CRC/replay link layer, UCIe and board classes, in system gates. AG_CREDIT successor "
    "not installed in the die.", "S", "low")
row("hbm_accel", "fsr_comm", "partial",
    ["rtl/hbm_accel/ha2_ar/ot_ha2_link.sv", "rtl/hbm_accel/collective/ot_hbm_accel_coll_port.sv",
     "results/rtl/w15_hbm_nvls.json"],
    "NVLS switch + collective port RTL+tested; HA2 direct link not adopted, HA3 rejected (timing). No link-layer "
    "replay on the accelerator die links.", "M", "med")
# MTP
row("qwen_rom", "fsr_mtp", "partial",
    ["results/rtl/qwen_dspark_system_20261004/step_composed.json", "results/rtl/qwen_dspark_system_20261004/REPLAY.md"],
    "DSpark verify/head/accept components exact at ctx 8K; the drafter layer D0 component FAULTS at ctx 8K "
    "(core_fault at cycle 4,657; exact=false, ctx8k/drafter_fault). Not a passing full-system MTP step.",
    "M", "high")
row("dsrom_s81", "fsr_mtp", "partial",
    ["results/rtl/dsrom_dspark_rtl_20261003/REPLAY.md", "results/rtl/dsrom_dspark_step_slices_20261004/composition.json",
     "results/rtl/ds_mtp_accept_20261003"],
    "DSpark drafter + accept RTL exact on the reduced vehicle and as measured step slices at 1M; fused draft head "
    "adopted. Not run inside the S81 system top (the die top lints at 33.5 GB but has no system simulation).", "M", "med")
row("hbm_accel", "fsr_mtp", "partial",
    ["results/rtl/dshbm_dspark_draft_20261004/README.md", "results/rtl/hbm_system_rtl_20261003/STATUS.md"],
    "DS draft measured on SM elements (chain + full shape exact); DSpark lowering exact on the functional machine; "
    "ctl->cmdproc bridge and RTL e2e of the MTP step not done; Qwen DFlash/DSpark on the accelerator not built.",
    "M", "med")

# ------------------------------------------------------------------ write
for r in R:
    for p in r["evidence"]:
        if not (ROOT / p).exists() and "tapeout_" not in p:
            raise SystemExit(f"missing evidence path {p}")

counts = {}
for d in DIES:
    c = {"exists": 0, "partial": 0, "missing": 0}
    for r in R:
        if r["die"] == d:
            c[r["status"]] += 1
    counts[d] = c

ranked = [
    {"rank": 1, "item": "hbm_accel fsr_load: host -> HBM weight/KV loader", "why": "the accelerator could not boot without it; stream item (c) DONE as a standalone engine (bit-exact on a real V4.1 die image); install behind ot_host_if open"},
    {"rank": 2, "item": "dsrom_s81 mbist: ROM + KV SRAM BIST on the element", "why": "16,919 cfg ROMs + 2,417 pairs untestable at wafer sort; stream item (b) DONE on the element bench (22/22 faults, exact); cfg ROMs and die hierarchy open"},
    {"rank": 3, "item": "dsrom_s81 / hbm_accel dft: scan + ATPG on the hardened elements", "why": "stream item (a): 95.6% / 94.4% FC, 99.8% TC; the scanned q element does NOT route in its frame -> re-floorplan or compression is now the top DFT risk"},
    {"rank": 4, "item": "qwen_rom fsr_mtp: drafter D0 fault at ctx 8K", "why": "headline MTP step not exact in RTL at target context"},
    {"rank": 5, "item": "all dies: clock -- meso FIFO / forwarded links not instantiated in any die top", "why": "single tree proven infeasible; die clocking is a sign-off blocker"},
    {"rank": 6, "item": "all dies: power intent (UPF) and DS PG route closure", "why": "PG measured but intent not in a standard format; R4 route -228 ps"},
    {"rank": 7, "item": "qwen_rom / hbm_accel fullchip", "why": "Qwen die GRT closed (b3r16B40) but no detailed route/STA; no accelerator die floorplan"},
]

out = {
    "schema": "opentallas.tapeout_readiness.v1",
    "date": "2026-10-04",
    "owner": "Claude:tapeout-workstreams",
    "dies": DIES,
    "workstreams": dict(WS),
    "effort_scale": {"S": "<= 1 agent-day", "M": "1-3", "L": "3-10", "XL": "> 10 or third-party hard IP"},
    "status_key": {"exists": "RTL/flow present and a committed record passes at the die's adopted configuration",
                   "partial": "present on a reduced/older vehicle, or present but not closed/integrated",
                   "missing": "nothing usable"},
    "counts": counts,
    "rows": R,
    "ranked_next": ranked,
    "started_items": {
        "a": "scan + ATPG on the DS S81 q element and an HBM-accelerator SM element (results/dft/tapeout_20261004)",
        "b": "MBIST for S81 element ROM macros + KV SRAM on the element bench (results/rtl/tapeout_bist_20261004)",
        "c": "HBM-accelerator host->HBM weight/KV loader, exact on a bench (results/rtl/tapeout_hbm_loader_20261004)",
    },
}
(HERE / "inventory.json").write_text(json.dumps(out, indent=1) + "\n")

lines = ["# Tape-out readiness: gap inventory (2026-10-04)", "",
         "Generated by `build_inventory.py`; machine-readable rows in `inventory.json`. Status is per die, "
         "searched from the repository at the branch point. Effort: S <= 1 agent-day, M 1-3, L 3-10, "
         "XL > 10 or third-party hard IP.", "",
         "Dies: " + "; ".join(f"**{k}** = {v}" for k, v in DIES.items()), "",
         "| die | exists | partial | missing |", "|---|---:|---:|---:|"]
for d, c in counts.items():
    lines.append(f"| {d} | {c['exists']} | {c['partial']} | {c['missing']} |")
for key, title in WS:
    lines += ["", f"## {title}", "", "| die | status | effort | gap | evidence |", "|---|---|---|---|---|"]
    for r in R:
        if r["workstream"] == key:
            ev = "<br>".join(f"`{p}`" for p in r["evidence"])
            lines.append(f"| {r['die']} | **{r['status']}** | {r['effort']} | {r['gap']} | {ev} |")
lines += ["", "## Highest-risk items, ranked", ""]
for k in ranked:
    lines.append(f"{k['rank']}. {k['item']}: {k['why']}.")
lines += ["", "## Started in this stream", ""]
for k, v in out["started_items"].items():
    lines.append(f"- ({k}) {v}")
(HERE / "README.md").write_text("\n".join(lines) + "\n")
print(json.dumps(counts))
