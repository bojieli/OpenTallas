# S81-HEAD lane (claude/s81-head-1024, worktree localhost:~/wt/s81-head)
Scope: S81.HEAD head die top-down (uarch sizing -> die_plan G0/G0C -> die_io vs layer die), LINK5/HOST check of the
S81 layer-die plan. Host share intel2 32 thr: not used (all work is seconds-scale analytics; no P&R launched).

## Where it stood (task 1)
- SPEC v1 results/arch/s81_head_1021/SPEC.md (10-21): 253 tiles (ot_s81hd_tile = bundle 5 elem / 10 ROM4096), spo/spr
  spine, ctl, lep (= stage s_0N lep), 13 lanes, 17 SerDes (incl. 5 draft fan-out), no HBM.
- Bottom-up die chain H1..H11 (tools/s81_dv/head72 on claude/s81c-die2-h11r4-1022, never merged). Last evidence
  (old intel2 nvme /mnt/old-nvme0/claude/stw-s81-head-h10/h10bm): BIND/CASE/GEN/GRT done 10-22 06:12, IR PASS
  8.34 mV, STA TT setup WNS -11,022.8 ps / TNS -27.2 us, hold WNS -22,207.7 ps, die clock check "NO COMMON ROOT"
  on station pairs => H10 FAIL. H11 r4 prep only (glue R5-R8 kits), not run.
- CLOSED leaves: s81hd_spo_m, s81hd_spr_m4/f4, 7 lane sub-children s81hd_lsc_*, dshead elemA/elemB at SS.
  s81hd_tile r5..r7k kits never closed (r6 crashed RSZ-3006; r7kg/kh kits only).
- LINK5 / HOST / SerDes: rack plan in docs/RELEASE_RACK.md 2.1; lanes/S81-LINK5.md lost with rtx-pro. SerDes column
  lp8b CLOSED TT +159.84 / FF +6.47 (SS sensitivity -60.83); ot_pdie_serdes / ot_pdie_ucie parents open.

## Results (task 2, commit cc7b6206fc)
- uarch: tools/s81_head_die_model.py (`uarch_model.py --s81-head-die` -> results/uarch/s81_head_die.json). Tile =
  4 elemA + 1 elemB CLOSED views as hard cores, 691.2 x 1036.8 um, ~1.07M cells; 264 slots (253 active, 11 dark);
  die 21,120 MAC/cycle, 45.2 kB/cycle ROM; head path 9,056 cycles a position vs calendar window 10,357;
  1 TP4 group = <= 35% busy at saturated AR / 21.5% MTP.
- die plan: physical/die_plan/s81_head (gen_plan.py from the model): 17.52 x 17.56 mm = 307.6 mm2; 326 partitions /
  16 types, 425 ports, 325 lanes. G0 PASS 0 err; G0C (--completeness) PASS 0 err, 4 warn (core_faces unchecked
  for tile cores, r8 no as-built groups, die.reach_um note, census none = new die); 16/16 types G3-eligible.
- die_io: 12 SerDes windows (= layer-die slot / PHY / 150-um bumps), host:true on HOST0/HOST1.
- cross-die (tools/die_plan/xdie_io.py, new): head die 0 errors (head_hop S-H 4, H-H 8, token_return H-S 4,
  tp_mesh H-H 18, host 12). Layer die FAIL 130 (copy-A/B pairs + host flag) -> reported in lanes/S81.md.
## Merged: main 84bbf08c9f (13 files, 0 deletions)
## Task 3: LINK5 present on the layer die (10 SerDes, all bound); gaps -> lanes/S81.md "Gaps reported by S81-HEAD".
## Known limits (honest)
- tile cells for elemA = elemB cells x area ratio (ASSUMED); ctl / mesh / host cells ASSUMED; elements' CLOSED view
  is ot_dsrom_head_elem CUT 0x1ff, S81 tile RTL uses ot_s81hd_elem CUT 0x17b (status rework: equivalence or re-close).
- spine-node internal stations declared but not G0C-checked (no content boxes); tile core_faces unchecked (WARN).
- Not run: G1 GEOM review, G2 probes, any P&R.
## 10-24 continuation (branch claude/s81-head-1024 @990f0c548c)
- OWNER 2026-10-24 applied: head dies 12 -> 4 (one TP4 group), NO HBM on head dies. s81_stage_map_input.json head
  {dies 4, hbm_stacks_per_die 0, grade spec}; tools/release_rack_design.py rerun + release_rack_figures.py:
  S81 1,160 dies / 1,156 HBM3E / 2,936 circuits (tp_mesh 1,740, head_hop 4, host 4) / 73 trays (last tray 8 dies) /
  3 racks; D 936 cables (906 DAC + 30 AEC, 8 host), 157 kW IT / 188 kW wall; S 8,802 AEC, 152 chips, 517 kW.
  docs/RELEASE_RACK.md updated (sections 1, 2.1, 2.4, 2.6, 4, 6), census regenerated (untriaged 4,353, both
  annotations synced). make check-figures: evidence grades / prose figures / coverage PASS; check-headline-bundle
  FAILS on 31 NEW stale-pins in results/rtl/hdc_* (rtl/hdc sources changed on main; none of my files) = pre-existing.
  Head die power still the 10-06 C1 ledger 92.34 W (MODEL; not re-derived).
- Draft fan-out SerDes evidence (owner lean "MTP draft rides copy-B, no draft SerDes"):
  * TOK-DS composition (~/wt/tok-ds-compose tools/s81_dv/tokfunc/compose_tok_ds.py @75d8ff675, not on main):
    transform_offchip() prices off-chip only for tp_mesh / stage_hop / head_hop (head.hop); draft.head carries
    only "head die wire +34" (UNMAPPED_TAIL), no link class.
  * token DAG results/arch/token_path_20261009/ds_rom_mtp.json: mtp.2.ffn.hc_post -> draft.head0 -> draft.markov0 ->
    ... -> draft.head4 -> draft.markov4 -> draft.fixed: every edge link None (the 5 draft head steps run on the head
    die back to back, no fan-out crossing). The draft blocks (mtp.*) themselves are "not built: no die" (DSpark
    placement stated, not bound) -> WHERE the draft blocks live (copy-B or else) is not in the composition.
  * MU calendar results/arch/mu_s81_1018/calendar_mtp.json offchip.saving.mtp.by_class = stage_hop 127 / tp_mesh 275 /
    head_hop 1 crossings a step; no draft class; head appears once ("Stage 58: head die").
  => The composition of record uses NO head-die draft fan-out link. Plan keeps 12 SerDes (no draft SerDes).
- G1: own visual review recorded results/geom_review/s81_head_plan__s81_head__3f5150797f1e.json (PASS-CONDITIONAL,
  SELF review, kit physical/die_plan/s81_head@cc7b6206fc; also in the takeover verdict dir). Notes: MY-symmetric,
  no G0 marks, 4 corner voids ~5.7 mm2 + 11 dark tiles = levers; clock root -> farthest tap ~17 mm.
  (Plan changed after the review only in hd_tile contents/module/cores binding, no geometry.)
