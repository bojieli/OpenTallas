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

# FABLE-CLOSURE-STRATEGY 2026-11-15 07:3x PST: cross-die levers, S81 delta order, stop list

Read-mostly review, technical physical design only, HBM parked. Nothing launched, stopped or changed.
New since 05:1x: FABLE-PD-S81-0335 D-H, PD-S81T-0710, PD-S81C-0730, PD-QC-0700, PD-QCC-0740, PD-PHY-0710, KVOVF 14-16,
the queue to 07:20, `failure_breakdown.py` 07:11. No FABLE-PD-HEAD-0700 file exists.
MEASURED = read by me today from a plan, log or report. REPORTED = from a lane or review post. INFERENCE is marked.
My scripts (read-only plan scans): epyc7 / epyc9 / epyc2 `/tmp/fcs_scan.py`, `fcs_det.py`, `fcs_l2.py`, `fcs_drc.py`.
Plans scanned: S81 `B6gslcf.json` (epyc7 s81-b3-clk/ev), QC `zz_s29_qc103_s4q2.json` (epyc9 die-qc-103/treeA), KV kvgeom6
`plan_c.json` (epyc7 kw45/src_kv_kvgeom6_pgL), HEAD `gate/plan_nc/prep/source_plan.json` (epyc2 die-head-route-1; NC, not NF4).

`failure_breakdown.py` 07:11, technical classes: none new. S81 134 held + 68 running, QC 64 running + 36 held + 5 waiting on
the sta_region cores, KV 42 running + 6 placed, HEAD 6 held. Every open technical item is behind a plan event or a die gate.

## 0. Five things the per-die reviews did not see

1. The HEAD route-unit residue is named. It is die clock cells under partition abstracts, not pins and not PG (lever 1).
   This is the same for all four dies.
2. B6gslcf did not pass at 07:06 (it is not "in bind"). Two causes, both small and both in the compose (lever 2).
3. Every one of the 216 S81 col types has two tap rows per element half with two different insertions, and neither is the
   signed reference (lever 3).
4. Station registers with plan sites inside hard cores: S81 36 types (not 5), QC 7 types. They sit in the G0 baseline (lever 4).
5. Two items PD-S81T lists as missing from the CA plan are in it: the col tap window (165 ps on 216 of 216 col types, in the
   die table `clock.tap_window.per_type_ps`) and `reset_replicate` on col_h10_r1 (12 of 12). Only the type-level key is absent.

## 1. Levers, ranked

| # | dies | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | HEAD now; KV, S81, QC next | Die clock cells under partition abstracts: cut the abstract, reserve the sites | the DRC gate of every die | DIE-HEAD-ROUTE-1 (proof), KIT-OPS-6 (abstract + site map) |
| 2 | S81 | CA delta: 7 lanes at -1 and one wrong source clock port; take `--strap-window` in the same bind | 335 landed types | DIE-S81-92, KIT-OPS-6 |
| 3 | S81, QC, KV | Core tap rows: one row per core, at the signed reference | S81 216 col types + bk_sel__t2 + eng__t1; QC 18 cb types and KV hub_C to check | DIE-S81-92; DIE-QC-103, KV-102 |
| 4 | S81, QC | Station sites inside cores and strips over their track count: one geometry delta | S81 about 60 leaf types; QC 7 su types | S81-LEAF-PLAN + S81-LEAF-STRIP (one row owner per type), DIE-QC-103 |
| 5 | QC, KV | Stations on one leg of a latency-matched join; frozen pad tables | QC S4v2 / S4fw adoption (about 45 types), KV 7j/7k (19 hg / hgi) | DIE-QC-103, KV-102, KIT-OPS-6 |
| 6 | all | Hold ECO: non-port scope, 5 ps target, setup guard | t47, gunit, 6 sta_region masters, the S81 routed-not-signed rows | FLOW-LATEECO, KIT-OPS-5 |
| 7 | QC | Skew depth of the sta_region masters as straps | 4 parents now, 3 re-hardenings per later station event | DIE-QC-103, CORE-ROWS-1115 |
| 8 | S81 | col and phy clock: build, do not plan further | 12 col_h10_r1 (then the col family), phy__t1 | DIE-S81-92 |

### Lever 1. Die route: clock cells under the partition abstracts (cross-die)

Evidence (MEASURED, epyc2 `die-head-route-1/head/p20nc_gate/unitruns/probe_u201_b/drc_TT.rpt`, written 06:03, not yet
posted by the lane; unit u201, 141 clock nets, crop form, 3 steps: 3,276 -> 2,786 -> 2,800):
- 2,800 markers. 1,904 are an own clock net against a partition instance (`tW1b8` 1,894, `tW1b9` 10):
  Short M1 400, M2 252, M3 252, M4 252, M5 252, M6 252, M7 244.
