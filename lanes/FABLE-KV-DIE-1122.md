# FABLE-KV-DIE-1122: KV (qwen_kvsys) die-level review and the D29 die-level change

Lane FABLE-KV-DIE (Fable), started 2026-11-22 04:2x PST by COORD at the owner's request. Work dir: epyc8
`/srv/opentallas-scratch2/claude/fable-kv-die`. Marking: **M** measured by me this round, **R** reported by the owning lane, **P** proposal.
Base read: D27d3 plan 48b92c30c8f6 (sealed tree on epyc8), D26 / D27d3 kit rows in `autopilot/kit_wave_stages.tsv`, D26 placed kits.
Nothing here is a new gate, cap or hold. Family lanes keep their builds.

## 0. Answer in five lines

1. **Area is not what stalls KV.** The die is 11.18 x 27.04 mm with 32 % under hard cores; every unsigned tile holds 0.06 to 0.20 std cells
   per um2 of free area (M). The street-rule legalizer, run with growth and added registers allowed, asks for at most +3.9 % on any type
   and 0 um on the die (M, section 3). Growth alone unblocks nothing.
2. **The KV tile is 3 to 5 reach lengths across and its glue is built per lane.** Tiles are 1,037 to 2,160 x 1,521 um against a 405 um
   reach; 8 to 36 hard cores stand in a grid with 43 to 104 um streets and 9 to 17 um off the tile edge. Everything a type builds itself
   (stations, landing rings, taps, reset relays) lives in those streets (M, section 1).
3. **Each crossing lane gets its own landing ring, however narrow.** 2,006 landing bands on 56 types; 1,188 (59 %) carry <= 16 live bits,
   761 are 1-bit `ftN_i` rings. A 1-bit ring is 811 cells / 200 flops in the D26 netlists; the LITE form the hub types already use is
   88 cells / 18 flops (M, section 2). Rings are 70 % of hub_Ei, 24 % of hgi_v3, 16 % of pv_v6, 6 % of hg_v1.
4. **The landing bands then do not fit at their pins.** pv types: 38 to 43 of 74 bands sit more than 300 um from their face pin
   (max 455 to 495 um), 10 to 49 bands are slivers under 15 um. 5 pv kits and io_cor_v1 failed place on "clock-landing band too small or
   blocked" on D26 / D27d3 (M, section 2).
5. **Why harder than S81: it is not logic, it is that every KV type is its own small die** (22 to 248 rings, 44 to 191 taps, a reset tree,
   14 to 43 internal station rows), 16 pv types are 16 different blocks, and every event re-keys them (FABLE-PD-KV-2000). Un-stationed
   nets are found one kit at a time at -500 to -2,400 ps (FABLE-VISUAL-0030).

## 1. Die-level geometry (M: D27d3 plan)

| Family | Types / inst | Tile um | Hard cores | Core area | Edge margin W/E/S/N um | Bands | Taps | Narrow bands | Bands > 300 um from pin |
|---|---|---|---|---|---|---|---|---|---|
| pv | 16 / 16 | 2160 x 1521 | 24-36 | 41-43 % | 15 / 15 / 43 / 233 | 18-79 | 96-191 | 5-59 | 5-43 |
| hg | 8 / 32 | 1279 x 1521 | 27-30 | 52-53 % | 60 / 86 / 17 / 26 | 13-24 | 65 | 5-11 | 0-2 |
| hgi | 11 / 32 | 1279 x 1521 | 18-25 | 40-42 % | 78 / 43-69 / 9-17 / 302 | 6-32 | 23-90 | 2-20 | 0-2 |
| pc | 6 / 32 | 1037 x 1521 | 8 | 26 % | 91 / 91 / 246 / 246 | 17-32 | 35-50 | 11-17 | 2-5 |
| hub | 5 / 5 | 1279-2160 x 1676 | 0-21 | 0-38 % | - | 60-248 | 74 | 22-186 | 0-15 |
| hroot | 1 / 4 | 1901 x 838 | 0 | 0 | - | 23 | 36 | 11 | 4 |

