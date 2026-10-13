#!/usr/bin/env bash
# Component gate of vm_service_root: exact + every mutant. Usage: run_service_root.sh <outdir> (on a fleet host, under ot-heavy)
set -uo pipefail
out=$1;here=$(cd "$(dirname "$0")";pwd);root=$(cd "$here/../../../..";pwd)
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out";if [[ -e $out/source.sha256 ]];then echo refuse_overwriting_receipt;exit 2;fi
S="$here/vm_service_root.sv $here/vm_service_wordbank.sv $here/vm_service_slice.sv $here/../checker9/vm_ck4.sv $root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $here/tb_vm_service_root.sv"
(cd "$root";sha256sum ${S//$root\//}) >"$out/source.sha256"
cases="exact MUT_SVC_TICKET_REUSE MUT_SVC_ACK3 MUT_SVC_EARLYREL MUT_SVC_STALE MUT_SVC_DUP MUT_SVC_NOVERIFY MUT_SVC_WRAP MUT_SVC_NOQUAR MUT_SVC_LEASE MUT_CK_IGNORE MUT_SERVICE_SERIAL"
for c in ${CASES:-$cases};do
 (
  d=;[[ $c != exact ]]&&d=-D$c
  $V --binary --timing -O1 -CFLAGS -O1 -j 4 -Wno-fatal -DOT_MEM_NO_INIT -DVM_SVC_FAULT_HOOK $d --top-module tb_vm_service_root --Mdir "$out/obj_$c" $S >"$out/$c.build.log" 2>&1
  echo $? >"$out/$c.build.rc"
  /usr/bin/time -v "$out/obj_$c/Vtb_vm_service_root" >"$out/$c.run.log" 2>&1
  echo $? >"$out/$c.rc"
  rm -rf "$out/obj_$c"
 ) &
done
wait
fail=0
for c in ${CASES:-$cases};do
 rc=$(cat "$out/$c.rc");echo "$c rc=$rc $(grep -E 'SERVICE_ROOT (PASS|FAIL)|^%Error|FAIL' "$out/$c.run.log"|head -1)"
 if [[ $c == exact ]];then [[ $rc == 0 ]]||fail=1;else [[ $rc != 0 ]]||fail=1;fi
done
echo GATE_FAIL=$fail;exit $fail
