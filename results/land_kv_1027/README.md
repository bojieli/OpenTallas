# LAND-KV-1: KV die (qwen_kvsys) in the LANDED form (COORD 12.10a 10-27)

Basis: the current KV plan hm_r26q5c39 (sha256 4190246956824a7a...) with the 546-pin plan. It has the same 1628 core instances, 31 modules and 521 core taps as the top-down form, so **no core needs a new kit** (QK-CORES-8 unchanged).
Work dir: intel1:/srv/opentallas-scratch2/claude/land-kv-1027. All numbers are from LAND-KV-1's own runs and are UNCHECKED (no NUMBER-CHECK yet).

## Step 1: plan (structural fixes)
- **30 band FAILs** (pv_v7 15 + pv_v12 15, "no macro-free band"). Root cause: 57 one-bit FT lanes on each pv face, each reserving a 64-bit padded ring.
  - Fix: `clock_landing_plan.compose(band_reserve="live")` sizes each ring from the measured yosys count, 4*(W+3)+124 FF plus 612 cells per 64-bit chunk.
  - Result: 0 placement failures, 60 types, boot ready 388 cycles, reset release 95, ring train 21.
- **20 G0C errors** (cells): fixed with `cells_fix.py`, which sets type.cells = base/parent estimate + measured landing rings, with the basis recorded in the type note.
  - Result: G0C PASS, 0 errors, 60/60 types clean.
- Ports: 128 groups, 3,595 ports / 519,111 bits, 2,084 lanes / 10,785 lane-cycles (identical to R26).

## Step 2: GEN (die_trial kit --region-trees --htree-full-depth --tree-site-legal --tree-site-slide --rep-um 405)
- 128 region trees, 4209 nodes, 824 repeaters, 1920 taps, 16 levels; abutted pin check PASS.
- Render `clock_tree.png` viewed.

## Step 3: die GRT incl. clock (mk_combo_kv.py: signals M4-M7, clock M8-M9, 50 iterations, -critical_nets_percentage 0)
- Overflow 0 at TT and FF; 5034 clock nets; usage M4-M7 4.4-4.8%, M8 1.57%, M9 0.61%.
- Clock slew: 74 nets over 320 ps (worst 684 ps). Rep 405 um is too long on routed RC, so ~300 um is needed; the sys_c root also slid to the edge.

## Step 4: die STA (main die_sta_related @133d979e4; declared-budget, 0 real views, MODELLED; droop b2 derate is NOT in main, so it was not applied)
| Check | TT | FF |
|---|---|---|
| Intra setup (TT) / zero-logic hold (FF) | +437.72 | -188.40 |
| Seam setup (TT) / zero-logic hold (FF) | +435.57 | -176.03 |
| HB4 plan, intra (TT setup / FF hold) | +308.06 | 0 |
| HB4 plan, seam (TT setup / FF hold) | +368.37 | +0.06 |
| LANDED window, margin vs 416.5 | **-652.6** | **-524.0** |

- The HB4 plan adds 6.42M intra cells and 119k seam cells.

## Landed phase OCV (landed_phase_ocv.py @be648cbdd7, 3915 crossings)
| Case | Worst margin (ps) | Crossings under 0 |
|---|---|---|
| TT, regions droop, core latency 250 | **-808.7** | 598 |
| FF, regions droop, core latency 202.5 | **-649.1** | 365 |

- Max unshared clock: 7.2 ns TT / 6.2 ns FF; 189 crossings have their LCA at the die root.
- **FAIL.** Root cause (same as HEAD): region roots hang off a 6-7 ns die tree (taps 6.3-7.8 ns TT).
- Next: a low-insertion top distribution that splits late (<=~3.4 ns unshared TT) or neighbour-forwarded region clocks, plus rep ~300 um. Then re-GEN, GRT, STA and LPO.

## Step 5: token price (kv_v39r_price.py lane-class model)
- +66 cycles per attention request (RX 33 + TX 33) and +123 embed, giving +2,499 cycles/token.
- DAG 4810.9 -> 4763.2 tok/s (-0.99%); QCE basis -0.84%; bracket upper -2.08%.
