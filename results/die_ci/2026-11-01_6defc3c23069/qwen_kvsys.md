# DIE-CI qwen_kvsys @ 6defc3c230 — FAIL

plan `physical/die_plan/qwen_kvsys/die_plan.json` digest `6997c898d04061a0`; run 11593.3 s

| gate | status | key numbers |
|---|---|---|
| g0 | FAIL | 22 err, 1536 warn; 40 types / 160 parts; worst cut 0.184 |
| g0c | FAIL | 22 err {'core_pin_form': 7, 'hops': 1, 'stations': 1, 'cuts': 13}; 2/40 types clean |
| xdie | PASS | in-die 0 err; no rack system |
| g2 | FAIL | 6 probes, overflow 0, no-access 0 |
| census | PASS | dropped 0 bits, unmapped 0, inter 396969 bits |
| latency | FAIL | 2416 lanes; table no latency table carries the current plan digest (stale table) |
| sta | NOT RUN (die STA exit 1; /srv/opentallas-scratch2/claude/die-ci/results/die_ci/2026-11-01_6defc3c23069/work/qwen_kvsys/sta/die_ci_sta.log) | 4/3939 seam ports measured; worst seam (gate, TT/FF policy) setup@TT - ps, hold@FF - ps; stand-in 0 / 80 ps. INFO margined: - / - ps (- neg groups), stand-in -84.8 / 17.4 ps |

INFO margins (not gating until the owner rules) on top of policy (833 ps, 60/25 ps unc): crosstalk 30.76 ps setup / 20.76 ps hold per seam (L 60.0 um); cell derate late 1.1037 (OCV x IR 1.0511) / early 0.95; IR stated (PDNSim: NOT RUN: no die-level PDN database (plan pg.grid only)).

Delta vs 262d070384: no gate status change; g0.errors +9, g0c.errors +9, g0c.clean_types -38.