- The M2-M6 markers are the same 252 points on every layer (184 distinct 1-um points over x 1654-2415, y 10869-11878),
  so each is one via stack from M8 down to M1. At the first point the net `ck_rn1089_1` also touches the die clock
  cell `ck_r1089_2` on M1. The stacks end on die clock cells that sit inside the partition.
- The partition abstract (`kit/abstracts/ot_s81hd_lep0N.lef`, source "plan abstract") has OBS on M1, M2, M3 over the
  full outline and block rectangles from M4 up.
- Rest: M1 clock net against VDD 178 and net against net 97 (at the cells); M7 against PG 77; M8 against abstract
  obstruction 120 short / 177 spacing, M8 against PG 67 + 7, M8 min step 83.
- The other five running units are flat as well (u201_b at 2,611 in iteration 9).
- Kit: 10,660 repeaters and 13,093 leaves in the HEAD tree. S81 has 91,460 die clock cells and 2,430 start stages
  (REPORTED, 0335 H), and its types carry no reserved sites (MEASURED: no `reserved_sites_um` key on any of 395 types;
  none on QC 130, KV 56 or HEAD 26 either).

Root cause: `die_trial.SiteMap` puts die clock cells on any site inside a partition and outside hard cores. The
abstract of that partition blocks every layer there, and the type under it never reserved the site. This corrects my
05:1x inference (stacks to lower pin shapes of the abstract): there is no lower pin shape; the target is a die cell.
No iteration count removes it. For a signed type the conflict is real metal, not only an abstract shape.

Fix:
1. Proof, 30-40 minutes (DIE-HEAD-ROUTE-1): cut the lep0N abstract OBS on M1-M7 over the 252 cell positions of u201
   (cell box plus one via column), rerun the same 3 steps. Expected: the 1,904 instance markers go to 0. The M8 part
   (about 400) stays and is then the only thing left to name.
2. Site map from the layout, not from the outline (KIT-OPS-6): for a type with a closed view, a site is legal only
   where the view has free rows and a free M1-M7 column; for a type without one, the plan reserves a small set of
   rectangles (`clock.reserved_sites_um`, kind die_clock_tree) on the tree pitch (HEAD kit: repeaters 150 um, leaves
   200 um) and the tree snaps to them. The abstract generator cuts OBS over the cells actually placed.
3. Count before choosing per type: sites used by the die tree against free sites in each signed view. A signed type
   keeps its record when every cell fits in free area; only the others re-key.
4. Same change for the start-stage flops (S81 2,430 x 4.32 um, already an open note in 0335 H).
5. M8: after step 1, split the M8 markers into pin landing against abstract obstruction (cut a window around each
   M8 pin) and against the region PG (the `clock_entry_pg_cut` form). DIE-KV-ROUTE-1's M8 / M9 pin-against-PG scan
   answers the PG half for KV.
Unblocks: HEAD die DRC today's blocker; the same defect waits on KV (127 units listed, none run), S81 and QC.
Owner: DIE-HEAD-ROUTE-1; KIT-OPS-6 for the generator and SiteMap; each die owner for the reserved rows.

### Lever 2. S81 CA delta: why B6gslcf failed, and the form to rebind

Evidence (MEASURED, epyc7 `s81-b3-clk/run/b/B6gslcf`, `g0/g0_report.json`, `bind.log`; compose rc 0):
- G0: 7 errors, all schema: `latency.lanes.<lane>.clock_landing: -1 < 0` on attn / attnh / hbm between svc_5 -> svc_4,
  svc_11 -> svc_10, svc_13 -> svc_12. This is the check 0335 section B asked for at 03:35 (2 crossings at -1 then).
- Bind: 80 errors in the summary; the log shows 1 EMIT and 29 LF_CS_DEPTH. EMIT: `bk_sel__t2: fclk_out_tl_o0 contract
  source_clock_port clk_t2 is not an input port of the type`. bk_sel__t2 has 7 core taps and no grid tap in the plan.
  The 29 LF_CS_DEPTH lines (24 leaf, 5 kv_leaf) say "no bound module file": INFERENCE, they follow from the failed emit.
- B6gshcf fails the same way.

