HBM face shells, collected 2026-10-25 by Codex

Source: claude/hbm-face-1024 at 3a81341c214a3790d29c24ca2a100ad0791a9ded.
Generation: 268/280 views. Latest available fleet synth records: 266 PASS, 2 not complete (idx_selector and idx_topk_link). No physical sign-off is claimed.

Eight representative shell equivalence benches PASS at 30,000 cycles: argmax, svc_pc, bankq lanes0_2, bankq lanes6_7_bank, lane_exp0, score_hcol HALF0 and corrected HALF1, sfu lane0. Zero shell/reference mismatches. Every bench catches an input flop bypass and both output latency mutants. svc_pc also reports two unobserved input mutants separately; its other input mutants are caught. Bench files retain the exact counts and kit hashes. The reference includes the +1 input and +1 output cycle shell latency.

The 32 HALF1 score views were regenerated with their recipe params, fixing the earlier HALF0 default elaboration. HALF1 has no dropped cf_in/cs_in bits; HALF0 legitimately drops 33.

Twelve generation failures remain diagnosed:
- hc_root tail0_rest/tail1_rest: MAP_AMBIGUOUS glue_1 combines fault, result[767:0], result_v; needs an explicit cut-bus adapter.
- coll_q2 body: del_flit absent from canonical cut map.
- sfu ctl: ro_v_e absent from canonical cut map.
- tkm root: x_u_u_g_tiles_0_e86_u_tile_clr absent from canonical cut map.
- hnx north/south: NO_RECIPE.
- vmdel five views: NPC mismatch on fill_v_i, fill_bank_i, fill_slot_i, fill_epoch_i, fill_data_i; native shape/pin tables must be reconciled.

The census uses the original B2n shell generation outlines. ep_static, sfustore and programme_store still need regeneration against the packing-corrected B2n outlines before P&R. Tables publish +1 input/+1 output cycle per core crossing and 4,369 unread input bits dropped across 202 distinct modules; the native bind/compiler must account for them before a token-pass claim.

Sources collected read-only from epyc1:/srv/opentallas-scratch2/claude/hbm-face (kits_all, gen_all_rc.txt, bench_res), and latest runs_synth face_guard records on epyc2/intel1/intel2. Existing failed evidence was retained.
