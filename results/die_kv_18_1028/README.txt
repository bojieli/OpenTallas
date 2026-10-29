DIE-KV-18 2026-10-28 (KV die owner; successor of DIE-KV-17 83d80b289a; branch claude/die-kv-18-1028).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-18-1028.  CHECKED-own = my run; nothing NUMBER-CHECKed independently.

(1) ESTIMATE - PV attention service vs the static link RESULT slot  [CHECKED-own]
  The service need of context T = PV_START + R + 48 + F_DLY with R unstretched (kv_static_programme.attention_calendar
  law). On bind5 ages (KST 90,90,88,88,88,78,78, PV RL 186 -> d_rl 167, RESULT_TRUNK_EXTRA 0): worst need 1775 edges
  (T 7937; 1775 also at 8192), the unpadded link slot gives 1689 -> 86 edges short.  The DIE-KV-17 "need grows with
  the pad" reading was the first FAILING context moving to larger T (7260 -> 7321 -> 7443 -> 7687 -> 7809); the need is
  a function of T only, so pads 8..64 were simply below the worst context.
  Cost: 86 edges per layer inside the attention window.  Token period 293,376 core edges with pad 0 AND pad 86
  (token_period_pad0_vs_pad86.json: layer_run_span 2802 -> 2888, absorbed by the RoPE 8,012-edge layer floor) ->
  0 tok/s cost; compiled MU frame user0 4089.4 tok/s (1.2e9/293,376), aggregate 10,223.6 (F 2).  vs the 4051.0
  reference: no loss (not the same basis: 4051.0 = nativev7 composer, UNCHECKED comparability).  < 5 %: no OWNER ASK.

(2) STRUCTURAL FIX (shared tool, READY for ROOT-MERGE)  [CHECKED-own]
  kv_static_programme.service_slot_pad(pr) = max(0, max_T need(T) - service_end at pad 0), one pad for every layer and
  context, from the ages at compile time (no per-layer pad, no override table).  link_calendar takes the pad explicitly;
  kv_boot_v36 service-pad prints it (JSON); run_mu833.sh derives it unless OT_KV_ATTN_SERVICE_PAD is given, and feeds
  the SAME pad to the pair image and the compile (link_image_check still fails closed).  Default-preserving: a die whose
  need fits gets pad 0 (committed die ages: pad 0, test) -> byte-identical images.
  Tests: tools/qwen_kv_die/test_kv_service_slot_pad.py 4 + test_kv_static_programme.py 14 = 18 PASS (unittest, intel1).
  Pair image: only the C_RX / K_TX calendar entries move (RESULT / STATUS slots); TXDP_C 0a010308, TXDP_K 030304aa
  unchanged; DUT dcal ROM content (kv_dcal_profile --sv) byte-identical pad 0 vs pad 86 (= profiles/cal_pair1024).
  Native MU833 boot bundle on bind5 COMPILED (status COMPILED_NOT_QUALIFIED = LOGICAL_ONLY retirement, as every native
  KV compile so far): 14 images, 7404 frames, epoch 2827, service_end 1775, compiled_end 1996.  bind5m compiles to
  the SAME 16 target hashes (mutant is RTL-only: one kv3_pv_v5n file differs in the staged vehicle).

(2b) Non-native (legacy as-built) MU-frame failure = a SECOND, independent cause  [CHECKED-own]
  The legacy compile (run.sh: as-built ages, two-clock profile) never reaches the slot check problem (as-built RL 112,
  pad 0 fits); it fails in kv_frame_search because it runs frame F 2 with the r16 STATUS tail, which has no
  collision-free frame (KV-PROG17 COORD decision: r16 frame F 3).  legacy_asbuilt_frame.txt: F2 FAIL, F3 PASS,
  F2 + CONTROLLER_CORE FAIL.  The image of record (run_mu833: common 833 clock, EMB 1627 + RoPE) finds an F 2 frame.

(3) B48 vehicle (KV-P7 kv_dieslice, NATIVE_BOOT=1) on bind5 / bind5m: NOT BUILDABLE from main  [CHECKED-own]
  Staged veh5 (DIE-KV-17) + veh5m (stage_src bind5m), image dir vimg5 (frames/expect/epoch from bind5 bundle +
  pair image as d2d_cal_image_kv41.svh).  Elaboration stops in seconds (vehicle_bld5_errors.txt, 36 errors):
  - kvpc_rst_diag.svh: tb_kvslice_native.sv says build.sh generates it; no branch has the generator (empty diag-off
    copy supplied in vimg5);
  - 3 packages not in the staged list (ot_crc_pkg, ot_gpu_w6_secded_pkg, ot_qfd_emb_pkg; prepended by a local helper);
  - then: bench hierarchical refs to modules the bind does not have (ot_qfd_serdes_112g_x6_phy_c45 u_phy/tx_up,
    ot_qfd_link_adapter slice body f_*), kv3_sys_c_part pins link_v/link_flit/far_v/far_flit, kvs_compute_end
    u_c.u_core, partrec_hub_Wi.svh nets of an older bind (x_hgi_WN_7_ft21_o_hub_Wi, dut.rst_n).
  The native bench on main targets the Codex B48 bind cohort (kv45 / qk-native-1351 staging), not the DIE-KV-13..16
  binds; its regenerators (partrec, kvpc_rst_diag, native staging) are not on main.  No 250 GB build was started.

(4) (b2) red_issue lane-group copies: NOT started.
