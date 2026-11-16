# FABLE-DIE-HEAD handoff (11-16 08:45 PST)
Report: lanes/FABLE-DIE-HEAD.md. Lane dir epyc7 /srv/opentallas-scratch2/claude/fable-die-head (epyc9 copy older; epyc9 scratch full).
- Runs done: base/head/fdh_base (hk6 + la300), base/head/fdh_st (stamped tree); each has CHAIN.log, CA_CHAIN.log, CA4.log, ca4/out.
- Scripts: run_base.sh, run_st.sh TAG BASE, ca_chain.sh TAG, an1.py/an2.py (die numbers), sb_audit.py (sideband audit), sb_rows.py (rows).
- ot-run: launch from intel2 with --disk 5 --hosts epyc7 --dir LANE --priority die.
- Delivered rows: lanes/handoff/FABLE-DIE-HEAD-sbrows-hd_lep0N.json, -hd_ctl.json; audit FABLE-DIE-HEAD-sideband-405.tsv.
Next: (1) HEAD-100 composes NF14 (rows A-C), gen + bind + LATCHECK on the v2 tree; local_resets via head_cland_stage_delta.py.
(2) count type-frame site sets on base/gate/cfg/stamped_fdh_st.json, then island rows. (3) die STA with closed views (hold).
(4) put sb_audit.py in tools/die_plan on branch claude/fable-die-head-1116 (not started).

## CODEX takeover 11-16 10:0x
- @6a4646b7e77ccb7765ba261295fe77ed72f059f7 gate collected63 files PASS+1 baseline, READY posted (schema pg_pin_rule, n3_turn/spn_end exemption removal, hd_ctl region reset rows).
- NF14 die chain CHAIN_DONE09:54 kit/GRT TT+FF PASS; declared-budget STA BLOCKED(kits), do not count it. Separate 19-real7-standin stamped NF13b STA live epyc2 scratch3/fable-die-head/fdh_st/real_sta. TT nonlanded abs(tap offset)<150 negatives only3, all standin host_e/w/serdes; FF pending.
- NF15pg COMPOSED_NOT_GATED epyc7 fable-die-head/prep21z20NF15pg/prep, plan sha bfda8330cbc2ca86fd90f17bfc72192eba242a0735430919df231f52b5f9e5b6; NF14r + pg_pin_rule=true n3_turn/spn_end +0cycles. Needs HEAD tree delta then republish/bind/LATCHECK/G0. NF14/r itself still awaits independent FABLE review r199/r308.

## CODEX NF15pg gate 11-16 10:1x
NF15pg at epyc7 fable-die-head/prep21z20NF15pg/prep is GATED, pending independent NF14/r review and coordinator adopt. Plan bfda8330cbc2ca86fd90f17bfc72192eba242a0735430919df231f52b5f9e5b6; only pg_pin_rule+note on hd_st_n3_turn and hd_spn_end differs from NF14r. Republish PASS, both wrappers byte-identical to NF14r. epyc7 fable-die-head/nf15_gate4: bind PASS (nested7157,0errors), cohort26/26, LATCHECK329/329 delta{} fixed_in_core12. G0 source nf15_gate3/g0: exact same single reset-wavefront native-release pending ERROR as NF14r, no new ERROR,233advisory warnings. Private nf15_root2 tools+r315 used, published tree intact. Initial setup/cwd/out-path failures preserved in nf15_gate{,2,3} and intel2 nf15pg-gate*.log; final client388470 exit0. No route or adoption.
