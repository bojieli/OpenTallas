#!/usr/bin/env bash
# Gate of vm_service_wordbank with the reusable checker (expected-seat UE fix fc58d5470 imported by source):
# exact passes, MUT_CK_IGNORE fails, and (CK_OLD=<pre-fix vm_ck4.sv>) the pre-fix checker fails on the
# expected-seat UE cases. Usage: run_service_wordbank.sh <outdir>
set -uo pipefail
out=$1;here=$(cd "$(dirname "$0")";pwd);root=$(cd "$here/../../../..";pwd)
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out";if [[ -e $out/source.sha256 ]];then echo refuse_overwriting_receipt;exit 2;fi
S="$here/vm_service_wordbank.sv $here/../checker9/vm_ck4.sv $here/tb_vm_service_wordbank.sv"
(cd "$root";sha256sum ${S//$root\//}) >"$out/source.sha256"
fail=0
for c in exact MUT_CK_IGNORE ${CK_OLD:+PREFIX_CK};do
 d=;[[ $c == MUT_* ]]&&d=-D$c
 [[ $c == PREFIX_CK ]]&&S="$here/vm_service_wordbank.sv $CK_OLD $here/tb_vm_service_wordbank.sv"
 $V --binary --timing -j 4 -Wno-fatal -DVM_SVC_FAULT_HOOK $d --top-module tb_vm_service_wordbank --Mdir "$out/obj_$c" $S >"$out/$c.build.log" 2>&1
 echo $? >"$out/$c.build.rc"
 /usr/bin/time -v "$out/obj_$c/Vtb_vm_service_wordbank" >"$out/$c.run.log" 2>&1;rc=$?
 echo $rc >"$out/$c.rc";rm -rf "$out/obj_$c"
 echo "$c build=$(cat "$out/$c.build.rc") rc=$rc $(grep -E 'SERVICE_WORDBANK' "$out/$c.run.log"|head -1)"
 if [[ $c == exact ]];then [[ $rc == 0 ]]||fail=1;else [[ $rc != 0 && $(cat "$out/$c.build.rc") == 0 ]]||fail=1;fi
done
echo GATE_FAIL=$fail;exit $fail