Root cause: the compose writes a negative landing when K lands before the lane's own stations, and it names a grid tap
as the write-clock source on a type that has only core taps.
Fix (DIE-S81-92, KIT-OPS-6 for the compose):
1. The 7 lanes: +1 station cycle on the three svc pairs (cycles are pre-approved) and re-plan K for those ports; do
   not relax the schema.
2. Source clock port: take it from the ports the type has (`clk` for a type without grid taps).
3. Rebind on the uncapped F table with `--strap-window` (REPORTED DIE-S81-92 06:38: 977 / 16, strap bind rc 0,
   0 violations, lo 105.5 / hi 112.4, 144 of 160 depth-8 crossings back to depth 4, 243 k fewer flops). Depth is type
   content; taking it now means the 335 types are built once. Guard 417 gives the same types 160 depth-8 buses that the
   next delta would shrink again.
4. Compose variant C as ruled. Its 17 -> 1 result was measured on the guard-417 table; read the band report again on
   the strap-window table before the bind.
Unblocks: 335 landed types. The 52 types of `types_depth_open.json` stay at risk of one depth change until the 48 long
start hops are measured (0335 G), as already ruled.

### Lever 3. Core tap rows (cross-die)

Evidence (MEASURED, plan scans):
- S81 B6gslcf, all 216 col types: each element half has two tap rows. `u_w.ck` 437.413 / 348.735 and `u_w.clk`
  532.993 / no FF value; `u_e.ck` 476.052 / 382.22 and `u_e.clk` 553.179 / no FF value. 3,456 rows. The signed
  reference is 465.39 / 361.26 (PD-S81C). The `.ck` rows are 28 ps late and 11 ps early of it, the `.clk` rows 67.6 and
  87.8 ps early. The kit wrote the `.clk` value against a 250 cap (PD-S81T section 5).
- S81 rows whose owner text is the liberty maximum: bk_sel__t2 `u_tx.ck` 829.1 (early 579.1) and eng__t1 `u_e.ck`
  848.98 (early 599.0; "no measured mean in the view"), both over T/2 = 416.5; `eng_rr_h0` 270.23. eng__t1 is new.
- QC S4q2: 72 core taps on 18 cb types are over T/2 early: tiles `u_tNN.ck` 733.25 and 774.38 against budget 250
  (early 483 and 524). KV kvgeom6: kv3_hub_C `ahub.ck[0..2]` 1,003.4 (early 753). HEAD NC: none.

Root cause: tap rows are written by several events from different sources (liberty maximum, placed view, routed view)
and nothing compares a row with the frame the core was signed in. A stale pin name leaves a second row behind.
Fix:
1. DIE-S81-92, rows only, in the CA rebind: one row per half, 465.39 / 361.26, on the pin name of the signed LEF;
   delete the twin. bk_sel__t2 at 450 with the idx row 722.7 / 592.8 (PD-S81C 2.3). eng__t1 `u_e`: read the signed
   record's `io_reference_ps`; if the core has none, measure the pin-register mean on its routed view first.
2. PLAN-READERS-1: the audit fails a core tap whose value differs from the signed `io_reference_ps`, fails two rows
   on one core clock, and fails a row without an FF value.
3. DIE-QC-103 and KV-102: state how the kit times a core tap more than T/2 early (cb tiles, ahub). If it is clamped,
   as on S81 col, part of the -861 ps on cbn_q11 is this and not a data path. Not checked by me.
Unblocks: timing truth on 216 col types before they are rebuilt on the CA plan; bk_sel__t2; eng__t1.

### Lever 4. Station sites inside cores, strips over their track count

Evidence (MEASURED, plan scans; my count for t14 by feed-through bit sites is 1,483, equal to PD-S81T):
- S81 B6gslcf, `internal_stations` register sites inside a hard-core box: 36 types, 1,306 sites, 75,617 bits; only
  71 sites are within 2.2 um of a core edge. Largest: leaf t22 29,674 bits (the vn -> lane bundle entry sits inside
  5 lane cores), t41 23,623, t8 4,415, t37 2,354, t56 1,574, t65 1,574, t28 1,569, t72 1,558, t75 1,308, t61 1,291.
  Also 6 col_h10_r0_p1 types with 1 site each.
- S81 feed-through bit sites inside cores: t65 3,140, t32 1,584, t14 1,483, t38 1,016, t16 21, and
  slice_station__t51 13,574 inside its two native children (plus 73 grid taps). t51 may be by design (child-side
  form); it is also the last CA band failure.
- QC S4q2: 7 su types, 208 sites, 19,918 bits (sle_su_l1 x2 3,713 each, sle_su_l0 x2 2,652, slw_su_l0 x3 2,396): the
  `flt_su_c_i` pin chain passes through lanes 5 and 6. KV: kv3_pv_v5 / v5n, 6 sites each. HEAD: 0.
