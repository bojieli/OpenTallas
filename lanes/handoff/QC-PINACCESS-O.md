# QC-PINACCESS-O handoff (Opus successor of FABLE-FIX-QC-PINACCESS)

Updated 2026-11-16 06:4x PST.

## Done
- r281 kit_topology snapshot re-root: claude/qc-pinaccess-o-1116@79aa99dd618 MERGED (main 12264006dce). Fixes FAIL-CLASS 07f8439040.
- Class B (DRT-0073): STALE, no code/rows (predecessor RESULT 02:31).
- coll_n repeat DRT-0255 (RESULT 06:4x): NOT pin access. All 6 failures are old-tree runs. Same net net25397, same box (62.70,653.22)-(66.69,657.21) um, same 12,732 violations after iteration 0. Pin access is clean (NoAp 0). Failing pin = worker-boundary M8 pin inside SRAM g_bank[2] (dense core_pg_M4 macro PG grid). This is the C3b PG-track class. coll_n has never routed on the new tree.
- ACKed c344a406fe (SELFCONT comment path) and b2d012998c (SRC_MANIFEST v1 tree vs main). Both are fixed by the QC v2 tree marker.

## Watch / next
1. QC v2 marker (lanes/handoff/tree_switch_qwen_compute.json, TOOLS-CONVERGE). Then coll_n + sle_sc_v1__cl115da35f/__cl7479a5ec + slw_su_l1__cla2a78701/__clcc9d0155 relaunch on v2 (KIT-OPS-5).
2. Proof routes: 5_2_route.log in the kit gen dirs (s29q103S4Q6D/items/<i>/... or ot-jobs/<i>-route-*/work/run/logs/asap7/dp_<i>/base/). A class-A proof that routes with no DRT-0255 -> post "RESULT PASS proof:DRT0255 ..." so HOLDGEN-1115 releases the hold records.
3. If coll_n fails again at net25397/box on v2: keep the route-input DB and run a PG-over-SRAM A/B (core_pg_M4 connect density / M5 strap pitch over macros).
4. Class-B real-route proofs: epyc2 /srv/opentallas-scratch2/claude/ot-jobs/{cbn_q00__cld7bf7197,cbn_q01__clab6e67f2,cbn_q01__cldd6ea846,cbn_q11__cl49ae4555,cbx_q10__cl94a12200_h}-route-dear-crayfish-*/work. In 5_1_grt at 06:35. Look for DRT-0073 (class B) and DRT-0255 (old tree, class A expected).
