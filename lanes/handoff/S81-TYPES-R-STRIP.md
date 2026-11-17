# S81-TYPES-R strip fork (strip leaves, bg_bare, t34 model, t43); started 11-16 17:1x PST

Parent lane S81-TYPES-R (columns + IFN0 are NOT here). Predecessor FABLE-FIX-S81-CONG.md (read its Codex handback section).

## bg_bare (DONE)
- Branch claude/s81-types-r-bgbare-1116 @11bfca8d9c9 (clone epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/lane). +9 lines in tools/die_plan/kit_bus_bitgroups.py, test_kit_bus_bare_alias.py (6 tests), fixture kit_bus_t34_current819.sv.gz.
- GATE main=34781ed8bbc pass=3/3 GREEN. READY posted (FABLE-FIX-S81-CONG post 266cbf08). COORD approval pending.
- leaf34 current819: IN 68/595 (VS 559..593, VN 0..32; soft VP captures 33..558 unresolved by design), OUT 667/668. t43 unchanged (IN 69, OUT 410 unprepared).
- Next immutable profile: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/code_2ef_11bfca8 (read-only; code_profile.json f0bd94f035a3, BG d13183d3083d, 24 tests pass). code_2ef_ac601 and the running constructor untouched.
- NOTE: on PREPARED bound RTL out_bit_owners resolves 0 for leafup_o0 (u_bout .d is the inserted u_ist station q). Owners must be taken on the unprepared text or traced through u_ist; not fixed here.

## Eight-leaf constructor (DONE 02:07 UTC, exit 0) + launches
- GEN_ONLY_OK x8 at E10 fable-fix-s81-cong/countable_F2s4tapfix1_eight/gen (run_kit.sh + flow_tag there). Replicated (rsync, 204 MB) to the same path on epyc7 / epyc8 / epyc9 / intel1.
- Images: intel2 ~/s81-types-r/review_eight/<t>.png (renderer kit_view.py + fetch.sh there). All LOOKED. 0 macro overlaps in all eight.
- Verdicts: t28, t34, t47, t62 PASS-COND (launched to sign-off); t75, t72 PASS-COND diagnostic (launched); t8 HOLD; t43 HOLD. Post fda8a225.
- t8 HOLD: plan edge_clocks fclk_in_ft0_i / fclk_in_ft1_i / fclk_in_cland_dn_1 tap_um x=1440.736 not moved with the 1598.40 outline (+155.52): taps inside vp_g_ln_4/11/13, 14 ring-on-macro overlaps. Needs the DIE-R row fix + regenerate; do NOT launch the current t8 kit.
- t43 HOLD: MAX1 bus cannot reach VS (rows posted); do NOT launch the current t43 kit.
- Launch form: intel2 `ot-run --mem 64 --threads 16 --disk 40 --hosts epyc7,epyc8,epyc9,intel1 --dir $G -- bash $G/run_kit.sh $G/<type> route 64 16` (G = the gen dir; --dir must be the gen dir, a kit --dir is REFUSED by ISOLATION step 3). Logs intel2 ~/s81-types-r/run_eight_<t>.log.
- SUPERSEDED by the 18:3x block below. Live at 18:2x PST: t28 client 850976 unit oth-ubuntu-2091121-1794881515, t34 client 853411 unit oth-ubuntu-2093685-1794881530, t47 client 856591 unit oth-ubuntu-2097861-1794881544, all on intel1 (floorplan). t62 client 857885, t75 client 861073, t72 client 865910 = queued waiters on intel1 (thread cap 108+16 > 112); they start by themselves.
- TODO: per kit read 4_1_cts.log taps, GRT overflow, reloaded-GRT TT setup / FF hold, then DRC / signoff.json; export SIGNED to AGIdock /archive/opentallas-signed-1114 + rtx-pro; classify failures (t34 expected class = VQ core-input, see below; t47 = START writer class).

