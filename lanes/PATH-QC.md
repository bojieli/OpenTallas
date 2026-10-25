# PATH-QC — one complete Qwen-compute path (lane started 2026-10-25 08:10 PDT)

Path (Codex 07:19-08:04 selection, coord/codex-qcphys-0719-path-matrix.md):
landed QK/V in slice **W5** (SU/CROM/VM in sl_W5_su_c + SU lanes sl_W5_su_l0/l1) -> slice glue -> `sl_W5_fw` (slw_fw_v3, u_fdn dd_wo 548b)
-> `coll_f4` (coll_ftc) -> `native59` (qfd_native59_dv_headprep_obs1) -> `glue` (d2d_rom FDI 583b) -> `ucie_kv` (phy_ucie_kv)
=> KV die `sys_c.u_ucie_rom` -> PC_EN_0/PHY_EN_0 + EN heads (PATH-KV) -> return dr_o 520b native59 -> coll_f4 -> sl_W5_fw.
Plan of record: START plan codex/qc-start-plan-0719@1c0e347be4 (epyc1 repo), plan SHA ce2406b9...b92720, delta vs main = reset.start=broadcast only.
Path boundary (Codex): QKV projections are fixture-landed, so the c_W5_* CB (A0) tiles are NOT on this path cut (see OWNER? below).
"Signed off" = GEOM PASS + route + TT setup / FF hold sign-off (60/25, pairs <=80) + bound in the die + token exercises it.

## Item list (state 2026-10-25 08:15 PDT)  — 1 of 21 signed off
| # | item (die/type or core; instances on path) | state | next |
|---|---|---|---|
| C1 | core qfd_dv_s5_su8_rst3 (sl_W5_su_c.u_suvm_u_su8) | SIGNED TT+93.04/FF+2.39 (archive) | match frozen RTL+pins at assembly |
| C2 | core qfd_dv_s8_crh_rp1 (su_c u_cl, u_ch) | f57r4 routed, NOT SIGNED TT+220.57/FF-13.91 12 EP (u_c1 W0 -> g_cbk W1 control) | structural local control replica (proof 19dc8bd8d8), rebuild from 3_place, GEOM REQ |
| C3 | core qfd_dv_s8x_vmr x3 (su_c u_va/vb/vc) | vmr_s6h GRT PASS FF+3.12/0 ep (8645 hold bufs), not routed | route via autopilot (GEOM REQ), sign-off |
| C4 | core qfd_dv_s8x_prog (su_c u_pg) | prog_t2 DRT intel2 (adopted 1e6ddd577b30) | collect; structural review if DRT diverges |
| C5 | core qfd_dv_s8x_btab (su_c u_bt) | btab_t2 DRT 3 viol (SRAM0 edge pin access), adopted 1e3946971811 | collect; pin-access structural fix if stuck |
| C6 | cores qfd_qc_su_lane_w x8 (su_l0 u_lane0-3, su_l1 u_lane4-7; 8 pin hashes) | NEEDS-KIT (never) | kit after plan PASS for su_l0/l1 |
| P1 | type slw_su_c (sl_W5_su_c) | PLAN-STRUCTURAL (PROTO geom FAIL) | plan delta |
| P2 | type slw_su_l0 | PLAN-STRUCTURAL (PROTO geom FAIL) | plan delta |
| P3 | type slw_su_l1 | PLAN-STRUCTURAL (PROTO geom FAIL) | plan delta |
| P4 | type slw_fw_v3 (sl_W5_fw; dd_wo/dr_wi) | NEEDS-KIT | kit, GEOM REQ |
| P5 | type slw_stm (feeds fw x_stm/x_fe) | PLAN-STRUCTURAL (G2 GRT overflow 15992) | plan delta |
| P6 | type slw_st_b (feeds fw x_ctl) | PLAN-STRUCTURAL (PROTO geom FAIL) | plan delta |
| P7 | type sle_ctl (sl_W5_ctl) | NEEDS-KIT (face_guard 179, plan widths) | kit after 7b widths |
| P8 | slice W5 rest (slw_sc, slw_fe_v2, slw_st_a, slw_hc0..3) | sc PLAN-STRUCTURAL; others NEEDS-KIT | confirm which are crossed (bind_sinks trace) |
| S1 | type coll_ftc (coll_f4; dd 548 out, dr 520 back) | PLAN-STRUCTURAL (PROTO geom FAIL) | plan delta |
| S2 | type native59 | NEEDS-KIT; 32x512 SRAM view; SRAM rd_out pins LEFT edge (helper orientation wrong, NOT_READY) | orientation + pin-track audit, FT, kit |
| S3 | type glue (d2d_rom, sys_face, ...) | NEEDS-KIT; needs 64x137 replay SRAM, 4096x72 ROM, 64x512 SRAM views | macro views, kit |
| S4 | type phy_ucie_kv (ot_qkvd_ucie_x64_phy hard IP) | NEEDS-KIT; abstract/model only | physical disposition (hard IP abstract) |
| D1 | die bind of START plan (canonical source 394765394) | probe/R8/final bind errors 0, 377 parts/1933 crossings, 0 unbound/tied/undriven; verify running (epyc1 unit 3819982) | collect verify + constants |
| T1 | token pass on the exact path (QK actual -> W5 dd -> native59 -> glue -> ucie -> KV -> return) | xt1 START PASS on proof bind (085b2934f); exact-path xdie adapter NOT built; START bootstrap deadlock (KV boot vs global START) OPEN at CLOCK | xt1 on fresh bind; then exact-path run |
| K1 | KV link endpoint sys_c.u_ucie_rom 583b (+PC_EN_0/PHY_EN_0) | PATH-KV owns; native PC boot 4/4 PASS (functional) | coordinate in lanes/PATH-KV.md |

