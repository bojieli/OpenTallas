# FABLE-PD-S81 D8h structural review (FABLE-PD-S81-D8H, 11-19)

Subject: `plan_d8h_d.json` fec6ef9b15d5 (epyc8 `/srv/opentallas-scratch2/claude/s81-die-r3-e8/d8h/`), diffed against the D8g plan
(`kw45/src_s81_pin_3c913dbdfb23_d8g_1117_work/.../plan_h2_2249.json`). COORD moved the review from c to d during the run.
Read-only. Estimator and review only: nothing here holds a build (r703).
Labels: V = I measured it on plan d or on the named file; R = read from a lane post; I = inference.
Scripts and outputs: epyc8 `/tmp/fable_pd_a1.py a2.py a3.py a3b.py`, `/tmp/fable_pd_pc/` (precheck on d, 395 types, 461 s, 544 findings).

## What d holds (V, key diff against D8g)

| rows | in d | not in d |
|---|---|---|
| interior taps | bk_sel__t2 +41, gunit__t1 +29, svc_hi_dsdv_svc_rs__t2 +22 (TAP-EDGE grid form) | tap_resolve tables for lepe mu/nh, seqhost, lepw_mu, lepw_mus |
| tap cap 1,000 | `tap_max_sinks` on 116 types | the 24 split rows (125 taps); the leaf / kv_leaf rows (76 types) |
| CBC relays | relay_branch / internal_stations / relay_sites / relay_depth on 234 types | 52 FT-station lanes (0 of 873 lanes changed, `latency` equal) |
| reset | phy__t1 port_relays 8 x 14, serdes__t12 bank_taps 9 | CBC bank_taps rows of the other 388 types |
| gunit shift | 6 cores -0.144 um | |
| type_template | 216 col types | |
| lepe reach row | | all 4 items |
| col_h9_r1 trunk | via the CBC generator (60 types) | |

## Ranked fixes

### 1. gunit__t1: three interior taps are 0.144 um inside the core halo after the shift. This fails G0 and the tap solve of 331 types.
- V: `g0_d/g0_report.json` FAIL, 10 errors, all "gunit__t1: explicit tap clk_t28 violates outline/halo/tap spacing".
- V: clk_t28 (171.72, 846.72), clk_t29 (541.08, 846.72), clk_t30 (910.44, 846.72) sit 8.496 um under `g_l1f[1..3].u_l1f.u_f`
  (bottom 855.36 -> 855.216). TAP_CLEAR is 8.64. The taps were solved on plan a, the cores moved in plan c, and c had no G0.
- V: precheck on d returns TAP-ERROR with this message on 331 of 395 types (all col, leaf 70, slice_station 46, serdes 10, kv_leaf 5):
  one bad gunit table stops the tap inventory of every type that resolves through it. The strict bind r1 now running on d will
  not give a usable PRE.
- Fix (S81-DIE-R3): apply the core shift first, then re-run `d8h_taps.py` for gunit (or move the three taps to y <= 846.576),
  and re-run G0 before the next bind. Order rule for every later event: core moves, then taps.

### 2. bs0 rows on 18 types are now listed twice: the bind raises "bit runs overlap".
- V: col_h9_r0_p4 (6 types) and col_h9_r0_p5 (12 types) carry 4 `relay_depth` sink rows on `u_r0_u_bs0` (i_x0 twice, i_x1 twice):
  the hand row renamed by `d8h_compose.py` (bits [0,282] / [0,265]) and the generator row (S81-RLYBR-1, whole port).
  These are exactly the 18 types in `compose_report.json` `bs0_renamed`.
- V: `bind.py` `relay_depth_sink_map` (line 947-954) raises BindError when two sink rows of one (inst, port) overlap.
- Cause: CBC `plan_branch.json` was generated on c4f, where the hand row named `u_bs0` matched nothing, so the generator added
  its own row. p3 / p6 (name `u_bs0` correct) have 2 rows, not 4.
- Fix (S81-DIE-R3): drop the 36 hand rows on these 18 types; keep the generator rows. Do not rename.

