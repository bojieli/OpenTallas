#!/bin/bash
# TOK-S81-GAPS/XS2 BF16 pair phases, MEASUREMENT build (BF_LEGACY=1: patched core COPY issues on its walker + TB_BFTRACE)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
BF_LEGACY=1 MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bm ../vecbm/p65 ../vecbm/p76 ../vecbm/p81
