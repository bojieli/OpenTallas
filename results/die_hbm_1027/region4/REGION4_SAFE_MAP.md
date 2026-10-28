# 12.14b ESTIMATE: HBM safe region map (hub W/E split, spt feed) under OWNER 12.15 (DIE-HBM-4, 2026-10-27 23:4x PDT)

Analytic page only; no region or clock build. **CHECKED** = I ran the tool myself on the C20f plan. **UNCHECKED** = model numbers; no NUMBER-CHECK yet.
Plan C20f (`intel2:/srv/opentallas-scratch2/claude/die-hbm-1027/c20f`, die_plan 5959e8fecd8b). Data in `intel2:/srv/opentallas-scratch2/claude/die-hbm-1027/region3/r4/`. Base map and tools: `../region3/` (DIE-HBM-3, 3448bfd9fe).

12.15c changes the goal. The map is sized for safe clocking first: in-region spread <= 150 ps incl. OCV+droop, CA margin >= 100 ps. tok/s is reported, not optimised. Latency hiding is dropped (optional, adds sequencer risk), so it is not costed.

## Wire speed (12.15b spice scale)
- Measured on the routed R15-F2 die tree (combined GRT, 50 it): 209.1 ps/mm TT (CHECKED, DIE-HBM-3). x1.0485 = **219.2**.
- Analytic 2W stage model: 265.7 ps/mm. x1.0485 = **278.6**. This is the primary gate speed because the native SPEF R is about 0.63x the 2W setRC value (UNCHECKED).
- Pessimistic bound: 366.4 (HEAD default width x1.05).

## Step 1: base map tok_l10_v1_c5 (34 regions, fish feed), crossing margins on C20f
| v ps/mm | D4/D8/FAIL | worst lo/hi margin ps |
|---|---|---|
| 209.1 nominal | 325/0/4 | 106.2 / 169.7 |
| 219.2 (x1.0485) | 317/8/4 | 119.2 / 175.7 |
| 265.7 nominal | 301/24/4 | 105.0 / 105.0 |
| 278.6 (x1.0485) | 296/29/4 | 115.8 / 145.3 |
| 366.4 | 220/102/7 | 114.2 / 114.3 |

- 329 crossings. The tool runs are CHECKED. The ring model is MESO-COUNT-2 and is UNCHECKED.
- The 4 FAIL are 26-bit status links (L117/L117m/L138/L138m) that the directed start tree does not reach. The fix is a start-forward wire, not geometry.
- At 366.4 there are 3 more FAIL: PHY_N <-> mca/spt, L8_5/L21_0/L22_0.
- Spread is the problem. Each **unsplit soft hub (8.22 x 4.32 mm) is 158 / 196 / 251 ps** at 219.2 / 278.6 / 366.4, all > 150.

## Step 2: split each soft hub into W/E clock regions (`hubsplit.py`)
- Method: scan a vertical cut over hub-local x = 2.9..5.3 mm and count the internal station bits that cross it. The internal_stations come from the plan (3024 / 2988 per hub). Keep both halves <= 150 ps at 278.6 and pick the fewest crossing bits.
- **NW_hub:** cut at die x 9097.9.
  - Crossing bits: W->E 6855, E->W 3065 = 9920 of 301,584 station bits (3.3 %).
  - 1 member straddles the cut.
  - Halves are 3.97 / 4.26 mm wide.
- **NE_hub:** cut at die x 18973.4.
  - Crossing bits: 6571 + 2883 = 9454 of 293,540.
  - 7 members straddle the cut. They take the side of their centre, and that half's bbox includes them.
- External hub ports go to the half that holds their bus face point: NW 56 W / 36 E, NE 56 W / 34 E.
- **Spread of the halves** (spread.py model I x (5.11 % droop + 3 % nets + 0.21 %/mm diag) + 20, UNCHECKED):
  - @219.2: 104.8 / 108.2 ps.
  - @278.6: 127.8 / 132.2 ps.
  - @366.4: 161.8 / 167.5 ps.
- **All soft regions are <= 150 ps at 219.2 and 278.6.**
- Still over 150 ps at 278.6 are the hard partitions only: PHY_N 171.7 and the SM singles 158.7. They are their own hard cores with in-core island clocks (12.2a1), so core sign-off owns their tree. They are not die region trees (assumption, UNCHECKED).
- Render `r4/hs/map_hubsplit.png`, VIEWED.

### Crossing margins of the split map (36 regions, 333 crossings incl. 4 synthetic in-hub HX ports; CHECKED tool runs)
| feed | v | D4/D8/FAIL | worst lo/hi margin ps |
|---|---|---|---|
| fish | 219.2 | 301/28/4 | 108.2 / 123.9 |
| fish | 278.6 | 224/87/**22** | 119.9 / 119.9 |
| **spt** | **219.2** | **291/38/4** | **111.9 / 246.4** |
| **spt** | **278.6** | **162/167/4** | **114.2 / 120.3** |
| spt | 366.4 | 96/169/68 | 122.9 / 154.5 |
| fwd | 278.6 | 137/84/112 | 118.6 / 135.1 |

- With the fish feed, the split leaves the R016E crossings off the start tree: 22 nontree FAIL at 278.6.
- **The spt feed passes:** 0 geometry FAIL at 219.2 and 278.6, every assigned crossing >= 100 ps, and only the same 4 unreached status links.
- The in-hub HX crossings are D4 with margins >= 129.7 ps and phys 2-4 cycles.
- The cost is more D8: 167 crossings at 278.6.

### TOK price, ds_ar, no hiding (UNCHECKED model; region3_tok.py price on C20f)
- **Split map, spt @278.6: 1764.7 tok/s (-8.0 %). @219.2: 1792.7 (-6.5 %).** qwen_ar loss is 1.61 %.
- This is inside the 12.15c accepted range (about 1700-1770).
- Not priced: the 2-4 cycles of HX latency on about 19.4 kb of hub-internal conns. Those conns are not die lanes in the ledger, so the real figure is somewhat lower.
- For reference only, since hiding is dropped: hide 1827.0, hide+SX 1837.0.

## Verdict / next
- **Safe map candidate: tok_l10_v1_c5 + hub W/E split, spt feed.** 36 regions.
- At the spice-scaled gate speeds it meets spread <= 150 ps and CA margin >= 100 ps. The remaining items are:
  - (i) add the start-forward wire for the 4 unreached status links;
  - (ii) at 366.4 it fails (68 FAIL), so the measured-vs-analytic speed must be settled by a GRT-RC re-time of the 2W tree. The SPEF rescale crashed for DIE-HBM-3.
- Next (re-plan event, 12.13e):
  1. Hub W/E sub-regions with their own local trees.
  2. HX crossings at the cuts as count-aligned rings in the hub bay streets.
  3. spt region feed.
  4. Then G0/G0C and die GRT0 incl clock (>= 50 it, -critical_nets_percentage 0).
