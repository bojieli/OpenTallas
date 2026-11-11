#!/bin/bash
# S81-ARCH-RTL-2 11-11: t73 vs->vq pin cycle (CS_U_D) leaf bench, docker verilator 5.032 (tools/s81_slice/leaf_bench.sh body)
W=/srv/opentallas-scratch3/claude/s81-arch-rtl-2; R=/srv/opentallas-scratch3/claude/wt/s81-arch-rtl-2; L=$W/leaf
T73="-GCS_Y_D=1 -GCS_VNI_D=1 -GCS_SW_D=1 -GCS_SWR_D=1 -GCS_HI_D=2 -GCS_HO_D=2"
run() {  # tag  extra-verilator-args
  local O=$L/$1; mkdir -p $O; rm -rf $O/run; cp -r $L/gold/run $O/run
  docker run --rm --name a2leaf_$1 --cpus 8 --memory 24g -u $(id -u):$(id -g) -e HOME=$O -e CCACHE_DISABLE=1 -v $W:$W -v $R:$R -w $R \
    --entrypoint bash verilator/verilator:v5.032 -c "
    srcs=\"\$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_leaf.sv\"
    verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $2 -GMUT=0 -GBEAT=37 -GXMEM=2 --top-module tb_s81sl_leaf -Mdir $O/obj \$srcs --build-jobs 8 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -5 $O/build.log; exit 3; }
    cd $O/run && timeout 3000 ../obj/Vtb_s81sl_leaf > ../run.log 2>&1; echo rc=\$?"
  echo "$1: $(grep -E '^PASS|^FAIL|TIMEOUT' $O/run.log | head -2 | tr '\n' ' ')"
}
run t73base "$T73" & run t73u1 "$T73 -GCS_U_D=1" & run t73u1mut "$T73 -GCS_U_D=1 +define+OT_S81SL_CST_MUT_UV" & run t73u2 "$T73 -GCS_U_D=2" & wait
