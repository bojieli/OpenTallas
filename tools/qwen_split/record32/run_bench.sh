#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
mkdir -p bench
for m in 0 1 2 3; do
 src=rtl/qwen_split/qfd_sys_face_record_port_n32.sv
 if [ "$m" = 2 ]; then sed '0,/if(!R)/s//if(R)/' "$src" > bench/mut_reset.sv;src=bench/mut_reset.sv;fi
 if [ "$m" = 3 ]; then sed 's/assign Y=A \& B;/assign Y=A | B;/' "$src" > bench/mut_boolean.sv;src=bench/mut_boolean.sv;fi
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_record32 -GMUT=$m --Mdir bench/obj$m tools/qwen_split/record32/tb_record32.sv rtl/qwen_split/qfd_sys_face_record_port.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv "$src" > bench/build$m.log 2>&1
 set +e
 bench/obj$m/Vtb_record32 > bench/run$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ]; then test "$rc" = 0;grep -q RECORD32_PASS bench/run$m.log;else test "$rc" != 0;grep -q RECORD32_FAIL bench/run$m.log;fi
 tail -n 3 bench/run$m.log
done
echo RECORD32_MATRIX_PASS
