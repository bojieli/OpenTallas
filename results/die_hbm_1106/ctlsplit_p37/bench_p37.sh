#!/bin/bash
# HBM-FORM-TIMING-11 part 37 lock-step bench (iverilog): old plan module (oneclk wrapper + gold ctl_core) vs part-37 plan module
# (glue -> __split -> rest_1c + pipe_1c), 800 random cycles, rst_n power-on + rst_lg_n pulse + rst_n 2-cycle and 1-cycle pulses.
#   bench_p37.sh WORKDIR   (from the repo root).  ok must be 0 errors; m2 (seam bits 0/1 swapped) and m3 (pipe reset never asserted) must FAIL.
set -eu
B=$1; mkdir -p $B; Q=results/die_hbm_1106/ctlsplit_p37; C=ot_hgi_sfu_core_split3__ctl; RD=rtl/hbm_accel/cores_split/ot_hgi_sfu_core_split3
python3 -I $Q/gen_tb37.py physical/die_plan/hbm_arch_cores/wrappers/oneclk/$C.sv 800 > $B/tb.v
sed "s/^module $C (/module ${C}__p37 (/" $Q/${C}__p37glue.sv > $B/glue.sv
cat $RD/ot_hgi_sfu_split3_ctl_rest_1c.sv $RD/ot_hgi_sfu_split3_ctl_pipe_1c.sv $RD/ot_hgi_sfu_split3_ctl_split.sv > $B/split_ok.sv
sed "s/else relay_q0 <= sync_q\[1\];/else relay_q0 <= sync_q[0];/" $B/split_ok.sv > $B/split_m1.sv
sed "/ot_hgi_sfu_split3_ctl_pipe_core u_pipe/s/\.seam_d(seam_d)/.seam_d({seam_d[279:2], seam_d[0], seam_d[1]})/" $B/split_ok.sv > $B/split_m2.sv
sed "/ot_hgi_sfu_split3_ctl_pipe_core u_pipe/s/\.rst_vm_n(relay_q0)/.rst_vm_n(1'b1)/" $B/split_ok.sv > $B/split_m3.sv
for m in ok m1 m2 m3; do ( iverilog -g2012 -o $B/sim_$m $B/tb.v physical/die_plan/hbm_arch_cores/wrappers/oneclk/$C.sv $RD/ot_hgi_sfu_split3_ctl_core.sv $B/glue.sv $B/split_$m.sv $RD/ot_hgi_sfu_split3_ctl_rest_core.sv $RD/ot_hgi_sfu_split3_ctl_pipe_core.sv && vvp -n $B/sim_$m > $B/$m.out 2>&1; echo "$m $(grep BENCH_DONE $B/$m.out)" ) & done; wait
