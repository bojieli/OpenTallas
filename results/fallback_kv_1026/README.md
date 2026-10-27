# FALLBACK-KV 2026-10-26: bottom-up landed fallback on qwen_kvsys (8 clock regions)

Lane FALLBACK-KV (owner 10-26 16:5x: the fallback runs in parallel with the master plan; the first to pass the die
freeze gate wins). Tool: `tools/die_plan/fallback_land.py` (plan / gate). All numbers are UNCHECKED unless marked.

## Seam classes (structural: region boxes, partition type, bus role; none chosen from slacks)
Clock = g32x64 12.8 by-construction build (path-kv-c128-1026), 8 dataflow regions h000..h111 (spec_c3 cuts), each
region one subtree with its own CPPR root. Plan = codex-kv-mesh-1026/plan.json (160 parts, 3915 ports).

| class | rule | plan ports / bits | die_sta seams |
|---|---|---|---|
| region (landed) | partitions in different regions (= die_clock_mesh landed_crossings.json, 0 mismatch) | 662 / 77,938 | 726 (678 data + 48 reset/start) |
| phy (landed) | one side kv3_phy* (regional PHY registers) | 346 / 80,026 | 378 |
| ctl (landed, boot only) | reset/start wavefront hop (arst_n, start_i), same region | not plan ports | 190 |
| related | everything else, one region tree | 2,907 / 441,147 | 2,907 |

Of the 2,280 FF-hold-failing seams on g32x64 (40-ps stand-in), 406 cross regions (worst -278.5) and 1,874 are same-region
(worst -95.3). So landing the cross-region seams removes the worst numbers, not most of the count.

## Cycles and tok/s (kv_v39r_price.py unchanged, lane delta = K per landed hop)
Per attention request +16 (K=2) / +24 (K=3) cycles (d2d rx bundle 4 crossings + attn tx 4); embed +20 / +30 per token.
Qwen ROM (KV side, 4,810.9 tok/s base): K=2 -0.24 % priced / -0.44 % upper; K=3 (as-built ring contract +3) -0.36 % / -0.66 %.
PHY hops are not in the priced lane classes: adding one serial PHY->PC + PC->PHY hop per request (+2K x 36) gives an
upper bound of -0.50 % (K=2) / -0.74 % (K=3). QC is unchanged (master-plan path). Qwen ledger 1.47 accepted + 7.12
proposed + 0.74 = 9.3 % < 15 % cap: NO cap break.

## Fallback gate on the existing g32x64 runs (die_sta flat, stand-ins, no CPPR credit) -- `gate_w40.json`, `gate_w80.json`
| | stand-in run (BHOLD 40) | plan contract W=80 (MODEL-SHIFT +40 of the same run) |
|---|---|---|
| related TT setup | +545.4 | +545.4 |
| related FF hold | -57.8 (1,604 seams) | -17.8 (5 seams: pc_WS_6->pc_WS_5 x3 -17.8, pv_N_1->pv_N_0 x2 -4.7) |
| landed window (die_sta_related, clock-kv-r1 base_g32x64_rel) | TT damage 390.4 / 416.7 margin 26.3, FF 323.6 margin 93.1 PASS | same |
| intra-partition | NOT RUN (intra-pairs 0) | rerun live |
| verdict | FAIL | FAIL (5 seams + intra not run + stand-ins) |

The landed set leaves 5 related seams at W=80. They are same-region neighbours on different subtrees (skew 54.8 / 44.4 ps).
Intra-partition tap spread FF is > 80 ps in 11 partitions (sys_c 157, hub_C 136, pv_S_4..7 102-109, pc_EN_1 109,
hg_EN_1 100). Landing does not touch it, so per-partition single-root CTS (kit rebuild) or the 12.8 tree is needed there.

## Live (collect, do not rerun): W=80 stand-ins + --intra-pairs 200, one corner per dir
epyc1 /srv/opentallas-scratch2/claude/fallback-kv-1026/sta_w80_{FF,TT}/die_sta.json (sta.sh, started 16:58, ~1-1.5 h).
Then: `fallback_land.py gate fallback_k3.json --sta FF=.. --sta TT=.. --rel FF=.. --rel TT=.. --run-bhold-ps 80 --standins`.

Files: fallback_k{2,3}.json (classes, landed ports, lane map), kv_fb_k{2,3}[_price].json, gate_w{40,80}.json,
fallback_regions.png (viewed), render_fallback.py, region_land_price.py.
