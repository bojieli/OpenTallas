#!/usr/bin/env python3
"""Exact static BF die-master pins, retaining every old live pin rectangle.

The packed xb port deliberately spans S(control) and N(data); the emitted bit
map, rather than a guessed bus face, is the physical contract request.
"""
import argparse,json,re,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81'))
import bf_direct_pins as B
from gen_bf_die_wrappers import XB

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 source=ROOT/'physical/s81_bf_hier/front_pins_aligned.tcl'
 old={n:(l,float(x),float(y),w,h) for n,l,x,y,w,h in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}',source.read_text())}
 mapping=B.groups();mapping['xb']=XB
 pins={}
 for port,names in mapping.items():
  for i,n in enumerate(names):pins[f'{port}[{i}]']=dict(zip(('layer','x','y','w','h'),old[n]),source_pin=n)
 assert len(pins)==3230 and len(set(old)-{n for v in mapping.values() for n in v})==1
 assert 'hph' in set(old)-{n for v in mapping.values() for n in v}
 # Reuse the unused hph track for the additional physical clock root.
 pins['io_clk']=dict(zip(('layer','x','y','w','h'),old['hph']),source_pin='hph track reused')
 occupied={round(d['x'],6) for d in pins.values() if d['layer']=='M5' and d['y']==0}
 grid=[round(.012+.096*i,6) for i in range(22,1022)]
 start=next(i for i in range(len(grid)-38) if all(x not in occupied for x in grid[i:i+38]))
 for i,x in enumerate(grid[start:start+38]):pins[f'f_prog[{i}]']=dict(layer='M5',x=x,y=0,w='.024',h='.192',source_pin='new fixed programme pin')
 locs={}
 for n,d in pins.items():
  k=d['layer'],d['x'],d['y'];assert k not in locs,(n,locs.get(k));locs[k]=n
  assert 0<=d['x']<=100.224 and 0<=d['y']<=198.72
 a.out.mkdir(parents=True,exist_ok=True)
 lines=['# Static BF master: exact packed-name map of old live pins +38 programme bits.']
 for n,d in sorted(pins.items()):lines.append(f"place_pin -pin_name {{{n}}} -layer {d['layer']} -location {{{d['x']:.6f} {d['y']:.6f}}} -pin_size {{{d['w']} {d['h']}}} -force_to_die_boundary")
 (a.out/'pins.tcl').write_text('\n'.join(lines)+'\n')
 rec=dict(schema='opentallas.s81.static_bf_pin_request.v1',status='REQUESTED_NOT_GRANTED',top='dsfd_bf_front_static',outline_um=[100.224,198.72],pins=pins,pin_count=len(pins),added_programme_bits=38,new_root='io_clk',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),invariants=dict(legacy_live_pin_locations_preserved=3230,duplicate_locations=0,outside=0,program_contiguous_M5_tracks=38),clock_pins=['ck[0]','io_clk'],clock_rule='both same833.333ps boundary phase, each root delivered at phi-R; actual cross-root D paths must remain timed',note='xb controls are on S, xb data on N; every literal bit has an explicit assigned rectangle. No bus face may replace this table.')
 (a.out/'pin_request.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('BF_STATIC_PIN_PLAN',len(pins),'pins; original live3230 retained; programme38 contiguous bottomM5; io_clk replaces unused hph track')
if __name__=='__main__':main()
