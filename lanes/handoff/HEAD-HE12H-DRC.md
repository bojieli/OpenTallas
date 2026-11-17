# HEAD-HE12H-DRC Codex takeover, 2026-11-16
Authoritative host E9 /srv/opentallas-scratch2/claude/fable-fix-head-timing.
- Original he12h: DRC60, TT -24.23, internal FF -18.64; preserved.
- ECO1 he12h_drc: actual DRC4, TT -24.28, FF +0.68; final signoff NOT SIGNED consumes stale inherited route metric DRC60. Remaining4 were left-edge reserved-site M2 spacing.
- ECO2 he12h_drc2: both-edge 3-site temporary placement padding, otherwise same exact geometry+hold corrections as ECO1. Actual final DRT0, empty5_route_drc.rpt. Full final PIN_AUDIT2167/2167.
- Diagnosed metric defect: custom RUN_LOG_NAME_STEM5_2_route_ecodrt produces no JSON; old5_2_route.json copied with kit remains60. Original automatic signoff retained unchanged.
- Required actual-frame signoff first setup client2022728 failed before STA (root-owned ORFS files deny unprivileged hardlink; failed partial frame and log preserved). Corrected sudo copy to fresh run_eco_actual2, client2038809, log ~/fht-logs/he12h_eco2_actual_signoff2.log. Script E9 he12h_drc2/signoff_actual.sh, output hd_host_e/signoff_he12h_eco_actual. run_eco_actual2 contains hardlinked finished results, current empty DRC report and current6_report; deliberately no obsolete route JSON. Actual kit/config/SDC/native files unchanged; no routing replay.
- NEXT collect actual-frame verdict then export on SIGNED to AGIdock+rtx-pro with localhost /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/ffht_export.sh. Tell HEAD-DIE-R real view. Keep failed verdicts.

- Final exact ECO2 final_all.webp LOOKED: EPC macro along E face, distributed smaller macros and open W-side corridors, PG stripes continuous; no new layout launch. Current final report DRC0 is the physical check of the reserved-site edge fix.
- Narrow source follow-up: E9 he12h_drc2/run_eco.sh custom DRT must emit actual DRT metrics (or explicitly supply current report); do not teach global signoff to trust file mtime. Parent agrees keep global signoff unchanged.

## SIGNED + ARCHIVED-BOTH 2026-11-16 19:5x PST
- ECO2 actual-frame signoff R-MINIMAL SIGNED, DRC0 (current 5_route_drc.rpt), TT setup -24.28ps (achieved857.28ps within42ps tolerance), FF standard min +0.69ps, complete internal FF census0violators. SDC lint and face_guard PASS; pin audit2167/2167. Antenna not present in actual-frame record (advisory). Legacy and pre-ECO failures retained.
- Actual signoff: E9 he12h_drc2/hd_host_e/signoff_he12h_eco_actual/signoff.json. Source output directory: hd_host_e/run/results/asap7/dp_hd_host_e/base.
- ARCHIVED-BOTH: AGIdock /archive/opentallas-signed-1114/s81_head/hd_host_e__he12h_drc2; rtx-pro /home/ubuntu/signed-export-1114/s81_head/hd_host_e__he12h_drc2. Both INDEX.tsv appended. ODB sha27077f92a77f9f9af459289146e1cf7f5f773b685db5ab868d38379682baf3f3,414166494bytes.
- Targeted final6_final.v output BUF/INV/HB4 alias-cycle check PASS:1083outputs checked,0cycles,max18bufferchain, onlycontinuousalias fclk_out_coll_o1=cland_fwd_fclk_out_coll_o1. Scopedcheck not LEC. JSON he12h_drc2/he12h_output_buffer_check.json.
- HEAD-DIE-R real-view worker informed to replace host_e stand-in. No more physical retries required for host_e. Narrow custom-runner actual metrics fix remains follow-up; no global signoff edit.