- G2 on intel2 (/srv/opentallas-scratch2/claude/s81-head/g2, docker --memory = --memory-swap): die probe PASS
  (overflow 0, M8 0.01% / M9 0.02%, clk reach max 16,998 um p90 13,159 over 2,540 taps, rst max 16,087);
  partitions worst-5 (hd_turn_a/b, hd_st_n3/n4/k5) PASS overflow 0 / no-AP 0; + hd_tile / hd_spn / hd_spn_end PASS.
  Reports physical/die_plan/s81_head/g2_report.json, g2_part_report.json, g2_part2_report.json.
  RISK: 17 mm root -> tap is a die clock-tree design job (H-tree / grid), not a probe failure.
- CUT 0x1ff vs 0x17b: NOT cycle-equivalent (SK 11 vs 8: +54 cycles a position), so instead of re-closing the elements
  the tile is REBASED on the closed views' point: ot_s81hd_tile / ot_s81hd_bundle defaults CUT 0x1ff, SPLIT9 1.
  Proofs: tools/s81_head/hd_elem_eq.sh = ot_s81hd_elem (census copy) vs closed RTL ot_dsrom_head_elem@f11f3cc47,
  cycle lockstep on every common output, protocol (finite x, fault-free argmax) + 2 stress + 1 Inf/NaN stress:
  EQ_BENCH_PASS A 4/4, B 4/4. ROM images re-skewed SK 8 -> 11 (tools/s81_head/hd_reskew_images.py, round-trip
  byte-exact). Mini array (spo -> 2 tiles -> spr, released head.weight) at 0x1ff/1: 4/4 exact, 8,429 cycles
  (was 8,375); CV=1 (closed-view models) 4/4; 6 mutants caught; 0x17b point still 4/4.
  Logs results/rtl/s81_head_tile_1024_closedcut/. Model: bundle 8,413 cyc, head 9,110 cyc a position (calendar
  window 10,357: -1,247 margin).
- G3 hd_tile kit: plan type module ot_s81hd_tile_p; elements = renamed closed views ot_s81hd_elem{A,B}_cv
  (physical/die_plan/s81_head/cores/views, tools/s81_head/hd_cv_views.py names-only, --check PASS) at
  u_core.u_b.g_cv.u_eA0..3 / g_cvb.u_eB; straps row0/ten = ot_s81hd_strap (18 kept TIEHI/TIELO, mask-variant class
  like the ROM code; kit built at ROW0 0 / TEN 1). Kit via gen.py phys (main 4b7b2b3e64 gates): sdc_lint PASS,
  synth PASS, face_guard PASS 1,132/1,132. ROUTE RUNNING: ot-run --hosts intel2 unit oth-ubuntu-514688-1792853423,
  dir /srv/opentallas-scratch2/claude/s81-head/g3/hd_tile (run_route.log). r1 died at synth (strap generate-if) ->
  kept at ../g3_fail_strap_r1.
## Next
hd_tile G3 route verdict (+ abstract, pin audit) -> record; then G4 needs the other 15 types (see ELEM-S81 reply).
## OWNER?
(1-2 DECIDED OWNER 2026-10-24: 4 head dies, no HBM; applied. 3: evidence above, owner to confirm.)
1. Head-die count: rack has 12 (3 TP4 groups, 10-06 record); model: 1 group (4 dies) carries saturated AR + MTP and
   single-user MTP positions never overlap (>= 23,239 cycles apart). 12 -> 4 saves 8 dies + 8 host links.
2. HBM on head dies: rack says 4 stacks/die (48); this die needs none (ROM-resident head). Plan has none.
3. Draft fan-out SerDes (SPEC v1: 5): rack wires none (placeholders); plan has none. Confirm MTP draft rides copy-B.
4. 11 dark tile slots (ten=0) kept for a regular chain; alternative shorter last chain, same outline.
5. Copy-A/B 6th pair on 64 layer dies (EN2/3, WS2/3) missing from the layer-die plan (S81 lane).

## From ELEM-S81 (2026-10-24, lane ~/coord/lanes/ELEM-S81.md)
COORD: ELEM-S81 closes the S81 + head-die types nobody runs. You own hd_tile. Do you plan G3 kits for the other head
types (hd_turn_a/b, hd_st_*, hd_spn/_end, hd_serdes, hd_mesh, hd_ctl, hd_host, hd_lep0N)? If not, I take them once
their RTL exists (ot_s81hd_ctl / mesh_ep / host_ep: is there RTL?). Reply here.

## 08:20 review before route (owner order 08:05) -> hd_tile floorplan REVISED (branch @fa3ada974c)
- r2 hd_tile route (started 07:47) reviewed from its own 3_3 global placement (dumped from the ODB):
  results/geom_review/s81_head_img/hd_tile_r2_global_place_FAIL.png => FAIL: elemB W face + 566-bit bus-i window in one
  8.64-um sliver; A S-face x pins (130 each) on the tile S edge; ~20k skew-line flops packed in the 27.9-um column while
  a 345 x 345 region stayed empty. Route CANCELLED (ot-run --cancel + docker stop of my container), kept at
  intel2 /srv/opentallas-scratch2/claude/s81-head/g3_fail_review_r2.
- r3: tile 708.48 x 1036.8 (+17.28 from the spine column 1,762 -> 1,382; die outline unchanged); A cores MX / R180 /
  R0 / MY at x 17.28 / 371.52, y 8.64 / 380.16: all A S faces on a 53.85-um centre row channel, E faces on a 36.57-um
  centre column, W faces on 17.28 / 19.29 strips; elemB centred in the top band (W / E regions 216 / 215 um for face
  flops, BST, skew, merge). Picture results/geom_review/s81_head_img/hd_tile_r3_floorplan.png. Die render re-read.
  Record results/geom_review/s81_head_hd_tile__s81_head__99c092a95cfa.json (PASS-CONDITIONAL, SELF).
- Running now (intel2): G2 re-run on r3 geometry (/srv/opentallas-scratch2/claude/s81-head/g2r3: die + 8 types) and
  G3 hd_tile r3 route (ot-run unit oth-ubuntu-706037-1792854766, dir .../g3/hd_tile). GEOM-REVIEW: second review welcome
  on the two PNGs above.

### Reply to ELEM-S81 (S81-HEAD 2026-10-24 07:55)
I run hd_tile G3 only. Please take the other 15 head types. RTL state: hd_spn/hd_spn_end leaves ot_s81hd_spo / spr
exist + CLOSED (rtl/dsrom_sys/s81_head); hd_turn_*/hd_st_* are ft-only frames (no leaf, gen.py rtl wrapper);
hd_serdes = ot_pdie_serdes (reuse); hd_lep0N = dsdv_slice_lepw_mu.LP (reuse). NO RTL on main for ot_s81hd_ctl,
ot_s81hd_mesh_ep, ot_s81hd_host_ep (new / rework); ot_s81hd_ctl(_glue) exists only on the unmerged H10/H11 branch
(commit b0dd078e0e 'S81 HEAD ctl glue R3', 4339e679fd, 0f16024219). Note: hd_mesh / hd_ctl / hd_host have type module == content module
in the plan (wrapper name collision, as hd_tile had); rename the type module (hd_tile -> ot_s81hd_tile_p) before
gen.py rtl. Plan generator physical/die_plan/s81_head/gen_plan.py; edit via me or tell me and I change it.

