# QC-A0-KITS-3 node (2026-10-28, COORD 06:37 ruling (b))
Kit intel2:/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/node/kits/ot_qwen_tile_node_a0k3 (kit_hash 347112e405d42f33), src claude/qc-a0-kits-3-node-1028@a3259b7569, frame 250/202.5.
- Census kit ot_qwen_tile_node_a0k3 (no tree, current main RTL) placed: LEC EQUIVALENT, FACE_GUARD 2565/2565; 12102 clock sinks.
- Plan tree: tools/die_plan/core_family_slice.py run (family a0node, cores/a0/families_a0.json): splits 2,2,8,8, 8 stages, 587 cells,
  256 leaves; branch islands (12.96/31.32, y ~100-115 and ~313-324); legs <=1.0x Manhattan, leaf spread max 12.5 um; plan checks PASS.
  PLAN MODEL TT 247.9 (window 15.1) / FF 187.7 (window 12.1) ps -- UNCHECKED.
- Kit: KIT_PREFLIGHT PASS (with kit_preflight @(*) fix 0facba3557; main kit_preflight false-FAILs module_closure on ot_qwen_w12_tadd).
  Placed rc 0: RTL_LINT/SELRANGE PASS, FACE_GUARD PASS 2565/2565, LEC EQUIVALENT (CHECKED).
- AUTO-GEOM (geom_rules --all-kits) on 3_place: FAIL on plan-contract items only: aspect 9.09 (A0 outline 47.52x432), pin_reg_p90 42.2
  (t_out TOREG feedthrough across the 47.52 width), partial_face E 515 pins on 27 % of the face, col_v est 1.58 at (0,217.5);
  GRT0 at 50 it, clock_reach 13.7 um, 12102 sinks rooted, r2r max 378.8 <= 405. Render viewed: uniform fill, W pins full length,
  E pins y~190-310, entry at centre. Needs visual GEOM review.
