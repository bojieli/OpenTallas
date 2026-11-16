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

## CLAUDE RESET — parked 2026-11-16
- No new die launch/adoption. NF14r independent Fable review is still required and root logged FOR-CLAUDE. NF15pg private pin proofs are distinct; n3_turn SIGNED and archived counts independently, spn_end still routes. Last known private published source base used for our proofs is epyc9/epyc10 /srv/opentallas-scratch2/claude/kw45/src_head_pin_ad3192c01c3_nf15_pgr1 (manifest1fff02e46f179177908574318fa9e1795f87cf27ac2185760c963faff9ebdd14, plan c89216adeac524cba32ff5f19171d84865df2dca28fe057bc9696e495553aed0, sidecar aef151594c563e98af58fd43e5d60968613ce15673c67a27bc30d93fee710127). Head_pack owns next source-pack state; we performed no marker switch.
- NF13b real STA diagnostic is complete (19 real/7 standin): three negative TT rows all standins; five FF negative rows, four standins and one real seam sp5(hd_spn_end)->sp5_xw_o_shim(hd_spn_wshim_tx)/link_i, -11.668 ps/51 of566, tap offset30.55ps. New spn_end view must recompose this seam; no extra clock/cycle waiver.
- Historical p16g cut_small DRT remains LIVE epyc2 /srv/opentallas-scratch3/claude/die-head-route-1/head/p16g/drt7_cut_small_TT, exact OpenROAD PID1024768/container dhr1-drt7-cut_small-p16g. At reset:35h12 total,CPU1081%,23.1GB RSS; iteration3 40%/10290 violations. Prior NOPROG was false. Preserve; no restarting old rp21z16/full-die jobs.
- Type continuation/review details: FABLE-FIX-HEAD-TIMING.md (he12 failedGRT13, missing M8 production builder, NO he12r); HEAD-SERDES-O.md (sd8r TT repair still live, spn_end live, uncommitted PMA realized-source hook); HEAD-TYPES-O.md (hw4 live automatic signoff and four-net A/B). Source DOREG r31467db0dbd is +1 recovered-clock cycle vs DKREG, +2 vs original decoder, already exact/gated/merged; no new latency cycle was introduced by these placement variants.

## FABLE-DIE-HEAD 11-16 13:45 PST (after r342 ADOPT-WITH-SPLIT)
Lineage (MEASURED, semantic plan diffs): NF13b d43c54ae -> NF14r f5fb75d2 (+ sideband hd_lep0N/hd_ctl, reserved sites 5 types)
-> NF15pg bfda8330 (+ pg_pin_rule n3_turn/spn_end) = in-tree NF15 4dfbf941 (nf15 tree) = c89216ad (nf15_pgr1 tree), path-only diffs
-> NF15a 88f7ab5a (epyc7 fable-die-head/prep21z20NF15a/prep): hd_lep0N sideband rows rebuilt (tree register at the lepk_o0 pin), hd_lep0N + hd_mesh fine reserved rects.
NF14 full 40e5a7f6 is WITHDRAWN. nf15_pinfix cfa84b99 (epyc2, FABLE-FIX-HEAD-TIMING) = c89216 + 3 hd_host_e pin x edits, not in any composed plan: next delta.
- NF15a gates (tools overlay nf15_root2, run_gate_nf15a.sh, nf15a_gate/): G0 1 standing error, bind PASS, cohort 26/26, LATCHECK 329/329. Only ot_s81hd_lep0N.sv differs from NF15pg (288 lines).
- hd_tile off-count proof plan: prep21z20NF15t_tileproof/prep sha a107f4b1 = NF15a + hd_tile 753 fine rects. NOT a plan of record. Build not launched by me.
- Frozen die clock: prep21z20NF15a/die_clock (stamped_fdh_st.json 7f09fd2e, fdh_st.yaml 05927c6d, feed_hk6 f17e805c, regions_hp1 e8c6b46f); la300 + --tree-json.
- OPEN: count-aligned bind sim on the stamped clock with the NF13b FREG ports (30 freg): 367 window violations / 2,000 chips, high-guard margin -60.3 ps at coll_ES1_d__1 (hd_st_turn d_i); 0 violations (+85.9) on the 18-freg plan copy. Runs base/head/fdh_st13 (NF13b) and fdh_nf14. Cause not established (my freg loop vs real).
- Real-view die STA (19 real types, epyc2 scratch3/fable-die-head/fdh_st/real_sta): one real-to-real FF seam hold -11.67 ps, sp5 -> sp5_xw_o_shim link_i, 51 endpoints (Codex read).
- Branch claude/fable-die-head-1116 head fe694c9f7f7 (gate ~/tmp/fdh/gate5.log on intel2).
