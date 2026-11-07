#!/bin/bash
# bench_rw.sh RTL_PATCHED.sv MACROS_DIR OUT [CYC]: ot_q2nf_rest old (no define) vs OT_Q2NF_RW, every output every cycle.
# m0 must PASS. Mutants on the new branch only, each must FAIL: m1 link rd addr bit0 flipped, m2 link w_mask 0, m3 issuer rd_out bits 0<->1 swapped, m4 link wd bit 0<->1 swapped, m5 issuer write addr bit0 flipped
H=$(dirname $(readlink -f $0)); R=$1; MD=$2; O=$3; C=${4:-6000}; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
python3 -I $H/gen_tb.py $R $O/tb.sv $C
python3 -I $H/mut_rw.py $R $O
M="$MD/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $MD/ot_sram_1r1w_64x141_m1_r0c0_g141/ot_sram_1r1w_64x141_m1_r0c0_g141.v $MD/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v $MD/ot_sram_1r1w_256x256_m2_r0c0_g256/ot_sram_1r1w_256x256_m2_r0c0_g256.v $MD/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v"
for m in ${MUTS:-0 1 2 3 4 5}; do ( d=$O/m$m; rm -rf $d; mkdir -p $d
 $V --binary -O1 --no-timing -j 6 -Wno-fatal -Wno-lint -Wno-style -DSYNTHESIS -DOT_Q2NF_TGTQ1 --top-module tb --Mdir $d/obj -o sim $O/tb.sv $O/old_w.sv $O/n$m.sv $M --timing > $d/build.log 2>&1
 $d/obj/sim +verilator+seed+${SEED:-1} > $d/run.log 2>&1; echo "m$m: $(grep -E 'LOCKSTEP|MISMATCH' $d/run.log | tail -1) [$(tail -1 $d/build.log | cut -c1-60)]" ) & done; wait
