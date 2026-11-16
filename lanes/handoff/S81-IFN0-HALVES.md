# S81-IFN0-HALVES handoff (11-16, lane Sonnet)
Goal: IFN=0 half cores hw/he for the 84 r0/h10_r1 col types (fallback for col-wave2).
## State
- Source kits copied from epyc10 s81-gotag-setup-1115/core/hwC,heC (not patched in place) to epyc7 /srv/opentallas-scratch2/claude/s81-ifn0-halves/hw0, he0 (run/ kept up to 3_place; 4_cts and later deleted).
- Measured (hw0, 4_cts, FF with vclk_ff): hold failing 2368 endpoints: 605 input ports (ws -137.1), 1763 reg (ws -82.5, mostly reset recovery/removal -23..). Input face = 604 input bits, 586 go direct into an ot_fcap_NNNNN_ff DFF; all fcap flops sit on the single `clk` net with 11,384 sinks (full core tree).
- Form (a) implemented: ifn0_face_branch.tcl (appended to face_capture_release.tcl, runs PRE_CTS): one BUFx12 from the clk net drives a new net ot_ifn_face_clk with every ot_fcap_*_ff CLK; TritonCTS builds a small separate tree. Env OT_IFB_BUF changes the buffer.
- Form (b): orfs_hold_mm.tcl copies: OT_HOLD_STOP_PS -1000000, endpoint/ws screen returns at once.
- Launched 11-16 ~08:2x via ot-run on epyc7: `run_kit.sh hw0 grt 64 16` and he0; logs intel2 ~/s81-ifn0-hw0.log, ~/s81-ifn0-he0.log; kit logs hw0/run_grt.log.
## Next
1. Read 4_1_cts.log: ot_ifn_face_clk tree, insertion of fcap flops (target TT 300-370 he / 330-390 hw); if CTS balance-latency re-adds delay, set the branch tap by a declared pin offset.
2. Read 5_1_grt: TT setup >= -42, FF non-port hold, GRT overflow; if setup of face->core loses, fallback in SPECS Spec 3 last paragraph.
3. Then route+signoff (goal finish), lib setup_rising/hold_rising check, tb_qxpq_go_boundary IFN 0 + mutant, LEC.
4. Post numbers to FABLE-FIX-S81-COLTAP and DIE-S81-92. Not yet posted: no CTS numbers yet.

## CODEX notes 2026-11-16 10:1x PST
- Took over hw0/he0 unchanged; active GRT FF hold repair at collection. The nominal face-branch hook moved only18 `ot_fcap_*_ff` cells. Actual input-cone census from 3_place.odb:604 input bits and604 first rising flops per half;586 via1 combinational hop,18 direct. Thus the name hook missed586 native input flops.
- Prepared independent successor kits epyc7 /srv/opentallas-scratch2/claude/s81-ifn0-halves/hw1, he1 from stable1-3 checkpoints. Clock hook reads exact604-name ODB list `ifn0_input_flops.txt`, errors on a mismatch; all original geometry/RTL stays. No added cycles.
- Visual review PASS-COND: results/geom_review/ifn0_all_inputs_1116.{png,txt} under lane root. Two central/east ROMs with10um horizontal separation, open west compute field and perimeter routes; actual clock timing remains to measure.
- Launched via ot-run64GB/16threads on epyc7, goal GRT: intel2 clients hw1 PID241701, he1 PID241702; logs ~/s81-ifn0-hw1-codex.log, ~/s81-ifn0-he1-codex.log. Follow604-flop hook count, TT/FF arrivals, GRT overflow and TT>=-42/FF hold before route continuation. hw0/he0 preserved as original experiments.
