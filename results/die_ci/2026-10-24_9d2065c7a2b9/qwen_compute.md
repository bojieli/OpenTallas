# DIE-CI qwen_compute @ 9d2065c7a2 — FAIL

plan `physical/die_plan/qwen_compute/die_plan.json` digest `8fd32979888311a1`; run 2824.0 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 88 warn; 56 types / 377 parts; worst cut 0.2218 |
| g0c | FAIL | 4 err {'ft_budget': 4}; 52/56 types clean |
| xdie | FAIL | in-die 4 err; no rack system |
| g2 | PASS | 6 probes, overflow 0, no-access 0 |
| census | PASS | dropped 0 bits, unmapped 0, inter 706998 bits |
| latency | PASS | 2015 lanes; table physical/die_plan/qwen_compute/qwen_compute_latency.json |
| sta | NOT RUN (tools/die_plan/die_sta.py not on this sha: lane DIE-STA claude/die-sta-1024) | 0/3002 seam ports measured; worst seam setup@SS - ps (policy -), hold@FF - ps (policy -); stand-in worst -106.5 / -24.4 ps |

Margins on top of policy (833.333 ps, 60/25 ps unc): crosstalk 49.44 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1107 (OCV x IR 1.0578) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta: no previous run.
