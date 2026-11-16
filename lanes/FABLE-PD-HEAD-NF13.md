# FABLE-PD-HEAD-NF13: r199 review-before-adopt, HEAD plan rp21z20NF13a (+ NF13b form, place_lines, hd_st_n4)

Reviewer FABLE-PD-HEAD-NF13, read-only, 11-15 18:40-19:30 PST. No build, no STA, no route by me. Tags: MEASURED = my
own arithmetic on the files named here; INFERENCE = expectation, not built.

Files read: plan epyc7 /srv/opentallas-scratch2/claude/head-99/prep21z20NF13a/prep/source_plan.json (sha256 810a66fa...15bfb,
recomputed, matches) vs .../prep21z20NF12/prep/source_plan.json; stamped tree epyc7
/srv/opentallas-scratch2/claude/clksite-reserve-1115/native_head_all.json; die kit epyc10
/srv/opentallas-scratch2/claude/head-100/dr/head/nf6r/tree/kit (kit.json, abstracts/) and its closed views
/srv/opentallas-scratch2/claude/head-100/dr/views/ (gen.tcl, LEFs); tools/die_plan/gen_phys.py die_islands_tcl.

## 0 Verdict

**NF13a: ADOPT-OK.** No blocking finding (no measured failure on a released type). Three non-blocking items go into
the next delta (NF13b), section 5 rows 1-3. Two findings outside NF13a are larger than the event itself: the
hd_tile and hd_st_n4 closed views in the die kit are STALE builds of older outlines (section 2, 3).

## 1 Q1 -- NF13a islands, measured

- Plan diff NF12 -> NF13a: 24 paths, all `partition_types/<12 types>/clock/die_islands_um` + `note`. No tap, window,
  tap_um, landing, pin, reset or outline field differs. So tap reach and `clock.tap_window` of hd_host_e / hd_host_w are
  byte-identical to NF12. MEASURED.
- All 12 types have one instance, all R0 (the MX/R180 rail caveat does not touch NF13a). MEASURED.
- Island = 2.70 x 0.81 box = cell body 1.62 x 0.27 + 0.54 / 0.27 margin. Per type: tree cells inside the partition =
  islands = cells covered (260/260 hd_spn_end, 106 n4, 141 k5, 658 lep0N, 191 ctl, 64 ctl_n, 21 ctl_e, 50 host_n,
  42 host_e, 46 host_w, 44 n3_transit, 65 n3_turn). 0 outside outline, 0 body-body overlap, all on even rows
  (0.54 row pitch), 0 overlap with hard cores (min centre-to-core 2.57-3.06 um on lep0N/ctl/host_e/host_w). MEASURED.
- Blocked area 46-1,439 um2 per type = 0.012-0.14 % of the outline; in landing bands at most 32 islands (hd_ctl
  lepk_i0, 70 um2 of 18,000). No capacity effect. MEASURED.
- The NF12 8.64-um square islands of these types (36 in all) are dropped; 35 of 36 overlap no new island, and no
  stamped-tree cell sits in them, so they were dead holes. MEASURED.
- A. hd_host_w islands come from the WRONG tap set. The stamped tree (NC plan) serves host_w with 12 taps at the old
  positions (clk_t1 162.02/17.31, clk_t4 630.24/285.98, ...); the plan since NF11 has 40 taps (clk_t1 9.65/242.48,
  ...; 28 names not in the tree, all 12 shared names at a different xy). The 46 islands reserve the old tree. MEASURED.
  Harmless to the type build (100 um2), useless for the die. hd_host_e: 11 taps match within 0.5 um, the NF11 early
  core tap u_epc.clk has no tree leaf. hd_serdes 22 = 22.
