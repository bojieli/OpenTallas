# HEAD-TYPES-R2 handoff (Opus, successor of HEAD-TYPES-R/Fable), 11-16 18:5x PST
Logs: intel2 ~/head-types-r2-logs/. Children: HEAD-HE12H-DRC (handoff HEAD-HE12H-DRC.md), HEAD-SD9A (HEAD-SD9A.md).
- eco_hw4 (hd_host_w): E10 .../fable-fix-head-types/eco_hw4/i1t routed, DRC 0, finish rc 0, no sign-off had run (post_runner -). Sign-off launched via ot-run (--dir i1t, only E10 has it): out i1t/signoff_r2, log i1t/signoff_r2.log, client ~/head-types-r2-logs/eco_hw4_signoff.log. NEXT: verdict, LOOK final_*.webp, export.
- he12h (hd_host_e): DRT ended 64 iter with 60 DRC (M6 at u_epc W edge x=423, M7 y~60, M2 W-edge clk_t7/t8 tb0 + relay nets). run_drt.sh continues finish/signoff. Owned by child HEAD-HE12H-DRC (also touches ~/fleet-ops-r-e9post.stop on sign-off).
- sd9A (hd_serdes): GRT exit 6 FAIL_POSTCTS SETUP_TRIAGE TT -189.6 after repair (worst start_o_0/rst_o_0). Owned by child HEAD-SD9A.
- hw5 (hd_host_w): epyc8 GRT goal still running (unit oth-ubuntu-3191148-1794878585). NEXT as HEAD-TYPES-R.md.
- SPEPRD3 (hd_spn_end): epyc8 DRT running (unit oth-ubuntu-3251096-1794878769), OT_PRD_POST=1 auto sign-off. NEXT as HEAD-TYPES-R.md.
- TP2 (hd_tile): tp2 tree replicated E10->E7/E8/E9 same path; launched run_kit.sh route 96/16 via ot-run --dir tp2 -> epyc7 unit oth-ubuntu-1157129-1794883329, client ~/head-types-r2-logs/tp2.log. (first try refused: run_kit.sh outside --dir.)

## STATE 11-16 20:0x PST (after Codex 19:42-19:51 cover)
- SIGNED+exported: hd_spn_end SPEPRD3 (s81_head/hd_spn_end__nf15_speprd3_1116; exported V has 566 cyclic output aliases -> child HEAD-SPE-EXPORT fixes exporter + fail-closed seam checker on claude/head-speprd3-export-1116, re-exports as a new entry, then NF15c real-view integration). he12h v2 SIGNED+exported s81_head/hd_host_e__he12h_drc2 (child HEAD-HE12H-DRC done; e9post.stop touched).
- READY posted claude/head-reset-tree-coherence-1116@b56e08e96e1 (GREEN 15/15, baseline 1).
- HEAD-HW-ECO child resumed: hw4e2 (localhost unit oth-ubuntu-2066093-1794887221), hw5 DRT (E8 unit oth-ubuntu-473593-1794887144), gate of claude/head-hw-eco-staticplan-1116@1ed0608cac.
- HEAD-SD9A child resumed: sd9c E8 unit oth-ubuntu-4115587-1794884149; plan-delta (u_chn 1548.0,109.44) request to HEAD-DIE-R.
- TP2 hd_tile: original NOT SIGNED (DRC0 TT+12.06 internal FF -6.46/34). hold1 insert DONE (34 HB4, 46 fillers removed, check_placement ok). Route-only-touched-nets + successor kit hold1/kit_hd_tile fill/finish + signoff: E7 hold1/run_route_signoff.sh, unit oth-ubuntu-1972223-1794887897, client ~/head-types-r2-logs/tp2_hold_route.log; logs hold1/{route,finish,signoff_hei}.log. ROUTE_ATTEMPTED guard.
- NF15c hd_mesh/hd_lep0N/hd_ctl: E9 route goal live (units oth-ubuntu-2687523/2687522/2687529-1794885716), logs ~/head-types-r2-logs/route_<type>.log.

## STATE 11-17 00:5x PST (after limit; Codex covered 22:20-00:43)
- SIGNED+exported by this lane tree: hd_spn_end SPEPRD3 (+ corrected view hd_spn_end__nf15_speprd3_fix_1116), hd_tile TP2 hd_tile__nf15c_tp2_hold1_1116, hd_host_e he12h_drc2, hd_host_w eco_hw4_hei3 (= Codex hw4e2_hei3_1116, count once). hd_spn NF13a view verified equal to NF15c pins/outline, swapped into die STA.
- Plan now NF15d2r1 (coord c34eab99). NF15c die STA FAIL coverage: die_top has no clock-landing network (379/1182 seams untimed) -> HEAD-DIE-R.
- hd_ctl NF15c routed NOT SIGNED TT -96.09 (mchk_cpy reduction 1 mm reach), FF core -9.59 -> child HEAD-CTL (Sonnet): pipeline mchk, regenerate on NF15d2r1, sign-off.
- hd_lep0N NF15c structural FAIL post-CTS TT -1552.79 (g_pout), killed 143 in hold repair -> NF15e lepn (r482) owner; no more NF15c attempts.
- hd_mesh NF15c: E9 unit oth-ubuntu-2687523-1794885716, GRT congestion iterations; log ~/head-types-r2-logs/route_hd_mesh.log. NEXT: sign-off read; one r417 HEI pass if only internal FF fails.
- hd_serdes -> FABLE-FIX-HEAD-SERDES (sd9c GRT flow error vclk_measured_hold native pad inputs; HEAD-SD9A.md).
- READY posted: reset-tree-coherence b56e08e96e1; hw-eco-staticplan 1ed0608cac (approved r506); head-spe-export 9dd182a70bd.
