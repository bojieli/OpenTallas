#!/bin/bash
# usage: ext.sh VAR TOP "PARAMS(k=v ...)" ; out in ext/VAR
set -eu
V=$1; TOP=$2; PRM=$3; MERGE=${4:-0}
R=/srv/opentallas-scratch/claude/elem-hbm/recipes2; WT=/srv/opentallas-scratch/claude/elem-hbm/wt-recipes2
O=$R/ext/$V; mkdir -p $O
SUF=__d4g_$V
CH=""; for kv in $PRM; do CH="$CH -set ${kv%%=*} ${kv#*=}"; done
M=$WT/physical/asap7_memory_macros_v2
cat > $O/ext.ys <<YS
read_verilog -lib $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v
read_verilog -lib $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
read_verilog -sv -DSYNTHESIS $R/src/$V.sv
${CH:+chparam $CH $TOP}
hierarchy -check -top $TOP
proc
opt_clean
setattr -mod -set keep_hierarchy 1 ot_hdc_v41x_hcp_lanes$SUF
flatten
opt_clean
splitnets
opt_clean
$( [ "$MERGE" = 1 ] && echo "splitcells; select -set m w:u_c.u_b.u_st.g_lg.sss* %ci1; opt_merge -share_all @m; select -clear; opt_clean" )
cd $TOP
select -set ex c:u_c.u_b.u_st.g_lg.g_grp?0?.u_lg c:u_c.u_b.u_st.g_lg.g_grp?1?.u_lg c:u_c.u_b.u_st.g_lg.g_grp?2?.u_lg c:u_c.u_b.u_st.g_lg.g_grp?3?.u_lg c:u_c.u_b.u_st.g_lg.g_grp?4?.u_lg c:u_c.u_b.u_st.g_lg.g_grp?5?.u_lg
tee -o $O/excl.txt select -list @ex
submod -name REM c:* @ex %d
cd ..
setattr -unset src
select $TOP REM
write_json -selected $O/parent.json
select REM
write_verilog -selected $O/rem.v
YS
$HOME/.local/opentallas-tools/bin/yosys -q -l $O/ext.log -s $O/ext.ys
echo done $V
