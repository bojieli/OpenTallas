# smh_rp4hs_a1019 -- HBM SM tile rp4, s half (L2H-SM9 10-19, RELEASE_TREE H.STA.BLK.9)
Top ot_hbm_smh_rp4h_s (rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv), outline 457.92 x 691.2 (aspect 1.51); row 1 y 561.6, N band 38.9 um; pairs with smh_rp4hn_a1019.
Generator tools/hbm_sm_repack_1015/rp4h_kit.py; branch claude/l2h-sm9-1019. Predecessor smh_tile_rp4lp (one 457.92 x 1598.4 landed
parent) failed the safe-design review: aspect 3.49, 13/18 macros off 43.2, landing read select rc[1] 8,284 loads, gate1 GRT ovf
51,363 / FF hold -957, gate2 CTS rc 2.

Bench (Verilator 5.050, ot-epyc5): tb_ot_hbm_smh_rp4h2 = flat parent vs the two halves abutted: MUT0 PASS 12,796 compares (also
SOFTBEAT=1), MUT1 (bin crossing short) / MUT2 (gpm relay short) / MUT3 (leaf-1 pad short) FAIL; witnesses
results/arch/l2h_sm9_1019/bench/.  Same cycle offsets as the priced lp record (gout +3, all else 0): compiler unchanged.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every data pin registered in RTL (pinrow/pinbeat/strap/gather/crossing regs; rout/bout from hard row_e/beat_e flops);
  reset: RTL landing u_rst = 2 kept face stages + 1 kept copy per consumer (port net 1 sink); s land/leaf/gs copies +3 (lp depth).
2 Reach: PASS with one waiver -- bin path W pins -> 2 relays -> S-face out reg (<= ~350 um hops); s landing regs at N face -> x store
  bk1 <= ~250 um; gin pass lanes in n: N face -> FIRM mid station (h/2) -> S-face out reg = ~454 um hops (n_a) / 432 (n_b):
  waived (< measured repeated reach 600-750 um, reach-405-repeaters-1016); s relays FIRM mid (<= ~345 um).
3 Fanout: FIXED -- the landing ring/read mux is gone (no 8,284 / 4,145 / 4,140-load selects); every crossing / landing / beat
  register is a kept per-bit flop (1-2 loads); reset copies 1-12 loads. Kept-copy survival: OT_KEEP_REGS count in the gate log.
4 Depth: PASS -- crossing/landing/beat regs are reg->reg with no logic; leaf / transport children are CLOSED views.
5 Storage: PASS / waiver -- no runtime-indexed flop arrays; x store = SRAM child. Leaf-1 alignment pads 3 x (818 + 26) b (s half,
  inherited lp schedule) waived: a ring buffer would add a read mux (the very fanout this redesign removes).
6 Floorplan: FIXED -- all hard children on the 43.2 lattice (MX views snapped +0.024 um to the track grid by ref_tile: WARN only);
  >= 20 um channels; aspect 1.51 (<= 2:1); hard land children replaced by soft landing registers (rl1 no longer crosses a macro);
  BF16 columns / transpose / block-dot oriented so operands face the x store and sums face the transpose; full-width std-cell area.
  Pin faces: W/E <= 6/um (bin - /um worst), abutment face 2,219 pins over 449 um (5.3/um, M5+M7).
7 Clock: PASS -- one CTS root per half, clk on the abutment face (x 404) beside the partner half's clk/rst so the die feeds both
  from one point; the n->s crossing is a registered tile-to-tile link judged per linked child-flop pair at die level (owner 10-17
  boundary-match rule; landing removed because both ends are pin registers < 50 um apart); child_clock_ref boundary;
  hold_margin 0.03.
8 Schedule: PASS -- static; latencies identical to ot_hbm_smh_rp4_flat_lp_record.json (no new cycles to price).
