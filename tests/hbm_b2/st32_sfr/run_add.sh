#!/bin/bash
# adder XCUTS lockstep: X in 1 2 4 7 x DRST 0/1 + mutants (expect fail)
W=/home/ubuntu/scratch-root/claude/dhbm61-st32-work; cd $W; export PATH=$HOME/.local/opentallas-tools/bin:$PATH; mkdir -p add
S=../die-hbm-61-rtl-st32/rtl/hdc; A=$S/ot_hdc_fp32_add_lat.sv
sed 's/(e_shfa | {27.d0, e_sa})/e_shfa/' $A > add/mut_sticky.sv
sed 's/carry}), .q(f_q));/carry}), .q(f_q)); \/\/ mut/; s/add_val, dif, dif\[26:0\] | sentinel, carry/add_val, dif, dif[26:0], carry/' $A > add/mut_sentinel.sv
# mut_gover: cut G drops the overflow branch (old mut_gzero, the -0 guard, is equivalent: exact cancellation is already g_zero; old form has the same guard)
sed "/else if (g_over) begin y <= 32.d0; err <= E_OVERFLOW; end/d" $A > add/mut_gover.sv
for m in mut_sticky mut_sentinel mut_gover; do cmp -s $A add/$m.sv && echo "$m UNCHANGED"; done
one() { n=$1; f=$2; x=$3; d=$4; exp=$5; o=add/b_$n
  systemd-run --user --scope -q -p MemoryMax=8G verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -GX=$x -GDR=$d --top-module tb -Mdir $o -o tb tb_add.sv $f $S/ot_hdc_fastfp.sv $S/ot_hdc_prefix.sv > $o.build.log 2>&1 || { echo "$n BUILD_FAIL"; return; }
  $o/tb > $o.run.log 2>&1; echo "$n expect=$exp rc=$?: $(grep ADD_LOCKSTEP $o.run.log)"; }
for x in 1 2 4 7; do for d in 0 1; do one x${x}_d$d $A $x $d pass & done; done
one mut_sticky add/mut_sticky.sv 1 0 fail & one mut_sentinel add/mut_sentinel.sv 2 0 fail & one mut_gover add/mut_gover.sv 4 0 fail & wait
