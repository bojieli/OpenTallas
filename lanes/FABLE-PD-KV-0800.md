# FABLE-PD-KV-0800: KV plan events 7j / 7k / 7m / 7n, KV type failures, kv3_pv_v1n split (2026-11-15 07:55 PST)

Read-only review. Technical PD only. Labels: MEASURED = read by me from a plan, log or record today; REPORTED = from a
lane file; INFERENCE = my reasoning, not measured.

State when written (epyc7 15:50 UTC): G0 PASS, 0 errors, 2350 warnings on 7j, 7k, 7m and 7n. The four strict binds were
still running; no bind, pinned-derive or LATCHECK result exists yet for any of them. Every adoption verdict below is
conditional on the variant's own bind and LATCHECK.

## 1. Verdict

| variant | sha | verdict |
|---|---|---|
| 7j | 6928f8db88c2 | ADOPT as the step, if its rebind passes. Keeps the ECTL round trip at 18, so the signed ectl cores stay valid. |
| 7k | 7c8bf86c127d | Fallback only. It drops the o_ectl eN / tN / kf stations and reopens the -559 to -633 ps family for no gain. |
| 7m | 5089a48698e7 | DO NOT ADOPT as built. Two defects, section 2. |
| 7n | b7543044989d | Tap value is right, but it sits on 7m and is incomplete. Rebase on 7j and complete it (section 3). |

## 2. 7m: the equal-depth form is right in principle, the event is not complete

What 7m does (MEASURED, kvgeom7m.py and the plan): copies the kv3_hg chains of `o_ectl_Q_N_rq` (+3) and `i_slg_Q_N_krsp`
(+3) to the 7 other hg frame types; 56 lanes, +168 cycles; every ECTL round trip goes 18 -> 24.

What is sound (MEASURED):
- All 8 hg types have the same windows for these two buses in the type frame (rq W face y 24.2, 13.0 wide; krsp W face
  y 212.6, 363.1 wide) and the same core origins, so the copy is geometrically valid.
- Declared hops: krsp 4 x 374.0 um, rq 4 x 365.5 um. None over 405. rq launches at ectl_q0, the only core with `req_*`
  pins (x 61, y 1341-1351): 280 um to the first station.
- No R8 interaction: the ECTL legs are not in the R8 table at all (0 of 5911 members in the control and the 7f table), so
  there is no pad to trade against the stations. A stationed krsp must move the round trip.

Defect 1, the round trip is a literal inside four signed cores (MEASURED).
- `kv_regen.py`: RESPONSE_LAT = 8 + krq + krs, QK_ISSUE_AGE = max(34, RESPONSE_LAT + 11). 7m gives 24 / 35. QK leaves
  its floor of 34 at RESPONSE_LAT 24 (23 would still give 34).
- `cores/harden/results/ectlk_bound1834_1031/README.md`: the quarter cores carry the two values as literals of
  `qkd_ectlk_reference.u_leaf`; they were changed 91 / 80 -> 34 / 18 and re-hardened. The archived records are
  qkd_ectlk_q0..q3, signed 2026-10-31 (q0 pin-register mean 231.99 TT).
- So 7m makes qkd_ectlk_q0..q3 (4 of the 34 signed KV cores, 32 instances each on the die) implement the wrong ectl.
  The event has no core rebuild, no miter and no check of the QK calendar consumers at 35.
- Not checked by me: whether the strict bind fails on this or silently writes 24 / 35 onto the leaf.

Defect 2, the krsp chain ends 406 to 788 um short of the pins (MEASURED from the plan pins files).
- The chain ends at the ectl row centre (626, 1270). `rsp_data` pins are on the W edge of each core: q0 x 61, q1 x 337,
  q2 x 657, q3 x 976, y 1325-1493.
- Manhattan from the chain end: q0 646-788 um, q3 406-573 um, q1 344-512 um, q2 86-254 um. From the last station
  (306, 1216): q3 780-947 um, q2 460-628 um.
- No single capture point reaches all four cores in 405 um: the pins span 915 um in x.
- Basis for the timing cost: FABLE-KVOVF 11.2 measured -302 ps on this same fan-out at 752 um path (494 endpoints).
  INFERENCE: the residue at 406-788 um is still negative by tens to a few hundred ps; not measured.
- G0 does not see it: it checks only the hops the entry declares.

Consequence: adopting 7m costs one rebuild of four signed cores and still leaves `rsp_data` open; closing it then moves
the round trip a second time and rebuilds the cores again.

Fix, one event (call it 7p), owner KV-102:
1. krsp +4, the fourth stage replicated per core on the streets next to each core's W edge (x 30 / 306 / 605 / 925,
   y about 1300); rq +3 as now. Round trip 25, QK_ISSUE_AGE 36, same on all 8 hg types.
2. In the same event: qkd_ectlk_q0..q3 literals at 36 / 25, miter (the bound1834 bench), re-harden, re-sign. New lane
   KV-ECTLK-RL (Sonnet); the 10-31 recipe is on file.
