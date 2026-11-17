# HEAD-TYPES-R2 handoff (Opus, successor of HEAD-TYPES-R/Fable), 11-16 18:5x PST
Logs: intel2 ~/head-types-r2-logs/. Children: HEAD-HE12H-DRC (handoff HEAD-HE12H-DRC.md), HEAD-SD9A (HEAD-SD9A.md).
- eco_hw4 (hd_host_w): E10 .../fable-fix-head-types/eco_hw4/i1t routed, DRC 0, finish rc 0, no sign-off had run (post_runner -). Sign-off launched via ot-run (--dir i1t, only E10 has it): out i1t/signoff_r2, log i1t/signoff_r2.log, client ~/head-types-r2-logs/eco_hw4_signoff.log. NEXT: verdict, LOOK final_*.webp, export.
- he12h (hd_host_e): DRT ended 64 iter with 60 DRC (M6 at u_epc W edge x=423, M7 y~60, M2 W-edge clk_t7/t8 tb0 + relay nets). run_drt.sh continues finish/signoff. Owned by child HEAD-HE12H-DRC (also touches ~/fleet-ops-r-e9post.stop on sign-off).
- sd9A (hd_serdes): GRT exit 6 FAIL_POSTCTS SETUP_TRIAGE TT -189.6 after repair (worst start_o_0/rst_o_0). Owned by child HEAD-SD9A.
- hw5 (hd_host_w): epyc8 GRT goal still running (unit oth-ubuntu-3191148-1794878585). NEXT as HEAD-TYPES-R.md.
- SPEPRD3 (hd_spn_end): epyc8 DRT running (unit oth-ubuntu-3251096-1794878769), OT_PRD_POST=1 auto sign-off. NEXT as HEAD-TYPES-R.md.
- TP2 (hd_tile): tp2 tree replicated E10->E7/E8/E9 same path; launched run_kit.sh route 96/16 via ot-run --dir tp2 -> epyc7 unit oth-ubuntu-1157129-1794883329, client ~/head-types-r2-logs/tp2.log. (first try refused: run_kit.sh outside --dir.)
