# GEOM-VIS-6 lane handoff (live; updated 2026-11-12 07:45 PST)

1 SCOPE: same as GEOM-VIS-5 (lanes/handoff/GEOM-VIS-5.md section 1): owner visual gate. View every render/drawing one at a time as an image; GOOD / OK / ISSUES-ACCEPT / ISSUES / BAD per FAMILY with a CLASS FIX in lanes/GEOM-REVIEW.md. Read-only on builds.
2 TOOLS: GEOM-VIS-5 tools (lanes/handoff/geom-vis-5-tools/) on the Claude localhost scratchpad /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad : v2/poll2.sh, v2/fetch_lr.sh, v6/post.sh (= v5/post.sh with GEOM-VIS-6 counts). Fetched renders in v2/vis/<key>/. Seen list v2/seen2.txt.
   Codex without scripts: list VISUAL-QUEUE.tsv WAIT-VISUAL rows; scp <render_dir>/place/{layout,density}.png (+ grt/congestion.png) + auto_geom.png and view them.
3 RUNNING JOBS: none of mine.
4 POSTED (GEOM-REVIEW.md):
  07:4x KV kv3_phy a15 + kv3_phy_v1 a9 BAD WAIT-FORM (unchanged from GEOM-VIS-1 00:27; pins 700 um from the core face; fix re-face/narrow ~450 um + pin reg column) -> DIE-KV-99.
  07:4x S81 leaf t59 a7 BAD WAIT-FORM (old e9eda32d41c plan; fix ready12 leaf floor).
  07:4x HEAD hd_mesh lb_mesh_eo / lb_mesh_st GRT ISSUES (seam knots col5|small-macro, SW W-face pins; >= 30 um trunk channel).
  07:4x QC sle_ctl cl67434795 a20 ISSUES (unchanged; s28 CTL form); slw_st_a_v2 cl9f076a5c ISSUES-ACCEPT; HBM q2n2 FORM C ISSUES not for route (bank collapsed into a 10-um N band; C2 = 60-100 um bank region) ; HEAD wshim_tx FT-HOP proof base GOOD.
  07:5x HEAD lep0N re-pack v2 drawing (a50145295ac5) FORM GOOD (check E-half row ends x~1850 vs E-strip pale-green objects); KV vN2 draft 2 FORM GOOD with conditions 1-5 (band re-site, LAND-RING B, N hgi E <=0.6, taps, phy re-face).
  07:5x S81 leaf t47 a8 ISSUES WAIT-FORM; QC st_a pvf82a6c28 LAND-RING pilot ISSUES-ACCEPT (E column 60-70%).
5 PENDING: HEAD lep0N v2 KIT PLACE (WAIT-VISUAL next; judge logic street y 538-638 < 0.9, no knot at the 81-um split); HBM q2n2 FORM C2 place (DIE-HBM-101); KV vN2d re-render + first hg/hgi vN2d places; S81 svc t6/t7 ring pilots; QC-S28-C re-post; S81 ready12b + centre re-pack drawing (waits LF3); QC st_b re-place on FW-EFACE; HBM handplan v2 (phase 2). Unviewed older (05:3x PST) renders: epyc7 land-ring-2/pilots slw_st_a_v1 pvdf8e5ca4, vislayout2-qc/sc sle_sc_v1 cl7479a5ec + slw_sc_v1 cl63e5a7a2 (sc family is WAIT-FORM already), gen-class-1 wtx_src hd_spn_wshim_tx (proof).
6 NEXT SUMMARY due ~09:30 PST to COORD.
7 GOTCHAS: see GEOM-VIS-5.md section 8. Never git in /home/ubuntu/OpenTallas.
