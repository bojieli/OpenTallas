#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM system inventory (stream claude/dsrom-system-rtl-20261003).

Every block on the token path, with status and owner, before and after this
stream.  Status vocabulary:
  RTL+tested  RTL on the token path with a committed passing bench/gate
  RTL-untested RTL exists, no bench composes it on the token path
  tb-only     the function exists only as testbench / C++ host logic
  model-only  only a Python model or record
  missing     nothing
`after` refers to this stream's deliverables; `evidence` names the record.
Writes results/rtl/dsrom_system_rtl_20261003/inventory.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/dsrom_system_rtl_20261003/inventory.json"
R = "results/rtl/dsrom_system_rtl_20261003/"
GAPS = "/tmp/claude-review-20261003/rombridge/partB.md"

ROWS = [
    # ---------------- data loading
    ("data", "ROM field read (cfg ROM + macro read + spine broadcast -> element)",
     "RTL+tested", "RTL+tested", "rtl/v41die/ot_v41_field_w17w10.sv, ot_v41_spine_w17w10.sv",
     "Claude W17/W10 field owners (qelem timing: claude/dsrom-qelem-timing-20261003)",
     "field gates rtl/test/v41_runtime/w17_w10_field_rt_gate.cpp; ROM ECC removed (owner decision 2026-10-02)"),
    ("data", "field fault vector (D1: 127 undriven n_fault bits)",
     "RTL defect", "RTL+tested (default-off successor FAULT_TIE)", "rtl/dsrom_sys/ot_v41_field_w17w10_sys.sv",
     "this stream", R + "field_sys_bench.json"),
    ("data", "element -> return tree -> VM row write: backpressure/ACK (B2a)",
     "missing (overflow only faults)",
     "RTL+tested (default-off RET_CREDIT; reduced NP16/R4; issue gate never engaged on real phases -- no-overflow came from root FIFO sizing)",
     "rtl/dsrom_sys/ot_v41_field_w17w10_sys.sv, ot_v41_spine_w17w10_sys.sv", "this stream",
     R + "field_sys_bench.json"),
    ("data", "embedding / Engram hash + table read", "RTL+tested", "RTL+tested (in system gate)",
     "rtl/hdc/v41x (X_EG=1) + package Engram history restore", "V4.1x core owners",
     "system gate; Engram history restore is still testbench logic (tb_hdc_v41x_array g_prime)"),
    ("data", "QE weight stream from attached HBM (qstream + timed HBM model)", "RTL+tested", "RTL+tested",
     "rtl/hdc/hbm/ot_hdc_qstream.sv, rtl/hdc/kv/ot_hdc_hbm_model.sv (behavioural timed HBM)", "V4.1x core owners",
     "results/rtl/hdc_v41x_array_allunit_b2_o1fast_full.json; system gate"),
    ("data", "attached-HBM KV service (descriptor gating, 2-slot prefetch, K-stack arbiter, runtime KV writes)",
     "RTL, array token gate never completed (KV_HBM preflight only)", "RTL+tested in array token gate",
     "rtl/chip/ot_chip_v41x_kv_prefetch.sv, ot_chip_v41x_hbm_karb.sv, rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
     "Claude KV prefetch owners", R + "system_gate_*.json (KVHBM line)"),
    ("data", "index-key service (pooled writer/read bridge on 4 HBM stacks)", "RTL+tested", "RTL+tested",
     "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv", "V4.1x core owners", "system gate IDXHBM lines"),
    ("data", "index scorer location (hub vs per-HBM-stack shoreline, coordinator 2026-10-03)",
     "missing", "RTL+tested (unit; IDX_SCORER_LOC param), not inside ot_hdc_core_v41x",
     "rtl/dsrom_sys/ot_dsrom_idx_scorer_loc.sv", "this stream", R + "idx_scorer_loc_bench.json"),
    ("data", "selected-KV gather: remote rows on ag_rx (D3: no ready/credit)", "RTL defect (always taken)",
     "RTL+tested (default-off AG_CREDIT successor; not installed in the die; full rate needs RXQ~160, unpriced)",
     "rtl/dsrom_sys/ot_chip_v41x_ckv_die_service_cr.sv",
     "this stream", R + "ckv_credit_bench.json"),
    ("data", "HBM controller domain + measured service (H3: HBM_LAT_S, PC_RDY)", "model-only", "model-only",
     "-", "Codex/Nash finite service; open", GAPS + " H3"),
    # ---------------- communication
    ("comm", "stage-to-stage hop / package link (credit cut-through)", "RTL+tested (delay-line PHY, immediate credit)",
     "RTL+tested (LINK_RT successor)", "rtl/rom/ot_rom_pkg_link.sv -> rtl/dsrom_sys/ot_dsrom_link_rt.sv",
     "this stream", R + "link_rt_bench.json; system gate LINK lines"),
    ("comm", "link layer: sequence / CRC-32 / ACK-NAK go-back-N replay / credit over reverse channel (L1)",
     "missing (W15 CRC detects, no replay)", "RTL+tested", "rtl/dsrom_sys/ot_dsrom_link_rt.sv, ot_dsrom_link_chan.sv",
     "this stream", R + "link_rt_bench.json"),
    ("comm", "intra-package UCIe die-die link class", "RTL (same pkg link, no class)", "RTL+tested (class 0, 12 cycles)",
     "ot_dsrom_link_sel LINK_CLASS=0", "this stream", "system gate sys_b5 links 0->1, 2->3"),
    ("comm", "board light-FEC link class with injected CRC errors", "missing", "RTL+tested (class 1, 156 cycles, errors 1/97 fwd 1/53 rev)",
     "ot_dsrom_link_sel LINK_CLASS=1", "this stream", "system gate LINK lines"),
    ("comm", "PHY / FEC / SerDes", "stand-in", "stand-in (delay line + bit-flip injection)", "ot_dsrom_link_chan",
     "hard IP, out of scope", "-"),
    ("comm", "link CDC (plesiochronous)", "RTL+tested (separately)", "RTL+tested separately, not in system gate",
     "rtl/rom/ot_rom_link_cdc.sv", "existing", "results/rtl/v41_link_cdc_campaign.json"),
    ("comm", "TP-4 one-shot all-reduce / all-gather (die_px, UCIe ring + relay)", "RTL+tested (w17 die group, behavioural links)",
     "unchanged; not in reduced array (TP=1 stages)", "rtl/rom/ot_rom_oneshot_allreduce.sv, ot_rom_oneshot_px.sv",
     "existing; C5hc/PAR2 mapping: claude/dsrom-c5hc-adopt-20261003", "results/arch/v41_collective_levers.json"),
    ("comm", "lm_head part chain (running-argmax reduce) + RESULT gather to source", "RTL+tested",
     "RTL+tested in system gate sys_b5", "ot_rom_pkg_ctrl_x COMBINE_IN/SEND_RESULT", "existing", "system gate sys_b5"),
    ("comm", "switched fabric router + multicast", "RTL+tested (X_HE-only array)", "unchanged; not in system gate",
     "rtl/rom/ot_rom_fabric_router.sv", "existing", "results/rtl/hdc_v41x_array_b5_router_rv_316_o1all_full.json"),
    # ---------------- control plane
    ("ctrl", "host command / completion queue (tagged, back-pressured, admission reservation)",
     "tb-only (bench prompt array + cfg)", "RTL+tested (unit + system gate)", "rtl/dsrom_sys/ot_dsrom_host_cq.sv",
     "this stream", R + "ctrlplane_units.json; system gate HOSTCQ line"),
    ("ctrl", "hardware progress watchdog with exported cause", "missing", "RTL+tested (unit)",
     "ot_dsrom_host_cq WDOG + stall_cause", "this stream", R + "ctrlplane_units.json"),
    ("ctrl", "per-die sequencer (decode core program issue)", "RTL+tested", "RTL+tested", "ot_hdc_core_v41x",
     "V4.1x core owners; Hubble: instruction/deadline", "system gate"),
    ("ctrl", "package controller (job scheduling, token feedback, per-user context)", "RTL+tested", "RTL+tested",
     "rtl/rom/ot_rom_pkg_ctrl_x.sv", "existing", "system gate"),
    ("ctrl", "stage handoff identity (dest/src/type/len/framing/user/position)", "partial (position order only)",
     "RTL+tested", "rtl/dsrom_sys/ot_dsrom_stage_guard.sv", "this stream", R + "ctrlplane_units.json"),
    ("ctrl", "stall / trace export", "missing (S0; original L0 undiagnosable)", "RTL+tested",
     "rtl/dsrom_sys/ot_dsrom_stall_export.sv (system gate), l0diag successor (L0)", "this stream",
     R + "ctrlplane_units.json; " + R + "l0diag/"),
    ("ctrl", "fault reporting (aggregation of core/protocol/link/guard/KV/host faults)", "partial", "RTL in system top",
     "tb_dsrom_system SYS_FAULT", "this stream", "system gate"),
    ("ctrl", "reset / power-up / power-gating sequencing (P1)", "RTL-untested on die", "unchanged (owner Maxwell/Archimedes)",
     "rtl/chip/ot_chip_v41_pg_ctrl.sv etc.", "Codex Maxwell/Archimedes", GAPS + " P1"),
    ("ctrl", "0.9 GHz serial-chain domain + 3:4 CDC (B4/C1)", "model-only (ratio FIFO fails SS)", "owned by two-clock stream",
     "rtl/common/ot_ratio_cdc_fifo.sv (claude/two-clock-rtl-20261003)", "claude/two-clock-rtl-20261003", GAPS + " B4"),
    ("ctrl", "Nash VM-version lease / dependent-SU guard / R+2 tag retirement (B3a/B3b)", "model-only", "model-only (Codex Nash owns)",
     "-", "Codex Nash", GAPS + " B3a/B3b"),
    ("ctrl", "checkpoints", "Codex Peirce", "unchanged", "-", "Codex Peirce", "-"),
    ("ctrl", "MTP verify/commit/rollback (M1)", "ISA-only", "owned by DSpark RTL stream", "-",
     "claude/dsrom-dspark-rtl-20261003", GAPS + " M1"),
]


def main():
    rows = [dict(zip(("area", "block", "before", "after", "rtl", "owner", "evidence"), r)) for r in ROWS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "opentallas.dsrom.system_inventory.v1", "gap_source": GAPS,
                               "rows": rows}, indent=1) + "\n")
    print(len(rows), "rows ->", OUT)


if __name__ == "__main__":
    main()
