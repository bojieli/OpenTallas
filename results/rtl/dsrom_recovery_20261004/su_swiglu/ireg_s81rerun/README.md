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
