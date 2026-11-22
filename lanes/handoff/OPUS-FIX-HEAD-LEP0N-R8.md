# OPUS-FIX-HEAD-LEP0N-R8 (Opus, from 11-21 23:1x PST): HEAD event r17b + hd_lep0N split to sign-off (successor of FABLE-FIX-HEAD-LEP0N-R7)

Predecessor handoffs: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R7.md (split facts, rename map, NEXT list), -R6/-R5/-R4.
My hub dir: intel2 ~/opus-fix-head-lep0n-r8/. Lane scratch: /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r8/tmp (intel2, epyc10).
R7 lane dir (adopted, still used): /srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r7 (intel2 + epyc10), hub logs ~/fable-fix-head-lep0n-r7/.

## HEAD event r17b (A+B of R7's 21:17 PLAN)
- Tree kw45/snap_s81_head/s81_head_r17b_s0, manifest 67d8b0903f20 (main 385f61b5582a), = r17b_e1b_s0 + native release receipt
  rewritten with in-tree relative paths (R7 e6.sh). Plan 18f3c0c7c0c1, sidecar facc71b93198. G0 PASS 0 errors on epyc10.
  Replicated: epyc10 (origin), epyc7, intel2, epyc9.
- First gate on r17b_e1b_s0 (0a25678af645) FAILED only pre_g0: receipt refused (absolute path into another tree). Fixed by r17b_s0.
- Candidate ~/opus-fix-head-lep0n-r8/cand_r17b.json (event head_rp21z20NF15f_r17b, tools 30b1f11ad5f7 >= 650916ebb262,
  gen_hosts epyc7/epyc10/epyc9 kept, review_before_route NOT required (owner rule), optimistic).
- Publish gate running (started 23:1x): ~/opus-fix-head-lep0n-r8/pgate_r17b.log, --gen-host epyc7, item hd_host_e.
- NEXT: on PASS: apply_reviewed_tree_marker.py --candidate cand_r17b.json --expect-source .../s81_head_r16_s0
  --expect-event head_rp21z20NF15f_r16 --optimistic --keep-gen-hosts. Then check the wave relaunches HEAD types.

## hd_lep0N split private kits (plan g9 in private tree epyc10 L/trees/s81_head_r7split, src_manifest off = proof only)
- W piece hd_lep0N_w: R7 run-item pid 1908887 (intel2, log ~/fable-fix-head-lep0n-r7/runitem_w4.log): place done, in geom/GRT.
- E piece hd_lep0N: R7 kit 1121224225 DIED at 3_3_place_gp: "OT_CLAND missing native stage group ...g_rxm.mrd[256..767]".
  ROOT CAUSE: in the E piece synthesis, yosys merged mrd[k] with the equal g_rxm.g_o[*].g_on.g_registered_select.g_bit[k].dm
  flop and kept the dm name for 1070 of 1104 bits (uncut kit keeps mrd). FIX (R8): the 4 mrd groups (mrd_bank0, mrd_bank1234,
  wdq_bank3, wdq_bank4) now match (?:mrd|g_o\[N\].g_on.g_registered_select.g_bit)\[k\](?:.dm)?$_DFF_P_. Patched in the
  private plan (backup .../opus-fix-head-lep0n-r8/tmp/source_plan_g9_pre_mrdfix.json, new sha 790a97d420d1; script tmp/mrdfix.py).
  All 4 groups now match 256/512/256/80 cells. MUST also go into premove.py / the split event rows.
- E relaunched: spec ~/coord/autopilot/private_specs/OPUS-FIX-HEAD-LEP0N-R8/s81_head_hd_lep0N_1121232043/spec.json,
  run-item pid 3412315 on intel2, log ~/opus-fix-head-lep0n-r8/runitem_e5.log.
- Cut-form LEC (R7 units, epyc10): oth-ubuntu-1452654-1795321534 (functional, CUT_EQUIV_PASS) and oth-ubuntu-1610100-1795322008
  (rst_n free, CUT_RST_EQUIV_PASS); client pids 432115 / 691937 on intel2.

## Open (from R7 NEXT): G0 of g9 had 14 errors (faces x6 need face_budget_g2; 7 START-tree rst_start_raw_N; 1 band_capacity
reader-start:lepk_i0 fill 1.445) -> need per-piece START / reset-export re-derivation before the split goes into an event;
sign-off build must come from a src_manifest tree.
