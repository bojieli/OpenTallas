#!/bin/bash
# TOK-S81-GAPS/XS2b (ot-epyc4, Verilator 5.050): vectors = xs_calendar.py gen --vec <bench_xsp4/xsp2 vector> (mutants --mutant nostall|shift|offm1|late; rank = --tags rank)
cd /srv/opentallas-scratch/claude/tok-s81-xs2b/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_slice_bench.sh ../out ../vec/p16 ../vec/p13 ../vec/p1 ../vec/p44 ../vec/p24 ../vec/p50 ../vec/p11_rank ../vec/p13_rank ../vec/p16_nostall ../vec/p16_shift ../vec/p13_offm1 ../vec/p16_late
# RTL mutant build:
XS_DEFS=-DOT_S81SL_XS_MUT_QSWAP MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_slice_bench.sh ../out_qswap ../vec/p16_qswap ../vec/p13_qswap
