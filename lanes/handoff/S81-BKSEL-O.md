# S81-BKSEL-O handoff (Opus successor of FABLE-FIX-S81-BKSEL)

Owns: dsdv_bksel_q sign-off (last unsigned S81 core) + S81 type bk_sel__t2 HCPARAM fix.
Gates: DRC 0, TT setup >= -42, FF non-port hold >= 0, LEC.

## bksel_q (2026-11-16 15:3x UTC)
- fx1 (epyc8 2767309) + fx3 (epyc2 43933): hung in GRT hold repair, STOPPED by exact PID 16:0x UTC.
- Root cause: pk2 clock lands late (tap clkbuf_4_6_1 -> 354 um -> shared leaf clkbuf_leaf_10_ck far side -> 208 um -> pin; 696 TT).
  811 pk2 inputs FF hold -124; worst TT setup pk2 -> u_fq SRAM r_addr -149.8; pk2 out hold +298 FF. Probes: epyc8 fable-fix-bksel/probe/o_c2p/.
- fx6 RUNNING epyc2 unit oth-ubuntu-1123151-1794844336 (kit fable-fix-bksel/fx6/bksel_vC9fx6 on epyc2+epyc8; fx1 kit copy, re-places): etm_land.tcl = v3 (probe/bkselO_etm_land3.tcl: dedicated BUFx24
  at each ETM clock pin, measured tap choice, target regs_med - 180), v1 kept as etm_land_v1.tcl; fx_repair.tcl caps hold repair (-max_iterations 2500, OT_FX_HOLD_MAX_ITER).
- fx5 epyc2 PID 2269863 (placement form): GRT hold repair, still improving.
- Export (first SIGNED): repo export_view.py -> AGIdock /archive/opentallas-signed-1114/s81/dsdv_bksel_q/ (via intel2 key) + rtx-pro
  /home/ubuntu/signed-export-1114/s81/dsdv_bksel_q/, INDEX.tsv append, odb sha both sides.

## bk_sel__t2 HCPARAM (posted READY-RTL 11-16)
- Wrong side = die RTL frozen copy physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv (cab54e3df937).
- Fix file sha 51beecd2dc38: intel2 /srv/opentallas-scratch2/claude/s81-bksel-o/idx_hcparam/dsdv_idx_l20s.sv; epyc10 same dir + repo path.
- Release: next S81 bind with it + OT_HCPARAM_ALL=1 -> 0 mismatches, BIND_RC 0, LATCHECK pass (tl_o +3 edges).
