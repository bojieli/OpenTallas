Qwen KV/system die BIND OF RECORD for the KV host cores (COORD 10-27 19:17 KV-HOST-REGEN-1 ruling (a)): KV-KITS-7 b3,
recipe_kv_2350. ROOT-MERGE-83 landed it on main so no qkd_hr_* core is cut from a non-main source.

Source: bind.py run on claude/kv-kits-7-1027 @496744d616 (clean tree). Its plan is the staging plan hm_r26q3 256600e2
(the die_plan.json of that commit), NOT the KV plan on main. Manifest:
physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv_2350.json (see provenance_bind.json).
Run dir: intel2:/srv/opentallas-scratch2/claude/kv-kits-7-1027/b3.
u_host = qkd_host_root_admission_obsx_bo1_c45 (bind/kv45/; D2D_BOOT_ORDER 1, REQUIRE_MISSION_START 1, every ck_* port
on the one core clock) + rtl/physical/ot_fdi_tx_pace.sv. This is NOT the plain obsx of bound_r8.

Files:
- bind.f: repo-relative. The original used absolute paths into the source worktree and into b3/rtl.
- rtl/: the 54 bound partition modules + the bound top, byte copies of b3/rtl.
- bind_latency, bind_report, bus_groups, port_bind_strict: .json.gz (gzip -n of the b3 json).
- param_regen.json; port_bind_strict.txt (DIE_PORT_BIND PASS, 51 masters / 160 instances).
- verify_report.json: 2,553,368 matched, 0 mismatched; unbound/tied/undriven 0; lint 52 runs, 0 errors.
- bind_names, bind_parent_id_straps, bind_por_gate, bind_tie_audit json.

Closure on main (CHECKED by ROOT-MERGE-83): every bind.f entry resolves on main.
- 49 shared sources are byte-identical to 496744d6.
- The sources that existed only on the staging commit were added byte-identical from 496744d6: kv45/, kv44/
  plan_rewires, inputs/kv_bound_rtl6/, the kvbind1025 recipe inputs + regen hooks, dcal_rom position2144b19,
  rtl/qwen_sys/{kv_pc_r8_positionbank_1025, kv_plan_leaves_1025}, the two static_kv_die_20261017 nc32 files, and
  rtl/physical/{ot_fdi_tx_pace, ot_fdi_phy_cdc, kv_pc_r8_position_bank}.sv.
- The 6 content-addressed kvbind1025/composed_rtl/<sha256>.sv files were copied; each file's sha256 equals its name.
- No existing main file was changed.

OPEN (KV owner): physical/die_plan/qwen_kvsys/bind/kv_regen.py on main (blob b51ae50313) is older than the b3 source
(blob 0ceb0d1a50, which adds QK_CONSUME_FLOOR = 34: QK_ISSUE_AGE = max(34, RL + 11)). param_regen.json here is the b3
output. A re-bind from main needs that kv_regen.py change and the hm_r26q3 plan; the KV plan on main is q5c39.
