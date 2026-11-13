# S81-FORMS-1 handoff (S81 die-form owner; COORD lane) -- started 2026-11-13 ~11:20 PST

## Scope
- (1) S81 leaf family: macro too close to a pin face (t28 a3, t75 a1 BAD; t73/t29/t34/t44/t53 milder, routing under watch).
- (2) dsdv_slice c1x/c3x: macros u_cap/u_xr near W/S faces + cell count over the 400k/run cap (c1x t3 BAD, c3x t1 BAD, c1x t1 queued).
- COORD scope change (11:3x): the street rule (R-STREET, RULES-STREET-1) and the cap/split rule (R-CAP, RULES-CAP-1) are set in
  ~/coord/lanes/RULEBOOK-1113.md. Apply exactly those rules; no own numbers; no READY before both sections are posted.
- Not mine: serdes/seqhost (HARD-S81-SERDES-1), cross-tap hold (HOLD-TAP-1).

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/s81-forms-1, branch claude/s81-forms-1-1113 off origin/main fbfb4fc6a6 (no commits yet).
- Work dir epyc7 /srv/opentallas-scratch2/claude/s81-forms-1/{w,census.py,why.py,peek.py}.
- Base plan = ready12b-A plan 18c864518844 (events/s81_ready12bA_1112/plan_ready12bA_18c864518844.json.gz) -> w/plan_A.json.

## Findings so far
- Census (w/census_43.json, street 43.2 provisional): 71 of 89 leaf/kv_leaf/dsdv c1x/c3x types have a core < 43.2 um from a face
  with pins in its span. The generator norm is 34.56 um (core_place --gap auto default); a few go to 4.3-21.6 (t54 cl706, t37, t13,
  t17, t21, t58, t7, t45, t44, t75 ln).
- Tool: tools/die_plan/core_place.py --face-clear FACE:UM:REGEX (CORE-PLACE-1) already legalises cores off faces and keeps EQ.
  Trial --no-search at 43.2 on t28/t75: reverted. Blockers: (a) ft station fixed points above ve_s (128 pts at y~392 in t28);
  (b) the W ln column is packed at 6.48 um < auto gap 8.64. Timing (tviol) was not the blocker. Trial with search + --gap 4.32:
  w/try43s (pid see log).
- dsdv cells (kit logs, event 7073a6b4a59): c1x t3 synth 329,380; floorplan nontap 332,424 + tap/endcap 120,238; place repair
  +72,504 buffers; DPL 631,375 = 167,552 fixed + 463,823 movable. c1x t1: synth 317,830, place repair inserted 104,799 + 573,207
  + 119,576 buffers -> DPL 1,066,264 (166,945 fixed, 899,319 movable). c1x t6 a27: +367,937 buffers. c1x t10 a16: +224 buffers,
  254k movable. The excess over the cap is repair buffering on long nets (reach), plus 120k fixed tap cells from the outline area.

## Next
1. Poll RULEBOOK-1113.md for R-STREET and R-CAP; apply exactly.
2. Plan stage: core_place face-clear on the listed types (+ station re-route); private ot-run builds to place for t28/t75/c1x t3;
   view renders; route where possible.
3. READY: event branch (plan files only) + tool branch separately; adopted after the freeze (11-15 04:00).

## Update ~04:2x PST
- FINDING posted 03:42 (on origin): street_rule.outline_rule counts only CORE face pins (and drops type-window pins), so the type
  I/O pin bar is never street demand -> the GEOM-VIS-12 class is invisible to the street tool.
- Method that works (no tool change): street_rule.py legalize with --set band_file=BANDS.json, BANDS = pinface_bands.py output
  ({type: [[face, lo, hi, CLEAR]]} from gen_phys.type_pins spans, merge 43.2, min 16 pins), --set add_regs=1 --set attempts=6.
  Band-only variant (core-core streets neutralised: street_min_um=4.32 pin_pitch_um=0.0001 wall_min_um=4.32), CLEAR 43.2:
  t28 APPLIED 0 growth, 7 moved, +4 station regs, rs p99 5.39->5.00; t75 APPLIED 0 growth, 3 moved, +0 regs, rs 3.43->3.18.
  Full street rule + bands (srbands2): t28 +7.7% H, 27 regs; t75 +4.2% W, 11 regs; c1x t3 0 growth, 3 regs, clean.
  No die re-pack tool exists for grown types -> prefer the band-only form. c3x t1 clean with bands at 0 growth.
