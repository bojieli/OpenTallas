#!/usr/bin/env python3
"""Planned rxsf N-input pin contract for the side-by-side rxsf->rxsb leaf pair.

Only i_v/i_x[31:0] move in the base view: E/M4 -> N/M3. Outputs stay W.
The optional XM view mirrors the complete pin/OBS abstract and snaps V-layer
pins to the plan tracks. Both are unclosed physical successors, requiring
matching new P&R views before they may be bound as SIGNED.
"""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
D = REPO / 'physical/die_plan/s81'
W = H = 140.4
OFFX = .108
VTRACK = {'M3': (.036, .009), 'M5': (.048, .024), 'M7': (.064, .032)}


def write():
    old = json.loads((D/'inputs/core_pins/dsfd_su_t_rxsf.json').read_text())
    lef = subprocess.check_output(['git', '-C', str(REPO), 'show', 'HEAD:'+old['lef']], text=True)
    # Preserve the accepted W-clock / W-output spreading structural remedy.
    # This exact seed is the source pin contract of the in-flight rxsf_w kit.
    seed = json.loads((HERE/'rxsf_w_0719_pins.json').read_text())
    pins = [dict(name=p['bus']+(f"[{p['bit']}]" if p['bit'] is not None else ''),
                 layer=p['layer'],x=p['x'],y=p['y']) for p in seed]
    assert {p['name'] for p in pins} == {p['name'] for p in old['pins']}
    moved = []
    for p in pins:
        if p['name'] == 'i_v' or re.fullmatch(r'i_x\[\d+\]', p['name']):
            index = 0 if p['name'] == 'i_v' else 1+int(re.search(r'\[(\d+)\]',p['name'])[1])
            x = .009+round((63.288+index*.216-.009)/.036)*.036
            p.update(layer='M3', x=round(x,6), y=140.358)
            moved.append(p['name'])
    assert len(moved)==33 and len(set(moved))==33
    for variant in ('north','north_xm'):
        pp = copy.deepcopy(pins)
        if variant.endswith('_xm'):
            used = {}
            for p in sorted(pp,key=lambda p:(p['layer'],-p['x'])):
                x=round(W-p['x'],6)
                if p['layer'] in VTRACK:
                    pitch,offset=VTRACK[p['layer']]
                    k=round((x+OFFX-offset)/pitch)
                    taken=used.setdefault((p['layer'],'N' if p['y']>H/2 else 'S'),set())
                    for dk in (0,1,-1,2,-2,3,-3):
                        xx=round(offset+(k+dk)*pitch-OFFX,6)
                        if xx not in taken and 0<xx<W:
                            x=xx;taken.add(x);break
                    else:raise ValueError(p)
                p['x']=x
        by={p['name']:p for p in pp}
        txt=lef
        def block(m):
            name=m[1]
            if name not in by:return m[0] if re.search(r'USE\s+(POWER|GROUND)',m[0]) else ''
            p=by[name]; x,y=p['x'],p['y']
            vertical=p['layer'] in VTRACK
            dx,dy=(.009,.042) if vertical else (.042,.012)
            direction=re.search(r'DIRECTION\s+(\w+)',m[0])[1]
            return f'  PIN {name}\n    DIRECTION {direction} ;\n    USE SIGNAL ;\n    PORT\n      LAYER {p["layer"]} ;\n        RECT {x-dx:.6f} {y-dy:.6f} {x+dx:.6f} {y+dy:.6f} ;\n    END\n  END {name}'
        txt=re.sub(r'  PIN (\S+)\n.*?\n  END \1',block,txt,flags=re.S)
        if variant.endswith('_xm'):
            # Mirror all retained obstruction rectangles as well.
            off=txt.index('\n  OBS'); a,b=txt[:off],txt[off:]
            def rect(m):
                x0,y0,x1,y1=map(float,m.groups())
                return f'RECT {W-x1:.6f} {y0:.6f} {W-x0:.6f} {y1:.6f} ;'
            b=re.sub(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;',rect,b)
            txt=a+b
        rel=f'physical/die_plan/s81/cores/leaf/lef/dsfd_su_t_rxsf_{variant}.lef'
        (REPO/rel).write_text(txt)
        data=dict(module='dsfd_su_t_rxsf',lef=rel,source=f'LEAF0719 planned {variant} successor: 33 input pins N/M3 on accepted rxsf_w clock/output-spread seed; 0 RTL cycles; NOT SIGNED',
                  pinhash=hashlib.sha256(json.dumps(pp,sort_keys=True).encode()).hexdigest()[:12],pins=pp)
        (D/f'inputs/core_pins/dsfd_su_t_rxsf_{variant}.json').write_text(json.dumps(data,indent=1)+'\n')
        print(variant,len(pp),'pins',data['pinhash'])


if __name__=='__main__':write()
