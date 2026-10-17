# tb_s81dv_xfin16, parallel-tree finish (RTL at d9af7ddfc, before the sequenced finish)

- Host ot-epyc4, Verilator 5.032 (version.txt).
- Run: `./run.sh x_base tb_s81dv_xfin16` (bundle = tools/s81_dv/norm16_bench.sh inputs).
- Result: `DVXFIN16 slices=16 y_vecs=80 y_err=0 rstd=16 rstd_distinct=0 rstd=3fbf858b fault=0 last_partial_to_first_rstd=171 rstd_spread=53`, then PASS.
- All 80 DS1M golden y vectors match bit for bit. All 16 slices produce the same rstd.
- Superseded design: the remote gate failed the clock rule (58,687 flops on one root). The sequenced finish replaces it.
- Negative controls were not run on this RTL; they are run on the sequenced finish.