- Core-free streets, pv: x 0-15, 395-648 (253), 1028-1132 (104), 1512-1765 (253), 2145-2160; y 0-43, 233-337, 527-605, 778-804, 994-1097,
  1287-1521. The pv split cut (x 1080) runs down the 104 um centre street: 52 um of cut-face margin per half.
- hgi: S margin 17 um under a face that takes 1,296 to 2,165 ft bits; N margin 302 um is unused.
- `clock.tap_max_sinks` is a plan key (pv 1000, others 1200 / 1500); G0 reports it as a warning. It is not a sign-off gate. The two KV
  types with post-CTS data carry 6 taps over 1,650 sinks at insertion <= 298 ps, skew <= 54 ps (failure_breakdown TAP-INSERTION).

## 2. Landing rings (M)

Plan count (D27d3): 3,754 ring instances on the die, 2,101 with <= 16 live bits. Per type: pv_v7 58 of 77, pv_v12 59 of 79, pv_v6 / v6n 55 of 74,
hgi_v8 20 of 32, hub_C 186 of 248, pc_v1 17 of 32.

Netlist count (`1_2_yosys.v` of the D26 kits, script `tmp/ringcount.py`):

| Kit | Cells | Soft rings | Ring cells | Share | 1-bit ring |
|---|---|---|---|---|---|
| kv3_pv_v6 (epyc9) | 490,358 hier. (449,407 std at floorplan) | 59 | 78,958 | 16 % | 52 x 817 cells / 200 flops |
| kv3_pv (epyc2) | 462,686 | 14 | 39,831 | 9 % | 3 x 811 |
| kv3_hgi_v3 (epyc7) | 114,433 | 24 | 27,282 | 24 % | 10 x 802 |
| kv3_hg_v1 (epyc2) | 267,549 | 15 | 15,899 | 6 % | 4 x 811 |
| kv3_hub_Ei (epyc2), has narrow + lite | 293,233 | 82 | 205,921 | 70 % | LITE 28 x 88 cells / 18 flops; narrow full 461-568 |

`clock.landing_ring_narrow` (R1-NARROW, 0 cycles, bench `rtl/test/meso/narrow` covers status copy, WREG, DSREP) and `clock.landing_ring_lite`
(RING-LITE-1, 0 cycles) are opt-in type keys. Only the 5 hub types carry them. `clock_landings._ring_lite` returns nothing for a type with
`landing_control_status_copy` (41 of 56 types), although the LITE ring has no status flags to copy.

## 3. Street rule (M: `tools/die_plan/street_rule.py` on D27d3, rt 3e5de95c409b)

- `check`: 45 of 50 checked types violate the street-or-abut rule (every pv type 8-9 outline slivers; hg 8-10; hgi 4-6).
- `legalize` dry runs (private outputs, `--no-bins`): default = 16 types applied, 0 die growth; `add_regs=3` = 14 applied. Not applied:
  all 16 pv, 7-8 hg, 6 hgi, hub_C ("points under cores", "ft hops over reach", "cores over LEF content macros").
  Largest outline the tool asks for: pv_v2n 2194.56 x 1555.2 (+3.9 %). Reticle headroom 14.8 x 5.96 mm.
- The tool's event writer crashes on a non-JSON bool (`cmd_legalize` line 3073); I ran it through a wrapper (`sr_wrap.py`).
- Reading: the automatic pass cannot re-floor pv / hg / hgi, and the moves it does apply are 8.64 to 43 um. Not worth a re-key by itself.

## 4. Proposed D29 die-level change (P)

