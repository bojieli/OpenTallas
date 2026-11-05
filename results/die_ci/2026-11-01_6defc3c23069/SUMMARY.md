# DIE-CI 2026-11-01 main 6defc3c230 (nightly) — FAIL

host tolerant-swine, 236254.4 s; previous run 262d07038412ff7193d73264d55b88380b244f25

| die | verdict | G0 | G0C | xdie | G2 | census | latency | die STA gate (TT setup / FF hold ps) | INFO margined (setup / hold ps) |
|---|---|---|---|---|---|---|---|---|---|
| s81 | FAIL | FAIL | FAIL (12) | PASS (0) | FAIL | PASS | FAIL | NOT RUN (- / -) | - / - |
| s81_head | FAIL | PASS | PASS (0) | PASS (0) | PASS | N/A | FAIL | NOT RUN (- / -) | - / - |
| qwen_compute | FAIL | PASS | PASS (0) | PASS (0) | FAIL | PASS | PASS | NOT RUN (- / -) | - / - |
| qwen_kvsys | FAIL | FAIL | FAIL (22) | PASS (0) | FAIL | PASS | FAIL | NOT RUN (- / -) | - / - |
| hbm | ERROR | - | - (-) | - (-) | - | - | - | - (- / -) | - / - |

Per-die detail: `<die>.md` / `<die>.json`. Gates: G0 and G0C from one check.py --completeness run; xdie = PLAN-TOOL5 in-die rules + xdie_io.py rack pairing; G2 = g2.py die + 5 worst partitions; die STA = die_sta.py ILM sub-top, GATED at the AGENTS.md policy (TT setup / FF hold, 60/25 ps); DIE-CI margins (crosstalk, OCV, IR) are an INFO column until the owner rules on them.
