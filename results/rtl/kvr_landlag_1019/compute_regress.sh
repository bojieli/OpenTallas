#!/bin/bash
# KVR-LANDLAG: compute-die regression -- the dv2f14bi c_ctl slice (Q-XPF bi_plan) annotated by the ORIGINAL land_lag_sim
# (08e7c5551) and by the extended one must give byte-identical slices (paths normalised), and match the committed Q-XPF run.
set -eu
T=$1; NEW=$2; ORIG=$3; B=/home/ubuntu/scratch/dkvr/kvr-landlag/compute_ref
rm -rf $T; mkdir -p $T
for v in orig new; do cp -r $B/pre $T/$v; done
PYTHONPATH=$(dirname $NEW) python3 $ORIG annotate $T/orig --lanes $B/fwd_lanes.json > $T/orig.out
python3 -I $NEW annotate $T/new --lanes $B/fwd_lanes.json > $T/new.out
sed -i "s#$T/new#$T/orig#g" $T/new/*.f $T/new/land_lag.json
diff -r $T/orig $T/new && diff $T/orig.out $T/new.out && echo "COMPUTE_REGRESS new==orig"
cmp $T/new/die_glue_lag.sv $B/annotated/die_glue_lag.sv && cmp $T/new/qwc_slice_ctl.sv $B/annotated/qwc_slice_ctl.sv && echo "COMPUTE_REGRESS == Q-XPF bi_plan annotated (glue + slice)"
python3 - $T/new/land_lag.json $B/annotated/land_lag.json <<'PY'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:])
for k in ('slice', 'lanes'): a.pop(k); b.pop(k)
print('COMPUTE_REGRESS land_lag.json == Q-XPF (paths aside):', a == b)
PY
