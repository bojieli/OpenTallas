#!/usr/bin/env bash
set -euo pipefail
# Run in a fresh admitted fleet scratch directory, never localhost.
tar xzf inputs.tar.gz
python3 prove.py
sed 's/module qkd_astk_rly_296_fl (/module qkd_astk_rly_296_fl_native (/' inputs/6_final.v > out/native.v
iverilog -g2012 -s tb -o out/sim out/native.v out/native_models.v inputs/qkd_astk_rly_296_fl.sv inputs/ot_rst_relay.sv inputs/qkd_astk_phys.sv tb.sv > out/compile.log 2>&1
vvp out/sim > out/witness.log 2>&1
cat out/witness.log