- PD-S81T: 13 leaf types with a strip over 1.0 x its tracks, 5 with a slot under 20 um holding over 200 sites. G0
  reports the in-core sites only when new; the old ones are in the accepted baseline.
- Limit: I did not open a placed database. The legaliser displacement (126 um on t14) is the check for each type.

Root cause: cores were moved by several events (LT2, quad staging, orient) and station sites were not re-derived.
Fix: one leaf geometry delta (section 2), with the station re-site as a generated step after every core move; G0
"station site inside a core" is never baselined (GENBUG-IMPL). QC: DIE-QC-103 re-sites the su pin chain in the S4fw
event. A type on this list is not released before its row is re-sited.

### Lever 5. Stations on one leg of a matched join (QC and KV, same class)

Evidence (REPORTED): QC S4x does not bind because +2 on st_b moves regions 4-7 past region 0 (PD-QC-0700 2.1); the
cb16 pad table was keyed to the old bound depth, three rounds lost (1.3). KV 7a-7f at 07:09: PARAM_REGEN "ECTL: K
round trips differ per frame [18, 24]", because the hg stations sit on the request / response buses of one frame
only; KV also had to pin 91 pad members. QC-FWST has S4fw on S4q2 with levers 3-6 in gates.
Root cause: a station event changes one leg of a latency-matched pair; tables derived once are not re-derived.
Fix:
1. KV-102: the equal-depth form (the same +N on krq / krs of every frame) is the structural one. 7j / 7k drop the
   stations and leave the hg krsp hop at -568 ps; adopt one of them only as a step.
2. KIT-OPS-6: the derive replay as a pre-bind step on both dies (the QC replay predicted 24,672 stale bits exactly,
   in minutes), and every pad table regenerated in the bind chain.
3. Stations enter a plan per matched group, not per bus.

### Lever 6. Hold ECO scope

Evidence (REPORTED): kv3_phy_v1 late ECO TT -34 -> -248 while fixing port hold; t47 -0.54 ps on one output port,
alternating between two bits at target 0; gunit_l1f_bf 15 reg-to-reg at -4.82; sta_region masters -3 to -7 on at most
19 endpoints, sibling closed in one pass. FLOW-LATEECO READY @d63e3dc5a1d (core-only default), no real-kit run yet.
Fix: merge it; add a 5 ps target and a stop when TT setup falls under -42; first real run = t47 from its i2 database
(3 h). Then the S81 routed-not-signed rows (25 since 11-06, 19 slice_station, not opened by anyone) in one batch.

### Lever 7. QC sta_region skew depth as straps

Evidence (REPORTED, PD-QCC-0740; GENBUG-IMPL 07:11): 4 types, 32 parameters differ between plan and bound RTL on S4p
and again on S4q2; KV, S81 and HEAD have 0 `param_wrap` rows (QC S4q2 has 188). 12 kits for both parameter sets run.
Fix: as PD-QCC R1: SKEW_N / SKEW_S as strap inputs of one master in the next QC event; the bind check merges now.
S4v2 and S4fw move the cb column again, so without straps the masters are rebuilt a third time.

### Lever 8. S81 col and phy clock

Evidence (MEASURED on B6gslcf): col types have `tap_max_sinks` 1500, budget 450, per-type window 165 on 216 of 216,
`reset_replicate` on 144 of 216 including all 12 col_h10_r1. phy__t1 has 0 taps and no `tap_max_sinks`.
Fix: no more col plan work before one col_h10_r1 build to CTS on the CA plan with the lever-3 rows (pass: PD-S81-2250
gate). phy__t1: grid taps along the strip in the same rows-only change (PD-S81T section 6).

## 2. S81 queued row deltas on B6gslcf: conflicts and order

Type overlap of the queued sets (MEASURED from the lists in 0335 D, PD-S81T, the 07:10 posts and my scan):

| type | collector (D2) | orient (D3) | strip | slot / in-core ft | in-core istation | CA band failure |
|---|---|---|---|---|---|---|
| leaf t8 | x | | x | | 4,415 | 2 |
| leaf t72 | x | | x | | 1,558 | 2 |
| leaf t33 | x | x | x | | | |
| leaf t52 | x | | x | | 273 | |
| leaf t58 | | x | | slot 1,342 sites | | |
| leaf t68 | x | | | slot 403 sites | | |
| leaf t65 | | | | slot 263 sites, in-core 3,140 | 1,574 | |
| leaf t28, t75, t13, t43, t10, t71, t74 | | | x | | 262-1,569 | |
| leaf t37 | | x | | | 2,354 | |
| kv_leaf t3 | x | x | | | | |

