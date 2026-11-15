# FABLE-PLAN-B6B: review of S81 plan event B6b, 2026-11-14 21:00 PST

Reviewer: Fable, read only. Event: DIE-S81-92, epyc7 `/srv/opentallas-scratch2/claude/s81-b3-clk`, plan `ev/B6b1.json`
(1b5b7f0d9ada), sidecar `ev/side_B6b1.json`, run `run/b/B6b`, chain `chainB6b_92.sh`, scripts `b6b0.py` + `b6b1.py`,
overlay `ovl_b6b`. Base for all diffs: `ev/B3z2sc2.json`.

State at review end (20:59 PST): the B6b G0 (check.py) is still running; elab and bind have not started. So check 1 is
answered from the plan with the tool's own check function, not from the posted G0, and check 4 (bound RTL) is OPEN.

## Verdict

- The bind may run on as data.
- F2 BLOCKS adoption of the 14 TX latency rows (numbers and lane check below). Fix in B6c.
- F3b (7 trial feed-through rows) blocks adoption of those rows; DIE-S81-92 found it already and fixed it in B6c1.
- F1, F3a, F5 pass. F4 is open until the bind writes output. F6 is the B6c spec.

## What the plan changes (measured: full JSON diff B3z2sc2 -> B6b1)

| Change | Count |
|---|---|
| `partition_types` rows changed | 125: leaf 67, col_h9_r0 p5/p3/p1 30, col_h10_r0_p1 5, serdes 11, slice_station 10, kv_leaf 2 |
| `die.channels` | 33 -> 37 (4 jumper channels) |
| `die.io` bump_exclude | 2 windows |
| `die.layer_budget.type_m8_grant` | new, 24 types (col_h9_r0 p5 x12, p6 x12), ndr 4w |
| `latency.lanes` rows | 38 = 14 TX rows +1, 24 feed-through rows (+1; x_W4_in, x_W4_out, up_s_1N_L4 +2) |
| `partitions`, `ports`, `lanes` | 0 changed (no lane has `fixed_cycles` on TX; the 14 RX lanes keep 1) |

Schema validation of B6b1: 0 errors.

## F1. Jumper channels: clear the 22 abutment errors, routable (PASS)

Measured by running `check.check_abutment` from the B6b source tree on both plans:
- B3z2sc2: 90 abutment errors. B6b1: 68. Exactly the 22 "do not abut" errors are gone, 0 new, 0 errors on the 22
  jumper ports or on the 8 seam partitions. The 68 left are the old `fi_W*` channel-width rows of the control.
- Every one of the 22 ports meets the three channel conditions of check.py lines 536-546: its two ends are the channel's
  `between` pair, the faces are 51.84 apart (= `width_um`), and its pin layers (M5, M7) are channel layers.
- The four channel rectangles are 1442.88 x 51.84 um; none overlaps a partition.

Routability at die assembly:
| Channel | Ports | Bits | Vertical tracks (M3+M5+M7) | Ratio (limit 0.6) |
|---|---|---|---|---|
| s_0N_x03 / x04 | 11 | 4,943 | 92,685 | 0.053 |
| s_7N_x10 / x11 | 3 | 1,059 | 92,685 | 0.011 |
| s_7S_x110 / x19 | 3 | 1,059 | 92,685 | 0.011 |
| s_0S_x07 / x08 | 5 | 1,129 | 92,685 | 0.012 |
On M5 + M7 alone (the pin layers) the worst channel is 4,943 bits on 52,605 tracks = 0.094.
- Both ends of a port use one pin table (no type-side geometry), so each bit is a straight 51.84-um wire on its own
  track and layer. No via, no jog, no cycle.
- The signed layout agrees with the plan pins: signed `slice_station__t41` `6_final.def` (rtx-pro signed-export-1114)
  has ft7_o on M5/M7 at x 458.136-567.520, y 1226.784; the plan puts port `coll__s_0N_LP__lk_WN0__1` at die x
  9365.98-9475.36 = type x 458.14-567.52. Same for ft8_o to ft12_o.
