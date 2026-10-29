# DIE-HEAD-21 HK3: plan_hk3 (HEAD non-tile landing bands at ring_ff x 2.0, ring_place ff; hd_lep0N cores re-sited)

COORD ruling 2026-10-28 (HEAD-KITS-2): plan_hk2 is the accepted HEAD kit plan. Every non-tile kit failed placement on the
proposed bands, which blocks HEAD-KITS-3. The hd_tile precedent (DIE-HEAD-11/12/13/14) is main
`compose(band_reserve="ring_ff", band_spread=2.0, band_ring="ff")`.

- Tool: `tools/s81_head/head_band_ringff_delta.py` (test `test_head_band_ringff_delta.py`: 3 PASS; the HK2 tests still pass, 5 PASS).
- Rebuild: `gen_kits_hk3.sh OUT`. OUT must be this directory, because the pins_file paths are relative.
- Input: `../hk2/plan_hk2.json.gz` (claude/die-head-21-hk2-1028@0a4b931c58).

## Method

A full `compose` would re-split the landing cohorts and rename types. The delta therefore re-runs only main
`clock_landing_plan._storage_band`. It uses the same reserve, spread step-down, 405-um reach rule and obstacles (die
islands, die clock-tree sites, ft-slot sites, earlier bands), in compose order (buses sorted). It applies to every band
of the 15 non-tile types: all of them carry landing rings. The new rect is written to three places:
`landing_contract.bands[bus]`, the matching `collector_local_sources[].band`, and the `landing_ring_bank` reserved site.

The order is infrastructure first. The bands are composed against the fixed objects only (lep_pair cores included).
The SRAM macros are then placed again around the new bands with the HK2 placer: serdes, mesh, ctl and host are re-run
from the census, and hd_lep0N moves its colliders to the nearest legal site. Reset taps that a macro blocks move as in HK2.

## Estimate (CHECKED: tool output, report.json)

Reserve per band = (5 x ring_width + 160) ring flops x 1.4166 um2 x 1.05 (DIE-HEAD-11 measured footprint).
ring_width = 64 x ceil(W/64), CA depth 4. A W=567/514 ring needs 4,522 um2, and the padded reserve gave 2,636. The band
is spread x reserve. Every band reached spread >= 2.0, so there was no step-down. Every band stays within reach
(max pin-to-band hop <= 242 um vs 403).

| type | bands | old band um2 (padded) | ring_ff reserve um2 | new band um2 | spread | max hop um | SRAM moved | overlaps |
|---|---|---|---|---|---|---|---|---|
| hd_ctl | 11 | 17799 | 30699 | 62578 | 2.01-2.07 | 221 | 3 | 0 |
| hd_host | 7 | 9494 | 16421 | 33531 | 2.00-2.07 | 172 | 110 (re-placed) | 0 |
| hd_lep0N | 7 | 16493 | 28320 | 58117 | 2.01-2.07 | 214 | 0 (field shifted, see (b)) | 0 |
| hd_mesh | 3 | 5949 | 10233 | 21103 | 2.03-2.07 | 166 | 110 (re-placed) | 0 |
| hd_serdes | 1 | 2636 | 4522 | 9308 | 2.06 | 165 | 2 | 0 |
| hd_spn | 10 | 16283 | 28082 | 56666 | 2.00-2.06 | 198 | - | 0 |
| hd_spn_end | 9 | 13647 | 23560 | 47495 | 2.00-2.06 | 198 | - | 0 |
| hd_st_k5 | 4 | 6625 | 11423 | 23482 | 2.03-2.07 | 166 | - | 0 |
| hd_st_m | 2 | 1353 | 2380 | 4830 | 2.03 | 123 | - | 0 |
| hd_st_n3 | 4 | 10544 | 18086 | 37304 | 2.06-2.07 | 166 | - | 0 |
| hd_st_n4 | 4 | 10544 | 18086 | 37304 | 2.06-2.07 | 166 | - | 0 |
| hd_st_str | 2 | 5272 | 9043 | 18652 | 2.06-2.07 | 166 | - | 0 |
| hd_st_turn | 2 | 5272 | 9043 | 18652 | 2.06-2.07 | 166 | - | 0 |
| hd_turn_a | 1 | 2636 | 4522 | 9073 | 2.01 | 198 | - | 0 |
| hd_turn_b | 1 | 2636 | 4522 | 9248 | 2.05 | 242 | - | 0 |

