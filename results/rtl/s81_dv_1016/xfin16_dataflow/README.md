# tb_s81dv_xfin16 on the final xfin RTL (dataflow-issue sequenced finish, 8 regional reset copies)

- Host: ot-epyc4, Verilator 5.032. Run with `./run.sh <tag> tb_s81dv_xfin16 [+define+...]`; bundle = `tools/s81_dv/norm16_bench.sh` inputs.
- **Base: PASS.**
  - `DVXFIN16 slices=16 y_vecs=80 y_err=0 rstd=16 rstd_distinct=0 rstd=3fbf858b fault=0`, `last_partial_to_first_rstd=234`, `rstd_spread=13`.
  - All 80 DS1M golden y vectors match bit for bit, and all 16 slices produce the same rstd.
- **MUT_BASE** (slice 3 tags its partials as slice 4's): FAIL as required. 16 faults (duplicate leaves), no rstd.
- **MUT_LEAF history:**
  - A 0/1 swap is blind, because it only commutes one add.
  - A 1/2 association swap also PASSED on this row: (0+2)+(1+3) rounds identically to (0+1)+(2+3) for the DS1M partials.
  - The control is now a wrong-operand exchange (leaf 1 fed beat 2's partial), result in `mutleaf/`.
  - Order exactness rests on the golden match of the base run. A wider golden set (more rows) is S81-SLICE's slice-bench task.
- Latency: 234 cycles from the last beat partial to rstd at every slice, including the ring exchange on the 9-stage street / 29-stage end-link snake and the tail. The parallel-tree finish took 171, so the sequenced finish adds 63; it is priced in `tools/s81_dv/dv_price.py` (`norm_finish_seq`).
