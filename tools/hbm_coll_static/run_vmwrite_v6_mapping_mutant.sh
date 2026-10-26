#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
base=rtl/hbm_accel/generic/collective/p2p
iverilog -g2012 -s tb_vmwrite_v6_mapping -Ptb_vmwrite_v6_mapping.MAP_MUT=1 -o "$out/map.vvp" "$base/ot_hgi_coll_static_vmwrite_roots_v6.sv" "$base/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv" tools/hbm_coll_static/tb_vmwrite_v6_mapping.sv
exec vvp "$out/map.vvp"
