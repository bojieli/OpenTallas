# S81: trading ROM for hub room (S-ROMTRADE, 2026-10-15)

Owner direction 18:55: the array gets more dies with fewer ROM pairs on each, so the hub has real room. The hub must hold A2 VM, SU, the capture group, collective, MIX4 and HC side by side, keep at least 20 % whitespace, keep every road and local cut at or below 0.50, and add no relay stages. The coordinator's 19:0x decision adds +3.6 mm² of f6/f8 station outlines to every die. That area is in the budget below: 1.3 mm² inside the hub, and 2.3 mm² of `stnv_566x1` on the streets.

Tool: `tools/s81/rom_trade.py` (`breakdown`, `geometry`, `summarise`). Data: `rom_trade.json`. Each point has its allocator stage map in `alloc/p<pairs>s<stages>/`. The stage counts come from the real allocator, `tools/dsrom_s73_pair1.py --stages S --pairs P --bf B`. It places every decoder matrix with 0 failures. It is a metadata model, not RTL. Geometry is a screen. Tok/s is derived. Power is modelled.

## 1. Where the area goes today (canonical full2417 capacity + GEN19b hard boxes)

| class | mm² | share of 858 |
|---|---:|---:|
| ROM field frames (128 roots, 2,417 pairs) | 538.6 | 62.8 % |
| field interframe channels and column slack | 99.9 | 11.6 % |
| field column gaps and the SW service street | 4.9 | 0.6 % |
| hub strip (5,987.5 µm between the fields × 26 mm) | 155.7 | 18.1 % |
| ↳ hub blocks inside it (old 1.54-mm VM slot) | 66.7 | 7.8 % |
| ↳ roads S14W / VCH / S14E and whitespace | 82.6 | 9.6 % |
| ↳ bank selector / collector | 6.3 | 0.7 % |
| IO (HBM PHY / ctrl / svc, 8 link stacks) | 29.8 | 3.5 % |
| HCP homes (north row) | 13.4 | 1.6 % |
| edges and corners | 15.6 | 1.8 % |

The ROM field takes about 75 % of the die and the hub strip about 18 %. With A2 (17.06 mm²) and the current blocks, the hub needs 88.4–89.9 mm² of blocks. That fits the 111.2-mm² hub interval by area alone. It does not fit in shape: the W-column stack is 246 µm too tall (a2_fit).

## 2. ROM slack that already exists

- **Seven of the 81 stages are empty.** The released binding fills only stages 0–73. Stages 74–80 (28 dies) hold just the 9 provider pairs of layers 37–39, at 0 to 9 pairs per die. The allocator reproduces the canonical map exactly. With the providers homed inside the matrix stages, the same 2,417-pair die needs **74 stages (296 layer dies)**.
- **Word fill is 77.6 %.** In the stages that hold matrices, 77.6 % of the logical words are used.
- **The frames waste one q lane.** The 19-pair frames leave one q lane empty. 20-pair frames in the same 22 columns give 2,509 pairs, which needs 70 stages.

## 3. Hub sizing: the columns to remove and the hub shape

Columns come off next to the hub, alternating W and E: W10, E11, W9, E12, W8, E13. Each column adds 1,191.5 µm of hub width. The 128 roots, and with them the mapping and return-tree regions, are kept and re-packed into the remaining columns, with the BF share kept at 21.5 %.

The hub order runs W→E: S14W, HC, capture column (capture/gather/PQ/WFC/sseq, then collective, then host), VM (MIX4 on its N face), SU, S14E. This mirrors today, so the collective stays at today's x and the K-link lengths do not change. The VM is centred at y 13 mm, so the farthest field return gets shorter by about 4.3 mm.

Roads are sized at 0.50 with option-C levers A, B, D and E. Return TDM is **not** used: it adds 2 stages on 12 paths, which the no-relay-growth rule forbids. That gives S14W ≥ 661.6 µm (6,977 tracks) and S14E ≥ 399 µm (4,207 tracks).

| point | columns removed | pairs / BF per die | hub content width | SU outline | HC | S14W / S14E cut | hub whitespace |
|---|---|---|---:|---|---|---|---:|
| minimal | 3 (W10 E11 W9) | 2,316 / 498 | 8,500 µm | 1,586 × 12,768 (reshape) | tower | 0.50 / 0.50 | 52 % |
| **recommended** | 4 (+E12) | 2,176 / 468 | 9,066 µm | 1,935 × 10,463 (closure a) | tower, 216-µm channel to the capture column | 0.50 / 0.19 | 55 % |
| generous | 6 (+W8 E13) | 1,904 / 410 | 10,882 µm | 1,935 × 10,463 | HC_t and HC_s side by side (corridor gone) | 0.50 / 0.13 | 63 % |
| compact_L (alternative) | 5, then roots go back above the hub | 2,421 / 521 | 10,666 µm × 10,463 µm tier | 1,935 × 10,463 | side by side | 0.50 / 0.32 | 21 % |

