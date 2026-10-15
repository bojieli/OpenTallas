#!/bin/bash
set -euo pipefail
ulimit -c 0
mkdir -p out
python3 - <<'PY'
import hashlib,json,pathlib
pathlib.Path('out/source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*pathlib.Path('.').glob('*.sv'),*pathlib.Path('.').glob('*.v')]},indent=2)+'\n')
PY
for mode in positive payload legacy; do
 args=()
 if [[ $mode == payload ]];then args=(-GMUT=1 -GROWS=1);fi
 if [[ $mode == badtag ]];then args=(-GBADTAG=1 -GROWS=1);fi
 if [[ $mode == legacy ]];then args=(-GMAX_OUTSTANDING=1 -GROWS=2);fi
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hgi_hc_prefetch_direct_static --Mdir out/$mode-obj -o sim "${args[@]}" *.sv *.v >out/$mode.compile.log 2>&1
 if [[ $mode == positive ]];then
  for period in 1080 1400;do
   out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex +PERIOD=$period >out/$mode-$period.log 2>&1
   cat out/$mode-$period.log;grep 'HC_PREFETCH_DIRECT PASS' out/$mode-$period.log
  done
  for fault in 1 2 3;do
   out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex +FAULT=$fault >out/owner-fault-$fault.log 2>&1
   cat out/owner-fault-$fault.log;grep 'HC_DIRECT_BADTAG PASS' out/owner-fault-$fault.log
  done
 else
  set +e
  out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex >out/$mode.log 2>&1
  rc=$?
  set -e
  cat out/$mode.log
  if [[ $mode == badtag ]];then [[ $rc == 0 ]];grep 'HC_DIRECT_BADTAG PASS' out/$mode.log
  elif [[ $mode == payload ]];then [[ $rc != 0 ]];grep 'actual aperture memory mismatch' out/$mode.log
  else [[ $rc != 0 ]];grep 'compiler deadline missed' out/$mode.log;fi
 fi
 done
