#!/bin/bash
# usage: run.sh SRC_TREE OUTDIR [extra verilator defines]   (verilator 5.032, as results/dh58_turnb_1103/wreg_equiv)
R=$1; O=$2; shift 2; mkdir -p $O; cp $(dirname $0)/tb_reader_start_equiv.sv $O/
docker run --rm --memory=8g --cpus=4 -v $R:/r:ro -v $O:/o -w /o verilator/verilator:v5.032 --binary --timing -Wno-fatal -Wno-lint -Wno-style "$@" \
  --top-module tb -o tbx tb_reader_start_equiv.sv /r/rtl/common/ot_dp_clk_landing_ca.sv /r/rtl/common/ot_meso_fifo.sv /r/rtl/common/ot_dp_clk_landing.sv > $O/build.log 2>&1 || { tail -20 $O/build.log; exit 1; }
docker run --rm --memory=8g -v $O:/o -w /o --entrypoint /o/obj_dir/tbx verilator/verilator:v5.032 +seed=7 +n=300 > $O/run.log 2>&1
tail -12 $O/run.log
