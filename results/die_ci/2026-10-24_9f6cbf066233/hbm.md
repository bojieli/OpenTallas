# DIE-CI hbm @ 9f6cbf0662 — FAIL

plan `physical/die_plan/hbm/die_plan.json` digest `21c9f0d3bb2000b9`; run 7505.5 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 516 warn; 60 types / 187 parts; worst cut 0.1447 |
| g0c | FAIL | 121 err {'core_faces': 110, 'die_io_plan': 10, 'ft_budget': 1}; 34/60 types clean |
| xdie | FAIL | in-die 11 err; hbm-ds: FAIL (961 err / 0 circ) |
| g2 | FAIL | 6 probes, overflow 0, no-access 0 |
| census | PASS | dropped 0 bits, unmapped 0, inter 506326 bits |
| latency | FAIL | 5483 lanes; table no <die>_latency.json in the plan dir (gen.py latency never written for this plan) |
| sta | NOT RUN (tools/die_plan/die_sta.py not on this sha: lane DIE-STA claude/die-sta-1024) | 0/12158 seam ports measured; worst seam setup@TT - ps (policy -), hold@FF - ps (policy -); stand-in worst -79.6 / -22.6 ps |

Margins on top of policy (833.333 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 9d2065c7a2: no gate status change; no metric change.
