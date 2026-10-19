#!/bin/bash
# TOK-S81-GAPS/XS bench_xsp3: fp8 down measurement (p44) + prediction check (p45)
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out ../vec3/p44 ../vec3/p45
