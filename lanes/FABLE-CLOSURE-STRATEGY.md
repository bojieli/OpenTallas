# FABLE-CLOSURE-STRATEGY 2026-11-16 03:43 PST: ring-ff is proven at post-CTS; every converged tree misses three fixes merged after it was cut

Read-only review by CLOSURE-STRATEGY-0343 (Opus; Fable at weekly limit). Technical physical design only. HBM parked.
Nothing launched, stopped or changed.
Read: FABLE-CLOSURE-STRATEGY 01:30, FABLE-PD-S81-0117, FABLE-PD-HEAD-NF13b, FABLE-PD-QC-S4q9 (+ section 6),
FABLE-FIX-S81-COL-SPECS; handoffs *-O.md, FABLE-FIX-QC-HCFE, GENBUG-IMPL, DIE-QC-103; queue RESULT / READY / RULING /
MERGED lines 00:30-03:14; `failure_breakdown.py` 03:14.
MEASURED = read by me 03:15-03:40 (logs, JSON, tree files on epyc8 / epyc9 / epyc10; no odb opened, no STA run).
REPORTED = lane post. INFERENCE is marked.

`failure_breakdown.py` 03:14: S81 41/394 types (62/64 cores), HEAD 19/26, QC 7/127, KV 6/56. Those classes are
kit-row states. The technical classes below come from the kits.

## 0. Verdict

1. **S81 ring_place ff now works through CTS, not only at place.** In A_t68 and B_t65, epyc9
   `fable-pd-s81-0117/*/5_1_grt.tmp.log` shows the final congestion `0 / 0 / 0` after CTS. A_t68 went 116 -> 1 -> 0 by
   iteration 10; B_t65 needed 3 extra iterations. The lane kits on the same rows read 131,263 and 354,826 at
   iteration 5. r282 is merged at c3c59b7dfea. The remaining S81 leaf risk is the STRIP / ft class (t34, t62) and
   E/W-face rings on resized rects. It is no longer the ring form.
2. **All four converged trees predate three merged flow fixes** (MEASURED on epyc10 `kw45/src_*_pin_*`):
   - `tt_setup_repair.tcl` has no `skip_buffer_removal` and no `OT_TT_SETUP_MEASURE`. tt-keep was merged at 006eb0df5ae.
   - `rc_signal_scales.json` has types `{s81 1.00, qwen_compute 1.25}` only, without HEAD x1.13 or KV x1.10.
     rc-signal was merged at c03ba6c3b92.
   - The S81 tree has no `_frozen_band`: the ring-ff guard was merged at c3c59b7dfea.

   So a HEAD or KV gate read on these trees under-reads by about 150 ps (he3 -10.49 at the gate, -160.14 routed). On
   any die, a GRT TT repair can also write back a worse database than its log says (sd2: -55.88 before, -127.85 after
   reload).
3. On HEAD, the remaining setup failures are DRV / fan-out structure on real RC (he3, hd_serdes). The clock is not
   the cause. Fix them in RTL replication. Repair iterations will not close them.

## 1. Known since 01:30: what I could verify

