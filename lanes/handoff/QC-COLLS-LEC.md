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

## 16:35 results
- H2 (patched, no hints) UNPROVEN 50797/50800, differs 0; H1 (old + 4 hints, all kept) UNPROVEN 76058/76061, differs 0.
  Remaining 3 undecided = face_4 u_ctl epoch_abort / fault_cause[0] / rx_v, 0 unmatched keys, solver limit (5M conf, 1800 s);
  face_3 twins proved by escalation. NOTE: H2 compare points 50800 vs 76042 (R1) / 76061 (H1): explain before counting.
- H3 = patched + OT_LEC_ESCALATE_C=50000000 OT_LEC_ESCALATE_S=10800, E10 QC-COLLS-LEC/r/H3_esc (queued on load cap; see logs/H3.client.log for unit).
- ot-push-main of clone commit cb2152fd55e launched 16:3x (result in hub post when it lands).
- FIX on main e52216b703b (ot-push-main OK). H3 unit oth-ubuntu-3820122-1795566900 (E10, r/H3_esc) running.
- H2 cp drop explained: gate_only_compare 32230 -> 162 (gate anon flops now paired); gold coverage identical (matched 40575, gold_only_compare 1001), gold_unmatched_live 4 -> 0.

## 17:40 sim witness (COORD ask 16:55 / 17:3x)
- Script epyc10 QC-COLLS-LEC/simwit3.py (per-face classes) / simwit4.py (+landing fstart/fclk). AIGs = r/H2_nearest/lec.
- SW1 1.2M, SW2 4.47M, SW3 4.47M, SW4 x2 lane-cycles: 0 mismatches over 31435 matched regs (both faces' u_ctl).
- Coverage gap: only fault_cause[3] (rv && !ev) and [4] (phy_fault) fire; ev / rx_v / crc / slot / unread / collision / cmd_ov
  never: core tokens enter via ot_dp_clk_landing_cas CDCs that port-level stimulus does not open. Next: block-level witness.
- H3 unit oth-ubuntu-3820122-1795566900 still running (r/H3_esc).

## 19:51 DONE: H3 EQUIVALENT 50800/50800 (posted hub 3c77cee)
- attempt_8 base 6_final.v sha d0b7a92bf6c9; lec.py main e52216b703b; OT_LEC_ESCALATE_C=50000000 S=10800; seed 0; no hints.
- record E10 QC-COLLS-LEC/r/H3_esc/lec/lec.json sha 9f168fc9686a. Asked COORD/RELEC-R2 to lift coll_s COUNT-REVOKED/RECHECK.
- Remaining (optional, other owners): fixed-lec on QC-ALLFIX cH8 coll_s netlist after its sign-off (needs ESCALATE 50M/10800);
  rerun coll_core UNPROVEN records (opus-fix-qc-coll-r3) with same settings.

## 11-25 00:37 PST: cH8 signed coll_s ECO LEC (QC-ALLFIX request) - DONE EQUIVALENT
- Netlist eco_20261124_211939_3874698/i1/run/results/asap7/dp_coll_s/base/6_final.v sha256 f34adcfc49853040dd579c76518de42421738f230de6775c97025183ad6d7873 (signoff.json final_netlist path; record stores no sha).
- Ran on epyc10 (moved from epyc8 queue; both epyc8 waiters cancelled, never started). Inputs copied to epyc10 QC-COLLS-LEC/r/H4_cH8eco/kit (sha re-checked).
- EQUIVALENT 52573/52573, 0 differs/undecided, no hints, 16565 s; lec.py 62f61ffca2f3, ESCALATE_C=50000000 S=10800; lec.json sha b9841468c58f. Posted 7963354.
- Open for others: coll_core = OPUS-FIX-QC-COLL-R3. Lane job complete.

## 11-25 01:0x PST: ARCHIVED, LANE CLOSED
- AUTO-EXPORT done 00:55 (RTX-FULL-AGI-META), unit coll_s__ax_d4ee7cbf4e: AGIdock /archive/opentallas-signed-1114/qwen_compute/coll_s__ax_d4ee7cbf4e + INDEX.tsv row; rtx-pro /home/ubuntu/signed-export-1114/qwen_compute/coll_s__ax_d4ee7cbf4e.
- LEC evidence: lanes/RELEC-1122.tsv row (record 360891638e3c) + lanes/evidence/QC-COLLS-LEC/cH8_coll_s_eco_360891638e3c_lec.json.
- coll_core owned by QC-COLL-CORE. Nothing open in this lane.
