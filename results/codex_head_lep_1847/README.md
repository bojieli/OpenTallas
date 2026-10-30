Actual LEP V1 geometry closure step, 2026-10-29 19:01 PDT.

The existing 777.6 x 492.48 pair trial placement failed 72 sequential reach endpoints, max518.24um. The failures were reset lr_f0/lr_f2 separation, endpoint a_in→b_pay/replay bypass separation, and ring chunks64..68 writer/control versus boundary reader separation. The candidate keeps the mapped netlist, SRAM sites, pins and clock unchanged; 0 added cycles/RTL changes. reach_milp.py iteratively adds full combinational-graph extreme-source constraints and macro disjunctions with1um clearance; face-bank cells x<12/y<12 are fixed. The graph scan re-runs after every solution to catch newly extreme sources.

Initial unconstrained LP0 reach failures but225 macro hits is retained in reach_unlegalized.json, and a greedy macro-side LP FAIL is retained in reach_candidate.json. Neither was physically routed. reach_milp.json is the legal-macro candidate, NOT a placed/signoff claim.

Personally viewed candidate.png before submitting one placement-only DPL. Candidate internal flops remain in existing SRAM channels. Review results/geom_review/codex_head_lep_1847.md.

Actual DPL unit oth-ubuntu-3562728-1793325606 completed0 on epyc2; check_placement passed, max legalizer displacement6.2um. Re-dump after.odb:27644 sequential captures,0 over405um,max403.06um; relay collapse1→0. post_dpl.json contains the actual graph/pin census. No macro/RTL/interface/cycle changes. No CTS/route/signoff submitted.

Still FAIL: single clock entry reach625.2um, k_lo_r pin-register324.4um,556 unregistered reported pins (land_slots schema compatibility separately owned by coverage). Lowfill/empty and channel-H warnings persist. These are not waived. Memory timing is not included in this r2r census (memory_reach=false), unchanged from inherited AUTO-GEOM.

Actual immutable files on epyc2:/srv/opentallas-scratch2/claude/codex-head-lep-serdes-1847/dpl/{before.odb,after.odb,after.tsv,apply.tcl,dpl.log}. Inherited sources/results untouched. First DPL launcher exit127 (OpenROAD missing PATH) preserved as dpl_launch_fail.log, corrected env source and rerun; only own analytical process was stopped to correct floating-point obstacle-boundary detection. No inherited job stopped.

Next: fix k_lo_r placement/typed interface and internal clock-entry coverage; inspect final placement and rerun full geometry before CTS. Original LEP LEC unit2876937 remains active. SerDes unit971192 still DRT at60% iter0, no signoff.json. Do not duplicate either.
