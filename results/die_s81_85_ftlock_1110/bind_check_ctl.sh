#!/bin/bash
# FTLOCK-S81 D (parent 11-11): control bind (same bsrc tools, plain wave plan b05c29bb) vs bind_ftlk (expect only
# t27/t49) and vs bind8 (isolates wave-src tool drift).  Fixed binddiff (rt/binddiff.py: s81p_ prefix + native dirs +
# bind-root normalisation) in a memory-capped container.
set -u
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock
cat $F/bind_ctl.rc
python3 -I -c "import json;r=json.load(open(\"$F/bind_ctl/bind_report.json\"));e=r[\"errors\"];print(\"ctl strict errors\", len(e) if isinstance(e,list) else e)"
echo "ctl u_fl_ files: $(grep -l u_fl_ $F/bind_ctl/rtl/*.sv | wc -l)"
run() { docker run --rm -u $(id -u):$(id -g) --memory 32g --memory-swap 32g --cpus 2 -v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro -v $F:$F python:3.14-slim \
  python -I -B $F/rt/binddiff.py "$@"; }
echo "=== ctl vs ftlk"; run $F/bind_ctl $F/bind_ftlk $F/s81/plan_ftlk_9c9ac92a70d1.json $F/event_types.json $F/binddiff_ctl_ftlk.json; echo "rc=$?"
echo "=== bind8 vs ctl"; run $F/ref_bind8 $F/bind_ctl $F/bsrc_ctl/physical/die_plan/s81/plan_h2_2249.json $F/event_types.json $F/binddiff_bind8_ctl.json; echo "rc=$?"
echo "=== bind8 vs ftlk"; run $F/ref_bind8 $F/bind_ftlk $F/s81/plan_ftlk_9c9ac92a70d1.json $F/event_types.json $F/binddiff_bind8_ftlk_v2.json; echo "rc=$?"
