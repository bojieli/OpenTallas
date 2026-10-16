#!/bin/bash
set -eu
out=$1
mut=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb -o "$out/sim" rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctfn_banks_candidate.sv tools/s81_suhc/ctfn_banks_candidate/reference.sv tools/s81_suhc/ctfn_banks_candidate/tb.sv
vvp "$out/sim" +mut="$mut"