- B. Edge cells: 28 islands lie within 0.81 um of a partition face (spn_end 5, k5 4, lep0N 2, ctl 1, ctl_n 3,
  host_n 2, host_w 1, n3_turn 4; ctl_n has 1 more at 5.1), 8 of them inside an M5/M7 face-pin bus window
  (hd_spn_end x_i, b_o, hu; hd_ctl h_rx_i at x 353.2-355.9 y 0.27-1.08, the DRT-0255 face of FABLE-PD-HEAD-1650;
  hd_lep0N coll_o0; hd_st_k5 d; hd_host_n ad). MEASURED positions; that the M1-M8 stack of such a cell meets a face
  pin is INFERENCE (no pin rect read).
- C. 17 interior M7 pins (rst_start_raw_* 16, cland_tstart_in 1 on hd_host_w) lie inside or within 1 um of an
  island in 9 types. They exist unchanged in NF12; the pin stays reachable from M6. Advisory.
- D. Two tree cells are half a site off the 0.054 grid: b51241 (lep0N x 1010.529) and b51242 (ctl_n x 785.781), the
  two inserted parity nodes. The island covers a 0.027 shift. Fix in the stamp.
- E. M7 PG pairs: a body-vs-pair test gives 21-30 % of cells over a pair [3.984, 4.656] in these types and the same
  21 % on stamped hd_tile tE0o0 (random = 26.5 %), so body overlap is not the stamp's clearance criterion and I make
  no finding from it. If hd_ctl / hd_spn_end move to die-phase pdn (M7 offset 8.448, DRT0255-PROOF), the pairs move
  4.32 um: the stamp's PG slide must be re-run for those types on the phase their kit really uses. INFERENCE.
- F. Cost, not a defect: 8 of the 12 types are closed views (signed builds) in the die kit: hd_spn_end, hd_st_n4,
  hd_st_k5, hd_ctl_n, hd_ctl_e, hd_host_n, hd_st_n3_transit, hd_st_n3_turn = 751 new sites that were placeable area in
  those builds. They must be rebuilt to honour the islands; until then the abstract cut hides real metal there (as
  today with the NC tree, so no regression). In-flight NF12 runs of the 12 types are stale on adoption.

## 2 Q2 -- hd_st_n4 1123.2 vs 993.6: real overlap, cause = stale view

- nst4 origin (5970.24, 15094.08), plan E edge 6963.84 = lep0N origin x. The view LEF is 1123.2 wide, so it covers
  lep0N x 0-129.6, y 95.04-1088.64 in lep0N frame: 129.6 x 993.6 = 128,770 um2, on top of lep0N W-face landing bands
  coll_i1 and coll_i2 (x 17.28-62.64). MEASURED.
- The view's E-face pins are at x 1115-1123.2: 1,030 M4 + 1,026 M6 + 28 M7 = 2,084 pins, 129.6 um inside lep0N; none
  at the plan seam 993.6. MEASURED (views/hd_st_n4/ot_s81hd_st_n4.lef).
- Cause: views/hd_st_n4/gen.tcl reads die-head-route-1/signed/DeepSeek_ROM/hd_st_n4/6_final.odb; the plan note says
  "CPL-HEAD 11-11 REDESIGN B: E edge cropped 1123.2 -> 993.6 (lep0N +129.6 W)". The signed DB is the pre-crop shape.
- Fix: neither outline growth (it would undo REDESIGN B and move lep0N, 49 cores) nor a view re-shape (the E-face
  pins and 4 ft stations are at the old pitch 280.8, plan 248.4). Drop the view: die kit takes the plan abstract for
  hd_st_n4 and the type is rebuilt at 993.6 (it needs a rebuild for its 106 NF13a sites anyway).

## 3 Q3 -- place_lines 8.64 shift

- hd_tile view = same class as hd_st_n4: LEF 708.48 from signed/DeepSeek_ROM/hd_tile/6_final.odb; plan note "HEAD-97
  rp21 (COORD 11-13 F1b): outline 717.12, elemA x 8.64, elemB +-8.64". The view is the pre-rp21 tile. Its E-face
  pins (283 M4 + 283 M6) are at x 708.48, 8.64 short of the plan seam, in all 264 instances, R0 and MY. MEASURED
  (pin x); "cores inside the view sit at pre-rp21 positions" is INFERENCE from the note.
