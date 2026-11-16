# FABLE-CLOSURE-STRATEGY 2026-11-15 23:15 PST: die-phase and TT-repair keys are inert on S81 and QC kits; seven levers; stop list; unowned areas

Read-only review by FABLE-CLOSURE-2315. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 21:15 strategy; FABLE-PD-S81-F2r, FABLE-PD-QC-S4q8, FABLE-PD-KV-2215; handoffs FABLE-FIX-KV-PV / HEAD-TYPES /
QC-HCFE, KV-102, KV-Q2-CLK; queue posts 21:20 to 23:20; `failure_breakdown.py` 23:13; `kit_wave.json` / `kit_wave_state.json`.
Measured by me (23:15-23:30 PST): `gen_phys.py` of the four live wave source trees (grep counts, epyc8 / epyc10);
`pdn.tcl`, `config.mk` and the file list of every S81 kit generated in the last 90 min on epyc8 / epyc9 / epyc10; every
`postcts_gate_tt.json` younger than 200 min on six hosts; the SDC and gate JSON of S81 serdes__t12. Text and JSON only,
no database opened, no STA run.
MEASURED = read by me. REPORTED = lane post, Fable review or COORD. INFERENCE is marked.

`failure_breakdown.py` 23:13: S81 41/394 types (62/64 cores), HEAD 19/26, QC 7/127, KV 5/56.

## 0. What changed since 21:15

| 21:15 lever | state 23:20 |
|---|---|
| 1 gate RC cross-die | Owned now. Two independent fits agree: signal C x1.40 (S81 bksel b1p) and x1.46 (QC hc2). Table-mode fit (COORD 23:2x): 14 ps pessimistic on col (-281 vs -267), 57 ps optimistic on b1p; guide / routed length 1.08-1.17 on both, so detour is not the cause. QC checks pending. |
| 2 `DRT-0255` forms | C3b hook READY (claude/pgcap-grt-hook-1115-1, default off), in no die tree. Die-phase keys set die-wide for S81 in the G3b adoption commit baf7c3e4ce5: NOT acting, section 1 lever 1. |
| 3 S81 col stations | F2r composed, review done: closes the frame_int_o0 chain, 66 of 1,387 endpoints. Five other classes remain (F2s). |
| 4 HEAD signed hd_tile | Done in form: 33 of 144 MY units at DRC 0 on the 717.12 abstract; signed-view kits nf13s / nf13t building. |
| 5 KV | 7uh adopted 23:18. q2 SIGNED. v21 superseded by v23 / v25 (hard ring child cores); 24 of 36 ring masters had failed unowned, 23 relaunched. |
| 6 QC events | S4q6d adopted (78 changed types). S4q8 reviewed: not blocking, not sufficient. |
| 7 S81 svc and cores | svc: no answer to the 20:49 synthesis fail (78 min, NEEDS-LANE). bksel: ECO path closed as a dead end; fx1 / fx2 on calibrated RC in GRT. |

## 1. Levers

| # | dies | lever | unblocks | owner | status |
|---|---|---|---|---|---|
| 1 | S81, QC, HEAD | Wave source trees that implement the keys in `die_gen_env` (die phase, TT repair, C3b) | S81 387 types; QC 120; HEAD 3 | TOOLS-CONVERGE-1115, KIT-OPS-5, GENBUG-IMPL | **NEW for S81 and QC**, HEAD part found by FABLE-FIX-HEAD-TYPES |
| 2 | all | One signal-RC model for gate and pre-route repair; `repair_design` in the TT repair | QC hc 16 types, S81 col 216, bksel, HEAD ctl / host | GENBUG-IMPL (table), FABLE-FIX-QC-HCFE, FABLE-FIX-S81-BKSEL | owned, progressing; one gap |
| 3 | S81 | col F2s: ROM clock pin, glue tap trees, full-cycle reset relay, reset copy chain, IFN = 0 | 216 types | FABLE-FIX-S81-COL, DIE-S81-92 | owned, direction right |
| 4 | QC | hc leaf: S4q8 + calibrated repair, then `wv` / `wep` copies and leaf placement group; strip density key | 16 hc types | FABLE-FIX-QC-HCFE, DIE-QC-103 | owned, direction right |
| 5 | KV | Ring child cores (hg v25, pv step 1), then the 3-way pv cut; masters and ectlk q0 / q1 / q3 first | 51 types | FABLE-FIX-KV-PV, KV-102 | owned, direction right, long chain |
| 6 | HEAD | Buffering on the repaired tree (host_e SRAM -> u_epc, ctl reset tree, serdes private leaf); hd_st_k5 | 7 types + hd_st_k5 | FABLE-FIX-HEAD-TYPES | owned; hd_st_k5 NOT owned |
| 7 | S81, QC | Serdes / phy families and the QC glue types at -180..-500 at the gate | S81 11 serdes + phy__t1; QC glue, tt_ctlm, phy_serdes x2 | none | **NEW, unowned** |

