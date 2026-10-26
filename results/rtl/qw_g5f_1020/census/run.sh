#!/bin/bash
# QW-G5F 10-20: mapped ASAP7 TT RVT synth + tools/ref_tile/native_census.py (main) of the fault capture leaves
D=$(dirname $(readlink -f $0)); rc=0
for T in fcap16 fcap1 for16; do
  bash $D/tools/synth_census.sh $D/src $T $D/out/$T rtl/fc_wrap.sv rtl/qfd_fault_capture.sv rtl/qfd_fault_or.sv || rc=1
  python3 -c "import json,sys; d=json.load(open('$D/out/$T/census.json')); print('$T', d.get('status'), 'max_dynamic_loads', d.get('max_dynamic_loads'), {k:d[k] for k in d if 'over' in k or 'worst' in k})" || rc=1
done
exit $rc
