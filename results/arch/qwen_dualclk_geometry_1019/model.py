"""Bounded abstract-anchor geometry; no macro views or timing libraries emitted."""
import csv
import hashlib
import json
from pathlib import Path
import re
from reference_planner import plan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'physical/asap7_memory_macros_v2'
def dump(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def pins(text):
    result=[]
    for name, body in re.findall(r'  PIN ([^\n]+)\n(.*?)  END \1\n', text, re.S):
        layer=None; rects=[]
        for line in body.splitlines():
            if 'LAYER ' in line: layer=line.split()[1]
            if 'RECT ' in line:
                rects.append((layer,[round(float(x)*1000) for x in line.split()[1:5]]))
        result.append((name,rects))
    return result

inventory=[]
for directory in sorted(list(BASE.glob('*1r1w2c*'))+list((ROOT/'physical/asap7_memory_macros').glob('*1r1w2c*'))):
    name=directory.name
    data=json.loads((directory/(name+'.json')).read_text())
    lef=(directory/(name+'.lef')).read_text()
    faces={'W':[], 'E':[]}
    w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',lef).groups())
    for pin,rects in pins(lef):
        if pin in ('VDD','VSS'): continue
        _,r=rects[0]; face='W' if r[0]==0 else 'E'
        faces[face].append((r[1]+r[3])/2000)
    inventory.append(dict(name=name,directory=str(directory.relative_to(ROOT)),outline_um=[w,h],capacity_bits=data['capacity_bits'],
        face_counts={f:len(v) for f,v in faces.items()},
        minimum_pitch_um={f:round(min(b-a for a,b in zip(sorted(v),sorted(v)[1:])),6) for f,v in faces.items()},
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()},
        physical_layout_views_present=[p.name for p in directory.iterdir() if p.suffix.lower() in ('.gds','.oas','.cdl','.sp','.spice')],
        semantics_source_sha256=hashlib.sha256((directory/(name+'.v')).read_bytes()).hexdigest() if (directory/(name+'.v')).exists() else None))
dump('inventory.json',inventory)

name='ot_sram_1r1w2c_32x64_m1'
directory=BASE/name
core=json.loads((directory/(name+'.json')).read_text())
lef=(directory/(name+'.lef')).read_text()
reference=json.loads((HERE/'reference_input.json').read_text())
data={k:reference[k] for k in ('rules','calibration','leakage_density_nw_per_um2')}
data.update(name=name+'_p192_access_MODEL',old_outline_nm=[31992,17304],target_height_nm=21144,
    core_geometry=core['area'],source_provenance={'master':name,'source_sha256':inventory[2]['files'] if inventory[2]['name']==name else next(x['files'] for x in inventory if x['name']==name),
        'reference_planner_commit':'19ccd29b9','platform_and_calibration':reference['source_provenance'],
        'reference_scope':'geometry and platform RC only; legacy minimum CQ fields discarded'},
    source_semantics_unchanged={'write':'posedge wclk, CE and per-bit mask', 'read':'posedge rclk, CE holds output when disabled',
        'collision':'same-address simultaneous cross-clock R/W forbidden; no OLD ordering', 'reset':'array and readout unreset'},
    timing={c:{'base':v} for c,v in core['timing'].items()},anchors=[],pg=[],obs=[])
for pin,rects in pins(lef):
    if pin in ('VDD','VSS'):
        data['pg'].extend(dict(net=pin,layer=l,rect_nm=r) for l,r in rects)
        continue
    layer,r=rects[0]; x=(r[0]+r[2])//2; y=(r[1]+r[3])//2
    data['anchors'].append(dict(pin=pin,face='W' if x==12 else 'E',old_center_nm=[x,y],
        kind='clock' if pin in ('wclk','rclk') else 'data_out' if pin.startswith('rd_out') else 'control'))
obs=lef.split('  OBS\n')[1].split('  END\n')[0]
layer=None
for line in obs.splitlines():
    if 'LAYER ' in line: layer=line.split()[1]
    if 'RECT ' in line: data['obs'].append(dict(layer=layer,rect_nm=[round(float(x)*1000) for x in line.split()[1:5]]))
model=plan(data)
# All nominal core CQ figures are analytical estimates, never earliest bounds.
# Publish passive lead costs only; no legacy SC2 MIN or aggregate STA claims.
model['timing']={c:{k:v for k,v in timing.items() if k in (
    'clock_lead_delay_upper_ps','input_lead_delay_upper_ps','output_lead_delay_upper_ps_by_load_ff',
    'clock_pin_cap_ff_by_pin','read_energy_fj','write_energy_fj','clock_access_energy_fj',
    'read_plus_clock_access_energy_fj','write_plus_clock_access_energy_fj',
    'simultaneous_read_write_plus_clock_access_energy_fj','complete_boundary_clock_driver_energy_fj',
    'core_source_leakage_nw','leakage_nw')} for c,timing in model['timing'].items()}
model['hold_policy']='No core CQ minimum established at any corner; no native timing qualification or Liberty emitted.'
model['claim_boundary']='Conditional on original analytical macro internals and cited platform RC; scalar geometry is not full native DRC.'
dump('input.json',data)
dump('model.json',model)
assert model['proof']['geometry_error_count']==0
assert model['proof']['source_to_terminal_connected_paths']==206
assert model['proof']['via_count']==408

placements=[]
for i in range(26):
    placements.append(dict(candidate_bank=i,x_um=(i%3)*86.4,y_um=(i//3)*43.2,
        outline_um=[model['outline_nm'][0]/1000,model['outline_nm'][1]/1000],
        actual_instance=None,parent_escape=None,pg_connection=None))
dump('hybrid.json',dict(placements=placements,macro_array_reserved_um=[259.2,388.8],
    macro_array_reserved_area_um2=259.2*388.8,standard_cell_band=None,
    actual_source_phase_reset_lifetime=None,declared_soft_ff=4672,macro_clocks=52,
    old_macro_area_um2=26*core['area']['macro_area_um2'],new_macro_area_um2=26*model['macro_area_um2'],
    total_signal_access_vias=26*408,total_signal_contacts=26*206,total_pg_contacts=52,
    corner_cost={c:dict(clock_cap_ff=26*sum(t['clock_pin_cap_ff_by_pin'].values()),
        simultaneous_all_banks_energy_fj=26*t['simultaneous_read_write_plus_clock_access_energy_fj'],
        boundary_clock_driver_energy_fj=26*t['complete_boundary_clock_driver_energy_fj']) for c,t in model['timing'].items()}))
with (HERE/'contacts.csv').open('w') as handle:
    writer=csv.writer(handle); writer.writerow(['bank','pin','face','native_anchor_nm','new_terminal_nm','vias','lead_cap_ff','actual_instance','escape','pg_bound'])
    for i in range(26):
        for p in model['paths']:
            writer.writerow([i,p['pin'],p['face'],p['preserved_anchor_nm'],p['terminal_nm'],p['via_count'],p['cap_ff'],'','',''])
print(json.dumps(dict(proof=model['proof'],outline_nm=model['outline_nm'],macro_area_um2=model['macro_area_um2'],timing=model['timing']),indent=2))
