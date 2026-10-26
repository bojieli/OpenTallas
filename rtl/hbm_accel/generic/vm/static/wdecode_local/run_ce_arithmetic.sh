#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
CORE=../ot_vms_bank_static_wdecode_local.sv
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for mut in 0 3; do
 iverilog -g2012 -s tb_bank_ce_population -Ptb_bank_ce_population.MUT=$mut -o "$OUT/pop-$mut.vvp" "$CORE" "$MACRO" tb_bank_ce_population.sv > "$OUT/pop-$mut.compile.log" 2>&1
 set +e
 vvp "$OUT/pop-$mut.vvp" > "$OUT/pop-$mut.log" 2>&1
 rc=$?
 set -e
 if [[ $mut == 0 ]];then test $rc = 0;else test $rc != 0;grep 'CE population decoder mismatch' "$OUT/pop-$mut.log";fi
 cat "$OUT/pop-$mut.log"
 rm "$OUT/pop-$mut.vvp"
done
iverilog -g2012 -s tb_bank_ce_prefix_wdecode -o "$OUT/prefix.vvp" "$CORE" "$MACRO" tb_bank_ce_prefix_wdecode.sv > "$OUT/prefix.compile.log" 2>&1
/usr/bin/time -v -o "$OUT/prefix.time" vvp "$OUT/prefix.vvp" > "$OUT/prefix.log" 2>&1
cat "$OUT/prefix.log"
rm "$OUT/prefix.vvp"
