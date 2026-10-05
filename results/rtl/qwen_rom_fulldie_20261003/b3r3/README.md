# Qwen3-8B ROM full die: b3r3..b3r16 global-route closure (2026-10-04)

Tool: `tools/qwen_rom_fulldie_b3r2.py` (default off). The final floorplan is b3r16B40:

```
python3 tools/qwen_rom_fulldie_b3r2.py {plan|grt|real|ir|pdn|wire8k} --enable-b3r2 --b3r3 --b3r6 --tree-cols 6 \
    --bw-align --bw-edge --io-faces --bw-edge-inner --bw-sp 200 --m6-strip 40 [--iters 50] [--pdn-rev r5]
```

The b3r3–b3r14 GRT, legality and IR runs used the ORFS `openroad/orfs:asap7lock` image on the local host (`/home/ubuntu/qfd-local/<case>`, runner `run_grt.sh`).
The runner launches each case with `openroad -threads 20` (GRT) or `-threads 8` (real, IR).
After the owner's localhost rule, the b3r13 50-iteration runs went to ot-epyc1tb, and the b3r15/b3r16 runs to ot-pve1 and ot-agidock128 (`/home/ubuntu/claude-qwen-fulldie/cases`). Every job went through admit.sh and is registered.

## Verdict: CLOSED with Option B (b3r16B40). The 50-iteration final GRT reaches 0 overflow on every layer.

The final floorplan is b3r16B40: the b3r13 block-word pins (`--bw-sp 200`) plus a 40 µm M6 entry strip (`--m6-strip 40`).
- The strip runs inside the array-facing face of every band port/scale slab.
- Under the strip the slab keeps OBS M1–M5 only; elsewhere the slab still blocks M1–M7.
- The block-word pins sit on M6 inside the strip. Edge-entry words are stacked 100 µm apart into the slab.
- Option B closed first, so it is adopted.

**50-iteration final GRT** (k = 16; ot-pve1, image `openroad/orfs:latest` = sha 16470cea, identical to EPYC asap7lock):

| case | total overflow | M2–M9 overflow | worst 4 × 4 window, every layer | iterations used | wall / RSS |
|---|---:|---|---|---:|---|
| **b3r16B40_k16_banded_i50 (final)** | **0** | 0 on every layer | **≤ 1.000** (M2–M9), 0 windows over | 31 of 50 | 3:01 h / 12.3 GB |
| b3r16B80_k16_banded_i50 (80 µm strip) | 0 | 0 on every layer | ≤ 1.000, 0 windows over | 27 of 50 | 2:34 h / 12.3 GB |

GRT stopped its extra iterations early because overflow reached 0. Final congestion report: Total 127,977,517 resource, 14,950,946 demand (11.68 %), Max H/V 0/0, Total Congestion 0.

The 5-iteration runs before the 50-iteration finals:
- b3r16B40 i5: 4,199 overflow, all windows ≤ 1.000.
- b3r16B80 i5: 3,859 overflow, M9 window 1.035 (1 window).
- In both, the 50-iteration run then cleared the remaining gcell overflow. That contrasts with every M8-only-entry floorplan, where the 50-iteration run regressed.

**Option A was not adopted** (slab routed M1–M5, `--slab-obs-top 5`):
- b3r15A i5: 16,187 overflow, M8 1.47, M9 1.60. This is worse because freeing M6/M7 over the whole slab pulled through-traffic onto the slab faces.
- The port-group element P&R in its slab share fails with M5 routing, and also with the M7 control (`results/rtl/qwen_slab_m5_20261004/README.md`).
- b3r15B i5 (first B attempt) had a mis-sided strip: the face was taken from the mean pin x, so the edge-entry slabs got their strip on the wrong face. It is fixed in b3r16.

**Physical checks at the final floorplan.** The b3r16B40 die has the same instance placement as b3r12 and b3r13; only the slab abstracts differ.
- **Legality** (`real_b3r16B40/`): 0 overlaps, 0 outside, track assert PASS (5,792,788 pins), macroNoAp 0, stdCellPinNoAp 0. Wall 9:24, 11.4 GB.
- **Full-die PDN** (`pdn_fix/`, b3r13c placement, `--pdn-rev r5`):
  - The old b3r2b run had executed the r3 script. The r4 grids also matched several instances per `-instances` regexp (PDN-0182).
  - r5 anchors every instance pattern (`^name$`) and groups the macro grids by stripe phase.
  - Result: OT_PDN PASS (27,742,379 special shapes), **check_power_grid VDD PASS and VSS PASS** ("All shapes on net VDD/VSS are connected"), 0 PDN-0182 conflicts; 69 PDN-0195 via-removal warnings remain.
  - Wall 2:27 h, 109 GB.
- **IR** (`pdn_fix/ir_record.json`, b3r13c floorplan, same recipe), interior rail to rail: tile field 21.03 mV, spine/hub 26.46 mV, shoreline W 20.26 mV. All pass the 35 mV budget.
- **Area:** 811.763 mm², under the 858 mm² limit. The M6 strip adds no area.
- **Latency:** see below; the floorplan is unchanged, so the numbers hold. The bound is applied to the 8K composition in `wire_bound_8k.json`.

