# S81 existing-results pickup, 2026-10-19 13:36 PDT

Read-only collection; no simulation, gate, restart, kill, RTL, compiler or golden changes.

REFILL-1225 S81REG now has all nine terminal LEG rc=0 receipts. The final original unit oth-ubuntu-4120668-1792438136 ended 13:24 with **SEQHOST_MU_GATE PASS**, after its own two positives, five faults, three causal mutants, lint and nested MU_HOST_GATE/MU_HWIN_GATE. This is the full-script verdict, not a nested-only inference. The HWIN eighth unit4120652 ended12:57 PASS. Source is staged3158fce1e+1e057b7bf, CLOSED HSLOT blob8e9b03d6 and HWIN519dab74. `seqhost_native_receipt.txt` binds actual staged source/runner SHA256 and Verilator5.050. `reg/` preserves all nine original wrapper logs and exact drivers. Original mutation FAIL lines remain intact.

Landed SVC source5d9c4ecaa has all16 base cases PASS: full1m, short300, skew1m, tail46, two seeds, ST0/PE0 and ST2/PE1. Every reported SVCRS field equals its historical flop baseline by case, including exact go/first/last/end/cycles and all numeric/error counters. Prefixes name different build objects, so raw complete lines differ; `terminal_summary.json` records both facts. Four mut6 cases reject with2048 PV errors; short300 additionally1472 score/665 SE errors. Units3824951/3825262 ended12:49 and3824949 ended12:44, all wrapperrc0. `svc/` preserves logs, baselines, driver and actual source/vector archive hashes. This collector does not flip any default.

All four physical chains are still diagnostic and live: mu2ep7 GRT10/30 PID2329250, mu1ep8 GRT18/30 PID724195, MABep8 GRT14/30 PID1174997; mu3cep7 PID3654923 remains repeaters pre-stage. No terminal GRT/TT/FF/clock-pair receipt exists. Old pre-GRT slew/cap failures and455um reach audit do not qualify405um. All three SVC diagnostic gate Yosys processes remain FSM_DETECT (~31–32GB), exact paths/PIDs in live receipts. No physical/native/PG/parent qualification follows from the behavioral table.

Old HOP4150465/6 and chain449774 remain live. Both original binaries compiled successfully and actual traces grow through13:36; endpoint checks await terminal simulations. No checker PASS is inferred from buildrc0.

The final ceaed strict bind FAIL1182 unread/open28 and original strict token SU1324/2628 failures remain unchanged. These component regressions do not qualify full SU/MU token operation. Next: main merger may import artifact-only receipts; existing gate/HOP/die owners collect terminal results without duplicates, while structural source/model owners close native/contact/reset/calendar gaps before adoption.
