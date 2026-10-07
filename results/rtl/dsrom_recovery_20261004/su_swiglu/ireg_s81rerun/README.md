# su_swiglu lane IREG (CLAUDE S81-RERUN, 2026-10-06)

Deferred-input-hold check (`results/rtl/dsrom_s81_fulldie_20261004/r9/deferred_hold/summary.json`): the adopted lane
(r4 / r4_shared, IO false-pathed) has ~1.0 ns of logic from `g` / `u` / `lim` to `p_g` / `p_u`; no parent register can
meet both its SS setup and FF hold windows.  `IREG = 1` (default off) captures every input in a flop at the pin and
registers the fault OR at its pin, so the boundary is register-to-register (owner MARGIN-FIRST).

| run | source | result | cycles (W64, routed / shared) |
|---|---|---|---|
| `run_rtl_W64_NB32_m5a4q5_ireg_*.json` | 7d2b942fb, IREG = 1 | PASS 9/9 (L0/L3/L20/L24 routed + shared, random) | 241 / 191 |
| `baseline_ireg0_run.json` | same tree, IREG = 0 | PASS | 240 / 190 |
| `mutant_g_bit20_run.json` | IREG = 1 with `r_g <= g ^ 32'h00100000` | FAIL (3,456 a errors, 108 q errors) | - |

Cost: +1 cycle (0.833 ns) per lane operation (ffn.swiglu, ffn.shared_swiglu each layer); about 0.1 us a token
(< 0.02 % AR).  Route: `physical/dsrom_su_swiglu_ireg/launch.sh` (IO timed, 0.770 ns, 200 ps IO budget), EPYC2
`/srv/opentallas-scratch2/scratch/claude/s81-rerun/swiglu_ireg/route/lane_ireg_m770`.

## Margin route `lane_ireg_m770` (IREG = 1, routed at 0.770 ns, IO budget 200 ps): NOT ACCEPTED

Flow (WC = SS, routed at 0.770 ns): WNS -73.5 ps, 42 endpoints, DRC 0, antenna 0, DRV 0; area 17,495.5 um2.
Re-timed at the 0.833333 ns sign-off (same routed odb + SPEF, SS libs, `route_m770/summary_raw.txt`):
WNS -10.18 ps; every endpoint under +40 ps is one adder stage -- `u_exp.g_h[2].u_a` (`ot_hdc_fp32_add_f12_l4`,
cut 1 -> cut 3: the sum carry chain AND the leading-zero OR tree in one stage) -- plus the flop-at-pin outputs `vo`
(+34.6) / `fault` (+38.0), whose slack is the 200 ps IO budget against ~400 ps of internal clock insertion.
The pin registers did their job (no boundary path is critical).  Below +40 -> RTL change, not a re-route: the exp
polynomial adds get the sum | LZC cut (CUTS bit 2), see `EXP_ASUM` below.

## ESUM = 1 (exp polynomial adds on `ot_hdc_fp32_add_f12_l5s`, 0c9c4c32a, default off)

| run | source | result | cycles (W64, routed / shared) |
|---|---|---|---|
| `run_rtl_W64_NB32_m5a4q5_ireg_esum_*.json` | 0c9c4c32a, IREG = 1, ESUM = 1 | PASS 9/9 | 247 / 197 (+6 vs IREG only) |
| `mutant_esum_LP_eq_LA_run.json` | same, exp alignment `LP = LA` (the cut's cycle not accounted) | FAIL (3,350 a errors, 106 q errors) | - |

Cost: +6 cycles per lane op on top of IREG (2 lane ops a layer): ~0.6 us a token, < 0.1 % AR.
Route (ONE variant): `physical/dsrom_su_swiglu_ireg/launch_esum.sh`, EPYC2 `.../s81-rerun/swiglu_esum/route/lane_esum_m770`.

## ESUM margin route `lane_esum_m770` (EPYC3; IREG 1 + ESUM 1, routed 0.770 ns): SETUP CLOSED, hold re-route

Die-context sign-off at 0.833333 ns with `physical/dsrom_su_swiglu_ireg/die_io_833_{ss,ff}.sdc` (IO clock latency =
the route's measured insertion, 200 ps setup IO budget = 150 ps die clock-arrival + 50 ps wire; 50 ps hold IO
uncertainty), `route_esum_m770/io_{SS,FF}.log`:
- SS setup WNS **+67.11 ps** (TNS 0): the exp sum | LZC cut removed the -10.18 ps stage; accept line +40 met.
- FF hold: internal WNS +7.91 ps (< +15), outputs -44.98 ps (flop-at-pin outputs leave ~60 ps after the earliest
  receiver could capture under the 50 ps hold IO term).  Hold is a repair item, not an RTL one: ONE re-route
  `launch_esum_hold.sh` (same RTL, `hold_io_append.sdc` puts the die hold IO constraints on the ideal port clock,
  hold margin 30 ps).
Note: `-reference_pin` IO delays crash this OpenROAD build (Sim::findDisabledEdges), hence the virtual IO clocks.

## Hold re-route `lane_esum_h770b` (EPYC3; input hold to die STA, buffer cap 100 %): SETUP CLOSED, HOLD NOT CLOSED

Flow: NOT_MET in the route's own acceptance (WC route at 0.770).  Die-context sign-off at 0.833333 ns
(`route_esum_h770b/run_io_h.sh`: IO clocks at this route's OWN measured insertion, SS 344.5..396.3 / FF 206.6..247.1 ps,
200 ps setup IO budget, -50 ps hold IO term):
- SS setup WNS **+65.23 ps** (TNS 0): closed.
- FF hold: inputs **-111.3 ps** (g_ireg.r_w/r_u/r_g pin flops: no input hold repair in the block by construction, the
  -50 ps term puts input data 50 ps before the earliest tree edge), outputs **-47.0 ps** (a[*]).
Under the budget sheets' FF hold model (input min = clk->Q FF 32.2 + 0.112 ps/um x L, vclk at the block's mean
insertion) the input classes are about -3 ps: hold is a repair item (die STA input hold window + the closure loop's
hold ECO), not RTL.  Next: one closure-loop job of this lane with the budget-sheet SDCs (route + FF) and the auto hold ECO.
