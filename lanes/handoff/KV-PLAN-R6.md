# KV-PLAN-R6 handoff (KV qwen_kvsys plan-event owner). Updated 2026-11-21 22:00 PST.
Dirs: epyc8 /srv/opentallas-scratch2/claude/kv-plan-r6 (d27d3/, pinclear2/, remap1/, repo/ lane clone); intel2 ~/tmp/kvplanr6 (apply scripts/logs).

## D27d3 (plan 48b92c30c8f6) - APPLIED 21:5x PST (receipt lanes/handoff/qwen_kvsys_atomic_apply_1795325990321432122.json)
- Tools of record rt 47a226faaa96 (3a68 reaped). Tree + portable bind verified on epyc8/7, intel2/1, epyc2/9/10. kit_wave 6a0ac2f1fd lifted pc x6 holds; hub_Eo held to D28; hub_Wi held; kv3_hg*/kv3_pv* auto-lift on KV-D28.
- TODO cleanup (guard skipped until its current-tree cache moves to D27d3): ot-delete epyc8 kw45/...d27d3.links_r6, epyc7 kw45/...d27d3.r6tmp (scratch and scratch2).
- Content: D27d + landing_remap (14 types) + pc r8_strap_pad_max 63 + hub_Eo r14 cut + pair image K 174/162/155 + clksite_pinclear 62 rows / 42 types (main 114851a275 tool, identical rows) + IOPC r10c io_cor_v1 ft11 bank3.
- Gates: PRE 0, G0 0 errors, strict bind 0 (160/56/2545), LAT 0, BPC 0, 9/9 gen proofs + kit_pin_site_check 0 on rt 3a68739125f4 (has 0b660fcf93 R8 width + faa5241952a bind is_exact_bank, my fix).
- Tree: epyc8 /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg15_48b92c30_t4e46a7ec_d27d3, REAL copy (nlink 1), manifest fa1d8c9906a3, verify --ro OK 03:41Z.
  Old hardlinked version at ...d27d3.links_r6 (epyc8) and partial epyc7 ...d27d3.r6tmp: ot-delete both after apply (guard skips until applied).
- Apply: intel2 ~/tmp/kvplanr6/apply_d27d3_e8.sh (out apply_d27d3_e8.out): portable bind on epyc8 + tar replicate to epyc7,intel2,intel1,epyc2 -> guard -> publish_bind -> candidate (epyc7 mk_candidate_g0) -> waits D27D3_PLAN_VISUAL "48b92c30c8f6 PASS" -> publish_apply.
  Visual render: intel2 kv-plan-r6/visual/d27d3.png (r.sh; 33 GB scratch copy in visual/t -> ot-delete after).
- Incident: FABLE-FIX-KV-HUB-R4 chain_h3_r4.sh cp -al'd the d27c/tree SYMLINK and wrote into the event tree (02:20Z); killed, restored, its additions in epyc8 fable-fix-kv-hub/from_d27d3_tree_r6/.
- Owner 19:0x: AFK/KREQ independent (no hold); K-C = -8 for the calendar (pair image is transport-only; goes into the KV boot programme compile input).
- After apply: post APPLIED; ping FAM-KV-IOPC-R4, KV-HUB-R4, HUBC-SYSC-R2, FAM-KV-HROOT-R1, OPUS-FIX-KV-HGI-R6; lift kit_wave hold_items that say "delete when D27 applied" (pc x5, pv_v6n; kv3_hgi_v8/kv3_hub_Eo R6 holds); kv3_hg*/kv3_pv* holds auto-lift on event_adopt:KV-D28 (eda955d481).

## D28 rules (FABLE-PD-KV-2000 + COORD)
- STABLE TYPE BLOCKS: change ONLY types a row fixes; every other key unchanged; no die-wide regeneration.
- Carry HGI R6c rows (19 types) + pv split (16 pv types) in ONE event; hub ring rows (HUB-R4, via a real copy), hub_Wi pin row, hr_core_peer re-export.
- KV-WAITBIND-R1 CBC: take ONLY kv3_hub_Wi + kv3_pc_v3 bank reset relay rows (+0 cycles); NOT the 72 lane K deltas.
- Re-run landing_remap (OLD=D27d3, NEW=D28) and clksite_pinclear (main) only on the changed types.
