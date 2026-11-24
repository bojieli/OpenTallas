# S81-LEPW-CHAN handoff (Opus 5.5, fresh lane 11-24 08:2x PST). Row LEPW-MUC-CAPXR -> S81-ALLFIX-INT. (SLICE dead, no draft existed.)
Job: dsdv_slice_lepw_mu_C__t1 CBC route-demand pinch; row on c9 048fa468f0a2; PRE + scoped strict; ROW-REBASED; private rep kit to sign-off.
## Measured
- CBC-ROUTE-DEMAND-1124 12.80 was on J8 plan_h2_2249 (outline 1442.88, u_cap|u_xr channel 17.28). c9 type: outline 1512, channel 69.12 (u_cap x..371.52, u_xr 440.64..) -> peak already 4.39 (1025 hot). Type is IDENTICAL in c8 9b25d6714339 and c9.
- Cause left on c9: 5 wide lane chains (leafdn_o0/o1 597b, leafup_i0/i1/i2 668b) all sited in one x~376-396 column y 30-1180.
- Row: re-site regs_um of those 5 into separate lanes (channel lane -> west column lane x 245..455 -> staggered east turn y 950-1110), same count, 0 cycles, max hop 390.1 (was 382), no reg in core+4.32 halo. est peak 4.39 -> 2.96 (614 hot), in passing range.
- Ops: intel2 /srv/opentallas-scratch2/claude/s81-lepw-chan/row/LEPW-MUC-CAPXR-ops.json 744777435579 (10 replace ops, old values); copy epyc9 s81-lepw-chan/in/. Tools: lanes.py (search), mkops.py, rd.py (estimator w/ station_bits fill as KITROW-GAPS).
## Running
- epyc9 s81-lepw-chan/row.sh (compose -> relay/LLR/fill tail -> anchor/PRE/PRE-base/G0/census, rt 515889f6ef75), log row.otrun.log, out/ ; was load-capped waiting at 08:5x.
## Next
- PRE pass -> ROW-REBASED to INT. Scoped strict: no c9 elab yet; plan = c8 elab allfix_c8_out (7.4G copy into my dir after c8 strict ends ~11:00) + c8+row plan, bind --strict --all-gaps --types dsdv_slice_lepw_mu_C__t1; same bind out feeds the private kit (kit_wave private-spec --bind-out, goal route).
## 13:5x ROW-REBASED posted (ed0bd02d)
- c9 row plan epyc9 s81-lepw-chan/out/p4_fill.json eeac27d5fc2e (= composed; tail no-op). PRE 36 findings = c9 base set exactly (0 new, none on type). G0 PASS 0 err; type warns = INT c9 G0.
- c8 variant out_c8/p4_fill.json 42e7cf18c581 (tail no-op). Its PRE (row_c8.otrun.log) was still running at 13:5x; supplementary only.
- Scoped strict (scope_c8.sh, copy of c8 elab in scope_c8/): rc1, 212 errors all base svc class (TIED 200, TYPE_DEFINE 11, TIED_TOTAL 1), 0 on the type; emitted .sv identical to allfix_c8_out; only istations.tcl sites moved.
- Overlay row/LEPW-MUC-CAPXR.overlay.json ca9597fd9d7d (base c8 canonical 28bd36bf), type_overlay check OK (rtl_projection EQ).
## Kit
- intel2 systemd unit s81lepwchan-kitwait runs ~/tmp/s81-lepw-chan/kit_after_c8s.sh: waits for INT C8S_DONE + c8s receipt for the type, then private-spec (c8seal_tree, plan c8, bind allfix_c8s_out, --overlay, rt 52c1a6417353, goal route) + INT specfix + run-item; posts KIT LAUNCHED. Logs ~/tmp/s81-lepw-chan/kit/. (Dry spec on allfix_c8_out refused BIND_STALE / rt mismatch, as INT found; c8s form is what INT uses.)
- INT's own c8s stream will also launch the type with base positions: side-by-side A/B.
## 13:5x COORD asks
- Watchers (intel2 systemd --user): s81lepwchan-kitwait (launch at C8S_DONE) -> s81lepwchan-grtwatch (~/tmp/s81-lepw-chan/kit_grt_watch.sh, log grt_watch.log; posts GRT verdict or KIT ENDED) ; s81lepwchan-stemwatch (posts stem draft PRE/G0).
- Stem draft LEPW-MUC-STEM: intel2 s81-lepw-chan/xrshift.py, ops 9a313610a780 (CAPXR + u_xr +86.4 + 15 sites). epyc9 row_stem.sh -> out_stem/. 180-um bank model (wide.py): stem 3.01 -> 1.51. Held; apply if kit GRT stem overflows. Needs type_overlay check before a kit (collector/reset-anchor keys may not be overlay-legal -> then plan row via INT).
- Estimator gap posted to LEAF-ROUTE-CBC.
## 14:0x COORD STEM-forward
- epyc9 stem_c8_chain.sh (out_stem_c8, scope_stem_c8, row/LEPW-MUC-STEM.overlay.json); row_stem.sh (out_stem, c9).
- intel2 units: stemrebased (auto ROW-REBASED), kitstemwait -> kit_stem_body.sh (kit #2, ~/tmp/s81-lepw-chan/kit_stem), grtwatchstem; control kit units kitwait/grtwatch; stemwatch (draft result post).
- If kit #2 overlay refused: build from composed plan tree (ot-tree-fork c8seal_tree + scoped bind out scope_stem_c8 as --bind-out).
## 14:0x COORD waiter+fallback
- epyc11 fork c8fork (fork.otrun.log). intel2 s81lepwchan-overlaywatch (overlay_watch.sh/.log): verdict post, PASS->ot-delete fork, REFUSED->fallback kit #2 (kit_stem_fb), then stemrebased check. s81lepwchan-grtwatchfb watches kit_stem_fb.
