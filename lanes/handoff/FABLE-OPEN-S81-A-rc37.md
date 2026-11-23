# FABLE-OPEN-S81-A rc37 worker handoff (Fable; S81 LP lep slice setup classes) - updated 11-23 11:15 PST
Deadline: ROWS-READY or REASONED to S81-J9-ASSEMBLY-R6 by 14:30 (PRE-clean 15:30, cut 18:00).
## Measured cause (census < -42 on post-hook CTS DBs; tool sta_census2.sh, sum.py in scratch)
- intel1/epyc7/epyc10 /srv/opentallas-scratch2/claude/fable-open-s81-a/rc37/cen2_{nhmus,muF2,lepwmus,muR1}/{classes.tsv,class_N.rpt,pathxy.tsv,ends.tsv}
- Data classes = one-cycle 840-1575 um W<->E traverses (clocks matched); only on types at RIP1 / ROS0; absent at RIP3+ROS3.
- Reset classes = all 60 ends are _rtap_clk_t* copies of R1 tap_reset_split, hanging unbuffered 600-1030 um from the source's driver.
- lpad_lpc -> lnl3 = Codex seat row epyc7 rc37/LEPE-LPC-D3-RANK-rc37-ops.json (PRE PASS) + branch_lpc_codex place_r2.
## Rows
- LP-PROFILE-1: epyc10 rc37/LP-PROFILE-1-rc37-ops.json (3 define ops on Wave A 4662b734580b: lepe_mu_LP t2, lepw_mu_LP t2, lepw_mus_LP t2 -> RIP3+ROS3). K: ri +2, inputs +3 per type, not priced by bind (x13 LK1).
- RSPLIT-REACH (flow): intel1 clone_rc37 branch claude/fable-open-s81-a-rc37-rsplit-maxum commit c11817b827 (opt-in clock.tap_reset_split_max_um). NOT pushed; push only after the probe shows the Tcl runs.
## Live units (11:15)
- PRE: epyc10 rc37/pre_lp_profile.otrun.log (queued on load cap) -> pre_lp_profile1.log/json
- lepw probes (goal cts, epyc7, N1 bound tree + plan epyc7 rc37/plan_rc37_n1ab.json): intel2 user units rc37-probe-mus, rc37-probe-mu; specs ~/coord/autopilot/private_specs/FABLE-OPEN-S81-A/
- lpc seat CTS: epyc7 rc37/branch_lpc_codex/cts_r2.otrun.log (Codex place_r2 kit continued to cts)
- RSPLIT probe: epyc7 rc37/rsplit_probe.otrun.log (F2 kit copy, MAX_UM 300, cts from 3_place)
## Next
Read each probe with sta_census2.sh on its 4_1_cts.odb; post ROWS-READY (PRE + probe) or REASONED; push c11817b827 via ot-push-main after the RSPLIT probe prints far_skipped.
## Update 11-23 15:55 PST: REASONED packet posted (hub 08d58c7)
- Row ready: lanes/handoff/FABLE-OPEN-S81-A-rc37-LP-PROFILE-1b-ops.json 631181597c49 (lepe_mu_LP t2 RIP3+ROS3 only). PRE PASS on 3-op superset; no bind/LATCHECK.
- lepw ops withdrawn: probes epyc7 rc37/cen3_pA_lepwmus (-677.2, 1200 ends), cen3_pB_lepwmu (-265.2, 473 ends).
- RSPLIT-REACH c11817b827 (intel1 clone_rc37) NOT pushed: partial (cen3_pC_rsplit 31 ends, root_r->group_r -179.3).
- Codex lpc seating as built: reject (cen3_pD_lpc root_r->group_r -1121.8).
- Open: RX registered read at the bank (lepw rid/ml_wd), ros_r rank seats for lepw, N2 TXQ3 measured on a tree whose portfix178 lep.sv has the selector, reset copy class with the RST-COTAP owner.
- No live units.
