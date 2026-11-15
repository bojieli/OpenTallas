# FABLE-CLOSURE-STRATEGY 2026-11-15 03:2x PST: technical closure levers for S81, HEAD, QC, KV

Read-only review. Technical physical design only. HBM is parked and not covered. No job, plan or kit was touched.
This section replaces the 01:3x review, which is kept unchanged below (section A.5 gives the state of its levers).

Sources: FABLE-TRIAGE-HEADKV sections 15-18, FABLE-TRIAGE-QC (with the CLAND-BIN post), FABLE-KVOVF sections 8-10,
the queue from 01:15 to 03:15 hub time, `failure_breakdown.py` (03:10), lane handoffs, and my own reads of the run
directories named below. FABLE-TRIAGE-S81 has no entry after 01:14. FABLE-PD-QC-0300.md does not exist.

MEASURED = read by me tonight from a log, plan or process table. REPORTED = taken from another report, not
re-measured. INFERENCE is marked. Host file times on epyc7 / epyc8 / epyc9 are UTC (PST + 8 h).

`failure_breakdown.py` technical classes at 03:10: timing after route 3 (S81 slice_station__t47; KV kv3_phy_v1 +1).
No congestion row is left in the table. All else is "running", "held" or a flow class, so the levers come from the
run directories.

## 0. Five things the lanes have not seen

1. The die detailed route is fixed for memory, not for time. The HEAD cut-out check has 26 nets and the full die
   area. Its iteration 0 has used 12.1 CPU-hours without the first 10 % line (lever 2).
2. S81 has no count-aligned die clock result. The chain ended within 2 seconds on a missing module (lever 1).
3. The QC die run finished: global route 0 overflow, count-aligned plan and bind pass. Its die STA did not run. It
   stops on 52 tap-offset rows over half a period, all on the 17 cb types, in S3R, S4c and S4k (lever 3).
4. The KV kit on the plan of record (p6, kvgeom6) is not running. It failed in 0.5 s on a missing module (lever 6).
5. The G1 proof is still in global placement (epyc10, 54 min in `3_3_place_gp` at 03:13). No hop census exists yet.

## 1. Levers, ranked by types or dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | One adoption: B6gsh + leaf throat delta + count-aligned bind, before the 350 types regenerate | 350 types, of which 79 leaf, 11 serdes | DIE-S81-92, S81-LEAF-PLAN |
| 2 | HEAD, KV (then S81, QC) | Die detailed route: time per route box, not per net | the DRC gate of every die | DIE-HEAD-ROUTE-1, DIE-KV-ROUTE-1 |
| 3 | QC | cb family: tap offsets over half a period block the die STA; ring-to-fabric span needs a planned site | 17 cb types, QC die STA | DIE-QC-103, DIE-QC-GRT0-2, CLAND-BIN |
| 4 | HEAD | rp21z20NF (hk6) with the lep0N local tree rebuilt and all 26 wrappers republished | 26 types | HEAD-99, HEAD-CLKFEED-1 |
| 5 | S81 | Leaf throat delta LT2 proved by place + global route on the worst types | 53 leaf types | S81-LEAF-PLAN |
| 6 | KV | Clock-form start tree on kvgeom6, taps for the 320 pc / phy crossings | KV lane-latency gate, KV die STA | DIE-KV-ROUTE-1, KV-102 |
| 7 | KV | hg / hgi: chain depth set by span (hops of 520 um are over reach); read the kv3_hg paths | 12 hg / hgi kits | FABLE-KVOVF, TYPE-KVHGI2 |
| 8 | QC | cb net-zero stations for the bco hop; `r_dly_spread` on the cbf_q01 pair only | cbn_q01 x3, 48 lanes | DIE-QC-103, TYPE-QCCB-GEN |

### Lever 1. S81: one adoption, and the die clock check it lacks

Evidence:
- MEASURED (epyc7 `/srv/opentallas-scratch2/claude/s81-b3-clk/log`): `B6gb.log`, `B6gp.log`, `B6fb.log` end
  `BIND_RC=2`. REPORTED (DIE-S81-92, 03:1x): the cause is a missing input file (dead-input re-proof not in the
  overlay), not a design result. The re-binds `B6gb_rebind2.log` and `B6gp_rebind2.log` were at their first line
  at 03:08. `B6gsh.log` (B6gs + `phy_pg_macros`) was at `SVCMEM_TIES`.
- REPORTED: G0 of B6gb, B6gp and B6h is 252 errors, 5 new against the control: seam hops of 454 / 494 / 540 /
  532 um and the cut `s_6S_L0` at 0.63 against 0.6. B6h has 0 PG-domain errors on the 11 serdes types.
- MEASURED (epyc8 `/srv/opentallas-scratch2/claude/die-grt0-s81/s81/b3x2d_ca/CHAIN.log`): `CA_OCV 1`,
  `CA_PLAN 1`, `CA_BIND 1`, `STA_CA SKIPPED`. `ca_ocv.log`: `ModuleNotFoundError: No module named 'clk_aocv'`.
  The plan and bind steps then failed on the missing output of the step before. Nothing has run since.
- The only S81 die clock numbers are the legacy half-period form on B3x2d (REPORTED): landed setup -3,126.8 ps,
  hold unmeasured. That form is on the stop list.
- HEAD precedent (REPORTED, HEAD-99 delta list): the count-aligned re-bind changed the kit inputs of all 26 HEAD
  types through K, depth and latency.

Root cause: S81 is adopting a plan for 350 types without the bind that sets K and depth per port on the B6 tap set.
INFERENCE: if that bind changes K on S81 as it did on HEAD, the 350 types regenerate a second time.

