# Qwen3-8B TP8 split: unit reuse and compute-die sizing (Q-REUSE, 2026-10-15)

This study answers the owner's question: can Qwen reuse compute units, the way the HBM design did? It also produces the 19:50 sizing points (the "S81 treatment").

Tool: `tools/qwen_reuse/reuse_1015.py`. Data: `reuse.json`. No new RTL or physical run was made.

How each number is graded:
- **measured:** an RTL bench or closed view.
- **derived:** arithmetic on the shipped TP8 programme shape.
- **model:** a composition or floorplan screen.

Bases:
- Ledger composition (`accepted_cost.py` qwen_rom): 249,431 cycles = 4,810.9 tok/s.
- TP8 A_central (the split design): 214,074 cycles = 5,605.5 tok/s.
- Owner target B4 central: 5,839.5 tok/s.

## 1. Busy fraction per unit (AR, batch 1, T=8192)

| unit | busy | grade |
|---|---|---|
| 768 `qfd_tile_nk` MAC lanes (49,152) | **8.0 %** (20,032 stream cycles/token) | derived; each weight is read once per token |
| ROM read | 8.0 % per tile port, 1.6 % per macro | derived |
| matvec windows (go to last capture) | 21.3 % | measured windows (1,432 cycles/layer); MACs are active for 36 % of each window |
| spine SU lanes | 5.8 % of windows, 3.3 % lane-active | model / derived |
| SFU exp/rcp, SFU rsqrt | 0.35 %, 0.1 % | derived |
| VM (SU traffic + result write face) | 13 % | measured captures + model |
| result serializers (3) | 7.4 % | measured captures + model |
| collective window | 30.3 % (latency-bound) | measured |
| SerDes payload | 1.9 % | derived |
| UCIe peer payload | 5.5 % | derived |
| D2D link to the KV die | 0.6 % | derived |
| KV-die attention, at price | 26 % | priced |
| KV-die attention, measured | 51 % of a 377k-cycle token | measured |

Inside the measured 5,362-cycle attention service at T=8192:
- The 128 QK row engines are busy only about 258 cycles (**4.8 %**).
- The two PV pairs are busy 4,686 cycles (87 %). They take one V row per cycle each, which is the 2.95x.

Batch-2 and DFlash have no TP8 composition. Modelled:
- **Batch 2:** 3,584 tok/s per user and 7,168 aggregate, with MACs 12 % busy.
- **DFlash block 5:** verify needs 5 x 20,032 = 100,160 MAC cycles per step. Every MAC cut multiplies its penalty by the block size.

## 2. Area

**Compute die, 840.7 mm²:**
- **Tile field:** 768 slots = 497.9 mm² (59 %). It holds 58.9 mm² of ROM macros, 55.7 mm² of MAC lanes (8 `lsl_fp1` per tile) and 18.3 mm² of rpair logic and node. The children fill only **26.7 %** of the tile slot.
- **The tile height sets the die height:** 5 rpair rows + 4 lsl rows per tile, 16 rows, 25.94 of the 26.0 mm reticle.
- **Small slots:** SU 11.9 mm² (22 % filled), VM 10.4, serializers 1.2, SerDes 12.0, UCIe IO 10.0.

**KV die, 265.5 mm²:**
- 128 `qkd_rhead` slots = 68.1 mm² (22.2 mm² of cells).
- ECTL 1.2 mm².
- AHUB 0.13 mm².
- PV slices 0.65 mm².

## 3. Reuse options, ranked

