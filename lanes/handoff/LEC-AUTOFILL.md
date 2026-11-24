# LEC-AUTOFILL handoff (split from RELEC-1122, 11-23 19:2x PST)
Job: lec.py LEC-FILL-AUTO (fill_proposals/auto_fill, OT_LEC_AUTO_FILL default on; hints proved via apply_hints, never waived).
- Code: epyc9 /srv/opentallas-scratch2/claude/LEC-AUTOFILL/clone branch lec-autofill commit 452278b7fb (on main 3e1a2180; lec.py sha1 1daedf4b = RELEC m6). Full test_lec passes on epyc9 (serial, pytest in ~/.local). NOT pushed yet (waits rxsb verdict). Same patch uncommitted in epyc11 LEC-AUTOFILL/clone (used by the sweep).
- Push from epyc9 clone (pytest exists there; epyc11 has no pytest).
- rxsb auto run (adopted): epyc9 RELEC-1122/ml/rxsb_autofill unit oth-ubuntu-1351631-1795490287; before 755 (hand hints 729).
  EQ -> ot-push-main, post sha to S81-KVLEAF-T2-ARCH-R2 (ikw rerun). Else trace m_l.s1_rows, a_sp.
- Sweep on epyc11: kits copied to LEC-AUTOFILL/k/<tag> (netlist sha checked), runner LEC-AUTOFILL/afrun.sh, outputs r/<tag>, results LEC-AUTOFILL/runs.log.
  Before: hd_ctl 727 NOT-EQ; hd_ctl_counted 101 UNPROVEN (m2 lec + fsm hints; rerun with same hints); hd_mesh 9377+2128 undecided; hc3_cld86 KEEP FAIL 68; hc3_clccfc KEEP FAIL 85; t40 c01b49be73a8 UNPROVEN 4943; coll_s 20+1. col774 skipped (REAL).
