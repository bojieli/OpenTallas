S81-KITS-RTLA round 3 (2026-10-24): ot_s81sl_vs pin registers + constant / unused pins, branch claude/s81-kits-1024r.
- face_guard/ot_s81sl_vs_before.json: the C3 kit RTL (= this branch before the fix). FAIL: 736 shared = x_wd 256, u 256,
  x_wa 10, x_wm 8, u_i 3, um_q / um_b / um_i 10 (all hold registers: the pin flop fed its own D on hold ops), fault 1
  (sticky), ve_ah 128 + ve_rh 64 (BF16 low halves on the TIELO net). 2 dropped = s_d[63] / s_d[61] (imm[31] / imm[29],
  no command field).
- face_guard/ot_s81sl_vs_*: fixed vs (synth-only kit from the C3 vs_lfp kit), raw + ODB PASS 2534/2534.
  face_guard/ot_s81sl_ve_*: ve with packed r_h / a_h inputs, raw + ODB PASS 973/973.
- vs_miter.log: old (a2b6fb6df) vs fixed vs lockstep, 40k random cycles. Packed ve_rh / ve_ah compare the old high
  halves, and the dropped low halves are checked 0. The old s_d gets the narrowed word with 0 at bits 61 / 63.
  Base PASS. Mutant (um_q state copy not updated) FAIL.
- gates/: vs MUT0 PASS + MUT1 caught, leaf MUT0 PASS + MUT1 caught, beat, ve bench / miters / mixmiter / s2miter + ve
  mutants, vq_pinreg_eq + mutant, aq12, hcpl, eng split, plan G0 / G0C 0 errors (after the LEAFPLAN af6b1f54d merge).
