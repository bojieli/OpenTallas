"""Emit an explicitly diagnostic source frame from actual RTL and literal pins.

This is a planned geometry input to diagnostic GEN. It carries no routed views,
clock insertion, Liberty, PG/connectivity or timing qualification.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/closure_loop'))
from submit_lint import top_ports

def emit(kit, out):
    kit,out=Path(kit),Path(out)
    s=json.loads((ROOT/kit/'spec.json').read_text())
    found=[]
    for n in s['sources']:
        text=(ROOT/n).read_text()
        if re.search(r'\bmodule\s+'+re.escape(s['top'])+r'\b',text): found.append(text)
    if len(found)!=1: raise ValueError('one actual selected top definition required')
    text=found[0];ports=top_ports(text,s['top'],s['params'])
    header=text.split('module '+s['top'],1)[1].split('\n);',1)[0]
    directions={}
    for d,names in re.findall(r'\b(input|output|inout)\s+(?:wire|reg)\s+(?:\[[^]]+\]\s+)?([^\n]+)',header):
        for name in names.split(','):
            name=name.strip()
            if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name): directions[name]=d.upper()
    expected={name if low<0 else f'{name}[{i}]':directions[name] for name,width,low in ports for i in (range(low,low+width) if low>=0 else [0])}
    pins={}
    pat=re.compile(r'place_pin -pin_name \{([^}]+)\} -layer (M\d+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}')
    for m in pat.finditer((ROOT/s['io_tcl']).read_text()):
        name,layer=m[1],m[2]
        if name in pins: raise ValueError('duplicate actual pin '+name)
        pins[name]=(layer,*map(float,m.group(3,4,5,6)))
    if set(pins)!=set(expected):raise ValueError({'missing':sorted(set(expected)-set(pins)),'extra':sorted(set(pins)-set(expected))})
    w,h=s['outline']['w'],s['outline']['h'];body=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {s["top"]}','  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {w:.6f} BY {h:.6f} ;','  SYMMETRY X Y ;']
    for name,(layer,x,y,dx,dy) in pins.items():
        box=(x-dx/2,y-dy/2,x+dx/2,y+dy/2)
        if min(box)<-1e-6 or box[2]>w+1e-6 or box[3]>h+1e-6:raise ValueError(('pin outside outline',name,box))
        body += [f'  PIN {name}',f'    DIRECTION {expected[name]} ;','    USE '+('CLOCK' if name==s['clock_port'] else 'SIGNAL')+' ;','    PORT',f'      LAYER {layer} ;','      RECT '+' '.join(f'{v:.6f}' for v in box)+' ;','    END',f'  END {name}']
    body += ['END '+s['top'],'END LIBRARY']
    target=ROOT/out;target.mkdir(parents=True,exist_ok=True);lef=out/(s['top']+'.lef');(ROOT/lef).write_text('\n'.join(body)+'\n')
    sha=lambda n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
    recipes=[s['io_tcl'],str(kit/'floorplan.json'),str(kit/'pin_geometry_plan.json'),str(kit/'clock.sdc'),str(kit/'signoff.sdc')]
    if (ROOT/kit/'pin_track_recipe.json').exists(): recipes.append(str(kit/'pin_track_recipe.json'))
    r=dict(schema='opentallas.kv_d2d_source_frame.v1',kit=str(kit),top=s['top'],params=s['params'],spec_sha256=sha(kit/'spec.json'),source_sha256={n:sha(n) for n in s['sources']},pin_recipe_sha256={n:sha(n) for n in recipes},lef=str(lef),lef_sha256=sha(lef),outline=[w,h],qualification='SOURCE_FRAME_DIAGNOSTIC_ONLY',source_base='de062539e',selected_source='exact real recurring OVL context bytes bound by source_sha256; no scalar view transfer',pins=len(pins),claim='NOT_A_DIE_RESULT: literal source-frame geometry only; no timing, routing, clock, PG or hardened-view qualification')
    (target/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'receipt':str(out/'receipt.json'),'pins':len(pins),'qualification':r['qualification']}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kit');p.add_argument('out');a=p.parse_args();emit(a.kit,a.out)
