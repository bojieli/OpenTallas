#!/usr/bin/env python3
"""Remove physically empty W0 header height; preserve width, RTL and edge calendar."""
import json,pathlib,subprocess
from build_a2f_parent_kits import sites
R=pathlib.Path(__file__).resolve().parents[2]
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
s=json.load(open(R/'tools/ref_tile/specs_s81vm_a2f_parent_0310/header.json'))
s['name']='s81_a2_w0_header_native_0310_r2';s['outline']['h']=21.6
s['structural_change']='r1 CTS had 2.4% utilisation, R296.7ps/spread81.5ps, reg->out TT-26.9ps and viewed tall empty body. Compact the empty height86.4->21.6um, preserve216um pin-limited width, all RTL/pinface/bit order/clock root and static edges. Opposite input/output faces now21.6um apart. No timing relaxation.'
s['slot_change_request']['why']='Compact physical header216x21.6 replaces inherited216x86.4 template after viewed CTS spread failure; exact parent pin rebind before adoption.'
pinold=json.load(open(R/'physical/s81_vm_a2f_parent_0310/s81_a2_w0_header.pins.json'));pins=pinold['pins']
for p in pins:
 if p['face']=='N':p['y_um']=21.6
 elif p['face'] in 'WE':p['y_um']=21.6/2+(.144 if p['port']=='rst_n' else 0)
out=R/'physical/s81_vm_a2f_parent_0310/header_r2';out.mkdir(exist_ok=True)
t=[]
for p in pins:
 sz='.024 .192' if p['layer']=='M5' else '.192 .024'
 if p['face'] in 'WE':p['y_um']=min(sites(21.6,'M4'),key=lambda q:abs(q-p['y_um']))
 t.append(f'place_pin -pin_name {{{p["port"]}}} -layer {p["layer"]} -location {{{p["x_um"]} {p["y_um"]}}} -pin_size {{{sz}}} -force_to_die_boundary')
path=out/'s81_a2_w0_header.tcl';path.write_text('\n'.join(t)+'\n');s['io_tcl']=str(path.relative_to(R))
pinold['pins']=pins;pinold['outline_um']=[216,21.6];(out/'s81_a2_w0_header.pins.json').write_text(json.dumps(pinold,indent=1)+'\n')
s['job']['extra_paths']=[s['io_tcl'] if p.endswith('s81_a2_w0_header.tcl') else p for p in s['job']['extra_paths']]
s['job']['tag']='compact2';p=R/'tools/ref_tile/specs_s81vm_a2f_parent_0310/header_r2.json';p.write_text(json.dumps(s,indent=1)+'\n')
subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],cwd=R,check=True)