| claim | state | evidence |
|---|---|---|
| ring_place ff r282: t68 / t65 huge -> 0 | **VERIFIED, post-CTS** | A_t68 `Total ... 5.58% 0/0/0`; B_t65 `9.24% 0/0/0` (full kit flow, place+CTS+GRT, no early stop) |
| F2s composing with ring-ff + col clock | **NOT composed** | try1 stopped at RINGFF accept: 82 svc frozen bands lost ff; root cause `_frozen_band` (S81-RINGS-O 02:50), fixed in r282. try2 hit a cp permission error. Col rows `tap_core_etap`, `tap_core_src`, `core_pin_lead_ps` are still missing on all 216 col types (S81-COL-O 02:44) |
| col measured windows p90 41 vs flat 165 | REPORTED, re-measured | IMPL proof CTS: p50 10 / p90 38 / max 49. But tap means are 415..542, above the 380..490 accept band (S81-COL-O handoff) |
| HEAD he3 gate -10 vs routed -160; RC per die | VERIFIED as merged, **NOT in any tree** | see verdict 2 |
| he4 skid RTL form running | REPORTED | bind + LATCHECK 329/329 on NF13a; kit from synth on epyc2 |
| NF13b FREG k5 -258 -> +76 | REPORTED, gate only | k5b post-GRT +75.86 / 0 violators; in detail route. NF13b COMPOSED 02:47 with F1 fixed (table regenerated, 12 rows +1, LATCHECK 329/329) |
| QC S4q9b +113 knee stations | REPORTED (checker) | S4q9b FAIL 0, worst 399.98 um; adopt pending DIE-QC-103 gates |
| hc2 still failing | REPORTED | P0 (E1 repair result) in detail route, 19.4k violations after iteration 1; no sign-off yet |
| QC class-A DRT-0255 fixed by C3b | REPORTED on HEAD only | n3t: 0 x DRT-0255 (wave a2 died there). Proof on HEAD, not on QC; the QC proof kits were blocked by holds until r283 |
| bksel fx1 setup 0 at GRT | REPORTED | -149.77 -> 0.00; FF hold repair -116.5 -> -83.3 at iteration 480, then pass 2 + DRT |
| KV pv k2 generating; hg v25h composed | REPORTED | v25hv G0 PASS, strict bind running |
| DRT-0206 on hold ECO with track-truth | REPORTED, A/B running | 10 kept scalar M7 landing port nets lose pin access in the route-keep session; eco_ab206 is the A/B |

## 2. Levers ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | F2s compose with ring-ff on all bands (incl. svc frozen) + col clock rows, on a tree from main >= c3c59b7dfea | 95 held types + 174 types with a ring >= 512 bits; col 216 rows | DIE-S81-92, S81-RINGS-O, S81-COL-O |
| 2 | all | Rebuild the four trees from main >= eb1e73448bd (tt-keep, RC HEAD/KV, ring-ff guard, pinaccess) | every gate read on HEAD 7, KV 50, QC 120, S81 | TOOLS-CONVERGE-1115 (existing lane), KIT-OPS-5 accept test |
| 3 | S81 | col: tap mean above band, then per-port windows, then the 26 structural endpoints | 216 col types | S81-COL-O, DIE-S81-92 |
| 4 | QC | Adopt S4q9b; prove DRT-0255 on QC; hc RC-aware repair; first current-tree read of the cb / glue family | 34 knee types + ~20 DRT-0255 + 16 hc + 18 cb / glue | DIE-QC-103, QC-HCFE-O, QC-PINACCESS-O, **new lane (cb/glue)** |
| 5 | HEAD | DRV-class RTL replication: hd_host_e/w isl_rp + macro-side register; hd_serdes fan-out + DKREG | hd_host_e, hd_host_w, hd_serdes | HEAD-TYPES-O, HEAD-SERDES-O |
| 6 | HEAD | NF13b FREG rows: adopt on the HEAD tree rebuilt in lever 2 | hd_st_k5, hd_st_turn | HEAD-100 |
| 7 | all | Route-keep ECO: no track-truth or pg_pair_cap obstructions in a wired-seed session | every ECO on a kit with OT_PG_TRACK_TRUTH=1 (QC die-wide, HEAD proof kits) | GENBUG-IMPL |
| 8 | KV | pv ring child cores (k2), hg v25hv, hub ring_place + gen_lint tool bug | 13 pv + 21 hg + 4 hub | KV-PVHG-O, KV-102 |

### Lever 1. S81: compose F2s once, whole die

Evidence.
- Proof: verdict 1.
- F2s try1: pre_ff 988, composed_ff 1,162, lost 82 (all on 10 svc types, all `band_fixed_um` frozen dicts copied by
  `copy.deepcopy`). Non-svc bands kept ff, 1,135 of 1,135 (REPORTED S81-RINGS-O, measured on `cmp_B6gF2s_try1`).
