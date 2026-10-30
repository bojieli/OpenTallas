# KV RX259 fault-gated data enables (FAULT_DREG), DIE-KV-46 2026-10-30

COORD ruling 2026-10-30 11:37 approved registering the RX fault broadcast (CAP_ED +1-fault-cycle class) for `qkd_hr_core_rx`.
The RX259 eco8 route failed TT -51.74 ps / 376 EP on `queue_fault -> fault reduction -> long wire -> BUFx24/16f fanout -> data
capture enables` (796 ps data in one cycle). The fanout is the 1028 data capture enables (`host_d`, `ing_d`, `ing_cls`).

Change: KV-only variant source `rtl/qwen_sys/host_20261013/fault_dreg/qkd_host_rx_class_admission.sv` (same module name,
drop-in for the KV qkd_hr_core_rx elaboration file list; `FAULT_DREG` default 1 there, 0 = original structure). The shared
original `rtl/qwen_sys/host_20261013/qkd_host_rx_class_admission.sv` stays byte-identical (pinned by signed S81/KV bindings). the data capture enables use a registered `fault_q`. Every grant and every control output (`host_v`,
`ing_v`, pointers, counts, credits, `queue_fault`, `admission_open`, `launch_quiet`, the `fault` port) still uses the raw fault,
so **no grant leaves in the extra cycle** and there are **0 added cycles** on any control output or the fault port.
The only difference: in the single fault-onset cycle a blocked grant may load the queue head into `host_d`/`ing_d` while
`host_v`/`ing_v` stay 0. `fault` is sticky until `rst_n`, so no later valid ever qualifies that data.

Evidence
- `run.sh <repo> 1 2 3 4 5 6` -> `bench_1030.log`: lockstep ref (origin/main) vs FAULT_DREG=0 (every output, every cycle) vs
  FAULT_DREG=1 (all control outputs every cycle; data whenever valid; no grant after fault), IR_REPL 0 and 1, 6 seeds x 400k
  cycles, 32-45 fault episodes and 9-19 blocked fault-onset grants per seed: PASS. Mutant `hp=hp_d` (grant leaks in the
  fault_q cycle) FAILS with D1_CTRL_MISMATCH.
- `equiv_fdr0.ys` (yosys 0.68, equiv_simple/induct -seq 2, STRAPPED=1): FAULT_DREG=0 vs original: 15632/15632 proven.
- `equiv_fdr1.ys`: FAULT_DREG=1 vs original: 14606 proven, 1026 unproven = exactly host_d 512 + ing_d 512 + ing_cls 2
  (the intended data-only difference); every other register and output equivalent.

Adoption (KV only): swap the variant path for the original in the `qkd_hr_core_rx` elaboration file list, regenerate the core RTL, kit LEC
against the new RTL, then G0C + die clock rerun under 12.20 one-block rules; RX counts only on a 259.2 plan-pin match.
