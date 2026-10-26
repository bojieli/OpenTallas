#!/bin/bash
# KVHR2 10-26: hr face recut for one core: yosys pre.json -> hr_face_ports.py -> <mod>.v ; equiv proof + mutant.
# usage: hr_face_ports.sh CORE_JSON OUTDIR   (run inside the ORFS image; yosys on PATH or ORFS install)
set -e
CJ=$1; O=$2; mkdir -p $O
HERE=$(cd $(dirname $0) && pwd)
Y=${YOSYS:-/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys}
MOD=$(python3 -c "import json;print(json.load(open('$CJ'))['module'])")
FILES=$(python3 -c "import json;print(' '.join(json.load(open('$CJ'))['files']))")
INC=$(for f in $FILES; do echo -n "-I$(dirname $f) "; done)
cat > $O/pre.ys <<YS
read_verilog -defer -sv -DSYNTHESIS $INC $FILES
hierarchy -top $MOD
proc
flatten
memory_collect
opt_clean
write_json $O/pre.json
YS
$Y -q -l $O/pre.log $O/pre.ys
python3 $HERE/hr_face_ports.py transform $O/pre.json $O/post.json $O/hr_face_ports.json --top $MOD
python3 $HERE/hr_face_ports.py transform $O/pre.json $O/mut.json $O/hr_face_ports_mut.json --top $MOD --mutant > /dev/null
cat > $O/emit.ys <<YS
read_json $O/post.json
select $MOD
write_verilog -selected $O/$MOD.v
YS
$Y -q -l $O/emit.log $O/emit.ys
# no absolute paths in the kit RTL (evidence reads repo-relative paths): drop the yosys src attributes; macro
# escaped instance identities remain intact so equivalence merges the SAME macro, not independent free outputs.
python3 - $O/$MOD.v <<'PY'
import re, sys
p = sys.argv[1]; t = open(p).read()
t = re.sub(r'\(\* src = "[^"]*" \*\)\s*', '', t)
open(p, 'w').write(t)
PY
for V in post mut; do
cat > $O/eq_$V.ys <<YS
read_json $O/pre.json
memory_share
memory_map
rename $MOD gold
design -stash g
read_json $O/$V.json
memory_share
memory_map
rename $MOD gate
design -copy-from g -as gold gold
equiv_make gold gate eq
hierarchy -top eq
expose -evert eq/t:ot_sram*
async2sync
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
set +e; $Y -q -l $O/eq_$V.log $O/eq_$V.ys > /dev/null 2>&1; echo "$V rc=$?" >> $O/eq_rc.txt; set -e
done
# round trip: the emitted kit RTL itself vs pre
BB=$(python3 -c "import json;print(' '.join(f for f in json.load(open('$CJ'))['files'] if f.endswith('_bb.v')))")
BBF=""; [ -n "$BB" ] && BBF="read_verilog -sv -DSYNTHESIS $BB"
cat > $O/eq_v.ys <<YS
read_json $O/pre.json
memory_share
memory_map
rename $MOD gold
design -stash g
read_verilog -sv $O/$MOD.v
$BBF
hierarchy -top $MOD
proc
memory_collect
memory_share
memory_map
rename $MOD gate
design -copy-from g -as gold gold
equiv_make gold gate eq
hierarchy -top eq
expose -evert eq/t:ot_sram*
async2sync
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
set +e; $Y -q -l $O/eq_v.log $O/eq_v.ys > /dev/null 2>&1; echo "emitted_v rc=$?" >> $O/eq_rc.txt; set -e
cat $O/eq_rc.txt
# The job status must report failed or incomplete proofs; the generator checks
# the same receipt before consuming the emitted RTL.
python3 - "$O/eq_rc.txt" <<'PY'
import pathlib, sys
actual = pathlib.Path(sys.argv[1]).read_text().split()
expected = ['post', 'rc=0', 'mut', 'rc=1', 'emitted_v', 'rc=0']
if actual != expected:
    raise SystemExit('HR face proof FAIL or incomplete: ' + ' '.join(actual))
PY
