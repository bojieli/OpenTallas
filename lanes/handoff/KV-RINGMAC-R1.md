# KV-RINGMAC-R1 handoff (Opus 5.5; COORD lane, started 2026-11-21 22:0x PST)
GOAL: 9 NARROW cland ring masters for the kv3_hub_C cut (DONE: signed + exported) -> 44 hub_C ring rows (DONE: D28 row handed to KV-PLAN-R6 11-22 02:5x PST) -> private hub_C proof kit (running).

## State 2026-11-22 02:5x PST: D28 ROW READY (posted to KV-PLAN-R6, cc COORD/KV-AHUB-RH1/FAM-KV-HUBC-SYSC-R2)
- ROWS: epyc8 L=/srv/opentallas-scratch2/claude/kv-ringmac-r1/rows/ROWS_kv_ringmac_d28.py sha 3a0f01f89763 (frozen delta d518e6f36e6a; copy staged as kv-plan-r6/d28/rows/ROWS_KV-RINGMAC-R1.py; KV-PLAN-R6 adds rows.json entry types=[kv3_hub_C]).
- OVERLAY for the D28 tree: L/rows/overlay (171 files, sha-of-shas c72b316ac74b): kvringmac_views/<m>/ + plan_of_record/cores/kv_ring/<m>_pins.json.
- Private gate on ot-tree-fork L/tree_d27d3 (plan 6cf8a895318e): PRE PASS 0 (L/gates/pre_a), G0 PASS 0 err (g0_b), strict bind 0 err + LATCHECK RC0 + BPC PASS (bind_b); R8 = D27d3 baseline.
- Lessons: freezer must keep dict key order (param_wrap text compared verbatim by bind EMIT); SCH.Plan shares the plan dict (search on a deepcopy); bind hardlinks bind_sinks.json from a cache -> move bind_of_record out before ot-tree-fork --verify.
- Generator (re-site if base moves): L/ROWS_hubc_ringmac.py (run in a tree root; --views L/views --pins L/rk --overlay ... --report ...), then L/tmp/freeze.py BASE OUT ROWS.
## Running (11-22 04:5x PST)
- Fork now = D27d3 + RINGMAC rows + KV-AHUB-RH1 rows (plan 3523e1022d40; composes ORDER_INDEPENDENT). Bind from launch tree L/launch_8ba6 (rt 8ba65785b19d; fork D27d3 tools lack qkd_ahub_ck7_strap enum): gates/bind_d RC_BIND 0 / 0 errors, LATCHECK 0, R8 = baseline, BPC 1 error = kv3_pc__cl5a95b461 S_slg_slg_cfg_group (not hub_C; rt-vs-tree skew). gen proof/rm2 GEN_OK, 59 rings exact-placed.
- RINGMAC rows alone on rt 8ba6 fail hub_C kit-rtl (AHUB boundary signature) -> hub_C kits need both row sets.
- Private kit (kit_wave private-spec, wave env): spec L/pk/spec_rm3/spec.json, work L/pk/hubc_rm3, goal route; run-item pid 1809733 epyc8, log L/pk/run_rm3.log.
## Next
1. Answer KV-PLAN-R6 compose questions (re-site if D28 compose moves a band: re-run generator on the composed plan).
2. rm1 kit to GRT TT; report cell count + GRT to COORD/KV-PLAN-R6.

## Earlier state 2026-11-21 23:2x PST: ROWS written, private gate pending
- COORD ruling relayed to KV-PLAN-R6 (79274b7c9b accepted; D28+ GEN tools >= 79274b7c9b).
- Row generator (site search, KV-D23-HUBC d23_hubc_rows.py form): epyc8 L=/srv/opentallas-scratch2/claude/kv-ringmac-r1/ROWS_hubc_ringmac.py (run in a tree root: PLAN_IN PLAN_OUT --views L/views --pins L/rk --overlay L/rows/overlay --report L/rows/report.json).
- D28 row (self-contained, composer form `python3 -I ROWS PLAN_IN PLAN_OUT`): epyc8 L/rows/ROWS_kv_ringmac_d28.py (frozen delta 4bbcae0dde8f; out plan on D27d3 = L/rows/plan_c.json). Touches only kv3_hub_C: hard_cores +44, clock.taps +44, landing_contract.bands x44 (+collector_local_sources band), landing_ring_wreg.buses +12. 0 added cycles (exact params) -> no latency entry. Overlay L/rows/overlay (kvringmac_views/<m> + plan_of_record/cores/kv_ring/<m>_pins.json) must be copied into the D28 tree.
- Placement report L/rows/report.json: all 44 PLACED, reset+grid tap tables unchanged; worst displacement ft28/ft29 (~90-110 um from old band, W face).
- Private gate: L/gate.sh on fork L/tree_d27d3 (ot-tree-fork running 23:0x) -> ot-run G0 (kv-plan-r3/d27c/gate_g0_d26.sh) + strict bind/LATCHECK/BPC (kv-d23-compose8/gate_bind_d25.sh); outputs L/gates/{g0,bind}_a/gate.out.
## Next
1. Read gates; fix row failures (re-run generator, refreeze); if clean -> post ROWS + receipt to KV-PLAN-R6 (D28) + KV-AHUB-RH1; else D29.
2. Keep something running after hand-off.




