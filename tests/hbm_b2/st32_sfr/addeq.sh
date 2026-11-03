#!/bin/bash
# default-parameter identity: ot_hdc_fp32_add_lat old (main) vs new, yosys-slang proc+flatten netlists; same sorted line set (only statement order differs)
W=/home/ubuntu/scratch-root/claude/dhbm61-st32-work; cd $W; export PATH=$HOME/.local/opentallas-tools/bin:$PATH; mkdir -p addeq
S=../die-hbm-61-rtl-st32/rtl/hdc
for v in old new; do f=$W/add_lat_orig.sv; [ $v = new ] && f=$S/ot_hdc_fp32_add_lat.sv
 for cfg in "3 -1 1" "4 -1 1" "4 1 1" "5 -1 1" "6 -1 1" "7 -1 1" "7 -1 0" "5 -1 0" "3 -1 0"; do set -- $cfg
  printf 'read_slang --keep-hierarchy --top ot_hdc_fp32_add_lat -G LAT=%s -G CUTS=%s -G DRST=%s %s %s/ot_hdc_fastfp.sv %s/ot_hdc_prefix.sv\nproc\nflatten\nopt_clean\nwrite_verilog -noattr addeq/%s_%s_%s_%s.v\n' $1 $2 $3 $f $S $S $v $1 $2 $3 > addeq/$v.$1.$2.$3.ys
  yosys -q -s addeq/$v.$1.$2.$3.ys > /dev/null 2>&1 || echo "yosys FAIL $v $cfg"
 done; done
for cfg in "3 -1 1" "4 -1 1" "4 1 1" "5 -1 1" "6 -1 1" "7 -1 1" "7 -1 0" "5 -1 0" "3 -1 0"; do set -- $cfg
 a=$(sed 1d addeq/old_$1_$2_$3.v | sort | sha256sum | cut -c1-12); b=$(sed 1d addeq/new_$1_$2_$3.v | sort | sha256sum | cut -c1-12)
 echo "LAT=$1 CUTS=$2 DRST=$3 old $a new $b $([ $a = $b ] && echo SAME_NETLIST_LINES || echo DIFF)"; done