3. Before launch: confirm what else reads QK_ISSUE_AGE / the QK_CONSUME slot (kvs_attn calendar, boot image).
   If a consumer is fixed at 34, the limit is RESPONSE_LAT 23 and the +7 form does not fit; then the krsp path needs a
   floorplan answer (ectl pins toward the W face), not stations.

## 3. 7n: hub_C taps

MEASURED:
- Signed record `Qwen_ROM/qkd_ahub` (hc_qkd_ahub__604_8x440_64, 2026-11-05, SIGNED): pin-register insertion mean 228.67
  TT / 179.9 FF, spread 96.21 / 68.53, n 623. 7n writes exactly these on ck[0..6]. 21 ps early of 250, inside the 40 tolerance.
- Pin sites agree: signed DEF ck[0] (302.376, 241.92), ck[1] (190.056, 73.44), ck[3] (149.976, 50.0) plus the core
  origin (216, 1045.44) equal the plan tap xy. The DEF has per-pin trim buffer chains, so one value for seven pins is
  reasonable; per-pin means are not in the record.
- 7m -> 7n changes 21 fields, all on kv3_hub_C ahub taps. No lane, station or R8 change, so no latency effect.

Gaps:
1. `kvs_ctl.ck` is untouched at 603.2 / 500.2 (an old ETM). The signed qkd_kvs_ctl record (371.52 x 371.52, 2026-11-05)
   measures 283.5 TT / 233.96 FF. The row is 320 ps off. Add it.
2. The plan `hard_cores` entries for ahub and kvs_ctl have no `lef` / `lib` (ahub note: "lef/lib pending"). The wave
   row for kv3_hub_C says PROVISIONAL[qkd_ahub:pending, qkd_kvs_ctl:pending] and "SIGNED IN COUNT BUT NO WAVE VIEW
   (qkd_ahub)". The tap row alone does not change what the kit times. Attach the signed view packs in the same event.
3. A newer ahub record exists (`qwen_kvsys/qkd_ahub`, eco1, 2026-11-14, verdict NOT SIGNED, 221.09 / 174.4). Keep the
   signed 11-05 values, as 7n does; do not mix the two.
4. It is built on 7m. Rebuild it on 7j: taps are independent of the stations.

Not checked: how the kit timed the old 1003.4 rows (clamp or not); R8 straps on hub_C (no strap field changed).

## 4. 7j / 7k and the rest of the hg family

- 7j = 7f without stations on rq and krsp: 40 stations on 13 buses of kv3_hg, +160 lane cycles. Declared hops 272 to
  376 um (MEASURED, all <= 405). Leaves krsp at -568 ps and rq open, as FABLE-CLOSURE-STRATEGY says.
- Stations in 7j are on kv3_hg only (4 of the 32 hg instances). On hg_v1 .. v1p6, 14 of the 15 buses exist and 3 windows
  sit elsewhere (i_head 21.8 -> 235.9, i_hst 358.7 -> 245.1); hg_v3 lacks 5 of the buses. These types already carry 20
  older bus stations each. Whether they have the same nine violating families is not measured (KVOVF: inferred).
- Cheap measurement, no new build: placed databases of kv3_hg_v1 (attempt 6), v1p3 (11) and v1p4 (12) sit on epyc10,
  held. Run the KVOVF 11.2 family listing on them instead of routing them.

## 5. KV type failures (kit_wave_stages.tsv 07:36, failure_breakdown 07:41)

| rows | what it is | root cause | fix, owner |
|---|---|---|---|
| kv3_hg +5 "placed, route held" (hg, hg_v1, hg_v1p3, hg_v1p4, hub_Ei, sys_c) | ROUTE hold SKIP-OLDPLAN: kvgeom5 attempt, current event kvgeom6 | Flow. The type block of all six is identical in kvgeom5 and kvgeom6 (MEASURED, whole `partition_types` entry equal). None has a kvgeom6 build. | hub_Ei, sys_c: release the hold, route the placed build (TYPES-KV-FAIL + KIT-OPS-5: hold keyed on block, not event). The four hg: do not route, see stop list. |
| kv3_hg_v3, kv3_hgi_v5 "held by die owner" | FAIL route INFRA, "client lost, kit logs idle 3.0 h", 11-14 12:05 and 08:09, event kv102sem_ftgrid | Infra orphan, no design verdict. No job since (19.6 h and 23.6 h). Attempts 14 and 6. | Relaunch on the adopted 7 event only (both blocks change in 7j). TYPES-KV-FAIL. |
| kv3_hub_C | No flow error row now; RUNNING with no stage, PROVISIONAL on ahub and kvs_ctl | Signed child views not attached to the plan cores (section 3 gap 2) | KV-102 in the 7n rework. |
| kv3_hub_Ei prelint | est 289,525 flat cells > 150,000 | Advisory plan estimate; the placed build exists | none |
| kv3_phy_v1, kv3_sys_SD timing rows; kv3_phy, kv3_sys_SD_v1 provenance rows | stale rows | REPORTED signed off and archived (FABLE-PD-PHY-0710, TYPES-KV-FAIL 07:1x) | KIT-OPS-5 clears the rows. |

