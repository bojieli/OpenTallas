# FABLE-CLOSURE-STRATEGY 2026-11-15 05:1x PST: technical closure levers for S81, HEAD, QC, KV

Read-only review. Technical physical design only. HBM is parked. No job, plan or kit was touched.
Previous version (03:2x, with the 01:3x review below it): the commit of this file before this one in the `~/coord` history.

Sources: FABLE-PD-S81-0335 (A-C), FABLE-TRIAGE-HEADKV 15-21, FABLE-KVOVF 8-13, FABLE-PD-QC-0300, the queue to 05:14,
`failure_breakdown.py` (05:10), `autopilot/kit_wave_stages.tsv` (05:07), and my own reads of the run directories below.
MEASURED = read by me at 05:1x from a log, table or process list. REPORTED = from a lane post. INFERENCE is marked.

`failure_breakdown.py` technical classes at 05:10: timing after route 3 (S81 slice_station__t47; KV kv3_phy_v1, kv3_sys_SD),
place error 2 (S81 slice_station t17 +1). Everything else is running, held or a flow class.

## 0. Four things the lanes have not seen

1. The HEAD region route units do not converge, and the residue is not a routing problem. Three units of 141 clock
   nets each stand at 2,750-2,850 violations after iteration 2, with the same count on five layers (lever 2).
2. QC and KV types go into detail route with setup already 130 to 1,550 ps negative. The route then runs for hours
   on a design that cannot pass the -42 ps gate (lever 3).
3. The S81 count-aligned plan passes on the adopted clock kit, but its compose step fails on the hard PHY wrappers
   and reports 5.6 million added flops. The 350 types wait on that (lever 1).
4. QC has no row on the adopted S4k event yet, and 13 KV types fail generation on one tool error (lever 4).

## 1. Levers, ranked by types or dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Count-aligned compose: one landing per hard PHY wrapper; explain the 5.6 M flops | 350 held types | DIE-S81-92, KIT-OPS-6 |
| 2 | HEAD, KV (then S81, QC) | Die route units: remove the fixed-shape violations before volume | the DRC gate of every die | DIE-HEAD-ROUTE-1, DIE-KV-ROUTE-1 |
| 3 | QC, KV | Read setup after CTS; start the structural fix then, not after the route | about 20 running types now, the family behind them | DIE-QC-103, KV-102 |
| 4 | QC, KV | Generation: S4k rows, pruned bind sources, `tap_offset_table` | QC 36 types, KV 13 types | KIT-OPS-5, GENBUG-IMPL, KIT-OPS-6 |
| 5 | S81 | Leaf kits fail before placement on B6gsh itself (3 defects) | 79 leaf types, the LT2 proof | S81-LEAF-PLAN, GENBUG-IMPL |
| 6 | KV | kv3_hg / hgi: kvgeom7 with a two-level reset tree and a start-broadcast stage | 19 hg / hgi types | KV-102, FABLE-KVOVF |
| 7 | HEAD | NF adoption: relay pin lists differ between copies of hd_spn and hd_spn_wshim_rx | 26 types | HEAD-99, HEAD-CLKFEED-1 |
| 8 | QC | cb family: S4p/q/r, and the ring-to-load site form that has no owner | 17 cb types | DIE-QC-103, CLAND-BIN |

### Lever 1. S81: the count-aligned compose

Evidence:
- REPORTED (DIE-S81-92 05:13, epyc7 `die-clk-s81-b6/s81/B6gsh/ca_g3f`): on the adopted B6gsh clock kit with measured
  fall arrivals: 2,330 crossings, 0 without K, depth 4/8/16 = 1,377/953/0, worst lo 104.5 ps, start tree 555/555
  clean (15 unclean with rise only). Plain and strap-form binds pass with 0 violations. Same form on B3x2d:
  1,683/647/0, 556/556 clean.
- REPORTED (DIE-S81-92 05:09, `ca_compose/compose_report.json`): compose of B6gsh with that table fails:
  `hard partition phy_hbm: exactly one landing per hard wrapper supported, got dfi_i0..dfi_i7`. Requirements line:
  9,320 new scalar pins, 5,612,245 added live storage flops, 395 types. Today's sidecar has 993 crossings.
- The hop-limited form fails (66 start edges), so the plan has no reach check on its 555 start hops.

Root cause: the identity part map gives every hard PHY wrapper several regions, so one wrapper gets several
landings. The table also moves 1,337 crossings from the fixed +3 form to rings. INFERENCE: the 5.6 M flops are
ring storage counted at full bus width times depth for all 2,330 crossings, about 2,400 flops per crossing.

