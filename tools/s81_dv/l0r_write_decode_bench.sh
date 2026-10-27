#!/bin/bash
set -euo pipefail
R=$(git rev-parse --show-toplevel)
B=${1:?scratch output directory required}
mkdir -p "$B"
git show 9f575a2e2b:rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0r.sv | sed "s/module dsdv_gunit_l0r/module legacy_l0r/" > "$B/legacy_l0r.sv"
cp "$R/tools/s81_dv/tb_l0r_write_decode.sv" "$B/tb.sv"
V=${VERILATOR:-verilator}
for variant in gold mutant;do
 SRC="$R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0r.sv"
 if [ "$variant" = mutant ];then
  python3 "$R/tools/s81_dv/l0r_write_priority_mutant.py" "$SRC" "$B/mutant.sv"
  SRC="$B/mutant.sv"
 fi
 "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_l0r_write --Mdir "$B/obj_$variant" -j 4 -CFLAGS -O1 "$B/tb.sv" "$B/legacy_l0r.sv" "$SRC" "$R/rtl/lib/ot_rst_relay.sv" > "$B/build_$variant.log" 2>&1
 if "$B/obj_$variant/Vtb_l0r_write" > "$B/$variant.log" 2>&1;then test "$variant" = gold;else test "$variant" = mutant;grep -q STORE_DIFF "$B/$variant.log";fi
done
echo L0R_WRITE_GOLD_PASS_PRIORITY_MUTANT_CAUGHT
