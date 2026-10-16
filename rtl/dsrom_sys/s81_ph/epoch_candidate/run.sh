#!/usr/bin/env bash
set -eu
iverilog -g2012 -s tb_s81_capture_epoch_release -o positive ot_s81_capture_epoch_release.sv tb_s81_capture_epoch_release.sv
vvp positive > positive.log
cat positive.log
iverilog -g2012 -DS81_EPOCH_MUT_EARLY_SERIAL -s tb_s81_capture_epoch_release -o mutant ot_s81_capture_epoch_release.sv tb_s81_capture_epoch_release.sv
if vvp mutant > mutant.log 2>&1; then
  cat mutant.log
  exit 1
fi
cat mutant.log
echo 'S81_CAPTURE_EPOCH_MUTANT_REJECTED PASS'
rstc=ot_s81ph_coll_rstc.sv
rstc_tb=tb_s81ph_coll_rstc.sv
if [ ! -f "$rstc" ]; then rstc=../ot_s81ph_coll_rstc.sv; rstc_tb=../test/tb_s81ph_coll_rstc.sv; fi
iverilog -g2012 -s tb_s81ph_coll_rstc -o legacy "$rstc" "$rstc_tb"
vvp legacy > legacy.log
cat legacy.log