### Lever 1. The keys are in `die_gen_env`, the trees do not read them (NEW)

Evidence (MEASURED). Count of the key name in `tools/die_plan/gen_phys.py` of each live wave source:

| die | wave src (kit_wave.json 23:21) | OT_TT_SETUP_REPAIR | OT_PG_DIE_PHASE | OT_PGCAP | `die_gen_env` carries |
|---|---|---|---|---|---|
| S81 | s81-b3-clk/run/b/B6gG3b/src | 0 | 0 (0 in all of tools/) | 0 | TT repair both, die phase + 4 PG keys |
| QC | wt/qc-s29-tree2 | 0 | 2 | 0 | TT repair both; no PG key |
| HEAD | kw45/src_head_rp21z_pgcaplec_c327 | 0 | 2 | 0 | TT repair both; no PG key (item_env only) |
| KV | kw45/src_kv_kvgeom7uh_c1 | 9 | 2 | 0 | TT repair both; no PG key |

- S81: every kit generated after the 22:26 adoption that I found (`pdn.tcl` written 22:4x-23:2x PST: 85 on epyc8, 65 on
  epyc9, 59 on epyc10, slice_station / leaf / serdes) has M7 `-offset {4.128}` = core phase, no `pg_pin_check*` file, no
  `tt_setup_repair*` file, and `config.mk` holds only `OT_PG_TRACK_TRUTH=1` / `OT_PG_CELL_KEEPOUT=0`. Example: epyc10
  `.../3fa87b84b18/items/slice_station__t43/attempt_4/gen/slice_station__t43/pdn.tcl` line 11 (22:47 PST).
- All 16 gate JSONs of the last 200 min (S81, HEAD, QC) come from kits with no TT repair step.
- REPORTED: 387 of 395 S81 types have N/S M7 face pins under the core-phase strap pair (DRT0255-PROOF 21:31); die phase
  routed DRC 0 on t49, hd_ctl, hd_spn.

Root cause: the adoption commit changed the environment, not the tree. The G3b tree was cut from an older main than the
die-phase and TT-repair code. A key the generator does not read is silent.

Consequence (INFERENCE from the 21:31 census): the about 88 S81 kits now running will reach DRT on the core phase and the
face-pin types among them stop with `DRT-0255` after 4-13 h of place and route. Their gate numbers are unrepaired.

Fix:
1. TOOLS-CONVERGE-1115 / KIT-OPS-5: S81 and QC wave src = main + plan data overlay (the head-v2 pinned form), with the
   C3b hook merged first so one tree carries die phase, TT repair and OT_PGCAP. Same for HEAD (already asked 23:11).
2. Accept test per die before any volume: one fresh kit has `pdn.tcl` M7 offset 8.448, a `tt_setup_repair*` file and,
   for QC, the `pg_pair_cap.tcl` source line last in `grt_pre.tcl`.
3. DIE-S81-92 / KIT-OPS-5: decide now on the running S81 G3b kits: those still before floorplan-dependent work should
   regenerate on the new tree; the 8 serdes types without N/S M7 pins are not exposed.
4. QC has no PG key at all in `die_gen_env`: add die phase (128 of 130 types exposed) with C3b in the same switch.

### Lever 2. Signal RC: owned; one gap

Evidence: REPORTED, same netlist at GRT with layer C scaled: hc2 x1.0 +2.48 -> x1.4 -155 -> x1.5 -194, routed -178.75
(factor 1.46); bksel b1p x1.0 +1.0, routed -157.6 (factor 1.40). Table-mode fit: col -281 vs -267; b1p 57 ps optimistic.
Repair at GRT on FF libs and kit RC saw 6 slew violations on hc2, sign-off TT has 465. All three route-keep ECOs on bksel
lost setup (-158 -> -318, -219 -> -481, -257 -> -704).

