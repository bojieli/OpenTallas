#!/bin/bash
set -eu
for groups in 1 2; do
  iverilog -g2012 -s tb_split_seq_shape -Ptb_split_seq_shape.GROUPS=$groups -o shape$groups.vvp ot_qkvd_fifo.sv ot_qkvd_cbridge.sv ot_qkvd_kv_seq_split_candidate.sv tb_split_seq_shape.sv
  vvp shape$groups.vvp
 done
iverilog -g2012 -s tb_split_seq_shape -Ptb_split_seq_shape.GROUPS=1 -Ptb_split_seq_shape.BAD_TAG=1 -o mutant.vvp ot_qkvd_fifo.sv ot_qkvd_cbridge.sv ot_qkvd_kv_seq_split_candidate.sv tb_split_seq_shape.sv
vvp mutant.vvp
