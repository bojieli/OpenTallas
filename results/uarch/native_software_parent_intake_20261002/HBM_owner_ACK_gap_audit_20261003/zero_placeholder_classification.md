# HBM comparator zero placeholders: classification and consumer trace

Main `7baca4be1`, read-only. The full evidence (file:line, consumer chains, magnitudes) is in `zero_placeholder_classification.json`.

## Bottom line
- **None of the 10 flagged zeros reaches a headline or gate.** Every producing record carries `whole_token_latency=None` / `hardware_admitted=False`. Each key is read only by sibling h3_/h4_ records, tests, and a pointer in `docs/CURRENT_WORK_HANDOFF_2026_10_03.md`. None is read by `uarch_model.py`, `current_final_number_readiness.py`, `results/uarch/hbm_gpu.json`, `qwen3_budget.json`, or the EVIDENCE_LEDGER/PROGRAM_STATUS/CHECKLIST/Atlas Table 5-2 figures.
- **The real implicit credit is an omission.** The published HBM token (`uarch_model.py:1416-1442` Qwen, `:1192-1228` V4.1, giving `hbm_gpu.json`) has no owner/ACK/visibility/reverse/CDC/stall term at all.
- **Sensitivity (computed from the model, read-only):**
  - Qwen HBM is stream-bound: +50 cycles on each of 181 boundaries changes the rate by 0.004%.
  - DS HBM is a serial chain with 329 boundaries at 1.0339 GHz: each cycle per boundary costs 0.089% of rate, so the 1% gate is crossed at about 11.3 cycles.
  - The ROM headlines do not read any of these records.
- **Gates:** all 24 cells (4 targets × G0–G5) are already blocked and no certificates exist, so no gate flips today. These terms will block future G0/G2/G4 HBM certificates.

## Classification
| id | zero | class | impact if priced (source floor) |
|---|---|---|---|
| Z1 | PC service write completion has no ready | NONADOPTED | 0 cyc when ready; stall unbounded (no source); ~0.015 mm² capture regs |
| Z2 | r14 read credit, no identity match | NONADOPTED (recorded blocker R14_READER_CREDIT_VALIDATION_OPEN; ROM-KV path, rejected) | 0 edges if same-cycle compare; 12 edges of credit lifetime if via tag lookup |
| Z3 | bulk-copy response, no ready/tag check | IMPLICIT, justified (slot reserved at issue, `bulk_copy.sv:67,135`) | 0 cyc; identity check only |
| Z4 | RF_both_copy_write=0 | UNKNOWN_BUT_ZERO ("reused", unverified; price() not run) | 576–1,152 edges ≤0.085% Qwen HBM |
| Z5 | grant ledger cost_addition/additional_cost=0 | NONADOPTED (inventory; unknown≠0 enforced `:557-559`) | not a cost |
| Z6 | structural_frontier retire 0 | NONADOPTED (scheduler refuses: 21 costs missing) | CDC ≈3 dest edges/crossing (`r14_fifo2.sv`, preflight `:69`) → DS −0.27%/crossing |
| Z7 | new_RF_I64_RMW_C0_provider_costs=0 | NONADOPTED | not a cost; floors at `production_owner.py:415` |
| Z8 | RMW/C0 incremental charges 0, 1-edge merge | NONADOPTED (FAIL status) | 3 edges/rank, negligible |
| Z9 | C0 stalls default 0 | UNKNOWN_BUT_ZERO (`time+=3+0`) | unbounded; DS 0.089%/cyc/boundary |
| Z10 | stall_bound=1 example | NONADOPTED ("example only") | L2 no-stall floor 30 ticks → DS −2.6% if ever on chain |

Not found by the prior audit:
- **M1 (IMPLICIT):** the headline omits the service terms (above).
- **M2 (IMPLICIT):** `sm_area`/`die_fit` has no register-file macros, about +20.9 mm²/die. The die still fits.
- **M3, M5, M6 (UNKNOWN_BUT_ZERO):** native-calendar `C0/I64_RMW_additional_ticks=0` with RF None; DIV `compose_service` waits default to 0; `SerializedOwner` stalls default to 0.
- **M4 (NONADOPTED):** further no-double-charge zeros.

Side notes:
- MICROARCH still states V4.1 HBM 2,920 tok/s; the model and `hbm_gpu.json` give 2,801.8.
- The prior audit's "two timed mirror ACKs" defect is only half right: `SerializedOwner.ack` charges 2+stalls once.
- `ot_hdc_qwen_pc_service` is the HDC/ROM-die KV service, reused by installed_r2.

## Remediation order (claim-determining first)
1. Price a per-boundary service term in `v41_hbm_chain`: mirrored ACK 2, plus visibility/reverse, plus a W11 stall bound. Then re-state the DS HBM rate.
2. Produce a W11 source-bound stall/credit-return bound to replace Z9/Z10/Z1.
3. Add RF macros to the HBM die area and refresh the MICROARCH V4.1 HBM figure.
4. Reconcile the no-double-charge flags (Z4, Z5, Z7, Z8, M3, M4) once clocks exist (W13). The magnitude is negligible.
5. Add the identity checks Z2/Z3. They are correctness only, with no rate impact.
