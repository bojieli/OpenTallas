# DIE-LEVEL-1119 (lane DIE-LEVEL-CHECK-1119, 2026-11-19)

The owner started die-level checks (11-19 04:xx). This lane ran die GRT, related-pair die STA with count-align (CA),
token pricing, and a core-tap clock offset table on each die's live plan. Everything ran through ot-run
(--priority die --crit) on epyc10.
Run root: epyc10:/srv/opentallas-scratch2/claude/die-level-1119/runs/<die>/<tag>. Clones: <lane>/wt (main 42a461c091) on epyc8/9/10.
Tool: tools/die_plan/proto_die.sh lane copy (kit = die_trial / ot_clk of the plan's OWN src tree, kw45 mounted read-only).
Each run has its own script copy; a script a live job reads is never edited (lesson: the 12:26 UTC in-place edit killed the S81 l1119b and QC l1119b chains).

| die / plan | clock measured | GRT overflow | related-pair setup (TT/FF) | landed CA | tok/s (last known) | owner |
|---|---|---|---|---|---|---|
| S81 D8g 154b8c6d | generic inv2 H-tree (ECOv3 kit gone) | 0; M4-M7 2.7/4.0/4.4/2.2 % | n/a (CA blocked) | NOT MEASURED: 66 no-K (default); 39/421 ambiguous start edges (r4 form) | 838.8 AR / 2701.3 MTP on live lanes (834); CBC +39 cyc off critical path | S81-DIE-R3: regenerate ECOv3 on D8g |
| QC N4.3 e5278ab8 | M4 template tree (epyc2 scratch3, cut for s4q9m4) | 0; M5 5.8 % peak | +376 / +433 intra | default recipe 562/2993 fail (lag); UNMEASURED until the reg-chain recipe | bound 4397.4 (4403.2), CBC +185 cyc | QC-PLAN-R3: reg chain on N4.3 |
| KV D25c 4a40f1db | kv_7yhr ot_clk (retargeted) | 0; M6 4.7 % peak | +490 / +555 intra | FAIL 9/3915: hg_ES_7->pc_ES_7 x4 (lo +73.8 TT / +1.0 FF), hub_Ei->Eo, pc_WN_6->7, hub_Wo->hroot_WN/WS, hg_WS_1->pc_WS_1 | bound 4402.6 (4403.2), CBC +8 | KV-CROSSING-1119 |
| HEAD NF15f 8fef0752 | link_htree 327 regions (head-plan-r4 t2p kit, cut for 65606a72) | 0; M8 0.68 % peak | +548 / +621 intra | FAIL 6/468 TT (5 lag: chE1_o0, turnE5/W5_t, host_rx__5, host_tx__6; chE5_b1 +96.6 < 100) | 834 system unchanged (+1 cyc) | FABLE-FIX-HEAD-MESH-O |

Intra hold is BLOCKED(kits) on every die: 0 pairs are on signed views, so no hold PASS is claimed.
Generic-tree hold numbers (posted 04:2x) are superseded and decide nothing.

## Core-tap clock offsets (coretap/<die>.tsv, coretap/summary.txt)
Early hard-core taps: die-tree early-ness vs the partition's regular taps, against need = signed lib max_clock_tree_path - common latency.
- HEAD: lep_pair plan 103 early, die -34..-3 (106-137 ps late) = lep0N intra hold -176; he_epc need 38, die 13.
- KV: 2372 taps, off -105..+128 vs need; plan early 0 where signed needs 11-30 (kv3_pv_pair ins 228 vs signed 280).
- QC: qfd_tile_nk_a0c plan 483 vs need 568; die -213..-20 vs need; 895/1461 taps >50 ps late.
- S81 (generic tree, proxy): 4513/6256 >50 late; bf_col3_c/bf16_half/rom_elem plan 185/53/215 vs need 226/86/303.
Finding: plan early_ps < signed latency - common on all dies, and the die tree under-delivers even that, so cores are fed late by design.
Fix class: early_ps := signed max_clock_tree_path - common, per module.

## Kits
- S81 ECOv3 (epyc10 s81-die-r3-proto/kit_d7w_ecov3, 11-17 22:46): absent on every disk of every gen host. Not in ot-delete-guard; deleted by cleanup after 11-18 00:54.
- QC M4: epyc2 /srv/opentallas-scratch3/claude/fable-die-qc-r/chain/qc/s4q9m4/kit (copy at runs/qwen_compute/kit_m4_copy).
- No ot_clk config exists for S81 ECOv3 or QC M4 (configs are 10-28-era).
