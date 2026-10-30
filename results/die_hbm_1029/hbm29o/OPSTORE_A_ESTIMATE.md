# opstore_a fit in q_b113: V1 repack vs V2 split (DIE-HBM-29-O, ESTIMATE ONLY)

2026-10-29 21:39 PDT. Plan of record d28c (intel1 /srv/opentallas-scratch2/claude/die-hbm-28/plan/d28c).
Script: opstore_a_estimate.py -> opstore_a_estimate.json + opstore_a_estimate.png (viewed). Nothing built, plan not edited.
CHECKED = computed from the real files by the script; UNCHECKED = estimate.

## Verdict
**V1 (repack, keep K's 760.32x483.84 4x8 opstore_a) is the better option.** Both variants need the same thing: ctl moves
west into the q_b113 NS die_ft_band. V1 intrudes less (267.2 um vs 319.0 um of the 346 um band), adds no pins, no type
and no cycle, and reuses K's outline, which already passes kit_contract. V2 saves no area-placement problem, adds 2,265
boundary pins and a second kit. Open risk for both: the band's die-net demand (UNCHECKED). The next plan event's die_trial
GRT must confirm it. The model already zeroes the core OBS layers (M1-M5) under bands, so the band keeps M7 over ctl.

## Area arithmetic (CHECKED)
- q_b113 outline 1857.6 x 1572.48 = 2,921,039 um2. die_ft_bands: EW y 8.64-207.36 (M4/M6), NS x 310-656 (M5/M7).
  Cores sit at y >= 216. Free of bands: east block x 656-1857.6 by y 216-1572.48 = 1,629,946 um2. West strip x 0-310 = 420,509 um2
  (310 um wide, so no core fits there: the narrowest is 388.8).
- Hard cores with V1 opstore_a: lane14/15 2 x 134,369 + opstore_b 525,533 + ctl 419,437 + opstore_a 367,873 = 1,581,582 um2
  = **97.0 % of the east block**. No rectangle packing fits there with 17.28-um gaps. ctl (669.6 x 626.4, pin-bound: 25.4k
  pins) fits only in row 2 (y >= 941.76, height 630.72). The row-2 width without the band is 1184.32, which leaves at most
  **497.44 um** for opstore_a. 3 columns of 172.824-um macros need >= 561.7 um. 2 columns x 16 rows need >= 689.8 um height,
  which is more than the 630.72 available. => **opstore_a cannot fit without using band area** (or re-aspecting ctl, which is
  not possible because it is pin-bound).
- Macros: 32 x 172.824 x 41.064 = 227,099 um2. Logic yardstick (lane core cell density, 2.284 cells/um2): 240,918 cells need about 105.5k um2
  of non-macro area (UNCHECKED proxy). V1 has 140.8k (1.33x). V2 has 2 x 56.8k = 113.7k (1.08x, tight).
- Stations/streets: 60 d28c internal_stations. V1 puts station sites carrying 16,289 bit-sites inside the new opstore_a
  body, so they must be re-sited (station_resite; 12.2a1 forbids parent cells in cores). V2 puts 11,334 bit-sites inside.
  ft_slots L106x7/L125x1 sit in the EW band (y ~8.6) and are untouched.

## V1: q_b113 repack (type-frame coordinates; the same delta applies to q_b113 and q_b113__physical_v1, NE is MY)
| core | origin | outline | change |
|---|---|---|---|
| lane14 | 1434.24, 216 | 388.8x345.6 | none |
| lane15 | 1434.24, 578.88 | 388.8x345.6 | none |
| opstore_b | 656.64, 216 | 760.32x691.2 | none |
| **opstore_a** | **1080.0, 941.76** | **760.32x483.84** | K 4x8 grid (kit_contract PASS on staged copy) |
| **ctl** | **388.8, 924.48** | 669.6x626.4 | moved west 267.84 (was 656.64), orient MY + track offset kept |
All gaps are >= 17.28 and everything lies inside the outline (CHECKED). opstore_a sits directly above lane15 and the east part of opstore_b,
its two read-path partners. Its E edge is at 1840.32. There is 147 um free above it (y 1425.6-1572.48) for M6/M7 station bays.
Cost: ctl covers the NS band from x 388.8 to 656 for y 924.48-1550.88. That loses M5 there; M7 stays. Full M5+M7 remains at x 310-388.8.
Band track estimate, UNCHECKED, using ASAP7 pitches M5 48 nm and M7 64 nm: 12.6k tracks drop to about 7.3k (58 %) at the
narrowest cross-section. The E-face bus chains (L47/L54/L127, 2056/2248 b) end at ctl's top face, now about 270 um further west.
Path length is about 2.1 mm over 6 existing stations (<= 405 um hops when re-spread), so +0 cycles (UNCHECKED until re-site).
ctl<->lane15 links get about 270 um longer and stay within the existing 2-station chain (UNCHECKED).
Fallback if band GRT fails: 3-col x 11-row opstore_a about 575x607. ctl then covers only about 78 um of band. The grid is irregular
(groups do not map to columns), so it needs a new static grid + kit_contract run.

## V2: split along operand groups (RTL CHECKED: rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv)
- opstore_a = g_operand[0] + g_operand[1] (each ot_hgi_su_lgroup2, 16 lanes x 16 banks crossbar, 16 macros) plus the u_memory
  remainder: lane pin registers + scalar mux for ALL 4 groups (rd_q 2048 = 16 lanes x 4 groups x 32), scalar regs, sticky fault.
  Every group path (pin reg -> xbar -> SRAM -> xbar -> scalar mux -> rd_q pin reg) is self-contained per group g. Natural cut:
  half g = group g + lane ports [4l+g] + scalar[g] + relay of group g+2. **Data bits crossing between halves: 0**. The fault adds 1
  crossing bit (or 2 bits to ctl).
- Extra boundary pins: stage sector writes are broadcast to all groups and are duplicated on both halves: sw_d 2048 + sw_mask 64 +
  sw_addr 120 + stage_group 16 + stage_v 8 + clk/rst/glue 7 = **2,263**. Total 7,534 -> **9,799** pins over 2 cores (+30 %).
- Half outline: 2 col x 8 row on K's grid = 390.576 x 434.976. That fits **390.528 x 436.32** (the current die_plan slot) if the
  col channel is 12.048. Macro fill 66.6 %, logic 56.8k um2 per half.
- Placement: a0 in the current slot (1434.24, 941.76). a1 at (1026.43, 941.76) needs ctl at x 336.96, so ctl covers **319 um of the
  346-um band** (worse than V1). There is no other 390x436 hole (col B above a0 is 194 um; the 1326-1434 gap is 108 um; the west strip is 310 um).
- Core count: 76 distinct hard-core modules on the die today (CHECKED). With identical halves (group/relay index as a declared
  ID strap, output-group sr relay + vm range check tied off in one instance) the count stays 76. Otherwise it is 77, still under ~80.
- Latency: no extra cycle on the read path if both halves are adjacent to lanes/opstore_b (no logic crosses groups). Placing a1 in
  the west strip instead (1-col 16-row about 273x763 fits x 0-310 with no band use) costs 1.2-1.6 mm, which means 3-4 stations each way,
  so **+6-8 edges on every SFU operand read** (static schedule aligns all groups). Rejected.

## Why V1
Same band dependency, less band intrusion (267 vs 319 um), 0 vs +2,263 pins, 1 vs 2 kits (the V1 outline is already kit_contract
PASS), no ID-strap/tie work, more logic headroom (1.33x vs 1.08x), +0 cycles both. V2's only plus is smaller CTS reach (413 vs
622 um Manhattan centre-corner). Both are > 200 um, so both need the in-core H-tree like opstore_b.
**Required before plan freeze:** die_trial GRT of the V1 delta (band demand over ctl), station re-site, ctl/opstore_a clock-entry
taps moved to the new centres (opstore_a 1460.16,1183.68; ctl 723.6,1237.68).
