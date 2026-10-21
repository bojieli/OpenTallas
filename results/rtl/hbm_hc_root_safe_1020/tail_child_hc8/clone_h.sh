#!/bin/bash
# HBM-HC7 fallback of clone.sh: the flat synth ABC ran >1.5 h without finishing (childc + plain child), so map each module
# on its own (synth WITHOUT -flatten; ABC per unique module), flatten AFTER mapping, then plain native32 census (baseline)
# + bound_fanout_clone + retained check + native32 census.   usage: clone_h.sh NAME TOP LIMIT FILE...
set -u
d=$(pwd); n=$1; top=$2; lim=$3; shift 3; src="$*"
rm -rf $d/s_$n; mkdir -p $d/s_$n && cd $d/s_$n && tar xzf $d/src.tgz
L=/srv/opentallas-scratch/claude/codex-sm9-native-north-1020/libs
LIBS="$L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
RL=""; AL=""; for f in $LIBS; do RL="$RL
read_liberty -lib $f"; AL="$AL -liberty $f"; done
cat > a.ys <<YS
read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST $src
hierarchy -check -top $top
tcl physical/common_flow/ot_keep_regs.tcl
synth -top $top -noshare
dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
abc $AL
opt_clean -purge
$RL
flatten
opt_clean -purge
hierarchy -check -top $top
write_json $d/mapped_$n.json
write_verilog -noattr $d/mapped_$n.v
tee -o $d/stat0_$n.txt stat
YS
yosys -q -l $d/a_$n.log a.ys > /dev/null 2>&1; echo "SYNTH_RC rc=$?" >> $d/a_$n.log
libs=""; for f in $L/*.lib; do libs="$libs --liberty $f"; done
[ -f $d/mapped_$n.v ] && { python3 tools/ref_tile/native_census.py --netlist $d/mapped_$n.v --top $top --out $d/census_p_$n.json $libs > $d/census_p_$n.log 2>&1; python3 $d/summ.py $d/census_p_$n.json > $d/summ_p_$n.txt 2>&1; }
python3 tools/hbm_hc/bound_fanout_clone.py $d/mapped_$n.json --top $top --name ${top}_bfc --out $d/native_$n.v --limit $lim ${BFC_TAG:-} > $d/clone_$n.log 2>&1; echo "CLONE_RC rc=$?" >> $d/clone_$n.log
cat > b.ys <<YS
$RL
read_verilog $d/native_$n.v
hierarchy -check -top ${top}_bfc
tcl physical/common_flow/ot_keep_regs.tcl
synth -top ${top}_bfc -flatten -noshare
abc $AL
opt_clean
write_verilog -noattr $d/retained_$n.v
tee -o $d/stat1_$n.txt stat
YS
[ -f $d/native_$n.v ] && { yosys -q -l $d/b_$n.log b.ys > /dev/null 2>&1; echo "RETAIN_RC rc=$?" >> $d/b_$n.log; }
[ -f $d/retained_$n.v ] && { python3 tools/ref_tile/native_census.py --netlist $d/retained_$n.v --top ${top}_bfc --out $d/census_r_$n.json $libs > $d/census_r_$n.log 2>&1; python3 $d/summ.py $d/census_r_$n.json > $d/summ_r_$n.txt 2>&1; }
cd $d && rm -rf $d/s_$n; gzip -f $d/mapped_$n.json $d/mapped_$n.v
exit 0