- 95 S81 types are held for the plan event (breakdown).
- The leaf place failures are mostly band-size classes: t36 / t46 / t47 / t72 "band too small", t8 / t7 / t17 preflight.
  The ff reserve (4,220 um2 against 8,105 per 1,104 bits) covers t72 by the composer's own arithmetic (0117 lever 4).
  INFERENCE: t36 / t46 / t47 are the same class; check them on the first F2s kit before giving them rows.

Root cause: one lost compose key. The frozen-band path did not inherit it.

Fix.
1. DIE-S81-92: compose F2s on main >= c3c59b7dfea (r282), with the RINGFF accept on all types and no svc exemption.
   In the same event, fold the three col clock rows from S81-COL-O 02:44: `tap_core_etap` + `tap_core_src` tree,
   `core_pin_lead_ps` ROM 255, and type `tap_max_sinks` 3000.
2. S81-STRIP-O: the 8 ff proof kits are in GRT / CTS / place on epyc8. Rows go only to types whose ff kit still shows
   ft-strip overflow: t34 (ft 38 %) and t62 (ft 51 %) are the expected ones.
3. Open E/W-face proof: only B_t65 on B6gsl-sized rects is proven. F2s with `--band-reserve ring_ff` resizes the rects
   toward that size, so it is close to the B_t65 form. Read t1 or t65 from the first F2s wave before volume.

### Lever 2. Trees: one more rebuild, all four dies

Evidence: MEASURED on epyc10 (verdict 2). The trees affected are QC / HEAD `src_*_pin_e594a73db756`, S81
`src_s81_pin_e4b9ae9f1c1f` and KV `src_kv_pin_fa627e234cf7`. All of them miss tt-keep and the HEAD / KV RC scales. On
the S81 tree, `core_pin_lead` is present (4 occurrences) and `_frozen_band` is absent.
- tt-keep class (REPORTED, measured by FABLE-FIX-HEAD-TYPES 01:33): the GRT-mode repair removed 26 buffers. That
  merged 42 loads (102.6 fF) onto one BUFx6f. In-session WNS was -43.92; after write_db and reload it was -127.85.
  Every die runs `OT_TT_SETUP_REPAIR=both`, so every die can be hit.
- RC: he3 at x1.13 reads -159.58 against -160.14 routed. Unadjusted it reads -10.49.

Fix: TOOLS-CONVERGE builds S81, QC, HEAD and KV from main >= eb1e73448bd. KIT-OPS-5's accept test on one fresh kit per
die adds three checks:
- `grep skip_buffer_removal tt_setup_repair.tcl`;
- `OT_RC_SIGNAL_SCALE` in config.mk equal to the die entry;
- `tt_setup_keep.log` present after GRT.

Until the switch, HEAD and KV gate reads are not decisions.

### Lever 3. S81 col (216 types)

Evidence (REPORTED):
- IMPL proof CTS windows: p50 10 / p90 38 / max 49 ps. Tap means are 415..542, so the upper taps are above the
  380..490 accept band.
- f2s2 pilot: GRT hold repair WNS -186 on u_bn11/e_r0 with the flat 165 window.
- The col wide rings are internal stations, not landing bands. ring-ff does not apply to them, and f2s2 is at GRT 0.

Root cause: the tap insertion delay of the upper taps exceeds the window. A flat 165 ps window turns that into
cross-tap hold.

Fix, in order:
1. Lever 1 rows, so the tap source is the tree and the ROM lead is in place.
2. On the F2s pilot CTS, measure per-port windows with `tap_window_measure.py`. Before adoption, check that the die
   side delivers each port within that window (S81-TAPROWS number).
3. Specs 1-3 of FABLE-FIX-S81-COL-SPECS (go_tag face, sh_free/bank_free, reset copies) in parallel.
4. Pad hold only on what remains after the windows.
5. If tap means stay above 490 on the pilot, split the tap (tap_max_sinks down) before any window change.

### Lever 4. QC (120 unsigned)

