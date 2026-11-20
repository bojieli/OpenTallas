# FABLE-FIX-HEAD-LEP0N handoff (Fable, started 2026-11-20 ~15:25 PST)

Task: own HEAD hd_lep0N (the 26th HEAD type) end to end to sign-off. 833 ps fixed; hold structural (lockups, shared taps,
CTS balance); setup by stages (+cycles pre-approved); no outline growth. r14 (HEAD-R14, epyc7 unit
oth-ubuntu-3749621-1795200539, kit epyc7 /srv/opentallas-scratch2/claude/head-crossing-1119/r14/lep_hop300/hd_lep0N)
is NOT mine and is not to be cancelled; if it signs off it wins.

## Read so far (r14 kit logs, 15:25 PST)
- r14 post-CTS, pre-repair (pregrt_ff_hold.log): FF hold wns -388.93, 25,801 ends: cross_tap 16,147 (-388.93),
  port_in 8,464 (-77.22), port_out 855 (-68.69), same_tap 336 (-154.61). Worst end is a hard-core pin
  u_core.u.g_pp[0].u_pair/coll_i[246]. Contract in_min -90, out_min 169.8, tap window 169.8, vclk FF 380.
- TT setup after the placement-RC repair: -171.65 (tns -1,364). Hold repair started 14:36 PST.
- Clock form: grid taps (OT_TAP_MAX_SINKS 800, target 450 ps) + 4 core-only taps clk_c0..3 (early 103.42, insertion 553.42).

## Next
- Census on r14 4_cts_pre_tt.odb (zl_pairs + class by tap pair / endpoint module) via ot-run on epyc7.
- Fork kit with the chosen structural form; build to sign-off; export.
