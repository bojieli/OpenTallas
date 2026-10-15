#!/bin/bash
set -eu
export OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz OT_S81_CTRL_GATE_WARN=phys
cd /srv/opentallas-scratch/claude/s81-die-iter/src_jog10
opts=$(cat results/physical/die_iter_1012/s81/s81_layer1_jog8.opts)
OT_S81_PAIR_GATE=1 python3 tools/s81/c5diag_v15_dump.py /srv/opentallas-scratch/claude/s81-die-iter/jog10_screen real $opts --cfifo-colck
