# HBM su31 endpoint-order proposal, PREP only

Picture: results/token_pass/hbm_su31_delay_prep_2058/order_review.png (viewed).

Current NW L5 N/E endpoint order is monotone. Paired reversal at NW_su31 output and NW_b110 input preserves all 2726 bit/layer contacts and zero seam gap, reducing the maximum pin Manhattan lower bound from 2998.512 to 2545.216 um, but introduces endpoint-order inversions. The chords cross the four core bodies and are explicitly not proposed routes. Layer crossing demand, actual legal station banks, clock/reset contacts and PDN access remain unqualified.

Verdict: PASS-COND for analytical PREP only; no physical dispatch. ROOT selected monotone 8 FF instead: +2726 flops and +1 NW L5 cycle, no pin-order changes. New macro-free bank allocation and its actual all-bit hop census and visual review must pass before route. NE seven-stage type remains unchanged if it closes.