- Family run fam43B (all 89 types, band-only, 43.2) on epyc7 w/fam43B.
- Private build route: copy wave spec (intel2 ~/coord/autopilot/kit_wave/s81_<item>_*/aN/spec.json), point plan/work/kit_rtl.bind_out
  at the candidate, run kit_wave.py run-item with a private AP_DIR. Station regs added => needs its own strict bind
  (pattern events/s81_ready12bA_1112/run_r12bA_dst.sh; seed OUT from kit-ops-1/s81_r12bA/out_main_7073a6b4a5_b) and
  street_rule.py sidecar for the landed sidecar.
- CLEAR is provisional (43.2) until R-STREET posts; R-CAP pending too.

## 2026-11-13 04:25 update
- PLAN for R-CAP-3 on the dsdv family is posted on origin (lanes/COORD-REVIEW-QUEUE.md). Kit projections: c1x t1 436k, t3 457k, t6 468k, t10 453k, lepe_mu 458k, lepe_nh_mus 455k, lepw_mus 460k, iq t1 514k.
- Cut design: epyc7 /srv/opentallas-scratch2/claude/s81-forms-1/leafgraph.py; c1x t3 group graph in cut/c1x_t3_graph.json. Candidate 2-way cut: xf cluster (eng_finish x4, norm_finish, xstop, soft xf) | rest (xg, xr, cap, eg, flt, landings, stations). Cut links: xstop<->xg 346 bits (+ check cfg/fault).
- Per-leaf cells: hierarchical yosys stat on epyc8 hstat_c1x_t3/ (ot-run; intel2 ~/tmp/s81f_hstat.log).
- Street family: fam43B (epyc7 pid 1653335) still in the die-wide post phase. R-STREET not posted yet.

## 2026-11-13 04:46 update
- fam43B done (band-only, provisional 43.2 um, no growth, die area +0.0%): 70/89 types clean. All named BAD/mild types are clean: leaf t28 (7 moved, rs p99 5.39->5.00), t75, t73, t29, t34, t44, t53, and dsdv c1x t1/t3/t4/t6-t10 and c3x t1. 19 reverted: route_supply worse (13: leaf t5/t12/t15/t30/t41/t72, kv_leaf t3, c1x t5, t54/t25/t40 clones), clock-tap radius (leaf t1/t8/t14), reset collector root moved (t37, t25 clone), band short (kv_leaf t5). Those need growth + regs (srbands2 form). Plan: epyc7 .../w/fam43B/plan.json, rows.tsv.
- R-STREET is still a header only in RULEBOOK-1113 (checked 04:46). Not applied, no READY.
- hstat rerun (yosys synth has no -noflatten flag; it failed after 28 min): ot-run on epyc8, log intel2 ~/tmp/s81f_hstat.log.
- Split mechanism: physical/die_plan/s81/bind/asbuilt_map_s81.json parts (longest prefix). Add e.g. u_s_<id>.u_lp.u_xf -> s_<id>_X plus a new plan partition and type.