Fix:
1. DIE-S81-92: add `clk_aocv` to `die-grt0-s81/ca_tools` and rerun `die_chain_ca.sh` now, on B3x2d first (the
   clock kit exists), to get the first S81 count-aligned numbers: crossings, depth histogram, worst lo / hi,
   start-skew, no-tap count.
2. Compare its K and depth per port with the table B6gb binds. Equal: release as planned. Different: put the
   count-aligned table into the adoption, as HEAD did, before KIT-OPS-5 releases the held rows.
3. Adopt the highest superset that passes (B6gsh), then LT2 as a leaf-only delta (lever 5). Do not adopt B6gb and
   B6gsh as two full events.
4. G1 goes in when its census exists. Rule for the proof: hops over 405 um on the lane-pad last stations fall
   from the kit's count to 0, and the total over-reach count does not rise (the G2 result on QC shows why the
   second number matters).

### Lever 2. Die detailed route: the cost is per route box

Evidence (MEASURED):
- Memory is solved. HEAD full die, small worker (epyc9 `die-head-route-1/head/p16g/drt7_small_full_TT/drt_TT.log`):
  52,489 nets, 164,794 guides, V8 shapes 37,237,920 (capped), 10.2 GB after track assignment, 29.7 GB in iteration
  0 at 24 threads. The stock worker held 144 GB on the same database. KV stock-worker baseline (epyc7): 183 GB.
- Time is not solved. Cut-out check (epyc2 `.../drt7_cut_small_TT/drt_TT.log`): `OT_NETS total=26`, but
  `Die area: (0 0) (17712000 17556480)` and the same 37,237,920 V8 shapes: the window removed nets, not area.
  Iteration 0 started 02:20. At 03:16 it had used 12.1 CPU-hours and had not printed "Completing 10 %".
- The full run printed nothing in its first 12 minutes of iteration 0 (3.7 CPU-hours in all).
- The two size-7 cut-out runs (stock call and single-step) at 4 threads hold 40-45 GB and have no iteration line after 50 minutes.
- No run has given a violation count, so the stock-against-size-2 comparison does not exist.

Root cause (INFERENCE from the 26-net run): the router builds and initialises a routing grid for every box on the
die in iteration 0, whether or not a guide crosses it. At size 2 that is about 666,000 boxes. More than 12.1
CPU-hours for under 10 % means over 120 CPU-hours for iteration 0, with 26 nets or with 52,489.

Fix:
1. Now: raise the thread count of the full runs. Memory per thread is small (29.7 GB at 24 threads). epyc9 has 96
   cores; 96 threads need about 90 GB (INFERENCE from 0.8 GB per thread). This divides the wall time by up to 4.
2. Read the time of the first 10 % line on the HEAD full run and post the projected iteration 0. Under 4 h: this
   form is the die gate. Over that: use form 3.
3. Region databases with the die area cropped. Time follows area only if the database is small; a net filter on
   the full die changes nothing (the cut-out shows it). One database per clock-region group, fixed shapes of the
   neighbours kept, one region of overlap, run on all hosts in parallel. I withdrew windows at 02:0x for memory;
   that still holds. For time they are the only form that scales with hosts. Not built, not measured.
4. Stop the two 4-thread size-7 cut-out runs and the KV 183 GB baseline when a size-2 run prints its first count.
   They cannot finish first.
5. Route the adopted clock kit. HEAD: the route gate must be rerun on the hk6 kit after lever 4. KV: p1 is
   kvgeom5; the gate needs p6 (lever 6).

### Lever 3. QC cb family: tap offsets over half a period, and the ring-to-fabric span

Evidence:
- MEASURED (epyc9 `/srv/opentallas-scratch2/claude/die-grt0-qc/qc/s3r_b/CHAIN.log`, plan S3R): global route TT
  and FF `EXIT 0`, overflow 0 / 0 / 0, wirelength 649.6 m, 17.3 GB. Taps 42,151 in 313 regions, 0 missing, fall
  rows present. Count-aligned plan: 2,993 crossings, 0 fail, depth 4 on 2,880 and depth 8 on 113, worst lo 104.4
  ps, worst hi 117.0 ps, 770 start edges clean, 0 violations in 300 chips. `BIND_C 0`.
- MEASURED: `REG_STA 1` and `STA_C 1`. `reg/sta.log` ends
  `ValueError: clock.tap_offset.per_port_ps[cbf_q00_s2][clk_c1] {'TT': -459.8, 'FF': -400.8} outside ... |o| <= T/2`.
- MEASURED (my script over the three plans): `per_port_ps` has 15,286 rows on 130 types. 52 rows exceed 416.5 ps
  at TT, on exactly 17 types, all cb (cbf_q00 x3, cbf_q01 x2, cbf_q11, cbn_q00 x2, cbn_q01 x3, cbn_q11 x2,
  cbx_q10 x4). Largest 459.8. The same 52 rows are in S3R, S4c (plan of record) and S4k. No FF value is over.
- REPORTED (CLAND-BIN, cbf_q01, place only): the G2 hook removes the 1,024 ring-to-`u_bin` hops over 405 um and
  creates 1,784 `u_bin`-to-fabric hops over 405 um (maximum 850). Whole type: 3,583 -> 4,246.
- REPORTED: the tile rows have a library clk-to-q of 923 / 938 ps; they pass only with the early-tap credit.

Root cause: the cb types carry a tile whose clock insertion is over 730 ps. Its ports are tapped 420-460 ps early.
That is past the half period the die STA reader accepts, and it puts over 420 ps of unshared clock on every tile
boundary path. Separately, the face ring and the fabric station are 720-850 um apart with one register between.

Fix:
1. DIE-QC-GRT0-2: get the die STA to run. The 52 rows are real plan data, so do not edit them. Read them as a
   declared early core tap (the form S81 uses for its 450 ps budget) and let the pair slack of the tile boundary
   paths be the result. A shape check must not hide the first QC die STA.
