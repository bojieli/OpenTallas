#!/bin/bash
set -euo pipefail
ulimit -c 0
mkdir -p out
python3 - <<'PY'
import hashlib,json,pathlib
pathlib.Path('out/source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*pathlib.Path('.').glob('*.sv'),*pathlib.Path('.').glob('*.v')]},indent=2)+'\n')
PY
for mode in actual payload stress legacy default;do
 top=tb_hgi_hc_prefetch_direct_phy_static;args=()
 if [[ $mode == payload ]];then args=(-GMUT=1 -GROWS=1);fi
 if [[ $mode == stress ]];then top=tb_hgi_hc_prefetch_direct_static;fi
 if [[ $mode == legacy ]];then top=tb_hgi_hc_prefetch_direct_static;args=(-GMAX_OUTSTANDING=1 -GROWS=2);fi
 if [[ $mode == default ]];then top=tb_hbm_svc_prefetch_block_cdc;fi
 verilator --binary --timing -j 4 -Wno-fatal --top-module "$top" --Mdir out/$mode-obj -o sim "${args[@]}" *.sv *.v >out/$mode.compile.log 2>&1
 if [[ $mode == default ]];then
  for phase in 137 773;do
   out/$mode-obj/sim +PHASE=$phase >out/default-$phase.log 2>&1
   cat out/default-$phase.log;grep 'PASS PREFETCH_CDC actualPHY' out/default-$phase.log
  done
  out/$mode-obj/sim +BADTAG >out/default-badtag.log 2>&1
  cat out/default-badtag.log;grep 'PASS wrong response epoch rejected' out/default-badtag.log
 elif [[ $mode == actual || $mode == stress ]];then
  for period in 1080 1400;do
   out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex +PERIOD=$period >out/$mode-$period.log 2>&1
   cat out/$mode-$period.log;grep 'HC_PREFETCH_DIRECT.* PASS' out/$mode-$period.log
  done
  if [[ $mode == stress ]];then
   for period in 1080 1400;do
    out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex +PERIOD=$period +STALL >out/stress-stalled-$period.log 2>&1
    cat out/stress-stalled-$period.log;grep 'HC_PREFETCH_DIRECT PASS' out/stress-stalled-$period.log
   done
   for fault in 1 2 3;do
    out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex +FAULT=$fault >out/owner-fault-$fault.log 2>&1
    cat out/owner-fault-$fault.log;grep 'HC_DIRECT_BADTAG PASS' out/owner-fault-$fault.log
   done
  fi
 else
  set +e
  out/$mode-obj/sim +IMAGE=../inputs/all24rows.hex >out/$mode.log 2>&1
  rc=$?
  set -e
  cat out/$mode.log
  [[ $rc != 0 ]]
  if [[ $mode == payload ]];then grep 'actual aperture memory mismatch' out/$mode.log
  else grep 'compiler deadline missed' out/$mode.log;fi
 fi
 done
