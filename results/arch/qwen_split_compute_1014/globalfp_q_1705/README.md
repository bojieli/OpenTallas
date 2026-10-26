# GLOBAL-FP-Q Qwen compute-die placement fpq_s6 (2026-10-15 19:00 PT, not qualified)

Homes for Q-COMPUTE-DIE: `fpq_s6-homes-pins.json` (all 1640 homes, moves, TRAIN_EDGES, comparison). The source
graph is Codex's `upper-specialized-routing-capacity-source.json` (model 7772f6e2: train24 + parallel VM write-back).
Pins stay on the source masters (whole-block x8.64 um translations, orientations kept; 3,581,024 pin-phase checks pass).

Same 62.5 um actual-layer grid model for every row. Timing-driven route = ME hops held inside their pin-pair 500 um stage bound:

| placement | worst cut | ME pin-pair | ME routed | stage cyc/AR token |
|---|---|---|---|---|
| selected C21sa (wide27 bodies) | 2.828 (0.792 if ME may detour, ME 252) | 134 | 137 | 29,729 |
| Codex seqwest | 6.105 (0.576 if ME may detour, ME 227-296) | 125 | 129 | 27,993 |
| fpq_s6 | **0.576** | 126 | **131** | 28,427 |

TRAIN_EDGES (te-fpq_s6.json): tag->issue 3, captures 37/26/25, fanout 24/12/16 -> TRAIN_EDGES 11 with fanout pads 1/0/5.
Tools in tools/ depend on the recovered gfp_core under artifacts/globalfp/qwen/recovery-1325 (Codex). Ideal geometry only:
no GRT/STA, no relay-frame legality, measured reach and clocks open.
