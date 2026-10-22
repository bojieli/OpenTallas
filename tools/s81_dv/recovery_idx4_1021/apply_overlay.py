#!/usr/bin/env python3
"""Restore actual IDX4 master bindings onto the current table; preserve current landing/frame data."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); t=json.loads(p.read_text()); o=json.loads(Path(__file__).with_name('overlay.json').read_text())
for key in ('masters','rtl_widths'):t.setdefault(key,{}).update(o[key])
for m in o['status_fault_masters']:
    if m not in t.setdefault('status_fault_masters',[]):t['status_fault_masters'].append(m)
for key in ('relay_mirror_vertical','relay_mirror_vertical_note'):t[key]=o[key]
p.write_text(json.dumps(t,indent=1)+'\n')
