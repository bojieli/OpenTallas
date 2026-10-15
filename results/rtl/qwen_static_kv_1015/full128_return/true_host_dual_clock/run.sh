#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
hostdual=1
out=/var/tmp/qkd-full128-hostdual-4749ff96e
src="$out/source"
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
for discover in 1 0;do
 verilator --binary --timing -Wno-fatal -j "${JOBS:-4}" --top-module tb_static_return_full128 -GDISCOVERY="$discover" -GHOST_DUAL="$hostdual" --Mdir "$out/obj$discover" "${sources[@]}" > "$out/build$discover.log" 2>&1
 if ((discover));then
  for phase in 137 637;do
   if ((hostdual==0&&phase==637));then continue;fi
   mkdir -p "$out/fixtures/p$phase"
   "$out/obj1/Vtb_static_return_full128" +phase="$phase" +fixtures="$out/fixtures/p$phase" > "$out/discovery_p$phase.log" 2>&1
  done
  find "$out/fixtures" -type f -print0 | sort -z | xargs -0 sha256sum > "$out/fixtures.sha256"
 else
  for phase in 137 637;do
   fixture_phase=$phase;if ((hostdual==0));then fixture_phase=137;fi
   for mode in 0 1 2 3 4 5 6 7 8;do
    if "$out/obj0/Vtb_static_return_full128" +fixtures="$out/fixtures/p$fixture_phase" +phase="$phase" +faultmode="$mode" > "$out/p${phase}_m${mode}.log" 2>&1;then rc=0;else rc=$?;fi
    echo "$rc" > "$out/p${phase}_m${mode}.exit"
    if ((mode==0));then test "$rc" = 0;grep -q '^PASS full128 persistent' "$out/p${phase}_m${mode}.log";else test "$rc" != 0;fi
   done
  done
 fi
done
find "$src" -name '*.sv' -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
echo 'PASS full128 actual persistent controllers and frozen independent return calendars; dual phases and eight mutants each'
