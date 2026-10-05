#!/bin/bash
cd /home/ubuntu/dsrom-s81-pruned-connectivity-r1
iverilog -g2012 -s tb_pruned_connectivity -o test rtl/v41rom/ot_v41_ret.sv rtl/v41die/ot_v41_retn_w17w10.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/test/dsrom_s81_return/*.sv > compile.log 2>&1
rc=$?
if [ $rc -eq 0 ]; then /usr/bin/time -v vvp test > run.log 2> resources.log; rc=$?; fi
printf "%s\n" "$rc" > exit.txt
exit "$rc"
