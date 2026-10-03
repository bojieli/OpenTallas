# DS ROM full-system RTL (stream claude/dsrom-system-rtl-20261003): replay

All new RTL is in `rtl/dsrom_sys/`. Benches are in `rtl/test/dsrom_sys/`. No existing file was edited. Every block is a new module or a successor copy, and its default reproduces the original.

## Inventory

    python3 tools/dsrom_system_inventory.py          # -> inventory.json (31 blocks: before/after/owner/evidence)

## Unit benches (Icarus 11 unless noted)

| Record | Command | Blocks |
|---|---|---|
| `ctrlplane_units.json` | `python3 tools/dsrom_system_unit_benches.py` | `ot_dsrom_host_cq`, `ot_dsrom_stall_export`, `ot_dsrom_stage_guard` (16 cases, 2 mutants must fail) |
| `idx_scorer_loc_bench.json` | same | `ot_dsrom_idx_scorer_loc`: hub vs per-HBM-stack scorer, both equal to the golden `sorted(topk_lowest_index)` (8 cases, 2 mutants) |
| `link_rt_bench.json` | `python3 tools/dsrom_link_rt_campaign.py` | `ot_dsrom_link_rt`: seq/CRC-32/go-back-N/credit over reverse channel (17 cases, 4 mutants; Verilator lint) |
| `ckv_credit_bench.json` | `python3 rtl/test/dsrom_sys/run_ckv_credit_bench.py` | `ot_chip_v41x_ckv_die_service_cr` AG_CREDIT (41 cases) |
| `field_sys_bench.json` | `python3 rtl/test/dsrom_sys/run_field_sys_bench.py` | `ot_v41_field_w17w10_sys` FAULT_TIE + RET_CREDIT (Verilator 5.050, reduced NP16/R4) |
| `levers/window_refill_tag.json` | `python3 tools/dsrom_lever_window_refill_tag.py --scratch DIR` | EPOCH_SAFE refill tag, 600 refills across epoch 512 |

## System gate (end-to-end functional token simulation)

`rtl/test/dsrom_sys/tb_dsrom_system.sv` is a successor of `rtl/test/tb_hdc_v41x_array.sv`. It runs the all-unit V4.1x cores with the following:

- KV in attached HBM: kv_prefetch, shared K stacks and a timed refresh-aware HBM model. HDC_KV_HBM=1 is mandatory.
- Every link is `ot_dsrom_link_rt`. Board links run 156 cycles and UCIe links 12, with CRC errors injected on board links.
- `ot_dsrom_stage_guard` sits on every inbound stream.
- `ot_dsrom_host_cq` is the host binding: prompts, LAUNCH, tagged completions under 30% back-pressure, and a watchdog.
- `ot_dsrom_stall_export` runs per die.

To prepare the images and the ISA pipeline, which is exact against `hdc_golden_v41` and needs the tokenizer:

    python3 tools/dsrom_system_campaign.py --only CFG --scratch DIR --output prep.json --prepare-only

To build and run on ot-epyc1tb (Verilator 5.050):

    PATH=~/.local/opentallas-tools/verilator-5.050/bin:$PATH \
      python3 tools/dsrom_system_campaign.py --only CFG --prepared --scratch DIR --output gate.json

| CFG | Dies / packages | Links | Users | Steps |
|---|---|---|---|---|
| `sys_b2` | 2 / 2 | 2 board | 1 | positions 0, 1, 2 (pos 2 generated) |
| `sys_b5` | 5 / 3 | 2 UCIe + 3 board; 3 body stages + 2 chained lm_head parts | 1 | positions 0, 1 |
| `sys_b5_u2` | as `sys_b5` | as `sys_b5` | 2 | positions 0, 1 |
| `sys_b5_p3g2` | as `sys_b5` | as `sys_b5` | 1 | positions 0..3 |
| `sys_d5`, `sys_d5_u2`, `sys_d5_p3g2` | 5 / 3 | 2 UCIe + 3 board; 5 body dies, whole lm_head on the last | 1 or 2 | positions 0, 1 (or 0..3) |
| `sys_b2` with `OT_SYS_GPARAMS=LINK_RT=0 OT_SYS_TAG=_lrt0` | as `sys_b2` | pinned delay-line link | 1 | control for the cost of the link layer |

A gate passes only if every check below holds:

- every reduced token matches the golden, both on the device and through the host completion queue;
- every lm_head logit is bit-exact;
- the final KV state is exact, both in the HBM sectors and in the shadow, and the vector-memory state is exact;
- there are no core, protocol, link, guard, KV, host-queue or watchdog faults, and nothing is stuck.

## L0 diagnosis

See `l0diag/REPLAY.md`. This is the original w17 r4 configuration with a read-only observer, run fresh.

## Results so far

- `system_gate_sys_b2.json`: **PASS**. Tokens 2815, 3537 and 2047 at positions 0, 1 and 2 were exact. 1,304,979 cycles.
- `system_gate_sys_b5_FAIL_r1.log`: **FAIL**. The split lm_head ME bank image was incomplete. The fix is in the gate tool (8f6459462), and the r2 runs are queued.
- The remaining runs and next steps are in `STATUS.md`.
