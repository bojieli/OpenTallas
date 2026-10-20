#!/bin/bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for edge in default initialedge;do
 flag=();[ "$edge" = initialedge ] && flag=(--x-initial-edge)
 "$VL" --binary --timing -j 2 -Wno-fatal --top-module tb_primitive "${flag[@]}" -Mdir obj_$edge -o Vcoupon tb_primitive.sv cells_primitive.v > build_$edge.log 2>&1
 ./obj_$edge/Vcoupon > coupon_$edge.log
 cat coupon_$edge.log
done
