#!/bin/bash
# TOK-S81-GAPS/XS2 L2 attn.cmp.wk (indexer.wk K 512 zero-padded to one BSEG) on the col_h9 E5 production build (predicted calendar)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
XS_DEFS=-DTB_BFTRACE MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bp ../vecl2/cwk ../vecl2/cwk_swap
