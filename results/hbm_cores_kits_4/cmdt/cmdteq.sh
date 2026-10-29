#!/bin/bash
# HBM-CORES-KITS-4: ot_static_cmd_target MODE 1 run_base/run_count constant fix: old vs new, MODE 0 / 1
cd /c; mkdir -p out
for mode in 0 1; do
  for v in old new; do
    cat > s_${v}_${mode}.ys <<YS
read_verilog -sv /c/$v/ot_static_cmd_target.sv
chparam -set MODE $mode ot_static_cmd_target
hierarchy -top ot_static_cmd_target
setattr -mod -unset keep_hierarchy *
proc; flatten; opt -full; memory -nomap; opt -full; clean -purge
tee -o /c/out/check_${v}_${mode}.txt check
rename -top g_$v
write_verilog -noattr /c/out/${v}_${mode}.v
YS
    yosys -q -s s_${v}_${mode}.ys > out/${v}_${mode}.log 2>&1 || echo "SYNTH FAIL $v $mode"
    echo "MODE $mode $v: check problems: $(grep -o "Found and reported [0-9]* problems" out/check_${v}_${mode}.txt || echo 0)"
  done
  cat > i_${mode}.ys <<YS
read_verilog /c/out/old_${mode}.v /c/out/new_${mode}.v
proc; async2sync; opt_clean
miter -equiv -flatten -make_outputs -ignore_gold_x g_old g_new miter
hierarchy -top miter
sat -verify -seq 12 -set-at 1 in_rst_n 0 -prove trigger 0 -set-def-inputs -set-init-zero miter
YS
  if yosys -q -s i_${mode}.ys > out/i_${mode}.log 2>&1; then echo "MODE $mode: miter (gold X ignored) BMC12 from reset PASS"; else echo "MODE $mode: miter BMC FAIL"; fi
done
echo DONE
