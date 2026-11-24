# QC-RSTCNT handoff (lane started 11-24 02:0x PST by COORD)
Job: generic in-die root stable counter (QC first for C1i by 07:00; then S81 c9, HEAD next event) + compose-tail needed-hold check (report-only now, FAIL from c9).
- Tool form: reset.source.hold {stable_cycles} = ot_dp_lockq u_rst_lockq tied .locked(1'b1) after u_rst_root; shift = N+3 uniform (unique root type). Commit d9cdb9a79f (lane clone epyc2 /srv/opentallas-scratch3/claude/QC-RSTCNT/wt), push via ot-run push1.sh (log push1.log there).
- Tests: tools/die_plan/test_reset_hold.py.
- Row script: ROWS_QC-RSTCNT-HOLD.py (epyc2 + intel1 lane dirs): IN OUT [N=256]; sets hold, retap --republish-reset on root type (QC: slw_sc_v1__cl63e5a7a2, part sl_W0_sc), asserts uniform shift.
- Trial on C1g 96cce77c1e2f: intel1 /srv/opentallas-scratch2/claude/QC-RSTCNT/g/tree (fork of epyc7 QC-ALLFIX/cF/tree).
- C1h sha: asked QC-ALLFIX 02:0x (C1h verdict ETA ~05:10).
