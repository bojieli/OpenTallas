#!/usr/bin/env bash
# ot_dsdv_vstop bench under Verilator (Icarus 12 vvp asserts of_RET_VEC4 on tb_dsdv_vstop, old and new RTL alike)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
W=/home/ubuntu/shvcb_1018; NEW=$W/src/rtl/dsrom_sys/s81_dv/unit; OLD=$W/old
for v in old new; do
  [ $v = old ] && D=$OLD || D=$NEW
  bad=0; n=0
  verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsdv_vstop --Mdir $W/vl_$v -o tb \
    $D/test/tb_dsdv_vstop.sv $D/ot_dsdv_vstop.sv > $W/vl_$v.build.log 2>&1 || { echo "$v BUILD_FAIL"; continue; }
  for s in 1 2 3 4 5 6 7 8; do for ts in "21 20" "ff 00" "e9 e9" "00 00" "ff ff"; do set -- $ts; n=$((n+1))
    $W/vl_$v/tb +seed=$s +tap=$1 +sink=$2 > $W/vl_$v.run.txt 2>&1
    grep '^VSTOP' $W/vl_$v.run.txt | sed "s/^/$v s=$s t=$1 k=$2 /" >> $W/vl_$v.all.txt
    grep -q '^VSTOP PASS' $W/vl_$v.run.txt || { echo "$v golden FAIL seed=$s tap=$1 sink=$2"; bad=1; }
  done; done
  for m in 1 2 3; do
    verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -DMUT=$m --top-module tb_dsdv_vstop --Mdir $W/vl_${v}_m$m -o tb \
      $D/test/tb_dsdv_vstop.sv $D/ot_dsdv_vstop.sv > /dev/null 2>&1
    $W/vl_${v}_m$m/tb +seed=5 +tap=21 +sink=20 > $W/vl_${v}_m$m.txt 2>&1
    if grep -q '^VSTOP PASS' $W/vl_${v}_m$m.txt; then echo "$v mutant $m NOT detected"; bad=1; else echo "$v mutant $m detected: $(grep -m1 '^VSTOP' $W/vl_${v}_m$m.txt)"; fi
  done
  verilator --lint-only -Wall $D/ot_dsdv_vstop.sv > $W/vl_$v.lint.log 2>&1 || bad=1
  echo "$v: $n golden runs, VSTOP_VL $([ $bad = 0 ] && echo PASS || echo FAIL)"
done
diff <(cut -d' ' -f2- $W/vl_old.all.txt) <(cut -d' ' -f2- $W/vl_new.all.txt) > /dev/null && echo "old/new VSTOP lines identical ($(wc -l < $W/vl_new.all.txt))" || echo "old/new VSTOP lines DIFFER"