2. Report from that STA the cb tile boundary pairs as their own class, with the `port_in` relay seams of the
   01:3x lever 8.
3. DIE-QC-103 + CLAND-BIN: the ring-to-fabric span is a plan item. Give the fabric station `u_st` a plan site at
   most 405 um from its load, then site `u_bin` at the midpoint. No register is added, so no cycle changes.
   INFERENCE: `u_st` can take a plan site; I did not check the generator.
4. Keep G2 opt-in until item 3 exists. Default-on raises the over-reach count by 663 on cbf_q01.

### Lever 4. HEAD: rp21z20NF

Evidence (REPORTED, FABLE-TRIAGE-HEADKV sections 17-18, HEAD-CLKFEED-1 handoff):
- hk6 feed: deepest tap 8,992 -> 7,001 ps TT, feed wire -28 %, 415 of 427 crossings parent-child. Both-edge
  count-aligned STA 427 of 427, FF worst lo 132.3 ps.
- lep0N: FF tap spread 271.6 ps over 195 taps (86.7 ps on rp21z16). The other 357 partitions are unchanged.
  The east half of the region's local tree is 160-272 ps late: the tree was built from the old root.
- Cohort 10 of 26: the 16 failing wrappers are dated 11-11. LATCHECK host_rx is a checker gap (fixed, @c8b5eecd7d).

Fix (HEAD-99, HEAD-CLKFEED-1): rebuild the lep0N local tree on the NC taps; accept at 92 ps or less with the
other 357 unchanged. Republish all 26 types. Delete `start_pins`, keep `root_settle_cycles` 88. Adopt NF, not NC
then NF. Then re-sign hd_mesh_e and hd_ctl_e for the seam hold. No root move; 7.0 ns is the floor of this die.

### Lever 5. S81 leaf throat delta

Evidence (REPORTED, S81-LEAF-PLAN 02:35, epyc7 `s81-leaf-plan/ev/B6gq_lt2.json`): on B6gq 53 leaf types have 182
slots with `u_station` over 1.0. LT2 bands every such station, moves four core groups by 17.8-18.9 um and gives
t14 the 34.56 um move. Lanes over 405 um through the changed types: 50 -> 45. The four seam hops become 382.6-402.8
um. MEASURED: `log/LT2.log` was at `SVCMEM_TIES` (bind) at 03:08. Wave failures since 01:15 in the same family:
leaf t54 `DRT-0255` on a `u_bin_leafdn` net, leaf t65 and slice_station t28 global-route congestion.

Fix:
1. Proof before the family regenerates: place + global route on t14, t62, t72, t17 and t54 from LT2; overflow 0
   within 30 iterations.
2. The 45 lanes still over 405 um need a station each or a re-site in the same delta. List them by type.
3. t54 was under 0.5 in my 01:3x table and still fails detail route, so slot use does not explain it. Read its
   route box (294, 55) um before it is relaunched.

### Lever 6. KV: start tree on the plan of record

Evidence:
- REPORTED (DIE-KV-ROUTE-1, on kvgeom5 p1): clock-form start tree 0 of 3,915 fail, worst lo +109.4 ps, 185 of
  185 edges clean, bind simulation 0 violations (was 32). 320 crossings have no fall-edge arrival: the 64
  pc / phy pairs (`lanes/handoff/KV-NO-TAP-CROSSINGS.tsv`).
- MEASURED (epyc7 `die-kv-route-1/runs6/p6/CHAIN.log`, `kit.log`): `KIT 1`, `FAIL_KIT` at 10:50:12 UTC after
  0.48 s: `ModuleNotFoundError: No module named 'signoff_profile'` from `ot_clk.py` in `src_kv_kvgeom6_pgL`.
  Nothing has run on kvgeom6 since.

Fix: DIE-KV-ROUTE-1 reruns the p6 kit with the module in the tree, then global route, taps and the native
count-aligned chain on kvgeom6. The clock kit must emit taps for the pc and phy partitions. KV-102 posts the
start-form change as the plan event from the p6 numbers. kvgeom6 moved 7 kv3_pc taps from 250 to 312 ps, so
the kvgeom5 margins do not carry over to those ports.

### Lever 7. KV hg / hgi

Evidence (REPORTED, FABLE-KVOVF sections 8-10; MEASURED state on epyc2 `fable-kvovf/forms`):
- Keep only: kv3_hgi_v2 setup -366 ps at CTS, -431 ps after hold repair with 36,635 hold cells.
- kv3_hg: -739 ps with the keep, -753 ps merged. The merge is not its limiter. Its worst paths were not read.
- t_hgi2: 21 of 24 stations placed, longest stage hops 519 and 425 um. MEASURED: t_hgi2 and t_hg were in global
  placement at 03:13; k_hgi2 has been in global route since 00:10.

Root cause: three stages over a span of about 1,000 um give hops over the 405 um reach.

Fix:
1. Set the chain depth from the span: n = ceil(span / 380 um), the same n on every front core of a bank so the
   lane latency stays uniform. Head 3 needs 4 stages. The added cycle is a plan item for KV-102.
2. kv3_hg: read the 10 worst CTS paths before another form is built.
3. kv3_hub_Wo landing bands (REPORTED, CLAND-BIN): the 4.32 um window is occupied by ft2 station cells placed
   first. Reserve the window before stationing; the `OT_LAND_RESERVE` what-if is the test.

### Lever 8. QC cb stations at net zero

Evidence (REPORTED, DIE-QC-103): S4k2 failed the bind with 30 `R8_STALE` + 1 `PARAM_REGEN`, the same signature as
y_o23 +2. S4k is binding. S4n = S4k + `r_dly_spread` on cbf_q01 and cbf_q01_s2 is binding.

