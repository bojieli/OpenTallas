#!/usr/bin/env python3
"""HBM-Q2NF-RF vF: vD ring translated +77.76 um in x inside width 786.24 (W strip 30 -> 108 um), macro y snapped to M4 tracks.
Same RTL/netlist as vD. Needs a one-block plan event (outline 786.24x311.04, pins, M6). Stages kit, never launches."""
import shutil,json,re,sys
from pathlib import Path
SRC=Path('/srv/opentallas-scratch2/claude/die-hbm-92-open/q2nf/vd1/kit_vD')
OUT=Path(sys.argv[1]); assert not OUT.exists()
DX=77.76; W,H=786.24,311.04
skip={'run','lec','lec_vd','lec_vd_r1','views','signoff','__pycache__','face_shell_work','lec_cone','lec_async.runs'}
def ign(p,n):
    return [x for x in n if x in skip or x.startswith('FAIL_') or x.endswith(('.log','.rc')) or x.startswith(('run_vd','vd_inner','postcts_gate','lec_async.')) and x!='lec_async.sh' or x in('placed.csv','ot_face_flops.txt','hold_census.txt','dtap.txt','face_guard.json','CTSGRT_DONE.txt','PLACE_DONE.txt','candidate_geometry.json')]
shutil.copytree(SRC,OUT,ignore=ign)
BASE='run/results/asap7/hbc_ot_q2nf_rest/base'; (OUT/BASE).mkdir(parents=True)
for f in ['1_2_yosys.v','1_2_yosys.sdc','1_synth.v','1_synth.odb','1_synth.sdc','clock_period.txt','mem.json']: shutil.copy2(SRC/BASE/f,OUT/BASE/f)
def rw(p,t): (OUT/p).unlink(missing_ok=True); (OUT/p).write_text(t)
# pins: W face stays at x=0 side, every other pin moves with the ring
pins=json.loads((SRC/'pins.json').read_text())
for p in pins:
    if p['face']=='W': continue
    if p['face']=='E': p['x']=W
    else: p['x']=round(p['x']+DX,3)
rw('pins.json',json.dumps(pins,indent=1)+'\n')
pp=json.loads((SRC/'plan_pins.json').read_text()); out=[]; lines=['# HBM-Q2NF-RF vF: vD pins, ring translated +77.76 um; W face unchanged. Plan event pending.']
sizes={m[0]:m[1] for m in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer \w+ -location \{[^}]+\} -pin_size \{([^}]+)\}',(SRC/'io.tcl').read_text())}
def isW(q): return q['x']<1.0
def isE(q): return q['x']>700.0
for q in pp['pins']:
    x,y=q['x'],q['y']
    if isW(q): pass
    elif isE(q): x=round(W-0.096,3)
    else: x=round(x+DX,3)
    out.append(dict(name=q['name'],layer=q['layer'],x=x,y=y))
    lines.append('place_pin -pin_name {%s} -layer %s -location {%.4f %.4f} -pin_size {%s}'%(q['name'],q['layer'],x,y,sizes[q['name']]))
assert len(out)==6222
pp['pins']=out; pp['source']='HBM-Q2NF-RF vF translate of vD'; pp['candidate_only']=True
rw('plan_pins.json',json.dumps(pp,indent=1)+'\n'); rw('io.tcl','\n'.join(lines)+'\n')
# macros
def snap(y): return round(round((y-0.012)/0.048)*0.048+0.012,3)
txt=(SRC/'macro_placement.tcl').read_text().splitlines(); new=[]; n=0
for l in txt:
    m=re.match(r'(\s+\{.*\} \S+) ([\d.]+) ([\d.]+) (R0)$',l)
    if m: new.append('%s %.3f %.3f %s'%(m[1],float(m[2])+DX,snap(float(m[3])),m[4])); n+=1
    else: new.append(l)
assert n==19
new[0]='# HBM-Q2NF-RF vF: vD ring +77.76 um in x, y on M4 tracks (0.012 mod 0.048); W strip 108 um.'
rw('macro_placement.tcl','\n'.join(new)+'\n')
cfg=(OUT/'config.mk').read_text()+f"""
# HBM-Q2NF-RF vF: vD ring translated, W strip 108 um, macros on M4 tracks; same RTL/netlist as vD; PIN CYCLES 0.
override export DIE_AREA = 0 0 {W} {H}
override export CORE_AREA = 4.32 4.32 781.92 306.72
override export MAX_ROUTING_LAYER = M6
override export PLACE_DENSITY = 0.40
"""
rw('config.mk',cfg)
f=json.loads((SRC/'freeze.json').read_text()); f['outline_um']=[W,H]; f['form']='vF (HBM-Q2NF-RF): vD ring +77.76 um, plan event pending'; rw('freeze.json',json.dumps(f,indent=1)+'\n')
rw('DO_NOT_COUNT','DO_NOT_COUNT: HBM-Q2NF-RF vF private outline 786.24x311.04 + pins; one-block plan event needed + current-tag sign-off\n')
print('STAGED',OUT)
