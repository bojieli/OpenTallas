# FABLE-CLOSURE-STRATEGY 2026-11-16 07:25 PST (FABLE-CLOSURE-0943): the trees are fixed; what blocks closure now is three structural classes no build can repair

Read-only review by FABLE-CLOSURE-0943 (Fable). Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: FABLE-CLOSURE-STRATEGY 03:43, FABLE-PD-S81-F2s, handoffs FABLE-FIX-{S81-CONG, S81-SVC, S81-COLTAP, S81-SERDES,
QC-KNEE-HC, QC-HCFE, KV-PVHUB, HEAD-TYPES}, FABLE-DIE-KV, the Opus successor handoffs (*-O), DIE-S81-92, the four
tree_switch markers, queue lines 03:40-07:24, `failure_breakdown.py` 07:13.
MEASURED = read by me 07:10-07:25 (plan / log / tree files; no odb opened, no STA run). REPORTED = lane post. INFERENCE is marked.

Signed types 03:14 -> 07:13: S81 41 -> 41 of 394, HEAD 19 -> 20 of 26 (hd_spn), QC 7 -> 7 of 127, KV 6 -> 6 of 56.
No class shrank in count in these 4 h. The causes moved; they are listed below.

## 0. Verdict

1. **The tree lever landed and I verified it.** On epyc10 all four v2 trees `kw45/src_{s81,head,qc,kv}_pin_eb1e73448bd0`
   carry `skip_buffer_removal` + `OT_TT_SETUP_MEASURE` (4 hits each), `rc_signal_scales.json` = s81 1.00 / qwen_compute
   1.25 / s81_head 1.13 / qwen_kvsys 1.10, and `_frozen_band` in `clock_landing_plan.py`. Gate reads on v2 kits are
   decisions again. No v2 kit has reached sign-off yet.
2. **Three structural classes now hold most unsigned types, and none is a repair or ECO item:**
   - one-cycle sideband nets that cross a type (raw reset -> FSTART, fault / ready, reset copies): QC cb / glue 17-19
     types, HEAD hd_lep0N, S81 col 216 types (residue class);
   - the S81 col tile layout (far half drives the loop): 216 types;
   - scalar 80-nm M7 pins against the die-phase M7 PG stripes (DRT-0206 in ECO, Rect Only, EOL keep-out at macro pin
     edges): HEAD 4 types today, every v2 kit that needs a hold ECO tomorrow.
3. **S81 non-col is one adoption away** (F2sv bound: BIND 0, LATCHECK 873/873, G0 new 0). No ring-ff kit has been
   detail-routed yet; read A_t65 and c_t34 routes first.

## 1. The 0343 levers: landed or not

| # | lever | landed? | numbers |
|---|---|---|---|
| 1 | S81 F2s compose with ring-ff on all bands + col rows | **PARTLY**: composed and bound, not adopted | B6gF2sv 4c163bdc1625: 0 ring bands without ff (82 svc bands stamped). B6gF2s2 a623deec2d38: windows 40 / 10 on 10,199 ports + 3 clock rows on 216 col. Both BIND 0, LATCHECK 873/873, G0 67 vs 68. sdc_lint + replication running. S81 stays 41 signed, 0 launches in ~7 h |
| 2 | Rebuild four trees from main >= eb1e73448bd | **YES** (MEASURED, verdict 1) | S81 on epyc10 / 9 / 8 / intel1; HEAD (d1, NF13a data in tree), QC, KV on epyc10 only. Launch refusals 06:51 "17,138 missing" on HEAD / KV / QC are a check run on a host without the tree |
| 3 | S81 col: tap means, windows, 26 endpoints | **Root cause found, fix not in a tree** | upper taps 520 / 542 = early core tap priced insertion - 450 (15.39 instead of 215.39). Fix f2091534ae0 (core_tap_lead_ps 200 + tap_balance top-up) approved r300; v2 tree lacks it (MEASURED: `schema.core_tap_early_ps` still `max(0, ins - common(t))`). New: go_tag / ef = tile layout fault (lever B). 0 col types built |
| 4 | QC: adopt S4q9b, DRT-0255 proof, hc repair, cb / glue read | **Mostly NO** | S4q9b was never bound (TOOLS-SKEW refusal + BIND_RC 17 on the v1 tree). S4q9c (= 9b + 3 PHY outline rows) chain started 06:55 on v2. hc2 P0 routed: DRC 0, setup -32.10 / 7 (was -178.75 / 494) = setup proof only; hold -36.66 / 289 on the old guard. DRT-0255: coll_n never routed on a new tree. cb / glue read done: reach, not tree |
| 5 | HEAD DRV-class RTL | **PARTLY** | he4 skid: -160.14 -> -66.43, DRC 30, ECO no gain (-66.93). hw3: -80.84, DRC 0. serdes fanout + DKREG approved r288; sd6 post-CTS -146.79 -> -26.55 (placement RC) |
| 6 | HEAD NF13b on the v2 tree | **NO** | F1 verdict PASS, k5b signed as a non-countable proof. The HEAD v2 marker carries the NF13a plan; NF13b is not adopted |
| 7 | Route-keep ECO without track-truth obstructions | **REFUTED** | eco_ab206 without track truth: DRT-0255 on net66547 in iteration 1 (101,563 violations at start, same as the failing run). The obstructions must stay; DRT-0206 is still open |
| 8 | KV: 7yhr, k2, v25hv, gen_lint | **PARTLY** | 7yhr passed every gate 03:59 on the c1 tree but was never posted; re-gate on v2 running (FABLE-FIX-KV-PVHUB). v25hv READY-ROWS (LATCHECK 2404/2404). k2n gated, k2r pending. gen_lint was tree skew, fixed in v2. KV q2 clock core signed (+225 / +10) |