Fix: the bco hop (xstn -> `u_bout_bc_o`, 460-970 um) takes the y_o23 form: one station in, one pad stage out on
the same join leg. If that leg has no pad to give, split the xstn tap register in the generator (TYPE-QCCB-GEN).
Adopt S4k alone when it passes.

## 2. Symptoms that came back after a fix (since 01:3x)

| item | what was tried | why it came back | cause to fix |
|---|---|---|---|
| Die DRT memory | stripes, capped vias, small worker | each step exposed the next cost | route boxes over the whole die (lever 2) |
| HEAD cut-out check | 2 x 2 mm net window | the database kept the full die area | crop the area, or drop the check |
| S81 bind gate | B6f, B6g, B6fb, B6gb, B6gp | schema key, then a missing proof file | one tree per gate chain (01:3x lever 1) |
| S81 / KV / QC die chains | relaunch | `clk_aocv`, `signoff_profile`, tap-offset check | die chains run from the bind tree |
| QC cb stations | S4e +2, S4j +1, S4k2 +2 | one collector leg cannot take a net cycle | net-zero form only (lever 8) |
| QC G2 hook | capture register at the ring | the hop moved to `u_bin` -> fabric | planned `u_st` site (lever 3) |
| KV hg chains | r_, c_, s_ forms | stages stay at the ring, or the last hop is long | depth by span (lever 7) |
| HEAD NC | rebind forms | 16 old wrappers; lep0N tree on an old root | republish all; rebuild lep0N (lever 4) |

## 3. Stop list: technical dead ends

New since 01:3x:
- Die detailed route with the stock worker size on a 10.8 um gcell (144-185 GB). The uncapped M8-M9 via arrays.
- A net-window "cut-out" on the full-area database as a speed or equivalence check.
- More threads on a stock-worker run (about 9.6 GB per thread).
- S81 adoption of B6gb and B6gsh as two full events; releasing the 350 types with no count-aligned bind on B6.
- Reading the S81 legacy landed -3,127 ps, or the QC `LPO` line (-6,666 ps), as a die clock result.
- QC: any station that adds a net cycle to one collector leg (S4e, S4j, S4k2 forms). G2 default-on.
- QC: editing the 52 tap-offset rows to get under 416.5 ps.
- KV: r_, c_ and s_ chain forms; three-stage chains on spans over 1,140 um; any hg form before the paths are read.
- KV: die results on kvgeom5 quoted as the gate.
- HEAD: root move for a 6.0 ns target; the 1.15 factor in the gate; NC adoption before the lep0N tree.

Still in force from 01:3x (section A.3 below): serdes island positions and die-rect shrinks, single-type leaf
growth, the chain spreader as the col answer, `MAX_COLUMN_PAD` raise, extra hold passes for `port_in`,
region-origin or partial HEAD re-binds, unchanged relaunch after the same net failed in the same place.

## 4. Not checked

- Why the route box cost is what it is: I did not read the router source. The 120 CPU-hour figure is a lower bound.
- Results of B6gb / B6gp / B6gsh re-binds, LT2, S4k, S4n, t_hgi2, the G1 proof: all running.
- Whether the HEAD full route kit (52,489 nets) is the regional hk6 tree or the generic tree of section 18.
- Whether `u_st` can take a plan site, and whether the wave generator applies the half-period check to cb kits.
- The S81 K table: I did not compare any count-aligned output with the B6 bind, because none exists.
- The `OT_LAND_RESERVE` what-if on kv3_hub_Wo, and the three cb hook proofs (their logs end at 00:24).

---

# A. Previous review (01:3x PST), unchanged

# FABLE-CLOSURE-STRATEGY 2026-11-15 01:3x PST: technical closure levers for S81, HEAD, QC, KV

Read-only review. Technical physical design only. HBM is parked and not covered. No job, plan or kit was touched.
This replaces the 00:3x review (git history keeps it; section 5 gives the state of its eight levers).

Sources: FABLE-TRIAGE-S81 / -QC / -HEADKV, FABLE-GENBUG, FABLE-KVOVF, the queue from 00:19 to 01:15 hub time, the
autopilot KIT-WAVE lines of 01:04, `failure_breakdown.py` (01:11), lane handoffs, and my own reads of the run
directories named below.

Clock note: several lanes stamp 02:xx-06:xx PST; the hub and host clocks read 01:15 PST (09:15 UTC). Order by file
position, not by stamp.

MEASURED = read by me tonight from a log, plan, kit file or my own script. REPORTED = taken from another report,
not re-measured. INFERENCE is marked.

`failure_breakdown.py` technical classes at 01:11: congestion 1 (kv3_hgi_v7), timing after route 3 (S81
slice_station__t47; KV kv3_phy_v1 +1). Everything else is "running" or "held", so the levers below come from the
run directories, not from that table.

## 0. Five things the lanes have not seen or not connected

1. The S81 B6f and B6g chains did not fail on the plan. Both G0 runs ended with 320 schema errors because their bind
   tree was built from an overlay without the `insertion_target_override` key. They were relaunched at 01:14 (lever 1).
2. No S81 leaf type is signed, and the kit generator's own number says why for most of them: 54 of 75 leaf kits have
   a feed-through slot whose station needs more tracks than the slot has (lever 2).
3. The HEAD die detailed route (pdn2 form) was killed at 209 GB, and the KV one peaked at 181 GB. The cause is the
   PG via mesh in the routing database: 2.31 billion V8 shapes on KV. The hand-stripe form used 7 GB (lever 4).
4. The trees that will feed the S81 regeneration of 350 types do not carry the G1 last-station fix (lever 1).
5. The col street delta is still a model number. Its A/B kits failed to generate a second time at 01:08 (section 3).

