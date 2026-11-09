#!/bin/bash
# run.sh <repo_root_with_patched_rtl> <outdir> ; seeds x {base, mutants}
set -uo pipefail
R=$1; E=$2; mkdir -p $E; export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
S=$R/rtl/dsrom_sys/s81_link
: > $E/summary.log
build(){ D=$E/obj_$1; ARGS=(); [ "$1" != base ] && ARGS+=("-D$1"); [ "$1" = MUT_ENC_CONST ] && ARGS+=("-DH0CONSTMUT");
 verilator --binary --timing -j 4 -O1 -Wno-fatal --x-initial unique --x-assign unique --top-module tb --Mdir $D -o tb -I$S "${ARGS[@]}" $E/tb_h0.sv $3 $S/ot_s81_kp4_common.sv > $E/build_$1.log 2>&1; }
cp "$(dirname "$0")/tb_h0.sv" "$E/"
build base x $S/ot_s81_kp4_enc.sv || { echo build fail; exit 2; }
for seed in 1 2 3 7 11; do $E/obj_base/tb +verilator+rand+reset+2 +verilator+seed+$seed > $E/base_s$seed.log 2>&1; echo "base seed $seed rc=$? $(grep H0_RESULT $E/base_s$seed.log)" >> $E/summary.log; done
# mutant 1: one input bit flipped on B only (test sensitivity)
build MUT_H0_SEQ x $S/ot_s81_kp4_enc.sv; $E/obj_MUT_H0_SEQ/tb +verilator+rand+reset+2 +verilator+seed+1 > $E/MUT_H0_SEQ.log 2>&1; echo "MUT_H0_SEQ rc=$? $(grep H0_RESULT $E/MUT_H0_SEQ.log)" >> $E/summary.log
# mutant 2: enc copy whose H0_SEQ_ONLY constant is A5D instead of A5C
sed "s/{12'hA5C, h0_s}/{12'hA5D, h0_s}/" $S/ot_s81_kp4_enc.sv > $E/enc_mut_const.sv
build MUT_CONST x $E/enc_mut_const.sv; $E/obj_MUT_CONST/tb +verilator+rand+reset+2 +verilator+seed+1 > $E/MUT_CONST.log 2>&1; echo "MUT_CONST rc=$? $(grep H0_RESULT $E/MUT_CONST.log)" >> $E/summary.log
# mutant 3: header seq off by one (wrong seq captured)
sed "s/if (H0_SEQ_ONLY != 0) h0_s <= seq;/if (H0_SEQ_ONLY != 0) h0_s <= seq + 8'd1;/" $S/ot_s81_kp4_enc.sv > $E/enc_mut_seq.sv
build MUT_SEQ x $E/enc_mut_seq.sv; $E/obj_MUT_SEQ/tb +verilator+rand+reset+2 +verilator+seed+1 > $E/MUT_SEQ.log 2>&1; echo "MUT_SEQ rc=$? $(grep H0_RESULT $E/MUT_SEQ.log)" >> $E/summary.log
cat $E/summary.log
