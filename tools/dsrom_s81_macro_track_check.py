#!/usr/bin/env python3
"""Focused geometry and source-selection checks; no physical tool calls."""
import json
from pathlib import Path
import tempfile
import dsrom_s81_macro_track_prep as P

r=P.read(P.BASE/'preparation_r2.json')
assert r['selected']['stages']==81 and r['selected']['pairs_per_die']==2417
assert r['selected']['total_dies']==368 and r['selected']['return_depth']==64
assert r['selected_inventory_input']['weight_macros_per_rank_die']==9668
assert r['actual_selected_object_status']['S81_frame_LEFs_netlist_DEF'] is None
assert not r['gates']['historical_S82_fit_credit']
assert not any(r['launches'].values())
rom=next(x for x in r['object_pin_supply_inputs'] if x['macro']=='ot_rom_4096x274_m8')
assert rom['alignment']['summary']['M4']['origin_rule_mod_track_nm']['MX']==[42]
assert rom['joint_site_track_lattices']['M4']['MX']=={'period_nm':2160,'origin_residues_nm':[810]}
assert P.lattice([24],48,54)=={'period_nm':432,'origin_residues_nm':[216]}
# Overlapping PG and clock exclusions must not debit the same track twice.
for blocked in ([],[[12,108]],[[12,60],[40,108]],[[0,1000]],[[60,60]]):
 a=P.channel_count(0,240,48,[12],blocked)
 expected=[t for t in range(241) if t%48==12 and not any(lo<=t<=hi for lo,hi in blocked)]
 assert a['available_tracks']==len(expected)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'old.json';p.write_text(json.dumps({'stages':82,'selection_commit':r['selection_commit'],'instances':[]}))
 try:P.selected_rows(p,'instances')
 except ValueError:pass
 else:raise AssertionError('S82 was accepted as selected geometry')
 p.write_text(json.dumps({'stages':81,'selection_commit':r['selection_commit'],'instances':[]}))
 assert P.selected_rows(p,'instances')==[]
print('PASS: S81 binding, retained ROM mirrored alignment, site/track intersection, PG/clock interval union, explicit S82 refusal; no P&R')
