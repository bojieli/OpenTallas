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