### 3. The 0-cycle relay fold adds internal cycles on 6 col families; no lane K changes. LATCHECK must show them.
- V: sum of `relay_depth` D per type, D8g -> d: col_h10_r0_p1 3 -> 13, col_h10_r0_p4 0 -> 3, h9_r0_p1 3 -> 7, p2 1 -> 5,
  p3 15 -> 17, p4 5 -> 9 (2 of these are the duplicates of fix 2), p5 5 -> 9 (same), p6 15 -> 17. h9_r1, h9_r2, h10_r1, h10_r2: unchanged.
- V: `lanes` and `latency` of d equal D8g. CBC `cbc_summary.md` says "relay_depth rows after 0-cycle fixes: 0", which does not
  match the plan it produced (162 far copies carry D 1 or 2).
- I: these are core-input pipe cycles priced by `bind_core_input_pipe`; if a far copy sits on a path with a reconvergent
  partner (bs0 i_x0 against t1 on the same copy), the bind has to pad the partner or LATCHECK fails.
- Fix (CBC-RULES-1119): correct the summary line and list the far copies with D per family. S81-DIE-R3: read
  `internal_pipe_check` and LATCHECK of the next bind per family before publish; h10_r0_p1 (+10 per type) first.

### 4. Lepe bank moves and the lepe tap table collide. Take them only as one re-solved pair.
- V: reach-row item 3 puts `g_rx[1]` bank[3] at (414.72, 293.772) and bank[4] at (483.84, 293.772) (51.4 x 20.8 um).
  Four taps of `FABLE-FIX-S81-LEPE-taps.json` (lepe_mu_LP__t2) fall in or within 8.64 um of them: clk_t68 (488.16, 295.92) inside
  bank[4], clk_t51 (483.84, 311.04) on its edge, clk_t45 (535.68, 317.52) and clk_t33 (423.36, 319.68) in the halo.
- V: without the moves all 11 lepe-lane tables validate on d (`explicit_tap_sites` / `grid_explicit_sites`), 0 name collisions,
  except bk_sel (fix 5).
- Fix (FABLE-FIX-S81-LEPE): re-run `solve_taps.py` with the 4 moved banks as obstacles and hand over one row (moves + table).
  S81-DIE-R3: take neither half alone.

### 5. bk_sel__t2 has two interior tap tables from two lanes with the same names.
- V: d holds the TAP-EDGE table clk_t8..clk_t48 (41 taps, static pitch rule). The LEPE-lane table adds clk_t8..clk_t16
  (9 taps, from placed registers): 9 of 9 names collide and `explicit_tap_sites` rejects it ("local tap names/order").
- Fix: one owner. Recommended: keep the TAP-EDGE table in D8h (it is in the plan and legal); FABLE-FIX-S81-LEPE withdraws the
  bk_sel table, or re-solves on d starting at clk_t49 once a bk_sel kit has a CTS log.

### 6. Tap cap 1,000 without the taps does not fix the over-cap types, and it re-keys 46 slice_station types.
- V: d sets cap 1000 on 116 types; the 24 types with over-cap taps keep them. Precheck on d: leaf t28 13 taps over
  (clk_t12 6,863 of 53,261 planned sinks on 16 taps), leaf t29 2,662, slice_station__t45 1,936, serdes__t14 1,232,
  eng 1,121, iqf 1,028, svc_lo_rs__t6 1,108.
- V: the leaf rows (`S81-LEAF-TAP-ROWS-cap1000.json`, 76 types, clock keys only) apply on d and validate: 76 of 76, same outlines.
  They are not in d.
- V / R: 38 of the 46 slice_station rows have no over-cap tap; 35 slice_station types are signed (FABLE-TYPE-REDUCE-S81-REST).
  The cap changes their kit input for no planned gain.
- Fix (S81-DIE-R3): take the 76 leaf rows in D8h (FABLE-FIX-S81-LEAF owns kv_leaf t1 / t4 too; the LEPE-lane kv_leaf tables at
  target 1,400 are superseded). Leave `tap_max_sinks` as it was on slice_station types with no split row.

