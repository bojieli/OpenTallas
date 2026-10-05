#!/bin/bash
# tps_remote.sh <src> <out>: tp_seq lockstep, 12 runs (Icarus)
src=$1; out=$2; mkdir -p $out; cd $src
for n in 2 4; do for a in 0 1; do for s in 1 2 3; do
 ( iverilog -g2012 -o $out/t_${n}_${a}_${s} -P tb_qwen_tp_seq_f12_lockstep.N=$n -P tb_qwen_tp_seq_f12_lockstep.ENABLE_AR256=$a -P tb_qwen_tp_seq_f12_lockstep.SEED=$s -P tb_qwen_tp_seq_f12_lockstep.CYCLES=${CYC:-1000000} rtl/rom/ot_qwen_tp_seq_w12.sv rtl/hbm_accel/qwen/fmax/ot_qwen_tp_seq_w12_f12.sv rtl/test/hbm_accel_qwen/fmax/tb_qwen_tp_seq_f12_lockstep.sv && vvp -n $out/t_${n}_${a}_${s} | grep RESULT > $out/t_${n}_${a}_${s}.res ) &
done; done; done; wait; cat $out/*.res
