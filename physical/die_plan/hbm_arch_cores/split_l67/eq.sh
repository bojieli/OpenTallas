#!/bin/bash
# eq.sh VAR MASTER "PARAMS" CORE CMP.sv OUTDIR : gold = scoped as-built master (leaves/SRAMs everted), gate = cmp_top
set -u
V=$1; TOP=$2; PRM=$3; CORE=$4; CMP=$5; O=$6
R=/srv/opentallas-scratch/claude/elem-hbm/recipes2; WT=/srv/opentallas-scratch/claude/elem-hbm/wt-recipes2
Y=$HOME/.local/opentallas-tools/bin/yosys
mkdir -p $O; SUF=__d4g_$V; LEAF=ot_hdc_v41x_hcp_lanes$SUF
M=$WT/physical/asap7_memory_macros_v2
BB="read_verilog -lib $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v; read_verilog -lib $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v"
CH=""; for kv in $PRM; do CH="$CH -set ${kv%%=*} ${kv#*=}"; done
EV="expose -evert t:$LEAF t:ot_sram_1r1w_1024x256_m2_r2c2 t:ot_sram_1r1w_128x256_m1_r2c2"
sed "s/ot_hdc_v41x_hcp_lanes /$LEAF /g" $WT/rtl/hbm_accel/cores_split/ot_hbm_hc_bankq_static/ot_hbm_hc_bankq_lanes3_core.sv > $O/lanes3_scoped.sv
cat > $O/gold.ys <<YS
$BB
read_verilog -sv -DSYNTHESIS $R/src/$V.sv
${CH:+chparam $CH $TOP}
hierarchy -check -top $TOP
proc; opt_clean; memory_map; opt_clean
blackbox $LEAF
flatten; opt_clean; splitnets
async2sync
$EV
rename $TOP gold
write_rtlil $O/gold.il
YS
cat > $O/gate.ys <<YS
$BB
read_verilog -sv -DSYNTHESIS $R/src/$V.sv
read_verilog -sv -DSYNTHESIS $R/core/$CORE.sv
read_verilog -sv -DSYNTHESIS $O/lanes3_scoped.sv
read_verilog -sv -DSYNTHESIS $CMP
hierarchy -check -top cmp_top
proc; opt_clean; memory_map; opt_clean
blackbox $LEAF
flatten; opt_clean; splitnets
async2sync
write_rtlil $O/gate_pre.il
YS
$Y -q -l $O/gold.log -s $O/gold.ys || { echo GOLD_FAIL; exit 2; }
$Y -q -l $O/gate.log -s $O/gate.ys || { echo GATE_FAIL; exit 2; }
python3 - $O/gate_pre.il $O/gate_ren.il <<'PY'
import sys, re
s = open(sys.argv[1]).read()
decl = set(re.findall(r'^\s*(?:wire|cell)\b.*? (\\\S+)$', s, re.M))
ren = {}
for d in decl:
    if d.startswith('\\u_core.u_x.'):
        n = '\\' + d[len('\\u_core.u_x.'):]
        if n not in decl:
            ren[d] = n
s = re.sub(r'\\u_core\.u_x\.\S+', lambda m: ren.get(m.group(0), m.group(0)), s)
for inst, g0 in (('u_l02', 0), ('u_l35', 3)):
    for k in range(3):
        s = re.sub(r'(cell \S+ )\\' + inst + r'\.u_lg' + str(k) + r'\n', r'\1\\u_c.u_b.u_st.g_lg.g_grp[' + str(g0 + k) + r'].u_lg\n', s)
s = s.replace('module \\cmp_top', 'module \\gate')
open(sys.argv[2], 'w').write(s)
PY
cat > $O/eq.ys <<YS
$BB
read_verilog -sv -DSYNTHESIS -lib $R/src/$V.sv
read_rtlil $O/gold.il
read_rtlil $O/gate_ren.il
cd gate
$EV
cd ..
cd gold
$EV
cd ..
tee -o $O/ports_gold.txt portlist gold
tee -o $O/ports_gate.txt portlist gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 4
equiv_induct -seq 4
tee -o $O/equiv_status.txt equiv_status
equiv_status -assert
YS
$Y -q -l $O/eq.log -s $O/eq.ys; rc=$?
echo "EQ rc=$rc"; tail -5 $O/equiv_status.txt
exit $rc
