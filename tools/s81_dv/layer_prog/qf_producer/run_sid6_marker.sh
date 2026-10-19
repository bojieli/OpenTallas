#!/bin/bash
set -euo pipefail
out=$1
if [ -e "$out" ];then echo "REFUSE_EXISTING_RUN_DIR $out" >&2;exit 2;fi
mkdir "$out"
src=(marker_sources/ot_s81_rly.sv marker_sources/dsfd_rly_masters_dv276.sv marker_sources/dsfd_rly_masters_dvh.sv marker_sources/ot_s81_land.sv marker_sources/dsfd_dvland.sv marker_sources/cells_used.v tb_sid6_return_marker.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_sid6_return_marker --Mdir "$out/obj" "${src[@]}" --build-jobs 2 > "$out/build.log" 2>&1
"$out/obj/Vtb_sid6_return_marker" > "$out/baseline.log" 2>&1
cat "$out/baseline.log"
for mut in 1 3 4;do
set +e
"$out/obj/Vtb_sid6_return_marker" +MUT="$mut" > "$out/gate_mut_${mut}.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q SID6_MARKER_FAIL "$out/gate_mut_${mut}.log";then echo MUTANT_NOT_CAUSAL;exit 1;fi
echo "SID6_MARKER_GATE_EPOCH_REJECTED $mut"
done
"$out/obj/Vtb_sid6_return_marker" +MUT=2 > "$out/gate_early_reset_masked.log" 2>&1
grep SID6_MARKER_PASS "$out/gate_early_reset_masked.log"
echo SID6_MARKER_PRE_RELEASE_GATE_EARLY_MASKED
