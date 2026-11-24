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

## 11-24 03:35 bk_sel ETM + class scan (FABLE-RC-ALL 4d132ca0) DONE
- Regen dsdv_bksel_q ETM from signed eco3 odb/spef + golden SDC: epyc2 /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/etm/dsdv_bksel_q_{tt,ff}.lib (scripts run.sh/etm_*.tcl, lat probe lat_tt.log).
- TT max_clock_tree_path 512.40 reproduced exactly: not stale. 512.40 = network latency of the u_pk/clk hq_pk2 macro pin (the max network+internal endpoint). Registers 635-747 TT; the signed pin mean 750.69 is the right target.
- Old FF (BC) lib: clk->out arcs TT-like (~851 vs regen 669, -181 ps), so FF hold on bksel_q outputs was optimistic. FF setup arcs -10, hold +10; TT clk->out +4.8.
- t2 re-read was not done: there is no routed bk_sel__t2 DB (R7 kits are on epyc10, which is full).
- Class scan: tmp/etm_class_scan.py; out/etm_scan_a.{log,json} (intel2: head, kvsys, s81) and out/etm_scan_b.* (epyc9: QC, c8).
  - 24 unique views flagged; 8 are material (posted).

## 11-24 03:45 FF-lib census (COORD) DONE
- Bundle of 320 views (TT+FF libs) in .../CORE-TAP-BUDGET/ffc on intel2 and epyc10.
  - Scripts: ff_census.py (arc compare), ff_outl.py, ff_report.py.
  - Outputs: ff_census.json, ff_report.log, ff_suspect.json.
- The COORD literal rule (FF within 2% of TT or slower) hits 0 views. The defect signature is a clk->out FF-TT median near -57 ps (HEAD -38); good libs are -120..-200.
- 55 suspect FF libs: S81 33, QC 20, HEAD 2, KV 0. Published as lanes/FF-LIB-CENSUS.tsv.
- 5 SIGNED consumer types need an FF hold re-check:
  - s81 col_h9_r2 x2
  - hd_tile
  - hd_serdes
  - qc slw_sc_v3
- Proven only on dsdv_bksel_q (regen). A second regen sample would confirm the class.

## CODEX notes 11-24 06:2x PST

- Inherited E10 job 1202585-1795526932 completed both split ROM view extractions. East TT clk-to-out 68/68 exact, FF delta median -128.09 ps. Pins and arc keys unchanged. Published normalized-name FF view on main 666e4921a9da, new sha256 925bfb49c6d700481c72cc580cc5c7b419012ec38b23349a7de6060dfc8ee59c.
- West regenerated all 68 arcs, but TT delta range -1.70..+1.24 ps exceeded the matched-view check. It still needs the original SPEF or an exact alternate extraction. No west publish.
- Archives for elemA/B_cv contained the later Nov 15 kit DBs, whereas counted hd_tile uses the original October 27 clock-freeze views. Original run provenance points to removed intel1 and epyc2 scratch paths. The exact FF pair remains open.

## 11-24 08:1x PST fresh lane (post-limit) DONE
- West rom_elem_hw: B5 exact pair (TT+FF) published main 2307e6b63e (romq_split_1106). Basis intel1 .../CORE-TAP-BUDGET/regen/exact_hw_1124. Raw skew is INFO, not a gate.
- Off-main QC 8: OLD in all QC trees. Apply tool main 4c29a21f results/ff_lib_regen_1124/apply_off_main.py. Handed to QC-ALLFIX. kw45 trees are read-only and left untouched.
- Still not exact: elemA/B_cv (hd_tile ruling: GO on estimates + 20 ps hold margin), rxsb (DS85 intake), norm_finish (RF1 intake): both are owned by S81-INTAKE-NORM-RXSB.
- hd_tile headroom: epyc2 /srv/opentallas-scratch3/claude/CORE-TAP-BUDGET/hd_tile_headroom_1124/out/headroom_summary.json. 329 viol, worst -72.3, every one has TT slack >= 660.