| Row | Change | Types | Cycles | Effect (M where a number is given) | State |
|---|---|---|---|---|---|
| R1 | `clock.landing_ring_narrow: true` | 44 unsigned types, 1,018 soft rings < 64 bits | 0 | about -350 cells per narrow ring (811 -> 461) | row script ready; gates running on a private fork |
| R1b | `clock.landing_ring_lite` on the same types, tool change so status-copy types qualify | 44 | 0 | 811 -> 88 cells and 200 -> 18 flops per grouped ring: pv_v6 about -37 k cells / -9.5 k flops, hgi_v3 about -12 k cells | tool change to write + bench |
| R5 | hg feedthrough street: head0/1_e4, e5 and the astk strips g_ex_N +43.2 um in y; opens a 51.8 um all-layer street at y 553-605 inside the ft3 band span (section 6) | hg_v1, v1p2..v1p6, hg_v3 (7 types, 28 partitions) | 0 | core_place RUDY H overflow 571k -> 270k (-53 %), over-core H ratio 1.52 -> 1.07; 15-30 stations re-routed, register count kept, EQ OK | row script ready; gate B (with landing_remap + pinclear) after gate A |
| R2 | re-site the narrow bands at their pins after R1 / R1b (`cland_band_fit`) | pv 16, hub, pc, hgi | 0 | bands > 300 um from pin and sliver bands go away where the ring shrinks | after R1b bind |
| R3 | pv re-floor inside the tile, no die growth needed: W/E margin 15 -> 58 um, centre (cut) street 104 -> 234 um, side streets 253 -> 145 um; cores move, shapes kept | pv 16 | re-price | cut-face margin per half 52 -> 117 um: tap and bank sites at the cut | geometry handed to FABLE-FIX-KV-PV-SINKSPREAD; not built by me |
| R4 | hgi head array +86.4 um north (S margin 17 -> 103, N 302 -> 216) | hgi 11 | re-price | S-face landing strip for 1,296-2,165 ft bits | proposal to OPUS-FIX-KV-HGI-R6 |

Not in my rows (owned, already moving): hg / hgi lockup + reset rows (HGI-R6, LOCKUP-INERT), pv split (PV-R7), hub hard rings (HUB-R6,
RINGMAC), pc pin stations (IOPC-R4), hroot (HROOT-R1).

## 5. LITE eligibility (M: D27d3 sidecar, rings <= 8 bits with the same source, K and depth; instance-level upper bound)

pv_v12 / v7 56 of 58; pv_v6 / v6n 51 of 53; pv_v5 / v5n 41 of 43; pv_v4 / v4n 35 of 37; pv_v3 / v3n 25 of 27; pv_v2 / v2n 19 of 21;
hgi_v3..v8 11-12 of 14-15; pc_v1 8 of 11; pc 5 of 7; pc_v3 7 of 10; hroot 7 of 9; io_cor_v1 12 of 15; sys_c 14 of 16; hg_v1.. 4 of 7.
Die: 1,338 of 1,687 narrow ring instances. Tool change RING-LITE-2 (`landing_ring_lite.status_copy`): unit tests 130 pass, lock-step
bench `rtl/test/meso/lite/run_csc.sh` 11 of 11 phases, 0 mismatches, shift and mutant negative controls caught.

## 6. hg central channel (COORD 04:5x, FLOW-CLKGRT-R2 kv3_hg_v1p2: GRT overflow 871k base / 566k clock-first, DPL-0033) (M)

- All hg cores block M1-M5 (LEF OBS 93-100 %; M6 / M7 2-4 %). Over a core a bundle has M6 (E-W) or M7 (N-S) only.
- ft3 (1,056 bits, W -> E) has three station banks, each a column in an x-street (x 309-333, 622-652, 950-966) spread over
  y 404-744 (340 um, plan `bit_sites_um`). Between the banks the bundle therefore runs over head e2/e3 (y 337-553), the astk strips
  g_ex_1 / g_ex_2 (y 561.6-673.9) and head e4/e5 (y 683-899), on M6 only; the only all-layer E-W space in that 340 um is two 9 um slots
  (y 553-562, 674-683). core_place's route-supply model gives demand / supply 1.52 for E-W wires over the cores of this type.
  CORRECTION to my 04:5x post: the bundle is not a 26 um ribbon over the astk strips alone; "1,050 M6 tracks for 1,056 bits" was the
  strip-only reading and is withdrawn. The class (E-W bundle over M1-M5 cores with no street) stands.
