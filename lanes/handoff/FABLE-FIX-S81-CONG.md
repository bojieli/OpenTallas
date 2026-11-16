# FABLE-FIX-S81-CONG handoff (owner of S81 routing congestion closure; directs S81-STRIP-O, inherits S81-RINGS-O open items)

Updated 2026-11-16 ~06:30 PST.

## Root cause (MEASURED)
- Ring class (t65, t68, 13 y-slot kits): lost `ring_place: ff` key. Fixed by r282 (S81-RINGS-O). A_t65 (B6gE rects + ff, E/W face) GRT 0.
- Strip class (what is left): ft bundles stacked in one strip between a face and an M7 core. t34: all six slots
  (ft0-ft5, 2,360 bits) have stations in the W strip x 0..48 beside u_ve.u_m (M7, x 48..220, y 78..423).
- t34 base kit b_t34 does NOT converge: one global_route call, it15 = 63 / 48 / 67 in three rounds. At about it15-17
  GRT prints `GRT-0273 Disabled NDR ... clknet_0_clk_tNN` (one clock net per round) and restarts from ~12k.
  4 rounds in 80 min, residual unchanged; it is H overflow at x 40..60, y 120..180 on ft2_o / ft3_i / ft5_o / ft0_o
  station nets, not clock. it5/it10/it15 of one round is not a convergence proof: count `Disabled NDR` lines.

## Fix in flight
- t34 ft5 (597 bits, S->N, window x 396..523) straight band x 486..552: the only full-height column free of every core
  (vsw ends 484, rxsf ends 477, vq starts 553, vn_a 570). corr2.py: 7 hops 201..207 um, 0 sites in M7 cores,
  0 collisions with kept slots. Takes 25 % of the bits out of the W strip.
  - rows: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/t34_rows.json; plan fx_t34.json (= fx0 + rows)
  - kit: same dir kit/c_t34 (GEN_LINT PASS, KIT_PREFLIGHT PASS), replicated to epyc8/9
  - run: intel2 ~/fable-fix-s81-cong/launch.sh c_t34 t34 grt (launched 14:2x UTC); log run_c_t34_grt.log
  - accept: GRT Final congestion 0 with 0 `Disabled NDR` restarts. Then launch.sh c_t34 t34 route, and READY-ROWS to DIE-S81-92.
  - if residual remains: next slot is ft2 (668 bits, stations (20,294),(52,9) in the same strip).

## Other types (S81-STRIP-O keeps the builds)
| type | base (ff) | row kit | decision |
|---|---|---|---|
| t47 | plateau 17.7k (4 NDR restarts) | c_t47 GRT FINAL 0 in 772 s | adopt t47_rows.json; route c_t47 |
| t43 | 7 at it25, H only | c_t43 plateau 3.7k | no row; base to route when GRT ends 0 |
| t62 | plateau 52.8k x2 (ft0/ft1/ft7, S strip x 400..600) | c_t62 in place | wait |
| t28 | 128k at it10 | c_t28 (sp2 core push) in place | wait |
| t75 | 83.5k at it15, 21 NDR lines | rows built 13:50 UTC | STRIP-O |
| t8 | 71k at it10 | t8c rows 14:01 UTC | STRIP-O |
| t72 | GRT extra iterations started 13:09 UTC | | wait |
| t65 A_t65 | GRT 0 | | route: post-GRT repair, 108k of 274k rows at 13:48 UTC (epyc9) |

## Inherited from S81-RINGS-O
- svc: 82 frozen bands without ff. Tool fix on main (r282). For the composed F2s plan: epyc10
  fable-fix-s81-rings/stamp/B6gF2s_svcff.json sha1 4c163bdc1625 (ring_ff_stamp.py). DIE-S81-92 adopts + lifts the svc
  exemption in chain_f2s.sh RINGFF accept. Asked in post 06:3x.
- t68 ft5_i band beside its pin window: advisory, no action.

## Next
1. Read c_t34 GRT (expect ~16:00 UTC). 2. Route goal on GRT-0 kits (c_t34, c_t47, b_t43, A_t65), sign-off, export
to AGIdock /archive/opentallas-signed-1114 + rtx-pro. 3. READY-ROWS per type to DIE-S81-92.
