# GEOM-VIS-5 lane handoff (updated 2026-11-12 06:50 PST)

1 SCOPE: independent visual-gate reviewer. View every place/GRT render and every hand-floorplan drawing ONE AT A TIME as an image (never verdict from numbers). Post GEOM VERDICT lines to lanes/GEOM-REVIEW.md: GOOD / ISSUES (+ ACCEPT recommendation or not) / BAD, each naming the FAMILY and a CLASS FIX. Reach items (taps > cap, hops > 405 um, reset reach) go to REACH-FIX-2; congestion/layout quality are ours. Answer each WAIT-VISUAL row in lanes/VISUAL-QUEUE.tsv within ~30 min. Read-only on builds (never launch/kill/route).

2 WORKTREE: none (review lane; no git branch, no uncommitted code). Hub writes only via coord-commit.sh. Local tools are on host ubuntu (localhost of the Claude session) in /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad :
  v5/post.sh <geom.md> <queue.md> "<msg>"  appends to GEOM-REVIEW.md + COORD-REVIEW-QUEUE.md on intel2 and commits; prints origin counts of "GEOM-VIS-5 viewed" / "GEOM-VIS-5 ->".
  v2/fetch_lr.sh <S> <key> <host:/.../run>  copies layout_review/*/*.png, smells.one, summary.txt and ../../../geom/auto_geom.png into v2/vis/<key>/.
  v2/poll2.sh + v2/scan_remote.sh  scan epyc2/4/7/8/9/intel1 for new layout_review dirs (unseen vs v2/seen2.txt) and pull VISUAL-QUEUE.tsv to v2/vq.tsv.

3 RUNNING JOBS: none of mine.

4 WATCHERS (re-arm every 30 min):
  v4/qwatch.sh <S>  every 5 min diffs COORD-REVIEW-QUEUE.md (line counter v4/qlast.txt) and prints lines about floorplan/drawing/GEOM-VIS/WAIT-VISUAL/vN2/QC-S28-C/ready12b/fix2/HFP-/HBM-HANDPLAN/lb_lep_m8/form B/re-pack.
  v4/rwatch.sh <S>  every 7 min runs poll2 (out v4/poll.out) and prints UNSEEN render dirs + new non-HBM WAIT-VISUAL rows (seen list v4/vq_seen.txt).
  After viewing: append "<host:path> <stage>" lines to v2/seen2.txt.
  Codex without these scripts: list VISUAL-QUEUE.tsv WAIT-VISUAL rows; for each, scp <render_dir>/place/{layout,density}.png + auto_geom.png and view them.

5 RESULTS POSTED this session (all in GEOM-REVIEW.md, 06:08-06:5x):
  S81 leaf t44 a11, t34 a4, t53 cl958451dd, t72 VL3 fam2: ISSUES, old e9eda32d41c plan; fix = ready12 leaf floor (DIE-S81-88). Taps t44 t5 3565, t34 t6 1965 -> REACH.
  HEAD: hd_spn_wshim_tx GRT GOOD (62%); wshim_rx prd t10 route GOOD (79%); hd_mesh route ISSUES (col4|small-macro seam knots, S-array W bus crosses rows; fix >= 30 um trunk channel at seam). hd_lep0N re-pack v1 DRAWING: APPROVED WITH CHANGES C1 pin-access offset if g_pp centre-face pins, C2 split tx rows 5+5 at the 121-um street, C3 three clock taps under tx rows, C4 pin orientation, C5 rx-stack slivers by declaration.
  QC: sle_su_l0 cl7a55c676 GOOD; slw_stm_v2 cl1ca9c415 BAD (oversize, stm shrink); slw_fw_v1 cl592e3d37 ISSUES; sle_fw_v2 cl69f5e854 a13 + coll_ft cl78c7b300 a2 / cla4a25d77 a1 ISSUES-ACCEPT recommended (GRT ov 0; COORD: accept only if DIE-QC-100 confirms the fingerprint is unchanged); sle_sc_v3 LR2 + sle_sc_v1 cl115da35f ISSUES (23-um E sliver; VISFORM full E channel); slw_st_a_v2 cl9f076a5c ISSUES-ACCEPT to GRT.
  KV: kv3_hg_v3 (01:01 job) ISSUES: W pockets at ~58%/~78% in head0 gaps, local 1.385; fix = vN2 W-street.
  NOT POSTED: die-proto-3 KV vN / HEAD fix2 runs have NO die-level render (searched epyc8/9 die-proto-3); ask DIE-PROTO-2 for a die GRT congestion PNG (owner visual-layout focus) in the 2-h summary.

6 NEXT STEPS:
  a) 2-h SUMMARY due ~07:30 PST to COORD (IMPROVED / STILL BAD / NEW CLASSES, every line from viewed images).
  b) Expected renders: HEAD lep0N re-pack v2 kit place (check C1-C4); S81 svc_hi t6 + svc_lo t7 ring-form pilots (DIE-S81-88; A/B vs VL3 base without ring; GOOD and no worse than base -> ring folds in); KV vN2 hg first place (street from face bits, W gaps street+landing only, pockets < 0.8); KV F1 place (VISLAYOUT3-KVHEAD); QC s28/HF-1c VISFORM forms; S81 ready12 leaf places.
  c) Drawings still to come: KV vN2 draft 2 (lanes/kv-vn2-1112 still holds draft 1 05:15); QC-S28-C re-post; S81 ready12b + centre re-pack (C2 C|LP interleave, C4 leaf->slot->partner table); HEAD fix2 drawing; HBM handplan v2 (phase 2, low priority).
  d) GRT watches: HEAD lb_lep_m8; QC fw / st_a (E column > 90% => BAD).
  Rule: no verdict on renders that are gone or on stale-plan rows; say so in the queue.

7 OPEN ASKS: COORD to mark the QC fw/coll_ft rows ISSUES-ACCEPT (pending the DIE-QC-100 fingerprint answer). HEAD-95 to answer C1 (g_pp centre-face pin count).

8 GOTCHAS: ot-jobs/*/work/run dirs vanish minutes after place (copy-back); fetch right away. epyc4 ssh resets under load, so retry sequentially. epyc5 host key CHANGED: do not touch. Lane timestamps on the queue are skewed (posts dated 07:20-09:00 arrived before 07:00 local). Never use git in /home/ubuntu/OpenTallas.
