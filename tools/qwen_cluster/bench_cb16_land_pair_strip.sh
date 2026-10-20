#!/bin/bash
set -u
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=(rtl/physical/qcluster/qfd_c_land_safe.sv rtl/physical/qcluster/qfd_c_land_pair_safe.sv rtl/physical/qcluster/qfd_c_land_pair_strip.sv tools/qwen_cluster/tb_cb16_land_pair_strip.sv)
sha256sum "${S[@]}" "$0" > "$OUT/sources.sha256"
for cfg in 257_0_0 258_0_0 257_0_100 258_0_100 258_1_100;do
 IFS=_ read -r w m phase <<< "$cfg"
 "$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_pair_strip -GW=$w -GMUT=$m -GPHASE_PS=$phase -Mdir "$OUT/obj_$cfg" "${S[@]}" > "$OUT/build_$cfg.log" 2>&1 || { tail -15 "$OUT/build_$cfg.log";exit 2; }
 "$OUT/obj_$cfg/Vtb_pair_strip" > "$OUT/$cfg.log" 2>&1;x=$?;cat "$OUT/$cfg.log"
 if [ "$m" = 0 ];then [ "$x" = 0 ] && grep -q PAIR_PASS "$OUT/$cfg.log" || exit 1
 else [ "$x" != 0 ] && grep -q PAIR_MISMATCH "$OUT/$cfg.log" || exit 1;fi
done
echo PAIR_BENCH_PASS