**Open items:**
- The slab element itself (port group + 16 scale ROM banks) does not route in its 0.2666 mm² share even at M7. The slab area needs to grow, or its content needs a re-split (`results/rtl/qwen_slab_m5_20261004/`). This is independent of the die route.
- Detailed routing and a routed-path STA of the die-level nets have not been run.

### History: why M8-only entry could not close
**Congestion is NOT closed under the owner's final criterion.**
- The 5-iteration route meets the window rule. At b3r12 (k = 16, 5 iterations) every layer's worst 4 × 4 window is at or below 1.000, with 0 windows over.
- The 50-iteration final GRT misses it. It regresses on every floorplan tried:
  - b3r12_i50: 14,149 overflow, worst M8 window 1.112, 10 windows over.
  - b3r13a–d_i50 (block-word pin spread and depth): 13,747–15,036 overflow, worst M8 window 1.107–1.268, 6–20 M8 windows over.
- **The cause is systematic.**
  - 6–12 of the over windows in each run sit in one gcell column: x = 11.4576 mm, the W spine slab face, next to the ends of the slabs.
  - The slab abstracts block M1–M7, so M8 is the only layer a block word can use to enter a slab horizontally.
  - FastRoute's extra iterations move the block-word entries onto that column, and on into the free spine space beside the slab ends.
  - b2 showed the same i5 → i50 rise (36.4k → 37.2k).
- **Rejected lever.** An empty routing gap between the array and the spine (b3r14, `--edge-gap` 37/74 µm) was tried and rejected. The router turns the gap into a vertical M9 highway, giving M9 windows of 1.22–1.51.
- **Next lever (needs an owner decision).** Give the slab entry a second horizontal layer. This means a port/scale slab abstract whose top routing obstruction is M5 (M6/M7 left free over the slab), which is an implementation claim to validate on a slab P&R. The alternative is a dedicated M6 entry channel along the inside of the slab face.
- Area, latency, legality and IR below are measured at the b3r12 floorplan. b3r13 changes only pin positions.

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
| b3r12_k16_banded_i50 (final, 50 it) | 14,149 | 0 | 0 | 1 | 1 | 9,456 | 4,691 | 1.000 / 1.112 / 1.018 | 11 |
| b3r13a (bw-sp 200) i5 / i50 | 4,982 / 13,747 | | | | | 1,677 / 9,410 | 3,281 / 4,332 | i5 1.000 / 0.973 / 0.991 (M6 1.014) ; i50 1.000 / 1.138 / 1.063 | 1 / 14 |
| b3r13b (bw-sp 300) i5 / i50 | 5,635 / 15,036 | | | | | 1,429 / 9,793 | 4,181 / 5,240 | i5 1.007 / 1.000 / 1.069 ; i50 1.000 / 1.107 / 1.086 | 6 / 36 |
| b3r13c (bw-sp 200, bw-x 80) i5 / i50 | 4,968 / 13,806 | | | | | 1,135 / 9,098 | 3,810 / 4,702 | i5 1.007 / 0.991 / 1.000 (M6 1.014) ; i50 1.000 / 1.268 / 1.060 (M5 1.005) | 2 / 23 |
| b3r13d (bw-sp 300, bw-x 80) i5 / i50 | 5,930 / 14,345 | | | | | 1,059 / 9,465 | 4,848 / 4,880 | i5 1.000 / 1.000 / 1.233 ; i50 1.000 / 1.138 / 1.121 | 14 / 11 |
| b3r14a–d (edge gap 37/74 µm, rejected) i5 | 8,718–11,196 | | | | | 1,530–2,294 | 6,935–9,078 | M9 1.22–1.51 | 88–157 |

M2–M6 are at or below 1.000 in every b3r6+ run. Per-case records are in `grt/<case>/`:
- `summary.json`: per-layer overflow and windows;
- `final_congestion.txt`;
- `gcell_over_by_layer.txt`;
- `windows_over.txt`: every 4 × 4 window above 1;
- `times.txt`.

b3r6_i50 and b3r11_i50 were stopped once a later floorplan superseded them (`SUPERSEDED.txt` in the local case directory).

The i50 runs took 3.8–5.3 h at about 12 GB. b3r13a_i50 and b3r13c_i50 were rerun on ot-epyc1tb (`*_i50r`) after the owner's localhost purge killed the local copies at iteration 43/44. b3r11_i50r was OOM-killed on EPYC at iteration 40 and is not recorded.
Legality at b3r13c (`real_b3r13c/`): 0 overlaps, track assert PASS (5,792,788 pins), macroNoAp 0.

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

## Open items recorded at b3r12 (the PDN item is fixed: see the verdict)

**The full-die pdngen at b3r2b produces shapes but fails connectivity** (ot-epyc1tb `cases/b3r2b_pdn/run_pdn_r2.log`, 2:57:46, 75 GB):
- `run_pdn_r2` gives OT_PDN PASS with 26.7 M special shapes.
- `check_power_grid` then fails with PSM-0069 on VDD and VSS. The reported causes are:
  - unconnected M4 VDD rails in the W band (x 20–853 µm);
  - more than 1,000 PDN-0182 grid-ownership conflicts, where a fragment slab and a tile are claimed by an earlier pattern grid.
- It has not been rerun at b3r12.

**The 64-stage block word is a latency cost, not a routing failure.** A re-pack that equalises word length (mean 37.6) would recover up to about 3 %.
