#!/bin/bash
# L2H-PAD 10-19: FAN32 0/1 x mutant sweep; writes <out>/f<fan>_m<mut>.log and a SUMMARY line per case.
set -uo pipefail
out=${1:?output};mkdir -p "$out";out=$(realpath "$out")
for fan in 1 0;do for mut in 0 1 2 3 8 9 12 13 14;do
 d="$out/f${fan}_m${mut}"
 if bash rtl/test/hbm_collar_idx256r/run_idx256r_one.sh "$d" "$mut" "$fan" > "$out/f${fan}_m${mut}.log" 2>&1;then r=PASS;else r=FAIL;fi
 echo "SUMMARY fan=$fan mut=$mut $r $(grep -ho 'IDX256R_[A-Z]*[^\"]*' "$out/f${fan}_m${mut}.log" | head -1)"
done;done