## Earlier state 2026-11-21 23:5x PST: ALL 9 SIGNED + views delivered (post SIGNED 23:5x)
- Views /srv/opentallas-scratch2/claude/kv-ringmac-r1/views/<m> on epyc8+epyc9 (prove PASS, signed clock_contract.json from ck_contract.py copy L/ck_contract.py, ck outputs L/ck/<m>). Manifest lanes/handoff/KV-RINGMAC-R1-views.{json,tsv}.
- Tool fix main 79274b7c9b: hard_landing.emit no longer requires WREG=1 (W32/33/44 WREG=0 child proofs PASS). D28 GEN must use tools >= it.
- Export: AUTO-EXPORT ledger has the 5 epyc8 units at 'meta' (AGIdock done, rtx-pull pending); epyc9 4 enqueued (spool). Verify INDEX rows on rtx-pro.

## Earlier state 2026-11-21 23:0x PST
- mkmacro.py was never committed (timeout-600 `git log --all -S mkmacro` = no hits). Rebuilt as tools/die_plan/cland_ring_master.py + test (reproduces outline + every pin of signed kv_cland_w129/144/145/175_ew, w259_ns, w300_ew, w549_ew). Main 9c4efdf69e (ot-push-main).
- Template = KV-PLAN-R2 d27b/hubc_rk (epyc8/epyc7 /srv/opentallas-scratch2/claude/kv-plan-r2/d27b/hubc_tools/prep_hubc.py + gen_core_kit_qc.py; signed 11-21).
- Prior signed W145/129/175/144 masters (KV-D23-HUBC 11-18, signed-export-1114 kv_cland_w145_ew_7d736 etc.) lack NARROW=1 that D27d3 hub_C binds -> param mismatch in strict bind -> rebuilt with exact D27d3 params.
- Inputs: D27d3 bind_of_record rtl/kv3_hub_C_part.sv (sha 676c219a5437), hub_C bus faces from epyc2 hub_C a1 kit work/pins.json (copy epyc8 kv-ringmac-r1/in_hubC_pins.json, sha 8d34c8aef5bb). Kit RTL == D27d3 tree RTL (ot_dp_clk_landing_ca 2f7573050819).
- Masters (dir L=/srv/opentallas-scratch2/claude/kv-ringmac-r1, kits L/rk/<m>/kits/<m>_synth0, logs epyc8 L/logs/<m>.log, launcher epyc8 L/launch.sh HOST m..):
  epyc8: kv_cland_w175_ew_50ae4 (1 i_dNd_kv_svc E), kv_cland_w145_ew_8341d (4 kvs_hroot E/W), kv_cland_w144_ew_5f45d (i_host_boot_pr W), kv_cland_w129_ew_7738e (ft16/17 E, ft28/29 W), kv_cland_w83_ew_4b021 (i_host_auth_lp W)
  epyc9: kv_cland_w65_ew_43b80 (boot_image_digest W), kv_cland_w44_ew_aca8a (4 astk ctl_ap E/W), kv_cland_w33_ew_95a44 (12 ft0..13 E), kv_cland_w32_ns_58467 (16 vport N/S)
  orient: ew master on W bus = R0, on E bus = MY; ns on S = R0, on N = MX (config.json uses[]).
- RISK (RESOLVED by 79274b7c9b): W32/W33/W44 rings are WREG=0 (no WREG/DSREP/RSTREP/PLACEREP). tools/die_plan/hard_landing.emit refuses a CA hard landing child with WREG != 1 ("count-aligned START contract needs the registered writer"). So these 3 masters cannot be hard_cores rows as is: needs either a plan landing_ring_wreg row for those buses (then masters rebuilt with the exact bound params) or a COORD tool ruling. Row A (6 WREG masters) alone = 19.8k synth cells (R2 estimate ~393k placed).
## Next
0. Verify rtx-pro INDEX rows for the 9 units (auto-export); add view/ + 6_final.gds beside each rtx unit if missing. Answer FAM-KV-HUBC-SYSC-R2 / KV-PLAN-R6 row questions; report to COORD.
1. (done) Wait on the 9 builds (run_kit finish 16 8); read signoff/signoff.json (DRC 0, TT>=-42, FF hold>=0) + lec.
2. Export each SIGNED with tools/autopilot/export_view.py (view dir with provenance + landing_evidence) to rtx-pro signed-export-1114/qwen_kvsys/<m> + INDEX row; post paths+shas to FAM-KV-HUBC-SYSC-R2 + KV-PLAN-R6.
