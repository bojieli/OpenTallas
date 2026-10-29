DIE-KV-19 (2026-10-28, successor of DIE-KV-18 d80b9a2573). Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-19-1028.

(1) (b2) red_issue/red_capture lane-group copies (estimate DIE-KV-14b: ~370 ps TT on the pv bank issue fan-out vs 36 ps deficit, UNCHECKED)
 RTL (SHARED, opt-in, default unchanged -> ROOT-MERGE): rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv pv_col LC/MUT_LC (wide_pair
   LEAF_LC/LEAF_MUT_LC): bank tile = ot_qwen_tp8_pv_slice_lc_t (G=4, main via RM230), bcx = {3x cmd[26], 3x cmd[25]} = same bits
   as bc[18]/bc[17]. tb + tools/qwen_attention_native/rate_1015/pv_pair_bench.sh pass LEAF_LC/LEAF_MUT_LC.
 LEC: slice_lc_t vs slice_t closed in DIE-KV-15 (results/die_kv_14_1028/pv_pair/lec_result.txt 101305/101305, MUT_LC caught).
 Bench: bench_lc (LEAF_LC=1, ctx 1/129/2049/8192 must PASS) + bench_lcm (LEAF_MUT_LC=1 ctx 129 must FAIL) -> see RESULT below.
 Die netlist leaf swap (die-local): physical/die_plan/qwen_kvsys/bind/kv45/kv_pv_lc_netlist.py -> die_bound_native_mission_lc.v.gz
   (512 slice_t -> slice_lc_t, bcx tied to the bc net bits l+17/l+18; equal to pv_col LC=1).
 Plan: pv_pair_lc_plan.py -> event/plan.json (= DIE-KV-15 event plan, only pv contents + kv3_pv_pair pins differ) and
   cores/kv3_pv_pair_pins{,_fMX}_r26c_lc.json: +s0/s1 bcx[0..5] = +12 pins, face re-spread by the committed law (committed face
   reproduced exactly first), 1660 face pins, max move 1.344 um, min gap 0.192 um. KV-KITS: regenerate kv3_pv_pair kits from these.
 Pads: kv_pv_col_pads.py takes bcx members (die-local); test_kv_pv_col_pads.py +test_lc_bcx_takes_the_bc_pad (4/4 PASS).
   bind_t1 (no column pads) -> r8_19.sh: R8 PASS, table = r8_b1 + 512 bcx members (pad 0), 0 changed -> r8_t1/.
   pv_col_pads_t1.json = pv_col_pads_b2 + 496 bcx members at their bc pad, law TRUNK_D 63 / FLAG_D 78 unchanged,
   pad FF 114036 -> 141684 (+27648 = 6 x 4608 bc pad stages).
 Bind6 (recipe position2144b19/recipe_kv19_b6.json): strict bind errors 0, unbound/tied/undriven/multiply_bound 0, 430554 bits.
 post_bind19.sh: V-D-H PASS (512 banks, bad 0), v_offset PASS, KV regen_constants 40 OK / 2 WARN (= bind5), image img6 assets
   byte-identical to DIE-KV-16 img5 except provenance labels in pair_transport_txdp.json; kv_constants2.svh differs only in
   the header (bind path + bound sha 7e9ebdcbace6eff6). QC_CONSTANTS_RC=1 there is the old QC fresh_v3 path of run_constants2.
(2) View-mode die gate (gate_views.sh; KV-15 proofF_fb + st_fall count-align + the 3 signed views e2/e5/e6 @3e7fccd216):
   label "real-view (3 core views, 0 kits) + declared-budget rest"; CA TT/FF fail 0 (min 106.5/108.4 ps), start-skew 0/156,
   intra TT setup 290.72 / FF hold -180.88 (real-view 9600/28970 pairs: setup 290.72, hold -97.29), seam 442.05/-183.45
   (0/768 real), HB4 plan model hold 0.0/0.13; GRT0 = KV-15 (50 it, overflow 0, not rerun). UNCHECKED. Missing views 27 types.
(3) TOK-QK-PEER-1: peer_link.sh (pair image derived from both current binds at every KV bind; called by post_bind19.sh);
   SUPERSEDED.txt written in 73 KV boot_v36 dirs carrying TXDP_K 03030443 (list SUPERSEDED_boot_v36.txt).
