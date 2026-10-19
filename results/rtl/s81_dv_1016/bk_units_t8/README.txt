S81-TILES8/bk 10-18: dsdv_bk_sel bench at cc9078d48 (rung relays u_rs / u_rn, +1 rung cycle per direction; bench model RL=1).
Run on the fleet (ot-run, ot-epyc4, runner /tmp/s81t8bk/run_sel.sh): run_bk_bench.sh sel <out> <mut> [variants].
exact (base thru mir thrumir odd thruodd): DSDV_BK_SEL PASS mut=0 (through beats checked at the +1-cycle latency, errors 0).
mutants 1..4 (base thru odd thruodd): all DSDV_BK_SEL FAIL (fail witnesses for the g2 / sq / selc2 jobs).
