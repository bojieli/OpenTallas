#!/bin/bash
# DIE-QC-58B LEC (DIE-QC-16 lec.sh recipe; main already has the me_idle port so no gold hook): gold = origin/main a0c,
# gate = branch a0c, body black box.  off: defaults (ICG 0)  icg1: ICG 1 both sides, ICG_EREG 0 on the branch  (must be EQUIVALENT)
set -uo pipefail
cd /srv/opentallas-scratch2/claude/wt/die-qc-58b; Y=$HOME/.local/opentallas-tools/bin/yosys
for t in nl nk; do O=/srv/opentallas-scratch2/claude/die-qc-58b/lec/$t; mkdir -p $O
 sed "s/module qfd_tile_${t}_a0c /module gold /" /srv/opentallas-scratch2/claude/die-qc-58b/lec/main_$t.sv > $O/gold.sv
 sed "s/module qfd_tile_${t}_a0c /module gate /" rtl/physical/a0_core/qfd_tile_${t}_a0c.sv > $O/gate.sv
 sed -e "s/module qfd_tile_${t}_a0c /module gate /" -e "s/\.tile_id(tile_id)/.tile_id(~tile_id)/" rtl/physical/a0_core/qfd_tile_${t}_a0c.sv > $O/gate_mut.sv
 echo "module ICGx8DC_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK); assign GCLK = CLK & (ENA | SE); endmodule" > $O/icg_model.v
 for L in off icg1 mut; do G=$O/gate.sv; P=""; [ $L = mut ] && G=$O/gate_mut.sv; [ $L = icg1 ] && P="chparam -set ICG 1 gold gate"
 cat > $O/$L.ys <<YS
read_verilog -DSYNTHESIS -sv -lib rtl/physical/a0_rc14_selected_2000/qfd_tile_${t}_rp2_45.sv
read_verilog -DSYNTHESIS -sv $O/icg_model.v
read_verilog -DSYNTHESIS -sv $O/gold.sv
read_verilog -DSYNTHESIS -sv $G
chparam -set REGROOT_MODE 9 gold gate
$P
hierarchy -check
proc
flatten gold gate
setundef -undriven -expose
async2sync
opt -full
opt_clean -purge
equiv_make gold gate lec_eq
hierarchy -top lec_eq
async2sync
equiv_struct
equiv_simple
equiv_induct
equiv_status -assert
YS
 $Y -q -l $O/$L.log -s $O/$L.ys >/dev/null 2>&1; rc=$?
 echo "LEC $t $L rc=$rc $(grep -o "Found [0-9]* .equiv cells" $O/$L.log | tail -1) $(grep -o "Found [0-9]* unproven" $O/$L.log | tail -1) -> $([ $rc = 0 ] && echo EQUIVALENT || echo NOT_EQUIVALENT)"
 done; done
