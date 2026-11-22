# CLASS-SWEEP-R1 handoff (Opus, 11-22 02:2x PST)
Task (COORD 11-22): sweep A (HB4 over-insertion on core pins), B (landing band overlap / capacity 1.25x), C (reset copy on another clock tap, >100 ps) on S81 J7/J8, QC V3, KV D27d3/D28, HEAD r17b/r18; hand rows to die plan owners.
Result table: lanes/CLASS-SWEEP-1122.tsv (die, class, type, evidence, proposed row). Status: DONE, rows handed over (posts 02:2x).
Work dirs: epyc10 + epyc8 /srv/opentallas-scratch2/claude/class-sweep-r1/{s,c,rows}; lane clone epyc8 class-sweep-r1/repo (tools cone, unused for commits).
Scripts: s/a_scan.py (plan HB4 pads), s/libwin.py (lib setup/hold per pin), s/b_scan.py RT PLAN DIE OUT [band_fill] (band overlap + capacity),
  s/rows_resite.py RT PLAN_IN PLAN_OUT SPEC [SIDECAR] (generic band/stage-band re-site row), c/ (class C odb scan, extended rst_cotap_scan + OT_TAP_INSERTION).
Rows (all PRE PASS with --baseline-plan, rt 6d2e187f0d65 which contains fda4eaad0e):
- KV D28: epyc8 class-sweep-r1/rows/ROWS_CLASS-SWEEP-R1.py (sha 7d250c7916c3, B 13 bands; needs rows_resite.py 7f37536085ea next to it) + ROWS_CLASS-SWEEP-R1-C.py (48f7cf2b9e8f, opt-in tap_reset_split 9 types).
- QC V4: lanes/handoff/CLASS-SWEEP-R1-QC-V4-rows.json (A module hb4 tap[0] 3->1; B slw_sc_v1 x2 monitor_0). V3p7d5 itself FAILS plan_gate_pre FIXEDCYC (6 coll_core lanes) on rt 6d2e - inherited, told QC-PLAN-R13.
- S81 J8: lanes/handoff/CLASS-SWEEP-R1-S81-J8-C-rows.json (14 types tap_reset_split); B svc ff bands = list only (no clear rect).
- HEAD r18: lanes/handoff/CLASS-SWEEP-R1-HEAD-r18-B-rows.json (11 stage-band moves on e6 split) + -C-rows.json (hd_host_w).
Caveats: B need models (KV ring 7.83w+179 fit to 2 place reserves; S81 ca_reserve40x1.05; x1.91 on HEAD stage groups is KV-calibrated); C insertion = per-tap OT_TAP_INSERTION average; 1-sink u_rrl relays are not split by the tool.
