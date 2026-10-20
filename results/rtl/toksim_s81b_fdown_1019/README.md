# TOKSIM-S81B/FDOWN 10-19: ffn.down on the release frame RTL

Vehicle: u_f_0L00 (col_h9_l4_nx, LK 5) of the p4l-MU die, GEN mu4c 19bf4121e RTL (78/78 RTL files blob-identical,
rtl_blob_vs_release_19bf4121e.txt), Verilator 5.050. The full multi-phase L0 field of the frame is compiled once
(xs_place.compile_frame); the 21 ffn.down phases (shared FP8 + 6 routed FP4 experts, K 2304, real rank-0 rows the
frame owns = 10 rows per expert, 70 rows) run one at a time and then as per-expert sequences (3 phases each, 4/4/2 rows).
Every row is checked by xs_place check: segment-tree values bit-exact vs golden, coverage, calendar edge-exact, fixture BF16 tie.
Tools: tools/s81_dv/layer_prog/qf_producer/toksim_fdown_frame_{gen.py,bench.sh}; bench tb_toksim_fgu_seq.sv and
toksim_fgu_check.py copied verbatim from TOKSIM-S81B/FGU.

Results:
- singles: 21/21 PASS (70/70 fixture rows); mutants swap / shift FAIL (witnesses).
- sequences (go period P): PASS at P >= 130 for all 7 experts; P <= 120 the element faults (status 11), so the floor is in (120, 130].
  go0 -> last frame-root RET = 2 P + 289 (routed) / 2 P + 301 (shared): 549 / 561 at P 130.
- Whole instance per frame (21 phases), composed: 20 x 130 + 289 = 2889 edges, if the next expert's x is ready by the next go
  (the frame bench holds one x per run, so the expert switch is not in one run). Sum of the separate per-expert spans = 3855 (upper bound).
- Priced tail added for the DAG node: 195 (frame root -> CAP pipe + hub return, as FIELD wq_b) -> 3084.

The previous fullsix attempt's 'golden != fixture 560' was a vehicle bug (bf16 bits compared at 32 bit vs fixture >> 16), fixed in toksim_fdown_program.py; that route was not rerun.