## 2. Levers now, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| A | S81 | Adopt F2sv; next delta = CONG rows + svc form-A sites + bk_sel RTL in ONE event | 266 non-col (incl 16 svc, 6 serdes, 6 strip leaf) | DIE-S81-92; FABLE-FIX-S81-CONG / -SVC / -SERDES |
| B | S81 | col F2s3: tool commits in the S81 tree, tile rows, r2 CTS read BEFORE the bind is adopted; r0 families get IFN = 0 in parallel | 216 col | FABLE-FIX-S81-COLTAP, S81-COL-O |
| C | QC, HEAD, S81 | One-cycle sideband reach as one class, one audit per die | QC 17-19 cb / glue, HEAD hd_lep0N, S81 col reset copies | QC-CBGLUE-1116 + FABLE-FIX-QC-KNEE-HC, FABLE-DIE-HEAD, FABLE-DIE-S81 |
| D | QC | S4q9c adopt; hc item_env on 18 hc keys; coll_n one v2 attempt | 34 knee + su_l0 + 3 PHY + 2 cbn_q00; 18 hc; ~20 DRT-0255 | FABLE-FIX-QC-KNEE-HC |
| E | all | M7 scalar pin form against die-phase stripes; hold fixed before route so no ECO is needed | HEAD hd_ctl, hd_st_n3_turn, hd_spn_end, hd_host_e now; every v2 kit with a hold ECO | GENBUG-IMPL; HEAD-TYPES-O (he6 proof) |
| F | HEAD | hd_serdes: sd6 GRT read decides sites vs env; host_w / host_e by repair_design, not ECO | hd_serdes, hd_host_e, hd_host_w | FABLE-FIX-HEAD-TIMING, HEAD-SERDES-O, HEAD-TYPES-O |
| G | KV | 7yhr + v25hv + k2r as one event on v2; first die run on 7yhr | 13 pv + 21 hg + 4 hub | FABLE-FIX-KV-PVHUB, KV-PVHG-O, FABLE-DIE-KV |
| H | S81 | Strip congestion: count NDR restarts; rows for t62 / t28 / t75 / t8; re-check rows on F2sv geometry | 6 leaf types | FABLE-FIX-S81-CONG |

### Lever A. S81 non-col: adopt F2sv, then one delta

Evidence.
- F2sv gates as in the table (REPORTED DIE-S81-92 07:3x). Ring proof: A_t68 / B_t65 / A_t65 GRT 0 after CTS.
- serdes t13 DPL-0033: 39,612 ring cells FIRM (`ring_place all`), 233 cells never legalise. F2sv has ff on all 11 serdes
  types with bands 38.9 um wide (was 75.6).
- svc: three causes. (a) memory closure refused the B6 bound: ref_1116 approved r298, 16 / 16 kit-rtl APPLIED, +0 cycles.
  (b) ff on svc bands: closed in F2sv (MEASURED by the lane: 0 without). (c) 31 form-A macros with no site: plan file
  B6gF2sv_formA 626de2b41910, 31 / 31 placed on 16 / 16, 0 overlaps, no outline growth.
