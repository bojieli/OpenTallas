#!/usr/bin/env bash
# H-NETLIST 1930 (A2P): ot_vms_status4_static NQ bench: NQ=2 and NQ=4 (vs the unchanged original) PASS; mutant FAILs both.
#   run_vms_status_nq.sh OUT REF_SV   (REF_SV = the original module renamed ot_vms_status4_ref)
set -uo pipefail
out=${1:?out}; ref=${2:?ref}; mkdir -p "$out"; d=rtl/hbm_accel/generic/vm/static; fail=0
for nq in 2 4; do
 for m in pos mut; do
  def=(); [ $m = mut ] && def=(-DOT_VMS_STATUS_MUT)
  iverilog -g2012 "${def[@]}" -Ptb_vms_status_nq.NQ=$nq -o "$out/s_${nq}_$m" "$d/ot_vms_status4_static.sv" "$ref" "$d/tb_vms_status_nq.sv" || { echo "BUILD_FAIL $nq $m"; exit 2; }
  vvp "$out/s_${nq}_$m" > "$out/${nq}_$m.log"; r=$(grep -o 'VMS_STATUS_NQ[0-9] [A-Z]* checks=[0-9]* errors=[0-9]*' "$out/${nq}_$m.log"); echo "$m $r"
  if [ $m = pos ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
 done
done
[ $fail = 0 ] && echo VMS_STATUS_NQ_GATE PASS || { echo VMS_STATUS_NQ_GATE FAIL; exit 1; }
