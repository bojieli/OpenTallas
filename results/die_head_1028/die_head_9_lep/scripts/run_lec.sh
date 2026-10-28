#!/bin/bash
# usage: run_lec.sh <pair.sv> <tag>   (wiring LEC: the 4 leaf modules are read -lib = blackboxes)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-head-9-lep; R=/srv/opentallas-scratch2/claude/die-head-9/lep/lec
PAIRSV=$1; TAG=$2; mkdir -p $R
cat > $R/lec_$TAG.ys <<YS
read_verilog -sv -lib /w/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv
read_verilog -sv -lib /w/rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv
read_verilog -sv -lib /w/rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv
read_verilog -sv /w/rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_core.sv
read_verilog -sv /p/$(basename $PAIRSV)
read_verilog -sv /r/lec_wrap.v
hierarchy -check
proc
flatten lec_gold lec_gate
async2sync
opt_clean
stat lec_gold lec_gate
equiv_make lec_gold lec_gate eq
hierarchy -top eq
equiv_struct
equiv_simple -seq 2
equiv_induct
equiv_status -assert
YS
docker run --rm --name dh9-lec-$TAG-$$ --cpus=2 --memory=8g --memory-swap=8g -v $W:/w:ro -v $(dirname $PAIRSV):/p:ro -v $R:/r openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /r/lec_$TAG.log -s /r/lec_$TAG.ys" > $R/lec_$TAG.out 2>&1
echo "LEC $TAG rc=$?"; grep -E "Found [0-9]+ unproven|Proved|Equivalence successfully|unproven|ERROR" $R/lec_$TAG.log | tail -4