OWNER?: (1) The QKV projection CB tiles (c_W5_bf/bn/tn/tf_xx, A0 NK/NL cores) are excluded from this path cut by Codex (fixture-landed QKV). Should "complete path" include them? Default: excluded for this first path.
2026-10-25 08:09 PDT PATH-QC: started; f57r4 is routed NOT SIGNED (FF -13.91/12, not 'in DRT'). Sub-lanes live: PATH-QC-RP1 (C2 structural control replica), PATH-QC-SU (C3 vmr_s6h route, C4/C5 prog/btab collect), PATH-QC-TOK (D1 bind verify + xt1 START on fresh bind + exact-path adapter plan), PATH-QC-PLAN (exact W5 membership, PLAN-STRUCTURAL causes, west-strip kit blockers, one per-die delta).
2026-10-25 08:11 PDT FLOW-INFRA/DIE-PROTO -> PATH-QC: qwen_compute die-top GRT kit_it5 (plan d27c3788 = main, 5 iters) overflow 1,659,581 (M4 747 H / M5 170 V / M6 407,499 H / M7 1,251,165 V; max 121H/40V), all hot gcells in band y=10-11mm (x 2-5,16-17,19-22,24-27,29-30mm), nets ft_sl_*_su_c/_su_l1 SU feed-throughs -> needs structural FT relief in SU band; 44,005 leg-inst over 405 (worst coll_ftc 500.9um). 50-iter run LIVE intel2 dtrial-grt-134732; kit2 STA TT/FF live intel1. claude/die-proto-1025@bd51e6310 results/die_proto_1025/SUMMARY.md

## SCOPE ADDITIONS 2026-10-25 08:12 PDT (owner-approved via coordinator)
(1) Die level is part of "complete". Path items:
| # | die-level item | state | next |
|---|---|---|---|
| L1 | die GRT with the path's real signed-off views (stand-ins elsewhere) | NOT STARTED with path views (0 path partitions signed). DIE-PROTO kit_it5 on main plan: overflow 1,659,581, hot band y=10-11 mm = SU feed-throughs ft_sl_*_su_c/_su_l1 -> structural FT relief in SU band needed (same band as P1-P3); 50-iter run live intel2 | fold SU-band FT relief into PATH-QC-PLAN delta; rerun with path views as they sign off |
| L2 | die STA TT setup / FF hold over the path | NOT STARTED (DIE-PROTO kit2 STA live intel1 on stand-ins) | after L1 + path views |
| L3 | clock tree die root -> path flops (regional taps, related-pair skew + CPPR) | per-core only (RP1 pairs TT60.3/FF48.3; vmr per-corner I); die root->W5/west-strip taps not checked | die clock check on L1 database |
| L4 | reset + START broadcast | START plan G0C PASS, xt1 START token PASS (subset of 22 parts, excludes glue/native59); bootstrap DEADLOCK (KV boot vs global START; glue D2D cal seq) OPEN at CLOCK/RESET | CLOCK fix; extend START proof to glue/native59 |
| L5 | die-to-die link QC<->KV (glue d2d_rom FDI 583b -> ucie_kv -> KV sys_c.u_ucie_rom) | functional model only; PHY hard IP abstract; xdie adapter not built | PATH-QC-TOK + PATH-KV |
| L6 | token test on exactly the bound views | = T1 | T1 |
(2) Representative coverage (OWNERS.tsv replica counts, qwen_compute): qfd_tile_nk_a0c 720, cbx_q10 48, qfd_tile_nl_a0c 48, qfd_dv_s8x_vmr 36 (on path, C3), CB types 23-24, slice cores 12.
The path did NOT cover the top three. Added (resolves my OWNER? (1): CB tile is now IN the path; QKV comes from the real projection, not the fixture):
| A1 | core qfd_tile_nk_a0c (720 replicas; in c_W5_bn_10 u_t20/u_t21/u_t31) | REVIEW: nk_r4 FAIL_POSTCTS FF -316.66/2066 (structural.tsv 8fffd9b75f35); real internal ROM reset hold -94.64 (missing macro-internal clock compensation); ODB deleted by autopilot 07:22 | structural fix (ROM-leaf clock/reset compensation), GEOM REQ, rebuild |
| A2 | core qfd_tile_nl_a0c (48; c_W5_bn_10 u_t30) | NEEDS-KIT; NL combined0719 GPL-0307 diverged (ctl corridor overflow 0.85/0.92) | structural: widen control corridor / re-place, GEOM REQ |
| A3 | type cbx_q10 (48; instance c_W5_bn_10, fed by sl_W5_su_c cws2 / su_l0 cws3) | NEEDS-KIT (BLOCKED-A0: needs NK/NL abstracts) | kit after A1/A2 views |
Why c_W5_bn_10: it is the cbx_q10 instance wired directly to the W5 slice parts already on the path (su_c cws2, su_l0 cws3), and cbx_q10 contains both A0 cores (NK x3 + NL x1), so one CB instance covers all three most-replicated items.
Item count now 30 (21 + L1-L6 + A1-A3, L6==T1 counted once => 29). Signed off: 1 of 29.
