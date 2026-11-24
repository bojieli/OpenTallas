# QC-RSTCNT handoff (lane started 11-24 02:0x PST by COORD)
Job: generic in-die root stable counter (QC first for C1i by 07:00; then S81 c9, HEAD next event) + compose-tail needed-hold check (report-only now, FAIL from c9).
- Tool form: reset.source.hold {stable_cycles} = ot_dp_lockq u_rst_lockq tied .locked(1'b1) after u_rst_root; shift = N+3 uniform (unique root type). Commit d9cdb9a79f (lane clone epyc2 /srv/opentallas-scratch3/claude/QC-RSTCNT/wt), push via ot-run push1.sh (log push1.log there).
- Tests: tools/die_plan/test_reset_hold.py.
- Row script: ROWS_QC-RSTCNT-HOLD.py (epyc2 + intel1 lane dirs): IN OUT [N=256]; sets hold, retap --republish-reset on root type (QC: slw_sc_v1__cl63e5a7a2, part sl_W0_sc), asserts uniform shift.
- Trial on C1g 96cce77c1e2f: intel1 /srv/opentallas-scratch2/claude/QC-RSTCNT/g/tree (fork of epyc7 QC-ALLFIX/cF/tree).
- C1h sha: asked QC-ALLFIX 02:0x (C1h verdict ETA ~05:10).
## 02:45
- main: d4a09a78ff (hold form), ffd0f832a5 (reset_hold_check.py), bf561f9534 (reset_hold_row.py). rt e348b919dd39 has the hold form.
- Trial unit oth-ubuntu-3468351-1795516380 intel1 (g/trial.ot, g/row.log, pre.log, bind.log, latcheck.json).
- S81 root type ot_s81sl_leaf__t34 (1 part, no lock) -> reset_hold_row works; HEAD not yet checked.
- After trial: release diff vs epyc7 QC-ALLFIX/cF/bind/bind_reset.json; reset_hold_check on C1g rtl + new root rtl + new bind_reset.json.
## 03:35
- C1g trial: row b992484397c0 shift [259], PRE had 76 ENTRYFOOT (inherited, also in QC-ALLFIX cH pre.log) -> trial abandoned, g/tree deleted (disk).
- C1i run: unit oth-ubuntu-226061-1795520056 intel1, script trial2.sh (h/trial2.ot), rt cbb5668a243d, base C1h 894e6f21991f. Outputs h/{row.log,pre.log,pre_base.log,bind.log,latcheck.json}.
- Leases: use --dir <subdir> (lane-root --dir lease blocks ot-delete of siblings).
- After bind: hold check = reset_hold_check on c1h full rtl? -> use QC-ALLFIX cH/bind/rtl (other types) + h/bind/rtl root type + h/bind/bind_reset.json, --plan row plan.
