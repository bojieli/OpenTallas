# QC-A0-KITS-7 (2026-10-28) — A0 parent path

## 1. rawleaf a0k7s (AP 53fcde6a6c40)
Autopilot held it at AUTO-GEOM NO-CHECKPOINT (no 3_place.odb). Place ran via ot-run (exit 0); AUTO-GEOM re-checks ~20:53.
The routed LEC is already in chain v2 (signoff_chain.py runs LEC on 6_final.v before archive when SIGNED). No manual ODB copy needed.

## 2. romleaf TT/FF slew root cause (a0k5, AP 1662a1bff39e)
The default GRT step (`OT_VCLK_CORNER=ff ... CORNER=BC CORNERS=bc`) loads only the FF liberty
(5_1_grt.log: 6 BC read_liberty, 0 tc). So both post-GRT repair_design passes are FF-only and never see TT slews.
Probe in docker on the same a0k5 kit (romleaf_probe/):
- A, unchanged: NOT SIGNED, DRV TT slew 23 / FF 5, TT +155.99, FF hold +3.41. GRT repair fixed 25 + 18 nets.
- B, staged two-mode (tools/die_plan/kit_modes.py stage: CORNERS tc BC, OT_HOLD_MM=1): **SIGNED**, DRV 0,
  TT +147.25, FF hold +4.16, pair skew 48.1/45.1. GRT repair fixed 38 + 65 nets. (CHECKED, signoff_{A,B}.json)
Fix: new opt-in recipe key `two_mode` in gen_core_kit_qc.py. It uses the gen_core_kit_hbm form, and kits without the key are unchanged (test TwoMode).
romleaf a0k7s = a0k5 plan + two_mode + --seam-hold 25,25. Results: KIT_PREFLIGHT PASS 0 (kit_hash 3fa0e62e4b30a2c5);
rtl_lint / sdc_lint / selrange / face_guard PASS; post-synth LEC EQUIVALENT; placed. Enqueued to the autopilot (coord bc777cfc1).

## 3. Parent plan issues (mechanics test with fake signed views; KIT_PREFLIGHT before -> after)
Before: 6 issues per parent. After: NK kit_hash f0e2995cd25c26a0 and NL a1d68a8675859e50 both **PASS 0** (CHECKED, parent_mech/).
- Child gaps / track phase: one rule in cores/a0/parent/a0_child_sites.py. R0 x = 0 and MY x+w = 0.024 (mod 0.048).
  Gaps are >= 10.8 um between y-overlapping children and between macro columns. Children only move right; the largest move is +5.664 um (romleaf R0).
- Mirrored rawleaf pins off grid: covered by the same rule. The MY mirror axis now lies on the M5 grid.
- Placed pins vs plan pin file: the plan table kept the legacy reference-gate pin centres (0.192-um pins at x 0.096 / 457.824).
  The generator places 0.084 M4 edge pins (0.042 / 457.878), so 1041 of 1042 pins differed. Fixed at the die-local input:
  build_parent_inputs.py face-snaps the pins_dir. 2584 NK / 1042 NL pins were snapped, all within 3 um.
- ROM tile file: ot_qwen_rom_tile_w12_land32.sv stays, because it defines ot_qwen_rpair_logic and ot_qwen_rom_tile_logic_w12, which the parent uses.
  The parent synth has 0 ROM or tile instances. The missing piece was the ot_rom_2048x266_m8 blackbox, now added to the spec sources.
- Parent routing M7 is in the recipe.

## 4-5. Open
- parent_trunk_dme hook (local form, centre entry 228.972,578.88) and composition LEC: NOT started.
- OWNER ~20:4x / COORD: ICG=1 per tile root (QC-PG-5 claude/qc-icg-2-1028@a55e5de9c5, not yet on main).
  Use the 75-um A0 PG for the parent PG. Add a clock-gating setup/hold check on u_g.me_idle -> u_icg ENA before sign-off
  (budget ~550 ps UNCHECKED). The parent kit waits for 3/3 children SIGNED (now 0/3) and the ICG on main.
