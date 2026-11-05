# DIE-CI qwen_compute @ 6defc3c230 — FAIL

plan `physical/die_plan/qwen_compute/die_plan.json` digest `cf288214fc628d76`; run 13778.7 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 293 warn; 68 types / 377 parts; worst cut 0.2159 |
| g0c | PASS | 0 err ; 3/68 types clean |
| xdie | PASS | in-die 0 err; no rack system |
| g2 | FAIL | 6 probes, overflow 9, no-access 0 |
| census | PASS | dropped 0 bits, unmapped 0, inter 697959 bits |
| latency | PASS | 1933 lanes; table physical/die_plan/qwen_compute/qwen_compute_latency.json |
| sta | NOT RUN (no seam between two partitions with routed views; stand-in budgets only) | 0/3005 seam ports measured; worst seam (gate, TT/FF policy) setup@TT - ps, hold@FF - ps; stand-in 0 / 40 ps. INFO margined: - / - ps (- neg groups), stand-in -84.8 / -22.6 ps |

INFO margins (not gating until the owner rules) on top of policy (833 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 262d070384: no gate status change; g0c.clean_types -65.
