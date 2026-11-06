#!/bin/bash
cd $(dirname $0)
for c in 'a_m0_s1 0 0 1' 'a_m0_s2 0 0 2' 'a_m0_s3 0 0 3' 'a_m0_s4x 0 0 4 417 512' 'a_m1 0 1 1' 'a_m2 0 2 1' 'a_m3 0 3 1'          'b_m0_s1 1 0 1' 'b_m0_s2 1 0 2' 'b_m0_s3 1 0 3' 'b_m0_s4x 1 0 4 417 512' 'b_m1 1 1 1' 'b_m2 1 2 1' 'b_m3 1 3 1'; do
  ./run_bench.sh $c > res_${c%% *}.txt 2>&1 &
done; wait; cat res_*.txt > MATRIX.txt; echo MATRIX_DONE >> MATRIX.txt
