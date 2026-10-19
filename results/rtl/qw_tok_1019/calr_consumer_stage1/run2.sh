#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p out2
verilator --version > out2/verilator.version
mapfile -t files < compile_files.txt
mapfile -t inc < <(find source -type d -printf '+incdir+%p\n')
/usr/bin/time -v -o out2/build.time verilator --cc --exe --build -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 +define+OT_QFD_UP4_CK_ENTRIES --top-module tb_stage1 --prefix Vtb -Mdir "$PWD/out2/obj" "${inc[@]}" "$PWD/source/rtl/test/qwen_dv/main2.cpp" "${files[@]}" one_column.sv tb_stage1.sv attempt2/consumer_probes.sv > out2/build.log 2>&1
for mode in baseline probes;do
 args=();if [ "$mode" = probes ];then args=(+QW_PROBE);fi
 /usr/bin/time -v -o "out2/$mode.time" out2/obj/Vtb +EV="$PWD/inputs/ev_nominal_l8_g4.txt" +LOG="$PWD/out2/$mode.trace" +NCYC=6460 +OT_ROM_DIR="$PWD/inputs/masks" "${args[@]}" > "out2/$mode.log" 2>&1
done
cmp out2/baseline.trace out2/probes.trace
grep -q 'ME_ACCEPT' out2/probes.log
grep -q 'XPF_LEAF_READ_CAPTURE' out2/probes.log
echo STAGE1_CONSUMER_MEASURED
