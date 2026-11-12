#!/bin/bash
# coll VM_RT rd1 bench: 5 configs in parallel (LAT = client round trip budget edges, MUT per tb header)
cd OUTDIR
F="OUTDIR/tb_coll_vmrt_rd1.sv $(sed '1d; s#^#WORKTREE/#' ../files.txt | tr '\n' ' ')"
run() { iverilog -g2012 -o t_$1_$2 -s tb_hgi_coll_ctl_vmrt -P tb_hgi_coll_ctl_vmrt.LAT=$1 -P tb_hgi_coll_ctl_vmrt.MUT=$2 $F > build_$3.log 2>&1 && timeout 7200 vvp -n t_$1_$2 > run_$3.log 2>&1; echo "$3: $(grep -E 'COLL_VMRT (PASS|FAIL)' run_$3.log | head -1)" >> coll_vmrt_rd1.log; }
: > coll_vmrt_rd1.log
run 3 0 main_VM_RT3 & run 4 0 rd1_VM_RT4 & run 4 1 rd1_VM_RT3_plus0 & run 4 4 rd1_VM_RT5_plus2 & run 4 2 rd1_VM_RT0 &
wait
echo DONE >> coll_vmrt_rd1.log