Root cause: two effects, not one. (a) Capacitance per length is under-read on dense nets (coupling), which a C scale or
table fixes. (b) INFERENCE from the two table errors with equal detour ratio: the table is fitted on long, sparse col
edge wires (pessimistic there) and under-reads dense short-net cores. One table per layer cannot fit both.

Fix:
1. GENBUG-IMPL: fit the table on two populations (net length under / over about 100 um, or by local routed density)
   and accept only if col, b1p and hc2 all read within 30 ps. Until then use the plain x1.45 scale for the REPAIR step
   (pessimism in repair is cheap) and keep the gate read advisory.
2. The TT repair must include `repair_design` (slew) on TT libs, not `repair_timing` only: hc2, hd_ctl (7 weak stages,
   646 ps) and bksel are all slew classes that `repair_timing` on a met design never touches.
3. Direction of BKSEL and QC-HCFE is right: pre-route repair on calibrated RC, no ECO. Do not wait for the table.

### Lever 3. S81 col: F2s, in the right order

Evidence (REPORTED, FABLE-PD-S81-F2r, routed TT, r2 pilot): ROM rd_out -> cfg7_seq about 830 endpoints at -169 (ROM clock
pin 270-370 ps after the capture pin; address side +348); lpl_13_r -> t6_payload 380 at -242 (tap tree clk_t22 at 770
against target 450; tap means 247..744, clk_t18 876, clk_t2 4,756 sinks against a cap of 1,500); half-cycle relay 25 at
-240 / -319; reset copies 74 at -151; go_tag 4 at -120.

Judgement: direction right. 1,210 of 1,387 endpoints are clock problems, not distance. Order by endpoints: glue tap
trees and ROM pin first, then relay and reset copies. Two cautions:
- The ROM pin offset (255 ps early) and the tap trees interact: fix the trees to target first, then re-measure the ROM
  offset; a 255 ps offset fitted on today's trees is wrong after the split.
- `reset_relay_full` and station hops cross taps that differ by up to 500 ps today: read FF hold on the first F2s pilot
  before the 216 types are released.

### Lever 4. QC hc

Direction right (FABLE-PD-QC-S4q8). KIT-OPS-5 removed `OT_CLAND_STRIP_DENS=1.0` from the 17 hc rows at 23:20. Open: the
proof kit needs lever 1 (tree2 has no TT repair), so FABLE-FIX-QC-HCFE's private key is the only path until the tree
switch. The leaf spread (110-364 um boxes at about 10 % fill) is the real cause; if the proof leaves the leaf under -42,
go to the placement group before more RTL copies.

### Lever 5. KV

Direction right: hard ring child cores are structural and reuse signed masters. Risk: the chain is long (masters ->
ectlk q0 / q1 / q3 -> v25 bind -> hg pilot -> pv ring delta -> placed census -> 3-way cut). Run the pv ring plan and the
cut compiler now, in parallel with the hg event, as the lane already does. 7uh: `cland_tstart_in` is 324 um inside the
soft hroot on M7; DIE-KV-ROUTE-1 has not stated the die-side length.

### Lever 6. HEAD

Evidence: hd_host_e -225.98, hd_host_w -179.04, hd_serdes -261.37, all unrepaired gate reads (lever 1). REPORTED (COORD):
host_e is badly buffered SRAM -> u_epc wires. MEASURED: hd_st_k5 NF13a attempt 2 gate -258.32, pin insertion 416-516,
`pdn.tcl` 4.128 (core phase); hd_st_n3_turn a2 failed `DRT-0255` again at 22:56 (needs C3b); hd_host_n a2 kit on epyc7
is 4.128 (a3 relaunched keyed, REPORTED).

Fix: FABLE-FIX-HEAD-TYPES continues the backport kits (he2 / hw2 / sd2). For host_e: if the repaired read stays under
-42, register the SRAM outputs at the macro edge or site the u_epc capture row at the SRAM, not more buffers. hd_st_k5
and hd_st_n3_turn are not in the lane's list of 7: add them.

