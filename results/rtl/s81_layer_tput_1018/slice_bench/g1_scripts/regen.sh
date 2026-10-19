#!/bin/bash
# regen.sh: cut + tb + slice kit + io for the G1 lane bench variants, then sync to the fleet dir
set -e
S=/home/ubuntu/scratch/s81-lbgap/g1; W=/home/ubuntu/wt/s81-lbgap-g1; R=/srv/opentallas-scratch/claude/s81-lbgap-g1
B=$W/results/rtl/s81_layer_tput_1018/slice_bench; LP=$W/results/arch/s81_dv_1016/landing/p4l/land_plan.json
SET=${SET:-$B/runs/lane_debug/set.txt}; REF=${REF:-215c8d15f}
for c in ${VARS:-tt ff mshift mnogate}; do
  DV=$S/g1/bind/die.v; KD=$S/KD; PB=$S/g1/bind/port_bind.json; X="--corner tt"
  case $c in ff) X="--corner ff";; mshift) X="--corner tt --flight-shift 4";; mnogate) DV=$S/base/bind/die.v; KD=$S/KDB; PB=$S/base/bind/port_bind.json;; esac
  rm -rf $S/cut_ld_$c $S/K_$c
  python3 $W/tools/s81_dv/dv_slice_cut.py --die-v $DV --kit $KD --insts $SET --out $S/cut_ld_$c --land-plan $LP $X | tail -1
  python3 $W/tools/s81_dv/dv_slice_tb.py --ports $S/cut_ld_$c/slice_ports.json --out $S/cut_ld_$c > /dev/null
  python3 $W/tools/s81_dv/dv_rtl_kit.py --ref $REF --port-bind $PB --top-v $S/cut_ld_$c/slice_top.sv --top slice_top --out $S/K_$c 2>&1 | tail -1
  mkdir -p $S/K_$c/tb; cp $S/cut_ld_$c/tb_slice_top.sv $S/K_$c/tb/
  python3 $S/mk_io.py $S/cut_ld_$c $S/K_$c
  for h in ot-epyc4 ot-epyc5; do ssh -o ControlPath=none $h "rm -rf $R/K_$c $R/out_$c"; rsync -a $S/K_$c $h:$R/; done
done
