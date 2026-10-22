#!/bin/bash
cd $(dirname $0)/repo
export L4=1 J=16
SET=plan LK=2 bash tools/s81_dv/frame_bench.sh ../out/h9_each_k2 col_h9 0 > ../out_h9_plan.txt 2>&1 &
SET=plan LK=2 bash tools/s81_dv/frame_bench.sh ../out/h10_plan_k2 col_h10 0 > ../out_h10_plan.txt 2>&1 &
SET=plan LK=5 LDLY=3 bash tools/s81_dv/frame_bench.sh ../out/h9mx_plan_k5 col_h9_MX 0 > ../out_h9mx_plan.txt 2>&1 &
wait; tail -n 2 ../out_h9_plan.txt ../out_h10_plan.txt ../out_h9mx_plan.txt