### From ELEM-S81 (08:35): taking the 15 head types
- ft-only types kitted (gen.py phys, sdc_lint PASS) and placing for review on epyc3: hd_turn_a/b, hd_st_turn/str/n3/n4/m/k5.
- BLOCKED on the plan (your gen_plan.py): hd_spn / hd_spn_end have no `sources` for ot_s81hd_spo / ot_s81hd_spr (kit RTL
  instantiates u_spo/u_spr with no definition) -- please add sources (or make spo/spr hard_cores with their closed LEF);
  hd_mesh / hd_ctl / hd_host: type module == content module + no RTL (as you said); hd_serdes (ot_pdie_serdes) and
  hd_lep0N (dsdv_slice_lepw_mu.LP) need sources/bind like the layer die. I re-close the spo/spr hard-core kits
  (signoff NEEDS RE-RUN) in my hc batch D.

## GEOM-REVIEW findings (2026-10-24 08:55 PDT, independent die-level review, batch 1)
- S81 head plan 6b6620d0 (@fa3ada974c; cc7b6206 geometry identical): PASS-CONDITIONAL (record s81_head_plan__s81_head2__6b6620d0e030.json) - independent review, supersedes the self review for G1. Clean: symmetry, no slivers, hops <= 0.31 reach, tile macros 10-15 um channels with the tap in a channel, all 18 bit reversals are corner crossings (free as L-routes). Lever: the 345-um station/spine partitions force 3-4x the stations reach needs (m0S 48 cyc / 16.3 mm, host 38 cyc / 12.4 mm, coll_WN2 20 cyc / 6.5 mm) - wider station partitions would cut tens of cycles on the mesh/host lanes. hd_tile: the revised floorplan after your failed r2 must be rendered + recorded before route; GEOM-REVIEW tile review of hd_tile running.

## CODEX notes
CODEX took over: hd_tile synth infrastructure fix in /srv/opentallas-scratch2/claude/codex-s81/head_g3r5 on intel2 (same reviewed r3 geometry). g3r4 FAIL at synth_odb: missing face_keep.tcl (kit generator hook-copy omission). Added both main face_keep hooks to fresh kit copy; r3 floorplan image visually reviewed: centre channels align A input pins, B centred, macro halos clear; PASS-COND carried, monitor clock balance. New route via ot-run 64GB/16 threads.

09:50 PDT CODEX: r3+G2 authorbranch integrated,TT macro libs insteadSS+5earlycore clockdrops,main9f180d5e4a;newr7routeintel2.../codex-s81/head_tt_g3r7. Ownr5FAILCTSmax18243holdbuffers(-352ps),preserved.

10:29 PDT CODEX: Head reach405 fix merged747cdc9dfb:13FTslots/29lanes,max+3cycles,die model+6(9114). CanonicalSDC/nativeMM/earlyclock c2hd_tile FAILCTS18200holdbuffers,flat-377.977ps. c3diagnosticCTS(skiprepair) capturesFFadjacentline24->40 launch232/capture604/data41=>-369ps. Root fixes tap_balance false T/2wrapping;own160umgrid variant generates35taps tosplit13,342sink coarsegridcluster. Intel2.../codex-s81/head_tt_g3r8_c3_diag preserved, noSIGNED.


CODEX 2026-10-24 11:24 PDT: tap160c7 correctTTCTS +FFonlyholdGRT failed pinaccess: four elemA_cv clkM5pins DRT0073. RealLEFclockRECT293.568,317.588..293.592,317.672 overlaps ownOBS through317.648, only24nmexposed; adjacentM6OBS. NeedsourceODBlegalclockpin/stub/phase repair, no syntheticpin enlargement. All160gridtimingattempts retained, noSIGNED.

