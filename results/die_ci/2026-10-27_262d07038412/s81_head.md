# DIE-CI s81_head @ 262d070384 — INCOMPLETE

plan `physical/die_plan/s81_head/die_plan.json` digest `a2eb7166e0b1fbc9`; run 531.3 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 6 warn; 16 types / 326 parts; worst cut 0.0637 |
| g0c | PASS | 0 err ; 16/16 types clean |
| xdie | PASS | in-die 0 err; s81: PASS (0 err / 2932 circ) |
| g2 | PASS | 6 probes, overflow 0, no-access 0 |
| census | N/A (census none: top-down plan of a new die: no bound as-built head-die netlist in this partitioning (the bottom-up H10 die chain used a ) | dropped - bits, unmapped -, inter - bits |
| latency | PASS | 328 lanes; table physical/die_plan/s81_head/lat/s81_head_latency.json |
| sta | NOT RUN (no seam between two partitions with routed views; stand-in budgets only) | 0/428 seam ports measured; worst seam (gate, TT/FF policy) setup@TT - ps, hold@FF - ps; stand-in 0 / 40 ps. INFO margined: - / - ps (- neg groups), stand-in -79.6 / -22.6 ps |

INFO margins (not gating until the owner rules) on top of policy (833.333 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 9f6cbf0662: xdie FAIL -> PASS; xdie.errors -130.
