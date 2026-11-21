# QC-PLAN-R11 handoff (11-21 11:2x to 13:5x PST; succeeds QC-PLAN-R10; successor QC-PLAN-R12). Read QC-PLAN-R10.md for the V2 apply recipe.

## Wave runtime (COORD ruling 1): DONE, nothing left to bump
- Kits run the scheduler rt/current at each launch (TOOLS-DECOUPLE, spec.json tools_rt). V2 launches recorded c2047d41ccdf and a13768301176.
  Both are >= aaa1dcff0349 (coll ring-path fix) and contain 3ed87c352a, 4f638b4e9f, f56d99cf55, 8d1cff9b1b and a0fc9811a19. a1376 also contains 289287760f and 3fba1b4bc0.
- dies.qwen_compute.tools_sha = 65f3f85d7c5f is the TREE-tools reference (tool_skew warn, apply marker), not the runtime. I bumped it (f656e319b7) and reverted it (a98671dde7)
  because the bump only produced 229-module skew-warn noise. The pin moves to the V3 bind rt with the V3 tree.
- Coll (FAM-QC-COLL-R2): the live V2 tree v2r10 carries ot_coll_tp8_static.sv 0943bafb45db (SRDREG only, pre-867126d928d), so it is NOT affected.
  The V3 bind uses the main ae660e1299 copy (14f815448b2c = aaa1dcff0349 content). No QC tree built in 867126d..aaa1dcff is live; FAM-QC-COLL-R2 rebuilt its private one.
## Units in flight (waiter commands)
- v3t TOOLS-ONLY control (epyc7 /srv/opentallas-scratch2/claude/qc-plan-r11, chain_v3t.sh pid 1857369, log chain_v3t.log): V2 plan 7f9f8260349f + bind rt 31c7ccbd1b93.
  Strict bind unit oth-ubuntu-1859342-1795292207: DONE, errors 0, LATCHECK 1921/1921 PASS. Post-bind G0 + census are running (ot-run on epyc7, out v3t/post_bind).
  Wait: timeout 3500 ssh -n -o ControlPath=none epyc7 'until grep -q CHAIN_DONE /srv/opentallas-scratch2/claude/qc-plan-r11/chain_v3t.log || ! pgrep -f "bash chain_v3t.sh" >/dev/null; do sleep 120; done; tail -45 /srv/opentallas-scratch2/claude/qc-plan-r11/chain_v3t.log'
  PASS mark: G0 0 errors, and the g0diff vs qc-plan-r9/b20/post_bind/g0 shows no new findings. Then rt 31c7ccbd1b93 is the V3 bind tools (it has a manifest; protect it by naming it).
