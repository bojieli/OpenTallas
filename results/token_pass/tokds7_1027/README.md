# TOK-DS-7 (2026-10-27): DS ROM token pass on main 262d07038 (ROOT-MERGE-28) + codex/ds-compiler-2005@e4267efa3

Source: claude/tok-ds-7-1027 = main 262d07038 (head-core-r11, head-rtl5, s81-rowx3) + codex ROWX helper (additive, clean
merge 91715602d1) + 3 tool fixes below. Vehicle: tree_fc31 die tree (legacy) + selected current sources
(OT_S81_SELECTED_SOURCE_ROOT = this worktree, 877 strict-bound define set, asbuilt_b178_coll.json), compile.sh.
intel1 ot-run units: ccA oth-ubuntu-1111248-1793090067, ccB 1111246-1793090067, ccC 1126604-1793090240,
ccD 1246424-1793091332, head legs 1215962-1793091094, beat rerun 1298027-1793092037.

## Fixes (each found by running the pass on main)
1. xr_timing.XRT_MODEL: main's ot_s81sl_xrt.sv = 59a53960 (844ead2a8b cores-kits lint: loop indices scoped) was
   unqualified -> EVERY layer compile on main refused (prepare_frame_schedules ValueError). Diff vs d09cf3f6 normalised
   for loop-variable declarations is empty -> same 7 V-CTL edges.
2. lower_svc Job: L20 (ratio 1) indexer selects id 1048575 = the compressed row this token appends (attn.cmp.row_qdq);
   the state image holds 1,048,575 rows -> IndexError. The row is appended with the fixture writer's packing
   (LC.pack_fp4_e4m3), as toksim_gl24_attnfix already does. No-op when no appended row is selected (L2/L14 unchanged).
3. head_mtp_fleet.sh beat leg: main ot_s81sl_vp instantiates ot_sram_1r1w_512x128_m4_r0c0 (no-repair view); the
   recipe only listed r2c2 -> 81/81 beat builds MODMISSING. Added the r0c0 model; LEGS= subset option.

## Per-layer compile (LOWERED / PARTIAL / GAP of ops; priced static span, cycles)
| layer | fixture | L/P/G | span | GAPs |
|---|---|---|---|---|
| L0 sliding | r0 (10-18) | 23/38/4 of 65 | 13450.5 | attn.rows_allgather, attn.out_allreduce, substage_hop0, ffn.router_allgather |
| L2 ratio2+idx | r3 new | 27/50/6 of 83 | 26100.2 | + attn.idx.topk_merge, substage_hop1 |
| L14 engram+ratio2+idx | r3 (fix_r3), shard die 0 | 27/57/8 of 92 | 26067.4 | + eng.rows_allgather, eng.knorm, eng.gate, attn.idx.topk_merge |
| L20 ratio1+idx+cand | r3 new | 27/52/5 of 84 | 28115.9 | + attn.idx.topk_merge |
| head | HEAD r0 | 0/4/4 of 8 | 11334.4 | head.lm_head, head.argmax, head.argmax_merge, token.return |
| mtp_draft | (none) | 0/0/11 of 11 | 42457.5 | all draft.head/markov/fixed |
New fixtures L2/L20 rank 3 (13/13 golden checks true) and MTP rank 0 (16/16 true) generated from the released checkpoint.

## RTL component benches on main sources (head_run/)
- tp4 (4-rank fused head argmax + TP4 merge, 129,280 logits): head PASS, draft0..4 PASS, mutants mut_lg / fh0 FAIL as
  required; HEAD_INTERIM 10953.9 (priced terms + measured tail 16) vs priced 11334.4.
- xfin16 base PASS (80 y vectors, y_err 0, last_partial_to_first_rstd 234 = model 234).
- egress rstopt_xo BENCH_PASS, xooff negative control FAILED as expected.
- wave smoke PASS (15 steps, 191,763 cycles, errors 0); mut_sseq_earlydone FAIL as required; wave/wave, mut_hep_stale,
  xfin mutleaf still running at commit (not collected).
- bundle / dhead legs NOT RUN: tools/s81_ftok/live_head_return.py and qf_producer/toksim_mtpd_draft_head.py were
  never merged to main (only on 0a85a2733).
- beat (80 beats + mutant): rerun after fix 3, not collected at commit.

Not done: per-layer slice-cut RTL replays (run_layers) -- the only cut kits (tok-ds-dskr veh, 1e7adc7) are fc30-era;
206 kit sources differ from main (69 RTL files incl. vp/vs/vsw/xrt/bk_sel/seq_host) -> a replay there is not the current
die. Whole-layer L14 carve still blocked (157 stim inputs, 84 ROM ids). Inter-die array collectives: no current-RTL
vehicle. full_token_qualified false.
