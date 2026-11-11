#!/bin/bash
# FTLOCK-S81 go-live check (epyc8): strict errors 0; u_fl_ hop latches only in t27/t49; per-type digest diff vs bind8
# (ref_bind8 = byte copy of epyc7 die-s81-85/s81p7/bind8).  binddiff runs in a memory-capped container.
set -u
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock; B=$F/bind_ftlk; B8=$F/ref_bind8
cat $F/bind_ftlk.rc
python3 -I -c "import json;r=json.load(open('$B/bind_report.json'));e=r['errors'];print('strict errors', r.get('n_errors'), len(e) if isinstance(e,list) else e, '| unbound', r.get('unbound') if not isinstance(r.get('unbound'),list) else len(r['unbound']))"
for t in slice_station__t27 slice_station__t49; do f=$B/rtl/s81p_${t}.sv; echo "$t u_fl_ latches: $(grep -c 'ot_dp_lk #(.W([0-9]*)) u_fl_' $f)  ft stations: $(grep -c 'ot_dp_st #(.W([0-9]*)) u_ft_' $f)"; done
echo "other bound files with u_fl_: $(grep -l 'u_fl_' $B/rtl/*.sv | grep -v 'slice_station__t27\.sv\|slice_station__t49\.sv' | tr '\n' ' ')"
docker run --rm -u $(id -u):$(id -g) --memory 32g --memory-swap 32g -v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro -v $F:$F python:3.14-slim \
  python -I -B $F/binddiff.py $B8 $B $F/s81/plan_ftlk_9c9ac92a70d1.json $F/event_types.json $F/binddiff_bind8_ftlk.json > $F/binddiff.out 2>&1
echo "binddiff rc=$?"; cut -c1-400 $F/binddiff.out
