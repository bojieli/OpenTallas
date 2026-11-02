# DIE-CI 2026-10-27 main 262d070384 (nightly) — FAIL

host dear-crayfish, 604438.6 s; previous run 9f6cbf0662335aa1380e17234c3e500f2d323bdd

| die | verdict | G0 | G0C | xdie | G2 | census | latency | die STA gate (TT setup / FF hold ps) | INFO margined (setup / hold ps) |
|---|---|---|---|---|---|---|---|---|---|
| s81 | FAIL | FAIL | FAIL (13) | PASS (0) | FAIL | PASS | FAIL | NOT RUN (- / -) | - / - |
| s81_head | INCOMPLETE | PASS | PASS (0) | PASS (0) | PASS | N/A | PASS | NOT RUN (- / -) | - / - |
| qwen_compute | FAIL | PASS | PASS (0) | PASS (0) | FAIL | PASS | PASS | NOT RUN (- / -) | - / - |
| qwen_kvsys | FAIL | FAIL | FAIL (13) | PASS (0) | FAIL | PASS | FAIL | NOT RUN (- / -) | - / - |
| hbm | FAIL | FAIL | FAIL (7712) | FAIL (202) | PASS | N/A | FAIL | NOT RUN (- / -) | - / - |

Per-die detail: `<die>.md` / `<die>.json`. Gates: G0 and G0C from one check.py --completeness run; xdie = PLAN-TOOL5 in-die rules + xdie_io.py rack pairing; G2 = g2.py die + 5 worst partitions; die STA = die_sta.py ILM sub-top, GATED at the AGENTS.md policy (TT setup / FF hold, 60/25 ps); DIE-CI margins (crosstalk, OCV, IR) are an INFO column until the owner rules on them.
