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