- Sites helper QC-PLAN-R11-SITES (Claude subagent of R11; it dies with R11's session, so R12 takes the files): epyc7 qc-plan-r11/sites/{compose_sites.py, compose.log, ctl/, run_g0.sh, g0diff_all.py}.
  Its last ot-run units were oth-ubuntu-3018773-1795293987 and oth-ubuntu-1824140-1795294153 (G0). Goal: regs_um/bit sites off macros for site-less multi-station ft slots at UNCHANGED station counts
  (23 reverted hop300 slots first), with static G0 showing no new findings vs b20 and 0 lane changes in the latency regen. Deliverable: sites/plan_sites.json + sites_report.tsv. If they are absent, re-run compose_sites.py.
- Done reads (no unit live): sle_ctl a5 -440.70 path (epyc8 /srv/opentallas-scratch3/claude/QC-PLAN-R11/sc_read/sc_path.rpt), and the sle_ctl reset-hop census
  (same dir rst_hops.tcl/.tsv, unit oth-ubuntu-1824140-1795294153): 3,656 reset-tree nets, 0 driver->sink over 250 um on a5 3_place.odb (V1 plan). So NO sle_ctl reset stations (COORD item 2).
## V3 row inventory (base = V2 plan 7f9f8260349f; bind = qc-plan-r11/bind_v3b.sh, which adds the ASB_MERGE env hook for asbuilt rows; row cut 11-22 06:00 PST; apply >= 11-22 11:16)
| # (FABLE-PD-QC-1230 sec 2) | row | source | gate state |
|---|---|---|---|
| 1 | sle_ctl x_su_l0_i pad as parent-tied count strap (before ANY su-path station row) | QC-SLE-R5 (asked 12:22) | not written; nothing in yet |
| 2a | asbuilt land_pad_tail_split.r8_keep=true + plan budgets.r_r8_core_seat ["slw_st_a","sle_st_a"] | FABLE-FIX-QC-STRAP-R2; epyc7 qc-plan-r9/v3rows/r8_straps_rows.json R8S-1 | b1 strict 0 + LATCHECK 1921 (epyc8 FABLE-FIX-QC-STRAP-R2/b1); proof kit p1 cl9f076a5c in place on epyc8 -> PROVISIONAL until its CTS post-hook |
| 2b | st_a btab SRAM column X about 250 um north (window 149-370; not 345.6) + re-site ist 0/4/5 | FAM-QC-HCST-R2 (asked); R12 owns the item (ACK to STRAP-R2) | not written |
| 2c | slw_st_a_v2__clf4365a62 face-home = copy the cl9f076a5c floorplan (5 core moves) | lanes/handoff/FAM-QC-HCST-R2-row-clf4365a62.json be330101a1cf | ready, not bound; check its interaction with 2b |
| 3 | reach rows WITH sites (43 slots >405; 300 site-less slots) | sites helper + family lanes (st_b/hc2 HCST, fe/fw FEFW, coll_ftm COLL, cbx CB) | sites helper running; family rows not in |
| 4 | cell splits: 9 of 19 over 400k (qc-plan-r9/cells_census.tsv), 22 st_b/hc projected 465-548k; G0 estimate about 56k low | FLOW-STRIPBODY-1121 (asked for the schema/order) | not started |
| 5 | cb: cbf_q00 inst_taps STAY t24/t25/t93/t100 (t77/t76 withdrawn); stations bc_i00/10/30, nb_i12, y_o00 after CTS | FAM-QC-CB-R2 | waiting on its p1 CTS reads |
| 6 | stm reset inst_taps: cl7b3062fa {tap 79, [u_core]} 699->190 um; cl55be2264 {tap 51, [u_core]} 643->149 um, 0 cycles | epyc7 /srv/opentallas-scratch2/claude/opus-fix-qc-sle-r4-rows/stm/stm_rows.json (2b2dfe128b06 lineage) | ready (plan key reset.inst_taps), not bound |
| 6c | coll reset: NO reset stations. Only the 29 name-refresh rows lanes/handoff/FAM-QC-COLL-R2-rows_reset_v3.json d312dd10fe2f (+ reach fix14 clock rows on epyc10 fam-qc-coll) | FAM-QC-COLL-R2 | ready |
| 6s | sle_ctl reset: none needed (census above) | R11 | done |
| 8 | fw x_sc_i +1 station (slw_fw_v1 cl592e3d37, sle_fw_v2, slw_fw_v3, slw_fe_v1) WITH sites; the W su_c/sc E/W pad rule applies | FAM-QC-FEFW-R2 (asked for the file) | not in; su-path, so after row 1 |
| R8S-3 | sle_ctl rp chd_q banks: relay_sites at the rp mux toward the x_su_c station (the -440.7 is a 705 ps wire detour, mux only 131 ps) | R11 read | to write on the V3 geometry after row 1 |
| 11 | coll_core six defines + 2 face-codec stations | lanes/handoff/FAM-QC-COLL-R2-rows_bcd.json 57bf4be9d132 (needs coll RTL >= aaa1dcff, in bind_v3) | waiting for the FAM-QC-COLL-R2 pkit7 GO |
| 7,9,10 | clock reach fix --rules 4, tap splits, early tap depth; reverted-slot sites (in 3); W chains by distance (after 1) | R12 / family | open |
| E/W pad | W su_c/sc crossing slots: keep (su_l1 arrival - su_l0 st/landing) E == W (qc-plan-r9/r10_ctlpad.py) or bind TYPE_SPLITs sle_ctl | R10 note | rule for every su-path row |
Gate = V2 recipe: compose -> gen.py latency regen -> static G0 vs control -> strict bind (bind_v3b.sh, rt 31c7ccbd1b93) + LATCHECK -> post-bind G0 vs b20 -> census -> proof GENs -> pack/seal/apply (QC-PLAN-R10 11:0x).
Stop list = FABLE-PD-QC-1230 sec 3 (no station without a site, no 23 hop300 bumps, no su-path station before row 1, no r_r8_core_seat beyond st_a before proof, no 345.6 btab shift).
## Done
- R8 strap rows updated (R8S-T1 LANDED, R8S-2 parked), sle_ctl path read, R10 cleanup via ot-delete (epyc7 qc-plan-r9/b17,b18,b18r,b19; qc-plan-r8/v2b_host/b12,b13,b13dbg), lane clone epyc7 /srv/opentallas-scratch3/claude/QC-PLAN-R11/clone.
