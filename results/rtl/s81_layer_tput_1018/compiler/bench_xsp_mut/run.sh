#!/bin/bash
# TOK-S81-GAPS/XS2: sgu mutants re-run on the FINAL per-segment field (seg_extra legalised), same 5.050 build as bench_xsp4
cd /srv/opentallas-scratch/claude/tok-s81-xs/src
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh /srv/opentallas-scratch/claude/tok-s81-xs2/out_mut ../../tok-s81-xs2/vecm/sgu ../../tok-s81-xs2/vecm/sgu_swap ../../tok-s81-xs2/vecm/sgu_shift
