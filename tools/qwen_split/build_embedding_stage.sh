#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh build directory};vectors=${2:?retained actual token151935 vectors}
mkdir "$out";cd "$root"
python3 tools/qwen_split/embedding_stage_image.py "$out/image"
sha256sum $(cat tools/qwen_split/embedding_stage.f) rtl/test/qwen_split/tb_qwen_embedding_stage.sv tools/qwen_split/embedding_stage_main.cpp tools/qwen_split/su_static_math.vlt tools/qwen_split/embedding_stage_image.py tools/qwen_static_schedule/{segments,calendar,issue_rom,collective}.py tools/{hdc_isa,hdc_program,hdc_golden,hdc_qwen_fullshape_isa_w12}.py "$vectors/codes.hex" "$vectors/scale.hex" "$vectors/expected.hex" > "$out/source.sha256"
verilator --cc --build --timing --hierarchical -Wno-fatal -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -Irtl/hdc \
 --top-module tb_qwen_embedding_stage -j 2 --Mdir "$out/obj" tools/qwen_split/su_static_math.vlt -f tools/qwen_split/embedding_stage.f rtl/test/qwen_split/tb_qwen_embedding_stage.sv > "$out/build.log" 2>&1
mapfile -t libs < <(find "$out/obj" -name '*.a' -type f | sort)
g++ -std=c++20 -O2 -I"$out/obj" -I/usr/share/verilator/include -I/usr/share/verilator/include/vltstd tools/qwen_split/embedding_stage_main.cpp \
 /usr/share/verilator/include/verilated.cpp /usr/share/verilator/include/verilated_timing.cpp /usr/share/verilator/include/verilated_threads.cpp \
 -Wl,--start-group "${libs[@]}" -Wl,--end-group -pthread -latomic -o "$out/obj/Vtb_qwen_embedding_stage" >> "$out/build.log" 2>&1
"$out/obj/Vtb_qwen_embedding_stage" +VECTORS="$vectors" +IMAGE="$out/image" > "$out/positive.log" 2>&1
if "$out/obj/Vtb_qwen_embedding_stage" +VECTORS="$vectors" +IMAGE="$out/image" +MUT=1 > "$out/missing_beat_mutant.log" 2>&1;then echo 'FAIL missing beat mutant escaped';exit 1;fi
echo PASS_ACTUAL_EMBEDDING_REGION_NOT_PHYSICAL_QUALIFICATION
