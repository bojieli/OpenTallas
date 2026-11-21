# KV-PLAN-R6 handoff (KV qwen_kvsys plan-event owner; successor of KV-PLAN-R5). Updated 2026-11-21 13:40 PST.
Dirs: epyc8 /srv/opentallas-scratch2/claude/kv-plan-r6 (remap1, pair, pinclear2, d27d_prev, scripts); intel2 ~/tmp/kvplanr6 (chains, logs).
D27d tree (edited in place, copy+mv only): epyc8 kv-plan-r3/d27c/tree. Old bind_of_record dirs: d27c/bind_of_record.d27d_r5, .d27d2_r6.

## Events
- D27d2 plan a39def2ca080 = D27d + landing_remap (14 types, 1740 names) + pc r8_strap_pad_max 63 + hub_Eo r14 cut + pair image K 174/162/155.
  Strict bind GREEN (d27c/bindgate_d27d2_r6: BIND_ERRORS 0, LATCHECK 0, BPC 0), G0 PASS. NOT applied: it carries 920 face pins under clock sites.
- D27d3 plan 48b92c30c8f6 = D27d2 + clksite_pinclear (62 die_clock_tree rows / 42 types, <= 2.16 um, 0 hits; = main 114851a275 tool; ledger kv-plan-r6/pinclear2/ledger.json) + IOPC-R3 r10c io_cor_v1 ft11 bank3 (kv-plan-r6/d27d3/).
  Tool fixes needed by D27d2 proofs: 0b660fcf93 (pc_v3 R8 width 4..max), faa5241952a (bind is_exact_bank, sys_c). Proofs + apply pinned rt 3a68739125f4.
  Chain intel2 ~/tmp/kvplanr6/chain_d27d3.sh (pid in chain_d27d3.log): waits for the D27d2 proof chain (pid 1354734, apply held by missing APPLY_OK),
  then bind_d27d3.sh (install plan, pinsite recheck, G0 g0gate_d27d3 + bindgate_d27d3_r6) -> d27d3_proofs.sh (9 gen proofs on rt 3a68739125f4 + kit_pin_site_check)
  -> touch APPLY_OK -> apply_d27d3.sh (final path kw45/src_kv_pin_eb1e73448bd0_hg15_3c5d2c04_t4e46a7ec_d27d3, TOOLS 3a68739125f4). Out: ~/tmp/kvplanr6/apply_d27d3.out.
  After apply: lift kit_wave holds that say "delete when D27 applied" (pc x5, pv_v6n, hub_Wi stays, kv3_hgi_v8/kv3_hub_Eo R6 holds), and decide retry_prev_kvr6_nod26.
- Fallback D27e = D26 + io_cor_v1 41 bank_taps (epyc7 fam-kv-iopc/tree_d26) -- would also need pinclear.

## Facts
- EMIT root cause: landing_raw_branches name relays of the reset tree solved on D26; D27d stations renumber it. Fix = landing_remap OLD=D26 NEW=event plan, as a generator step.
- Pair image: KST 95,95,93,93,93,77,77 HRT 158 EMBRT 152; QC must bind the same image (told QC-PLAN-R10). KV boot programme compile fails on D26 and D27d alike (kv_frame_search), pre-existing.
- kit_wave 9db6f8e25e: retry keys parked (retry_prev_kvr6_nod26), holds kv3_hgi_v8 + kv3_hub_Eo (COORD lever 6: no new D26 relaunch).
- epyc8 D26 tree src_manifest --ro OK. rt 4e46a7ec lacks obs_gcell_cap; use rt >= dd507bc8ba2a.
- Open: hub_Wi io_pad_die_id pin row + qkd_hr_core_peer re-export (asked HUB-R3 / IOPC); D28 rows (pv split PV-R5, hub rings HUB-R3, hgi HGI-R6, taps TAP-GRID-R4) on the applied D27d3 base with landing_remap + clksite_pinclear re-run.
