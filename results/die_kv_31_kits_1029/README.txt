DIE-KV-31-KITS receipt (2026-10-29 10:08 PDT) -- the two HELD KV core-free kits from DIE-KV-30-KITS (ee4dc88618).
Results only; no RTL / shared tool change. Work dir intel1:/srv/opentallas-scratch2/claude/die-kv-31-kits-1029.

(1) kv3_sys_c -- macro_pin_grid FIXED, KIT_PREFLIGHT --contract --plan-dir PASS 0 issues (CHECKED, preflight_kv3_sys_c.*).
  Mechanism = the existing plan-content snap already on main, physical/die_plan/qwen_kvsys/g3/kv_sysc_grid_snap.py
  (DIE-KV-13 4cc85bb2f, COORD faf936223 item 1; the same idea as KV-KITS-11 4cc2d64d7 for qkd_ahub):
  4 d2d SRAM y +12 nm, ot_qkvd_ucie_x64_phy x +12 nm, ot_rom_64x32_m2 y +12 nm (snap.json). That is 1/4 of the M4/M5 48-nm pitch.
  Plan: die-kv-30 plan (sha fc24c089..) -> plan_snap/die_plan.json (sha in plan_snap.sha256). A semantic JSON diff shows
  exactly these 6 origin_um values changed and nothing else (CHECKED). The kit was regenerated with the SAME generator
  (Codex wt codex-kv-kits-0822 @93a731342f tools/die_plan/gen.py phys, --hold-ff-margin 10; gen_sysc.sh), via ot-run on intel1.
  macro_pin_grid now: 6 macros, 4211 pins, worst 0.0 nm off (was 12.0 nm; CHECKED).
  Kit diff vs the die-kv-30 kit copy (kit_delta.py -> kit_delta_sys_c.json, CHECKED):
    102 files byte-identical, rtl/ included. All 21 rtl/ files are byte-equal to their bind27f kit_rtl.f sources.
    macro_place.tcl: the 6 snapped origins (+0.012).
    io.tcl / plan_pins.json: 1168 lines each, all +0.012 um. These are exactly the 1168 UCIe interior bump pins
      (link_flit 583 + link_v + far_flit 583 + far_v), which sit on the macro's own pins and move with it.
    freeze.json: pins sha only. Nothing else changed.
  RESET-TREE CATCH, found and fixed: run 1 (snapped plan, bind27f kit_rtl.f as is) re-planned the reset relay tree.
    The 12-nm macro moves shifted the CLEAR_UM blockages, so reset_tree.tcl went from 53 to 52 tree relays and the
    rtr_place names shifted onto different u_rrl_<n> instances. That is wrong against the bound RTL, which has 107 relays
    from the unsnapped plan (e.g. RTL u_rrl_84 = wire depth 7, run 1 placed rst_n_t9 there).
    Fix uses gen_phys's existing rule ("kit_rsync writes reset_tree.tcl next to bound kit RTL"). rtlsrc/kv3_sys_c holds
    byte copies of the bind27f kv3_sys_c_part{,_bound}.sv, istations.tcl, kit_rtl.json and native_station_*.json, plus
    reset_tree.tcl. That reset_tree.tcl is the bind-plan tree, copied byte-for-byte from the die-kv-30 kit.
    kit_rtl.f is repointed for those 2 files only (sys_c/kit_rtl.f). With this, the regenerated reset_tree.tcl is
    byte-identical to the die-kv-30 kit (CHECKED).
    The relay sites keep >= 4.308 um clearance from the moved macros (4.32 minus at most 12 nm).
  DIE FOLLOW-UP (not done here): the die-level plan/bind still carries the unsnapped origins. The next KV bind/event must
    apply kv_sysc_grid_snap.py BEFORE bind, so that die plan, kit and RTL reset tree all agree.
  NOT LAUNCHED (estimate before build): all 6 die-kv-30 place runs ended FAIL_PREFLOOR port_bind after synth (CHECKED,
    <kit>/FAIL_PREFLOOR). The extra netlist bits are the count straps: extra hroot 140, hub_Ei 488, io_cor 134,
    io_cor_v1 152, io_ft 26, io_ft_v1 26. Cause: the kit has no straps.json and no strap pins, while the RTL has strap_ca_*
    inputs. sys_c RTL has 50 strap_ca lines, and its kit has 0 strap pins, no straps.json and 0 strap_ca in
    port_bind_pins.json (CHECKED), so it would fail the same gate. Fix the generator's count_strap export first, then
    run place.

(2) kv3_sys_SD / kv3_sys_SD_v1 -- NOT FIXED. A modelled view alone is not enough: the cell type needs an alias step.
  Views exist, but not on main: Codex results/kv_serdes_pg_event27 (gen_model.py, commit 9b66de546 on
  origin/codex/kv-physical-prep-1027):
    - masters ot_qfd_serdes_112g_x6_phy_w522 / _w521, 1866.24 x 972 um at type origin [17.28, 54];
    - all signal pins on the E face on M4 (the host/FDI side of both types in their own frame);
    - M6 VDD/VSS straps, OBS M1-M5;
    - timing from the x12 TP8 view (mem_compiler Timing: setup/hold/clk->q at the boundary).
    The COORD 10-27 15:24 ruling sys_SDx6 (derived from x12, no fake logic) matches it.
  Why the view alone does not place: the RTL blackbox is ot_qfd_serdes_112g_x6_phy #(W) with ports [W-1:0] (dynports).
    Yosys derives $paramod\ot_qfd_serdes_112g_x6_phy\W=..., which has no LEF master (the old ORD-2013). Probes in
    serdes_probe/ (orfs:latest yosys 0.68, CHECKED):
    (a) a liberty cell named ot_qfd_serdes_112g_x6_phy (the ADDITIONAL_LIBS path) gives
        "ERROR: Module `bbx' ... does not have a parameter named 'W'";
    (b) `rename` of the derived module does NOT retype the cell;
    (c) `chtype -set <master> {t:$paramod\<module>\W=*}` after `hierarchy` DOES retype the cell (u_core -> bbx_w522).
  What is needed:
    (i)   gen_phys physical_inst/physical_master content alias (9b66de546) plus a synth canonicalize hook emitting that
          chtype per content. This is shared tools/die_plan code, and the kits come from Codex's unmerged generator
          93a731342f (29 tools/die_plan files differ from main), so it is a ROOT-MERGE / Codex-generator change.
    (ii)  plan delta: serdes content inst = the real path (kv3_sys_SD_part_bound u_core under ot_qfd_serdes_112g_x6_phy_c45),
          lef/lib/origin/outline/orient R0 and physical_master w522/w521.
    (iii) a PHY PG domain for sys_SW/sys_SE. Not in the plan yet; Codex pg_domains_candidate.json has VDDPHY_SW/SE.
    (iv)  LEC must accept the aliased black box (gold $paramod vs gate _w52x). lec.py not audited.
  Estimate (UNCHECKED): ~0.5 day incl. tests; place run 0.0-0.1 M cells -> 16-24 GB.
