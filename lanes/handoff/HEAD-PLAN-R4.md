# HEAD-PLAN-R4 handoff (Opus), successor of HEAD-R3 (Fable). s81_head ASAP7 833 ps. Started 2026-11-17 ~07:30 PST.
Read lanes/handoff/HEAD-R3.md for the NF15e -> NF15f decision (hop halving + corridor +181.44, die 17737.92).

## (1) u_lep RX-head rank RTL (RXH)
- Branch claude/head-lep-rxh-rank-1117, worktree epyc9 /srv/opentallas-scratch2/claude/head-plan-r4/wt (ot-lane-clone, cone tools rtl
  + physical/die_plan/s81/bind/source_modules/portfix178).
- Generator tools/s81_head/head_lep_nr_sources.py: opt-in core param RXH (default 0). RXH 0: g_rxm reads *_h aliases (no flop,
  no added cycle). RXH 1: kept leaves u_core.u.u_lep.u.g_rxh.g_l[0..3].u_st (552 data FF each = 2,208) + g_rxh.u_ctl (44 control
  FF on rnx): rhd + every ring-side term of g_rxm (rne/relp/rpb, ring_meta_regions, rhk, look-ahead rnex/rringx/rhkx/rtagx,
  rne_return) delayed one edge; ri / mu_rt / ml_w all +1 together; replay ml_rd/ml_rv, pops, credits, perr unchanged.
- ot_s81hd_lep0N_core / noidx_core: RXH param pass-through. lep_calendar: Stages.rxh (0/1), leg 'rx_head.ri+mu_rt+ml_w',
  state bits +2,252, params() adds RXH only when 1 (old tuples byte-same), NF15F constant. check_calendar PASS.
- Bench tb_head_lepk_stages + head_lepk_stages_bench.sh: RXH_DUT, cases nf15f / nf15f_norxh / rxh_only, mutants
  MUT_RXHBIT / MUT_RXHSKEW (must FAIL). Runs: epyc9 head-plan-r4/b_<case>, bench1 (plan zero mut_dbit). Default equiv
  (RXH 0 vs main) head-plan-r4/equiv0.
- Die LATCHECK unaffected (provider leg inside hd_lep0N; external lane fixed_cycles unchanged).
- RESULTS: RXH 0 default equivalence vs main PASS (yosys equiv_induct, E9 unit oth-ubuntu-4014994-1794927585, equiv0/out).

## (2) NF15f geometry event g1 (E10 /srv/opentallas-scratch2/claude/head-die-r/nf15e_e10/hr4)
- code_r4 = private copy of nf15e_e10/code (tools real copy; rtl now a REAL copy of the kw45 src rtl, old symlink renamed
  rtl.kw45link) + RXH files. kw45 src tree untouched (read-only, write was refused).
- compose_g1.py on prep_f1 (3210bf1f): type cut y>=665.28 +181.44 (415 coords; 2 W/E collector bands stretched), outline
  1892.16 x 1408.32, upper pair cores at 846.72; model corridor-word groups (rxbank/txread/rop, krx1 re-site) in the
  allocator frame; chains renumbered with 28 REAL relay anchors at the allocator columns (max offset 60.48 um) + RXH
  lanes/ctl; RXH 1. Parent: die 17712 x 17737.92, 6 north hd_serdes + 6 PHY domains/bumps/IO + 3 channels +181.44,
  W/E full-height channels stretched, no overlap / outside. landing_remap (all types) re-picks reset relay names by site.
- run_g1.sh RUN: compose -> landing_remap -> republish (provider calendar nf15f_g1) -> receipt, kit RTL, strict bind,
  cohort, LATCHECK, G0.  run_alloc_g1.sh RUN: edges_g1.py splits every relayed hop at its real anchor, alloc_r4 (no
  virtual relays, band 490..851.44).
- g1/g1b failed in republish GEN (reset relay names renumbered: hd_lep0N, then hd_st_turn) -> g1c remaps all types.

