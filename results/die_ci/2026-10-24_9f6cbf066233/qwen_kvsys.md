# DIE-CI qwen_kvsys @ 9f6cbf0662 — FAIL

plan `physical/die_plan/qwen_kvsys/die_plan.json` digest `de8ae38fc37a11b7`; run 8633.1 s

| gate | status | key numbers |
|---|---|---|
| g0 | PASS | 0 err, 1788 warn; 49 types / 160 parts; worst cut 0.0714 |
| g0c | PASS | 0 err ; 49/49 types clean |
| xdie | PASS | in-die 0 err; no rack system |
| g2 | PASS | 6 probes, overflow 0, no-access 0 |
| census | PASS | dropped 0 bits, unmapped 0, inter 396969 bits |
| latency | FAIL | 2416 lanes; table no latency table carries the current plan digest (stale table) |
| sta | NOT RUN (tools/die_plan/die_sta.py not on this sha: lane DIE-STA claude/die-sta-1024) | 4/3939 seam ports measured; worst seam setup@TT - ps (policy -), hold@FF - ps (policy -); stand-in worst -79.6 / -22.6 ps |

Margins on top of policy (833.333 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 9d2065c7a2: g2 FAIL -> PASS; no metric change.
