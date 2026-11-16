# FABLE-DIE-HEAD handoff (11-16 08:45 PST)
Report: lanes/FABLE-DIE-HEAD.md. Lane dir epyc7 /srv/opentallas-scratch2/claude/fable-die-head (epyc9 copy older; epyc9 scratch full).
- Runs done: base/head/fdh_base (hk6 + la300), base/head/fdh_st (stamped tree); each has CHAIN.log, CA_CHAIN.log, CA4.log, ca4/out.
- Scripts: run_base.sh, run_st.sh TAG BASE, ca_chain.sh TAG, an1.py/an2.py (die numbers), sb_audit.py (sideband audit), sb_rows.py (rows).
- ot-run: launch from intel2 with --disk 5 --hosts epyc7 --dir LANE --priority die.
- Delivered rows: lanes/handoff/FABLE-DIE-HEAD-sbrows-hd_lep0N.json, -hd_ctl.json; audit FABLE-DIE-HEAD-sideband-405.tsv.
Next: (1) HEAD-100 composes NF14 (rows A-C), gen + bind + LATCHECK on the v2 tree; local_resets via head_cland_stage_delta.py.
(2) count type-frame site sets on base/gate/cfg/stamped_fdh_st.json, then island rows. (3) die STA with closed views (hold).
(4) put sb_audit.py in tools/die_plan on branch claude/fable-die-head-1116 (not started).