Fix (DIE-S81-92; KIT-OPS-6 for the tool):
1. Hard wrappers keep one landing: merge each hard partition's regions into its wrapper region in the region table
   (the `merge_hard` form), then re-plan. Check that the 8 `dfi` buses still get one K each; if their windows do
   not overlap, they stay on the fixed +3 form, which the PHY has today.
2. Before the bind, split the 5.6 M by type and by depth. Depth 8 on 953 crossings is the cost. Give the per-type
   added area against the free area of the 350 types; a type over its outline is a plan change, and it must be
   known before 350 kits regenerate.
3. Start-hop reach: list the start hops over 405 um from the plan (66 edges fail the limit). Each needs a retime
   site or is declared and measured; do not leave it unread.
4. Then bind + LATCHECK, release the 350 once.

### Lever 2. Die route by region units: fixed-shape violations

Evidence (MEASURED, epyc2 `/srv/opentallas-scratch3/claude/die-head-route-1/head/p20nc_gate`):
- `units/units.log`: 326 units, 44,549 nets all assigned, 1 merge, 11 passes (sizes 40/42/48/42/40/40/32/21/14/5/2).
- Three units, 141 own nets each, started 03:56-04:03. Form (a) full die: iteration 0 ends at 3,833 / 3,276 / 4,151
  violations; 11.6-12.0 GB; still in iteration 1 after 75 min. Form (b) crop (6.7 mm2): the same iteration-0 counts
  within 1 (3,887 / 3,276 / 4,152), then 2,856 -> 2,852 (u198), 2,786 -> 2,800 (u201), 2,758 -> 2,769 (u261);
  3-7.6 GB; in iteration 3 after 70 min.
- u198_b after iteration 2, by layer: Short M1 691, M2 252, M3 252, M4 252, M5 252, M6 252, M7 298, M8 183;
  Metal Spacing M1 50, M8 274; Min Step M8 79. The own nets have 5 / 20 / 3 / 3 / 26 um of wire on M3-M7 and
  6.4 / 4.6 mm on M8 / M9. The database has 9 fixed shapes on M2 and 9 on M3 in the region.
- No marker file is written, so the violating shapes are not named.
- The full-die run (`p16g/drt7_small96_TT`) started iteration 0 at 03:38 and has printed nothing since (95 min).

Root cause: the residue is the same on every unit and does not fall between iterations, so no number of
iterations reaches 0. INFERENCE: 252 shorts on each of M2-M6 with almost no wire there is one via stack per
terminal, dropped from M8 to a pin shape on M1 through the partition abstract (about 250 terminals per unit).
The M8 part (spacing 274, min step 79, short 183) is the landing at the M8 pin against the region PG grid.
The crop form agrees with the full-die form at iteration 0, so the split itself is sound.

Fix (DIE-HEAD-ROUTE-1; DIE-KV-ROUTE-1 uses the result):
1. Rerun one unit in form (b) with `-output_drc` and 3 iterations. Group the markers by layer and by the two
   shape owners (own net, PG, abstract pin, abstract obstruction). This takes about 30 minutes and decides the rest.
2. If the M1-M7 shorts are stacks to lower pin shapes: the die abstracts must carry one pin shape per die pin, on
   the plan pin layer (M8, or M7 for the 133-168 clock pins the wave reports "on M7, not M8"), and no lower shape.
   Regenerate the abstracts; no type is rebuilt.
3. If the M8 part is pin against PG: cut the region grid over the pin window (the `clock_entry_pg_cut` form the
   kits already use inside a type).
4. Do not start the 326-unit volume, and do not start KV, before one unit ends at 0. A pass costs about 440
   thread-hours.
5. Use form (b) for volume (same counts, a third of the memory, faster). Stop the full-die run and the three
   form (a) units once item 1 is posted.
6. Timing of (b): at 0 violations a unit should take about 3 iterations. From today's 20-25 min per iteration,
   11 passes are about 12-14 h of wall time if each pass has its threads. That closes HEAD on 11-16, not today,
   and only after items 1-3.

### Lever 3. QC and KV types: setup is lost before the route starts

Evidence (MEASURED, `run_route.log` / `pregrt_ff_hold.log` of the running kits, line `OT_PREGRT_FF_HOLD ... setup_wns`):

| die | type | setup before route, ps | cells | note |
|---|---|---|---|---|
| QC | cbn_q11 cl49ae4555 | -861 | 365 k | 10,948 hold cells |
| QC | sle_fw_v2 cl69f5e854 | -453 | 403 k | hold still -92 ps on 515 endpoints |
| QC | slw_fw_v3 | -380 | 405 k | |
| QC | sle_st_b_v2 clfde1249e | -302 | 469 k | |
| QC | slw_fw_v2 cl8537f156 | -133 | 398 k | |
| QC | slw_su_l1 clcc9d0155 | -84 | 122 k | |
| QC | coll_ftc / coll_n / sle_su_l0 | -41 / +22 / +28 | | can pass |
| KV | kv3_pv_v1n | -1,546 | 824 k | 60,255 hold endpoints |
| KV | kv3_hgi_v3 | -1,160 | 434 k | |
| KV | kv3_hgi_v2 cle0015330 | -641 | 310 k | |
| KV | kv3_io_cor | +54 | 278 k | can pass |

