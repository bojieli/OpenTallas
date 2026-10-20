#!/bin/bash
# QW-CLAYER2: residual row-order (io_collective message order) landing on the reg_vec tb_qfd_dv2 N12 executable (5.050)
set -u
SRC=/srv/opentallas-scratch/claude/qw-clayer2/src; EXE=/srv/opentallas-scratch/claude/qw-clayer-1018/runs/reg_vec/work/obj_n12
AG=/srv/opentallas-scratch/claude/qw-clayer-1018/runs/reg_vec/vec_ages.json; OUT=/srv/opentallas-scratch/claude/qw-clayer2/runs/resid_row
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $SRC
for mu in - arwin xslot; do
  tag=resid_row_${mu/-/m0}; W=$OUT/$tag; mkdir -p $W; ln -sfn $EXE $W/obj_n12
  ma=""; [ "$mu" != - ] && ma="--mutant $mu"
  ( python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $W --mode resid --ar-order row $ma --ages $AG > $OUT/$tag.out 2>&1; echo "rc=$?" >> $OUT/$tag.out ) &
done
wait
verilator --version > $OUT/verilator.version
sha256sum rtl/test/qwen_dv/dv_lower_vec_bench.py tools/qwen_layerbench/dv_lower_vec.py tools/qwen_layerbench/dv_lower.py rtl/test/qwen_dv/dv_lower_bench.py rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/dv_bench.py rtl/qwen_dv/*.sv $AG > $OUT/source.sha256
cat $OUT/*.out
