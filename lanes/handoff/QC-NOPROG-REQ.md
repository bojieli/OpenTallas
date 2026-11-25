# QC-NOPROG-REQ handoff (2026-11-24 19:05 PST)
Job: re-enqueue the 9 QC V4 kits that NOPROG stopped at pregrt_ff_hold with TNS 0.
Result: none re-enqueued. All 9 items have a live C1h QC-ALLFIX private kit (posted 19:04).
Watching 5 kits not yet past GRT (NOPROG-KEEP rows 794195d8be2): QC-ALLFIX/slw_hc1__cl3449ea95_1124053803,
slw_hc1__cl68f9248e__cl144ee7b3_1124054224, sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304_1124081928,
wave items/sle_st_b_v1__pvc5a85fd4__pv38472fb8/attempt_3, items/slw_st_b_v1__cl6357f1cc__pv6ace3e48/attempt_3.
If one is stopped with TNS 0: release it with a dies.qwen_compute.retry item@N row (kit_wave_edit), or tell QC-ALLFIX for a private kit; then tell NOPROG-TNS0.
Remove the KEEP rows once the NOPROG-TNS0 fix lands.
