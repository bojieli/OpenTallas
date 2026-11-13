#!/bin/bash
# r2-only composition: col_h9_r1 items stopped (clk_t21 radius 288.7 > 220 from reset relay rst_rl_77; needs an added tap = design call)
cd /srv/opentallas-scratch3/claude/frame-forms-1/all1
python3 -I /srv/opentallas-scratch3/claude/wt/frame-forms-1/events/s81_frame_spine_1113/compose_frame_spine.py /srv/opentallas-scratch3/claude/frame-forms-1/w/plan_A.json merged_r2.json --shards /srv/opentallas-scratch3/claude/frame-forms-1/all1/sh/col_h9_r2__t1__cl774acf45,/srv/opentallas-scratch3/claude/frame-forms-1/all1/sh/col_h9_r2__t1__clb8d86cd5,/srv/opentallas-scratch3/claude/frame-forms-1/all1/sh/col_h9_r2__t1__clce45cab5 --report compose_r2_report.json --tsv compose_r2_report.tsv > compose_r2.log 2>&1; echo COMPOSE_RC=$?
python3 -I /srv/opentallas-scratch3/claude/wt/frame-forms-1/events/s81_frame_spine_1113/finalize.py /srv/opentallas-scratch3/claude/frame-forms-1/w/plan_A.json merged_r2.json plan_fin_r2.json > finalize_r2.log 2>&1; echo FIN_RC=$?; cat finalize_r2.log
grep "^col_h9_r2" accepted_types.txt > accepted_r2.txt; wc -l < accepted_r2.txt
