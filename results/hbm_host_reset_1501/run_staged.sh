#!/bin/bash
set -eu
iverilog -g2012 -s tb_host_delivered_reset -o positive tb.sv ot_hbm*.sv ot_rst*.sv >build.log 2>&1
vvp positive >positive.log 2>&1
mkdir -p mutant
cp *.sv mutant/
sed -i 's/assign rst_n\[r\]=pipe\[1\]/assign rst_n[r]=pipe[0]/' mutant/ot_rst_delivered2.sv
iverilog -g2012 -s tb_host_delivered_reset -o mutant/bad mutant/*.sv >mutant/build.log 2>&1
set +e
vvp mutant/bad >mutant/run.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ]
grep -Eq 'errors=[1-9]' mutant/run.log
printf 'HOST_RESET_GATE PASS positive0 mutant%s\n' "$rc"
