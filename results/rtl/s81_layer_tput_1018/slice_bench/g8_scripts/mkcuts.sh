#!/bin/bash
# S81-LBGAP/G8: recut cut_3S (G1 replay set) + the four L0 cuts from the G8 die.v, tb, slice kits
W=/home/ubuntu/wt/s81-lbgap-g8; S=/home/ubuntu/scratch/s81-lbgap-g8; B=$S/bind/bind; KD=/home/ubuntu/scratch/lb2-s81-l0/KD
REF=bd3ed009b; LP=$W/results/arch/s81_dv_1016/landing/p4l3/land_plan.json; PL=results/arch/s81_dv_1016/bind_p4l3_g8/sim_kit_sources.f
SB=$W/results/rtl/s81_layer_tput_1018/slice_bench
one() { c=$1; set=$2; C=$S/cuts/$c; K=$S/cuts/K_$c; rm -rf $C $K
  python3 $W/tools/s81_dv/dv_slice_cut.py --die-v $B/die.v --kit $KD --insts $set --out $C --land-plan $LP --corner tt > $S/cuts/$c.cut.log 2>&1 || { echo "$c CUT FAIL"; return; }
  python3 $W/tools/s81_dv/dv_slice_tb.py --ports $C/slice_ports.json --out $C >> $S/cuts/$c.cut.log 2>&1
  python3 $W/tools/s81_dv/dv_rtl_kit.py --ref $REF --port-bind $B/port_bind.json --top-v $C/slice_top.sv --top slice_top --out $K --prefer-list $PL > $S/cuts/$c.kit.log 2>&1 || { echo "$c KIT FAIL"; return; }
  mkdir -p $K/tb; cp $C/tb_slice_top.sv $K/tb/; cp $W/tools/s81_dv/run_dv_slice.sh $K/ 2>/dev/null; echo "$c OK $(head -c 150 $S/cuts/$c.kit.log)"; }
cd $W
one cut_3S $SB/cut_3S/set.txt &
for c in cut_0S cut_7 cut_3S_ctl cut_svc; do one $c $SB/sets/set_$c.txt & done
wait