## 1. Levers, ranked by types or dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Adopt B6g once, with G1 + flat 165 col window in the wave source before the 350 types regenerate | 350 of 395 types | DIE-S81-92, GENBUG-IMPL, KIT-OPS-5 |
| 2 | S81 | Leaf feed-through slot supply as one family delta (throat width + last-station site), not per type | 79 leaf types (0 signed) | S81-LEAF-PLAN, TL-LEAFT14, DIE-S81-92 |
| 3 | QC | cb family: S4k (net 0 cycles) + patched hooks; `r_dly_spread` per type, not die-wide | 16 cb types + 48 lanes | DIE-QC-103, TYPE-QCCB-GEN, DLY-SPREAD |
| 4 | HEAD, KV | Die detailed route without the PG via mesh in the routing database | 2 dies (die DRC gate) | DIE-HEAD-ROUTE-1, DIE-KV-ROUTE-1 |
| 5 | KV | Clock-form start tree as a plan event now, before more KV types route | KV lane-latency gate; types with start ports | KV-102, DIE-KV-ROUTE-1 |
| 6 | HEAD | One re-bind of all 427 crossings in partition-origin form; then the two seam-hold re-signs | 26 of 26 types | HEAD-99, DIE-HEAD-ROUTE-1 |
| 7 | S81, HEAD | One serdes delta: `phy_pg_macros` + kp4_dchn face register | 11 S81 serdes types + hd_serdes | DIE-S81-92, S81-RESIGN-DEEP, new Sonnet lane |
| 8 | QC, KV | Port-seam hold contract (QC) and merged-bank keeps (KV, QC) | 8-13 QC types; 12 KV hg / hgi kits | QC-HOLDGRT-1, DIE-QC-103, MERGE-CENSUS, KV-102 |

### Lever 1. S81: B6g adoption, and what must be in the wave source first

Evidence (MEASURED, epyc7 `/srv/opentallas-scratch2/claude/s81-b3-clk`):
- `log/B6f.log` and `log/B6g.log` end `G0_RC=1`. `run/b/B6g/g0.log`: "G0 FAIL: 320 errors". All 320 are
  `unknown key 'insertion_target_override'`.
- `run/b/B6f/src/tools/die_plan/schema.py` and `run/b/B6g/...` have 0 lines with that key; `run/b/B6f5eg` has 1.
  `ovl_b6d` and `ovl_b6g` have 0; `ovl_b6e` and `ovl_b6i` have 1. The chains used `ovl_b6d`.
- Relaunched 01:14 as `run/b/B6fb` and `run/b/B6gb`: the key, `reset_replicate` and `tap_group` are in their schema.
- Plan in both: 320 types with `insertion_target_override`, 216 col types with `tap_max_sinks`, 0 of 216 col types
  with a per-type `tap_window` (the flat 165 is a separate KIT-OPS-5 fragment), 0 types with `phy_pg_macros`.
- Both trees: `kit_istations.py` has no `is_place_alt` (G1), no `dly_spread.tcl`, no `u_bin` handling (G2).
- FABLE-GENBUG (REPORTED): the last planned station of a lane pad is unplaced in 297 of 343 S81 kits.
- DIE-S81-92 delta list (REPORTED): 350 of 395 types change a kit input between the wave plan and B6f5e.

Root cause of the delay: three source trees (bind overlay, G0 tree, wave gen replicas) that differ by single files.
The same class hit QC at 01:1x (S4km G0: `budgets.r_dly_spread` unknown in tree6, known in treeA) and the wave at
01:04 (`No module named 'signoff_profile'` at gen on QC and KV rows).

Fix:
1. Adopt B6g (= B6f5e + cg2), not B6f5e and then B6g. cg2 touches 144 col r1 / r2 types; adopting twice builds
   them twice.
2. Before KIT-OPS-5 releases the held rows: G1 in the S81 wave source (GENBUG-IMPL; its c1x proof was in placement
   at 01:12), and the flat 165 col window fragment in the kit environment. Otherwise 297 of 343 kits repeat the
   long-hop defect and regenerate again.
3. G2 (`u_bin` siting) and `r_dly_spread` follow as type deltas when their proofs pass. Do not hold the wave for them.
4. One rule for every plan gate: G0, bind and audit run from one tree copy made by one script. A schema error
   count equal to the number of changed types is a tree fault; the chain should say so and stop, not post "NOT clean".

### Lever 2. S81 leaf: slot supply is short on most of the family

Evidence:
- MEASURED (my script over `ft_track_use.json` of the newest attempt of each leaf kit on six hosts, wave source
  7073a6b4a59; list in section 6): 75 leaf-class kits. Maximum `u_station` per kit: over 1.0 on 54, over 0.79 on 66,
  at or under the 0.5 target on 8.
- t14 is at 1.05 on two slots and never converged in three GRT runs (REPORTED, FABLE-TRIAGE-S81 section 8: 92.5 %
  of the overflow in one 17.3-um gap; ft5 needs 152 % of its tracks).
- The types the watchdog flags at GRT are higher: t62 1.99 (6 slots over 1.0), t72 1.99 (8 slots), t51 1.48,
  t34 1.48, t57 1.48, t70 1.85, t71 1.48.
- Wave rows for the 75 (MEASURED, `kit_wave_stages.tsv`): 0 signed; 30 in route, 22 of those with a slot over 1.0.
- B6e G0 (REPORTED): seam hops of 454 / 494 / 540 / 532 um; 39 of 104 need a die-level change.
- t57 outline growth gives 46 new port-geometry errors (REPORTED): a width change needs the whole column.

Root cause: leaf types are hard cores plus feed-through slots. The slot is planned by bit count and reach; the
station row and the turn are not checked against the tracks of the gap they sit in. This is the FABLE-LEAF-FTSLOT
class, now with a count.

