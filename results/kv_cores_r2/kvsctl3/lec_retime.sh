#!/bin/bash
# KV-KVSCTL-3 10-27: sequential LEC of the landed qkd_kvs_ctl with the DECLARED retiming.
#   gold = OLD cut (KVSCTL-2 dead-dropped core, native 41ac57c25f) + the declared changes only:
#          +1 landing regs on 305 sealed dcfg bits + boot__setup_ready, async reset on u_lprg w_data/w_zero/w_one
#   gate = NEW cut (core json of this dir, repo-relative): adds the 0-cycle retimes (layer/layer_e, auth, cf2 IN_LAND).
#   retime_wires.blacklist: the 8 retimed cf2 nodes internal OR nets m / q (gold = |fault_in(t), gate = |landed(t)) are NOT
#   name-matched (they are different signals by the declared retime); the node outputs, every pin and every flop are compared.
# usage (repo root): lec_retime.sh OLD_CORE_JSON GOLD_DIR OUT   (inside the ORFS image)
set -e
OLDJ=$1; GD=$2; O=$3; mkdir -p $O
NEWJ=results/kv_cores_r2/kvsctl3/rtl/qkd_kvs_ctl_core.json
Y=${YOSYS:-/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys}
GF=$(python3 -c "
import json,os,sys
fs=json.load(open('$OLDJ'))['files']
out=[]
for f in fs:
    b=os.path.basename(f)
    if b in ('qkd_kv_ctl_nc32_face.sv','qkd_kvs_ctl_nc32__leaf.sv'): f='$GD/'+b
    out.append(f)
print(' '.join(out))")
NF=$(python3 -c "import json;print(' '.join(json.load(open('$NEWJ'))['files']))")
inc(){ for f in $*; do echo -n "-I$(dirname $f) "; done; }
MAC="eq/t:ot_sram_1r1w_128x256_m1_r2c2 eq/t:ctl_sram_1r1w_64x128_p192"
cat > $O/lec.ys <<YS
read_verilog -defer -sv -DSYNTHESIS $(inc $GF) $GF
hierarchy -top qkd_kvs_ctl
proc
flatten
memory_collect
opt_clean
memory_share
memory_map
setattr -mod -unset keep_hierarchy
flatten
rename qkd_kvs_ctl gold
design -stash g
read_verilog -defer -sv -DSYNTHESIS $(inc $NF) $NF
hierarchy -top qkd_kvs_ctl
proc
flatten
memory_collect
opt_clean
memory_share
memory_map
setattr -mod -unset keep_hierarchy
flatten
rename qkd_kvs_ctl gate
design -copy-from g -as gold gold
equiv_make -blacklist results/kv_cores_r2/kvsctl3/retime_wires.blacklist gold gate eq
hierarchy -top eq
expose -evert $MAC
async2sync
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
set +e; $Y -q -l $O/lec.log $O/lec.ys > /dev/null 2>&1; rc=$?; set -e
echo "retime_lec rc=$rc" > $O/rc.txt
grep -A3 "Found .* \$equiv cells in eq" $O/lec.log | head -5 > $O/status.txt || true
grep "Unproven" $O/lec.log | head -50 >> $O/status.txt || true
cat $O/rc.txt $O/status.txt