## (3) 11-17 status (after g1c + a2)
- RXH benches: rxh_only PASS, mut_rxhbit / mut_rxhskew CAUGHT, plan (vF) PASS, RXH0 equiv vs main PASS.
- BLOCKER: the NF15f tuple (KTX 1111 KRX 2660 TXI 2442 PIN 6 POUT 8) fails tb_head_lepk_stages with and WITHOUT RXH:
  perr=1 at cyc 4053 phase 2, hang ri 1018/1040 lw 6/80.  The 3210bf1f gates never simulated the tuple.
  Bisect on E9 head-plan-r4/x_{dbg,krx,ktx,io} (bisect.sh): KRX-only / KTX-only / PIN+POUT+TXI-only.
- Geometry g1c (E10 hr4): compose/remap/republish/receipt/kit RTL PASS; G0 10 abutment errors (5 north hd_serdes not above
  lep0N moved +181.44).  compose_g1.py fixed: only the lep0N column moves (not yet rerun).  bind.log: --out must be
  repo-relative (run_g1.sh fixed).
- Corridor model: column-centre anchors 3244 unassigned / 8345 reach-bad; reach-optimal re-site (place_anchors.py,
  hr4/anchor_a2) 2387 unassigned / 3275 reach-bad (g_kl 1106, g_pin 1104, g_tx 1065), worst cut 1.17, krx3_r0 > 405 um.
  NOT < 90 % / 0 unassigned.
- Lever 7(a) relay access (vert_access.py, anchor_a2/relay_access.json): pin access 0.02-0.03, FF util 0.21-0.27 fine;
  vertical M5+M7 drops exceed 0.9 of supply at 22/27 anchors (worst pout_r4 2.19).  Anchors must be wider (span along x,
  h 12 -> w x2) or split per source column; growth alone does not fix it.
- Lever 7(b) uarch_model.s81_head_lep_nf15f_stage_calendar_model added (ring legs lane0..3 = 18/26/26/20 vs NF15e 9/13/13/10);
  production calendar rerun still owed.  7(c) die_clock.face_pin_keepouts (opt-in die.clock.face_pin_keepout_um) + 3 tests PASS.
- Branch not yet committed: wait for the tuple bisect (RTL may need a credit-depth change with the tuple).

## (4) 11-17 late: integration + credit root cause
- g1e (column-only growth + all-type republish), plan c291c4a4: compose/receipt/kit/bind/cohort/LATCHECK 329/329/G0 PASS.
- rs-series = g1e + r564 rows (old-clock) + strap_rst_ph sites, tree code_rs2 (main tools incl r564 + event rtl + RXH overlays):
  rs2 validate invocation (-I relative import), rs3 republish used code_r4 (old schema), rs4 code_rs2 rtl was a main snapshot
  (XO_HOP missing) -> rtl replaced by event rtl; rs5 running.  All harness, no gate finding.
- Tuple root cause: perr = pair A/B release collision; KRX lane 6 alone fails, KTX 1 alone fails, PIN/POUT/TXI pass; K-link
  credit depth 16 fails, 24 passes (ri/rt/lw exact, gap 4).  Isolation of which credit end (lep DR/CRED vs lane CORE_CRED;
  the lane CRED12 view is CLOSED) running x_c24k / x_c24L / x_c24kr (RXH 1).
- Evidence: ~/coord/lanes/evidence/head_plan_r4_1117/.

## (5) 11-17 afternoon: credit RTL gated, rs7 integrated
- Branch claude/head-lep-rxh-rank-1117 @3cc88ac6 GREEN 24/24 (main ba7a96a1), READY posted: RXH + KCRED (both ends, default 12)
  + LOCAL_POP(CORE_CRED>=12) + calendar kcred/credit_rtt (measured) + tb LEPK_RTT + bench cases + uarch entry + face keepout.
- Measured credit loop (LEPK_RTT, k12 credit-bound): RX 14/24/24/21, TX <= 17 -> KCRED 28.  Isolation: lep+lane 24 / peer 12
  PASS (peer type unchanged); lep-only 24 FAIL (pair CORE_CRED binding) -> HEAD-TYPES-R4 rebuild + re-sign ot_s81hd_lep_pair.
- rs7 (plan 10e41a91ec8c73d7, epyc9 hr4/prep_rs7): main be66cd6f tools (r564 + r588) + event rtl + RXH + KCRED 28 (contents AND
  native_stage_groups params) + r564 rows (OLD-clock labels) + grid straps 10.016 / 566.752: compose, receipt, kit RTL
  hd_lep0N + hd_tile, bind, cohort 26/26, LATCHECK 329/329, G0 0 errors all PASS; r588 kit-common files staged in kits.