- bk_sel__t2: the bind reads a frozen `source_modules/portfix178/dsdv_idx_l20s.sv` with the old `dsdv_idx_tx_n32`;
  drop-in file ready (S81-BKSEL-O 06:57).

Root cause of the stall: one lost compose key (fixed), then four independent row sets waiting for separate events.

Fix.
1. DIE-S81-92 adopts F2sv now. svc stays on its typed hold until the two pilots pass.
2. One next delta, F2sv1: t34 + t47 corridor rows, the 496 svc contents rows, the bk_sel source file. Contents and
   ft-slot rows do not change the bound RTL except bk_sel, so one rebind.
3. Read before volume matters:
   - first detail route of a ring-ff kit (A_t65 on epyc9, c_t34 on epyc8): DRC count at the ff bands. Flops sit on the
     pin slots; pin access under 1,104-bit bands is unproven past GRT.
   - svc_hi t3 / svc_lo t7 floorplan: 76 / 97 macros placed, then GRT overflow in the 10.8-um gaps between the
     26 x 32x128 macros (INFERENCE: the gap is the only escape for their pins).

### Lever B. S81 col: F2s3, with the proof before the bind

Evidence (REPORTED by FABLE-FIX-S81-COLTAP, measured on r2 CTS).
- Element core pins arrive 520 / 542 against declared 465.39 with main tools; 460 / 468 on the F2r tree.
- Sequencers s11 / s14 sit 150 ps early (243 of 394 ps padded; tap_balance skips `clk_c*`).
- go_tag + ef loop: left tiles -345 (s -> u_w pin 405 um), right tiles +173 / +96 (53 um).
- Window scan on the same DB: 165 flat 4,928 endpoints below -42; 40 / 10 gives 14; the residue is go_tag / ef / reset copies.
- pgh on col_h9_r0_p6 at the 165 window: pre-GRT hold repair added 31,543 cells of 246,440, setup stayed -348.65, run exit 2.

Root cause: the far half drives the feedback, and the early core tap leaves no wire run to trim.

Fix.
1. S81 tree v3 = v2 + r298 svcmem paths + f2091534ae0. No col kit from a tree without it.
2. S81-COL-O runs the r2 evidence pilot to CTS with the overlay tools and rows_F2s3 NOW. Accept: core pins within
   20 ps, go_tag and ef >= 0. The 372 swaps and the +100 sequencer lead rest on one right tile of one type
   (INFERENCE by the lane). DIE-S81-92 may compose and bind F2s3 in parallel but adopts after this read.
3. The 84 r0 / h10_r1 types have a CTS estimate of +23..+63 before routed RC. That margin is not enough. Start the
   IFN = 0 halves (Spec 3) as a parallel form now, not as a fallback.
4. Check that a half swap moves no bs / bn pin by more than its station hop budget: re-run the relay station
   check (1,176 stations) and LATCHECK on F2s3, not only G0.
5. FF hold is read on a 40 / 10 kit only.

### Lever C. One-cycle sideband reach, three dies

Evidence.
- QC glue (GRT, 658 endpoints below -42): raw reset -> FSTART face flop 32 endpoints, -492, about 1,670 um, 23 buffers,
  no logic. cbf_q01 -1,916 and cbf_q01_s2 -3,020 at CTS. cal_fault -> cal_t 170 endpoints -436. cbx_q10 station select:
  one 78 fF net, 1.2 ns of wire.
- HEAD hd_lep0N: coll_i0 fault port -> coll_o1 fault_o, arrival 5,411 against 1,186 = -4,224.98; three BUFx16f stages of
  842-888 ps. Its hold repair ran 7 h at iteration 0.
- S81 col reset copies u_d7_6_Y: 780-816 um in one cycle, -100 at CTS, -151 routed, 74 endpoints.
- KV closed this class on 11-10 with `clock.landing_raw_branches`.

Root cause: the reach scripts cover data lanes and the clock. Sideband flop-to-flop nets with no logic (raw reset,
start, fault, ready, select) are not in any reach table, so each die finds them at CTS.

