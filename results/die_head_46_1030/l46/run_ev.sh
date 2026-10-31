#!/bin/bash
# DIE-HEAD-46: build one st_str event TAG (edits_TAG.json on input_l40) then chain.sh TAG
T=$1; cd /srv/opentallas-scratch2/claude/die-head-46/event
$HOME/.local/bin/ot-run --hosts localhost --mem 16 --threads 1 --dir $PWD -- python3 build_event_stable6.py meta_tools input_l40 input_l40/start_stages_src25q.json edits_$T.json src25${T}_codex > build_$T.otrun.log 2>&1 || { echo BUILD_FAIL_$T; exit 1; }
bash chain.sh $T > chain_$T.log 2>&1; echo EV_DONE_$T $(date)