- Open: relay rects = g1e (stage-vs-macro 4, groups over reserved sites 32) -> FABLE-FIX-HEAD-CORRIDOR (g2 it3 seed);
  labels + strap values from the NF15f clock census after the clock GEN; mesh PG knobs + north clock re-site in that GEN;
  reset seam timing after the census; production token calendar rerun on NF15F; no kits until the corridor fix lands.
- Harness lessons: one attempt per run dir; run_rs6.sh is the current runner (code_rs6); republish_g1.py takes HR4_CODE.

## (6) 11-17 evening: corridor prefix map withdrawn, tag map adopted
- My "corridor capacity shortfall" is WITHDRAWN. It came from hr4/edges_g1.py, which mapped model stage groups to the composed plan by PREFIX; the NF15f chains are renumbered, so stages were sent onto relay rects (FABLE-FIX-HEAD-CORRIDOR 09:09 / 12:49).
- Fix: hr4/edges_g1.py now maps by TAG and exits 2 if any model rect fails to map uniquely (104/104 map). The old builder is kept as hr4/edges_g1_prefixmap_WRONG.py. This is a scratch event tool; no repo tool maps stage groups by prefix (grepped code_rs6/tools: landing_place.py and head_lep_nf15e_delta.py only validate prefixes), so no repo branch is needed.
- Rerun on rs7 source_plan 10e41a91 (hr4/rs7_tag/): edges are byte-identical to fable-fix-head-corridor/rec/edges_rs7_g3.json apart from the plan path string. alloc_r4 unchanged: 59,089 nets, unassigned 4,295, reach_bad 0, worst full-rect cut 0.903 at x=1180, mandatory 0.502 at x=980.
- Still open on rs7, all in the anchor form: 4,295 unassigned, cut 0.903 (just over 0.9), 4 stage-on-macro and 32 reserved-site rects (g1e column-centre relay rects).
- Next: when FABLE-FIX-HEAD-CORRIDOR posts the hybrid (unassigned 0), apply its apply_stage_rects.py onto rs7 source_plan, then rerun the rs6/rs7 pipeline (compose, strap, KCRED 28, republish, bind, cohort, LATCHECK, G0, keepout count = 0). Then the HEAD type kits. Kits stay held until then.
- 11-17 late (COORD r597): rs7 used main be66cd6f tools, which are from before r597 (tap escape). Staged hr4/code_rs8 = code_rs6 with tools/ from main 26f27e90 (contains e24301f0d9a; every code_rs6 tool overlay is byte-identical in main because the RXH/KCRED branch is merged; physical/common_flow unchanged). gen_phys.py tap_escape refs=6, on by default (per-site opt-out only); test_clksite_kit + test_die_clock_face_keepout 9 passed. New runner hr4/run_rs8.sh RUN HYB: code_rs8, PRECHECK exits 78 if gen_phys has no tap_escape, applies FABLE apply_stage_rects.py after the KCRED step, keepout must be 0 0. No rs8 launched until the hybrid rows land. HEAD kits (hd_lep0N, hd_mesh) only from code_rs8 or a later main.

