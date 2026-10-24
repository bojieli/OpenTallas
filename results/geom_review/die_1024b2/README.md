# GEOM-REVIEW die-level batch 2 (2026-10-24 13:05 PDT) — Codex candidates 08:50-12:04

Method as batch 1 (`../die_1024/README.md`): candidate's own `check.py --completeness` + `tools/geom_review/plan_review.py`.

| die | plan sha | G0C | verdict | key change vs reviewed predecessor |
|---|---|---|---|---|
| S81 26-slot frame FT ledger (codex/s81-integrate-1024 51ae2e4cef, WIP) | e33b4208 | FAIL 91 (= main hard_cores) | PASS-COND | stations in ROM macros 72 -> 0 (explicit bit sites); 72 lanes +3..15 cyc; needs canonical regen + latency receipt |
| S81 xdie reserve-PHY rebased (fe3d259091) | 14ae25e6 | FAIL 91 (census regression 108 fixed) | PASS-COND | still on FT405 not the ledger: 72 in-ROM stations remain |
| KV reach405 (codex/kv-hub-1024 6dd64015fd) | f36ead41 | PASS 49/49 | PASS-COND | stations in cores 1,394 -> 8; hub_Ei hops <= ~300 um; 117 lanes +1..4 cyc |
| HBM B2l (main 9c5104bfcc50) | e1c50d83 | PASS 49/49 | PASS-COND | q_sm channels, q_hub core links >2 mm 66% -> 13%, root crossing band; batch-1 G3 blocks lifted at plan level, RTL relay binding pending; clock root on a macro |

Images: `img/<die>/` (die_cores, die_wire, zooms, review.json).
