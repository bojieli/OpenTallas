#!/bin/bash
# TOK-S81-GAPS/XS2 BF production on the col_h10 master (u_f_0L01, E 2): measured descriptor + emission (measure col_h10|E2)
cd /srv/opentallas-scratch/claude/tok-s81-xs2/src
XS_DEFS=-DTB_BFTRACE MASTER=col_h10 LK=2 LDLY=1 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh ../out_bp10 ../vec10/p65 ../vec10/p77 ../vec10_m/p65_desc