## (7) 11-17 night: rs8b PASS, clock GEN PASS, apply next
- rs8b (hr4/run_rs8.sh rs8 hr4/in_rs8/c3_plan.json, code_rs8 = main 26f27e90 tools): plan prep_rs8/source_plan.json 65606a72 (= FABLE fc4). G0 0 errors / 0 pending / 220 warnings; bind PASS, nested unbound 0; cohort 26/26; LATCHECK 329/329; keepout 0 macro / 0 reserved. hd_lep0N SRAM u_m binds ot_sram_1r1w_512x128_m4_r0c0.
- The first rs8 launch was REFUSED by ot-run ISOLATION (input path outside --dir) and my log-grep watch missed it. Inputs are now staged in hr4/in_rs8/.
- ot_wait.py --unit X.scope reports FAILED ("collected, no exit status") for units that ot-run logs as exit 0. Seen twice; reported to WAVE-FLOW.
- Clock GEN: hr4/clock_rs8 (GEN3 feedrepair config of head-die-r/nf15e_clock unchanged except event name and paths; fresh GEN, no graft; code_rs8 ot_clk). Attempt 1 (tree/) failed in 3 s because the plan copy sat outside its dir and native_domains did not resolve. Attempt 2 (tree2/), input prep_rs8/source_plan_clock_input_65606a72.json: rc 0, stage_check PASS, 346 s; 44,509 clock cells; max packed reach 387.288 um, 0 over 405; max move 1.08 um; 13,122 taps (lep0N 195). Geometry only; no GRT/STA.
- Apply, next steps (tools/autopilot):
  1. Build the overlay: event rtl diff vs main, prep NF15f (prep_rs8 to physical/die_plan/s81_head/prep/NF15f/prep, tree2/kit to .../NF15f/die_clock).
  2. src_manifest.py build at main 26f27e90 into kw45/src_head_<sha>_nf15f.
  3. data_pack make for lane-folder inputs.
  4. publish, then replicate to epyc8 epyc9 epyc10 intel1, then verify on each host.
  5. kit_rtl smoke.
  6. Candidate JSON (template lanes/handoff/tree_switch_s81_head.json).
  7. publish_gate.py run (dry gen on the pilot).
  8. apply_reviewed_tree_marker.py --expect-source <NF15d2 tree> --expect-event head_rp21z20NF15d2r1.
  9. Release hd_lep0N and hd_mesh.

## (8) 11-18 night: NF15f APPLIED
- Live HEAD tree: /srv/opentallas-scratch2/claude/kw45/src_head_pin_8569788b0328_nf15f_d2, manifest 06dc1568, main 8569788b, event head_rp21z20NF15f, gen_hosts epyc9/epyc8/epyc10/intel1. Plan prep/NF15f/prep/source_plan.json de6c7105 (= rs8 65606a72 with tree paths renamed to _d2); receipt results/head_native_release_nf15f (digest 5108da57).
- How it was built: delta from NF15d2, hardlinked (tree_nf15f/mk_overlay.py, mk_pack.py, mk_pack_d2.py, build_tree2.sh, build_d2.sh). Overlay: HEAD prep/data carried; tools from main; XO_HOP rtl (tile, tile_native, tb_mini) kept because main lacks it. Intermediate trees _nf15f (link base, replicated) and _nf15f_d1 (contained FAIL, unused; retire via ot-delete when convenient).
- Gates on _d2: static schema/PRE/G0/hashes/contained PASS; strict bind PASS; cohort 26/26; LATCHECK 329/329; kit_rtl lep0N/mesh/serdes PASS; publish_gate run PASS incl. dry gen hd_lep0N (record autopilot/publish_gate/s81_head/06dc1568...json); tree_check guard ok/full_ok.
- Apply receipt lanes/handoff/s81_head_atomic_apply_1794965012010366819.json. Pilot record pilot-s81_head-06dc15683502: pilot_items [hd_lep0N, hd_mesh], release gen_pilot:s81_head:06dc15683502 (first gen pass releases the rest; gen only).
- Open:
  - real hd_lep0N GRT is the verdict on the 367 allocator nets (x 880-1160 / 1230-1472); post the gcell map if it overflows;
  - HEAD-TYPES-R4 rebuilds ot_s81hd_lep_pair at KCRED 28;
  - final r564 labels from the NF15f clock census;
  - reset-seam timing;
  - die STA on tree2;
  - XO_HOP rtl should be merged to main;
  - ot_wait .scope FAILED false negative (reported).

