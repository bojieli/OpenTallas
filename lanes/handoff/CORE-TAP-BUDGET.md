# CORE-TAP-BUDGET handoff (from FABLE-RC-ALL 701c4a59, 11-24 01:1x PST)
Job: core taps without budget owner -> legacy kit path (ETM max pin target). (1) census all dies, (2) generator fix, (3) report-only PRE check. Also ONE census for QC-CBX-CLOCK defect B (tap_offset raw span; their tool fix landed main 467604377ee).
- Clone: intel2 /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/wt ; outputs out/ (head.tsv, qwen_kvsys.tsv, s81.tsv); QC on epyc9 same dir out/qwen_compute.tsv.
- Census tool: tools/precheck/core_tap_census.py --plan DIE=PLAN --tools <die_plan> --out X.tsv --json X.json (wave plans from ~/coord/autopilot/kit_wave.json).
- HEAD: hd_lep0N + hd_lep0N_w no owner, ETM-tap +58.65, plan-signed -4.75/-4.52; West SIGNED row generates OK; East refused on SRAM 32x128_m1 sheet (no alignment spec) -> fixed in reader.
- QC: 44 legacy (owners are free-text notes); KV: kv3_hg family 8 legacy (+24..56); S81: pending.
- Commits: gen_phys.legacy_core_tap_targets (+legacy_signed_means), core_tap_retarget apply KEEP rows, core_clock_contract SRAM spec fallback, head_lep_nr_sources spec, precheck CORE-TAP-OWNER, census. Push 1 failed on census test after rebase (fixed), push 2 running.
