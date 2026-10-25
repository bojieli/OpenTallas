Engine curcap correspondence repair

The fixed dsdv_eng_rr_e engine's earlier LEC reports 1193 differences; 539 are the curcap bank.
Its gate netlist chose different interchangeable counter/reset copies than the independent RTL frontend.
A register-by-register cut leaves those copies independent and reports false differences.

Propose same-name generated-register cohorts on both RTL and netlist using their external-input support.
The normal simultaneous inductive SAT proof accepts or drops every proposed relation on BOTH designs.
No proof checks, corners, input data identities or RTL-X policy change.

PASS on the exact production engine AIGs: all 539 curcap bits plus the complete retained hypothesis set,
10407/10407 points proved,0 differences,12.85 s (intel1 ot-run unit oth-ubuntu-1311653-1792922616 was an earlier
structural trial; final both-side proof unit is recorded in the lane log and scratch curcap-cone-both.log).
Pure tests10 PASS, including distinct-PI false-pair prevention and a corrupted-gate control.
Csa31 pre/fix controls PASS: pre y[24..30] still fails7 points, fix109/109 proved
(intel1 unit oth-ubuntu-1378150-1792922951).

This proves the dominant failure class is correspondence, not a curcap hardware bug. Full engine equivalence
remains open: the earlier feedback-only full CLI is still running on epyc2; inactive roff[ej] at ej==CPR has an
out-of-range-X mapping issue, and FSM binary3/onehot6 correspondence is unresolved.
The rejected constant-X discovery experiment is retained in ../feedback and is not part of the change.

Replay: python3 results/lec_1025/replica/prove_curcap.py SNAPSHOT NEW_OUTPUT.
SNAPSHOT needs gold/gate.aig,map and the original hyp.json, held at
intel1:/srv/opentallas-scratch2/claude/codex-lec-1025/engfix (copied from epyc2 lec/eng/lec_engfix).