Fix (plan, one family event):
1. S81-LEAF-PLAN runs the `u_station` table on the B6f leaf plan (not on the old kits) and lists every slot over 0.6.
2. For each: widen the gap by a core move (t14: u_vs north 34.56 um, gap 17.3 -> 51.8 um), and move the last
   station out of slots narrower than 20 um. Core shapes stay.
3. Where a move is not possible inside the outline, the answer is a column re-pitch at die level, in the same event
   as the 39 die-level seam hops. Do not grow single types.
4. Proof per changed type: place + GRT only, overflow 0 within 30 iterations.

INFERENCE: the 22 leaf kits in route with a slot over 1.0 will end like t14. I did not open their GRT logs. If
COORD wants one check before acting: read the congestion report of t62 or t72 for the same single-throat pattern.

Limit: the kits are from plan B3v. If B6f_leaf already applies the L6f slot rule, the count will be lower; step 1
gives the real number.

### Lever 3. QC cb family

Evidence:
- S4e (+2 cycles on y_o23) failed bind with PARAM_REGEN + 30 R8_STALE; +1 cannot balance either (REPORTED,
  FABLE-TRIAGE-QC section 6). S4k is the net-zero form: one station on y_o23 (hops 339-348 um), `nb_i12` pad 4 -> 3,
  lane back to 9 cycles. Binding; no result at 01:15.
- Patched hook proofs q00 / q11 / q01 (MEASURED, intel2 `~/type-qccb-gen/*.log`): last lines are the kit preflight
  of 00:23. No GRT number yet.
- `r_dly_spread` what-if on cbf_q01 (REPORTED, place-only, no legalisation): hops over reach 3,583 -> 408.
- The key is a die-level boolean, and the order is `OT_DLY_SPREAD=warn` for all QC kits.

Fix:
1. Adopt S4k as soon as bind + LATCHECK pass. S4k2 adds +2 cycles on the `c_*_01__bcf*` lanes: adopt only if its
   bind shows no PARAM_REGEN; otherwise the bco stations need the same net-zero form (station in, pad out).
2. Make `r_dly_spread` a type key (DLY-SPREAD). With a die-wide switch and `warn`, a stage shortfall on any QC type
   is downgraded silently; a shortfall is a plan item and should stay a failure on the types that opt in.
3. One full place + legalise + GRT of cbf_q01 with the spreader and the patched hooks together before the 16 types
   are keyed. The two what-ifs were measured apart.
4. cbn_q11 cl49ae4555 attempt 3 is running on the old plan and old hooks. Its result says nothing about the fix.

### Lever 4. HEAD and KV die detailed route: the PG via mesh fills the memory

Evidence (MEASURED):
- KV, epyc7 `die-kv-route-1/runs/p1/route.log` (run of 00:50-01:07): `V8 shape region query size = 2309967775`,
  V7 377,514,240, M8 19,385,796, M7 16,371,969. Maximum resident set 181 GB. Ended `DR_DRT_ERROR DRT-0073`
  (no access point on CKINVDCx16 `ck_b*` pins, over 1,000 messages), 32,281 clock nets without wire.
- HEAD, epyc2 `die-head-route-1/head/p16g/drt4_pdn2_TT/drt_TT.log`: 4,972 nets, 48,403 special nets, killed in the
  special-net region query, `EXIT 137`, maximum resident set 209 GB after 39 min. This is the fifth HEAD attempt
  without a routed result.
- HEAD `drt3_clk_TT` (hand-built stripes): V8 region query 0, peak 7.07 GB, reached detail route iteration 0.
- Both kits: `grt/obs.tcl` already carries the die M8 stripes as obstructions (KV 333,530 lines, HEAD 38,134), and
  `pdngen` then adds the real grid on top.
- HEAD pin access passed with 4,629 of 4,970 clock cells inside partition boxes (my script), so the KV DRT-0073 is
  not caused by the partition obstructions. The KV `tail.tcl` written at 01:16 rebuilds the real M1-M3 tracks,
  which is the HEAD fix; the failed run predates it.

Root cause: the die PG grid on M8 / M9 crosses about every 2 um over 300 mm2. Each crossing is a via array. The
router loads every cut as a shape. The die-top problem itself is small (KV 32,281 clock nets, HEAD 4,972 nets).

Fix:
1. Route database: PG as M8 / M9 obstruction stripes only (the `obs.tcl` form, plus M9), no `pdngen` vias. Routed
   DRC against PG shapes is still checked, because the stripes are there.
2. PG correctness (160 of 160 partition grids, region macro grids, the `ot_pg_9` sliver) stays in the separate
   pdngen / PSM run. FABLE-TRIAGE-HEADKV stop-list item 5 ("keep pdn2 only") should read: pdn2 for the PG proof,
   stripes for the route.
3. KV: the 01:16 relaunch carries the track rebuild but still the full grid. Watch its memory; if it passes 150 GB
   in the region query, stop it and use form 1.
4. Report from the first routed database: DRC by layer, split inside / outside partition boxes.

Not determined: what killed the HEAD run (container limit 400 GB, no kernel OOM line readable by me; earlyoom is
likely, INFERENCE).

### Lever 5. KV: clock-form start tree

Evidence (REPORTED, FABLE-TRIAGE-HEADKV section 7, with my read of `runs/p1/CHAIN.log`):
- Data-port start tree: 14 of 159 start edges ambiguous; bind simulation 32 of 500 violations, minimum -208.9 ps.
  Ten edges have a TT-to-FF phase hull of 480-490 ps, wider than half a period.
- Clock-form tree on the same inputs: 193 edges clean, 3,915 crossings at depth 4, simulation 0 of 500, start-skew
  0 of 193 at TT and FF. Cost: 32 retime flops, one start port per clock-tree edge.
