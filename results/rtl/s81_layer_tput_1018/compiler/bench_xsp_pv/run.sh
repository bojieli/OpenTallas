#!/bin/bash
# TOK-S81-GAPS/XS: PV-traced build (-DTB_PVTRACE): per-element emission edges for the shapes the one-term rule misses
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
XS_DEFS=-DTB_PVTRACE MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_pv ../vec2/p16 ../vec3/p44 ../vec3/p1 ../vec2/p50
