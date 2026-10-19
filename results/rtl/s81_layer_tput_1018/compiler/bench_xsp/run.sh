#!/bin/bash
# TOK-S81-GAPS/XS frame bench of the multi-phase field: one build (col_h9 LK 5 = die frame u_f_0L00), 7 phase vectors
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out ../vec/sgu ../vec/sgu_swap ../vec/sgu_shift ../vec/wob ../vec/wqb ../vec/egu ../vec/down
