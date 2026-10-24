# DIE-CI 2026-10-24 main 9f6cbf0662 (commit) — FAIL

host tolerant-swine, 8634.1 s; previous run 9d2065c7a2b91a378a9712037f27125d6e0a1844

| die | verdict | G0 | G0C | xdie | G2 | census | latency | die STA (worst final setup / hold ps) |
|---|---|---|---|---|---|---|---|---|
| s81 | FAIL | PASS | FAIL (91) | FAIL (130) | PASS | PASS | PASS | NOT RUN (- / -) |
| s81_head | FAIL | PASS | PASS (0) | FAIL (130) | PASS | N/A | PASS | NOT RUN (- / -) |
| qwen_compute | FAIL | PASS | FAIL (4) | FAIL (4) | PASS | PASS | PASS | NOT RUN (- / -) |
| qwen_kvsys | FAIL | PASS | PASS (0) | PASS (0) | PASS | PASS | FAIL | NOT RUN (- / -) |
| hbm | FAIL | PASS | FAIL (121) | FAIL (972) | FAIL | PASS | FAIL | NOT RUN (- / -) |
| hbm_arch_B2 | NOT PRESENT (plan not on this sha) | | | | | | | |

Per-die detail: `<die>.md` / `<die>.json`. Gates: G0 and G0C from one check.py --completeness run; xdie = PLAN-TOOL5 in-die rules + xdie_io.py rack pairing; G2 = g2.py die + 5 worst partitions; die STA = die_sta.py ILM sub-top with DIE-CI margins (crosstalk, OCV, IR) on top of the AGENTS.md policy.