## (9) 11-17 17:2x-18:0x: Fable lever 3, lep_pair KCRED28, XO_HOP to main
- Fable hd_lep0N -3,897 ps / 76,299 hold cells: that kit is NF13a (epyc10 ot-jobs/hd_lep0N-route-civil-redfish-2363933-1794854605), not NF15d2r1. NF13a feeds landing faults straight into u_cland_up_coll_o* (0 stations). NF15d2r1/NF15f have 174 registered ot_dp_landing_collect stations on those chains, so no follow-on event is needed. Hold classes before repair (NF13a): cross_tap 25,840 ends -194.5, port_in 12,571 -83.6, port_out 3,235 -105.9, same_tap 418; +40 ps cross-tap pass added 21,737 cells. Next: compare the NF15f pilot pregrt_ff_hold class line and the 4_cts_final u_fault_port group.
- Pilot launch BLOCKED by LAUNCH-KEEP: the old NF13a hd_lep0N attempt 3 (kw-s81hea-hdlep0N-3-47709) and the NF15d2r1 hd_mesh row bb7589f7825a0 still run; asked COORD/WAVE-FLOW-R2 to reap them.
- lep_pair KCRED28 signed record s81_head/ot_s81hd_lep_pair__kcred28_hei3_1117 is 388.8x432 (other pin geometry, same 2,144 names), and the NF15f core is 777.6x492.48 (vE). It can't be bound without a reshape; HEAD-TYPES-R4 is asked to re-sign in the vE form.
- XO_HOP: claude/head-xo-hop-1117 @6932d71e443 (tile, tile_native, tb + tools/s81_head/tests/test_hd_tile_xo_hop.py), GATE main=41129805aac pass=2/2. Bench evidence: epyc9 /srv/opentallas-scratch2/claude/head-plan-r4/xoh_bench.
- Superseded trees posted for FLEET-OPS-R (24 h): kw45 ..._nf15f (all 4 hosts, the _d2 link base) and ..._nf15f_d1 (epyc9).

## (10) 11-17 19:0x-23:xx: tools refresh, KIT_NOT_SELF_CONTAINED, HPWL, pilot release, band capacity
- Live HEAD tree: kw45/src_head_pin_8569788b0328_nf15f_d2_t86a9d26_d1_t58211f4_t30393b4 (manifest cb7690ed7003; tools from main incl r668/r669/r670; plan de6c7105 unchanged). kit_wave dies.s81_head: tools_refresh true + HEAD bind cmd (head_die_portbind, pass regex), OT_SIGNED_VIEW_SHA in-tree, OT_GPL_HPWL_RATIO "0", gen_hosts epyc9/intel1. Pilot record released at f7705695 on the hd_mesh gen pass (RESULT corrects in 6aea7354).
- KIT_NOT_SELF_CONTAINED fixed in the tree: _d1 carries physical/die_plan/s81_head/kit_wave/signed_view_sha_head.json (kit-ops-6 table, md5 8e2571...). hd_tile PLACE-HPWL: s81 ratio leaked to s81_head by prefix; main fix claude/gpl-hpwl-s81-exact-1117 (r670, merged). XO_HOP merged (r642).
- 22:39 hd_lep0N + hd_tile relaunched on t30393b4 (units kw-s81hea-hdlep0N-4-83983, kw-s81hea-hdtile-2-83972). FABLE-FIX-HEAD-LEP0N / HEAD-LEP0N-OPUS own the hd_lep0N build.
- Band capacity (COORD 11-17): epyc9 head-plan-r4/bandfill. fill_plan.json = all 385 landing rects (217 native stage groups + ring/reader/status/reset) from the p2 synth netlist; 16 over 0.7, 1 over 1.0 (reader-start:lepk_i0 stage 3, 37 FF in 4.32 box). Static fill under-reads shared bands vs the lane sequential dry pass (wdq_bank3 0.707 vs 1.09), so wdq_bank3 is grown in x to [976.40 510.62 1145.80 514.62] (y growth hits SRAM te.u_m.g_bank[0] at 518.4); inside corridor x 880-1160.
  - plan_grown2.json = de6c7105 + 11 stage rects (14 entries) + reader box_um (lepk_i0 s3 7.56 sq, coll_i0..3 s3 5.4 sq); G0 on it: 0 band findings. Tools: band_grow.py, set_box.py.
  - Main branch claude/band-capacity-g0-1117 @e6fd00ab88a: tools/die_plan/band_capacity.py (measure + G0 check on all dies, WARN >0.7 / ERROR >1.0, sidecar PLANDIR/band_fill/<type>.json), stage box_um opt-in in schema + landing_place. Gate log epyc9 head-plan-r4/logs/gate_bandcap.log.
  - NEXT: READY + merge -> HEAD tools_refresh -> one plan revision (pack plan_grown2 as source_plan.json, indent 1 + newline; sidecar prep/NF15f/prep/band_fill/hd_lep0N.json; receipt, bind, cohort, LATCHECK, G0, publish_gate, apply), with the vE KCRED28 lep_pair views + 4 pair tap offsets from its clock_contract (mean ~586 ps) if signed by then.
