#!/usr/bin/env bash
# Minimum native VM leaf differential: exact full-shape banks, MIF0 versus MIF1.
# Invoke under ot-run; args: exact qfd_dv_s5_vm8x.sv native sram_models.sv fresh workdir.
set -euo pipefail
if [[ $# != 3 ]]; then echo "usage: $0 VM_SOURCE SRAM_MODEL FRESH_WORKDIR" >&2; exit 2; fi
bench_dir=$(cd -- "$(dirname -- "$0")" && pwd)
vm_source=$(realpath "$1")
sram_model=$(realpath "$2")
work_dir=$(realpath -m "$3")
mkdir "$work_dir"
cp "$vm_source" "$work_dir/qfd_dv_s5_vm8x.sv"
cp "$sram_model" "$work_dir/sram_models.sv"
cp "$bench_dir/tb.sv" "$work_dir/tb.sv"
cd "$work_dir"
sha256sum qfd_dv_s5_vm8x.sv sram_models.sv tb.sv > inputs.sha256
/usr/bin/time -v verilator --binary --timing --top-module tb -Wno-fatal -j 2 --output-groups 4 -Mdir obj qfd_dv_s5_vm8x.sv sram_models.sv tb.sv > build.log 2>&1
./obj/Vtb > result.log 2>&1
cat result.log
