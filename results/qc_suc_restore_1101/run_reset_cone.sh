#!/bin/bash
set -eu
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o /tmp/qc_suc_reset_$$ tb_reset_cone.sv
vvp /tmp/qc_suc_reset_$$
rm /tmp/qc_suc_reset_$$
