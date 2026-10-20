# QW-DIECLK4 10-20: Qwen compute die clock (Q.CLK), rN re-analysis + rF/rFG trials

Source run (Codex own-copy recovery, DIAGNOSTIC copy of the dv2f19g3r PDN case): ep6
`/srv/opentallas-scratch/claude/codex-qw-dieclk3-recover-1020/chain_rN` (GRT0, TT -6305.08 / FF setup -4917.18 / hold -18579.43).
Tools: claude/qw-dieclk4-1020 (cc8ab9604).

- Drift: rN dck_FF/dck_TT = 0.83, so the drift is 0.17 x the src->dst region-entry offset. The spine entries spread
  20.5-25.0 ns (dc_root_r54 21.9 vs dc_root_r145 25.0). The old verdict's T/2 proxy (69/421 FAIL) is 4x stricter than
  the LANDING-CONTRACT L5 window (width D*T). Against the window: 0/421 over the (D-1)T - 200 ps proxy. With the die STA
  (fwd_land_plan --D-auto 4,5,6,8, hold margin 25 ps): window_fail 12 -> 0, with 388 lanes at D4 and 13 at D5.
  The D5 lanes are dv_rs_{W0,E1,E4,E5}_1_{a,b} (r41->r106, dst 3.4 ns late) and dvw_{rv,rd,rr,re}_wi (coll->r145).
  The GEN instantiates D5 rings for these (landing variant).
- NO_ROOT 8 is split into 6 BUMP + 1 FEED + 1 RESET_SYNC. BUMP covers bump_fwd_epoch / bump_fwd_lrst (qfd_sigbump) ->
  rly_lnk_fwd_* hop-0 on pll_r55. These are off-die inputs forwarded with pll_fwd. The GEN owes hop-0 clocked by the
  feed net (n_pll_fwd) + a landing into r55.
- Feed: ckb_rom/pll_ck[0] -> clk_rx/pll_fwd[0] (2.7 mm) is now its own buffered safe tree ("feed"), and the reach check
  covers it. GEN option: place clk_rx beside ckb_rom.
- Still FAIL `landed`: 182 slice<->slice NEIGHBOUR links (50,267 b). These are owed by the slice2 face parent (QW-SLICE4
  plan 7811217d7, SLICE7). The rN neighbour trim measured r110|r114 FF 91, r122|r96 95/97 and r126|r97 TT 102 (> 80),
  so neighbour matching is NOT a substitute for landing them.
