#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?builddir};if [[ ${RESUME:-0} == 1 ]];then test -d "$out";else mkdir "$out";fi;cd "$root"
sha256sum $(cat tools/qwen_split/su_static_math.f) tools/qwen_split/su_static_math.vlt tools/qwen_split/su_static_math_main.cpp > "$out/source.sha256"
verilator --cc --build --timing --hierarchical -Wno-fatal --top-module tb_qfd_sp_su64_native -j 1 --Mdir "$out/obj" \
 tools/qwen_split/su_static_math.vlt -f tools/qwen_split/su_static_math.f > "$out/build.log" 2>&1
# Verilator5.032 forwards --exe to child --lib-create when using --binary.
# Build real hierarchy libraries first, then link only an event-driver main.
mapfile -t libs < <(find "$out/obj" -name '*.a' -type f | sort)
g++ -std=c++20 -O2 -I"$out/obj" -I/usr/share/verilator/include -I/usr/share/verilator/include/vltstd  tools/qwen_split/su_static_math_main.cpp /usr/share/verilator/include/verilated.cpp  /usr/share/verilator/include/verilated_timing.cpp /usr/share/verilator/include/verilated_threads.cpp  -Wl,--start-group "${libs[@]}" -Wl,--end-group -pthread -latomic -o "$out/obj/Vtb_qfd_sp_su64_native" >> "$out/build.log" 2>&1
for case_id in 0 1 2 3 4;do
 "$out/obj/Vtb_qfd_sp_su64_native" +CASE="$case_id" > "$out/case_$case_id.log" 2>&1
done
if "$out/obj/Vtb_qfd_sp_su64_native" +DATA_MUT=1 > "$out/data_mutant.log" 2>&1;then
 echo 'FAIL data mutant escaped';exit 1
fi
for case_id in 0 1 2 3 4;do cat "$out/case_$case_id.log";done
cat "$out/data_mutant.log"