- 320 crossings still have no STA tap pair (phy-side partitions), so the verdict line prints FAIL.
- MEASURED: the 01:14 native run failed on an argument: `count_align_plan.py: --sta-clock-ocv: invalid choice`
  (a file path where the tool takes none / flat / table). `CA_NATIVE 2`, `CABIND_NATIVE 1`.

Fix:
1. KV-102 posts the start-form change as a plan event now. Types that gain a start port regenerate; the rest keep
   running. 47 KV types are in the wave on the old form; each hour adds types that will be built twice.
2. DIE-KV-ROUTE-1: fix the `--sta-clock-ocv` call, emit taps for the 320 phy-side crossings, rerun with
   `--start-tree clock`.
3. No per-edge padding and no feed shortening on the 14 edges.

### Lever 6. HEAD: one re-bind in the plan-of-record form

Evidence (REPORTED unless marked):
- Three re-bind forms tonight: 262 ports only (two count frames), all 427 from the region-origin sidecar
  (TYPE_SPLIT on hd_spn and hd_spn_wshim_rx), and now partition-origin (`ca4`; MEASURED: `p16r/CA4.log` started 01:15).
- Partition-origin what-if: 427 crossings at depth 4, worst margin 113.3 ps, 0 of 2,000 chips, 358 origins, 0 relays.
  Open: 12 start hops over 405 um.
- Both-edge count-aligned STA with the freg cycle: 427 of 427, start-skew 0 of 1,556.
- All 26 HEAD types change kit inputs with the re-bind (HEAD-99 delta list).
- Seam hold on real views: mesh0S strip -52.7, mesh7N strip -14.0, ctl strip -11.4 ps FF.

Fix: HEAD-99 binds rp21z20NC only from the `ca4` output, with 18 freg ports. The 12 long start hops take the plan
of record's launch-tap selection. After adoption: re-sign hd_mesh_e and hd_ctl_e with the `*_ft_i` input minimum
set for the 90 ps seam window + 10. elemA hold -6.5 ps on 58 endpoints is a near miss; the ECO is the right size.

### Lever 7. Serdes: one delta for 11 S81 types and hd_serdes

Evidence:
- Island against the PHY PG domain (REPORTED, FABLE-TRIAGE-S81 section 7): the domain floor follows every placed
  block inside the die rect, so B6f4d, B6f5d and B6f5f all overlap; B6f5f is geometrically B6f5d. With membership
  declared (`phy_pg_macros` = the two PMA macros) all 11 types pass with 0 errors, no coordinate change.
- MEASURED: 0 types in B6fb / B6gb carry the key. The wave at 01:04 failed serdes t13, t15, t16, t4 at gen with
  "PG domain ... holds no macro". I saw no implementation post for the `gen_phys.py` change.
- kp4_dchn: clk->q 450 + setup 310 = 760 ps for any insertion (11 S81 rows + hd_serdes). Fix is the input face
  register on 320 bits, +1 cycle on the rx lanes. In re-sign.

Fix: one serdes delta after B6g: `phy_pg_macros` on the 11 types (tool change needs a Sonnet lane today), island
at the derive() rect, kp4 view with the face register, +1 cycle in the S81 and HEAD lane tables, one bind +
LATCHECK per die. No third island position, no domain rect shrink.

### Lever 8. QC port-seam hold; merged banks

QC port-seam hold (REPORTED, FABLE-TRIAGE-QC M3): relay input ports carry `-max 676.36` and `-min -85`; the capture
window left is 72 ps and the tap window (4-90 ps) is taken out of it. stm_v1 ends at -98.27 ps with 3,260 endpoints,
all `port_in`. The hold-arm change lets the kit pass; it does not close the paths.
- The flow change is right under R-MINIMAL (port hold is judged at the die), but it moves the failure to die STA.
- Structural fix (DIE-QC-103, plan): relay capture flops on taps with a window of 20 ps or less, or `-max` near 600.
  Decide from the QC die run: DIE-QC-GRT0-2 must print the `port_in` relay seams as their own class. Its clock kit
  stage ended 01:14 (MEASURED, `s3r_b/CHAIN.log`: `KIT 0`).

Merged banks (REPORTED, MERGE-CENSUS): confirmed merges `ti_b` (12 KV kits, 4,677 flops), `qkd_seq_fan_s` (hub_Eo /
Wo, 1,142 of 1,151), S81 lep `wdata` (4 kits). Unclassified and large: QC `ot_qfd_xs_leaf` `wo_d` / `wctl`, 15 kits,
up to 2,632 flops, 6 of 8 instances short on slw_hc2 / hc3.
- KV: no hg / hgi result yet; r_hgi2 and r_hg were launched 00:37. kv3_hgi_v7 is the one congestion row.
- QC: classify `ot_qfd_xs_leaf` before the next hc2 / hc3 build. If it is a merge, the hc3 hold and reach numbers
  measured tonight are on a netlist that will change.
- Generator default (KV-102, KIT-OPS-5): keep on replicated bank registers; census as a kit check after synthesis.

## 2. Lanes working on a symptom, and failures that came back after a fix

