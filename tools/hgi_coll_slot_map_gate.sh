#!/usr/bin/env bash
set -eu
src=${1:?source_checkout};out=${2:?immutable_output_directory}
mkdir -p "$out"
rtl="$src/rtl/hbm_accel/generic/collective"
for mut in 0 1; do
  iverilog -g2012 -s tb_hgi_coll_slot_map -Ptb_hgi_coll_slot_map.MUT_ORDER="$mut" -o "$out/map-$mut.vvp" "$rtl/ot_hgi_coll_slot_map.sv" "$rtl/tb_hgi_coll_slot_map.sv"
  set +e
  vvp "$out/map-$mut.vvp" > "$out/map-$mut.log" 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ];then test "$rc" -eq 0;grep -q 'PASS HGI_SLOT_MAP' "$out/map-$mut.log";
  else test "$rc" -ne 0;grep -q 'FATAL:' "$out/map-$mut.log";fi
  rm "$out/map-$mut.vvp"
done
sha256sum "$rtl/ot_hgi_coll_slot_map.sv" "$rtl/tb_hgi_coll_slot_map.sv" > "$out/source.sha256"