- What moves with place_lines (MY/R180 lower-left = ox + Wp - Wm): only the placed master (cells, pins, internal PG)
  by +8.64 in die x. Nothing in the plan frame moves: islands, tap sites, seam pins, landing, die PG and the stamped
  tree are already mirrored about 717.12. Check: mapping MY-tile tree sites with x_t = 717.12 - x - 1.62 reproduces
  the R0 majority site set (70.5 of 117 sites per MY tile; every other offset tried gives 0). MEASURED.
- To regenerate after the change: die placed DB, tap-pin snap, unit prep + route of the 144 units over a MY tile
  (their results so far, 0 DRC ones included, are on shifted pins), die GRT/STA parasitics. Not the plan.
- Exclusion: the cut-window generator must keep mirroring about the PLAN width. HEAD-MYTILE's first proposal (windows
  mirror about LEF SIZE) plus place_lines together shift the windows 8.64 the other way. A padded 717.12 master is
  safe with either.
- After the change one face is still open: MY type-E face at ox + 8.64 (today the type-W face is at ox + 708.48).
  Seam pins abut only when hd_tile is re-signed at 717.12. So place_lines is a die-route proof aid, not the cure.
- 1.62 um: it is NOT a PG phase and NOT the 8.64. 1.62 = the die cell body width; a MY mirror of a lower-left site
  needs x_t = W - x - 1.62 (measured above). M7 PG phase is unchanged by 8.64 (one M7 pitch; ox and both widths are
  multiples of 8.64; 2 M8 pitches). The 1.62 will not disappear with place_lines; fix = body-width term in whatever
  mapped MY boxes as points. Not checked: 8.64 is a quarter of the M9 PG pitch (34.56), so MY-tile M9 tap pins vs
  die M9 straps should be re-read once on the fixed placement.
- One event? No. NF13b is plan/type-frame only; place_lines is die-kit code. Order: place_lines (or view-size
  refusal, row 1 of section 5) first, then any die kit / unit evidence for NF13b.

## 4 NF13b form (COORD add-on)

Measured context: hd_tile R0 majority set 117 sites (in >= 50 % of 132 R0 instances), MY tiles match 70.5 of them;
HEAD-100: mean 145 sites per instance, 61/45 common to all, union 963/1,548; CLKSITE: 7 classes, two of them hold
120 + 120 instances, 70 sites deviate by forbidden rects, plus kit-laid legs, 26 parity nodes, tap q-cells.

| Form | Cost | Risk |
|------|------|------|
| (a) one entry side per type | Die tree re-topology for 264 tiles (R0/MY alternate, so one type-frame entry = alternating die feed direction), then CA + related-pair STA re-proof, all windows re-measured. Hours of proof, longer legs | CA worst margin is 104.6-106.4 against a gate of 100: 5-6 ps of room for a re-topology. High |
| (b) template of the two dominant classes (240 of 264 instances) + die legaliser restricted to template slots for every other cell | Islands about 250-300 holes = about 650 um2 of 743,510 (0.09 %); one hd_tile re-sign, which the 717.12 view needs anyway; kit code: legal set = template slots for minor-class cells, the 70 deviating sites, re-laid legs, parity nodes, tap q-cells; a few spare slots per region | Cells of 24 minor-class tiles move to the nearest slot: leg delta of one slot spacing, to be shown in the CA run (INFERENCE: inside the 9-23 ps the stamp already cost). Template must clear the union of per-instance forbidden rects. Low-medium |
| (c) class subtypes of hd_tile | 7 types to sign instead of 1, 7 views, 5 cores each; plan + bind + LATCHECK re-type; against the type-reduction rule | Classes are a property of the die tree: every tree change re-types the tile. Highest |

Recommend (b), with the rule turned round: the tree follows the template (slots are a fixed superset per type; the
die legaliser picks slots), not one list per observed tree. Same rule for the 13 other multi-instance types. (a) only
as a later tree clean-up; (c) not at all.

