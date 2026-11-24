# QC-COLLS-LEC handoff (child of QC-ALLFIX, started 2026-11-24 13:2x PST)

Job: coll_s attempt_8 LEC NOT EQ 20+1 (g_face_4 u_ctl) -> root cause, fix, re-sign with LEC, coll_* census.

## Root cause (13:32 post, hub cb86662)
- (b) ruled out: 19/19 kit rtl shas (E10 RELEC-R2/k/coll_a/rtl) == attempt_8 bind closure (E9 .../coll_s/attempt_8/rtl/closure).
- (a)+(c): face epoch tied 8'h01, so u_ctl re[0] == e1[0] (same reset 0, same hold on epoch_begin, same D);
  yosys merged re[0] into e1[0] in BOTH faces (gate has no re[]). renamed() re-keys gate e1/e2/e3[0] as #t.
  lec.py trace_proposals walks gold-only regs in name order and takes the nearest free gate flop: gold face_3 re[0]
  (sorts before face_4) took gate face_4 e1#t[0] (R1 hyp.json), so gold face_4 e1/e2/e3/re[0] stayed free ->
  epoch_abort, fault_cause[1], rx_v differ. Design is fine; LEC correspondence gap.
- Fix (flow, lec.py only): LEC-TRACE-NEAREST: per trace class, a gate flop is reserved for the nearest-named
  eligible gold-only reg. Clone epyc10 /srv/opentallas-scratch2/claude/QC-COLLS-LEC/clone (base main dce92f0c92a),
  +test test_trace_proposals_reserve_gate_flop_for_nearest_name (old lec.py fails it exactly: B.e1#t -> A.re).

## Live units (epyc10, ot-wait <unit>)
- H1 proved-hint control (old lec m=RELEC-R2/m, hints gate e1/e2/e3#t[0]=gold, gold re[0]=e1[0]):
  oth-ubuntu-3159172-1795555606, dir QC-COLLS-LEC/r/H1_scope_pair
- H2 patched lec.py (m2 sha 62f61ffca2f3), no hints: oth-ubuntu-3263329-1795555878, dir QC-COLLS-LEC/r/H2_nearest

## Next
1. H2 EQ -> ot-push-main the lec.py fix; post FIX.
2. Re-sign vehicle: QC-ALLFIX private coll_s (cH8 R6V4) already routed, in post-GRT chain (eco i1 13:19);
   NO duplicate P&R (no RTL/plan change needed). When its sign-off lands, run fixed lec.py on its 6_final.v.
   spec intel2 hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_s_1124052534; work epyc8
   kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/coll_s_1124052522
3. Census (find lec.json *coll*, mtime<10d; E10/E2/intel1/intel2 done): coll_s 6x NOT EQ (re0 class);
   coll_core 2 faces SAFE=0 = same latent risk (opus-fix-qc-coll-r3: 3x UNPROVEN 3 undecided u_ctl face_1, 1x EQ);
   coll_n 1 face EQ (no cross-face pairing); coll_ft*, ftc, ftm, ftn, ucie: no face, EQ / N/A.
