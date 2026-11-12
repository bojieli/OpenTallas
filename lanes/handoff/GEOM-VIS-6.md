# GEOM-VIS-6 lane handoff (FINAL, 2026-11-12 08:17 PST; lane stopped, context heavy)

1 SCOPE: same as GEOM-VIS-5 (lanes/handoff/GEOM-VIS-5.md section 1): owner visual gate. View every render/drawing one at a time as an image; GOOD / OK / ISSUES-ACCEPT / ISSUES / BAD per FAMILY with a CLASS FIX in lanes/GEOM-REVIEW.md. Read-only on builds.
2 TOOLS (copies in lanes/handoff/geom-vis-6-tools/{v2,v6}; set S to a dir holding v2/ v4/ v6/ - qlast.txt and vq_seen.txt belong in v4/): GEOM-VIS-5 tools (lanes/handoff/geom-vis-5-tools/) on the Claude localhost scratchpad /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad : v2/poll2.sh, v2/fetch_lr.sh, v6/post.sh (= v5/post.sh with GEOM-VIS-6 counts). Fetched renders in v2/vis/<key>/. Seen list v2/seen2.txt.
   Codex without scripts: list VISUAL-QUEUE.tsv WAIT-VISUAL rows; scp <render_dir>/place/{layout,density}.png (+ grt/congestion.png) + auto_geom.png and view them.
3 RUNNING JOBS: none of mine.
4 POSTED (GEOM-REVIEW.md):
  07:4x KV kv3_phy a15 + kv3_phy_v1 a9 BAD WAIT-FORM (unchanged from GEOM-VIS-1 00:27; pins 700 um from the core face; fix re-face/narrow ~450 um + pin reg column) -> DIE-KV-99.
  07:4x S81 leaf t59 a7 BAD WAIT-FORM (old e9eda32d41c plan; fix ready12 leaf floor).
  07:4x HEAD hd_mesh lb_mesh_eo / lb_mesh_st GRT ISSUES (seam knots col5|small-macro, SW W-face pins; >= 30 um trunk channel).
  07:4x QC sle_ctl cl67434795 a20 ISSUES (unchanged; s28 CTL form); slw_st_a_v2 cl9f076a5c ISSUES-ACCEPT; HBM q2n2 FORM C ISSUES not for route (bank collapsed into a 10-um N band; C2 = 60-100 um bank region) ; HEAD wshim_tx FT-HOP proof base GOOD.
  07:5x HEAD lep0N re-pack v2 drawing (a50145295ac5) FORM GOOD (check E-half row ends x~1850 vs E-strip pale-green objects); KV vN2 draft 2 FORM GOOD with conditions 1-5 (band re-site, LAND-RING B, N hgi E <=0.6, taps, phy re-face).
  07:5x S81 leaf t47 a8 ISSUES WAIT-FORM; QC st_a pvf82a6c28 LAND-RING pilot ISSUES-ACCEPT (E column 60-70%).
  08:0x KV kv3_hgi_v1 cl141fc26e a4 + cl42bc8b12 BAD WAIT-FORM (pre-vN2 pockets, r2r 2187/873, relay_collapse 271); HEAD hd_spn a3 ISSUES (tap split); QC st_a x3 ot-jobs ISSUES-ACCEPT.
  08:1x COORD order: VISLAYOUT2-QC 11 routing items viewed: sc x7 ISSUES probe (GRT watch W column 85-95% on cl4590432d/cl7479a5ec/cl63e5a7a2/cl5e017c6f/slw_sc_v3), st_a x4 ISSUES-ACCEPT (clf4365a62 new S-E band). NONE BAD. Next: view their GRT congestion PNGs (vislayout2-qc/{sc,sta}/runs/.../run/layout_review/grt) when they land.
  HEAD-95 07:50: my lep0N v2 check found real band overlaps; fixed rp13/rp14 df181b8d64d0; kit place on epyc8 next -> WAIT-VISUAL.
  08:1x COORD order (GEOM-VIS-5-addressed requests are ours): S81 dsdv_slice_lepe_nh_mus_LP__t1 VL3 L1 ISSUES-ACCEPT probe (resume cts); KV kv3_hgi F1 ISSUES evidence only (do not adopt staggered core offsets); HBM hp4 seam drawing FORM GOOD w/ change (orange station lines off L202 gcell row -> ~10417 row); kv3_sys_SD_v1 SD-GROW A OK route (reach items -> REACH-FIX-2).
  08:2x HEAD wshim_tx FT-HOP fix GRT GOOD (61% = base); eshim_rx w10 route OK (79%). 2-h SUMMARY posted 08:2x (early); next due ~10:20.
5 PENDING: HEAD lep0N v2 KIT PLACE (WAIT-VISUAL next; judge logic street y 538-638 < 0.9, no knot at the 81-um split); HBM q2n2 FORM C2 place (DIE-HBM-101); KV vN2d re-render + first hg/hgi vN2d places; S81 svc t6/t7 ring pilots; QC-S28-C re-post; S81 ready12b + centre re-pack drawing (waits LF3); QC st_b re-place on FW-EFACE; HBM handplan v2 (phase 2). Unviewed older (05:3x PST) renders: epyc7 land-ring-2/pilots slw_st_a_v1 pvdf8e5ca4, vislayout2-qc/sc sle_sc_v1 cl7479a5ec + slw_sc_v1 cl63e5a7a2 (sc family is WAIT-FORM already), gen-class-1 wtx_src hd_spn_wshim_tx (proof).
6 NEXT SUMMARY due ~10:20 PST to COORD. Re-arm: bash v6/qwait.sh S 40 and bash v6/rwait.sh S 40 in background (each exits on a hit); after viewing, append '<host:path> <stage>' to v2/seen2.txt. Requests addressed to GEOM-VIS-5/6 are yours (COORD 08:1x).
7 GOTCHAS: see GEOM-VIS-5.md section 8. Never git in /home/ubuntu/OpenTallas.
