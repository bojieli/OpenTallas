# ASTK / ECTLK variants (ELEM-QK fork ELEMQK-ASTK, 2026-10-24) — all NOT CLOSED (no route reached)
Kits: KVG3-CORES astk/ectlk kits via Codex recovery copies; SDC/clock/pins unchanged; tools/elem_qk/astk_variants.sh,
tools/elem_qk/run_variant.sh (run_kit_kv.sh then main signoff.py tt,ff).
| core | variant | result |
|---|---|---|
| ASTK EN/ES/WN/WS | hm55 (hold margin 55) | CTS FAIL RSZ-0060 max hold-buffer count (epyc3) |
| ASTK EN/ES/WN/WS | r4h (replica RTL + hm55) | CTS FAIL RSZ-0060 |
| ASTK EN/WN/WS | r4hs (+setup 20, density .72, TD GPL) | CTS FAIL RSZ-0060; ES r4hs not run (queued log empty) |
| ECTLK | e1 -no_insertion_delay | CTS FAIL RSZ-0060, 11366 hold buffers (intel2) |
| ECTLK | e2 e1 + buffer distance/clusters | CTS FAIL RSZ-0060, 11362 hold buffers |
| ECTLK | e3 e1 + BUFx24 root/tree + balance_levels | CTS FAIL RSZ-0060 |
Finding: a flat 55 ps TC hold margin overruns the CTS hold-repair buffer cap on ASTK (canonical margin 15 routes but
FF hold -36..-38); ECTLK hold explosion persists with macro-latency balancing off -> the late clock is the trunk/pin
geometry (ck at the E corner of 881 um), not delay buffering. Next: ASTK FF-only post-route hold ECO (root r4b/r4d
recipe) on margin-15 routes (+ replica RTL for TT); ECTLK: measure insertion of e1 CTS tree (4_1 snapshot) and
consider a centre clock entry (plan change, OWNER?).
