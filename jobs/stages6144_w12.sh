#!/bin/bash
# Build the 37-stage lists (36 layers + lm_head) for the G=6144 token at stream-unit width SW
# (programs re-emitted by tools/qwen_rom_program_sw.py), and the port-local-scale twin.
# usage: HDC_SU_WIDTH=<SW> [QWEN_O4_TP=4] jobs/stages6144_w12.sh <image dir> <out dir>
set -e
I=$1; O=$2; mkdir -p $O
export QWEN_O4_GROUPS=6144
TP=${QWEN_O4_TP:-2}; export QWEN_O4_TP=$TP
DIES=$(seq 0 $((TP-1)))
for d in $DIES; do
  H=$O/stage-head-src-d$d; mkdir -p $H
  ln -sf $I/binding/head_final_norm_crom.hex $H/crom.hex
  ln -sf $I/binding/head_program_d$d.hex $H/program.hex
  ln -sf $I/binding/head_segments_d$d.hex $H/segments.hex
  ln -sf $I/head-d$d/matrix_int8.hex $H/matrix_int8.hex
  ln -sf $I/head-d$d/matrix_scale_bf16.hex $H/matrix_scale_bf16.hex
  python3 tools/qwen_rom_program_sw.py --src $H --dst $O/sw/head-d$d --head-die $d --head-geometry $I/head-d$d/head_rom.json > /dev/null
done
: > $O/stages.txt; : > $O/stages_local.txt
for L in $(seq 0 35); do
  for d in $DIES; do
    python3 tools/qwen_rom_program_sw.py --src $I/L$L-d$d --dst $O/sw/L$L-d$d > /dev/null
    python3 tools/qwen_rom_scale_local.py --src $O/sw/L$L-d$d --dst $O/local/L$L-d$d --groups 6144 --smin $([ $TP = 4 ] && echo 7 || echo 6) > /dev/null
  done
  echo "L$L $(for d in $DIES; do echo -n "$O/sw/L$L-d$d "; done)1" >> $O/stages.txt
  echo "L$L $(for d in $DIES; do echo -n "$O/local/L$L-d$d "; done)1" >> $O/stages_local.txt
done
SMIN=$([ $TP = 4 ] && echo 7 || echo 6)
for d in $DIES; do python3 tools/qwen_rom_scale_local.py --src $O/sw/head-d$d --dst $O/local/head-d$d --groups 6144 --smin $SMIN > /dev/null; done
echo "head $(for d in $DIES; do echo -n "$O/sw/head-d$d "; done)0" >> $O/stages.txt
echo "head $(for d in $DIES; do echo -n "$O/local/head-d$d "; done)0" >> $O/stages_local.txt
head -1 $O/stages.txt > $O/stages_l0.txt; head -1 $O/stages_local.txt > $O/stages_local_l0.txt
echo STAGES_OK