| item | what was tried | why it came back | cause to fix |
|---|---|---|---|
| S81 serdes island | B6f4d, B6f5d, B6f5f positions | domain floor follows the blocks | declared membership (lever 7) |
| S81 B6f / B6g G0 | relaunch per variant | 320 schema errors from the overlay tree, twice | one tree per gate chain (lever 1) |
| S81 idx_tx_n32 | idxA, idxB CTS arguments; hold pad cap 7 -> 16 | mean moved 25 ps between forms; spread 417-432 ps | idxC split clock pin (in re-sign) |
| S81 leaf t14 | attempts 4, 5 and private r1, same kit | one 17.3-um throat | plan geometry, family-wide (lever 2) |
| S81 col_h10_r0_p1 cl911743eb | 30 attempts | place WNS -1,315 ps, no path read | one path read after B6g; no relaunch |
| S81 col_h9_r1 long hops | chain spreader (4,493 -> 4,242) | a 1,317-load fan-out, not a chain | cg2 reset_replicate (in B6g), G1, G2 |
| S81 col street A/B | two gen rounds | plan / bound-tree mismatch each time (`cland_up_ready` at 01:08) | generate from the B6g bind output |
| QC y_o23 | S4e +2, S4j +1 | one pad per column cannot separate rows | S4k net zero |
| QC hold-stall types | accept-rule change | residue is `port_in`, setup-locked | port contract (lever 8) |
| QC `r_dly_spread` | die-wide switch + warn | hides stage shortfalls | type key |
| HEAD re-bind | 262 ports; 427 region-origin | two count frames; TYPE_SPLIT | partition-origin form (lever 6) |
| HEAD die route | DRT-0073, exit 1, DRT-0155, exit 137 | each fix exposed the next; pdn2 costs 209 GB | stripes-only route database (lever 4) |
| KV die route | DRT-0155, then DRT-0073 | HEAD fixes ported one at a time | port the whole HEAD tail; lever 4 |
| KV start-skew | read as 34 model rows | the 14 ambiguous edges pass the STA | clock-form tree (lever 5) |
| Wave gen | `ot_store` fixed 00:26 | `signoff_profile` missing at 01:04 | replicas synced as a set, with a manifest (GENBUG G4) |

## 3. Stop list: technical dead ends

S81
- Any further serdes island position, and any shrink of the 14 PHY die rects.
- Adopting B6f5e and B6g as two events; releasing the 350 held types before G1 is in the wave source.
- idxA / idxB to GRT; kp4A / kp4B shallow-CTS forms; hold pad cap above 7.
- Leaf t14, t62, t72, t51 relaunches on an unchanged plan; single-type outline growth (t57).
- Generalising the col street p2 delta to 216 types on the model number (cutV 0.887 -> 0.544) alone. 5 of the 12
  p2 variants already report `e3.u_w` "no legal spot".
- The chain spreader as the answer to col hops.
- Copying b3x2d per-port windows onto B6 col types; reading 240 / 276 / 702 ps (core taps included) as tap spread.

QC
- Any net cycle change on a single collector-tree leg; raising `MAX_COLUMN_PAD`.
- More hold passes, a larger guard or `-allow_setup_violations` for the `port_in` residue.
- Tile tap 483 -> 568; the t00 + t11 mirror; unchanged cb relaunches.
- `OT_DLY_SPREAD=warn` as a die-wide default.

KV
- hg / hgi forms without the `ti_b` keep; per-edge padding of the 14 start edges; lowering tap caps die-wide.
- Another die detailed route with the full pdngen grid if the running one passes 150 GB.

HEAD
- Region-origin or partial re-binds; splitting hd_spn; any u_epc tap; a latch on the strip seams.
- The pdn2 form as the routing database.

All dies
- Reading the legacy half-period "landed FAIL" or a rise-only readout as a clock result.
- A plan gate run from a tree that differs from the bind tree.
- Unchanged relaunch after the same net failed in the same place.

## 4. Not checked

- The 01:14 B6fb / B6gb result, the S4k / S4k2 binds, the cb proofs, r_hgi2 / r_hg, the HEAD `ca4` run and the KV
  01:16 route relaunch: all running, no result.
- Whether the 22 leaf kits in route with `u_station` over 1.0 show the t14 overflow pattern (no GRT log opened).
- The `u_station` scale: I used the kit's own figure and its 0.5 target; I did not recompute track supply.
- Which of the KV DRT-0073 pins failed (the log was overwritten by the 01:16 relaunch while I read it).
- What killed the HEAD drt4 run.
- QC die GRT / STA: the chain had only finished its clock kit stage.
- The flat 165 window against a die clock on the B6 tap set: no such die run exists yet.

## 5. State of the 00:3x levers

| 00:3x lever | state at 01:15 |
|---|---|
| 1 S81 budget 450 + tap split | in B6f5e / B6g: 320 overrides, 216 `tap_max_sinks` (MEASURED); C1 rows not re-checked |
| 2 col tap windows | flat 165 fragment prepared, not in the plan; per-port after a die rerun on B6 |
| 3 element halves first | heA / heB / hwA / hwB launched 00:20; no result |
| 4 QC cb head-hop patch | owned by TYPE-QCCB-GEN, proofs running; audit rows fixed (0 FAIL) |
| 5 both-edge count-aligned die check | HEAD done (427 of 427); S81 and QC chain scripts installed, no S81 / QC result |
| 6 KV `ti_b` keep | keep forms running; census confirms the merge |
| 7 three col proofs | col_h9_r1 L1 route proof started; street A/B failed gen twice; fd A/B not seen |
| 8 hd_host_e | form B folded into rp21z20NC; waits for the re-bind |

## 6. Data for lever 2

My table: localhost `/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/ftuse.txt`
(columns: type, attempt, max `u_station`, slots over 1.0, slots, source sha). Source files:
`<host>:/srv/opentallas-scratch*/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/<type>/attempt_N/.../ft_track_use.json`
on epyc2, epyc7, epyc8, epyc9, epyc10, intel1.

Highest: kv_leaf t2 4.27, leaf t17 4.27, t31 3.28, kv_leaf t4 2.83, t41 2.81, t16 2.16, t1 2.08, t3 2.08; then 1.99
on t8, t23, t47, t62, t67, t72. At or under 0.5: 8 kits, among them both t54 variants (0.23).
