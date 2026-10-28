#!/bin/bash
# usage: gen.sh TOP PARAMS(chparam string or "") TAG
TOP=$1; PS="$2"; TAG=$3
DEPS=$(ls /work/rtl/*.sv /work/rtl/*.v | grep -v ot_s81sl_vn.sv | tr '\n' ' ')
cat > /fv/$TAG.ys <<YS
read_verilog -sv -DSYNTHESIS $DEPS /fv/old_vn.sv
${PS:+chparam $PS $TOP}
hierarchy -check -top $TOP
proc; flatten; memory -nomap; memory_map; async2sync; opt_clean
rename -top gold
design -stash gold
read_verilog -sv -DSYNTHESIS $DEPS /fv/new_vn.sv
${PS:+chparam $PS $TOP}
hierarchy -check -top $TOP
proc; flatten; memory -nomap; memory_map; async2sync; opt_clean
rename -top gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
YS
yosys -q -l /fv/$TAG.log -s /fv/$TAG.ys > /dev/null 2>&1; echo "$TAG rc=$?"; grep -E "Found .* \\\$equiv|unproven|Equivalence successfully" /fv/$TAG.log | tail -3
