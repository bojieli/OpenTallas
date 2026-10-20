QW-N59-4 hardened native59 split: fleet witnesses (Verilator 5.050 via ot-run, ot-epyc5) at source b3c92b7a6
(git archive), bench rtl/test/qwen_split/run_native59_split_bench.sh, commands cmds.tsv.  Reference DUT
qfd_native59_dv_service_r1 (SAFE 2, RST_FOREST 1, EMB_RELAY 1); split = qfd_native59_split_flat (SOFF 1 BOFF 0 ROFF 1)
and its landed form qfd_native59_split_flat_lp (lp_*: SOFF 6 BOFF 2 ROFF 6).  Positives PASS (every output lockstep;
rnd_*: 37.2k random edges, internal service + bank probes exact).  Every mutant FAILs with ^N59SPLIT_FAIL.
