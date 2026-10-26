# TOK-QW xdie_bound 2026-10-24: compute -> KV D2D co-sim on the BOUND link ends (main 8a5d1f3dab)

Run: intel1 (key-cardinal) ~/ot-scratch/tok-qw/xdie_bound/run2, ot-run unit oth-ubuntu-194042-1792851975,
tools at e2aa830fad (tools/qwen_tokfunc/xdie_bound/run_all.sh), Verilator 5.050. 07:26-07:29 PDT.
(run1_missing_inputs = infrastructure NOT RUN: two results/arch inputs missing from the staged archive; not a verdict.)

## Scope (what is bound RTL and what is not)
- Literal carve of the bound partitions (bound_carve.py, instance text byte-for-byte, binder's own source resolver):
  compute bound_r8 {glue, ucie_kv, native59}; KV bound_pv {sys_c}. Closure files byte-identical to main (ELAB.txt).
  - KV sys_c (d2d_kv qkd_d2d_static_sfm + dcal bc4 + ucie_rom PHY): ELABORATES.
  - compute glue: DOES NOT ELABORATE: u_d2d_rom TXDP trap (F1) + missing macro ot_sram_1r1w_64x137_m1_r2c2_p192 (F5).
- Dynamic co-sim = the bound link-end MODULES with their bound parameters inside main's tb_xdie_qwen_exchange checks
  (make_tb.py: only the compute-master swap). NOT the full partitions: driving them needs the sys_face ROM calendar
  producer (OVL ROM content not in bound RTL), tt_ctlm, KV hub_C boot cfg and the distributed KV attention.
  Stand-ins: compute native59 = qfd_native59_dv_service; KV attention = qkd_kvs_attn_fl r17 + qkd_pv_fin_s; seam = xq_dly
  chains at XDIE_DIE_STAGES; PHY = ot_qkvd_ucie_x64_phy_model LAT 5. Bench shim: ot_sram p192 alias (F5).
- Constants: law compile (xdie_exchange_cal.py, seam 2,2,2,3,2,2/34,34,32,32,32,31,31) reproduces regen
  D2D_TXDP_C 0a010308 [8,3,1,10], D2D_TXDP_K 03030443 [67,4,3,3], D2D_KV_TX_LAT 67.

## Verdicts (23/23 configs met expectation; SUMMARY.txt)
- bnd_pair (bound compute master qfd_d2d_static_ovl_sf7_obs1 + bound KV master, TXDP applied by bench): FAIL — F6:
  KV status fault at the first STATUS landing (layer 1 rel 655): compute obs1 sends the kind15 v1 observer extension
  DATA[511:304]; KV qkd_d2d_static_sfm uses ot_qwen_d2d_status_rx_sf (requires d[511:156]==0). The obs1-aware KV RX
  ot_qwen_d2d_status_rx_sfm3_obs1 exists on main but nothing instantiates it.
- om_pair / _t8192 / _l0 (same, observer extension masked = DIAGNOSTIC source mod): PASS, 35 layers bit-exact.
- src_pair / _t8192 / _l0 / _phy9 (source compute master qfd_d2d_static + bound KV master): PASS.
- bnd_asbound_c_txdp: BUILD_FAIL (D2D_TXDP_NOT_COMPILED) = F1 dynamic witness.
- src_asbound_kimage (calendars compiled for the old 11/9 seam = what the bound images hold, bound seam + TXDP_K 67): FAIL.
- Mutants, all FAIL as required: TXDP_K 66 / 68 (src + om), TXDP_C 9, seam KS_RXV +1 (src + om), SK_TXP +1, CS_TXS +1,
  RESULT bit flip (src + om), STATUS done, PHY bit, KV run late.

## Measured (PASS vehicles, edges @1.2 GHz, identical all 35 layers; phy9 in brackets)
C2K cmd issue->land 55 [59], C2K q31 56, K2C r0/r31 53 [57], KVN k3 20, K2C status 49,
roundtrip cmd->r31 land 1887 [1895], kv_service cmd land->r31 issue 1779, compute done after r31 land 219,
exposed d2d on cmd->r31 = 1887-1779 = 108 / layer (3,780 / 35 layers); calendar layer period 7,056.
Layer-1 landings: cmd 658, q0 660, q31 691, kvn0 657, r0 2459, r31 2490, status 2701, done 2709.

## Static audit (audit.json)
F1 FAIL compute glue.u_d2d_rom TXDP bound 0 vs 0a010308 (constants.json: "not in param_regen.json").
K1 OK KV u_d2d_kv TXDP 03030443; K2 OK D2D_KV_TX_LAT 67 == TXDP_K port 0.
F6 FAIL STATUS codec pairing (above).
F7k FAIL KV dcal bc4 includes d2d_cal_image_mu.svh: TXDP_K 22, period 249,600, CAL_START differ from the regen image
  (period 258,048); K tables are boot-loaded (target 11) but START / PERIOD are compiled in.
F7c FAIL compute sys_face qfd_d2d_cal_seq_ovl_rope images (ovl_release_rope OVL_TXDP_K 16h, *_ew1627_r16_rope period
  293,376) differ from the regen image AND from the KV die's image.
Regen recipe with the OLD seam reproduces main d2d_cal_image_mu_ew595_r16.svh exactly; with the bound seam it differs
only in D2D_CAL_C_RX_IMG and D2D_TXDP_K.
