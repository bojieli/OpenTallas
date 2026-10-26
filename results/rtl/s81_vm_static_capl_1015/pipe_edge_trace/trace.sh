#!/bin/bash
set -euo pipefail
for pipe in 0 1;do
sed "s/\.CAP_PIPE(1)/.CAP_PIPE($pipe)/;s/q = p + 3;/q = p + $((2+pipe));/" tb_trace.sv > tb_trace_$pipe.sv
iverilog -g2012 -s tb_dsfd_vm_static_cap -o trace_$pipe ot_s81_vm_x34.sv dsfd_vm_static_capl.sv dsfd_vm_static_capl_pipe.sv dsfd_vm_static_cap_leaf.sv dsfd_vm_static_cap.sv tb_trace_$pipe.sv
vvp -n trace_$pipe +mode=0 +seed=1 > trace_$pipe.log
grep -q 'TB_VMCAP PASS mode 0' trace_$pipe.log
done
