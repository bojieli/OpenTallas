# CORE-TAP-BUDGET handoff (from FABLE-RC-ALL 701c4a59, 11-24 01:1x PST)
Job: core taps without budget owner -> legacy kit path (ETM max pin target). (1) census all dies, (2) generator fix, (3) report-only PRE check. Also ONE census for QC-CBX-CLOCK defect B (tap_offset raw span; their tool fix landed main 467604377ee).
- Clone: intel2 /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/wt ; outputs out/ (head.tsv, qwen_kvsys.tsv, s81.tsv); QC on epyc9 same dir out/qwen_compute.tsv.
- Census tool: tools/precheck/core_tap_census.py --plan DIE=PLAN --tools <die_plan> --out X.tsv --json X.json (wave plans from ~/coord/autopilot/kit_wave.json).
- HEAD: hd_lep0N + hd_lep0N_w no owner, ETM-tap +58.65, plan-signed -4.75/-4.52; West SIGNED row generates OK; East refused on SRAM 32x128_m1 sheet (no alignment spec) -> fixed in reader.
- QC: 44 legacy (owners are free-text notes); KV: kv3_hg family 8 legacy (+24..56); S81: pending.
- Commits: gen_phys.legacy_core_tap_targets (+legacy_signed_means), core_tap_retarget apply KEEP rows, core_clock_contract SRAM spec fallback, head_lep_nr_sources spec, precheck CORE-TAP-OWNER, census. Push 1 failed on census test after rebase (fixed), push 2 running.
## 02:4x PST: all three deliverables done
- Main: 9bfb2254dc (gen legacy_core_tap_targets, retarget KEEP owner, SRAM spec fallback, precheck CORE-TAP-OWNER, census), 8041649984 (signed view mean preferred), 096817a8a3 (census W_raw/W_tool/W_res).
- Census: lanes/CORE-TAP-CENSUS.tsv, 450 types; legacy with error: S81 301, QC 32, KV 8, HEAD 2. S81 census takes 42 min (ROM libs).
- Open: plan rows belong to die lanes (core_tap_retarget rows+apply). Possible COORD/S81 veto of default-on gen change (col ROM pins move ~88 ps in new kits) -> would make it plan-keyed.
## 03:2x PST: c8 census done (COORD 02:4x job)
- COORD ruled the GEN fix stays default-on. c8 p6u_hops2 94eb2af6a4f5: lanes/CORE-TAP-CENSUS-S81-c8.tsv. 301 of 302 legacy types move (col 216, leaf 75, kv_leaf 4, LP 4, gunit 1, bk_sel 1). Census column etm_TT/etm_err_TT on main 5ba73cdc86.
- bk_sel: bksel_eco3_1117 lib ETM 512.40 stale vs signed mean 750.69. LP: ln0..3 unowned, plan 405/340 vs signed 424.6/336.26 (row for the S81 lanes).
- Note: for declared_lead rows (core_pin_lead_ps), etm_TT is pre-lead, so pin_target - etm_TT includes the lead.