- Wave table, last 48 h: QC has 5 failures at place or route (4 of them host events) and KV has 4. Neither die has a
  congestion or DRC class. The types do not fail early; they run 2-15 h and end as "timing after route".
- The gate is -42 ps. Of 13 running types read, 4 can pass.
- Limit: these are placement-parasitic numbers from the kit's hold-repair step, both corners. On the cb types part
  of the -861 may be the early-tap credit (tile clk-to-q 923 ps). Not split by path family by me.

Root cause: the long zero-logic hops and unstationed buses already measured on kv3_hg / hgi (FABLE-KVOVF 11-14)
and on the cb family (FABLE-PD-QC-0300) exist in the other families too (fw, st_b, su, pv), and nobody reads them
until the route ends.

Fix (DIE-QC-103 for QC, KV-102 for KV; one Sonnet lane per family):
1. Now: for every type with a `4_cts.odb`, run the endpoint listing FABLE-KVOVF used (`fable-kvovf/sta_t_hgi2`,
   10 minutes each): families, endpoints, worst slack, straight distance. Post one table per die.
2. Start with QC fw (6 slw + 4 sle types, -133 to -453 ps), st_b, and KV pv (11 types; pv_v1n is 824 k cells).
3. Each family gets the kv3_hgi form: station the bus at 380 um steps in the plan, or site the existing register
   at the equal-hop point. The S4r-style nested delta is the vehicle on QC, kvgeom7 on KV.
4. A type worse than -150 ps after CTS does not need its route to be judged; the lane starts the fix at CTS.
   The route may finish for DRC data.
5. kv3_pv_v1n at 824 k cells: split it (the approved over-400 k rule) in the same delta.

### Lever 4. Generation on the adopted plans

Evidence (MEASURED, `kit_wave_stages.tsv` 05:07):
- QC: 0 rows on event S4K; the newest rows are S4C. 36 types fail at `kit_rtl` between 01:14 and 04:43 with
  "bind of record names HDL sources that are gone" (`die-qc-103/treeA/...`). 28 of the 127 types end there now.
- KV: 13 types fail at `gen` between 04:25 and 05:06 with `module 'gen_phys' has no attribute 'tap_offset_table'`:
  kv3_hgi, hgi_v1, v4, v7, v8, hroot, io_cor_v1, pc x4, pv_v3n, pv_v5. REPORTED (KV-102 04:01): `check.py` in the
  same tree calls `port_pg_free`, which the installed `schema.py` lacks.
- QC also: sle_hc2 has 345,951 cells on 0.44 mm2 (0.79 cells/um2 against 0.42); the wave asks for x1.87 area or a split.

Root cause: the KV tree has a `gen_phys.py` / `schema.py` older than its callers after the 03:43 copy install
(INFERENCE; the QC die STA failed on the same function from an old tree). The QC bind of record lost its sources.

Fix: GENBUG-IMPL + KIT-OPS-6 put main's `tap_offset_table` and `port_pg_free` into the KV tree and test one gen and
one G0. KIT-OPS-5 points QC `kit_rtl` at the S4KR bind and confirms the first S4K row. DIE-QC-103 puts the sle_hc2
split into S4p/q/r.

### Lever 5. S81 leaf kits

Evidence (REPORTED, S81-LEAF-PLAN 05:12, epyc7 `s81-leaf-plan/cp27`): all six leaf kits fail before placement on
B6gsh and on LT2 alike. (1) t14, t54: `sdc_lint`, the core-tap latency has early = late (-96.8 ps) where the plan
window is -355.8 early. (2) t17, t72: the sidecar's reset collectors differ from the bound RTL. (3) t62: a lane
macro R180 -> MX cannot sit on the tracks. B6gsl (LT2) is in gates.
MEASURED (epyc2 process list): S81 col_h9_r0_p1 x2, col_h9_r0_p2, col_h10_r1 and leaf t11 have been in `5_1_grt`
for 6-15 h at one core each. Their logs were not read.

Root cause: base-plan and generator defects, not the throat delta. (1) is the plan W window missing from the SDC
writer; it would under-constrain every core-tap type, not only these.