Fix.
1. QC: branch 5e8855d43fe is READY (raw branches: 2,330 um -> max hop 306, 0 cycles; xcst_rep and cal_fault RTL).
   FABLE-FIX-QC-KNEE-HC composes S4q9d = S4q9c + rawbr rows now, in parallel with the 9c gates, so it binds the
   moment 9c passes.
2. HEAD: FABLE-DIE-HEAD puts fault / ready relay registers for hd_lep0N coll_o1 / o2 in the NF13b event (about 5.4 ns
   of wire: 6-7 stations; cycles pre-approved), and lists every other dn -> up fault / ready pair.
3. S81: FABLE-DIE-S81 takes Spec 1 (two-level reset copy tree, coarse grid 600 um) into F2s3.
4. Each FABLE-DIE lane runs one audit on its bound RTL + plan: every flop-to-flop net with <= 2 logic levels whose
   pin-to-pin Manhattan length exceeds 350 um. Post the list before the next event (new lane not needed).

### Lever D. QC event and hc

Evidence: knee checker on S4q9c 988 chains FAIL 0; hc2 P0 as in the table; one hc2 type signed 05:14; coll_n six times
the same net25397 and box (62.70, 653.22), inside SRAM g_bank[2] under the M4 macro PG grid, pin access clean.

Fix.
1. S4q9c adopt criteria as in the lane handoff (BQ bind 0, LATCHECK 1921/1921, hcparam 0, G0 = 2 inherited rows).
2. hc: `OT_TT_SETUP_DESIGN=1 OT_TT_SETUP_MARGIN=30` on the 18 hc keys. The hold proof is still missing: check that the
   pre-GRT non-port hold guard (qc-src-close r271(b)) is in the v2 tree before counting on hc or fe hold.
3. coll_n: one attempt on v2. If net25397 fails again, A/B the `core_pg_M4` connect density over the SRAM edge; no
   further relaunch.

### Lever E. M7 scalar pins against die-phase stripes

Evidence.
- DRT-0206: 10 kept scalar landing-port nets on 0.080-um M7 pins (hd_spn, hd_ctl) lose access in the route-keep ECO
  with track truth (637 / 1,359 temporary obstructions). Without them the ECO dies on DRT-0255.
- Rect Only M7: 3 markers each on hd_st_n3_turn and hd_spn_end, all on interior `rst_start_raw_*` pins.
- he4: 26 Lef58EolKeepOut + 3 spacing, all where die-phase M7 stripes end 0.104 um below the u_epc M7 pin edge.
- All four v2 markers set `OT_PG_TRACK_TRUTH=1` and `OT_PG_DIE_PHASE=1` (MEASURED), so this now applies to every die.

Root cause (INFERENCE, one cause for three symptoms): min-width M7 pins sit inside the M7 stripe field at 8.448 phase,
and the pin has one legal approach.

Fix.
1. gen io: scalar landing ports and `rst_start_raw_*` become M8 pins landed from above (the bus ports already are).
   HEAD row in NF13b; same row form for QC / KV / S81 scalar ports.
2. pdn: stop core M7 stripes 1.08 um short of any macro edge that carries M7 pins (he6 is the proof; if DRC 0, make it
   a gen_phys rule, not a per-type halo).
3. Use `pregrt_ff_hold` on every type whose first route needed a hold ECO, so the keep-route ECO is not on the path.
4. GENBUG-IMPL: in the ECO session keep the obstructions and cut them only inside the bbox of kept M7 port pins.

### Lever F. HEAD timing

Evidence: sd5 (wrong env: density 0.5, M7 cap) 414 of 474 violators start at u_chn, outputs on the top edge 14 um under
the VDDPHY floor, 350-520 um to the loads. sd6 (wave env) post-CTS -26.55. hw3 -80.84 with a BUFx2 on 64 loads,
slew 314. he4 worst path = u_epc in_ready (582 ps clk->out) into the skid enable.

Fix.
1. hd_serdes: the pin geometry is real, the -198.9 is not (sd5 env). Decide on sd6's GRT-stage TT on the reloaded
   DB at RC x1.13: >= -42 keeps the sites; below, sd7 (u_chn R180, u_dmem MY, u_cmem move) goes to HEAD-100. Build sd7 in
   parallel. Before posting the rows, check the M7 pin lattice of u_chn / u_dmem in the new orientation (the t51 case
   was 20 nm off lattice).
