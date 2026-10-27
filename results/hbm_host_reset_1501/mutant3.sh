#!/bin/bash
set -eu
mkdir -p mutant3
cp *.sv mutant3/
sed -i 's/assign rst_n\[r\]=pipe\[2\]/assign rst_n[r]=pipe[1]/' mutant3/ot_rst_delivered3.sv
iverilog -g2012 -s tb_host_delivered_reset -o mutant3/bad mutant3/*.sv >mutant3/build.log 2>&1
set +e
vvp mutant3/bad >mutant3/run.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ]
grep -Eq 'errors=[1-9]' mutant3/run.log
printf 'HOST_RESET_MUTANT3 CAUGHT rc%s\n' "$rc"
