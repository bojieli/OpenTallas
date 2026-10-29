DIE-KV-30-KITS receipt (2026-10-29 09:37 PDT) -- 9 KV core-free partition kits, GEN -> preflight -> GEOM REQ -> autopilot.
Results only; no RTL / plan / tool change.

Inputs
- Kits: Codex gen_batch2.py (gen.py phys --hold-ff-margin 10; kv3_hub_Ei --gpl-plain) at
  intel1:/srv/opentallas-scratch2/claude/codex-kv-partition-0822/kits, generator source codex/kv-kits-batch-0822@93a731342f.
  Own byte copies (originals untouched): intel1:/srv/opentallas-scratch2/claude/die-kv-30-kits-1029/kits/<type>.
- Plan: plan_reserved.json sha256 fc24c089... (29431-window clock+provider union), copied as die-kv-30-kits-1029/plan/die_plan.json.
- Kit RTL: strict bind27f exports intel1:/srv/opentallas-scratch2/claude/codex-kv-0822/bind_fast/kit_rtl/<type>/kit_rtl.f
  (bind_report n_errors 0, unbound/undriven/multiply_bound 0). sha256 of each kit_rtl.f: bind27f_kit_rtl_f.sha256.

(1) RTL hash check (rtl_hash_check.py -> rtl_hash_check.json) CHECKED: all 9 MATCH, every kit rtl/ file byte-equal to its
    kit_rtl.f source, 0 missing, 0 extra.
(2) KIT_PREFLIGHT --contract --plan-dir <plan> (kit's own kit_preflight.py; preflight/*.json, *.log) CHECKED:
    PASS 0 issues: kv3_hroot kv3_io_cor kv3_io_cor_v1 kv3_io_ft kv3_io_ft_v1 kv3_hub_Ei kv3_sys_SD kv3_sys_SD_v1
    FAIL 6: kv3_sys_c macro_pin_grid -- 4 d2d SRAMs, the UCIe PHY and the ROM are each 12.0 nm off the M4/M5 track grid
            (plan-site origins, e.g. SRAM clk M4 centre 18.06 vs tracks 0.024+0.048k). Same failure FLOW-GEN-2 (f) found
            10-28 and assigned to the KV generator (fix: snap the plan content origins to the grid, as KV-KITS-11b did
            for qkd_ahub). Without --plan-dir the check is skipped, so run_kit.sh's own preflight would NOT catch it. HELD.
(3) Pre-place geometry: Codex atlas results/kv_partition_batch_0822/geometry.png (codex/kv-kits-0822@d1dd8a67e, copied
    here as geometry_atlas.png) VIEWED by me. Outlines = plan slots (freeze.json outline == plan outline_um).
    FT per-bit legs from each kit's ft_bit_sites.tcl (ft_bit_legs.py -> ft_bit_legs.json) CHECKED, worst leg um:
    hroot 360.99, io_cor 388.08, io_cor_v1 246.78, io_ft 218.43, io_ft_v1 218.43, hub_Ei 402.30, sys_c 372.22: 0 legs >405.
    (The plan's nominal regs_um give hub_Ei ft63/ft64 478.6/479.9 um (ft_legs.json), but the kit places per-bit sites,
    which are what gets built.)
    hub_Ei station column (GEOM-REVIEW-24 spine FAIL had 9,276 station flops in one 15-um column at x~640):
    now max 2,512 per 15-um column (x 885), next 2,456 (x 495); 33,867 per-bit sites. CHECKED (counts). Routability
    is judged on 3_place + GRT.
    Pins-near-flops / fill / r2r cannot be judged before placement; these are large transport partitions (1.3-2.2 mm2)
    with low logic fill set by the die slot, so expect low fill / high empty in AUTO-GEOM. Prior FAILs to recheck on
    3_place: hroot gen1 ordinary r2r 1407 um (CODEX-GEOM 10-27 10:12), io_cor full r2r 1579/9938 >405 (withdrawn 10-27).
(4) HELD kv3_sys_SD / kv3_sys_SD_v1: preflight PASS, but the bound RTL instantiates the blackbox
    ot_qfd_serdes_112g_x6_phy (via serdes_c45.sv u_core) and the kit carries no LEF/lib for it (config.mk has no
    ADDITIONAL_LEFS; no x6 view on origin/main; plan contents 'serdes' has no origin/outline). That is the ORD-2013
    ("no LEF master") failure KV-KITS logged before. Needs a modelled x6 SerDes view + plan site (PHY owner) first.
    Not run (inference from kit contents, not from a run).

Kit hashes (sha256 of all kit files, 16 hex): kit_hashes.txt.
