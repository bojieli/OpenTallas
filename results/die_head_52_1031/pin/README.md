# DIE-HEAD-52 helper pin: HEAD plan l48x / l49x (raw-export pin shorts) + 12.25 gate with fclk-fall fstart

COORD 10-31 18:0x (4), HEAD-RINGHOLD-2 17:49 (1)(2).

## Pins (l48x = l48w + 51 pin moves; l49x = l49s + the same 51)
- pinov.py: same-layer pin-rectangle overlap over every type io.tcl generated from the plan (gen_phys.io_tcl, tools 5eeeccdc50c).
- l48w: 51 overlaps in 18/25 types, every one = a rst_start_raw_<k> M7 export pin on a die spine tap pin (clk / clk_t<n>, M7);
  same on l47v/l48a (pre-existing), and the hd_turn_a one is the DRC 1 HEAD-RINGHOLD-2 hit in the l48f route.
- make_l48x.py: each such landing_contract pin moves +1.728 um along its M7 track (HRH2 offset; hd_turn_a = [27.0, 741.528]);
  reset_start_raw_exports keeps the raw FF source xy (G0C proves it against the actual reset tree;
  moving it gives 1866 G0C errors). No RTL, net, tap or other pin change; plan diff = 52 xy values.
- After: 0 overlaps on all 25 types (ov_l48x.json, ov_l49x.json). START stage leaves (variant h) are M9 die pins: no same-layer conflict with partition pins (<= M7).
- G0C (tools 5eeeccdc50c): l48x / l49x = l48w (1 err pre-existing SerDes native release PENDING, 44 warn), 0 new / 0 gone.
  Strict bind HEAD_DIE_PORTBIND_SOURCE PASS (both).
- sha256: l48x e63f00ea5740..., l49x 714da58fbdf1...

## 12.25 die gate, fstart sampled at the fclk fall
- die_sta_related had no write_fall term. claude/dh52-gate-1031 adds opt-in --ca-write-fall (count_align_bind.write_fall_ports,
  lag L + T/2, the same model as count_align_bind.verify()).
- run_gate.sh: proof clk_st51/proof_l48w_sth (variant h), bind clk_st51/bind_l48w_dm700.json, plan l48x.
- o_l48x (no fall): = variant h (TT +252.75, contract 0, CA lo TT 215.3 / FF 244.5, start-skew 0/1607, BLOCKED(kits)).
- o_l48x_wf: 28 fall crossings (hd_turn_a 12, hd_st_turn 8, k5 4, n4 4): fall rows lo >= 710.5 TT / 714.1 FF, hi >= 676.2 / 701.8;
  die worst hi 888.0 -> 676.2 TT, 1015.4 -> 701.8 FF; lo/slot_read unchanged 215.3/244.5; guard slack 572.1 / 597.6;
  0 fails; TT setup +252.75; contract 0; verdict BLOCKED(kits) (530106 hold pairs without signed views).
