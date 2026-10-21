# dsdv_sh_lk_s10g: structural successor of s10f (S81-SHLK-1021, 2026-10-21)

s10f route dsdv_sh_lk_s10f-...-b0972fda0 (ot-epyc7) FAILED. Classification from the route reports:
- Judged sign-off (daemon w18 STA, 833 ps, die-context IO reference): TT setup +13.8 ps (MET), FF hold -20.6 ps on 31 D pins
  (reset-relay leaf ot_rlv -> RESETN removal, n=19; 2-4-level reg->reg fs/hr_d->mk_p1/apr->p_wb/rbin->rgray, sibling skew 50-60 ps).
  Route hold repair targeted +30 ps; ~50 ps was lost to RCX.
- The ORFS raw "hold -273 ps / 1449 paths, setup -79 ps" is the unreferenced constraint.sdc view (input min delay 166.7 ps vs
  ~450 ps propagated capture insertion; output max at the 770-ps over-constraint): not a clock-structure fault, not judged.
- DRC 19: all M4 shorts on the centre-facing pin face of the three MY-mirrored left-column macros (u_ox, hx u_mem0, u_rae;
  x = edge-1.5..edge-1.0). The m1 masters carry ~10 pins/um on their side faces (SAFE limit 6/um), so routes jog inside the
  1-um OBS gap. max_slew 30 on output drivers is secondary.

Fix (no RTL behaviour change, no added cycle):
- Codex p192 contact-pitch masters (accd38c70, behaviour body byte-equal, 0.192-um pin pitch = 5.2 pins/um), as _pa views
  (PG M4 straps pulled back 1.5 um from both pin faces), selected by `OT_S81_SH_P192` (default off; benches unchanged).
- Outline grown for the 77/86-um tall masters (s10g 345.6 x 432; s10h 388.8 x 453.6 with wider channels, parallel).
- Route hold repair margin 30 -> 60 ps.

SAFE checklist: 1 pins source-registered (unchanged s10e) PASS; 2 reach: tile <= 0.45 mm, no wire > 405 um PASS;
3 fanout native-32 (s10e census, same RTL) PASS; 4 depth unchanged (TT setup +13.8 at s10f) PASS; 5 storage in SRAM macros PASS;
6 macros on 43.2 lattice, pin faces 5.2/um <= 6 (fixed), 10.8 halo, aspect <= 1.25, full std band PASS (fill 30-35% = p192
perimeter cost); 7 one region, centre/E-face root as s10f, spread judged at gate; io_hold 0.03, hold margin 0.06; 8 static, +0 cycles.
Parent dsdv_seq_host_d must re-pack for the taller lk (432 / 453.6 tall instead of 280.8).