| # | option | area | tok/s effect | risk | verdict |
|---|---|---|---|---|---|
| R1 | **PV on the 128 QK row engines (HBM-SM style).** V rows come back on the K ports into a 2-SRAM V buffer per rhead. The rhead's own multipliers and ktree compute 64-long p·v dot products. The AHUB trees reduce the partials. The PV pairs, vrow and the 4 V ports are removed. | KV die cells +0.63 mm² net. The alternative, 4-8x dedicated PV pairs, costs +1.9 to 4.5 mm² and still misses price. | service ~860 cycles (model) vs 5,362. This removes the 33.85 % proposed ATTN.NATIVE loss: ~1,315 with the link, under the 1,816 price. | medium: re-close 128 rheads; PV summation becomes tree order, so the golden must adopt it; p is rounded to the q operand format | **RECOMMENDED → Q-ATTN-RATE** |
| R2 | **48 MAC per tile** (6 lsl, 3 ROM macros per 2 cycles) | −60.8 mm² per compute die with a 2x row gap; −83.2 at today's gap | +6,967 cycles/token (stream +6,677, pin-register +290) = **2.72 %** | medium-high: tile ctl K-split, compiler ROM re-image. The tile parent is not closed yet, so now is the cheapest time | **RECOMMENDED sizing** |
| R1b | 64 QK row engines, each serving 2 PCs (only after R1 measures) | −34 mm² of KV die slots (−12.8 %) | about 0 vs price (est. ~1,635 with the link, vs 1,816) | medium | conditional |
| R2-min | 32 MAC per tile | −144 to −166 mm² | +20,322 cycles = 7.5 % | high | reject unless the owner grants an exception |
| R5 | SU: rsqrt 64 → 4, exp/rcp 64 → 32 | 1.1 mm² of cells; the die does not shrink | 0.40 % | low | optional |
| R6 | Attention on the compute-die tiles (PC11 VM-weight mode) | – | KV is 2 MiB per layer over a 64 B/cycle link: +32.8k cycles per layer | – | reject |
| R7 | Softmax on the compute-die SU | – | scores out and probabilities back over the link: +4k cycles per layer | – | reject |
| R8 | One shared serializer | 0.8 | measured +1,297 cycles per layer = 15.8 % | – | reject |
| R9 | Fewer SerDes | 4.0 | measured relay +339 per all-reduce = 8.9 % | – | reject |

**Why the HBM trick does not transfer to the compute die.** The HBM SMs sit next to the KV. Qwen's matrix tiles are a die away from it, and the link moves 64 B per cycle. The HBM lesson applies inside the KV die (R1). On the compute die, the matching move is fewer MAC lanes (R2).

## 4. Sizing points (owner 19:50: fewer multipliers vs TP10/TP12)

**Verdict: the tiles are oversized for the rate target, so use fewer multipliers per tile at TP8.**
- The MACs are 8 % busy and the token is latency-bound: all-reduce 2,100, attention, and tree/relay latency per layer.
- TP10/TP12 leave the per-die stream unchanged at 512 words per layer, so tok/s does not improve.
- 32 Q / 8 KV heads do not split over 10 or 12, so KV heads would be replicated.
- The all-reduce loses the K4 two-level fold.
- Total silicon would be 9,987 / 11,124 mm², against 8,850 mm² today.

| point | MAC/tile | tile (µm) | row gap | die (mm) | die mm² | tile fill | tok/s vs B4 5,839.5 (A_central 5,605.5) | ledger | total silicon (8 + 8 KV dies) |
|---|---|---|---|---|---|---|---|---|---|
| minimal | 32 | 449.28 x 1,122.08 | 86.4 | 32.41 x 21.50 | 696.7 | 27.1 % | 5,314 (5,120) | 7.5 % | 7,698 |
| **recommended** | **48** | 449.28 x 1,282.48 | **86.4** | 32.41 x 24.06 | **779.9** | 26.9 % | **5,648 (5,429)** | **2.7 %** | **8,363** |
| generous | 48 | 449.28 x 1,282.48 | 172.8 | 32.41 x 25.44 | 824.7 | 26.9 % | 5,648 (5,429) | 2.7 % | 8,722 |
| today | 64 | 449.28 x 1,442.88 | 43.2 (fixed) | 32.41 x 25.94 | 840.7 | 26.7 % | 5,839.5 (5,605.5) | 0 | 8,850 |

Assumptions in this table:
- The column corridor stays at 73.0 µm, because the reticle width has only 587 µm spare.
- The pin-register rule is charged at +2 cycles per matvec op (145 ops per token).
- Tile fill stays at about 27 % at every point. The whitespace comes from the 20-µm channel rule and the pin-bound tile control. Reaching ~60 % block utilisation needs a tile re-pack: for example, rpair rows at 45 % utilisation and the ctl/TX column. Removing MACs does not get there.
- The spine stack (about 14 mm) still fits at 21.5 mm.