## RESUMED 2026-10-24 12:16 PDT (Claude, after the 08:50-12:04 limit)
- Adopted: (1) Codex head abstract PSM c2 (intel2 .../codex-s81/trial_head_psm_c2, container dtrial-psm-1648419, VDD/VSS connectivity PASS, IR analysis still running): left running, I collect its result. (2) The hd_tile pin-access blocker (tap160c7 GRT DRT-0073 on the four elemA_cv clk pins, 24-nm sliver of the closed view's M5 clk stub; source ODB lost). (3) Codex's partial elemA rebuild builder (localhost scratch headA_native_rebuild_c1, never ran past sdc_lint): replaced by tools/s81_head/hd_elemA_rebuild.py on my branch.
- My branch claude/s81-head-1024 = main 24b2da3433 (all my earlier commits were already on main via Codex 27fe25b8b2).
- elemA rebuild: same source f11f3cc47 / params (LV8 PAD0 JOIN1 ROWS32 IOREG1 SAFE1 CUT511 SPLIT9 1), 458 signal pins pinned to the closed-view rects, clk = 0.192 square M5 at the same centre column. Template = signed kits_repin core (VQ r12): kit SDC, TT setup / FF hold, sdc_lint, face_guard, signoff.py.
  - c1 (intel2 scratch2 .../s81-head/elemA_rb/elemA_rb_c1): FAIL sdc_lint: the closed build's ROM 2-cycle multicycle is a forbidden exception. Kept.
  - c2: no multicycle (rd -> capture timed at 1 cycle, stricter; ROM clk->q 590 ps TT). Running synth + floorplan only; floorplan review before any route.

## GEOM-REVIEW findings (2026-10-24 13:40 PDT, tile batch 2, main da5213b0b3)
- hd_tile tap160c7 (4_cts, GRT fail): FAIL. Pin defect confirmed visually: elemA_cv M5 clock pin is 84 nm tall, 60 nm of it under the macro's own M5 OBS and an M6 OBS under the via, leaving a 24x24 nm opening, on all 4 elemA instances. Fix: regenerate the elemA_cv LEF/abstract (the native rebuild path), then rerun GRT/DRT only. Separately: u_eA0/best_key 14-level logic path TT -627 ps needs an RTL pipeline register before route. 8 taps carry no sinks. CTS (tap means 238-264 ps) and face flops (p90 6.7 um) are fine. STOP resubmitting this kit until the LEF and the best_key path are fixed.
  Images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-B2/hd_tile_tap160c7/{review,clkpin_obs_zoom,codex_tap_review}.png; record results/geom_review/hd_tile__head_tap160_c7_ff__1681610bdc9a.json
- 2026-10-24 13:16 PDT elemA rebuild progress:
  - c3 (lane RTL + sim wrapper): FAIL face_guard ('shared' l_d / best_row / go / done).
  - c4 (f11 RTL + keep regs on o/l): FAIL face_guard. Keep on the reg wires leaves a buffer load on the port net; best_row feeds the argmax compare; done / best_* are hold flops feeding their own D.
  - c5: f11f3cc47 RTL under rtl/dsrom_sys/s81_head/ot_s81hd_elemA_rb.sv, with one dedicated output stage ot_s81hd_oreg (keep_hierarchy, as ot_dp_st) on EVERY output.
    - Cost: +1 cycle on all elemA outputs. The tile sim model ot_s81hd_elem_cv.sv carries the same stage.
    - Tile bench CV=1 ALL PASS at 8,430 cycles (was 8,429). Die model +1: 9,115 a position.
    - face_guard PASS 456/456. Auto ROM placement REJECTED at review: both ROMs on the W core edge, rd/ctl pins in the halo.
  - c6: fixed centred R0 ROM sites. Floorplan review PASS-COND (results/geom_review/s81_head_elemA_rebuild__s81_head__745b97d78c32.json + s81_head_img/elemA_rb_c{5,6}_floorplan*.png). GEOM-REVIEW second review welcome.
  - ROUTE c6 running on intel2 (scratch2 .../s81-head/elemA_rb/elemA_rb_c6): route + abstract + pin audit + TT/FF corners + signoff.py.
  - Next: new view → views_rb, regenerate the hd_tile plan/kit (main gen.py, face_keep), review, route the tile.
- 2026-10-24 14:27 PDT (Claude) elemA/elemB rebuild + reply to GEOM-REVIEW tile batch 2:
  - LEF/clk-pin finding: being fixed by the native rebuild. Element clk pins are now 0.192 squares: A M5 at the N edge, B M4 at the W edge.
  - best_key -627 ps finding: fixed in RTL. ot_s81hd_bundle now has a pk_q register stage, so the four A results are registered tile-side before the level-1 compare.
    - The element outputs are also dedicated flops now (ot_s81hd_oreg).
    - Tile bench ALL PASS: CV=1 8,432, CV=0 8,430. Die model 9,117.
    - Mutants re-running.
  - elemA c6 route cancelled: the TT CTS tree is ~450 ps, which gave -214 ps IO hold on every pin register (21.5k hold buffers).
  - elemA c7 = CP2 early core tap: kit SDC has clk source latency -200, and sdc_lint port_latency matches. The tile must deliver it early.
  - c7 CTS: 976 setup endpoints and 16.2k hold endpoints before repair (HOLD_SLACK_MARGIN 15 on a CUT-0x1ff pipeline: 1-gate flop-to-flop paths). 21.8k hold buffers. Route continuing.
  - elemB c2: face_guard PASS (u_bin_jn kept register on the JOIN-0 unused inputs, plus face_keep hooks). Floorplan review PASS-COND (results/geom_review/s81_head_elemB_rebuild__s81_head__c04272d38bef.json). Route running, early tap 170.
  - The hd_tile kit is NOT resubmitted until both views are routed and signed.
- 2026-10-24 18:53 PDT (Claude) after the second resume. Owner decisions (BRIEFING 10-24 18:4x) are applied to the head elements.
  - Status: main 9b1a4d16e0.
  - Done already: builder committed, floorplans reviewed, best_key pipeline register (bundle pk_q).
  - Reset rule: each rebuilt element takes rst_n through one local relay flop (synchronous delivery), and its flops then use timed recovery/removal. Bench CV=1 ALL PASS.
  - elemA c7 routed: NOT SIGNED.
    - Clean checks: DRC 0, ant 0, pin audit 458/458, face_guard / sdc_lint PASS.
    - TT setup -71.32: rst_n recovery only. The clk group is +159.9, vclk +500.
    - FF hold -43.21 (150): output face flops arrive at 122 ps FF against the fixed 250-ps vclk, because the early tap of 200 is too large at FF.
    - Pin-register insertion TT mean 214 / FF 138, spread 54.
  - elemB c2 routed: NOT SIGNED. TT -3.26 (2), FF hold -36.78 (149 outputs), TT slew 5, TT insertion 199.5 (< 210).
  - Relaunched: elemA c8 (early 160 + reset relay) and elemB c4 (early 120 + reset relay), both full route on intel2 scratch2 .../s81-head/elemA_rb/.
  - Margins: INFO only, per decision 3.

## PARKED 2026-10-24 19:04 PDT (Claude, S81-HEAD)
- Branch claude/s81-head-1024@6333cd8efb, pushed. main 9b1a4d16e0 has everything gated; the only unmerged commit is 6333cd8efb (gen_plan picks cores/views_rb once the rebuilt views land; G0 PASS, no geometry change).
- Live jobs (running, mine), both on intel2 docker:
  - elemA c8: /srv/opentallas-scratch2/claude/s81-head/elemA_rb/elemA_rb_c8, container krepin-elemA_rb_c8-1355604. Full route plus signoff.py; early tap 160 + reset relay. Local log /tmp/s81h_elemA_rb_c8_route.log.
  - elemB c4: .../elemA_rb/elemB_rb_c4, container krepin-elemB_rb_c4-1362968. Early tap 120 + reset relay. Local log /tmp/s81h_elemB_rb_c4_route.log.
  - When they finish, read <kit>/signoff.log and signoff/signoff.json.
- Head PSM c2 (Codex, adopted, container dtrial-psm-1648419): still running IR. No result yet.
- Results:
  - elemA c7: routed, NOT SIGNED. TT -71.32 (rst_n recovery only; clk group +160). FF hold -43.21 (150 output face flops; early tap 200 too big at FF). TT pin-register insertion 214. DRC/ant 0, pin audit 458/458.
  - elemB c2: routed, NOT SIGNED. TT -3.26, FF -36.78, TT slew 5, TT insertion 199.5.
  - Tile bench CV=1 ALL PASS at 8,432. 6 mutants caught. Die model 9,117.
- Failures kept (records): elemA c1 (sdc_lint multicycle), c2–c4 (face_guard), c5 (auto ROM placement rejected), c6 (IO hold, cancelled); elemB c1 (face_guard dropped), c3 (cancelled).
- Next steps:
  1. If c8/c4 are SIGNED, copy <kit>/views (LEF + TT/FF lib) to physical/die_plan/s81_head/cores/views_rb/ot_s81hd_elem{A,B}_cv/.
     - Check the lib max_clock_tree_path: early_core_taps.py takes the early tap as lib rise - 250, and it must equal the kit early (160 / 120).
  2. Regenerate the die plan and the hd_tile kit (main gen.py, face_keep). Do the visual review, then route the tile.
  3. If NOT SIGNED: retune the early tap (TT pin-register mean target ~250; FF output hold) and/or fix the slew.
- OWNER?:
  - Each rebuilt element adds a +1 output register stage (face guard), and the tile adds a pk_q stage, for +3 cycles a position in total. Each element also adds +1 reset cycle.
  - The ROM-read 2-cycle multicycle of the closed build was dropped; the read path is timed single-cycle and passes.
- Local ot-run clients: pid 2349614 (elemA c8), pid 2382002 (elemB c4).
2026-10-24 20:17 PDT RESET -> S81-HEAD: hd_tile: plan reset.release pipelined + gen.py phys gives the kit-level delivered reset (u_rst_in + equal-depth tree; no per-tap u_rsync_t). Your element relay (d456fea42f) = core reset depth +1 vs its tap: count it in the schedule. s81_head priced: K 10, E 43, release 56 clk, 12 partitions unhosted for die relays. recipes in lanes/RESET.md ## RECIPES; tool claude/reset-1024@d1152532c (READY)

## CODEX notes 2026-10-24 21:11 PDT / PARKED back to Claude
- Collected elemA c8 NOT SIGNED TT +104.68 / FF -14.24 (118), DRV0, DRC0; elemB c4 NOT SIGNED TT +108.34 / FF -9.87 (104), slew6TT/5FF, DRC0; face/sdc/pinaudit PASS both. Later c9 A/c5 B already active on epyc2; no duplicate launched. c9 CTS/GRT hold repair, c5 detailed-route pin access/extra GRT iterations at latest read.
- Preview tile placement DONE epyc2:/srv/opentallas-scratch2/claude/s81-head/tile_prev1/hd_tile (3_place.odb), 68% utilization. Geometry-only dump via ot-run completed epyc2:/srv/opentallas-scratch2/claude/codex-head-review/dump.json (unit oth-ubuntu-2705537-1792901374 exit0); rendering/visual review NOT RUN, so no route authorized. CLOCK kit_taps informed density needs actual internal skew-flop sinks beyond face/FT inventory.
- Prepared codex/s81-head-1024r at c8218bab98; no edits/commits, interrupted only own initial worktree creation on park and removed that partial worktree safely. Branch retained. No new heavy jobs running from CODEX HEAD.
- 2026-10-24 21:20 PDT CLOCK -> S81/HEAD: RULING core-latency contract: the early core tap value = the core's SIGNED kit pin->register mean insertion (signed kit clk source latency, i.e. elemA 160 / elemB 120 early vs the 250 common latency), NOT lib max_clock_tree_path - 250 (max is a worst sink, not the mean the core was signed against; lib value = cross-check only, flag if |lib mean - signed| > 20 ps). Your gen_plan override (signed kit early + 250 from views_rb MANIFEST) is the correct value; keep it. Density-tap kit option: CLOCK is finishing codex/kit-taps-1024 (sink-density taps, cap ~1000-1500, none over hard cores, distance+load assignment, GRT-RC 20 ps window); will post here when it exists.
- 2026-10-24 21:52 PDT CLOCK -> S81/HEAD: the density-tap kit option EXISTS: claude/kit-taps-1024@8d4be5a76 (opt-in; defaults unchanged; tests 7 new + g2/cp2/schema/check pass; READY being posted). Set hd_tile clock: tap_mode="density", tap_max_sinks=1500, sink_bins_file="physical/die_plan/s81_head/hd_tile_sink_bins.json" (23,152 regs from epyc2 tile_prev1 3_place, committed on that branch). Probe (CTS only on your preview 3_place, placement RC): 30 taps, 237-1266 sinks/tap, none on a core/keep-clear, raw tap trees 86-143 ps mean (grid had a 716-ps branch), balanced 232-262 ps (28/30 within 250+-20); worst sinks t23 290, t14 278. Core taps came out late only because the preview kit core_latency.txt still holds lib max 441/435 -> use the signed kit means (ruling above). GRT stopped on DRT-0073 no access point u_core.u_b.g_cvb.u_eB/clk (elemB clk pin access, yours). PNG + logs epyc2:/srv/opentallas-scratch2/claude/clock/ktprobe/keep/. GEOM review before routing.
2026-10-24 22:25 PDT RESET -> S81-HEAD: RESET wavefront API (OWNER DECISION 13), claude/reset-1024@0a08a66af (READY, not yet on main): plan "reset": {"release": "wavefront"} (opt relay_um 405, hop_um, in_sites {type:[x,y]}, root_part; hard types reset.tap_um / reset.depth). Then: gen.py rtl/phys emit u_rst_in (u_rst_root in the root's type) + equal-depth u_rrl tree to taps AND registered outs rst_o_<k> (interior pins, io.tcl + LEF), die top wires parent rst_o -> child arst_n; bound kits: kit_rsync.py PLAN TYPE KIT_RTL_DIR --release wavefront (adds rst_o to bound module + wrapper). Offsets: python3 tools/die_plan/reset_tree.py offsets PLAN.json [--release wavefront] --out J. G0 errors list partitions whose IN pin has no neighbour rst_o within hop (move IN / hard reset.tap_um to a face). Reset only control state; start broadcast after reset (13c/d) are RTL/schedule items.
2026-10-24 22:33 PDT METH-ALIGN -> S81-HEAD: REQUEST s81_head: only die_use ft_reserved remains (G0C FAIL 1E m89_signals); hops all <= 405 (worst 361 um). Drop ft_reserved from die.layer_budget.die_use (and set die.reach_um 405) on claude/methodology-align-1024@5173eb8e3a2a rules.
2026-10-24 22:35 PDT COORD -> S81-HEAD: METH-ALIGN re-plan request above is the ONE batched plan change for dec. 12 (signals <= M7, hops/stations <= 405 um exactly, no 0.9 margin). Do it now on a branch based on claude/methodology-align-1024@5173eb8e3a2a, regenerate stations with the tool (no hand edits), report added cycles per lane to TOK-* for pricing, list SIGNED/in-flight types whose ft stations change (re-kit once), post READY. Do not start new routes on types this re-plan changes until it lands.
2026-10-24 22:37 PDT COORD -> S81-HEAD: fold the wavefront reset switch (reset.release=wavefront, claude/reset-1024@0a08a66af) and any reset.tap_um moves RESET posted for your hard partitions into the SAME batched re-plan (dec. 17). One plan change per die covers both rules.

## CODEX notes 2026-10-25 02:40 PDT
CODEX took over: head3 element result collection + FF repair on codex/s81-head3-1025 (own sparse WT /srv/opentallas-scratch/claude/wt/codex-s81-head3). Collected elemB c9 NOT SIGNED TT +117.24 / FF -14.34ps (180 ep), TT slew2, DRC0, face/sdc PASS. Clock pair 179.65/177.23ps has exact120ps measurement cross-check error matching early source latency; sent to CLOCK/root for tool fix, no gate credit. c8 legacy STA FF -4.79ps/1ep, current signoff pending; A c11/c12 still finishing. Comparator mini bench CV0/CV1 4/4 PASS, five mutants caught. Own warm GRT copies epyc3:/srv/opentallas-scratch2/claude/codex-head3/elemB_{c8,c9}_ff5 use BC-only hold margin5 then route/default TT, slew50; geometry inherited and image viewed, review results/geom_review/codex_head_ff_eco_1025.json. Original jobs untouched. ot-run local client logs /srv/opentallas-scratch/claude/codex-head3/{c8,c9}_client.log.

## CODEX notes 2026-10-25 02:48 PDT
Original elemB c8 also NOT SIGNED: TT +113.32 / FF -4.79ps (1 ep), TT slew1/FF slew1, DRC0. Original elemA c12 NOT SIGNED TT +113.42 / FF -18.02ps (154 ep), DRV0/DRC0, face/sdc PASS. Original pair metrics carry exact120/160ps source-latency cross-check errors; CLOCK corrected b0613e9d9, installed in all own ECO kits. A12 own warm BC5 successor now live epyc3 codex-head3/elemA_c12_ff5; no constraint change. Initial nohup clients vanished before starting; actual launches use setsid and admission confirmed (B8 unit1924040, B9 similarly, A12 client3518524). Tile chain_anchor root cause confirmed in code: independent 4um bins allocate overlapping 8-column FIRM clusters and clamp x at the core edge; new global footprint allocator is in own tree, anchor-only preflight epyc2 codex-head3/tile_anchor_legal unit3712002. It respects all macro halos and existing fixed cells; no GPL or route until rendered anchors reviewed. New density1500 taps owed after placed sink inventory (CLOCK recipe taps.py bins; tap_balance_rc=grt).
2026-10-25 03:08 PDT COORD RULING S81.IR: adopt pg_domains.py --split on S81 and S81 head (PHY domain = macro + guard inside the serdes partition, no overlap; core strip with core C4 for boundary flops + ft stations; core C4 kept 15 um outside the domain). Sequencing (no extra re-plan of other types): do NOT hold claude/s81-dec12-1025 for it -- merge the batch as is; the split is a follow-on plan delta limited to the serdes partitions + their direct neighbours, done right after the batch merge. Until that delta merges, NO kits for the serdes partitions or their direct neighbours on S81 and S81 head; all other types proceed. PHY load 6.5 pJ/bit x 112 Gb/s x 6 lanes is the recorded assumption.
2026-10-25 03:16 PDT INFRA -> S81-HEAD: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: /srv/opentallas-scratch/claude/s81-head, claude/wt/s81-head-r. When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.

## CODEX notes 2026-10-25 03:20 PDT
A11 current corrected-pair signoff (intel1 codex-head3/elemA_c11_resign) NOT SIGNED: TT+104.94 / FF-13.32ps(103), pair65.1/65.3PASS, DRV0/DRC0, face/sdcPASS. Warm BC5 GRT successors also FAIL afterRCX: B8 TT+106.19 / FF-11.48(64), DRV0/DRC0,pair65.5/60.7; B9 TT+114.48 / FF-15.42(163), slew1TT+1FF,DRC0,pair63.6/59.7. Diagnosis: +5psGRT hold loses~20ps atRCX; moving to actual extractedSPEF repair, no more blindGRT re-runs. Live m5 extracted variants (KV proven recipe, TT+FF setup/hold,fanout24,DRV_LAST+RETIME_LAST): epyc3:/srv/opentallas-scratch2/claude/codex-head3/elemB_c8_rcx_m5 unit2443219; intel1:.../elemA_c11_rcx_m5, client3680485.
Head tile anchor v3 image viewed: results/geom_review/codex_head_anchor_1025/review.json PASS-COND PLACEONLY.32,896FF/768chains,0 overlaps/0halo,34,176 actualconnections max396.144um,0>405. Preserved v1FAIL14,484overlaps(setLocation beforeMXorientation),v2FAILone460umhop; fixedorientationorder andmovedoneB rootstage65.07um; sourceaddsconsecutivehopguard. WarmGPLvariants intel2 codex-head3/tile_anchor_legal,tile_bin256,tile_init_dp; baselinechooses2048²subcellbins,coarse256variantandinitial+DPvariant testfiller/densityartifact. Allsamereviewedgeometry; NOroute. Freshfullsourceanchorproof intel2 codex-head3/tile_anchor_reach active. Density1500clock awaitsplacedfullsinkinventory; SIGNEDnativeelementviews awaited.

2026-10-25 03:30 PDT CODEX PHY: head supply metadata READYcodex/head-phy-strip-1025@7cbf009cc, source-approvedsame6laneS81PHYreservation. Keeps150umCOREdigitalstrip+63.64umguard, reservedzone2885.76x1013.24um, separatelylabels562680.012um2MODELarea; no measured-bodyclaim. G0C0E6W; partitions/types/ports/lanes/all325depthsunchanged. Viewedregion+plannedPGpinmaps inresults/geom_review/head_phy_strip_1025. RequiresXDIE3die_io.py@69f1API; dependencyfilekeptuncommittedinownheadworktree(notinowncommit). Opt-inprototypewithnewPGtoolgenerates16views+326partassembly664bindings12PHYpins; releasedviewsnotrelabelled. Parent/rootgivenexactcherry-pickshas.

2026-10-25 03:36 PDT CODEX PARKED on Claude reset instruction. Exact worker branches/jobs/results/next steps are in CODEX-LOG.md "Handoff to Claude 2026-10-25 03:36 PDT — CODEX clock/reset partcap worker". No half-written sources or merge. Live N27 and owned guardian may continue; no new work started.

## CODEX notes 2026-10-25 03:36 PDT — parked for Claude reset
S81 missing-core/head non-tile branch codex/s81-missing-1025@4e4d8acad (LOCAL WIP; prior6502d0a04/8a2a5db7a/f5ccc9519/d0ffb0275 pushed). Core layout face/track gates0/0 but actual core-core relay RTL remains NOT IMPLEMENTED, explicitly held. Normal/endspine real relay exactness PASS3000 each, mutants caught68/40, both placements now COMPLETE (normal epyc3 unit2384296, end epyc1 unit3489931); view actual placed images before route. HeadFT corrected ffonly route final signoff pending epyc1:.../codex-s81-missing/head_ft/hd_st_m_ffonly (unit3050405). RealKP4 SerDes adapter good1200beat exact miter PASS; status mutant still live .../serdes_eq(unit3813238). Complete job paths/commands/failure diagnoses/OWNER items in CODEX-LOG handoff section. No main merge, no false closure, original jobs untouched.

## CODEX notes — Handoff to Claude 2026-10-25 03:36 PDT
S81 subgroup parked on RESET; all jobs preserved. Main summary in CODEX-LOG.md Handoff S81 subgroup. Exact FT source36915c557 pushed;178type cached outputG0C0E at epyc1 codex-s81-ft-exact/adopt178, not committed yet and predates nine fault feeders. New hcpost_h5 actualSIGNED TT+61.39/FF+3.68ps, views unintegrated. Core-pair relay metadata missing actualRTL remains held/assigned; one-stage legacy canonicalfaceFAIL remains, two-stage ruling20:42 ownedCLOCK. Child detailed handoffs follow; no newjobs/merges.

## CODEX notes — PARKED 2026-10-25 03:36 PDT
Claude reset. codex/s81-head3-1025@4159282c5 pushed WIP (not merge-ready); full handoff in CODEX-LOG. Live m5 extracted ECOs B8 epyc3 unit2443219, A11 intel1 unit1417712; fresh anchor source proof intel2 unit2555513; baseline GPL unit2476881. Placement initial+DP and bin256 variants completed exit0; initial+DP has0 violations,34,176 actual hops max396.360um,37,602 register inventory. Native element SIGNED views still awaited; no route authorized on old preview B clock pin. Density SOURCE+bins committed but generated plan restored (full latency regen owed). All failures retained and next fixes recorded in CODEX-LOG. No new owner question.

## Claude S81-HEAD resumed 2026-10-25 04:25 PDT (fresh lane agent, main 7c33a7a81)
- Collected (all Codex head jobs terminal, no live containers):
  - elemA c11 m5 (intel1 codex-head3/elemA_c11_rcx_m5): SIGNED TT +93.06 / FF +0.99, pair 59.9/60.6, DRC0, face/sdc PASS, pins 458/458. Obtained by the post-route extracted-SPEF hold ECO launched ~03:20, BEFORE the owner 04:13 no-ECO rule. COORD? adopt this view or require the structural rebuild (FF margin 0.99 ps).
  - elemB c8 m5 (epyc3 codex-head3/elemB_c8_rcx_m5): NOT SIGNED TT +112.88 / FF +5.05, DRV slew 1 per corner (u_m.w_r[244]/D 350.8 vs 320). -> structural review (sub-agent HEAD-ELEM), no ECO.
  - Tile anchor fresh full-source proof (intel2 tile_anchor_reach): 32,896 chain flops / 768 chains FIRM, placed max hop 402.192 um, 0 > 405, max legalisation displacement 200.1 um; reset tree 29 flops max hop 369.4 PASS. tile_init_dp / tile_bin256 placed 3_place.odb (max hop 396.36). No route (needs signed element views).
- Started: HEAD-ELEM (elemB structural fix + GRT-vs-RCX check, GEOM REQ), HEAD-ADAPT (COORD ruling 3: beat-link contract/RTL + H4 tl/ca/cb plan delta). Lane itself: PHY/PG cherry-picks 1ac73030d/1f9559e2d/7cbf009cc onto main -> checks -> READY.
2026-10-25 04:34 PDT PROTO-KITS -> S81-HEAD: GEOM-REVIEW 04:29 conditions on hd_turn_a/b (routes running): your hd_tile kit must show i pin -> first register <=60 um on the b t_o face (345 um leg on our side), and the zero-sink clock taps hd_turn_a clk_t2 / hd_turn_b clk need pruning or an 'unloaded' declaration in the head plan for spine tap balance.

## S81-HEAD/ADAPT 2026-10-25 04:39 PDT (COORD ruling 3) -- READY claude/s81-head-adapt-1025@f0e4dd18de
- Contract results/arch/s81_head_1025/ADAPTER.md; RTL rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv; bench tools/s81_head/beat_link_bench.sh
  (logs epyc1:/srv/opentallas-scratch2/claude/s81-head-adapt/b5): 12/12 good runs PASS, 18/18 mutant runs caught.
- Plan: H4 tl/ca/cb lanes ctl<->lep0N added (2 cyc each); G0 0E/6W, G0C 0E 16/16. No jobs live.
COORD?/OWNER? (not fixed by the compiled schedule, not invented):
 1. Host lane width: a 553-b record needs P=277 for 2 beats (2x276=552) -> port 279 wires (HBC 1104/4 also 279). Plan host_tx/rx +
    spine hu/hd ft = 276. (a) widen to 279 (+3 wires/dir, 0 cyc; re-kits hd_spn/_end/host/ctl, hd_spn place in flight) recommended;
    (b) keep 276, record in 3 beats (1 rec/3 cyc ~221 Gb/s < 331 model).
 2. Host-lane calendar: calendar_rel241_G4_{ar,mtp}.json has no head-die host/HBC slot dates; dsdv_hostb_stage_hbc BOOT_HEADER_EDGE /
    BOOT_COMMIT_EDGE unset. Which compiled slots carry lane records vs HBC words (or separate lanes) is owed; no kind field invented.
 3. H4 on the head die: head ctl originates tl / consumes ca,cb, or forwards (TOK-DS rank-tree role); lanes + pins exist (no tie-off).
2026-10-25 04:43 PDT GEOM-REVIEW-2 -> S81-HEAD: POST-ROUTE hd_st_m FAIL on IO basis + rst_o_1 pin on an M7 strap (geometry/stations OK) in lanes/GEOM-REVIEW.md.
2026-10-25 04:48 PDT HEAD-ELEM (sub-agent): structural review of pre-ECO elemA c11 / elemB c8 done -> GEOM REQ posted. C1 GRT clock C error (B 37 / A 69 ps late per sink at FF; C-calibrated GRT -6 / 12), C2 elemB ROM-side vs x-pin-side lane crossing (w_r[244] 139-um M2, slew 351), C3 vclk FF contract -> CLOCK request. Fix opt-in in hd_elemA_rebuild.py (--hold-rc-cal, --rom-orient MY, --max-wire-um) on claude/s81-head-elem-1025@02bebf7208 (not merged, no kits launched). Codex m5 ECO results not adopted (COORD ruling). Probes (read-only, done): epyc3 + intel1 /srv/opentallas-scratch2/claude/s81-head-elem/.
2026-10-25 04:50 PDT HEAD-ELEM: rebuild kits PREPARED, NOT launched (wait GEOM-REVIEW PASS): epyc1:/srv/opentallas-scratch2/claude/s81-head-elem/kits/elem{A,B}_rb_s1 (generator claude/s81-head-elem-1025@02bebf7208 via epyc1 wt /srv/opentallas-scratch2/claude/wt/s81-head-elem-1025; = c11/c8 kits + RCX-fitted hold RC margin 15; B + ROMs MY + MAX_WIRE_LENGTH 100; post_cts_gate.tcl + SKIP_CTS_REPAIR_TIMING copied from the HEAD3 c8/c11 kits since main's generator lacks them). Launch: ssh epyc1 ot-run with the kit run_kit.sh as for c8/c11 (~48g).
2026-10-25 04:50 PDT GEOM-REVIEW-2 -> S81-HEAD: head elemA c11 / elemB c8 routed review = PASS-COND for ROM mirror + RC-calibrated C + per-corner vclk (all three required, one rebuild); see lanes/GEOM-REVIEW.md.
2026-10-25 04:51 PDT HEAD-ELEM: GEOM-REVIEW 04:49 = PASS-COND for the head elem rebuild. Prepared kits epyc1:.../s81-head-elem/kits/elem{A,B}_rb_s1 do NOT yet meet cond (2) shared F2 calibration tool (they carry a private set_layer_rc wrap: M2 C 0.108, M4 0.100, M5 0.095 fF/um, platform R) or cond (3) per-corner FF vclk = measured FF pin-reg I (9.7/5e; main signoff.py --ff-vclk pin-flop-mean --ff-vclk-contract exists, but the flow's GRT hold repair still repairs outputs against vclk 250 -> must also use the FF I, else hold buffers on output ports). HOLD the kits until FLOW/CLOCK land F2 + kit-level FF vclk; then regenerate (hd_elemA_rebuild --rom-orient MY for B is final), post-CTS render (B: t_r->w_r median <=20, none >100) before route. OWNER?: none.
2026-10-25 04:55 PDT S81-HEAD -> PROTO-KITS: hd_turn_a/b cond (2) zero-sink taps (a.clk_t2, b.clk): no plan change needed. The die flow already drops sinkless taps from the kit result: gen_phys.dropped_taps() reads views/<type>/ot_clock_taps.json "dropped" and both the die top (gen_rtl.die_top) and the spine branch table (spine.branch_table) exclude them; die_sta.py top --views does the same for die STA. Requirement on your side: publish ot_clock_taps.json with the routed hd_turn views. Cond (1) hd_tile i pin -> first reg <= 60 um: will be proven in the hd_tile kit (waits on signed element views).
2026-10-25 04:55 PDT S81-HEAD: READY one head delta claude/s81-head-delta-1025@f5223815f2 (see COORD-REVIEW-QUEUE; supersedes the ADAPT-only READY). hd_st_m POST-ROUTE FAIL (GEOM-REVIEW-2 04:43: per-corner IO basis, face hop budget > 0.08 T, rst_o_1 pin on an M7 strap) noted; the IO-basis part waits on the shared 9.7/5e form, pin-off-strap is a head-plan pin item for the next delta. HEAD-ELEM2 sub-agent: elem rebuild kits s2 to GEOM conds (rc_fit.tcl F2 + per-corner vclk) -> autopilot enqueue.
2026-10-25 04:58 PDT S81-HEAD -> CLOCK-RESET/PROTO-KITS (tool finding, cross-die): hd_st_m DRC 3 (GEOM-REVIEW-2 04:43) = interior M7 pin rst_o_1 at (1434.272,1073.504) = 8.608 um inside the E face, between kit-PDN M7 VSS/VDD straps (5_route_drc.rpt: Short VDD/rst_o_1, Metal Spacing VSS/rst_o_1, EOL keepout). Cause: interior tap/reset pins (gen_phys._snap_tap; reset_tree face_sites INSET 8.64) snap only to M7/M6 tracks and never check the kit PDN M7 strap pattern (gen_phys.PDN: M7 width 0.288 spacing 0.096 pitch 8.64 offset 4.128 from CORE_AREA at 4.32). A face-inset pin lands at a fixed phase of the 8.64 strap pitch, so every type whose width is a multiple of 8.64 can hit it on the far face. Rough predictor (x phase vs strap band, not validated: it also flags hd_st_m arst_n at 8.608,8.608 which routed clean) flags ~77 s81_head / 206 s81 / 264 QC / 434 KV interior pins. Ask (tool owner, not head plan): snap interior M7 pins to a track that clears the strap pair (or offset the kit M7 strap so the inset pin column is free), plus a gen-time check against the real pdngen special wires; regenerate affected kits once. hd_st_m rebuild should take it.

2026-10-25 05:02 PDT CLOCK-RESET -> S81-HEAD: decision 13c START broadcast is READY (claude/clock-reset-1025@e84452a8fd, opt-in plan key reset.start="broadcast"; see COORD-REVIEW-QUEUE). Your next per-die batch: set reset.start=broadcast, re-kit soft types once (+start_i, +start_o_<k> beside rst_o_<k>), re-bind (raw bind emits the die 'start' pin + start wiring automatically; QC proof: epyc3:/srv/opentallas-scratch2/claude/clock-reset/start/qc_bind, errors 0). Benches: drive die 'start' (tie high = old wavefront); control state releases at S + published release offset. 
2026-10-25 05:11 PDT S81-HEAD (HEAD-SPINE review, claude/s81-head-spine-1025@07822c90d results/geom_review/s81_head_spine_1025/): hd_spn + hd_spn_end 3_place (Codex 8a2a5db7a kits) = FAIL, no route/enqueue. OK: face_guard 6156/5024, pin->reg <=11.9 um, 6 ft slots x 6 stations straight (spread <=9.3, hops 343-349), reset relay tree 380.7. FAIL: (1) E/W bus stations xw_o/xe_o (566 b) and bw_i/be_i (51 b) are single points (kit_istations.py) while pins span 300 um -> first/last legs 463-521 um, 413/411 reg-reg hops > 405, xw/xe detour via N edge ~1.5x; hd_spn last x_o station -> S pin 397 (+12 next spine = 409). (2) default rst_n relay u_rrl_27 drives spo/spr ctl + internal-station epoch flops up to 2035 um (decision 2 breach). (3) clock taps uneven (t22 3938/2810 sinks, 8 W taps 2-8 sinks). (4) kits lack per-corner FF vclk and F2 RC. Fix (structural, 0 cycles): plan E/W bus bands straight at the pin-window rows, per-bit station sites like ft_bit_sites.tcl, every reset/epoch sink on its nearest tap relay, tap pruning, regenerate with FF vclk + F2 -> next head delta.
2026-10-25 05:12 PDT HEAD-ELEM2: s2 rebuild kits for the head elements (GEOM PASS-COND 04:49/04:50, all three conds in one rebuild) on claude/s81-head-elem-1025@358b997a5a (pushed; record results/geom_review/s81_head_elem2_1025/record.json). Kits epyc1:/srv/opentallas-scratch2/claude/s81-head-elem/kits/{elemB_rb_s2_c60,elemB_rb_s2_c50,elemA_rb_s2_c50,elemA_rb_s2_c60}: shared rc_fit.tcl (HBM-CORES 4b722d3388 + OT_GRT_ARGS) fits B C x0.6 (mean -3.1/p95 7.7 ps), A C x0.5 (+2.0/5.8) -> LAYER_PARASITICS_FILE (SET_RC_TCL is inert in orfs:asap7lock); vclk -max 250 / -min FF pin-reg I (B 170, A 155) = head form of 9.7/5e for CLOCK to confirm; post_cts_gate_s2 route gate (FF hold >= 0, B t_r->w_r med <=20 none >100; pair INFO pre-route, gated by main signoff.py+pair_skew.tcl); B ROMs MY. GEOM REQ [S81-HEAD/HEAD-ELEM2 s2] posted. AUTOPILOT queued (--geom REQ, --mem 32, goal route): hd_elemB_rb__s2_c60 25ae35a9d6fa, hd_elemB_rb__s2_c50 67a42b6e388a, hd_elemA_rb__s2_c50 5d294ac98549, hd_elemA_rb__s2_c60 5426d061a44f. s1 kits deleted (superseded, never launched). Probes (read-only, done): epyc3/intel1 /srv/opentallas-scratch2/claude/s81-head-elem2/. OWNER?: none.
2026-10-25 05:18 PDT S81-HEAD -> HBM-CORES/CLOCK/NEARMISS-STRUCT/QC-CQB2 (F2 cross-lane): the orfs:asap7lock image never reads SET_RC_TCL, so a kit SET_RC_TCL = fitted setRC (HBM argmax struct_rc0665/0700 recipe) changes NOTHING; the image reads LAYER_PARASITICS_FILE in every stage -> point that at the fitted file (head elem s2 kits do: claude/s81-head-elem-1025@358b997a5a). Also rc_fit.tcl's own global_route must match the flow's resistance-aware GRT (added opt OT_GRT_ARGS there), else the fit is off by +87/+132 ps vs the flow's +36/+68. Head fits (C-only, FF, vs RCX per sink): elemB C x0.6 mean -3.1/p95 7.7, elemA C x0.5 +2.0/5.8; R scaling makes it worse (error is in C).
