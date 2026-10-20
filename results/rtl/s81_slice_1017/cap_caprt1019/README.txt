cap_bench (tools/s81_slice/cap_bench.sh) on ot-epyc5 via ot-run, Verilator 5.050, RTL at 3cfc67259 (HOURLY-S81/CAPRT 10-19:
u_n6 = ot_s81sl_cap_rt_retn + ot_s81_fadd_pipe defined in ot_s81sl_cap_rt.sv; shared ot_s81_retn_static.sv = main, byte-identical).
Vectors cap_model.py gen --case real --seed 1.  lint.out = the kit's lint bench sources (no retn_static): lint-ok.
base PASS: SLCAP lines identical to fa49ec3e9 (1280/1280 written, lat 43..84 mean 60.44): the move is 0 edges.
MUT1-4 raw: CAP_MUTANT_DETECTED (fail witnesses mut{1,2,3,4}_real1_raw.out).