## 2026-11-13 05:23 update (R-CAP-3 dsdv, design state)
- hstat c1x t3 (epyc8 /srv/opentallas-scratch2/claude/s81-forms-1/hstat_c1x_t3/hstat.txt, generic cells): total 326,144. u_xg = ot_s81sl_xgt_xo: u_s ot_s81sl_xs4 172,755 + 37 macros (24 SRAM 128x256, 7 ROM 4096x72, 6 SRAM 128x64); u_r ot_s81sl_rstopt_xo 51,390. Rest about 100k.
- PLAN-REV posted (origin): harden u_xg.u_s xs4 as ONE core (projection about 207k), parent C about 253k; iq/kv512 swap u_xg master xg->xgt_xo (+1 edge x path).
- Template: commit 81afc6c5dd "S81 xfin event" (delta_xfin_split_1104.py, ref_tile spec.json, cores/legacy recipes_*.json, asbuilt dissolve, provisional libs from the LEF contract). Core kit: physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module M --recipes R (pin contract = plan hard_core outline + pins_file).
- History: ref_tile/s81sl_xgtxo (whole xgt_xo 734.4x777.6, 11,914 pins, 10-21) never signed. xs4 alone has 4,365 port bits.
- SITE SCAN (epyc7 /srv/opentallas-scratch2/claude/s81-forms-1/xssite.py, margin 34.56, gap 8.64): with the current core positions NO C type except c1x t1 has a free site for any xs4 outline from 432x950 to 734x562. The xf row (941.76x190.08), cap (336.96x414.72), xr and eg block it. Next step: a per-type hand re-layout of the C rows (move/rotate cores, shapes frozen) with the xs4 core, which also applies the street bands. Area is fine (about 0.73 of 1.59 mm2 inner).
- Leaf street: R-STREET still header-only at 2026-11-13 05:23. fam43B result above.

## 2026-11-13 10:32 update (leaf template event)
- Work dir epyc7 /srv/opentallas-scratch2/claude/s81-forms-1. Tools: rs8d/ = R-STREET final 8dd3028a50 (street_rule.py patched: json default for numpy bool; .orig kept), rsd73/ = orient_realize 4a438c2be2.
- Base: plan_A 18c864518844 -> orient_realize -> w/plan_Ao.json f1add586784c.
- Legalize runs: A2 (plan outside --repo) reverted 71/79 on 'collector root moved' = ARTIFACT (reset_resel could not resolve pin tables, 0 trees republished). A3 (reset_resel=0): 46 applied, 22 reticle-reverted (die +181x+553 um, W headroom 10.9), 6 route_supply reverted; reset_contract post-hoc passes 44/46 (t25__cl431c660f, t66 fail). A4 = rsleafA4.sh (plan INSIDE repo, full contract) running, out w/rsleafoA4.
- Post pipeline: leaf_post.sh TAG LEGALIZED_PLAN BINS [CAP] (orient -> core_tap_fix -> tapcap 1500 -> tapknobs (pregrt_ff_hold all leaf, tap_pitch 200 on kv_leaf t1-5 + leaf t29) -> resetfix in w/vt -> checks -> run_bind.sh G0/strict bind/LATCHECK). NEVER cp onto a hard-linked repo file; rm first (rsleafA4 does).
- Leaf hold family (COORD 10:xx/11:xx): t6 = core-tap reach (clk_c24 181 um) + port-out boundary; kv_leaf t5 = pocket tap overload (clk_t5 11,297). Posted STATE.
- Next: A4 result -> leaf_post -> private place proofs -> READY (event branch off origin main, plan + street_rule_bins only; tools core_tap_fix/tapcap/tapknobs on separate branch).

## CODEX notes 2026-11-13 13:49 PST
- Took over existing E7 forms worktree/run dirs. A5 chain terminal: plan8aaa80ba73cf, BIND_RC0, LATCHECK873/873 unchanged; SIDECAR_RC1 makes candidate incomplete (not READY).
- Cause: source sidecar67 leaf collector trees differ from source plan geometry (coordinates and one self-type label), not topology/depth; old run_bind also retains asbuilt.base at original source so the candidate sidecar was ignored.
- Private repair helpers E7 s81-forms-1/sync_baseline_sidecar_codex.py and run_bind_codex.sh align only geometry after topology/depth equality, fail on sync error, and rebase asbuilt.base to private tree. A5 candidate sidecar now syncs with refused_stale_sidecar0. No production src/sidecar edited, no adoption.
- Existing DIE-S81-89 legy CPU job retained (PID4040400 E7); fold combined leaf/frame event before next bind; no duplicate whole bind launched.

