# TOKSIM-S81C/GATH: attn.gather and attn.window_load on the S81 p4l-MU release RTL (10-19/20)

Both ops are measured on the release svc_rs RTL (16 x `dsdv_svc_rs`, protect-libs from git archive 19bf4121e). Every
checked row is bit-exact vs the released-checkpoint layer fixtures. Record: `GATH.json` (built by `mk_gath_json.py`).

| DAG op | old per instance | measured | definition |
|---|---:|---:|---|
| attn.gather L2/L8/L14 | 808 | **577** (worst of the views run so far) | SEL_IDS header at the entry q pins -> last owned selected-row HBM beat at the slices |
| attn.gather L20 | 819 | **618** | same |
| attn.gather L24..L36 | 811 | old (no fixture) | |
| attn.window_load (all four classes) | 300.9 / 169.9 / 265.9 / 207.1 | **532** | WIN_LOAD frame -> last window-row read beat before GO |

## attn.gather vehicle (new, bench-only)
- `tools/s81_dv/layer_prog/toksim_gath_vectors.py` turns a layer fixture (`/home/ubuntu/scratch/layerbench-s81/fixtures/L2`, `L20`)
  into the `tb_dsdv_svc_rs` case format. It uses the real 512 `attn.idx.topk_final` ids, the stored FP4 rows from fixture state
  (plus real neighbour rows), the window state + own row, q_rope and exp. It asserts bitwise that the stored rows decode to
  `attn.gather` / `attn.window_load` / `attn.rows_allgather`, that scores x scale equal `attn.scores`, and that P.V equals `attn.pv`.
- `rtl/dsrom_sys/s81_dv/svc_rs/test/tb_toksim_gath.sv` is an observation copy of `tb_dsdv_svc_rs.sv` (made by `scripts/mk_tb.py`). It adds
  `+sel_gap` and the `GATH_T` line. The checks are unchanged. It runs with `+static_io=1`: fixed issue and HBM latency 40.
- Owner views: the bench is DIE 0 / ST 0, and `--view D,S` XOR-relabels the owner bits of every id. This gives die D / stack S's owned
  set; PC, block and row stay unchanged. The first job ran views L2 (0,0), (1,1) and L20 (0,0), (1,3). The other 28 views are pending.
- Finding: the span does not depend on the window traffic (sel_gap 800 gives the same 577). It is set by the slice SEL scanner
  (one rank a cycle over 512 ranks) plus the last fetch.
- Mutant witness: one E2M1 code of an owned row is flipped in HBM. The run then FAILs (sc/se/pv errors 16, `runs/run_L2_v00_mut_g0.log`).

## attn.window_load
- This is the collected TOKSIM-S81/IDX L0 `tb_svc_lower` run (compiled lower_svc frames, HBM model latency 40..55): seeds 530 / 532,
  PASS, with the slot / late mutant witnesses FAILing.
- In the T-640 gather vehicles, WIN_LOAD -> last window read is 424 at a static latency of 40. The window reads all come before the
  owned-row reads.
- FINDING: the load is credit x latency bound (DQ 8 a PC). At latency 100 it takes 1,063 cycles (PASS). At latency 180 the window has not
  landed by the compiled GO, and the run FAILs (`window_load/run_lat180_s1.log`). The lower_svc W_SLACK 560 assumes HBM latency <= 56.

Edges owed: +2 (L20 B1 svc splice, once dsdv_idx_rg binds). The HBM latency is the bench model's.
