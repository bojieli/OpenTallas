#!/bin/bash
set -eu
export PYTHONDONTWRITEBYTECODE=1
export PATH=/tmp/token_ds_followthrough1116/readonly_bin:$PATH
cd /tmp/token_ds_followthrough1116/source
exec /usr/bin/time -v -o /tmp/token_ds_followthrough1116/fsa_h9_x.time python3 tools/s81_dv/frame_schedule_asb.py --master col_h9 --var x --out /tmp/token_ds_followthrough1116/fsa_h9_p2 --frame-instance u_f_0L02 --mem-gb 24 --bound-plan /tmp/token_ds_followthrough1116/f2s4_source/selected_plan.json --source-root /tmp/token_ds_followthrough1116/f2s4_source --manifest physical/die_plan/s81/bind/frame_asbuilt.json
