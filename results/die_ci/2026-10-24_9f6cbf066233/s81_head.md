# DIE-CI s81_head @ 9f6cbf0662 — FAIL

plan `physical/die_plan/s81_head/die_plan.json` digest `512bce22a6c7d250`; run 302.8 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 4 warn; 16 types / 326 parts; worst cut 0.0254 |
| g0c | PASS | 0 err ; 16/16 types clean |
| xdie | FAIL | in-die 0 err; s81: FAIL (130 err / 2868 circ) |
| g2 | PASS | 6 probes, overflow 0, no-access 0 |
| census | N/A (census none: top-down plan of a new die: no bound as-built head-die netlist in this partitioning (the bottom-up H10 die chain used a ) | dropped - bits, unmapped -, inter - bits |
| latency | PASS | 325 lanes; table physical/die_plan/s81_head/lat/s81_head_latency.json |
| sta | NOT RUN (tools/die_plan/die_sta.py not on this sha: lane DIE-STA claude/die-sta-1024) | 0/425 seam ports measured; worst seam setup@TT - ps (policy -), hold@FF - ps (policy -); stand-in worst -79.6 / -22.6 ps |

Margins on top of policy (833.333 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 9d2065c7a2: latency FAIL -> PASS; no metric change.
