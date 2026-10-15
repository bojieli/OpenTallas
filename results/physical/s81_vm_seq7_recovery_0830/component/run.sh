#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
bash tools/s81_vm/vm_seq_static_gate.sh "$PWD/exact" 1500 > exact_gate.log 2>&1 & exact_pid=$!
docker run --rm -v "$PWD:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -p "read_verilog -sv /work/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_static.sv; synth -noabc -top dsfd_vm_seq_static; write_json /work/mapped.json" > mapped.log 2>&1
wait "$exact_pid"
cat exact_gate.log
