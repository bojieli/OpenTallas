# Qwen3-8B ROM full die: b3r3..b3r12 global-route closure (2026-10-04)

Tool: `tools/qwen_rom_fulldie_b3r2.py` (default off). The final floorplan is b3r12:

```
python3 tools/qwen_rom_fulldie_b3r2.py {plan|grt|real|ir} --enable-b3r2 --b3r3 --b3r6 --tree-cols 6 \
    --bw-align --bw-edge --io-faces --bw-edge-inner [--iters 50] [--window tile_field|spine_hub|shoreline_w]
```

The GRT, legality and IR runs used the ORFS `openroad/orfs:asap7lock` image on the local host (`/home/ubuntu/qfd-local/<case>`, runner `run_grt.sh`).
The runner launches each case with `openroad -threads 20` (GRT) or `-threads 8` (real, IR).

## Verdict

@@VERDICT@@

## What changed after b3r2b (54,584 overflow, worst window M8 1.31)

| step | change |
|---|---|
| b3r3 | Spine widened 500.256 µm. Each band half gets its own port and scale slab, so the scale ROM sits inside its port slab and the scale bus stays inside the slab. Central blocks are placed around the hub. The constant ROM sits beside SU64. |
| b3r4 | The hub north link moves to the E face, and the block-word pins are spread (the spread missed the band slabs, see b3r6). |
| b3r5 | Corridor pins at 2 tracks. |
| b3r6 | The band-slab block words are actually spread. b3r4 and b3r5 matched `qfd_sp_*`, but the band-slab masters are `qfd_port_tiles_*`. The channel buses (crom, seq) are face to face. |
| b3r7 | Tile tree-word pins spread over 6 gcell columns. |
| b3r8 | Slab block-word pins sit at the height of their block root. |
| b3r9 | East-array block trees mirrored. **Not kept:** M9 rose to 1.32. |
| b3r10 | Words of a slab whose roots lie outside it enter at the near edge, spread across the slab width. |
| b3r11 | The collective → SerDes word moves to the E/W faces. |
| **b3r12** | Edge-entry block words climb inside the slab, with the nearest-root word deepest. |

## Global route, k = 16, banded tree top

Overflow is the GRT final "Total Congestion" (gcell level). Use/cap is the worst 4 × 4-gcell window per layer (`gcell_usage.txt`).

| case | total | M4 | M5 | M6 | M7 | M8 | M9 | max use/cap M7 / M8 / M9 | windows > 1 (all layers) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| b3r2b_k16_banded_i5 (before) | 54,584 | 231 | 82 | 116 | 447 | 2,226 | 51,482 | 1.06 / 1.31 / 1.17 | — |
| b3r3_k16_banded_i5 | 62,182 | 84 | 38 | 42 | 221 | 687 | 61,110 | 1.076 / 1.125 / 1.103 | 140 |
| b3r4_k16_banded_i5 | 63,684 | 85 | 52 | 27 | 208 | 601 | 62,711 | 1.090 / 1.095 / 1.060 | 119 |
| b3r5_k16_banded_i5 | 20,399 | 81 | 41 | 30 | 205 | 682 | 19,360 | 1.104 / 1.098 / 1.095 | 122 |
| b3r6_k16_banded_i5 | 23,992 | 0 | 5 | 5 | 13 | 455 | 23,514 | 1.000 / 0.991 / 1.103 | 24 |
| b3r7_k16_banded_i5 | 10,445 | 0 | 8 | 9 | 13 | 1,402 | 9,013 | 1.007 / 0.991 / 1.103 | 28 |
| b3r8_k16_banded_i5 | 6,419 | 0 | 5 | 7 | 18 | 2,064 | 4,325 | 1.000 / 0.982 / 1.302 | 10 |
| b3r9_k16_banded_i5 (not kept) | 10,769 | 1 | 5 | 8 | 23 | 1,646 | 9,086 | 1.000 / 1.000 / 1.321 | 9 |
| b3r10_k16_banded_i5 | 6,130 | 0 | 7 | 9 | 19 | 1,944 | 4,151 | 1.000 / 0.982 / 1.036 | 4 |
| b3r11_k16_banded_i5 | 5,398 | 0 | 6 | 7 | 12 | 1,922 | 3,451 | 1.000 / 1.000 / 1.043 | 2 |
| **b3r12_k16_banded_i5** | **6,178** | 1 | 7 | 7 | 12 | 1,751 | 4,400 | **1.000 / 0.983 / 1.000** | **0** |
@@I50ROW@@

