#!/usr/bin/env bash
# Admit with ot-run; measure native RED timing only, leaving arithmetic outputs unobserved.
set -euo pipefail
[[ $# == 2 ]] || { echo "usage: $0 SOURCE_ROOT FRESH_WORKDIR" >&2; exit 2; }
source_root=$(realpath "$1")
work_dir=$(realpath -m "$2")
bench_dir=$(cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work_dir"
for name in qfd_dv_s5_red2_leaf.sv qfd_dv_s5_red2_k79.sv qfd_dv_s5_red2_k79_helpers.sv; do
  cp "$source_root/rtl/qwen_dv/s5/$name" "$work_dir/$name"
done
cp "$bench_dir/tb.sv" "$work_dir/tb.sv"
cd "$work_dir"
cat > sources.sha256 <<'HASHES'
1eeef8d0eb9de3f0544c1446b116dbc68a70d249ebbb9fcd4c236ec07ef221b2  qfd_dv_s5_red2_leaf.sv
f9ad5ad1ede49132bc309abd0d2ed58e3ee130c46d13670b417fa0791c1c952a  qfd_dv_s5_red2_k79.sv
f4acdc20e57a6c194e0bef662890fbd689e189caaf95d54881e62ac5ff23c1fd  qfd_dv_s5_red2_k79_helpers.sv
HASHES
sha256sum -c sources.sha256 > input_guard.log
/usr/bin/time -v verilator --binary --timing --top-module tb -j 1 -O3 -finline --output-groups 16 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -CFLAGS '-O0 -w -fno-var-tracking' -Mdir obj qfd_dv_s5_red2_leaf.sv qfd_dv_s5_red2_k79.sv qfd_dv_s5_red2_k79_helpers.sv tb.sv > build.log 2>&1
./obj/Vtb > result.log 2>&1
cat result.log