- Kit congestion.rpt (clock-first arm, 20,000-gcell sample): 69 % of the overflow lies inside hard-core footprints (head0_e5, head0_e2,
  head1_e4), hot bins x 432-700, y 604-860. The kit's own placed scan: 263 groups over reach, 12,020 bits.
- Variants tried with `core_place.py --seed --no-search` on kv3_hg_v1p2 (RUDY H overflow, base 571,430): head e4/e5 up only 523,527;
  head e2/e3 down: not legal (ring core `cl_..zo_d1` in the lower channel); **head e4/e5 + astk strips up 43.2: 270,198**.
  `ft_corridor --band` finds no 3-station chain for a detour into an off-axis street, which is why the street is put on the ft3 axis.
- kv3_hg (4 partitions) has another feedthrough path (ft2 at y 213-232); R5 leaves it (331k -> 323k only). Open.

## 7. Gates (private ot-tree-fork of the D28 work tree, epyc8 `fable-kv-die/tree_a`, base dry5 fcfa38bdb65b, tools rt 6d2e187f0d65 + RING-LITE-2)

| Gate | Rows | Plan | Result |
|---|---|---|---|
| A (`gate_a1`) | R1 + R1b | 6f866b1b34cc | precheck PASS, PLAN-GATE-PRE PASS 0, G0 PASS 0 errors / 2585 warnings, ELAB 0, strict bind 0 errors (160 / 56 / 2545), LATCHECK rc 0, BPC PASS 570, R8 = baseline (91 / 32 / 7). COORD ruled R1 + R1b into D28; scripts in `kv-plan-r6/d28/rows/` (9860691ee0da, 74bdc3ee5a86). |
| B (`gate_b2`) | R1 + R1b + R5 + landing_remap + pinclear | 0585b4608c74 | row RC 0 (hg_v3 added tap clk_t52 moved 43.2 um off head0_e5), remap RC 0, pinclear 0 moves, PLAN-GATE-PRE PASS 0; G0 + bind running at 06:1x PST |

LITE rings in the Gate A bound RTL: pv_v12 / v7 56, pv_v6 / v6n 50, pv_v5 / v5n 41, pv_v4 / v4n 34, pv_v3 / v3n 25, pv_v2 / v2n 18, pv_v1 / v1n 9,
hgi_v3..v8 11-12, hroot 7, pc_v1 x3 / pc_v3 7, pc x2 4, io_cor_v1 12, sys_c 14, hg_v1.. 4.

## 8. sys_c (COORD 05:3x: D27d3 kit GRT setup -418, 285 intra-D2D groups over 405 um, 2.7 mm reset recovery path) (M + ruling)

- The slot is the pv column width x the io row height (2160 x 1036.8); both are shared, so a smaller sys_c outline frees no usable die area.
- Pins on W and E only; the UCIe PHY is a fixed bump field at slot x 691-1469, y 60-838. A compact outline must contain it and reach
  one face, so the other face stays 700-1500 um away: same station count as a compact region in the full slot, plus a re-shape of a
  neighbour (io_cor is signed).
- Ruling: D29 keeps the slot. Compaction = one place region for the D2D core (about 330 x 330 um at x 1500-1830, y 500-830 round the
  four SRAMs), stations by placed length from the W bands over the PHY, a reset relay in the region. Owner FAM-KV-HUBC-SYSC-R2.

## 9. Not checked

- No placed-DB sink census by me (FABLE-FIX-KV-PV-SINKSPREAD owns it). The pv centre-bottom cluster is only partly rings: 14-18 narrow
  bands there on v6n / v5n, 0-1 on v12 / v7 / v2 (plan).
- LITE group sizes depend on K per lane; the real count comes from the R1b bind.
- S81 / QC plans were not on epyc8 for a like-for-like table.
