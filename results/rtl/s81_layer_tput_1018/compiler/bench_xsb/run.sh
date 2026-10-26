#!/bin/bash
# TOK-S81-GAPS/XS2 BF16 pair phases, PRODUCTION build (static BF programme from the cfg spare columns; tb BF word valid fix)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
XS_DEFS=-DTB_BFTRACE MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bp ../vecbp/p65 ../vecbp/p70 ../vecbp/p76 ../vecbp/p77 ../vecbp/p81 ../vecbp_m/p65_swap ../vecbp_m/p65_shift ../vecbp_m/p65_desc
