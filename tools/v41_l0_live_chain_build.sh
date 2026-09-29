#!/bin/bash
# Build rtl/test/tb_v41_l0_live_chain.sv (tools/v41_l0_live_chain.py). usage: tools/v41_l0_live_chain_build.sh OBJDIR [extra verilator args...]
set -o pipefail
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/.."
obj=$1; shift
mkdir -p $obj
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
cat > $obj/hierarchy.vlt <<'VLT'
`verilator_config
// Simulation compilation boundaries only. No RTL arithmetic/scheduling edits.
hier_block -module "ot_hdc_v41x_attn_tile"
hier_block -module "ot_hdc_v41x_attn_merge"
hier_block -module "ot_hdc_v41x_attn_staging"
hier_block -module "ot_hdc_fmul"
hier_block -module "ot_hdc_qadd"
VLT
echo "start $(date +%s)" > $obj/build.status
/usr/bin/time -v $V --cc --exe --build -j 12 --top-module tb_v41_l0_live_chain --prefix Vtb_v41_l0_live_chain -Mdir $obj \
  -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MODDUP -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-lint -Wno-style \
  --output-split 20000 --output-split-cfuncs 2000 --unroll-count 1 --unroll-limit 131072 \
  -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --hierarchical $obj/hierarchy.vlt -Irtl/hdc/v41 "$@" \
  $(cat "$here/v41_l0_live_chain_files.txt") rtl/test/tb_v41_l0_live_chain.sv rtl/test/tb_v41_l0_live_chain_harness.cpp > $obj/build.log 2>&1
echo "exit=$? $(date +%s)" >> $obj/build.status
