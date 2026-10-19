#!/bin/bash
set -euo pipefail
yosys -Q -T -p 'read_verilog -formal -sv tools/hbm_hidx_coupon1/coupon.sv tools/hbm_hidx_coupon1/formal.sv; hierarchy -top formal; setattr -mod -unset keep_hierarchy; prep -top formal -flatten; sat -seq 3 -prove-skip 2 -prove bad 0 -verify -show-ports' >out/formal.log 2>&1