Conflicts:
1. Two lanes own rows of the same type: S81-LEAF-STRIP (13 strip types) and S81-LEAF-PLAN (orient 13, t14, slots).
   t33 is in both. One owner per type row; S81-LEAF-STRIP takes every type in the table above.
2. Order inside a type matters: a core move changes station sites, collector taps and landing bands. A collector
   reattach or a band placed before the move is wrong after it.
3. The CA compose rebases 21,010 pins and places bands against the cores. Any leaf row change after it invalidates
   the bands of that type. The compose must be the last step of every S81 event from now on.
4. `--strap-window` and the capped start tree change depth (160 -> 16 depth-8, or 205 + 13 depth-16 with the 48 long
   hops open). Variant C was proven on the guard-417 table only.
5. FABLE-S81-TYPEMERGE R2 (strap width = group maximum) edits what the compose writes; as a row patch it is
   overwritten by the next compose. R3a (monitor entry union) moves col landing pins and must come before a compose.
6. The clock rows (lever 3, col reset copies, phy__t1 taps) touch col, bk_sel, eng and phy only: no overlap with the
   leaf sets.

Merge order:
- E1, now: B6gsl + rows-only clock changes (lever 3 S81 rows, phy__t1 taps) + compose (F table, `--strap-window`,
  variant C, the two compose fixes) -> bind + LATCHECK. Release: col, slice, svc, serdes and the leaf types not in E2.
- E2, leaf geometry, one delta: orient -> core moves (strip re-path, slot, t14) -> station re-site (ft and
  internal) -> collector reattach -> compose again. About 60 leaf types; proof = place + GRT 0 overflow on t75, t14,
  t22 and t8 before the bind. These types are held out of E1's release.
- E3, die level: capped start tree with the measured long hops, TYPEMERGE R2 inside the compose and R3a before it.
  Re-keys only the types whose depth or strap width changes.
- R1 of TYPEMERGE (sign-off key = layout hash) is no plan change and can apply at E1's release: it cuts the col
  builds from 216 to about 14-20 and is the largest single saving on S81.

## 3. Stop list (technical dead ends)

1. No more iterations, unit volume or KV unit runs on the current abstracts: 1,904 of 2,800 markers are fixed
   geometry. No full-die run either.
2. No reading of the unit residue as pin-against-PG until the abstract cut is proven; the PG part is under 330.
3. No rebind of the CA delta with the schema relaxed for negative landings.
4. No guard-417 CA release if the strap-window table binds: it builds 144 depth-8 buses that the next delta removes.
5. No further shallow-tree forms of gb_he / gb_hw, no idxD, no kit vclk below the typed reference (PD-S81C).
6. No col_h10_r1 form on the B3t block and no new col plan fields before one CTS build on the CA plan.
7. No leaf row change after a compose without a compose rerun; no second owner on a leaf type row.
8. No release of a type whose station sites lie inside a core, and no baseline for that G0 class.
9. No KV or QC station event on one leg of a matched join; no S4r4 / S4r5 sign tests; no S4x as built.
10. No n6_s7 / n6_s8 sta_region views registered as S4p or S4q2 children.
11. No port-scope hold ECO on a type; no zero-target ECO pass.
12. No wave attempts on the three QC PHY types; no plan-window move to the PHY macro pins.
13. No phy__t1 split and no relaunch before it has taps; no t75 retry as INFRA; no t14 launch on its current row.
14. Still in force: the 05:1x list items 5-9.

## 4. Not verified

- Lever 1: no rerun with a cut abstract; the M1-M7 claim rests on the marker geometry and the lep0N LEF. I did not
  confirm the master of `tW1b8`; the marker field (760 x 1,010 um) fits inside lep0N (1,892 x 1,227).
- Lever 2: the 29 LF_CS_DEPTH lines as a follow-on of the emit error; the band fit on the strap-window table.
- Lever 3: which of `.ck` / `.clk` is the pin of the signed LEF; how QC and KV kits handle a tap over T/2 early.
- Lever 4: plan reads only, boxes as origin + outline; no placed database opened; whether t51 and the QC su lanes are
  true hard cores for placement (they are `hard_cores` rows in the plan).
- HEAD was scanned on the NC source plan, not NF4 / NF5. The route gate must be rerun on the adopted kit.
- No what-if was run in this review.
