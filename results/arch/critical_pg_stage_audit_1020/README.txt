Critical Qwen intermediate PG stage diagnosis, 2026-10-20 00:37 PT.
Prior read-only audits reported unbound PG on CTS/GRT checkpoints and inferred that critical submission was blocked by a modern PG protection defect. That inference was premature: these are intermediate checkpoints before the normal final global_connect, not final signoff ODBs.

Real OpenROAD read-only-mounted ODB experiments (unpinned ot-run ep9+ep5, exact scripts/logs committed) show ALL8 checkpoints have ZERO protected or fixed unbound PG terms. An in-memory canonical global_connect, using their own persisted design rules, connects every missing terminal: AFTER_GLOBAL_CONNECT unbound=0. No ODB writes are issued. Initial ep9 script accidentally placed ep5 where its ODB was absent, exited1 without mutation; corrected data-local ep9-only run exits0. Original input mounts /srv read-only for all experiments.

Counts BEFORE / AFTER: bc3 CTS5244/0 GRT6060/0; bc3c CTS6692/0 GRT7512/0; sf7w CTS15100/0 GRT18306/0; mainface CTS18380/0 GRT18380/0. Every BEFORE protected=0 fixed=0. Failure inventory is repair hold/rebuffer cells, not stranded protected clock-tree cells. Remote source inspection bc3 src hooks clock_spine/clk_net_protect/native_pg_binding all contain modern standard-bind functions.

No source fix or PG waiver is warranted by these checkpoints. Gate physical review may proceed on its existing criteria; actual full-route final ODB must still pass native terminal audit after normal final global_connect. This receipt does NOT assert final route PG closure, nor silently rewrite previous failed audit evidence. It corrects only the interpretation of intermediate checkpoint audits.

Original audit evidence /home/ubuntu/wt/codex-ctlm-coll-critical-1019/results/rtl/codex_qw_physical_pickup_1019. Exact original ODB paths are in committed read-only inspection Tcl scripts. Logs show all stages BEFORE and AFTER.
