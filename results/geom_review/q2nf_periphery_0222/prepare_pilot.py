#!/usr/bin/env python3
"""Stage a source-identical, uncounted Q2NF placement candidate; never launches CAD.
Usage: prepare_pilot.py SOURCE_KIT CANDIDATE_JSON NEW_KIT
The source netlist/RTL is copied unchanged. do-floorplan/do-place can use the
mapped checkpoint after the full saved-AIG miter and negative controls pass;
the ordinary source LEC receipt remains required for qualification.
"""
from pathlib import Path
import sys,json,shutil,re,hashlib
source,geometry,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
assert not out.exists(), 'choose a fresh context; failed contexts are immutable'
d=json.loads(geometry.read_text());W,H=d['outline']
assert len(d['pins'])==6222 and len(d['macros'])==19
skip={'run','lec','views','signoff','__pycache__','face_shell_work'}
shutil.copytree(source,out,ignore=lambda p,n:[x for x in n if x in skip or x.startswith('FAIL_')or x.endswith(('.log','.rc'))])
oldbase=source/'run/results/asap7/hbc_ot_q2nf_rest/base';base=out/'run/results/asap7/hbc_ot_q2nf_rest/base';base.mkdir(parents=True)
files=['1_2_yosys.v','1_2_yosys.sdc','1_synth.v','1_synth.odb','1_synth.sdc','clock_period.txt','mem.json']
for name in files:shutil.copy2(oldbase/name,base/name)
config=(out/'config.mk').read_text()
config+=f'\n# CODEX Q2NF PERIPHERY: new physical form, same mapped source, placement diagnostic ONLY.\noverride export DIE_AREA = 0 0 {W} {H}\noverride export CORE_AREA = 4.32 4.32 {W-4.32} {H-4.32}\noverride export PLACE_DENSITY = 0.40\noverride export MAX_ROUTING_LAYER = M6\n'
(out/'config.mk').write_text(config)
new={(p['bus'],0 if p['bit'] is None else p['bit']):p for p in d['pins']};actual=[];lines=[]
for line in (source/'io.tcl').read_text().splitlines():
 m=re.match(r'place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{[^}]+\} -pin_size \{([^}]+)\}',line)
 if not m:continue
 name,L,size=m.groups();a=re.fullmatch(r'(.*)\[(\d+)\]',name);bus,bit=(a[1],int(a[2]))if a else(name,0)
 p=new[bus,bit];x,y=p['x'],p['y'];face=p['face']
 if face=='W':x=.096
 elif face=='E':x=W-.096
 elif face=='N':y=H-.096
 elif face=='S':y=.096
 actual.append(dict(name=name,layer=L,x=x,y=y));lines.append(f'place_pin -pin_name {{{name}}} -layer {L} -location {{{x:.4f} {y:.4f}}} -pin_size {{{size}}}')
assert len(lines)==6222
(out/'io.tcl').write_text('# Own Q2NF periphery candidate: no POR adoption.\n'+'\n'.join(lines)+'\n')
(out/'pins.json').write_text(json.dumps(d['pins'],indent=1)+'\n')
pp=json.loads((out/'plan_pins.json').read_text());pp['pins']=actual;pp['source']='candidate_geometry.json';pp['candidate_only']=True;pp['view']=pp['module']+'@candidate_periphery_0222';pp['source_sha256']=hashlib.sha256(geometry.read_bytes()).hexdigest()
(out/'plan_pins.json').write_text(json.dumps(pp,indent=1)+'\n')
ml=['# Own periphery placement: no internal issuer wall or old no-cell gap cuts.','foreach {inst master x y orient} {']
for m in d['macros']:ml.append('  {'+m['name']+'} '+m['master']+f" {m['x']:.3f} {m['y']:.3f} "+m['orient'])
ml+=['} {','  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact','}']
(out/'macro_placement.tcl').write_text('\n'.join(ml)+'\n')
shutil.copy2(geometry,out/'candidate_geometry.json')
f=json.loads((out/'freeze.json').read_text());f['outline_um']=[W,H];f['candidate_only']=True;f['candidate_geometry']='candidate_geometry.json';f['candidate_base_view']=f['view'];f['view']=f['module']+'@candidate_periphery_0222';f['pins_sha256']=hashlib.sha256((out/'plan_pins.json').read_bytes()).hexdigest()
(out/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
for name in ['HOLD_CTS','HOLD_ROUTE','DO_NOT_COUNT','PLACE_ONLY']:(out/name).write_text('Own uncounted geometry candidate. Ordinary source EQ required before one PLACE; view actual PLACE before CTS.\n')
# Source identity, not a proof or physical PASS: only the changed geometry is new.
identity={}
for p in (source/'rtl').glob('*'):
 if p.is_file():
  a=hashlib.sha256(p.read_bytes()).hexdigest();b=hashlib.sha256((out/'rtl'/p.name).read_bytes()).hexdigest();assert a==b;identity['rtl/'+p.name]=a
identity['mapped_netlist']=hashlib.sha256((base/'1_2_yosys.v').read_bytes()).hexdigest()
(out/'SOURCE_REUSE.json').write_text(json.dumps(dict(source_kit=str(source),copied_source=identity,first_physical_step='floorplan',new_pin_cycles=0,physical_release='HELD for ordinary source EQ'),indent=1)+'\n')
print('CANDIDATE_STAGED',out,'6222pins19macros source-identical, floorplan/place only; NOT RUN')
