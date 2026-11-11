#!/bin/bash
# run_shape.sh RUN GEN VARIANT: tools/s81_dv/bf_asbuilt_1101 flow on one prepared as-built bench RUN (obj_walker +
# obj_static built), the frame's measurement vector GEN/vec and its field snapshot GEN/field.json:
#   walker run -> xs_bf measure -> replay vectors (positive full/tail/router[+extras], descriptor_fault, payload_fault)
#   -> static runs -> xs_place check -> collect (native family: RUN/../native_family/check.json)
set -u
RUN=$1; GEN=$2; VAR=$3
D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; C=$D/code; FIX=/srv/opentallas-scratch2/claude/tok-verify-1/fixtures/L0
PY="python3 -I $D/pyrun.py"; T=$C/tools/s81_dv
cd $RUN || exit 4
[ -d vec ] || cp -al $GEN/vec vec
args() { sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$1#" $1/ARGS; }
rm -f vec/check.json  # replay dirs hard-link the vector: never write through a shared inode
./obj_walker/Vtb_s81dv_frame $(args $RUN/vec) > walker.log 2>&1; echo "WALKER rc=$? $(grep -m1 '^END' walker.log)"
$PY $T/layer_prog/xs_place.py check --dir $RUN/vec --log walker.log --fixtures $FIX > check_walker.log 2>&1; tail -n 1 check_walker.log
$PY $T/layer_prog/xs_bf.py measure --frame $VAR --log $RUN/walker.log --vec $RUN/vec --lk 2 --out $RUN/measure.json > measure.log 2>&1
mrc=$?; echo "MEASURE rc=$mrc"; cat measure.log; [ $mrc = 0 ] || exit 5
python3 -I $D/pick.py $GEN > cases.txt; cat cases.txt
mkdir -p replay pv
extra=()
while read name phase _; do
  if [ $name = full ]; then src=$RUN/vec; else
    src=$RUN/pv/$name; [ -d $src ] || $PY $T/bf_asbuilt_1101/phase_vector.py --snapshot $GEN/field.json --vector $RUN/vec --fixture $FIX --phase $phase --out $src || { echo "PV_FAIL $name"; continue; }
  fi
  case $name in full|tail|router) ;; *) extra+=($name) ;; esac
  [ -d replay/$name ] || $PY $T/bf_asbuilt_1101/replay_vectors.py --vector $src --measurement $RUN/measure.json --out $RUN/replay/$name || echo "EMIT_FAIL $name"
done < cases.txt
[ -d replay/descriptor_fault ] || $PY $T/bf_asbuilt_1101/replay_vectors.py --vector $RUN/vec --measurement $RUN/measure.json --out $RUN/replay/descriptor_fault --descriptor-fault
[ -d replay/payload_fault ] || $PY $T/bf_asbuilt_1101/replay_vectors.py --vector $RUN/vec --measurement $RUN/measure.json --out $RUN/replay/payload_fault --payload-fault
for d in replay/*/; do d=$RUN/${d%/}
  rm -f $d/check.json $d/run.log $d/check.log
  ./obj_static/Vtb_s81dv_frame $(args $d) > $d/run.log 2>&1
  $PY $T/layer_prog/xs_place.py check --dir $d --log $d/run.log --fixtures $FIX > $d/check.log 2>&1
  echo "CASE $(basename $d) $(tail -n 1 $d/check.log)"
done
echo "${extra[@]}" > extra_cases.txt
$PY $T/bf_asbuilt_1101/collect.py $RUN "${extra[@]}"; echo "COLLECT rc=$?"
python3 -I -c "import json;c=json.load(open('$RUN/check.json'));print('CHECK',c['status'],{k:c[k] for k in ('static_replay','controls_caught','trace_lockstep','native_family_hold')})"
