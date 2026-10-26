#!/usr/bin/env bash
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
build=$(mktemp -d /tmp/hcoll-writer-equivalence.XXXXXX)
trap 'rm -rf "$build"' EXIT
iverilog -g2012 -s tb_vmwrite_decode_equiv -o "$build/sim" \
 "$repo/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite.sv" \
 "$repo/tools/hbm_coll_static/vmwrite_decode_reference.sv" \
 "$repo/tools/hbm_coll_static/tb_vmwrite_decode_equiv.sv"
vvp "$build/sim"
