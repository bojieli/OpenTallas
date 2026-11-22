# KV-RINGMAC-R1 handoff (Opus 5.5; COORD lane, started 2026-11-21 22:0x PST)
GOAL: sign 9 NARROW cland ring masters for the kv3_hub_C cut (D28 cut 11-22 12:00 PST, else D29), export views, hand paths+shas to FAM-KV-HUBC-SYSC-R2 + KV-PLAN-R6.

## State 2026-11-21 23:5x PST: ALL 9 SIGNED + views delivered (post SIGNED 23:5x)
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
