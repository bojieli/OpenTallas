#!/bin/bash
# TOK-S81-GAPS/XS bench_xsp2: validation of the shape-keyed element terms on OTHER phases of the same field (same build)
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out ../vec2/p16 ../vec2/p13 ../vec2/p18 ../vec2/p24 ../vec2/p50 ../vec2/p17
