# Replay

Both generators are pure arithmetic. Part A prints in under 1 s and Part B in about 20 s.

```bash
cd results/uarch/risk_perf_reticle_20261003

# Part A: every input is a literal from the record named in SOURCES inside the script
python3 part_a_ledger.py > part_a_ledger.json

# Part B: run the corridor gate's own die_statement from an archive of its branch
TREE=$(mktemp -d)
git archive origin/claude/qwen-corridor-gate-20261003 | tar -x -C "$TREE"   # 19a660e14 at the time of writing
python3 part_b_reticle.py --tree "$TREE" > part_b_reticle.json
```

## Inputs read

| Input | Ref |
|---|---|
| Qwen one-stream full token, 144,522 cycles | `claude/layer-parallel-sim-20261003` @ 4c51918c9 |
| Near-HBM attention, 1,824 cycles at R=8 and 2,022 at R=6 | `claude/qwen-nearhbm-attn-20261003` @ ba283a6ad |
| HBM streaming at 0.958 TB/s (needs the 261-cycle notice and REFpb) | `claude/qwen-hbm-sustained-bw-20261003` @ 52ce3e9c1 |
| Calibrated calendar: 2,793 tok/s, KV-fill bound, `target_3k_s` | main, `results/uarch/qwen_rom_calibrated_calendar_20261003/` |
| Qwen DSpark pricing | `claude/qwen-rom-speculation-recheck-20261003` @ f10a0df32, `pricing.json` |
| DS ROM C1 with measured collectives: 2,356.8 AR, 3,203.4 MTP | `claude/dsrom-c5hc-adopt-20261003` @ 4ec2eef0e |
| Phase-merge gap (87,800 cycles) and the other RTL-vs-model gaps | `claude/free-levers-audit-20261003` @ b98b05222 |
| q-element pipelining price | `claude/dsrom-qelem-pipeline-20261003` @ 0b831a7d4 |
| Failed zero-latency q-element timing | `claude/dsrom-qelem-timing-20261003` @ 693a69076 |
| Two-clock crossing successor: 2/2 cycles, +0.54–0.65% | `claude/two-clock-rtl-20261003` @ 27d86cfe |
| DS HBM DSpark real draft and measured union | `claude/v41-hbm-speculation-20261003` @ d2aff19ef |
| DS HBM W19 fused 2,261.7 and H5 2,322.7 | main, `results/uarch/consolidation.json` |
| Qwen HBM 880.5 and DFlash b16 2,671 | main, `results/uarch/hbm_gpu.json` |
| r2 floorplan, 792 mm² | `claude/qwen-rom-floorplan-nearhbm-20261003` @ ced04cd96, `model-r2.json` |
| Corridor gate records | Uncommitted, read on 2026-10-03: `ot-agidock128:/home/ubuntu/otjobs/qcg_records/*_released.json` and `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-corridor-gate/STATUS.md`. Re-read them, and the committed `verdict.json` once `summary` has run, before acting on Part B. |

## Limits

- The τ values are unqualified: 3.649 pooled, 4.69 pilot agentic median, and the LMSYS figures 2.91 / 5.24. The LMSYS 3.78 is a verify window, not an accepted length.
- Part A converts the DS phase-merge and fusion gaps from the `v41_rom.json` proposal basis at 1.2 GHz. Their exposure on the C1 critical path is assumed, as it is in the audit.
- The Part B fallback multipliers assume a demand cut maps one-for-one onto tracks at the measured density. A gate re-run at the new demand is required before adoption.