- Not checked: the other three signed DEFs pin by pin; die PG or die clock shapes on M5/M7 inside the strips
  (inference: none, the die layers are M8/M9).

To confirm when G0 posts: abutment count in `run/b/B6b/g0` = control minus 22.

## F2. TX +1 row encoding is wrong: LATCHECK does not check TXPIPE or RXNEG (BLOCKS adoption of the 14 rows)

What B6b did: `fixed_cycles` stays absent on the 14 TX lanes, and the 14 `latency.lanes` rows got `cycles` and
`natural` +1 by hand (b6b0.py).

Measured:
- `Plan.lane_latency()` on B6b1 gives the old value for all 14 lanes; the table says one more. Examples:
  coll__s_0N_LP__lk_WN0 table 34 / plan 33, WS2 72 / 71, EN3 57 / 56, ES1 62 / 61. bus_pads conflicts 0.
- G0 compares exactly these (check.py lines 1365-1370): expect 14 new `[latency]` errors "table says N cycles, plan
  gives N-1" in the B6b G0.
- The bind reads `cycles` from the table (bind.py line 1599) and builds the receiver pad as table cycles minus
  boundary, feed-through and landing stages (bind.py `lane_pad`, line 5998). So the +1 becomes a real `u_lpad` D1
  register bank on the serdes input bus of each TX lane. That is the same hardware as B6a's `fixed_cycles` 1.
- LATCHECK counts u_bout, u_bin, pads, u_lpad, u_ist, feed-through and landing instances only
  (lane_asbuilt_latency.py header). It will pass 14/14 by construction and never sees `u_txl` or `u_rxf`.
- Result: TX grows by 2 registers (bind pad + TXPIPE row) while the bench measured +1 (88 -> 89).

Lane check:
- SERDES-TXPIPE handoff and READY 20:5x: "stages are inside the column; LATCHECK counts u_bout/u_bin/pads/ist/ft/
  landing only", "no lane table change".
- DIE-S81-92 21:3x: "in-core register priced in the row, LATCHECK checks it". The second half is not true.
- FABLE-PLAN-B6A F3 asked for rows -1 (back to natural), not for a hand +1.

Fix for B6c:
1. Restore the 14 rows to the B3z2sc2 values (cycles = natural; no `fixed_cycles`). Then G0 latency is clean and no
   pad is built.
2. The check that covers TXPIPE and RXNEG is the link bench, not LATCHECK: `tb_s81_col_rlat` with EXPECT_LAT 89 on
   the bound `ot_pdie_serdes_col.sv` with the bind define set (RST_TREE, TXPIPE, RXPIPE, RXNEG). Post it as a B6c
   gate next to LATCHECK.
3. Inference: the token schedule takes the link latency from a link constant, not from this lane table; I found no
   such key in the plan and did not find its consumer. SERDES-TXPIPE to name the constant that moves 88 -> 89.

## F3. Leaf merge

### F3a. Three-way sidecar merge and signed types (PASS)
- Re-running the merge of b6b1.py (mine `ev/side_z2c.json`, theirs `side_B6s.json`, base `side_z2_92e2_fix.json`)
  reproduces `side_B6b1.json` exactly: 1,528 leaves changed.
- b6b1.py clears its conflict list before printing it, so "conflicts 0" is printed whatever happens. Recomputed: there
  is exactly 1 real conflict, `collector/types/ot_s81sl_leaf__t72/local_sources`, the one the script takes from B6s on
  purpose. Fix the script (print before `conf.clear()`), no data change.
- Only `collector.types` differs from mine: 113 rows; all 114 delta types equal B6s. All other sidecar sections equal
  both inputs.
- Plan rows: 114/114 delta rows equal `B6s.json` (107) or `B6t_ft.json` (7). None of the 114 types was changed by
  DIE-S81-92 between 92e2 and B3z2sc2 (its 60 own changes are col_h9_r1/r2, col_h10_r1/r2), so the overwrite lost nothing.
