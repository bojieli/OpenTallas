# KV-101/PVFIN handoff (2026-11-13 18:03 PST) — DO_NOT_COUNT

## State: DONE (nested reset bind), no live job
- Branch claude/kv-101-pvfin-1113 @ 6fa4a6c454 (on origin), worktree epyc7 /srv/opentallas-scratch2/claude/wt/kv-101-pvfin (base 3952588291).
- Files: physical/die_plan/qwen_kvsys/hubc_pair_1113/kv101_rst2_form.py (private constructor, derives native4_rst2 from W native3),
  source_rst2/qkd_pv_fin_s8_pin_physical_model.sv + physical_reset_context.json (bytes of 4675ca42cc, sha 9b7d02d5 checked),
  source/qkd_pv_fin_s8.sv (= 4675ca42cc rtl, = W staged). No tool code changed (no tests needed).
- Untracked in my worktree: native4_rst2/ (hard links of W native3 + new plan_c.json/asbuilt_vN.json/core_pin_cycles.tsv), hard links r8_invariant_1113/, ns_kv100_out7/plan2/eW_sidecar.json, census/census_map_v35.json. plan_c.json still names census_map_v35 by W absolute path (as native3 did).
- Form edits (only these): pvfin content + substitute_inst + core_pin_cycles module -> qkd_pv_fin_s2x8_pin_i1_rst2; files/prefer staged pin.sv REPLACED by donor; pvfin_lo/hi verilog_params removed (fixed master), sub_core_parent pvfin, sub_core_leaf_pin rst_n; asbuilt.sub_core_leaf {pvfin: pvfin}; asbuilt.pvfin_reset_receipt (routed_eq PENDING).
- Bind: recipe /srv/opentallas-scratch2/claude/kv-101/pvfin/run_bind_rst2.sh (= dkv100/event/run_native_pair2.sh with new plan dir/out), unit oth-ubuntu-3422292-1794620244 (ended), I2 ~/kv101log/pvfin_bind_rst2.log, out E7 /srv/opentallas-scratch2/claude/kv-101/pvfin/bind_rst2/out. Result 160/56/2545, structural all 0, errors 1 = stale PAIR PARAM_REGEN (split-owned). The two EMIT wavefront core reset errors are closed.
- Ran with clean 3952588291 tools (W dirty landing_contract.py one-liner NOT included); no landing_contract error appeared.

## Open
1. hub_C emitted RTL: u_pvfin.rst_n and u_kvs_ctl.rst_n are driven by the ahub reset spine ri_ahub_rst_n_q[0] (rsync S2), not by taps 131/132 that bind_core_resets.json records (port kind = in-bus, core_reset applies only to kind rst). Pre-existing for kvs_ctl; bind_component reset proof would flag both. KV owner: choose spine or wavefront for hub_C cores.
2. Per COORD relay: final KV event is the split (KV-101/SPLIT). It must apply kv101_rst2_form.form() edits to its pvfin pair (same 4 edits); not done here.
3. Donor routed EQ PENDING (E4 lec_s8pin2 prepared by PVFIN parent; E4 route job dkv100-s8pin2-route untouched).
4. internal_depth stays 1 (KV convention, no hard core declares reset.depth); donor lands rst_n in 2 stages inside the master.