Repeat failures: the stages table keeps one row per item and event, so I cannot count failures per class from it.
Attempt numbers (MEASURED): kv3_hg 16, hg_v3 14, hgi_v2__cl2862d491 13, hg_v1p4 12, hg_v1p3 11, hgi_v1__cl141fc26e 11.
The measured cause for the hg / hgi family is FABLE-KVOVF 11.2: single-cycle hops of 0.75 to 2.1 mm (kv3_hg after CTS:
WNS -705 ps, 4,915 endpoints). It is a plan-station problem; no kit setting or relaunch closes it.

## 6. kv3_pv_v1n: the split is the wrong fix

MEASURED on the live one-piece build (epyc10, kvgeom5 attempt_7; block identical in kvgeom5, kvgeom6 and 7m):
- Floorplan: 389,907 instances = 389,887 standard cells + 20 macros (16 kv3_pv_pair, 4 pv_join_t; 1,275,610 um2 of
  3,284,580). Standard-cell utilisation 2.9 %.
- It ran in one OpenROAD process: global place 2 h 12 min at 8.0 GB peak, CTS 2 h 54 min at 18.8 GB peak.
- The 7.1 M cells / 425 GB is the census figure with the hard-core interiors; the kit never places them.
- After placement 808,495 instances, after CTS 823,409. The growth is repair: 156,221 and 153,834 buffers inserted in
  about 38,800 nets.
- Timing: setup worst -1488 ps placed, -1573 ps after CTS, 17,239 endpoints; hold -328 ps, 56,107 endpoints; clock
  skew 438.6 / 493.0 ps.
- Auto geometry: register-to-register max 3009 um, 10,345 pairs over the limit, relay_collapse 209, pin-register
  max 470.6 um, clock_on_macro 20, clock_tap_sinks 3118.

Reading: the type fits one run with large margin. What fails is the same class as hg: unregistered hops of up to 3 mm
(hence the 310 k buffers) and a clock with 440-490 ps skew. A split fixes neither; it adds landing pairs and cut lanes.

Answers:
- (A), (B), (C): moot. Do not make the compiler change for a second tx pin; do not diagnose L2359; do not rebalance x1.
  If a split is ever needed for another reason, the second tx pin (same flop, one pin per side) is the smaller form.
- Ranked fix:
  1. Family listing on the attempt_7 `4_cts.odb` (as KVOVF 11.2: family, endpoints, worst slack, from / to, length).
     Owner KV-PVSPLIT, re-tasked; hours, no build.
  2. Plan stations per matched group for the families, on all pv types in one event, and the clock sinks off the
     macros / tap sinks per KVOVF and CLOCK rules. Owner KV-102 (next event, after 7j).
  3. Remove the split from 7g; 7g = 7f + split has no remaining purpose.

## 7. Ranked fixes

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | Adopt 7j when its rebind and LATCHECK pass; relaunch the 19 changed hg / hgi types on it | section 4 | KV-102, TYPES-KV-FAIL |
| 2 | Drop the pv_v1n split; family listing on the placed build, then pv stations | section 6 | KV-PVSPLIT (re-tasked), KV-102 |
| 3 | 7n rebuilt on 7j + kvs_ctl.ck 283.5 / 233.96 + ahub and kvs_ctl views attached | section 3 | KV-102 |
| 4 | 7p: krsp +4 with a per-core last stage, rq +3, with the ectlk q0..q3 rebuild at 36 / 25 in the same event, after the QK consumer check | section 2 | KV-102 + new KV-ECTLK-RL |
| 5 | Release SKIP-OLDPLAN on kv3_hub_Ei and kv3_sys_c (block unchanged) | section 5 | TYPES-KV-FAIL, KIT-OPS-5 |
| 6 | Family listing on the held placed hg_v1 / v1p3 / v1p4 databases | section 4 | TYPES-KV-FAIL |
| 7 | Raw start / reset branches (item 6) | not reviewed here; FABLE-KVOVF 16 has the diagnosis | KV-RAWFIX |

## 8. Stop list

1. No adoption of 7m, or of 7n as built.
2. No further work on 7g, B1 / B3 gates, `type_split` landing changes or the L2359 bind error.
3. No routing of the held kvgeom5 hg / hg_v1 / hg_v1p3 / hg_v1p4 builds, and no unchanged relaunch of hg or hgi types
   on kvgeom6: placement timing is -700 ps by plan.
4. No second ECTL depth change after the first: decide the krsp depth once, with the core rebuild.
5. No tap row from the unsigned ahub eco1 record.

## 9. Not verified

- Bind, pinned-derive and LATCHECK results of 7j / 7k / 7m / 7n (running).
- Whether the bind detects a RESPONSE_LAT change against a hardened ectl core.
- The size of the `rsp_data` residue in ps, and the proposed per-core stage sites (streets read from the kvgeom7.py
  comment, not from a placed database).
- Which consumers fix QK at 34.
- The pv_v1n violating families (only totals read); whether the other pv types behave the same.
- R8 strap effects: none of 7j / 7k / 7m / 7n changes a strap field, but the pinned-derive result is the proof.
- Side effect: I ran `tools/failure_breakdown.py` at 07:41; it rewrites the failure section of the release tree as designed.