## t34 VQ +43.2 Y (BLOCKED on bind, post 0e32d614)
- Rows: epyc10 fable-fix-s81-cong/t34_vq_current/{t34vq_rows.json,t34vq_report.json,resite_t34_vq.py,t34vq_review*.png}. VQ origin 527.04 -> 570.24, 21 VQ station rows rebuilt at the SAME depth (0 FF, 0 cycles), max per-bit hop 394.8 um, 0 station / FT / tap collisions. Image LOOKED PASS-COND (VQ.u -> VS station sits above VS at (248,625); wire overflies VSW M5).
- Kit GEN: intel2 client 283901, E10 unit oth-ubuntu-2192800-1794878457, log intel2 ~/s81-types-r/gen_t34vq.log, script E10 fable-fix-s81-cong/gen_t34vq.sh, out fable-fix-s81-cong/t34vq_F2s4tapfix1 (private plan 7c84f6d385b5 = 819 + t34 rows; profile code_2ef_11bfca8; --max-wire-um 405 instead of the 100 um advisory pitch).
- TODO: review kit image, stage off E10, run to GRT (run_kit.sh ... grt), read GRT overflow + reloaded-GRT TT setup / FF hold, post typed row to S81-DIE-R. The 256-FF / 336-clone packing is NOT forced in this kit (placer decides); if the x_qd / VQ input class still fails at GRT, add the pack as a placement seed.

### t34 attempt 1 FAILED at GEN (17:3x), cause measured
- gen phys: "physical collector_tree differs from captured bound reset identity". Bound reset relay u_rrl_117 (kind wire, depth 3) sits at (574.32, 669.32) = under the new VQ footprint (y 570.24..699.84). The row is therefore NOT RTL-neutral: the reset tree re-solved on the private plan has 263 relays (bound 267), n_tree 130 (128), 162 relay edges renumbered, depth 6 = 6 (reset latency unchanged). Diff: epyc10 fable-fix-s81-cong/t34_vq_current/t34vq_reset_resolve_diff.json.
- So VQ +43.2 = 0 data FF / 0 cycles, but -4 reset relay FF and a new reset RTL emission: it needs a bind (S81-DIE-R event), not a row-only carry. No receipt was edited, no gen patch.
- Attempt 2 (r2, FAILED exit 4 KIT_TOPOLOGY_BIND_STALE; kit-rtl still carried the bound 267-relay tree): kit-rtl + prepare-stations on the PRIVATE plan (type-local emission with the re-solved tree), then gen. intel2 log ~/s81-types-r/gen_t34vq_r2.log, E10 unit oth-ubuntu-2447808-1794879298, out fable-fix-s81-cong/t34vq_F2s4tapfix1_r2, script gen_t34vq_r2.sh. If kit-rtl refuses a plan that differs from the bind, the proof kit must wait for the DIE-R bind.

## t43 (ROWS POSTED 17:4x, post 59ad5785)
- Full-width result: both buses need MAX2 (VS.g L1 1003.5..1015.1, VS.e 965.9..999.7): +1265 FF, dn +1, up +1. 15 typed rows, hop bound max 390.1 um, 0 M7 hits. No core moves.
- Files epyc7 + epyc10 fable-fix-s81-cong/t43v_current/t43_fullwidth_{rows,report}.json, t43_fullwidth_review.png, t43_rows_audit.py. Old drafts with mission_cycle_delta 0 superseded.
- Open: S81-DIE-R must regenerate source at MAX2 and bind. Zero-cycle alternative = VS/VE re-floor (not built).

## 18:3x PST after COORD ruling (bgbare approved r392; DIE-R folds t34 + t43 rows; t8 must be fixed; follow six leaves)
- Six leaves RUNNING (ot-run 64 GB / 16 thr, goal route = to sign-off), logs intel2 ~/s81-types-r/run_eight_<t>.log:
  - intel1: t28 client 850976 unit oth-ubuntu-2091121-1794881515; t34 client 853411 unit oth-ubuntu-2093685-1794881530; t47 client 856591 unit oth-ubuntu-2097861-1794881544.
  - epyc7: t62 client 941066 unit oth-ubuntu-920741-1794881978; t75 client 944226 unit oth-ubuntu-927383-1794882003; t72 client 948373 unit oth-ubuntu-932069-1794882028 (the three queued intel1 clients 857885 / 861073 / 865910 were stopped unadmitted after a PID + cmdline check and relaunched on epyc7,epyc8,epyc9).
  - Watcher: intel2 ~/s81-types-r/leafwatch.sh (prints stage changes / FAIL / exit). Read helper for CTS / GRT: epyc7 fable-fix-s81-coltap/an/stage_sta.sh KIT OUT cts|grt (+ stage_ffh.sh).
  - Per leaf TODO: place image LOOK, relay_mid check (grep OT_HOOK_COVERAGE hook=relay_mid in the place log: default OT_RELAY_MID_RE misses underscore-joined relay names), CTS read, GRT read (TT >= -42 reloaded GRT DB, overflow 0), route DRC 0 / TT >= -42 / internal FF hold >= 0, export.
