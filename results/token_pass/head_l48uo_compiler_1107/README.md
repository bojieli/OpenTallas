# HEAD compiler witness on l48uo (DIE-HEAD-82, 2026-11-07)

`tools/s81_dv/layer_prog/head_root_boot.py` now pins plan f140216c (l48uo) per COORD 13:14. Sidecar
90d006, START tree 255b2b4e, START SV e9ed25cd and root88_report are the same as l48un. boot88_account
differs only in its plan_event field. Boot bounds unchanged: settle 88, root START 110, part START 382,
ready-or-fault 5861. Status stays SOURCE_WITNESS_ONLY: no physical START, HOST, PMA or mission date, no token.

Controls in qualification.json: missing witness, 10-30 plan selected, 10-30 bundle, caller START date,
sidecar without n4, stale settle 74. Also run once with the l48un bundle as OLD_BUNDLE: rejected,
manifest differs. Rerun of head_l48un_compiler_1107/qualify*.py now fails on purpose against these pins;
its records stay as evidence.

Schedule: plan alone 336, with sidecar 336, delta 0 (l48un plan alone was 332). Spine 174, gather m0S_rx 81.

Rebuild: make_bundle.py REPO BUNDLE; qualify.py REPO BUNDLE OLD_10_30_BUNDLE OUT; qualify_pipeline.py REPO BUNDLE RUN OUT.json.
