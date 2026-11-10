#!/bin/bash
# FTLOCK-S81 go-live check after bind_ftlk finishes (read-only on bind8): strict errors 0, u_fl_ hop latches only in
# t27/t49 bound RTL, per-type digest diff vs bind8 (expected: t27, t49; any other type = explain before going live).
set -u
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock; B=$F/bind_ftlk; B8=/srv/opentallas-scratch2/claude/die-s81-85/s81p7/bind8
cat $F/bind_ftlk.rc
python3 -I -c "import json;r=json.load(open('$B/bind_report.json'));print('errors',r.get('n_errors'),len(r['errors']) if isinstance(r['errors'],list) else r['errors'])"
for t in slice_station__t27 slice_station__t49; do f=$(ls $B/rtl/*${t}.sv); echo "$t u_fl_ latches: $(grep -c 'ot_dp_lk .* u_fl_' $f)  stations: $(grep -c 'ot_dp_st .* u_ft_' $f)"; done
echo "other types with u_fl_: $(grep -l 'u_fl_' $B/rtl/*.sv | grep -v 'slice_station__t27\|slice_station__t49' | wc -l)"
python3 -I /srv/opentallas-scratch2/claude/die-s81-85/s81p7/binddiff.py $B8 $B $F/s81/plan_ftlk_9c9ac92a70d1.json $F/event_types.json $F/binddiff_bind8_ftlk.json > $F/binddiff.out 2>&1; echo "binddiff rc=$?"; cat $F/binddiff.out | cut -c1-300