- t8 fix ROW posted (post ad8c8cd9): 3 edge-clock taps + 23 landing pins x 1440.736 -> 1596.256, bands ft0_i / ft1_i / monitor_1 = one legal rect each in the east strip. Files E10 fable-fix-s81-cong/t8_tapfix/. Proof-kit GEN (private plan + private sidecar, profile code_2ef_11bfca8): intel2 log ~/s81-types-r/gen_t8fix.log, E10 unit oth-ubuntu-3290180-1794882228, out fable-fix-s81-cong/t8fix_F2s4tapfix1. If GEN passes: image review (kit_view.py), replicate, launch; it is evidence until DIE-R binds the row.
- t34 / t43: wait for the DIE-R event bind, then regenerate both on it with profile code_2ef_11bfca8 (t34 with --max-wire-um 405) and prove t34 to GRT.

## 19:4x PST six leaves + t8fix: CTS reads all FAIL (structural, VP family) - post f8aa92d9
- Live: t28/t34/t47 intel1 (clients 850976/853411/856591), t62/t75/t72 epyc7 (941066/944226/948373), t8fix epyc7 unit oth-ubuntu-1132984-1794883228 (log intel2 ~/s81-types-r/run_t8fix.log; kit E10+e7/8/9/intel1 fable-fix-s81-cong/t8fix_F2s4tapfix1/gen). Watcher intel2 ~/s81-types-r/leafwatch2.sh.
- Place LOOK PASS-COND t28 t34 t47 t62 t8fix (renders: an_place/dump.tcl + render.py on intel1/epyc7 fable-fix-s81-cong/an_place; DPL 0 overlaps). relay_mid expected=0 is correct: no u_y_ names in any leaf netlist.
- CTS read (fable-fix-s81-coltap/an/stage_sta.sh, cap x1.45): t28 -577/926, t34 -758/939, t47 -3956/15893, t62 -548/1067, t75 -1454/10091. Outputs an_place/sta/<t>_cts/setup_paths.tsv (intel1: t28 t34 t47; epyc7: t62 t75).
- Class: ot_s81sl_vpw (VP WRP=1 write unit) decodes RAW x_wv/x_wa/x_wm (VS via cst_vsp, depth 0) + sw_* (leafdn pad) into wa_q/wdo_q; placer puts vpw among the lanes, far from VS. t34 floor puts VS at x=78 west of VSW (t47/t62 VS x~450-467). Also hig cst_gd -> ln rN/y, VP driver internal dswp->hw_d, VP u_rr rst_n -> ln, t47 ft_o last station -> port (wl 2538).
- Next: reloaded-GRT reads (stage_sta.sh grt) per leaf; Fable PD review of the VP soft-logic family requested; structure candidate = vpw decode+flops at the source, long hop wdo_q -> lane pins; +1 on x_w + x_wd together if needed (needs DIE-R bind + LATCHECK).

## CODEX parked 2026-11-16 19:5x PST (Claude returned)
- No fleet jobs launched/cancelled. Published D3 unchanged. WIP E8 `/srv/opentallas-scratch2/claude/fable-fix-s81-cong/strip_xr_1116`: overlay VP + generic slice + portfix178 slice; builder `../build_overlay.py`, bench `../tb_vpw_xr.sv`. VP SHA956d17ec4536a79c124d408593fd2d9eddcd898e2a299074b25ff894cf3cd199 from D3 SHA2488b31c. Not committed to OpenTallas branch, not adopted.
- VP XR opt-in stages all write requests/payloads (+907 FF), effective CS_HI_D+1 local (shared unchanged), reset TREE_STAGES1->2. Smallest write-port sim PASS9951 checks /33 reset edges, XR0 identical to D3; mutant XR bypass fails cycle5. Initial bench used asynchronous xwd incorrectly and failed cycle7; corrected bench models the actual parent xwd_c pin flop. Full VP arithmetic behavior/physical result UNMEASURED. Syntax parse with missing modules ignored PASS only.
- IMPORTANT: bound kits preserve ot_s81sl_vpw but flatten VP HI/reset. Swapping VP source into old kit alone does not test form B; fresh elab/bind mandatory. Per-leaf VP_XR/LF_VP_XR masks added only to generic slice and portfix178 slice; actual active wrappers still need forwarding. t34 source chain: cap_end/ot_s81sl_slice_w3.sv iq_w3 -> slice_w3 -> lf[3]. t62: landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w_w3.sv -> lp_w3 -> u_lf1. Forward LF_VP_XR parallel existing LF_CS_HI_D. DO NOT also increment LF_CS_HI_D when XR adds effective depth, or HI becomes +2.
- Census `affected.json`: 75 ordinary leaf types/75 parts, 291 touching lanes. Global macro would change all; per-leaf masks required for B34/B62. Touching-lane list is semantic mapping only, not blanket +1 feedthrough pricing. `model.json` captures write+1/HC post+1/reset+1 with read timing unchanged; closure UNMEASURED.