MX/R180 caveat (open, not NF13a): tile rows 3,840 = even, so MX/R180 maps row k to N-1-k with the opposite rail
polarity. Template slots must be defined in the TYPE frame (even rows, as measured for all 12 types) and the die
cell orientation composed with the instance orient. If the die legaliser instead asks for die-frame R0 rows, MX
instances get a 0.27-shifted set and a VDD/VSS rail swap. Affected: hd_serdes 5 instances, hd_st_str 2, hd_mesh_e.
Check before NF13b binds for those types: one placed-DB read per type, cell VDD pin y vs tile rail net at that y.

## 5 Ranked fixes

| # | Fix | Evidence | Owner |
|---|-----|----------|-------|
| 1 | Die kit refuses a closed view whose LEF SIZE != plan outline_um and falls back to the plan abstract; today that drops hd_tile (708.48 vs 717.12) and hd_st_n4 (1123.2 vs 993.6). Removes the nst4/lep0N overlap and the MY 8.64 class at the source | sizes, pin x, gen.tcl source, plan notes MEASURED | HEAD-MYTILE-1115 (check exists) + DIE-ROUTE-ABS-1 |
| 2 | Rebuild hd_st_n4 at 993.6 and hd_tile at 717.12 under the adopted plan; register the new views | section 2, 3 | HEAD-100 rows, KIT-OPS-5 launch |
| 3 | NF13b: hd_host_w islands from a tree built on the 40-tap plan (and the hd_host_e core-tap leaf); until then drop the 46 hd_host_w rects or accept them as dead holes | 12 vs 40 taps MEASURED | CLKSITE-RESERVE-1115 -> HEAD-100 |
| 4 | NF13b form (b), tree follows template; MX/R180 rail check first | section 4 | CLKSITE-RESERVE-1115 |
| 5 | Stamp: face keep-out (no die cell within 6 um of a face inside a bus pin window: 8 cells today, 28 within 0.81 um of a face), the 2 parity nodes on the site grid, PG slide on the pdn phase each kit really uses | 1B, 1D MEASURED; 1E INFERENCE | CLKSITE-RESERVE-1115 |
| 6 | place_lines outline-aligned as a proof aid only, with the window generator kept on the plan width; re-prep the 144 MY units | section 3 | HEAD-MYTILE-1115 |
| 7 | First kit of each of the 12 types on NF13a: read `OT_DIE_ISLANDS blockages=N` = island count and the DPL result (islands inside landing bands: hd_ctl 73, lep0N 63) | counts MEASURED; DPL risk INFERENCE | KIT-OPS-5 |

## 6 Stop list

- No outline growth of hd_st_n4 and no lep0N move for the 129.6: the plan is right, the view is old.
- No "windows mirror about LEF SIZE" together with place_lines outline alignment on the unpadded master.
- No PG-pitch placement snap row in NF13b and no chase of 1.62 as a PG phase.
- No hd_tile class subtypes; no union island list (963 + 1,548).
- No die kit that takes native_head_all.json as the tree on NF11+ plans before host_w (40 taps) and the host_e core
  tap are in it; the NF12 per-port windows were measured on a different tree.
- Do not count die-route DRC 0 of units over hd_tile or nst4/lep0N as seam evidence while the two stale views are in.
- No sign-off count from the 8 closed-view types on NF13a until rebuilt with the islands (stops are the owning
  lanes', not mine).

## 7 Not checked

- No signed DB opened (die-head-route-1/signed is gone from epyc10): real cells under the 751 new sites, and core
  positions inside the hd_tile view, are not measured.
- Pin rects of face pins next to the 28 edge cells; the stamp's actual PG clearance criterion; stamp code.
- Whether the type kit places landing ring flops before or after the island blockages.
- G0 / bind / LATCHECK were not re-run by me; the 233 warnings were not read.
- MY-tile M9 tap pins vs die M9 straps after the 8.64 shift; MX/R180 rail polarity on any placed DB.