- Signed index (rtx-pro INDEX.tsv, 98 S81 names, 36 are plan types): 36/36 plan rows equal B3z2sc2 and equal 92e2;
  36/36 sidecar rows equal mine and 92e2-fix. No signed type is in the 125 changed rows. Re-key 0.
- The 10 changed slice_station types are all unsigned.

### F3b. The 7 feed-through rows are a trial (blocks those rows; already fixed in B6c1)
- B6b1 took 7 type rows and 24 latency rows from `B6t_ft.json`. S81-LEAF-PLAN 20:45: that 27-slot chain "is NOT for
  merge"; the real increment is B6t = B6s + 2 type rows (t7 ft3, t53 clb66fa5cb ft0) + 2 latency rows.
- Measured: 7/7 of these rows differ from the final `B6t.json`; the B6b1 sidecar has the B6s rows for t7 and t53, B6t
  has new ones.
- DIE-S81-92 posted the same correction (22:1x) and built `ev/B6c1.json` ae869d5e0b7d. I did not review B6c1.

## F4. Bound RTL greps (OPEN: no bind output)

Before the bind, measured:
- 243 overlay files differ from the seed tree; 238 are in `run/b/B6b/src` byte for byte; the other 5 are the
  LIMIT-BIND-1 files applied after the overlay (taps.py, cap_estimate.py, kit_preflight.py, native_cell_cap.tcl,
  check.py), as intended.
- RTL and bind inputs in the tree: `ot_pdie_serdes_col.sv` sha1 8c6e192433f9 (RXNEG form), `ot_s81sl_vp.sv` sha1
  72caa2932c06, `die_b178_lfcs.v` sha1 b22eb41e4167, l1f_ba0/ba1/bf views.
- `asbuilt_run.json`: base = `run/b/B6b/src`; defines hold RST_TREE, TXPIPE, RXPIPE, RXNEG, GUNIT_FWDOWN; files list
  the col, vp and l1f sources.

After BIND_RC, DIE-S81-92 posts:
- per `s81p_serdes__t*` module (11): `u_rxf` present with the negedge row; `u_txl` at 3 rows; `u_lpad_*` D on the TX
  input bus (expect D1 with the B6b rows: that is F2);
- l1f FWDOWN form: 24 `g_wq` groups, 21 reset regions;
- `OUT/asbuilt_sources.json` sha of col.sv, vp.sv, dsdv_gunit_l1f.sv equal the overlay;
- the 16 slice instances carry the LF_CS depths of `ev/lfcs_B6b1.json` (79 leaves);
- LATCHECK rows for the 24 feed-through lanes and xtier__s_0S_C__s_0N_C, up_s_1N_L4.

## F5. Serdes tap cap: no cap (settled)

- FABLE-SERDES-STRUCT section 0 item 3 is the final text: taps by pipeline group, delete OT_TAP_MAX_SINKS. It
  WITHDRAWS "cap 1000 sinks" from its own section 3 item 1. That cap was per tap, never per island. There is no
  per-island 1000-sink cap.
- Reason given there (measured on t12): the cap pass cut tap clk_t10 from 5,419 to 3,000 sinks and split the encoder
  pipeline over two taps (-157 pair).
- The same section also withdraws: "macros as sinks of the nearest leaf" for u_chn, and the HEAD island position
  "around the port at x 1106".
- B6b encodes it as `clock.tap_max_sinks` 100000 on the 11 serdes types. Correct: an absent key means 3000
  (gen_phys.py `_tap_cap`, line 3061), so the key must stay.
- Advisory: until B6c adds the pipeline grouping and the island, B6b serdes rows are cap-free nearest-tap assignment.
  Do not build serdes kits from B6b rows.

## F6. B6c plan key spec and gen_phys readers

Line numbers are for `run/b/B6b/src/tools/die_plan` (gen_phys.py sha256 a69c86f00f4e, schema.py 75fe839f0fc5).
Three of the five items need no new reader.

