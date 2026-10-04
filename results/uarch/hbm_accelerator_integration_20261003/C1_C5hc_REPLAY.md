# DS-ROM C5hc collective gate (2026-10-03): REJECT

**Verdict: REJECT C5hc. C1 (PAR2) stays the selected mapping.** This failed verdict is final and must not be overwritten.

The decision rule was committed in `decision_rule.json` (bd840b303) before anything was measured. It requires both of these to adopt C5hc:

- re-priced C5hc AR at 1M is at least 5% above re-priced C1;
- re-priced C5hc AR at 200K is at least 1% above re-priced C1.

Every exactness check passed. The 1M rate condition did not.

| AR tok/s | model (abd77c4e1) 1M | measured 1M | model 200K | measured 200K |
|---|---:|---:|---:|---:|
| C1 PAR2 (4 owner dies, 4 packages) | 2347.4 | 2356.8 | 2445.0 | 2455.3 |
| C5hc TP-8 (4 packages x 2 dies) | 2606.6 | 2462.4 | 2677.1 | 2525.3 |
| C5hc vs C1 | +11.0% | **+4.48%** (needs 5%) | +9.5% | +2.85% (needs 1%) |

MTP at 1M re-prices to 3203.4 for C1 and 3485.7 for C5hc. MTP payloads are now charged at P = 6. The W15 term in the base graph does not scale MTP collective bytes with P.

Sensitivity at the model's fc4 link bandwidth gives +4.64% at 1M and +3.02% at 200K, which is also REJECT.

## What was measured

Collectives were measured under Verilator 5.050 on ot-agidock128.

- **Bench:** `rtl/test/tb_dsrom_hcoll.sv`.
- **Engine:** `rtl/rom/collectives/ot_rom_hcoll_die.sv`.
- **Link layer:** the unchanged W15 link layer (`ot_w15_link_tx/rx`, `ot_link_chan_model`, CDC FIFOs, CRC, FEC encode/decode stages).
- **Clocks:** every die has its own core clock (0.834 ns), plus its own UCIe and SerDes link clocks.
- **Wire stages:** 34 VM-to-UCIe-PHY and 45 VM-to-SerDes each side.
- **Flow control:** credits and backpressure throughout.
- **Release:** deterministic, calibrated as W15 does it: the worst arrival over 10 seeds plus 2 channel corners, plus 3 guard cycles.
- **Measurement runs:** 8 seeds plus 2 corners.
- **Payloads:** every C5hc and C1 payload at P = 1 and P = 6. Sizes over 2,048 words per rank use the linear fit.

**C5hc topology.** Each die links to its partner over UCIe (4 VCs) and to its counterpart in each of the 3 other packages over a 9-lane 112G light-FEC link (the fc4 package link split into 2 planes).

- All-gather: board first, then a UCIe relay.
- All-reduce: an exact hierarchical tree, `s_p = r_2p + r_2p+1` over UCIe, then `((s0+s1)+(s2+s3))` on every die after the board exchange.

**C1 topology.** The owner dies are linked by 18-lane board links.

Fits are in cycles at 0.834 ns, from issue to the last VM commit on the slowest die. Every point fits its line with zero residual.

| config | gather fixed + per word (per rank) | reduce fixed + per word |
|---|---|---|
| c5hc_phys | 352 + 2.0 | 374 + 1.0 |
| c1_phys | 252 + 1.0 | 265 + 1.0 |

C5hc pays about 100 more fixed cycles (+83 ns) than C1: the UCIe relay or level-1 hop (82–86 cycles hub-to-hub).

The model had priced that in-package step at about 10 ns. It counted UCIe's 10 ns hop without its 2 x 34 wire stages.

The C5hc MoE combine is two all-gathers, and each pays the fixed part:

| per-call depth (ns) | model | measured |
|---|---:|---:|
| C5hc MoE combine | 561 | 905 |
| C5hc a_allgather | 233 | 321 |

**Result:** on the 1M AR path, C5hc's collectives rose from 72.3 to 93.9 µs, while C1's fell from 68.5 to 66.7 µs.

## Exactness

All checks pass.

- **wo_b golden check.** A full-shape wo_b (5120 x 8192 FP8, UE8M0 scales) is used. The tree of the 8 rank partials, each an aligned 4-chunk subtree, equals `hdc_golden_v41.csum` bit-for-bit. `to_bf16` of that sum equals `linear_q`. The same holds for 4 ranks (C1).
- **RTL commits.** Every committed RTL word was checked against the golden as it was written: 0 mismatches and 0 faults over all 6 configs.
- **Timing determinism.** Timing is identical across seeds and corners for `_phys` and `_modelbw`.
- **Backpressure stress.** The `_bp` configs (64-word FIFOs, VM write port stalled 30% of cycles) are bit-exact with no overflow. Their timing varies with the stall pattern, as it should.

## Replay

```
python3 tools/dsrom_c5hc_collective_gate.py fixture          # golden checks + vectors (scratch)
python3 tools/dsrom_c5hc_collective_gate.py measure --jobs 6 # ~1 h per C5hc config on 128 cores; writes measurements.json
python3 tools/dsrom_c5hc_collective_gate.py reprice --verify # re-derives verdict.json from measurements.json (~20 min)
python3 -m pytest -q tests/test_dsrom_c5hc_collective_gate.py tests/test_dsrom_parallelism.py
```

The model hook is `cfg["measured_coll"]` in `tools/uarch_model_parallelism.py`. It is opt-in. Without it, `tests/test_dsrom_parallelism.py` reproduces the abd77c4e1 record unchanged.

The hook keeps every non-link term of the graph's collective (VM-H write, CDC: 14.4–18.6 ns). It replaces the W15 TP-4 fit, the SS wire term and any PAR2 fabric delta with the measured latency.

## What would change the answer (not done: the rule says stop)

- **The gap is the in-package hop on every collective.** Two options might win C5hc back, but each needs its own model entry and gate:
  - a die-direct board mesh (6 board sublinks per die, no relay) for the small gathers;
  - one fused MoE gather instead of two.
- **C1's own collectives re-price at +0.4%.** The W15 TP-4 fit was a fair proxy for the 4-owner board group.
