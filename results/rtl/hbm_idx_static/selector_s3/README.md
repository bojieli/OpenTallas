# L2H-IDXSEL s3 -- landed IDX selector cluster (LEAD3-HBM route B), evidence

Source: branch claude/l2h-idxsel-s3-1019. RTL rtl/hbm_accel/index/sel_s3/ (quadrant tile ot_hidx_s3_q x4, ctl tile
ot_hidx_s3_ctl, flat parent ot_hidx_s3_flat, generated landed parent lp/ot_hidx_s3_flat_lp, die master ot_hbm_idx_selector_s3
with the port list of the die's current master ot_hbm_idx_selector_static_sel). Spec tools/landed_parent/specs/hidx_sel_s3.json.

## Structure
- 5 clock regions: ctl (u_ctl) + q0..q3 (u_q0..u_q3, one hardened tile). 20 landed crossings (D 4, E 2, +3 edges, shared write
  rings, landing_reset_lead), 1-bit reset runs only (depth 2). Landing flops 1,252 (ot_hidx_s3_flat_lp_record.json).
- Only control crosses: cw (14 b) and thr (16 b) ctl -> every quadrant, ties_<q> (14 b) ctl -> q, ret_<q> (25 b: histogram read
  + the op tags of the edge that read it) and qf_<q> (1 b) q -> ctl. The 2 x 2,368-bit line faces are per-quadrant ports on the
  quadrant's own clock (no landing, no ring flops on the wide data).
- ctl <-> quadrant is a loop: lp.py reschedule mode; the re-schedule is the IDX compiler's.

## Schedule (tools/hbm_idx_static_calendar.py, table registered_s3; legacy tables byte-identical)
| term | s2 (registered) | s3 (registered_s3) | why |
|---|---|---|---|
| sel_in (op word -> quadrant core) | 3 | 7 | ctl pin flop + ctl output flop + landing 3 + quadrant pin copies + P2 |
| sel_in_line (score line -> core) | 3 | 2 | quadrant pin flop in_p1 + in_p2 (line port on the quadrant clock) |
| sel_out (selected stream) | 2 | 1 | S3 register -> quadrant output pin flop |
| sel_choose_rt (idle after each op5 run) | 0 | 8 | threshold back at the quadrant 12 edges after the deciding hist read (flat 3), ties 13 (flat 4) |
| sel_scan_drain | 2 | 2 | op4 -> op5 drain is quadrant-internal |
IDX frame 1411 -> 1433 edges (+22, +1.56 %); scan -> TX 14 -> 17 (+3); first TX instruction 1283 -> 1305.
Price: DS (V4.1 HBM): the IDX-PIPE ledger (lanes/HBM-IDXPIPE.md) has IDX 7,872 exposed edges/token on ~0.99 M edges/token,
i.e. ~5.6 frames' worth: +22 edges/frame -> <= ~+123 edges/token (<= ~0.012 %) if every frame edge were exposed (the
critical scan -> TX path grows +3 edges/frame -> ~+17 edges/token). Qwen: no IDX (DeepSeek indexer only) -> 0.

## Benches (Verilator 5.050, fleet ot-epyc5, src = claude/l2h-idxsel-s3-1019 @9d744adab; sources_*.sha256 == the commit)
- sel/ rtl/test/hbm_idx_static/run_selector_s3.sh: full shape, 4 frames (frame 0 = CRAFTED margin frame of
  tools/hbm_idx_s3_selector_vectors.py: the 512th key sits on pass-2 bin 0 with one tie in quadrant 0 line 0 and pass-2 bin-63
  keys in line 170; frames 1..3 = the historical frames), selected stream exact vs gold.
  m0 PASS (4 x checked512 errors0 fault0). FAIL ("fullshape exact selector mismatch"): d1 tie compare >=, d3 lane-5 SRAM
  write-data copy late, d5 histogram read one edge after its tags, d6 ctl tags one edge early, rt7 choose spacing one edge
  short (frame 0: 511 chosen), dr3 scan drain one short (frame 0 rank shift: the s1 'mut_drain survives' gap is closed here),
  l1 lp landing 0 bypassed, l2 landing 0 read K+1.
- lp/ generated lockstep bench (landed vs the reschedule reference, scripted programme rtl/hbm_accel/index/sel_s3/lp/tb_hidx_s3_stim.svh):
  AUDIT PASS, unland mutant audit FAIL, MUT 0 PASS, MUT 1 / 2 / 4 / 5 FAIL -> BENCH_EXIT 0.
- sched/ rtl/test/hbm_idx_static/run_scheduled_s3.sh (calendar SRAM + full IDX parent, -DOT_IDX_SEL_S3, crafted operands
  IDX_VEC_CRAFT=1): see sched/README.md when collected (pending_results).
