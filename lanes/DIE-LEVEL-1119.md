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
| KV D25c 4a40f1db | kv_7yhr ot_clk (retargeted) | 0; M6 4.7 % peak | +490 / +555 intra; intra hold -222.0 TT / -202.8 FF (open) | PASS 0/3915 TT+FF with KV-CROSSING-1119 A4 rows (worst lo +192.3 TT / +214.4 FF, start-skew 0/159). Was FAIL 9/3915 on the default CA recipe | bound 4402.6 (4403.2), CBC +8; A4 lat total 10486 vs 10164, re-price when plan_c follows | KV-CROSSING-1119 |
| HEAD NF15f 8fef0752 | record form: region.early + head_current_ca.py regions_hp1 (HEAD-CROSSING-1119 runs/s81_head/l1119e1, epyc10) | 0; M8 0.68 % peak | +608.6 / +663.2 intra | PASS 427/427 TT+FF (record-form CA). Earlier FAIL 6/468 was the generic start form, superseded | 834 system unchanged (+1 cyc) | HEAD-CROSSING-1119 |

Intra hold is BLOCKED(kits) on every die: 0 pairs are on signed views, so no hold PASS is claimed.
Generic-tree hold numbers (posted 04:2x) are superseded and decide nothing.

## Core-tap clock offsets (coretap/<die>.tsv, coretap/summary.txt)
Early hard-core taps: die-tree early-ness vs the partition's regular taps, against need = signed lib max_clock_tree_path - common latency.
- HEAD: lep_pair plan 103 early, die -34..-3 (106-137 ps late) = lep0N intra hold -176; he_epc need 38, die 13.
- HEAD 14:xx correction: with region.early the intra hold is -115.1 TT / -105.4 FF (kit-contract -76.1, setup +608.6/+663.2; was -176 generic). Next HEAD item: lep0N leaf skew t77->t103 125.7 ps (HEAD-CROSSING-1119).
- HEAD r6e (06:59 PST, s81_head_r6e_s0 plan 19cb134b, live). Intra hold TT/FF, checked in epyc10 head-crossing-1119/runs/s81_head/*/ca/sta_ca.log: generic -176 -> e1 region.early -115.1/-105.4 -> e2 lep0N max 387.7 -110.2/-101.1 -> e3 residual.snake -92.6/-104.5 (kit-contract -72.9, setup +631/+664). t77->t103 is gone. The worst now is tile leaf spread in every tile region (p90 86 ps), and the next fix is tile-region DME (HEAD-CROSSING-1119). The default-recipe CA in these runs still shows 3/468 fail; the record-form CA is 427/427 PASS.
- KV: 2372 taps, off -105..+128 vs need; plan early 0 where signed needs 11-30 (kv3_pv_pair ins 228 vs signed 280).
- KV 06:16 PST: core-early rows (ROWS-KV-CORETAP-1119, 985 taps raised to the signed lib) made hold worse: TT -222.0 -> -253.5, FF -202.8 -> -239.4. The worst pair is pc_ES_2 clk_c3<->clk_c4 (kv3_pc_v3 kvpc0 taps, no signed lib), and the kit delivers early only in 5 regions. Don't adopt; KV-CROSSING-1119 is splitting the hold by tap-pair type.
- QC: qfd_tile_nk_a0c plan 483 vs need 568; die -213..-20 vs need; 895/1461 taps >50 ps late.
- S81 (generic tree, proxy): 4513/6256 >50 late; bf_col3_c/bf16_half/rom_elem plan 185/53/215 vs need 226/86/303.
Finding: plan early_ps < signed latency - common on all dies, and the die tree under-delivers even that, so cores are fed late by design.
Fix class: early_ps := signed max_clock_tree_path - common, per module.

## Kits
- S81 ECOv3 (epyc10 s81-die-r3-proto/kit_d7w_ecov3, 11-17 22:46): absent on every disk of every gen host. Not in ot-delete-guard; deleted by cleanup after 11-18 00:54.
- QC M4: epyc2 /srv/opentallas-scratch3/claude/fable-die-qc-r/chain/qc/s4q9m4/kit (copy at runs/qwen_compute/kit_m4_copy).
- No ot_clk config exists for S81 ECOv3 or QC M4 (configs are 10-28-era).
