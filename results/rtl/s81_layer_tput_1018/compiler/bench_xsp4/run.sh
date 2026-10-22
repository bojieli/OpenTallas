#!/bin/bash
# TOK-S81-GAPS/XS bench_xsp4: per-segment element terms (fp8 K 1280 / 2304 half-unit last segment) legalised in; wq_b /
# shared down phases incl. ones not measured (2, 11, 46) + regression p16 / p13 (same build as bench_xsp)
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out ../vec4/p1 ../vec4/p2 ../vec4/p11 ../vec4/p44 ../vec4/p46 ../vec4/p16 ../vec4/p13