## CODEX notes 2026-11-13 14:14 PST
- Concrete hand t28 form in E7 w/leaf_template_codex/plan_grid4_cycles.json is0growth/0hardstreet, but NOT a realizable form yet: proposed74 new station rows are receipt-only in nativeflat RTL (50core_unmapped,24recognizedonlycounted). Sum157 proposed edge-cycles must NOT be claimed actual latency. Exactcensus realization_grid4.json + report_grid4_cycles.json.
- Root shared lane owns actual station lowering kit_istations/bind fix + minimal exact/mutant proof. Leaf helper owns plan/t75 variant. No P&R or falseREADY; original failed grid/cut analyses retained.

## CODEX leaf hand template 2026-11-13 14:25 PST (private; no P&R)
- Existing E7 workdir w/leaf_template_codex: hand t28 grid4 fits1442.88x1226.88 at0growth,0overlaps,0fixedpointsunder, all27cores seed-legal (no automaticlegalization). R-STREET zerohard,16transitWARN; projectedcutH0.779->0.78,V0.585->0.50. Image t28_grid4_cycles.png viewed; existingwt/results/geom_review/leaf_grid4_codex_1113.json verdictBLOCKED_RTL_REALIZATION.
- plan_grid4_bundle.json is current private t28 candidate. Four reverse-direction VN_b->leafdn genericrows corrected to coherent face->VN_b branches at unchanged maxbusdepth3. No actualcycleclaim.
- Station-reality failure measured on actualboundmodule b/la5/out/rtl/s81p_ot_s81sl_leaf__t28.sv: kit_istations.core_stations replay leavesRTLhashUNCHANGED. Newgeneric74rows:50unmapped/4vni/10ve/10ver; nativeHI4vs2,HO4vs2,VER2vs0,VE2vs0,VNI3vs1. realization_replay.json and realization_grid4.json retain exactreceipts. Sharedtoolowner owns emitter fix andrestaging stage_lfcs_netlist+freshbind+lockstep/mutant. Planned157SUMedgecycles are not actual latency.
- Rejected hand proposals retained: initial4x4LN square cutH1.645(t28); t75grid5 mainE cutH1.58. t75grid6 keepsmainleft, cutH0.56/V0.56 vs0.584/0.655, but3fixedgeometryconflicts(VE_s southFTstation overlap,VSW northlandingband,LN9clocktap). Grid7 liftsVE_s8.64,movesLN9tofreeWbay, proposes34.56Ygrowth tofitVSW below northlandingband; modelonly via ot-run E7 unitoth-ubuntu-1074460-1794608692/clientI2PID298904, log~/codex-s81-log/leaf_t75_grid7.log. No productionplan/wave edit.
- 14:38 PST CODEX t75 room-first template complete physically: plan_t75_packed_bundle.json,1442.88x1261.44 (+34.56Y),27legal/0seedrepairs/0overlap/fixedpointunder. R-STREET0hard,1sparseoutlineWARN+2transitWARN. DirectCS229.044um. CutH0.555->0.483,V0.655->0.479; overflowH4.94M->3.80M,V3.15M->2.98M. CanonicalVQ10busbranches keepwholebundledepth2 unchanged;72newcorelinks+56existingexpandedchains UNREALIZED untilsharedLFCSlowering/freshbind/lockstep+mutant. t75_packed.png viewed, wt/results/geom_review/leaf_t75_packed_codex_1113.json BLOCKED_RTL_REALIZATION_AND_DIE_REFLOOR. No188actualcyclesclaim.
- Zero-growth leaf family room-first geometryconstructor running (NOT P&R): E7w/leaf_template_codex/pack_family.sh, clientI2PID486883, log~/codex-s81-log/leaf_family_pack.log. Reuses actualhardcore shapes,43.2gaps,FT/tap/bandkeepouts; onlyexistingstationchainexpansions (no newgenericdirecthop rows). Progress family_pack_rows.json/family_pack.log, terminal FAMILY_DONE thenstreet_family_packed_private.json. Treatoutputs PRIVATEgeometry untilRTL/bind/clock/reach/model gates; noPORchange.