### 7. Families that still fail r713 with no row in d
| family | measured | owner |
|---|---|---|
| lepe mu / nh LP, seqhost, lepw_mu LP | per-tap mean insertion spread 302 to 315 ps (R, tap_resolve); tables valid on d (V) but not taken; cap 1000 alone changes nothing on clk_t6 with 22,199 sinks | FABLE-FIX-S81-LEPE -> S81-DIE-R3 |
| ot_s81sl_leaf__t25__cl431c660f | TAP-EDGE: 9 local taps span 26 % of the width (V, precheck); row exists in the leaf file | S81-DIE-R3 |
| leaf, kv_leaf FOLD | 15 to 16 kits per host in the hourly kit scan (R); a flow fix, no plan row can fix it | FABLE-FIX-S81-LEAF |
| slice_station__t51 | native macros still in the plan (2 hard_cores, 73 explicit taps) (V); preflight PLAN-SRC-MACRO every attempt (R) | S81-DIE-R3 |
| reset bank distance | CBC rows: 388 of 390 types have a bank reset hop over 405 um (to 3,506 um, svc_lo_rs) with a 0-cycle bank_taps row; d takes 2 (V). Failure measured only on phy and serdes__t12; leaf recovery is +72 ps (R) | S81-DIE-R3: take with types already changing (col 216, leaf 75); skip signed |
| FT REACH | plan hop 0 of ft slots 455 to 495 um on leaf t75, svc_hi_rs t5, svc_lo_rs t7 (V, precheck); placed scan pending | S81-DIE-R3 |
| col_h10_r1 | 12 station hops 423 um after re-aim (V) | S81-GEOM-OPUS |
| BOUNDARY-REG | 192 types with port bits with no register within 50 um, mostly ft outputs (leaf t8 5,820 bits) (V, precheck) | CBC-RULES-1119, after the FT rows |
| serdes rck tree, north taps | no rck_island / regional-root key in d (V); FABLE-PD-S81-0855 fixes 3 and 4 open | S81-CORES-OPUS |

### 8. Checked and clean
- type_template: 42 layout keys before and after the CBC rows; no base group is split by a per-position row (V; 51 with the RTL key, R).
- New relay / station sites (30,400 on 234 types): 0 outside the outline, 0 inside a hard core (V). 12 single reset-station
  flops (h10_r0_p1, h10_r0_p4) sit 2.4 um from a tap: harmless.
- phy__t1: 112 relay sites, hops 77 to 377 um, depth 15 against the 64-cycle boot hold (V). Sites lie on the outline edge
  y 1226.88; the proof kit decides.
- col_h9_r1: proof kit TT -13.62 from -277.82 (R); 20 ends left, inside the -42 gate.

## Bind / LATCHECK summary
1. G0 fails now (fix 1). 2. Bind will fail on 18 types (fix 2). 3. Cycle rows without lane K (fix 3). 4. Flow, not plan: the D8f
post-apply bind failed with "no asbuilt.json" (ELAB_RC 2) at 02:40; the same wrapper would fail after D8h.
5. Precheck RESET-FANOUT still flags phy and serdes__t12: it does not read `port_relays` / `bank_taps` (PRECHECK-1119 tool gap).

## Stop list
1. Stop solving taps before core or bank moves of the same type are in the base (gunit, lepe).
2. Stop renaming hand rows onto instances the generator already covers; drop them.
3. Stop two lanes writing tap tables for one type (bk_sel; kv_leaf t1 / t4).
4. Stop setting `tap_max_sinks` 1000 on types with no added tap, above all on signed slice_station.
5. Stop running the strict bind (about 90 min) on a plan whose G0 has not passed.
6. Stop quoting "0 cycles" for the relay fold: far copies carry D 1 or 2.

## Not checked
- No render: D8h d has no kit; the whole-die visual review is still owed before publish.
- Bind r1 on d was in elaboration when I stopped; I did not see its result.
- Whether the far-copy cycles reconverge correctly (fix 3) is inferred from the plan, not from bound RTL.
- Which slice_station types are signed today (count 35 is from a lane handoff).
