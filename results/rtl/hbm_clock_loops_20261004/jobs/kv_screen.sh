#!/bin/bash
# KV lifecycle SS screen from src_kv (2026-10-04 restructure). Usage: kv_screen.sh <round> <label> <source.sv> [extra screen args]
R=/srv/opentallas-scratch/claude/hbm-clock-loops
rnd=$1; lab=$2; src=$3; shift 3
O=$R/runs/$rnd; mkdir -p $O
cd $R/src_kv
export OT_SCREEN_ROOT=$R/src_kv
FKV='fsm=(^|\.)(st|state|pc|beat|cstage|op|reader_count|sector_cursor|writer_live|commit_sent|drain_sent|receipt_visible|receipt_reverse|reader_live|row_select|snap|go_ref|acq_arm)(\[|$)'
exec /srv/opentallas-scratch/admit.sh ${NEED:-12} -- python3 jobs/screen.py --work $O/$lab --output $O/$lab.json --label $lab \
  --source $src --top ot_hbm_accel_kv_lifecycle --param ENABLE=1 --period-ns 0.833 --domain 1.2GHz-SM --focus "$FKV" \
  --focus 'rows=(^|\.)(pub_valid|pub_pos|pub_tag|reader_live|reader_tag|reader_pos|consumer_mask|consumer_reverse_mask|responded_mask|reader_metadata_mask)(\[|$)' \
  --focus 'rsp=(^|\.)(rsp_[a-zA-Z_]*|fault)(\[|$)' \
  --focus 'cmd=(^|\.)(stage_data|ident|seq|producer|key|op|pc|beat|cstage|incoming_[A-Za-z]*|row_select|cin_[a-z_]*)(\[|$)' \
  --focus 'ev=(^|\.)([cmh][123]_[a-z_]*|wc_ok_q)(\[|$)' \
  --focus 'masks=(^|\.)(visible_mask|reverse_mask|metadata_mask|old_sector|receipt_[a-z]*|cur_oh)(\[|$)' "$@" > $O/$lab.log 2>&1