Relay-stage check, using the edge-to-edge gap at 500 µm per stage, today → new:

| bus | stages today → new |
|---|---|
| SU–VM, capture–VM, capture–gather | 0 → 0 |
| MIX4–VM | 2 → 0 |
| collective–VM | 3 → 0 |
| collective–HC_s | 4 → 0 or 1 |
| HC_s–VM | 4 → 4 |
| HC_t–HC_s | 2 → 2 (0 in generous) |

No relay stages grow. Vertical fit: every point fits the 21,822-µm hub interval, and the HC tower is the tallest part at 19,974 µm.

Still open: the VM-internal cut of 2.17 belongs to S-VM. Native pins, PG, CTS and station homes are not modelled.

## 4. Array, re-cut placement and per-user rates

Every row uses the real allocator. "today" is the 81-stage binding. Tok/s takes today's report headline (AR 1,447.7 / MTP 4,238.4 at τ 4.159) as the 81-stage array. Only the stage-hop change is applied, at 0.8384 µs per stage: the measured full-KP4 hop plus the mean rack flight. Per-layer compute is unchanged, because the pairs per layer do not change.

| point | stages (matrix) | layer / total dies | stacks | AR tok/s | **MTP tok/s per user** | chips kW | silicon (dies + stacks) |
|---|---:|---:|---:|---:|---:|---:|---:|
| today (81-stage binding) | 81 (74) | 324 / 376 | 476 | 1,447.7 | 4,238.4 | 33.1 | 841.0k mm² |
| today, re-cut | 74 | 296 / 348 | 448 | 1,460.1 | 4,263.9 | 30.6 | 786.5k |
| minimal | 74 | 296 / 348 | 448 | 1,460.1 | 4,263.9 | 30.0 | 786.5k |
| **recommended** | 82 | 328 / 380 | 480 | 1,445.9 | 4,234.8 | 31.7 | 848.8k (+0.9 %) |
| generous | 96 | 384 / 436 | 536 | 1,421.8 | 4,184.8 | 33.9 | 957.8k (+13.9 %) |
| compact_L | 74 | 296 / 348 | 448 | 1,460.1 | 4,263.9 | 30.6 | 786.5k |

- **Every point stays above 3,000 MTP tok/s per user.** The worst case, generous, is 4,184.8 (−1.3 %).
- **The recommended stage 82 is a ragged tail.** It carries about 4 % of a stage. Trimming roughly 15 pairs of packing, or using 2,190 pairs per die, keeps the array at 81 stages.
- **Time balance.** The matrix issue cycles per stage are within +1.7 % (today) and +6.3 % (recommended) of the mean, because the byte cut already tracks time for the ROM. The hot die is the stage that holds layer 20's 1M index scan: 4.97 µs of reader time, modelled, on the scan-home die, which is stage 41 at 82 stages and stage 48 at 96. In every re-cut that stage now falls inside layer 20's own matrix stages. Balancing by time means giving that stage about 0.7 of a stage less ROM, which costs about one more stage: −0.8 µs, −0.1 % MTP. That improves II, the aggregate rate, not the per-user AR.
- **Basis note.** The per-user rates use today's report headline (120 stages on the old 1,792-pair HALF_PHL mapping) as the 81-stage die, with hop-only shifts. Anchored instead on three_machine_compose (85 stages), the same points give MTP between 4,653 and 4,752.

## 5. Comparison with the other plans

- **In-reticle closure (a)** (c22a, su_s reshape): it changes no ROM and keeps 81 stages, but leaves 0 µm of height slack. The VM, SU and capture stay stacked. The cuts are 0.57 / 0.60 rather than 0.50, and they need return TDM: +2 stages on 12 paths, +0.34 % AR. It does not meet the 18:55 rules.
- **Multi-die hub split (B)**: it adds about 324 companion dies, about 21 Tb/s of SU↔VM D2D bandwidth per die, and new PHY RTL. It adds at least 8 µs per token (UCIe at 12 cycles per crossing, at least 2 crossings per field phase): ≥ +1.3 % AR before serialization. It is strictly worse than removing 3 or 4 columns.
- **Removing columns (this study)**: the minimal point is cheaper than today, because today's 7 empty stages absorb the loss. The recommended point costs +1 stage and +4 dies (+0.9 % silicon). The generous point costs +15 stages (+60 dies, −1.3 % MTP). compact_L keeps 2,421 pairs at 74 stages, but it needs a field-topology screen: roots above the hub must return straight down into the gather.
