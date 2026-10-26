#!/bin/bash
# KV-TOK 10-26: unit replay of the exact B33 boot bundle through the HOST ingress + program loader (both RTL as staged in
# the B33 vehicle, byte-identical to main).  run.sh REPO FRAMES OUT   (FRAMES = B33 boot9_inputs/frames.hex, image7,
# sha256 e2b5ba139292c13166b6cb80505275e2e5f8ca043a446437ee4bdf489dd9f073)
# Variants: legacy (defaults = the old 327/77 table) must FAIL at the first BEGIN (target 10, 96 words);
# mu_only / ages_only must FAIL at target 10 / target 1; native (MU 1, AGES 1) must PASS all 14 images with the
# AUTH digests of expect.txt.
set -u
R=$(readlink -f $1); FR=$(readlink -f $2); O=$(mkdir -p $3 && readlink -f $3); H=$(cd "$(dirname "$0")" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="$R/rtl/qwen_sys/host_integrated_20261014/qkd_host_program_rx_target.sv $R/rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv $R/physical/asap7_memory_macros_v2/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v"
for v in "legacy:.MUT(0)" "mu_only:.MU(1),.AGES(0)" "ages_only:.MU(0),.AGES(1)" "native:.MU(1),.AGES(1)"; do
  n=${v%%:*}; P=${v#*:}
  $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "+define+LPARAMS=$P" "+define+FRAMES=\"$FR\"" \
    --top-module tb_hostload -Mdir $O/obj_$n $H/tb_hostload.sv $SRC > $O/build_$n.log 2>&1 || { echo "$n BUILD FAIL"; continue; }
  $O/obj_$n/Vtb_hostload > $O/sim_$n.log 2>&1
  echo "$n: $(grep -E 'HOSTLOAD' $O/sim_$n.log)"
done
