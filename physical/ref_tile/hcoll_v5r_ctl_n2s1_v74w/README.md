# hcoll_v5r_ctl_n2s1_v74w -- d4g COLL release leaf n2s1 (VM_RT 74), structural SAFE successor after v74k/v74e GRT FAIL (L2H-SMATT 10-19)
RTL ot_hgi_coll_ctl_v5r_n2s1_safephys unchanged (Codex COLL-SAFE fixed-delay SRAM pipes + 9 KEPT reset copies, mapped max 32). Same ABI/edges as v74.
Parallel twins: hcoll_v5r_ctl_n2s1_v74w (259.2 x 345.6) and _v74x (302.4 x 345.6). Bind whichever closes first; cancel the other.

Why (v74k/v74e gates, branch claude/hbm-coll-v74e-1019, evidence committed on claude/hbm-coll-v74w-1019): trial GRT M4 overflow
398/1267 (n1s0) and 96/270 (n2s1), every marker inside the macro-stack bbox at cap-0 gcells. The four SRAMs (LEF OBS M1-M4 over the whole
macro, pins M4 on BOTH W and E faces: rd_out/wd_in W, w_mask/wd_in/rr/cr E) were ONE abutted N-S column spanning y 43-284 of a 345.6 tile
with layer cap M5: no horizontal layer crosses a macro, so all W<->E traffic (W tile pins + W-face pins <-> E-face pins + E tile pins)
had to squeeze through 2x 43 um at the stack ends and GRT pushed it through cap-0 macro gcells. Halo/pin-pitch fixes could not help.
Structural fix: TWO macro columns with full-height horizontal channels between macro rows (no abutment):
  col A x 43.2: u_vm 128x256 at y 43.2 (top 123.7), u_se 128x256 at y 172.8 (top 253.3)
  col B x 172.8: u_inj 32x128 at y 43.2 (top 83.2), u_sl 32x128 at y 172.8 (top 212.8)
  horizontal channels across both columns: y 0-43, 123.7-172.8 (49 um), 253.3-343 (90 um); col B also 83-172.8, 212.8-343.
  std bands: W 2.2-43.2 (41 um), middle 138-172.8 (34.8 um, serves col A E faces + col B W faces), E 224.2-259.2 (~33 um).

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (native v74 ABI) -- inputs captured at pins in RTL, outputs flop Q (pin_regs OFF as approved v74; a synthesis stage adds
  an unscheduled edge); reset 2-stage face landing then 9 kept D1 copies; pin_min_tracks 4 (0.192 um, <=5.2/um); W ~1,700 pins over 345.6.
2 Reach: PASS -- outline 259.2 x 345.6, every pin->flop and flop->macro path < 405 um Manhattan.
3 Fanout: PASS -- reset copies max 32 (results/arch/hbm_coll_safephys_1019/mapped_sizing_rst).
4 Depth: WAIVED-measure -- iter_mul pd->m_rgx_l ~655 ps / 19 levels estimate (< 833 ps period, 600 ps is guidance); measured TT setup
  decides; pipelining it would add an edge to the v74 schedule (H.STA.BANKLAT.COLL price) -> only if measured setup fails.
5 Storage: PASS -- 4 fixed-delay SRAMs (2x 128x256 p192_mir, 2x 32x128 p192_rc); macro faces 410/199 pins at 0.192 = 5.1/um (<=6).
6 Floorplan: FIXED -- macros on the 43.2 lattice, no abutment, >=33 um std channels at every pin face (row halo MACRO_ROWS_HALO_X 6.48),
  horizontal channels between macro rows; continuous std band (no islands); aspect 1.33; fill WAIVED pin-bound (~22-25%).
7 Clock: PASS -- clock_split_km K=8 regional roots on clk_control (v74k measured pin-flop spread 33/37 TT/FF); io_hold_margin 0.03.
8 Schedule: PASS -- static, no added edge vs v74 (proofs production 1792 + dense 8192 PASS at LAT 74; mutants FAIL).
Parent impact: slot grows from 172.8 x 345.6 to 259.2 x 345.6 (ctl_v5 parent / GEN2e COLL slot, H.STA.BLK.16.4).
Critical prefix (ot_hgi_coll_ctl_v5): gate PNGs go to the coordinator review queue; no REVIEW.json / submit by this lane.
