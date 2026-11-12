#!/bin/bash
# KV-TIMING-FORMS-1 LEC: OLD = main b35eaa100a ot_fdi_phy_cdc + ot_async_fifo (renamed *_old); NEW = branch.  Runs in the ORFS yosys image.
cd /srv/opentallas-scratch2/claude/kvtf1; R=repo; W=lec; rm -rf $W; mkdir -p $W
git -C $R show b35eaa100a:rtl/lib/ot_async_fifo.sv | sed 's/\bmodule ot_async_fifo\b/module ot_async_fifo_old/' > $W/old_fifo.sv
git -C $R show b35eaa100a:rtl/physical/ot_fdi_phy_cdc.sv | sed 's/\bmodule ot_fdi_phy_cdc\b/module ot_fdi_phy_cdc_old/; s/\bot_async_fifo #/ot_async_fifo_old #/; s/\bot_fdi_up_rsync\b/ot_fdi_up_rsync_old/g' > $W/old_cdc.sv
cp $R/rtl/lib/ot_async_fifo.sv $R/rtl/physical/ot_fdi_phy_cdc.sv $R/rtl/lib/ot_reset_sync.sv $W/
mk() { # tag newparams
cat > $W/$1.ys <<YS
read_verilog -sv -DSYNTHESIS $W/old_fifo.sv $W/old_cdc.sv $W/ot_reset_sync.sv
read_verilog -sv -DSYNTHESIS $W/ot_async_fifo.sv $W/ot_fdi_phy_cdc.sv
chparam -set W 522 -set DEPTH 8 -set SEL_PIPE 1 -set SEL_CHUNK 8 ot_fdi_phy_cdc_old
chparam -set W 522 -set DEPTH 8 -set SEL_PIPE 1 -set SEL_CHUNK 8 $2 ot_fdi_phy_cdc
hierarchy -check
proc; flatten; opt_clean; memory -nomap; memory_map; opt -fast
rename ot_fdi_phy_cdc_old gold
rename ot_fdi_phy_cdc gate
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 4
equiv_induct -seq 4
equiv_status -assert
YS
}
mk eq_default ""
mk eq_rc4 "-set SEL_RSTC 4"
for t in eq_default eq_rc4; do
 timeout 3000 docker run --rm --network=none --memory=24g -v $PWD:/w -w /w openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $W/$t.log $W/$t.ys > $W/$t.out 2>&1
 echo "$t rc=$? $(grep -h 'Found.*equiv\|Of those\|unproven\|Equivalence successfully' $W/$t.log | tr '\n' ' ')" >> $W/RESULT
done
echo DONE >> $W/RESULT
