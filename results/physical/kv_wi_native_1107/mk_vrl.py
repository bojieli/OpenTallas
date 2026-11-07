#!/usr/bin/env python3
"""Wi vRL kit: alias kit + per-pin spine relays (bind reset_spine_out_relay form) + ca ring declarations (gen_phys.ca_ring_land_slots)."""
import json, re, shutil, sys, hashlib
from pathlib import Path
base, new, src = map(lambda x: Path(x).resolve(), sys.argv[1:4])
sys.path.insert(0, str(src/'tools/die_plan')); sys.path.insert(0, str(src/'tools'))
import gen_phys
skip = re.compile(r'^(run|alias_before|lec|physical_completion|preflight_history|__pycache__|FAIL_PREFLOOR|resume\.json|kwrs_.*|\.kwrs_done.*|lec_async\.(?!sh$).*|face_guard.*\.json|face_guard.*\.log|port_bind\.(json|log)|kit_preflight_.*|.*\.log|dont_use_check\.json|selrange\.(json|rc)|1_synth_odb\.v|synth_odb_v\.tcl)$')
new.mkdir(parents=True)
for p in base.iterdir():
    if skip.match(p.name): continue
    (shutil.copytree if p.is_dir() else shutil.copy2)(p, new/p.name)
f = new/'rtl/kv3_hub_Wi_part_bound.sv'; s = f.read_text()
pat = re.compile(r'^    assign (rs_\w+) = (w_\w+\[\d+\]);  // reset spine \(async; landed by ot_dp_rsync in the sink\)$', re.M)
names = [m.group(1) for m in pat.finditer(s)]; assert len(names) == 141 and len(set(names)) == 141
n = pat.sub(lambda m: f'    ot_dp_rrelay u_rsout_{m.group(1)}_0 (.clk(clk), .d({m.group(2)}), .q({m.group(1)}[0]));  // reset spine relay (landed by ot_dp_rsync in the sink)', s)
assert 'reset spine (async' not in n and 'module ot_dp_rrelay' in (new/'rtl/bind_cells.sv').read_text()
f.write_text(n)
pins = {p['bus'] for p in json.loads((new/'pins.json').read_text())}
lc = json.loads((new/'landing_contract.json').read_text())
lc_in = {str(x['name']) for x in lc.get('pins', []) if x.get('dir') == 'in' and x.get('kind') != 'clock'}
ca = gen_phys.ca_ring_land_slots(new/'rtl', pins | lc_in, None)
ls = json.loads((new/'land_slots.json').read_text()); ls['buses'] = {**ca, **ls['buses']}
(new/'land_slots.json').write_text(json.dumps(ls, indent=1) + '\n')
c = {}
for v in ca.values(): c[v['form']] = c.get(v['form'], 0) + 1
(new/'RESET_SPINE_RELAY.json').write_text(json.dumps(dict(schema='opentallas.private_reset_spine_relay.v1', relays=len(names), die_rst=sum('die_rst' in x for x in names), hbm_rst=sum('hbm_rst' in x for x in names), added_clocks_at_sink=dict(assert_=1, release=1), rule='COORD 11-07: registered relay per spine output, no face_guard exemption', source_sha256=hashlib.sha256(n.encode()).hexdigest(), por=False), indent=1) + '\n')
print(len(names), c, len(ls['buses']), 'cland_tstart_in' in ca)