Fix: GENBUG-IMPL fixes (1) in the SDC writer (write early and late from the plan window) and checks how many
released S81 types carry the equal pair. S81-LEAF-PLAN regenerates the sidecar from the B6gsh bind for (2) and
runs `orient_realize.py` for (3), then the place + global-route proof. DIE-S81-92 reads one of the 15-h `5_1_grt`
logs before the 350 types are released into the same step.

### Lever 6. KV hg / hgi

Evidence (REPORTED, FABLE-KVOVF 05:14, v_hgi2 at CTS): TNS -4.47k (merged -558k), 30 endpoints left, WNS -414 ps.
kp bus 0 (was 430), core reset pins 0, chain 0. Left: 7 reset-relay D pins (-227 ps), 12 start / reset broadcast
flops from `u_cland_rst_ft0_i` (-252 to -414), 6 `u_bin_i_ectl` (-80), 2 others. kvgeom7 a/b/c are in gates;
their G0 fails on the tool error of lever 4.

Fix (KV-102): kvgeom7b plus a two-level reset relay tree and one relay stage on the start / reset broadcast, on
all 19 hg / hgi types. The kp +2 cycles and reset +1 cycle need the RTL owner's functional check. Then the same
family listing on kv3_hg (lever 3 method), whose WNS stays near -600 without bus stations.

### Lever 7. HEAD NF

Evidence (REPORTED): NC gates pass on the old-form sidecar (bind, cohort 26/26, LATCHECK 329/329). lep0N spread
246 -> 63 ps. Start reset regenerated: 1,368 reset ports, settle 88. Open (HEAD-99 04:50): the both-edge re-bind
does not prepare, because relay pin lists differ between copies of hd_spn (sp0/3/4 against sp1/2) and
hd_spn_wshim_rx. K per copy is a strap and is not the cause. The route gate (lever 2) must use the adopted kit.

Fix (HEAD-99): use the partition-origin form with 0 relays, as section 17 of FABLE-TRIAGE-HEADKV set, through the
approved `landing_remap` branch. If two copies still need different relay stage counts, give all copies the larger
count (one type, +1 cycle on the short copies) and do not split the type. sp5 seam trim of 20 ps goes with it.

### Lever 8. QC cb family

Evidence (REPORTED): S4k adopted (bind 0, LATCHECK 1,921/1,921). S4p/q/r binds launched; no result posted. The die
STA chain on S4k runs from a main-based tree. Hops after S4k on nb_i12 are 411-418 um (accepted).
DIE-QC-103's question on a plan site for `u_st` has no answer; CLAND-BIN has posted nothing since the G2 result.

Fix: CLAND-BIN builds the equal-hop form (FABLE-PD-QC-0300 section 3) and the cbf_q01 place-only proof. Adopt the
largest of S4p/q/r that passes. The first QC die STA result then ranks the tile-boundary pairs.

## 2. Answers to the three questions

(a) QC and KV sign slowly for two reasons. The types that run are not failing early: they carry -130 to -1,550 ps of
setup into a multi-hour route (9 of 13 read). The types that do not run are stopped at generation (QC 36 on
missing bind sources and no S4K row; KV 13 on `tap_offset_table`). Congestion and DRC are not classes on either die.
(b) Not today. The split is right and form (b) matches form (a), but a unit of 141 nets holds about 2,800
violations that iterations do not remove. One marker dump decides the fix. After it, HEAD needs about 12-14 h for
11 passes. KV has no unit run that I found, and DIE-KV-ROUTE-1 has no post since 03:2x.
(c) No owner or no progress: the `u_st` / equal-hop site form (CLAND-BIN silent); KV start tree and unit route on
kvgeom6 (DIE-KV-ROUTE-1 silent); the 45 S81 lanes over 405 um after LT2 (set aside, no owner); the read of leaf
t54's route box; the HEAD relay pin-list rule (HEAD-99 asked for an owner).

## 3. Stop list

1. No unit-route volume and no KV unit run before one unit reaches 0.
2. No more iterations on a unit whose count is flat; 60 iterations will not clear fixed shapes.
3. No full-die single-process detailed route (95 min in iteration 0 without a line), and no form (a) for volume.
4. No release of the 350 S81 types before the compose passes and the added flops are priced per type.
5. No hop-limited start form on S81 (66 fail), and no rise-only start edges.
6. No relaunch of a QC or KV type that entered route under -150 ps of setup without a design change.
7. No type split of hd_spn for a relay count difference.
8. No counting of v_hgi2 or any kit-RTL edit form.
9. Still in force from 03:2x and FABLE-PD-QC-0300: no cycles on a subset of the four cb columns, no G2 beside the
   ring as default, no legacy half-period S81 clock numbers, no size-7 cut-out runs.
