# QC-PINACCESS-O handoff (Opus successor of FABLE-FIX-QC-PINACCESS)

Updated 2026-11-16 03:2x PST.

## Scope
QC detail-route failures. Class A = DRT-0255 (~19 types, expected fixed by C3b on kw45/src_qc_pin_e594a73db756).
Class B = DRT-0073 pin access (6 types). Also owns FAIL-CLASS 07f8439040 (native clock table outside base) and e21636a9ba (slw_sc_v2).

## State
- Class B: STALE (predecessor RESULT 02:31). Pin access PASS on current S4Q6D views. No code, no rows.
  Real-route proof: epyc2 /srv/opentallas-scratch2/claude/ot-jobs/{cbn_q00__cld7bf7197,cbn_q01__clab6e67f2,cbn_q01__cldd6ea846,cbn_q11__cl49ae4555,cbx_q10__cl94a12200_h}-route-dear-crayfish-*/work/run_route.log (in 4_1_cts at 02:41). Check for DRT-0073 / DRT-0255 / final violation count in work/run/logs/asap7/dp_<item>/base/5_2_route.log.
- Class A proof kits (coll_n, sle_sc_v1__cl115da35f/__cl7479a5ec, slw_su_l1__cla2a78701/__clcc9d0155) are BLOCKED at kit_topology by 07f8439040.
  coll_n old baseline: a19 12,732 DRT violations then DRT-0255.
- 07f8439040 cause: zz_manifest_iso_s29q103S4Q6DBQ.json clock_landing_table is an absolute live path; with kit_snap the base resolves under kit-store/snaps/<sha>/root -> kit_topology.py:47 raises. All 109 iso manifests are absolute.
  Fix (a) code: kit_topology.native_contract re-roots an absolute table under the snapshot root (branch claude/qc-pinaccess-o-1116, epyc2 /srv/opentallas-scratch2/claude/qc-pinaccess-o/repo). Needs QC tree re-pin.
  Fix (b) fast: KIT-OPS-5 kit_snap off for qwen_compute.
- e21636a9ba slw_sc_v2: stale 11-12 S25-plan attempt interrupted by signal 15; needs a fresh launch.

## Next
1. DONE: claude/qc-pinaccess-o-1116@79aa99dd618 GATE pass=9/9 GREEN, READY posted. Follow: merge, then TOOLS-CONVERGE QC tree re-pin (or KIT-OPS-5 kit_snap off) and relaunch of the 10 + proof kits.
2. When a class-A proof routes with no DRT-0255: post RESULT PASS naming proof:DRT0255 so HOLDGEN-1115 releases the hold records.
