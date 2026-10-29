#!/bin/bash
# DIE-HEAD-29 replay on KV event27 die STA (DIE-KV-28 sta_E_edge inputs, as HEAD-START-4 replay_kv.sh), base vs new
K=/srv/opentallas-scratch2/claude/dh29
PF=/srv/opentallas-scratch2/claude/die-kv-27-1029/proofE; PL=/srv/opentallas-scratch2/claude/die-kv-26-1029/plan_e26a.json; CA=/srv/opentallas-scratch2/claude/codex-kv-25-1029/native6/native_bind.json
CV=""; for n in 1 2 5 6; do M=kv3_head_eighth_e$n; CV="$CV --core-view $M=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/${M}__3e7fccd216/view/$M"; done
for V in base new; do
  ( S=$K/$V/tools/die_plan; O=$K/sta_$V; rm -rf $O; mkdir -p $O; cp -r /srv/opentallas-scratch2/claude/head-start-4/kv/sta_old/regchar $O/
    python3 $S/die_sta_related.py $PF --plan $PL --out $O --clock-cal spice_edge --cppr-lca --count-align $CA --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $PF/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion view > $O.log 2>&1; echo KV_${V}_RC $? $(date) ) &
done
wait
