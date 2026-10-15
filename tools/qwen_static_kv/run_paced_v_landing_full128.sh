#!/usr/bin/env bash
# Uses already-frozen legal controller reservations and an independently
# compiled first-request calendar. Never discovers slots during this replay.
set -euo pipefail
ulimit -c 0
out=${1:?prepared immutable input directory};src="$out/source"
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
verilator --binary --timing -Wno-fatal -j "${JOBS:-4}" --top-module tb_static_paced_v_landing_full128 --Mdir "$out/obj" "${sources[@]}" > "$out/build.log" 2>&1
for phase in 137 637;do
 for mode in 0 9 10;do
  if "$out/obj/Vtb_static_paced_v_landing_full128" +phase="$phase" +faultmode="$mode" +fixtures="$out/fixtures/p$phase" +landing_calendar="$out/landing_calendar" > "$out/p${phase}_m${mode}.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "$out/p${phase}_m${mode}.exit"
  if ((mode==0));then test "$rc" = 0;grep -q '^PASS actual128 persistent' "$out/p${phase}_m${mode}.log";else test "$rc" != 0;fi
 done
done
find "$src" -name '*.sv' -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
echo 'PASS actual128 controller-to-mapped-landing static calendar; common leaf clocks only'
