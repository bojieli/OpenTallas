KV-KITS-22 2026-10-29 (COORD 07:09; parallel to KV-KITS-21). Plan event27f = intel1 die-kv-28-1029/event27f/plan_e27f.json
sha256 db8fc720ab16 (CHECKED). Tools main a4453d4004. Census = census.py (this dir) -> census_e27f.tsv.

(1) DEPENDENCY CENSUS of the 56 types in DIE-KV-28 sta_E_edge missing_views (55 intra + kv3_phy seam-only),
    160 instances [CHECKED-own, plan hard_cores vs signed views e1/e2/e5/e6@3e7fccd216]:
    - 45 types blocked on missing CORE views (kits need each hard core's timing lib; gen_phys refuses LEF-only macros):
        hg  x8  (32 inst): e0 + qkd_ectlk_q0..q3
        hgi x11 (33 inst): e0 ONLY   <- e0 (KV-013) alone unblocks 11 types / 33 instances
        pc  x6  (32 inst): qkd_kvs_pc (+ qkd_kvs_pc_h_head_p on 2 types)  <- kvs_pc alone unblocks 4 types / 28 inst
        pv  x17 (17 inst): kv3_pv_pair + ot_qwen_tp8_pv_join_t
        hub_C (ahub, kvs_ctl), hub_Eo/hub_Wo (kv3_astk), hub_Wi (14 qkd_hr_* host cores)
    - 2 types HARD-MODEL: kv3_phy (4), kv3_phy_v1 (28). plan "hard": true -> gen_phys emits NO kit (by design,
      gen_phys.write_kits skips hard types). They gate ALL seam hold (KV-004) together with pc. -> ASK-1 below.
    - 9 types with NO hard core: hroot, io_cor, io_cor_v1, io_ft, io_ft_v1, hub_Ei, sys_SD, sys_SD_v1, sys_c.

(2) The 9 core-free types: event27f vs event26 type diff = ONLY clock.landing_contract START/reset pin sites
    (4-12 fields per type) [CHECKED tdiff]. Kit RTL = bind.py kit-rtl, which needs the bind plan's asbuilt manifest:
    plan_e27f and event26/plan.json have none; bind26b was made from Codex source dbbb186a8 + recipe_kv26b.json,
    which are NOT on main or GitHub [CHECKED git cat-file]. Also DIE-KV-29's provider import puts the START provider
    cells (10530 FF + 12141 comb) into the partitions. => kits for these 9 types wait for DIE-KV-29's strict bind of
    event27f (+ import); a kit built now would be stale. Size class (estimate before build, ot_dp_st stations/bits in
    bind26b RTL, CHECKED grep; cell totals UNCHECKED): io_ft 24/6.3k, io_ft_v1 24/6.3k, io_cor 104/13.4k,
    io_cor_v1 137/19.1k, hub_Ei 455/41.2k (+4 or2), hroot 87/5.5k (+kc/kvs_hroot leaves), sys_SD(_v1) 4/1.05k + serdes
    x6 blackbox, sys_c 68/10.2k + d2d cal/sfm + UCIe/SRAM/ROM macros. All far under 400k cells/run.

(3) PHY estimate (ASK-1 basis): kv3_phy_part = 11 ot_dp_st (2512 bits), kv3_phy_v1_part = 14 ot_dp_st (2518 bits) +
    landing cas/collect/origin + rsync around ONE blackbox qkd_hbm3e_phy_pc4 (port model, bind/models/kv_phy_slices.sv)
    [CHECKED bind26b RTL]. Every pc<->phy seam lands on these wrapper registers, which are real std cells that today
    exist only as the plan-generated abstract LEF (no netlist, no clock tree, no view). ~2.5k FF/instance = a tiny kit
    (<~20k cells UNCHECKED), but it needs (i) a gen_phys opt-in to kit a hard type's registered wrapper and (ii) a
    LEF+lib for the PHY blackbox (registered-pin hard partition contract, PATH-QC-PHYB hard_pinreg form).
