#!/bin/bash
set -eu
P=$(cd "$(dirname "$0")" && pwd)
W=$(cd "$P/../../../../../../../.." && pwd)
O=${1:?fresh out};MODE=${2:-nominal}
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
test -x "$V"
"$V" --version
D="+define+OT_GUNIT_BF_M1REG+OT_GUNIT_BF_C1REG+OT_GUNIT_BF_SVREG"
case "$MODE" in nominal);;mut_ctl)D="$D +define+OT_GUNIT_BF_SVREG_MUT_CTL";;mut_bias)D="$D +define+OT_GUNIT_BF_SVREG_MUT_BIAS";;*)exit 2;;esac
F="$W/rtl/lib/ot_rst_relay.sv $W/rtl/hdc/ot_hdc_fastfp.sv $W/rtl/hdc/ot_hdc_prefix.sv
 $W/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv $W/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_sel_n32.sv
 $W/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $P/gold_gf4_fullband.sv $W/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f.sv $P/tb_gf5_fullband.sv"
sha256sum $F > "$O/sources.sha256"
"$V" --binary --timing -j 12 -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
 $D --top-module tb_gf5_fullband --Mdir "$O/obj" -o tb $F -CFLAGS -O1 > "$O/build.log" 2>&1 \
 || { echo GF5_BUILD_FAIL;grep -m8 %Error "$O/build.log";exit 2; }
for SEED in 11 37;do
 "$O/obj/tb" +SEED=$SEED > "$O/run_$SEED.log" 2>&1
 tail -3 "$O/run_$SEED.log"
 if [ "$MODE" = nominal ];then grep -q '^GF5_FULLBAND PASS$' "$O/run_$SEED.log"
 else grep -q '^GF5_FULLBAND FAIL$' "$O/run_$SEED.log";grep -q '^GF5 MISMATCH' "$O/run_$SEED.log";fi
done
echo "GF5_EXPECTED_RESULT_PASS mode=$MODE"
