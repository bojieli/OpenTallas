# Die-region detailed route pilot (2026-10-12): GRT-vs-DRT error bar

Tool: `tools/die_region_drt/region_drt.py` (pick / stage / cut / spef / compare; see its README). Windows are cut from
the die's own GRT checkpoint; instances inside a window are kept as fixed abstracts, instances crossing the edge are
*intruders* (their in-window body becomes OBS on their OBS layers, their in-window pins become fixed terminals), and the
die nets are detail-routed on the clipped die guides under the layer contract (die nets M4-M9, over a block body only
M8/M9). Runs: EPYC1tb `/srv/opentallas-scratch/claude/region-drt/{kv,s81}/<window>/`.

**Status: INTERIM.** The 64-iteration DRT runs have not finished. Numbers below come from the DRT logs at the stated iteration.

## Qwen KV die (die_kvi1b GRT, overflow 0)

| window (um) | kept / intruder pins | nets (internal / boundary) | DRC iter 0 | latest | dominant class |
|---|---|---|---|---|---|
| column [3500,21900,4100,22500] | 23 / 1,608 | 13,229 (3,189 / 10,040) | 37,472 | 9,344 (iter 1) | M8 Short 2,454 + M8 Min Step 1,404 |
| cong [4650,14950,5250,15550] | 10 / 8,955 | 9,288 (1,863 / 7,425) | 22,241 | 10,557 (iter 1) | M8 Short 5,863 + M8 Min Step 1,178 |
| relay [1107.6,5931.6,1983.6,6807.6] | 9 / 4,015 | 7,300 (4,236 / 3,064) | 30,488 | 7,548 (iter 1) | M8 Short 2,458 + M8 Min Step 1,188 |
| ioedge [7236.9,18066,8370.4,18666] | 0 / 8,158 | 4,396 (3,775 / 621) | 58,224 | 17,738 (iter 3, flat since iter 1) | M8 Short 3,584, eolKeepOut M5-M7 6,193, CutSpcTbl V4-V6 1,730 |

Above-only pin-access audit: 0 blocked pins in every window. Pre-route cut flags: relay 225 projected + 581 no-track
boundary crossings, cong 60 no-track.

Reading so far: the die GRT (overflow 0) is not a detailed-routable plan in these windows. In every window, M8 holds most of the
violations (Short + Min Step), on the one horizontal layer that crosses block bodies. The count stops falling after
iteration 1. This points to a systematic cause (M8 die PDN / intruder OBS / M8 track supply over blocks) and not to
local congestion. One-iteration diagnostic runs with per-iteration DRC reports (`kv/diag_{cong,relay}`) will give the
colliding objects. The cut semantics are fixed or the cause is recorded as the error bar only after that.

## S81 (c199b1 GRT, 458,253 overflow / 2,036 overflow gcells)

Window cong [7000,1200,7600,1800]: 19,373 nets (6,865 internal / 12,508 boundary), 2,234 no-track crossings. The first
DRT never started (docker rc 125: its container name collided with the KV cong run). Relaunched 07:05 PDT. With a
GRT already overflowing at die level, this window is expected to give a large DRC count. The overflow comes first.

## Pass / record per window
DRC total + classes (`drt_drc.rpt`), WL DRT/GRT ratio + per-net p95, via ratio, layer_contract violations 0, STA TT
setup / FF hold on GRT SPEF vs RCX SPEF for internal nets (`compare.json`).
