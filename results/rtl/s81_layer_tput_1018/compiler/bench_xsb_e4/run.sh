#!/bin/bash
# TOK-S81-GAPS/XS2 BF production on a col_h9 frame at lane latency E 4 (u_f_1L00): calendar PREDICTED from the E 5 measurement (+E-5)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
XS_DEFS=-DTB_BFTRACE MASTER=col_h9 LK=4 LDLY=3 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bp4 ../vec4/p65 ../vec4/p77