## 20:3x PST Claude resumed; FABLE-PD-S81-STRIP levers (lanes/FABLE-PD-S81-STRIP.md) - post 260f1a11
- STOPPED via ot-heavy-stop (Fable stop list, no route): t47 oth-ubuntu-2097861-1794881544 (intel1), t75 oth-ubuntu-927383-1794882003 + t8fix oth-ubuntu-1132984-1794883228 (epyc7). t28/t34/t62/t72 still running to their GRT read; local stopper (scratchpad stopper.sh, systemctl --user) stops each after its GRT read.
- Fix 1 PLACE-HPWL gate: branch claude/s81-gpl-hpwl-gate-1116@588ce8106e6 GREEN 69/69 (worktree epyc8 fable-fix-s81-cong/wt_hpwl). gp_noconverge.py --hpwl-gate + gp_noconverge_gate.tcl block (OT_GPL_HPWL_RATIO) + gen_phys.gpl_hpwl_ratio (1.3 on s81 only). OpenROAD check: t47 STOP 2.35x, t34 OK 1.047x. NOT merged: needs COORD approval.
- Fix 1 pilot: place-only copies intel1/epyc7 fable-fix-s81-cong/gpl_pilot/{t47_keep0,t47_tdoff,t47_d065,t75_keep0,t75_tdoff} (setup gpl_pilot/gate/gpl_pilot_setup.sh; GPL from the kit's 3_2, then resize with the gate, then DPL, then HPWL reads). Logs intel2 ~/s81-types-r/gplpilot_<v>.log. keep0 = GPL_KEEP_OVERFLOW 0, tdoff = GPL_TIMING_DRIVEN 0, d065 = PLACE_DENSITY 0.65. Pick: lowest exit/min ratio that passes 1.3; then CTS read on its 3_5 before adopting.
- Fix 2 form B: XR branch claude/s81-strip-vp-xr-1116@d1645b7afcd GREEN (worktree epyc8 fable-fix-s81-cong/wt_xr). Tool tools/die_plan/s81_vp_xr_overlay.py ROOT --die 3S=01000 --die 6N=00010 on a WRP source tree (D3). S81-DIE-R2 binds it (latency post 455558d5). After the bind: t34/t62 kits get a bank-end region (vpw + XR flops at u_b0/u_b1), image review, GRT read. No form B for t47/t75/t8 until fix 1 is in.
- Fix 3 dswp: DSR (16 kept dswp copies, active with XR) added to the overlay in scratchpad + wt_xr (uncommitted until the iverilog elaboration of XR=0/1 with the D3 deps passes).
- t47 polarity: claude/s81-ft-port-polarity-1116@d7f31e5f8cd (gen_phys _ft_polarity_local opt-in + test_ft_polarity_local.py, merged origin/main) re-gating, log intel2 ~/s81-types-r/gate_ftpol_d7f31e5.log. Fable: no station move needed.

## 01:05 PST 11-17 (strip fork, Opus)
- DONE: XR-aware source depth READY claude/s81-strip-xr-lfcs-1117@baceba7b51a457dcaf5629c1ae57af49051c80b3, GREEN 69/69 (post 2470a35c). Completes Codex WIP bbd0da4c1ba.
  `--vp-xr TYPE:1` stages source HI_D = plan HI - 1 (plan 3 -> 2 / GS 2). The LF_VP_XR mask is checked against the contracts on every run, so the old path on an XR netlist refuses.
  Worktree: E8 fable-fix-s81-cong/wt_xr (now on that branch).
- DONE: C4 relay rows sent to S81-DIE-R2 (post 1f13b807).
  START legs: reach_rules fix --rules 1 on the d5c canonical plan; rows in E10 /srv/opentallas-scratch2/claude/s81-types-r-strip/c4_relay_rows/c4_start_relay_rows.json (7965c83abd01).
  t47 reader/writer depth 9/9 (worst hop 302.8/334.7); t75 6/5 (282.2/329.9); 0 data cycles; idempotent.
  Die reset -> FSTART: fstart_reset_delta.py on DIE-R2's C4 strict bind (it needs a bind dir; it cannot be pre-made).
- 78c5645 (-overflow 0.2) is withdrawn; the setting of record is r496 056783ac187.
- Stopped by exact ot-heavy-stop: t28 (intel1), t62 and t72 (epyc7, all inactive). t34 is kept and was at extra iteration 29/30 at 01:04; grtread2 reads it at FX DONE, then stopper2 stops it.
- Leftover: E8 fable-fix-s81-cong/clone_depth is a partial clone (timed out, unused); delete via ot_delete_guard.
## Next
1. t34 GRT class table at route RC, posted (vpw / VP driver / reset shares) before C4 seals.
2. After C4: generate t34/t62 from the tree with 056783ac187 + OT_S81_VPW_BANK=1; image review; GRT; TT >= -42 and internal FF hold >= 0; route; sign-off; export to both archives.

## 02:0x PST 11-17
- C4 START rows v2 (rst_n_t same-edge raws) dd78ad986cf9 to S81-DIE-R2 (post e9c6bf60); v1 rr_t rows superseded.
- READY R-REACH-5 edge rule claude/s81-reach-edge-rule-1117@1f0f757a622. Reset-tree half-cycle hops over 180 um (t47 156, t75 121, t37 97) reported to COORD/FABLE, not fixed by me.
- Own scratch to retire: E10 s81-types-r-strip/c4_relay_rows/tools_overlay (copy of d5c tools), E8 fable-fix-s81-cong/clone_depth.

## CODEX resumed 2026-11-17 04:2x PST
- Collected t34 terminal GRT-0116 FAIL at01:27, congestion3516(M6=2199,M8=1254), failedDB only. Reviewed actual grt/congestion.png: west seam x33..35 besideVE and VN/VQ channels hot; 2232saturatedgcells. No same-input retry. FailedDB route-RC diagnostic unit2196103-1794917050 terminalEST-0005(no usableGRTparasitics), so timing NOTMEASURED. All older t28/t62/t72 already stopped by predecessor.
- Complete30file FormB source overlay BUILT against exactD5c and DELIVERED E10 `/srv/opentallas-scratch2/claude/s81-types-r-strip/formB_c4_packet1117` (E8 origin cong/formB_c4_packet1117). `source_packet.json` SHA d99fdbb7ec8ccd832e240feb9bb75fa45b2ff8b468fd09232313981d0392c99a; overlay/ + tools_overlay/. Mask3S01000(t34L3)/6N00010(t62L1), XR+DSR16+CFR+16resetcopies. CurrentLFCSsourceHI2/GS2 preserved, actualeffectiveHI3. HIrows worker owns missingplanthirdHIrows (C4R2b stillHI2). FreshfullsourceELAB then strictbind/LATCHECK required, no partialbind credit.
- Sourceprice: existing fullshape B34/B62 v3 vsbase_v3 measured+5018RTLFF=(907XR+15DSR+4096HI), hardcores27unchanged. Currentpacket additionallyCFR5/reset32; freshfullshape totalpending. Writeavailability+1/hcpost+1/boot+1; read/laneIOunchanged. No blankettouchinglane+1. CarryGPL056783ac187 and OT_S81_VPW_BANK=1/e1b62d6096a for physicalpilot.
- Sourceoverlay has expected-beforehashes; do notoverwrite J6c-modifieddiefiles withwholeD5cfiles: rerunoverlayhelperafterotherdeltas. Failedfirstapply copiedreadonlymodes preservedapply.log, ownedcopyfixed only thenapply_r2.logsuccess; publishedtree/activekit untouched.