Evidence:
- S4q9 had 113 per_bit chains over the 403 um knee in 34 types. S4q9b has 0, worst 399.98 um (REPORTED; the checker is
  the kit's own rule).
- Class A DRT-0255, about 19-20 types: all kits built on wt/qc-s29-tree2, which has the pdn M7 offset 4.128, no
  pg_pair_cap and no tt_setup_repair (REPORTED QC-DRT-1116 01:22). QC switched to the pinned tree at 02:02, with kit
  snapshots off since r281.
- hc2: 494 violators in the 8 xs leaves; GRT RC under-read about x1.46. E1 repair at x1.5 takes -194 to +18 (REPORTED).
- **cb / glue, unread on the current tree.** Autopilot 02:52-03:02 setup triage:
  - cbf_q01 -1,169.16 (S4Q2);
  - cbf_q01_s2 -621.98 (S4Q3C);
  - glue -491.66 (S4Q6D);
  - cbn_q00__cld7bf7197 -157.71.

  All four are on src `qc-event-s28-1111`, with pinreg mean 253-270 against bound 250. No lane has posted a
  current-tree read of this family.

Fix:
1. DIE-QC-103 adopts S4q9b after its bind, LATCHECK and G0.
2. KIT-OPS-5 sets item_env `OT_TT_SETUP_DESIGN=1 OT_TT_SETUP_MARGIN=30` on the 16 hc types (r199). The first wave hc2
   kit is the hc proof.
3. QC-PINACCESS-O: the 4 DRT-0255 proof kits are now launchable (r283). One clean route posts `proof:DRT0255`.
4. **New lane, QC-CBGLUE**: one cbf_q01 and one glue kit on the pinned tree and the S4q6d/S4q9b plan, to CTS + gate.
   Classify the worst 200 paths (pin-register depth against the 250 bound, wire, or logic) before any plan row.

### Lever 5. HEAD DRV-class setup

Evidence:
- he3 routed: TT -160.14 / 386 endpoints, DRC 30, FF hold -74.81. The worst path is the isl_rp QN: BUFx10 (24 loads) ->
  BUFx3 (34 loads, slew 132) -> OA21x2 driving 68.7 fF of routed wire into u_epc in_data[520]. Gate delay is 140 ps
  and wire 273.5 ps; slew at the macro pin is 863 ps (REPORTED FABLE-FIX-HEAD-TYPES 02:17).
- hd_serdes: the pma_rck decoder cone has nets of 21 / 32 / 41 loads. Wave attempt_6 on main read setup_est -261.37 at
  post-CTS triage (MEASURED, autopilot 03:02).

Root cause: high-fan-out select and unbuffered mux-to-macro wires. On real RC they cannot be repaired within one cycle.

Fix (RTL, no cycle where possible):
- he: replicate isl_rp per 64-bit group, and register the mux output next to the macro pins. The slice already pays the
  +1 cycle. The he4 skid form is the vehicle.
- serdes: DNGB 12 / RMRPC 32 fan-out copies (+0 cycles) and DKREG 1 (+1 pma_rck RX; HEAD-100 prices the LATCHECK row).
  Build on the lever-2 tree, so the GRT repair cannot undo the fan-out split.

### Lever 6. HEAD NF13b

NF13b is composed with the 12-row table regenerated by the tool. Its gates are on the old tree, so re-run G0, bind,
cohort and LATCHECK on the lever-2 HEAD tree, then adopt. k5b route plus sign-off is the timing proof.
`pregrt_ff_hold` only if the routed k5 shows the face-register hold class.

### Lever 7. DRT-0206 in route-keep ECO

Evidence (REPORTED, odb-measured by the lane): 10 failing nets on hd_spn and hd_ctl. All are scalar landing ports on
0.080 um M7 pins, and pins, wires, guides and buffers are unchanged by the ECO. Both failing kits carry
OT_PG_TRACK_TRUTH=1, which added 1,359 temporary GRT obstructions (M7 135). The wave hd_spn ECO without track-truth
passed.

INFERENCE: QC die_gen_env sets OT_PG_TRACK_TRUTH=1 die-wide (KIT-OPS-5 02:02), so every QC hold or setup ECO is exposed.

Fix (GENBUG-IMPL, after eco_ab206 confirms):
- in a wired-seed session, add no track-truth or pgcap obstructions;
- assert 0 temporary obstructions before write_db of 5_1_grt.odb.

### Lever 8. KV

- pv: the k2 tap-stable ring plan is generating (REPORTED).
- hg: v25hv G0 PASS, bind running.
- hub_Wo fails "band too small" (f5fa4d600f). The hub ring_place rows are in 7yhr, which is not adopted.
- gen_lint c59ba070b0 (8 items) is a tool bug by KV-102's own r266 read, but it went NEEDS-LANE at 02:38.

Fix: KV-102 adopts 7yhr and lands the gen_lint tool fix. KV-PVHG-O carries k2 and v25hv to READY-ROWS. Rebind both on
the lever-2 KV tree.

## 3. Families nobody is working on (technical)

| family | evidence | proposed owner |
|---|---|---|
| QC cb / cbf / cbn / cbx + glue setup (about 18 types) | setup_est -158..-1,169 at post-CTS triage, old tree only | new lane QC-CBGLUE (lever 4) |
| S81 svc (16 types): staging memory 4 x 160 x 265 FF | decision 23:51 = RTL split to `ot_sram_1r1w_160x265` with SRAM_MACRO=1. The memwr merge (merged) fixes the synth stall, not the 42,400 > 16,384 memory check. No lane posted the RTL split since | new lane S81-SVC-SRAM (or S81-SVC-SYNTH-1115 if live) |
| S81 serdes t13 / t15 DPL error | NEEDS-LANE 2b733f6eb3 at 02:38, S81-SERDES-PHY-1116 did not answer | DIE-S81-92 |
| S81 leaf t36 / t46 / t47 band, t7 / t8 / t17 preflight, t53 GPL, slice_station t25 edge_outline | NEEDS-LANE 02:38-02:39, no answer. Most are expected to clear with ff (lever 1); read on the F2s kits | DIE-S81-92 |
| S81 slice_station t20 DRT-0255 on u_cland_ft0_i (03:14) | old S81 kit tree without C3b / die phase | goes with lever 2 (no rows) |
| KV gen_lint tool bug c59ba070b0 | NEEDS-LANE 02:38 | KV-102 |
| S81 core dsdv_gunit_l1f_bf | no kit-wave row | DIE-S81-92 |

## 4. Stop list (technical dead ends)

1. Any S81 kit from B6gE / F2a / G3b bands without `+ff`. Reusing B6gsl rects. More GRT iterations on those kits.
2. Releasing col on the flat 165 ps window. Adopting per-port windows without the die-side number. Hold padding before
   the windows.
3. Relaunching wave hd_serdes on unchanged RTL (attempt_7 launched 03:04 after -261.37). Reading the in-session
   "after" WNS of a GRT TT repair.
4. Treating HEAD or KV gate reads on the current trees as RC-calibrated. Counting he3 / hw3 / n3t from a gate number.
5. Route-keep hold ECO on kits with OT_PG_TRACK_TRUTH=1 until the lever-7 fix.
6. Raising the QC 403 um knee limit. Releasing fe / sc / su_c / fw / su_l1 on S4q9.
7. Relaunching QC cb / glue kits from the `qc-event-s28-1111` tree or S4Q2 / S4Q3C plans.
8. Hand-editing latency tables (NF13b F1). Regenerate them with the tool.
9. Still valid from earlier reviews:
   - route-keep ECO on cores at -150 or worse;
   - hc2 counted from a gate read;
   - `BANK_PIPE`;
   - KV v20 / v21, PVGEN 2-way, pv on kvgeom6, 7p;
   - releasing pv_v1n on 7yh.

## 5. Not checked

- The 8 S81-STRIP-O ff kits: t34 / t43 are in GRT extra iterations, t28 just started GRT, t72 still in place. No final
  numbers.
- The S81 tree's main sha relation to tt-keep was inferred from file content, not git.
- QC cb / glue on the current tree: no kit exists to read.
- hc2 P0 sign-off, k5b route, he4, sd3 / sd5, bksel fx1 detail route: all in flight.
- eco_ab206 A/B result (lever 7 is INFERENCE until it prints).
