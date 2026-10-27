# R17 physical clock build (launched 2026-10-27 01:40 PDT)
Data: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg/build. Unit oth-ubuntu-1796220-1793090377 (ot-run --mem 120 --hosts epyc2, hub log intel2:~/r17_build.otrun.log).
Steps: (1) die_trial kit on plan_d43 (plan dir has cores/ copied from infra-first-qc-r9-1026/plan) with --island-sites
r17_island_sites.json (8064 hosted d43b cells, ot_clock_sites/1), --island-margin-um 1.65 (max pin-stack riser 1.375;
2.6 put 24 windows on su_c prog cores, 1.65 puts 0); 959 type windows, 8064/8064 instance windows used.
(2) die_infra clockkit; (3) die_clock_mesh build --explicit-cells out/d43b/spec_exact.json --ndr 16w (8330 cells,
0 overlaps, 0 keep-out); (4) combo --routed-clock (4646 clock nets, shields VSS tied 23132/23132, 0 PG shorts);
(5) clock_routed route --rcx-rules rcx/asap7_rcx_ndr016.rules; chain.sh = run_route.sh (GRT -> RCX -> DRC 20857 boxes
+ STA TT/FF native/rcx) -> clock_routed report -> drccls.
Collect: grep R17_BUILD_DONE /srv/opentallas-scratch2/claude/qc-mesh-r17/pkg/build/../build_chain (ot-run stdout in intel2:~/r17_build.otrun.log); tree/combo_TT.log (GRT
overflow), tree/route.log, tree/drc.log + drccls.txt, report.out, tree/tree_{TT,FF}_rcx.txt.