M2–M6 are at or below 1.000 in every b3r6+ run. Per-case records are in `grt/<case>/`:
- `summary.json`: per-layer overflow and windows;
- `final_congestion.txt`;
- `gcell_over_by_layer.txt`;
- `windows_over.txt`: every 4 × 4 window above 1;
- `times.txt`.

b3r6_i50 and b3r11_i50 were stopped once a later floorplan superseded them (`SUPERSEDED.txt` in the local case directory).

@@I50TEXT@@

## Area (`plan_b3r12/plan.json`)

- **Die.** 811.763 mm² (24,747.552 × 32,801.76 µm) against the 858 mm² reticle limit, a margin of 46.2 mm².
- **Growth.** +15.8 mm² over b3r2b (795.977 mm²), from the b3r3 spine widening (500.256 µm here, replacing b3r2b's 24 µm band widen).
- **FIFO slots (decision C).** 2.53 mm², unchanged.

## Added latency (`latency_b3r12.json`; unified model `qwen_tp_point(4, 6144, 'board', 1.2 GHz, SU64)`, base 179,782 cycles, 6,674.8 tok/s)

| term | floorplan | model | cycles/token | rate |
|---|---:|---:|---:|---:|
| Worst block word → tree top, stages at the 430.56 µm pitch (mean 37.6, min 15) | 64 | `QWEN_WIRE_W12.tws` = 30 | +7,378 | −3.94 % |
| Hub ↔ stack link stages (trunk 17.5 mm + fan 5.07 mm) | 53 | 46 | +504 | ≈ −0.28 % |
| F2 two-beat instruction (bound; 0 with prefetch) | +1 / ME op | 0 | +217 | −0.12 % |
| **Sum (bound)** | | | **+8,099** | **≈ −4.3 %** |

- **Block-word history.** b2 101, b3r2 117, b3r2b 68, b3r3..b3r12 64.
- **The term is the worst word, not the mean.** The ME-op reduction finishes only when the last word reaches the tree top.
- **Instruction for the model owner.** Set `QWEN_WIRE_W12["tws"] = 64` and the hub↔stack total to 53 stages, then re-run the Qwen ROM headline.
- **These are bounds.** The pitch is the corridor-gate SS link stage; a routed-path STA has not confirmed it.

## Physical checks at b3r12

**Legality and pin access** (`real_b3r12/run_filtered.log`; wall 7:39, 11.3 GB):
- OT_LEGAL: 3,225 instances, 0 overlaps, 0 outside.
- OT_MACRO_TRACK_ASSERT PASS: 5,792,788 pins, 0 off-track.
- pin_access: macroNoAp = 0, stdCellPinNoAp = 0.

**IR (PSM)** (`ir/ir_record.json`):
- Recipe: the b2/b3r2b PASS recipe (bump-aligned straps, every core bump power, 63.64 µm per-net pitch).
- Interior rule: cells at least one bump pitch from the window edge.
- The edge numbers (38 mV VSS) are window-boundary artefacts, the same as in b3r2b.

| window | interior rail to rail | budget | b3r2b |
|---|---:|---:|---:|
| tile field | 21.03 mV | 35 mV PASS | 21.03 |
| spine/hub | 26.46 mV | 35 mV PASS | 28.47 |
| shoreline W | 20.26 mV | 35 mV PASS | 20.26 |

## Open items (not route closure)

**The full-die pdngen at b3r2b produces shapes but fails connectivity** (ot-epyc1tb `cases/b3r2b_pdn/run_pdn_r2.log`, 2:57:46, 75 GB):
- `run_pdn_r2` gives OT_PDN PASS with 26.7 M special shapes.
- `check_power_grid` then fails with PSM-0069 on VDD and VSS. The reported causes are:
  - unconnected M4 VDD rails in the W band (x 20–853 µm);
  - more than 1,000 PDN-0182 grid-ownership conflicts, where a fragment slab and a tile are claimed by an earlier pattern grid.
- It has not been rerun at b3r12.

**The 64-stage block word is a latency cost, not a routing failure.** A re-pack that equalises word length (mean 37.6) would recover up to about 3 %.