### 6.1 Balance target 450: existing key
- `partition_types[serdes__t*].clock.insertion_ps = 450`, `insertion_basis = "FABLE-SERDES-STRUCT s0.5"`.
- Reader: `insertion_binding`, gen_phys.py 2824-2841; exported at 5145 (OT_TAP_TARGET_PS) and 5146-5147 (vclk TT/FF;
  FF = 0.81 x 450 = 364.5 unless `insertion_ff_ps` is given); clock_binding.json at 5467.
- The binding returns `early_tap_ps` = 450 - 250 = 200. Inference: the die clock must then land the serdes taps 200 ps
  early, or die STA must use the 450 contract; I did not trace the die-side consumer.

### 6.2 Tap pitch <= 200 um: existing keys
- Explicit taps over the placed logic: `clock.added_taps = [{name, xy}]` at pitch <= 200 over the island and the lane
  corridors (kitH island 760 x 304 um = 4 x 2 taps). Mode stays `grid+explicit`.
- Or the grid: `clock.tap_pitch_um = 200` (schema.py `tap_pitch`, 2377-2380; gen_phys.py 5180). On 2885.76 x 1226.88
  that is up to 84 M9 tap ports per type against 3-28 today; count them in the die clock tool first.
- Recommendation: explicit taps. The finding was that the taps sit on the die grid and not over the logic.

### 6.3 Taps by pipeline group: existing keys
- `clock.tap_group = {"re": "(?:^|[/.])(u_enc)[/.]"}`; reader `tap_group_exports`, gen_phys.py 2913-2928.
- `p_d` + `u_txl` row 0 on one tap: `clock.tap_pair_affinity` (gen_phys.py 2931). One regex cannot give two names
  one group key.
- Caveat in clock_taps.tcl 136-140: compact blocks only, never station rows.

### 6.4 Recovered-clock island and early u_chn tap: one new type key, one new optional field
The rck root and the separate u_chn net already have a reader: second pad-clock entries (pad_clock.py; hook written at
gen_phys.py 4987-4992; schema.py 1394-1402).

```
partition_types[T].clock.pad_clock.pins[io_pma_rck].entries = [
  {"name": "rck_isl", "xy_um": [x, y], "stations_um": [[x, y], ...], "cell": "<clock buffer>",
   "region_um": [[x0, y0, x1, y1]],
   "sink_pins": [{"module": "ot_s81_pma_rxm", "pin": "pma_rck"},
                 {"module": "ot_sram_1r1w2c_64x546_m1", "pin": "wclk"},
                 {"module": "ot_sram_1r1w2c_64x546_m1", "pin": "rclk"}],
   "evidence": "FABLE_SERDES_STRUCT_s0_1"},
  {"name": "rck_chn", "xy_um": [x, y], "stations_um": [], "cell": "<clock buffer>",
   "region_um": [[one empty row at the u_chn clk pin]],
   "sink_pins": [{"module": "ot_s81_kp4_dchn", "pin": "clk"}],
   "evidence": "FABLE_SERDES_STRUCT_s0_2", "min_early_ps": 175}
]
partition_types[T].rck_island = {"rect_um": [x0, y0, x1, y1], "clock": "io_pma_rck",
                                 "inst_re": "u_core[.](u_dec|u_rxf|u_lrx)", "release_before_dpl": true}
```

New optional entry field `min_early_ps` (number >= 0): the entry's macro pin must be clocked at least that long before
the earliest register clock pin of the island entry.
- pad_clock.py 29: keep ENTRY_KEYS, add `ENTRY_OPT = {"min_early_ps"}`.
- pad_clock.py 152: accept `ENTRY_KEYS <= set(e) <= ENTRY_KEYS | ENTRY_OPT` (today "exactly").
- schema.py 1396-1402: add property `min_early_ps` (not required).
- pad_clock.py `write_contract` (438): write `rck_early.txt` rows "entry inst pin min_early_ps".
- gen_phys.py 5284: `cfg += rck_early_exports(P, tn)` next to `rck_band_exports` (OT_RCK_EARLY); postcts_gate.tcl
  reports the measured lead per row. Report only: under the academic profile it does not block.

