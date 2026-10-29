DIE-KV-15 2026-10-28 (KV die owner; successor of DIE-KV-14 19cef52376 + 14b f628504846; branch claude/die-kv-15-1028 = 14 + 14b + main a639e30f6f).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-15-1028.  CHECKED-own = my run reproduced/measured; nothing NUMBER-CHECKed independently.

(1) pv_pair 12-cycle LEC (DIE-KV-14b lec_slice_lc.sh, intel1 kv14b-lec/t0,t1): nominal 101305/101305 proven (equiv_status -assert
    passes); mutant MUT_LC=1: 256 unproven, all g_lane[15] = CAUGHT.  [CHECKED-own read]  (b2) NOT landed in this event (see end).
(2) INTEGRATED EVENT.
  a. Clock: hm_r26q15c = pd9c hm_r26q9c + core_tx_plan.py apply (DIE-KV-14a delta).  The core_tx clock entry is a hub_Wi PARTITION
     leaf (type clock.taps, from the partition tap (639.36, 838.08)); the die tree only reaches partition taps, so the fishbone
     rebuild (kit2/chain2/ca.sh = DIE-KV-14 recipe) gives a BYTE-IDENTICAL tree.json and TT arrivals to DIE-KV-14 [CHECKED cmp].
     Partition leaf re-plan: plan tap xy (864.024, 989.28) -> (805.896, 935.28); Manhattan from the partition tap 375.9 -> 263.7 um
     (CHECKED-own arithmetic); insertion budget 250 TT / 202.5 FF unchanged, realised by the hub_Wi kit CTS.
     GRT0 incl clock (50 congestion iterations) TT/FF overflow 0, usage 2.37 %; duty TT 47.2-52.6 / FF 47.7-51.3 %, 0 outside 45-55.
     Gate of record (proofF_fb = tap_fall_merge TT then FF; st2.sh fall; main count_align_bind + die_sta_related, clock_variation
     table, spice, cppr-lca, shared droop, inv, HB4, FF 202.5): CA TT/FF fail 0, worst lo 106.5 / 108.4 ps, START-SKEW 0/156 TT and FF
     = COUNT-ALIGN PASS; landed verdict PASS; intra TT setup +458.97, FF hold -180.88 raw / HB4 plan model 0.0 (kit-contract -62.78 =
     DIE-KV-14 known class).  [CHECKED-own; logs/st2_fall.log, logs/sta_fall.log]
  b. Event (kv15_event.py = kv13_event.py with paths changed; compose on hm_r26q15d = q9d + core_tx delta): repro of the st2 fall
     bind 3595/3595 ports identical; ECTL RT = 17 on all 32 frames -> 0 extra rows (the fishbone needs no ECTL equalisation);
     verify 0 loop errors, 0 window violations, min 105.2/110.5 ps; compose 56 types / 160 parts, 0 placement failures.
     event_gz/ (gunzip to event/; plan.json pins_file paths are relative to results/die_kv_15_1028/event).
  c. Binds (run_bind15.sh, ot-run intel1): bind1 (KV-13 R8 table) 31 R8_STALE (expected) -> r8_15.sh R8 regen PASS (71,501 pad FF,
     write groups 78/78/78/78) -> bind2 0 errors -> kv_boot_v36 prep -> vport_w_pads --boot-dq (12/16 vports, 630 stages, max 91,
     9,450 FF, boot RL 186) + kv_pv_col_pads on the PV-unpadded bind2 (C 9: TRUNK_D 63, FLAG_D 78; 682 members; 114,036 FF)
     -> bind3 (recipe_kv15_b3) 0 errors -> pair_image_txdp seams 90,90,88,88,88,78,78 (TXDP_K 030304aa) -> bind4 0 errors,
     param hook TRUNK_D/FLAG_D 63/78; boot prep on bind3: 0 remaining W pads.  [CHECKED-own]
  d. Image (kv_native_image_13 run_constants2 + emit_assets, QC peer fresh_v3): KV REGEN_CONSTANTS PASS {OK 40, WARN 2: VPORT_DQ,
     CFG_FIA 166}; 96 DCFG + 19 AGE words (img4_assets/); QC COLL_LS 376 vs 407 MISMATCH = ONEQC owner (unchanged).
(4) V-word vs command offset (v_offset_check.py, static on bind4 bus_groups; v_offset_bind4.json): FAIL.  Each bank registers
    pv2 and bc on one edge and takes V on c_r.take; as-built V - cmd is one constant per vport (DIE-KV-14d CHECKED).  On bind4
    d = (V landed - asb) - (bc landed - asb) per vport source spreads up to 48 stages (pv2; 35/36 sources not single-valued) and
    11 (pe2 ASTK response).  The vport streams one V row per cycle (qkd_pv16_vport_b out_v <= row every edge), so no hold window
    absorbs it: DESIGN BUG.  Fix estimates (UNCHECKED): per-bank sink pads 1.35M FF (no); one pad per column at the pv partition
    entry (the 8 banks of a column share d) ~168k FF; shared tapped line at the vport ~83k FF + ~13.5k output bits.
(5) B48 token sim NOT run (held by (4)).
(b2) red_issue copies: the pv slice leaves are plan contents (kv3_pv type, ot_qwen_tp8_pv_slice_t x32) with bc as a ctl->bank
    crossing; bcx needs the pv_col RTL (rtl/hdc/nearhbm, shared), the plan leaf module, the pv_pair pins (+12) and the PV column pad
    generator (bcx must take the bc pad) -> separate KV event after (4).
