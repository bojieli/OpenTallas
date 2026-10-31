# HEAD l44 = l43 + budgets.cland_pinslot_types (DIE-HEAD-44, 2026-10-30)
One-block kit-export fix (COORD 17:24 (1), FLOW-11 pinslot 255a6469a06 on main): plan of record l43 (meta_l43 source_plan sha256 67bb06b1)
+ budgets.cland_pinslot_types = [hd_turn_a, hd_turn_b, hd_st_str, hd_spn_wshim_rx]. Only difference (json compare): that budget key.
The key is read only by gen_phys.py (export OT_CLAND_PINSLOT=1 into the named kits); no geometry, pin, clock or RTL change -> no strict bind rerun.
- plan l44 source_plan.json sha256 afe2304d767a6d805bba0a378dcdeb982730bc1c896b2ff14a58ac1d1b230d66 (sidecar 02dececead4a = l43 copy)
- G0C (main aff657cac check.py, same tools both): l43 1 err / 26 warn, l44 1 err / 26 warn; 27 findings each, 0 new / 0 gone (error = pre-existing reset wavefront PENDING).
  Pre-main tools (die-head-43 ncd_tools) reject the new key (schema) -> G0C must use main tools.
- Die clock l44a405 (same config as l43a405, plan path only): GRT TT/FF total overflow 0 (90679 nets); spread scaled 122.33/120.14;
  OCV stated 149.78/142.16 (0 > 150); duty 0 outside 45-55 TT/FF = l43a405 identical.