New type key `rck_island`: every std cell matching `inst_re` in the `clock` fan-out goes into one placement region
`rect_um`, released before detail placement (the HARD-S81-SERDES-1 G3 DPL-0033 class).
- Reader: new `rck_island_exports(P, tn)` right after `rck_band_exports` (gen_phys.py 583-593); call at 5284; kit file
  copy and hooks in the block at 5383-5388 (after the rck_band copy), into face_flops.tcl and face_flops_release.tcl as
  kitH2 does.
- Schema: beside `rck_band`, schema.py 405.
- G0: rect inside the outline, outside `clock.keepouts_um`, holds the u_chn hard core.
- The hook files `serdes_lanes.tcl` / `serdes_lanes_release.tcl` are on branch claude/hard-s81-serdes-1-1113
  (04298c1baa1), not in the B6b tree (only serdes_gpl_fence_release.tcl is). They must be in the overlay.

Geometry (measured, kitH/kitH2 on serdes__t2, epyc9 hard-s81-serdes-1):
- island 245..1005 x 640..944; u_prx (244.536, 951.48) MX; io_pma_rck pad (257.952, 1090.8);
- u_chn (280.8, 680.448) R180; dmem (600.48, 650.172); cmem (790.56, 650.172);
- B6b1 still has t2 u_chn at (864, 95.04). B6c must move the u_chn hard core and the two SRAM sites by
  (-583.2, +587.52) on t2, and the same way on the other 10 types (the core moves, its shape does not).
- Per type: anchor the island at the type's io_pma_rck pad x, directly under the rck_band top.
- "pins x 1603-2412" is the HEAD hd_serdes pma_rx pin range (FABLE-SERDES-STRUCT section 0, HEAD item 1). It is not an
  S81 number. I did not measure the S81 u_prx pin x range per type (no rxm LEF found in the kit by my search).

### 6.5 type_m9_grant: new key, generalised m8_grant
```
die.layer_budget.type_m9_grant = {"enable": true,
  "types": ["ot_s81sl_leaf__t34", "ot_s81sl_leaf__t9", "ot_s81sl_leaf__t73", "ot_s81sl_leaf__t75"],
  "ndr": "4w", "guide": "<die M9 route guides>", "note": "..."}
```
Later: t28, t13, t7, t71 (S81-LEAF-PLAN order). A type in this list must also be in `type_m8_grant` (M9 needs M8 vias).
- Schema: sibling of `type_m8_grant`, after schema.py 271.
- Reader: gen_phys.py 4873-4877. After `m8g = MG.kit_grant(P, tn)` add the M9 grant and set `top = "M9"`.
- Obstructions: loop at 4883-4900 already walks to `top` and schema.PART_PG_BANDS has an M9 row (schema.py 2703); add
  the M9 twin of lines 4886-4888. Write `m9_grant.json` at 4927-4929. MAX_ROUTING_LAYER at 5027 follows `top`.
- m8_grant.py is fixed to M8 and to a horizontal layer (lines 57, 66-69, 79, 106-111, 137). It needs a layer
  parameter; M9 is vertical.
- run_kit abstract fix (gen_phys.py 6273, `m8_grant.py fixlef`) needs the M9 obstructions too.
- Blocking precondition (inference, not measured): S81 die use of M9 is clock spine + PG and every type tap pin is on
  M9 (`clock.layer` M9). Without `guide` the grant subtracts PG only. Require the die clock M9 guides, or a halo
  around every tap pin and spine leg, before any type routes on M9.

### Also for B6c
- F2 fix (14 rows back to natural) and the rlat gate.
- Keep `tap_max_sinks` 100000.
- b6b1.py conflict print.

## Not checked
- Posted G0 of B6b (still running); bound RTL; B6c1; the B6s bind result on epyc8.
- p5/p6 M8 grant content (existing key; 24 types listed, no kit generated here).
- Die-side handling of a 450-ps serdes insertion.
