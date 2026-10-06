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
