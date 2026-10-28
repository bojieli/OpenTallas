# ot_hdc_v41x_fdiv ZERO_RST=1 proof with mutant controls (HBM-CORES-REBAL-7, 2026-10-28 08:59 PDT)

gold = ot_hdc_v41x_fdiv from origin/main (renamed fdiv_orig, no zero-flag reset); gate = shared branch 9335c29df3 with ZERO_RST=1.
yosys 0.68 (openroad/orfs:asap7lock), miter -equiv, async2sync, sat -seq 26 -prove-skip 22, initial state of every flop FREE (independent per side),
inputs a/b/v free (general dividend, stronger than the side_rest a=1.0 use). DEPTH = 19.

| run | reset model | result |
|---|---|---|
| p_new_once | rst_n=0 at steps 1-2, 1 after (one power-on reset) | PROVED (no model) |
| p_mut1_once / _free | gate d_zero <= (a[30:0]==1) | CAUGHT (model found) |
| p_mut2_once / _free | gate r_zero[7] forced 0 (reset-path flag lost mid pipe) | CAUGHT (model found) |
| p_new_free | rst_n free after step 2 (reset may re-assert) | model found: outputs differ only at a step with rst_n=0 and vo=0 (both sides), i.e. invalid output during a re-asserted reset |

Feed-forward pipeline (no state loops besides vline), so equality at steps 23-26 after one reset holds for every later step.
The proof catches both mutants, so it counts (COORD 08:46 condition). Mid-run reset: only invalid (vo=0) y/fault differ.
