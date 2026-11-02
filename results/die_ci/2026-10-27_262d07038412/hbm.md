# DIE-CI hbm @ 262d070384 — FAIL

plan `physical/die_plan/hbm_arch/B2l/die_plan.json` digest `b1782481b0eb2139`; run 487501.6 s

| gate | status | key numbers |
|---|---|---|
| g0 | FAIL | 586 err, 7713 warn; 49 types / 88 parts; worst cut 0.3239 |
| g0c | FAIL | 7712 err {'complete': 6925, 'm89_signals': 41, 'hops': 204, 'stations': 312, 'cuts': 29, 'reach': 201}; 12/49 types clean |
| xdie | FAIL | in-die 201 err; hbm-ds: FAIL (1 err / 480 circ) |
| g2 | PASS | 1 probes, overflow 0, no-access 0 |
| census | N/A (census none: B is a 2-quadrant die: lanes = the 16-SM r18h5 census folded (SW->NW, SE->NE; per-pair width = max over the folded quadr) | dropped - bits, unmapped -, inter - bits |
| latency | FAIL | 298 lanes; table no <die>_latency.json in the plan dir (gen.py latency never written for this plan) |
| sta | NOT RUN (no seam between two partitions with routed views; stand-in budgets only) | 0/918 seam ports measured; worst seam (gate, TT/FF policy) setup@TT - ps, hold@FF - ps; stand-in 0 / 40 ps. INFO margined: - / - ps (- neg groups), stand-in -79.6 / -22.6 ps |

INFO margins (not gating until the owner rules) on top of policy (833.333 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 9f6cbf0662: g0 PASS -> FAIL, census PASS -> N/A, g2 FAIL -> PASS; g0.errors +586, g0c.errors +7591, g0c.clean_types -22, xdie.errors -770.