The overlaps column is the tool's exact-rect check: band x band, band x island / die-clock site, band x core,
core x core, and core x clock. The new bands use 3.5 % of the outline on hd_ctl, 3.3 % on hd_lep0N, 5.2 % on hd_turn_a,
and less on the other types.

## (b) hd_lep0N lep_pair cores (decided by design)

There are four 388.8 x 432 lep_pair cores (no view yet). Each one serves one face: g_pp[0] N, g_pp[1] and g_pp[2] W,
g_pp[3] E (coll_ik/coll_ok; RTL `ot_s81hd_lep0N_core.sv`). With ring_ff bands, a coll_i band in front of its 206-um
window is 44 um deep (80 um for the 114-um coll_i3 window). lepk_i0 (W=1104) is 72 um deep. The HK2 positions leave
26 um on the W face (cores at x43.2) and 26 um on the E face (g_pp[3] right edge at 1417).

Options estimated (tool runs, CHECKED):
- **N0: keep the cores; the bands stack around them.** This is legal but poor. coll_i1 becomes a 13 x 700 um strip
  (hop 380), coll_i2 is pushed under the core (hop 377), lepk_i0 sits below g_pp[3] (hop 399, at reach), and coll_i3
  sits above it. Two more problems:
  - E corridor: about 850 lepk bits plus 2 x 514 coll_i3 bits run N-S in a 26-um strip (about 1,660 vertical M3/M5/M7
    tracks, 998 at 0.6). The coll_i3 segment needs 1,028 > 998, so it FAILS track use <= 0.6.
  - The core also sits in the 34.56-um boundary-flop strip.
  REJECTED.
- **N2: move only g_pp[3] to (1010.88, 639.36), above the island row.** coll_i3 cannot sit in front of its window. Its
  band goes below the core (hop 281), and lepf/unit become 20-um slivers. coll_i3 data runs down to the band and back
  up to the core: about 280 um x 514 bits = 144 bit-mm, vs 53 for N1.
- **N1 (CHOSEN):** every band sits directly in front of its own window, as on all other types. The moves:
  - g_pp[3] -> (950.4, 639.36): above the clock-island row, which ends at y617.8 + 8.64 halo, and west of the E bands.
    Its E edge is at 1339.2, the coll_i3 band starts at 1345.7, and the core faces coll_i3/coll_o3 directly.
  - g_pp[0] -> x 544.32 (-60.48): this makes room. It also moves g_pp[0] 60 um nearer its own N coll windows
    (x160-587), about -62 bit-mm on 1026 bits.
  - g_pp[1] and g_pp[2] -> x 69.12 (+25.92): W bands 44 um deep in front of coll_i1/coll_i2 (hop 166, was 380/377 in N0).
  - The 45 parent SRAM (u_lep/u_land, x >= 440) shift +25.92 as one block, which keeps the bank pattern. 0 SRAM are
    scattered. 6 reset taps moved.
  - No clock island or die clock-tree site moves. The die clock plan is unchanged; moving the island would change the
    die tree.

  The cost: g_pp[3] is now 104 um from the E face (it was 26 um, but that was illegal). The k-link to u_lep (centre
  south) is about the same: the core is 78 um nearer in x and 311 um higher. g_pp[0]'s top edge (y1218) touches the
  coll_o0 face strip over x544-587 (43 of the 205-um output window). That is a soft keepout, the same as HK2 allowed
  for cores. All four cores still have no view (kits do not place them).

Render: `png/hd_lep0N.png` (VIEWED).

## Validation

- G0C (`check.py --completeness`, core_conns): FAIL with 16 ERRORs, all `insertion_target` (one-entry 450 vs 250).
  The finding list is identical to plan_hk2: 0 new, 0 gone, warnings included (CHECKED, set diff of messages).
- The G0C report has no schema, hard_cores or reset error.
- `gen.py phys --clock-landing --trial` for all 15 types, then `kit_preflight`: 14/15 PASS. hd_lep0N FAILs as in HK2
  (module_closure: `ot_s81hd_lep_pair` has no view or `_bb`; it needs the PAIR child kit). head_land_slots was
  regenerated for all 15 kits.
- Renders `png/<type>.png`: all 15 VIEWED. Bands sit at their faces, with no visible overlap with macros, islands or
  die-clock sites. The hd_turn_b band ends at x82.56, and the die-clock sites start at x84.72.
- Placement-only diagnostic (ot-run on intel2, `run_diag.sh KIT place`): see the PLACEMENT section below.