### Lever 7. Serdes / phy / glue families (unowned)

Evidence (MEASURED):
- S81 serdes__t12 (epyc7, 22:11 PST): gate TT setup -496.16, hold -157.11, pin-register insertion 144-409 against the
  250 bound (spread 265). Outline 2,885.76 x 1,226.88, 32 grid taps at 400 um pitch, `OT_TAP_MAX_SINKS=100000`, no
  private leaf, no TT repair. serdes__t4 / t14 and 7 slice_station types fail `sdc_lint`: clock-port window (-24.6 /
  -34.4) outside plan `clock.tap_window` (-59.7 / -74.4 .. 0).
- S81 phy__t1 attempt 11: `DRT-0073` no access point for `u_bound.u_core/k_v[1]`.
- QC glue attempt 3 gate -491.66; tt_ctlm -178.81; coll_ftc -106.66 then `DRT-0255`.
- QC phy_serdes: gen "hard wrapper requires a placed macro with LEF and TT/FF views" (28.7 h); phy_serdes_b: "native
  clock table must resolve inside its declared native base" (33.3 h).

Root cause (INFERENCE for serdes): a 2.9 mm type on one clock with a 265 ps insertion spread is the HEAD hd_serdes class
(-261 -> -40.58 with private leaf + repair, REPORTED). The path list was not read.

Fix: one lane for S81 serdes + phy (read the t12 gate paths, apply the HEAD private-leaf form, cap tap sinks, pin-access
view for `k_v`), one lane for QC phy_serdes / phy_serdes_b (build the macro views), and DIE-QC-103 reads glue and
tt_ctlm paths on the first S4q6d kit.

## 2. Stop list

1. Volume on S81 G3b or QC S4q6d kits from the current trees: core-phase PDN and no TT repair (lever 1).
2. Reading any gate number from S81, QC or HEAD wave kits as "after repair". None has the step.
3. Route-keep ECO as a setup or hold closer on cores at -150 or worse (bksel: three of three lost setup).
4. One RC table per layer as the final gate model before it fits col, b1p and hc2 together.
5. Releasing the 216 col types on F2r; stations as the answer to the ROM, tap-tree and half-cycle classes.
6. hc2 as closed on the S4q8 gate read; `BANK_PIPE` now; more select copies before the leaf placement is measured.
7. Relaunch of hd_host_e / hd_host_w / hd_serdes / hd_st_k5 on c327; hd_st_n3_turn before C3b is in the tree.
8. KV: v20 / v21 ring split, PVGEN 2-way, pv kits on kvgeom6 (band no-site), 7p.
9. All items of the 21:15 stop list not named above remain.

## 3. Areas with no owner

- S81 serdes (11 types), phy__t1, eng__t1: lever 7.
- S81 svc (16 types): 20:49 synthesis fail unanswered; the write-port merge has no visible owner.
- S81 stale 242: about 200 are superseded / dedup col rows (covered by the col event), the rest are leaf / kv_leaf
  rows now regenerating on G3b; no separate technical class, but they inherit lever 1.
- HEAD hd_st_k5, hd_st_n3_turn, hd_host_n: outside FABLE-FIX-HEAD-TYPES. hd_host_w and hd_host_e are owned.
- QC phy_serdes, phy_serdes_b, glue, tt_ctlm; sle_ctl x6 (`rst_xn` 8-9 shared loads in the hard landing child proof, a
  design fault in the landing ring, with DIE-QC-103 but no post).
- KV hub family (hub_C / Ei / Eo / Wo, sys_c, pc): today a wave-config class (fixed 23:18). hub_C "leaf modules without
  a source qkd_ahub" is separate. No hub type has reached place on 7u, so its physical state is unknown.

## 4. Not checked

- Whether a hook outside `tools/` of the G3b tree applies the die phase; I read `pdn.tcl` of about 200 kits and all are 4.128.
- Which of the running S81 kits are past floorplan; how many of the 85 / 65 / 59 are the same kit replicated.
- serdes__t12, glue, tt_ctlm, hd_st_k5 path lists (gate JSON only).
- The table-mode fit itself; the two-population split is my inference from two numbers.
- F2s, S4Q8BQ, v25 bind results: none posted by 23:20.
- Whether hd_st_k5 is among the 19 signed HEAD types under an earlier event.
