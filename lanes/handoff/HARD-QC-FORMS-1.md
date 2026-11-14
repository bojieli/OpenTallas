# HARD-QC-FORMS-1 handoff (Fable; QC hard repeat-failing type forms; COORD coordinates)

Started 2026-11-13 06:05 PST. Scope: the unowned DIEVIEW-QC-1113 findings: (a) su_l1 / su_c macro walls behind pin faces, (b) coll_core, (c) CB window-to-tile binding and tap windows, (d) stm ROM row + ROM-read pipeline, (e) setup negative at CTS (st_a). Deliver: plan deltas to DIE-QC-100 for s29, RTL / tool READY branches off origin main, rules in RULEBOOK-1113.md. Then stop.

## Where
- Work dir: epyc7 /srv/opentallas-scratch2/claude/hard-qc-forms-1 (ev2/ = file copy of DIE-QC-100's epyc9 wt/qc-s28-event2 @0bac129af3 without .git; bind_ev2st_g1 copy; tools/tr.py = my type plan render; png/; out/street_head.json = street_rule check of the head with the 59858adeb6 tool).
- Plan base: s28 head zz_gates_ev2st.json 736058c458ee; bound plan zz_bind_ev2st_g1.json 9f3ed3486d81 (bind not clean: 92 errors R8_STALE / LANE_ASBUILT / PARAM_REGEN, DIE-QC-100's item).
- Build pipeline: sub-agent HQF-PIPE (Opus) builds epyc9 /srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe (chain_qc.sh, rebind_qc.sh, README.md); private kits via component-proof + kit-rtl + gen phys; builds through ot-run on epyc7 / epyc4. Baseline: sle_stm_v2__cl7b3062fa.
- Local scratch: localhost scratchpad hq/ (scripts p1-p3.py, tr.py, png/).

## State
- 06:40 read DIEVIEW, RULEBOOK, DIE-QC-100 / CTLCAP / RESID handoffs, METHODOLOGY 12. Base renders of su_c, su_l1 (sle, slw), coll_core, stm, cbn_q00 drawn and viewed.
- stm: DIE-QC-97 (11-10 23:10) measured the class: ROM clk->Q 598 ps, then OR4/AOI + 13 buffers to tw_data registers 350-663 um away. qfd_dv_table_rom_loader already has an opt-in CAPTURE_STAGE (+1 write edge). Form = CAPTURE_STAGE on + ROM block under the N window.

## Next
Design forms per family (guarded delta scripts), proof builds, RULEBOOK rows, READYs.

## 08:1x state (read this first after a restart)
- CORRECTION of my first note: the QC token sim reference is also CAPTURE_STAGE 0 / LOCAL_JOIN 0 (tools/qwen_tokfunc/current_path/table_roms.py: "Current no-S6_SIM inlined reference 0/0; archived ns4 is 1/1"). So OT_QC_TLOADCAP is a real +1 write edge (first VM write 3 -> 4, last 90 -> 91 after the sample); TOK-VERIFY / compiler must take it. Kit netlist check: epyc4 kw26 slw_stm_v2__cl1ca9c415 a8 1_2_yosys.v has 34 g_wek copies and 0 g_capture.
- F-STM (11 stm types): epyc7 hard-qc-forms-1/tools/form_stm.py + hqf_apply.py (guarded, idempotent) -> forms/f_stm.json, plans/head_fstm.json df03db72315f (on head 736058c458ee). ROM 2x2 block x {77.76, 246.24} y {1537.92, 1602.72}, orient kept, + define OT_QC_TLOADCAP. street_rule (59858adeb6): all 11 types 0 violations (was face_street 1 each). Render png/fstm_*.png viewed.
- F-SUC + F-COLLCORE: tools/form_su_coll.py -> forms/f_su_coll.json, plans/head_fsucoll.json 8c885ebb72c6. su_c middle row +25.92 x, u_cl -8.64: sle_su_c 0 violations, slw_su_c x2 keep 1 (u_va 25.92 behind 735 W pins; u_va carries a physical ft, needs the seam event). coll_core face_1 bank[0] SRAM x 17.28 -> 60.48: face_street 0 (slivers 25 -> 39, tool reclassified 14 "street": not understood yet).
- Bench: epyc7 hard-qc-forms-1/bench/rtl/test/qwen_dv/tloadcap (tb_tloadcap.sv, run_tloadcap.sh, iverilog -DSYNTHESIS): base N=1 PASS (447 loader writes, 43 stream writes), N=0 / N=2 / CAPTURE_MUT 1 / warm-reset-not-moved all FAIL. Local copy scratchpad hq/tloadcap/.
- st_a CTS setup (HQF-STA, epyc4 hard-qc-forms-1/sta/sle_st_a/): WNS -464.73, 602 endpoints, 0 clock class. DEPTH+MACRO: u_scale_wait SRAM (clk->Q 250) -> 18 cells of u_mul (qfd_dv_s8_station_tail1.sv:275/283), 260 endpoints incl. mul internal 21-cell stage; MACRO+REACH: btab SRAM (364 ps) -> g_read 685 um, 160; REACH: g_pin.r[32] merged across 4 regions (39 shared flops) 27, cland_rs_s1 dsel -> u_bin_rs_s1 1146 um 64, r3.g_nb.u_o -> u_bout_x_fe_o 1232 um 64.
- Worktree clone epyc7 hard-qc-forms-1/wt (blob:none, 9 GB of trees, slow) for branch claude/hard-qc-forms-1-stm-tloadcap-1113; RTL patch not yet written: qfd_dv_s6_stm + qfd_dv_s6_stm_se0 get `elsif OT_QC_TLOADCAP -> #(.SLICE(TSLICE),.CAPTURE_STAGE(1),.LOCAL_JOIN(1)).
- HQF-PIPE (Opus sub-agent) still building the private kit chain on epyc9 hard-qc-forms-1/pipe.
- CB (c): cbn_q00 = 2x2 NK mesh; t00 takes na/nb from the N face and drives y_o00 on the S face, so a N->S transit of the quad is inherent; no plan delta yet.

## 07:35 resumed after the Fable limit (QC-FORMS-2 carried 06:55-07:26; read lanes/handoff/QC-FORMS-2.md, its HANDBACK section is the state)
- Added by QC-FORMS-2 and kept: F-SUC2 (u_va / u_vb +17.28), fwd_repoint.py (R-REACH-4 after every core move: NEEDED), form_stm_reach.py (stm S / E window stations), OT_QC_PINKEEP branch claude/qc-forms-2-pinkeep-1113@17e7e452ca (not READY), pipe run_q2.sh / AUTO_HOST, s29/compose_qf2.sh.
- Every core-moving form needs reset_pad -> reset_repick (-> tap_ident) before the re-bind, else EMIT kills kit-rtl for the whole bind.
- Runs in flight (epyc9 pipe/runs): base stm (cts), fsta (place), fsta2, fstm3, fsuc2r. Failed and to redo with pad + repick: fsucr, fsul1r, fcbr. base cbn_q00 failed at gen.
- RTL branch is train 46 (merge lane landing 28be9ae16c). SU double insertion (60 LATCHECK) is DIE-QC-100's; su forms wait for its order.

## 13:00 state (newest; supersedes the form numbers above)
- POSTED: queue 08:35 FINDING (18 types off-row ft bit sites; coll_core tap contradiction), 09:34 READY s29 form deltas (package lanes/HARD-QC-FORMS-1/s29, compose_hqf.sh, gates), 12:51 STATE proofs; RULEBOOK section R-QCFORM (7 rules) appended.
- RTL: train 46 on main. Follow-up claude/hard-qc-forms-1-tloadcap-synth-1113@3a7c24cff9 (loader capture profile synthesizes; SWREG on the _nb0 copy) offered to ROOT-MERGE in the 09:34 READY. PINKEEP branch 17e7e452ca not READY.
- Forms (final shas in s29/): f_stm 849c4c118d2a (8.64 lattice: x 77.76/250.56, y 1486.08/1598.4), f_su_coll bda9f17df6f1, f_suc2 dbf3a459cc7d, f_cb fb2dbfec33b7 (candidate), f_sta2 ab9d7dcb0cd5, f_sul1 4c4ccd4629ba (NOT ready: schema 28 errors). Composed gate plan 4a5e5065baf3: schema PASS, G0 349 -> 344, G0C 449 -> 442.
- Proofs (epyc9 pipe/runs; post-CTS): stm base -679.0/886; fstm4 (block + stations) -578.7/666; fstm6 (+TLOADCAP, old block position) -437.3/806, all three in GRT. fsuc3 sle_su_c placed, -873.1/2533, GRT DRT-0073 u_va/ck. fcoll2 coll_core placed (epyc2), running. fsta/fsta2 INVALID (define not compiled).
- Running: fsta3 (st_a_v2 with patched kit RTL incl. s8_ce nb0; launcher waits for the first rtl/gen), bsuc (no-form su_c baseline: rebind then run_prov.sh). pipe/run_prov.sh = provisional child views; overlay lives in pipe/provw (ot-run --stage refuses links inside W). epyc4 root under the 150 GB guard: jobs spill to epyc2 / intel1.
- Kit RTL comes from the bind source list (s28 event tree), NOT pipe/tree: any RTL form must be copied into K/rtl after gen and the netlist checked.
- NEXT: st_a result; su_c DRT-0073 split; F-STM-REACH last station inside the home + lattice-position stm build; GRT / route numbers and renders; post READY for PINKEEP after the flop-count check; then stop.

## CODEX 2026-11-13 14:2x PST
- Current task details and jobs are appended to handoff/QC-FORMS-2.md. No new lanes/worktrees.
- READY source95dd92ef230b pushed hub on existing claude/hard-qc-forms-1-tloadcap-synth-1113 (parent3a7c24cff9). Default-off PINKEEP now covers actual ce/nb0 copied tail plus normal tail, 0 cycles. Actual-g_pin lockstep2048cycles+bitflipmutant PASS; synth nb0 baseline325 FFbits vs1300 with4 independent kept copies. Evidence E7 hard-qc-forms-1/pinkeep_nb0_codex4. First bench harness drafts had syntax/command-separator errors; final suite fixed them and passes, failed draft logs preserved. No physical PINKEEP claim.
- fsta3 E7unitoth-ubuntu-539407-1794606451 remains running as SWREG-only proof; CB output-landing E4unitoth-ubuntu-3442636-1794607533 PLACE-only; HCI new-band E9 private rebind+gen chain pending. All via canonical I2ot-run; see I2~/hqf-codexlog.
- CBF +1 fixed PINcycle corridor candidate (514bits each cbf_q01/s2,maxhop311.130um) packaged in pipe/s29/cbf_r8_corridor_candidate.json and CBF_CORRIDOR_CODEX.md. No generated RTL edited, no contract adopted. Parent die lane owns coherent INNER/model/bundle update before any physical proof.

READY CODEX 2026-11-13 15:30 PST — NS face-register bank geometry
Branch claude/hard-qc-forms-1-tloadcap-synth-1113; commit d2506256e2 (above PINKEEP95dd92), pushed HUB. Explicit3files face_flops.tcl/gen_phys.py/schema.py only,24lines. Adds default-off budgets.face_flop_ns_types per exact/unsplit type with bounded row_stride/inset_rows; existing EW rules unchanged. Actual fsta4 Nstrip census showed516payload boundaryFF+epoch packed on adjacentrows at .987density; deterministic candidate uses2.16umcolumns,occupiedrowpitch.81um,1.08umedgeinset. Actual OpenROAD placement pass all517pin→FF-D hops max20.295um<30; payloadbank91.8x12.15um, true x1/x2/x3 FFfootprints, plot personallyviewed. Proof I2 hqf-codexlog/fsta4_nstrip_spread4.log unit1437431 exit0. No RTL/cycles change. Defaultconfig unchanged, invalid geometry rejected, pertype/base selection checked; no broadtests. Candidate plan E9 hard-qc-forms-1/pipe/tree/physical/die_plan/qwen_compute/plan_of_record/zz_st_a_nsbank_codex.json sha bf791501e4d0; constructor s29/st_a_nsbank_codex.py/report/plot qc-ns-bank.png. One private fsta5 PLACE-only pilot from unchanged4xPINKEEPnetlist (sha4d90be208ee8), noCTS/GRTuntilfreshreview. Merge ownerroot; preserve other additive clock schemas during merge.