2. hd_host_w: the hc recipe (repair_design at TT + margin 30) on the GRT DB. Two ECO loops gave nothing.
3. hd_host_e: he5 / he6 are the right forms. If he5 misses, register `in_ready` at the macro (the slice already pays
   the cycle).

### Lever G. KV

Fix: adopt 7yhr on the v2 event tree when the gate ends; v25hv and k2r compose on it as one event (KV-HG1) with
f79d061f1f3 in the tree. FABLE-DIE-KV's b7 is the first die GRT / STA on 7yhr: read it before the hub rows.
pv types stay off kvgeom6 (30 HCPARAM errors: join RESET_PIN die 1 against hardened 0).

### Lever H. S81 strip congestion

Evidence: b_t34 plateaus at 63 / 48 / 67 over four GRT-0273 restarts; c_t34 with ft5 on a straight band x 486..552
ends 0 with no restart. c_t47 ends 0 in 772 s. t62 53k, t28 128k, t75 83.5k (21 NDR lines), t8 71k.

Fix.
1. Judge convergence by the final line and the count of `Disabled NDR` lines. Re-read t43 ("7 at it25") this way.
2. A kit that reaches 0 only after NDR was disabled has clock nets without NDR: read its clock skew at sign-off.
3. The rows were built on fx0 (B6gE rects + ff). Re-run corr2.py collision checks against the F2sv band rects before
   the fold.

## 3. Lanes whose approach looks wrong

| lane | issue | change |
|---|---|---|
| FABLE-FIX-S81-SERDES | form A rebuilds the G3b `ring_place all` kit with the preflight disabled to read a failure that F2sv removes | keep form B only; A only if B fails DPL |
| HEAD-TYPES-O | route-keep ECO loops on he3 (-116.51), he4 (-66.93), hw3 | stop the loops; structure (he5 / he6) and repair_design |
| FABLE-FIX-HEAD-TIMING | site rows derived from the mis-configured sd5 | gate the rows on the sd6 GRT read |
| FABLE-FIX-S81-COLTAP | 372 swaps on 216 types from one tile; r0 fallback serial | r2 CTS read before adopt; IFN = 0 in parallel |
| QC-CBGLUE-1116 / KNEE-HC | raw-branch delta queued as a later event | compose S4q9d now |
| S81-STRIP-O | it15 used as convergence | NDR-restart rule |
| S81-SEAM-RST-1115 | pgh hold repair on a 165-window col kit | re-run only on a 40 / 10 kit |
| KV-PVGEN | 7p_d4 (57,452-65,644 pad flops per pv type) on kvgeom6 | superseded by k2r on 7yhr |

## 4. Stop list

1. Any S81 col kit from F2s2 or from a tree without f2091534ae0 (216 builds would land core pins at 520 / 542).
2. Any S81 kit on G3b / B6gE bands; serdes kits with `ring_place all`.
3. Hold repair or hold padding judged on a flat 165 ps window.
4. Dropping track-truth or pg_pair_cap obstructions in an ECO session (brings DRT-0255 back).
5. Route-keep ECO as the closure step for a setup miss below -60, or for DRC at M7 macro pin edges.
6. Relaunching hd_lep0N unchanged; relaunching coll_n more than once on v2; any QC cb / glue kit before the raw
   branches are in the plan.
7. Reading u_chn numbers from sd5. Counting hd_serdes from a post-CTS placement-RC number.
8. Reading it5 / it10 / it15 of one GRT round as convergence.
9. Any gate read from a v1 tree (e594a73db756, c1, qc-s29-tree2, kw43 wave src c327).
10. Still valid: raising the QC 403 um knee; hand-edited latency tables; `BANK_PIPE`; KV v20 / v21, PVGEN 2-way,
    pv on kvgeom6, 7p; GENBUG g_macro160 for svc.

## 5. Not checked

- A_t65 and c_t34 detail routes, sd6 GRT, he5 / he6, S4q9c BQ bind, 7yhr v2 gate, FABLE-DIE-KV b7: all in flight.
- FABLE-DIE-S81, FABLE-DIE-QC and FABLE-FIX-QC-CBGLUE have no post or handoff yet; FABLE-DIE-HEAD and FABLE-DIE-KV only a start line.
- Whether the r271(b) hold guard is in the QC v2 tree.
- v2 trees on hosts other than epyc10 (I read epyc10 only).
- The common-root claim in lever E is INFERENCE from three symptom sets; he6 and the first M8 scalar pin kit test it.
