#!/bin/bash
# TOK-S81-GAPS/XS2 BF MEASUREMENT on the col_h10 master (u_f_0L01, E 2; landing window needs LDLY < LK)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
BF_LEGACY=1 MASTER=col_h10 LK=2 LDLY=1 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bm10 ../vec10m/p65
