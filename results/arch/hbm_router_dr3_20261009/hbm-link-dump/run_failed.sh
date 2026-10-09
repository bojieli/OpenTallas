#!/bin/bash
# rebudget 2026-10-08: HBM r25 die link dump on the grt3 case (in-session full-die GRT, as die-gaps sta_pad3), TT max + FF min
D=/srv/opentallas-scratch/claude/rebudget/hbm_r25; W=/srv/opentallas-scratch/claude/die-evidence/hbm_r25/grt3
/srv/opentallas-scratch/admit.sh 70 -- docker run --rm --name rb_hbm_r25_links --memory=150g -v $W:/work:ro -v $D:/rb openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /rb/run_rb.tcl > /rb/rb.log 2>&1; chmod -R a+rwX /rb"
echo "$(date "+%F %T %Z") HBM links: $(grep -h "OT_RB_DUMP\|OT_CLOCK_CONTEXT\|^Error" $D/rb.log | tr "\n" " ")" >> $D/STATUS.log
