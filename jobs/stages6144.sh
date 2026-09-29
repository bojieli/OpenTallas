#!/bin/bash
# Build the 37-stage list (36 layers + lm_head) for the G=6144 token and its port-local-scale twin.
# usage: jobs/stages6144.sh <image dir> <out dir>
set -e
I=$1; O=$2; mkdir -p $O
for d in 0 1; do
  H=$O/stage-head-d$d; mkdir -p $H
  ln -sf $I/binding/head_final_norm_crom.hex $H/crom.hex
  ln -sf $I/binding/head_program_d$d.hex $H/program.hex
  ln -sf $I/binding/head_segments_d$d.hex $H/segments.hex
  ln -sf $I/head-d$d/matrix_int8.hex $H/matrix_int8.hex
  ln -sf $I/head-d$d/matrix_scale_bf16.hex $H/matrix_scale_bf16.hex
done
: > $O/stages.txt; : > $O/stages_local.txt
for L in $(seq 0 35); do
  echo "L$L $I/L$L-d0 $I/L$L-d1 1" >> $O/stages.txt
  for d in 0 1; do python3 tools/qwen_rom_scale_local.py --src $I/L$L-d$d --dst $O/local/L$L-d$d --groups 6144 --smin 6 > /dev/null; done
  echo "L$L $O/local/L$L-d0 $O/local/L$L-d1 1" >> $O/stages_local.txt
done
echo "head $O/stage-head-d0 $O/stage-head-d1 0" >> $O/stages.txt
for d in 0 1; do python3 tools/qwen_rom_scale_local.py --src $O/stage-head-d$d --dst $O/local/head-d$d --groups 6144 --smin 6 > /dev/null; done
echo "head $O/local/head-d0 $O/local/head-d1 0" >> $O/stages_local.txt
head -1 $O/stages.txt > $O/stages_l0.txt; head -1 $O/stages_local.txt > $O/stages_local_l0.txt
echo STAGES_OK
