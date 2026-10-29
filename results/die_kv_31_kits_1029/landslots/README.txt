DIE-KV-31-KITS land_slots (face_guard "shared" root cause), Thu Oct 29 11:05:15 AM PDT 2026
Root cause CHECKED: KV --kit-rtl kits had no land_slots.json (gen_phys refused --clock-landing with --kit-rtl);
face_guard 4 loads == ot_dp_clk_landing_ca/_cas DEPTH 4 of every u_cland_<bus> (sidecar
wt/codex-kv-0822/results/kv_start_25_1029/event26/sidecar.json sha edfde3ee..., the binder's clock_landing_table).
Shared fix: origin/claude/die-kv-31-landslots-1029@810219984 (off origin/main c6e14b798); same gen_phys.py
(sha f114e583...) applied to a COPY of the Codex 93a731342f generator: intel1 die-kv-31-kits-1029/gen_root/tools/die_plan
(main and 93a731342f gen_phys.py were byte-identical 03765e95...).
Kits: intel1 /srv/opentallas-scratch2/claude/die-kv-31-kits-1029/kits_gen3/<type> (gen_land.sh); diff vs kits_gen2 = +land_slots.json only
(freeze unchanged).  KIT_PREFLIGHT 7/7 PASS 0 (pf3/).
face_guard offline on kits_gen2 1_2_yosys.v + kits_gen3 land_slots (fg3.sh, fg3/), CHECKED:
  hroot PASS 4365/4365   sys_c PASS 5015/5015
  io_cor FAIL 2, io_cor_v1 FAIL 2, io_ft FAIL 2, io_ft_v1 FAIL 2 (was 3508/3081/1059/1057 shared):
     cland_tstart_out = cland_start directly (bound RTL; needs dedicated face flop from cland_start_d),
     cland_raw_reset_out reg cland_raw_reset_q has 1 extra load.
  hub_Ei FAIL 5: the 2 above + rst_o_0 = rr_t21 (5 internal loads) + cland_dn_ready_0/fault_0 into
     default-form ot_dp_clk_landing u_cland_monitor_0 (DEPTH 4, not count-aligned, undeclared).
  Residuals are binder-emitted bound RTL structure, not land_slots.
Place-only launched on kits_gen3 hroot + sys_c only.
