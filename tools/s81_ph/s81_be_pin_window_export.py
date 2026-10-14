#!/usr/bin/env python3
"""Conservative face-pin windows for the source-pinned legacy BE abstract.

Run after abstract_pin_stub.py. Keep the largest clear outer window only at blocked face PORT rectangles.
Unblocked PORT rectangles retain their original geometry. Retain all removed PORT metal as same-layer OBS;
no routed metal/OBS is erased and all pin identities remain unchanged. This
candidate requires actual parent access/DRC qualification and its honest M7 cap.
"""
import argparse, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C
import abstract_pin_stub as A

def window_export(src,frac=.25):
    model=C.parse_lef(src);head,obs=A.split_lef(src)
    retained=[];changed=[]
    obstruction_by_layer={}
    for r in model['obs']:obstruction_by_layer.setdefault(r[0],[]).append(r)
    def pin_replace(match):
        name,body=match.group(1),match.group(2)
        if re.search(r'USE (POWER|GROUND)',body):return match.group(0)
        def layer_replace(lm):
            layer,body=lm.group(1),lm.group(2)
            def rectangle(rm):
                x,y,u,v=map(float,rm.groups());face=C.face_of((layer,x,y,u,v),model['W'],model['H'])
                if face is None:return rm.group(0)
                level=C.metal(layer)
                above=obstruction_by_layer.get(f'M{level+1}',[])
                if not C._overlaps((layer,x,y,u,v),above):return rm.group(0)
                fractions=[.75,.5,.25]
                for fraction in fractions:
                    a,b,c,d=x,y,u,v
                    if face=='W':c=x+(u-x)*fraction
                    elif face=='E':a=u-(u-x)*fraction
                    elif face=='S':d=y+(v-y)*fraction
                    else:b=v-(v-y)*fraction
                    if not C._overlaps((layer,a,b,c,d),above):break
                assert not C._overlaps((layer,a,b,c,d),above),name
                a,b,c,d=x,y,u,v
                chosen=fraction
                if face=='W':c=x+(u-x)*chosen;removed=(c,y,u,v)
                elif face=='E':a=u-(u-x)*chosen;removed=(x,y,a,v)
                elif face=='S':d=y+(v-y)*chosen;removed=(x,d,u,v)
                else:b=v-(v-y)*chosen;removed=(x,y,u,b)
                retained.append((layer,*removed));changed.append(dict(pin=name,face=face,layer=layer,fraction=chosen,old=[x,y,u,v],window=[a,b,c,d]))
                return 'RECT '+' '.join(f'{q:.6f}'.rstrip('0').rstrip('.') for q in [a,b,c,d])
            return 'LAYER '+layer+' ;'+re.sub(A._RECT,rectangle,body)
        body=re.sub(r'LAYER (\S+) ;(\s*(?:RECT[^;]*;\s*)+)',layer_replace,body)
        return '  PIN '+name+'\n'+body+'\n  END '+name
    head=re.sub(r'  PIN (\S+)\n(.*?)\n  END \1',pin_replace,head,flags=re.S)
    # Add removed, electrically real pin metal to OBS instead of hiding it.
    extra=''.join('\n    LAYER '+layer+' ;\n      RECT '+' '.join(f'{q:.6f}'.rstrip('0').rstrip('.') for q in [x,y,u,v])+' ;' for layer,x,y,u,v in retained)
    obs=re.sub(r'\n  END\s*\n',extra+'\n  END\n',obs,count=1)
    out=head+obs
    after=C.parse_lef(out)
    assert set(after['pins'])==set(model['pins'])
    assert len(after['obs'])==len(model['obs'])+len(retained)
    # Each cut exactly partitions one original PORT rectangle into its retained
    # access window and the new OBS; overlap is boundary-only.
    for row,rem in zip(changed,retained):
        x,y,u,v=row['old'];a,b,c,d=row['window'];_,e,f,g,h=rem
        assert abs((u-x)*(v-y)-(c-a)*(d-b)-(g-e)*(h-f))<1e-9
    return out,dict(strategy='onlyblockedfacepins;largestclearfraction .75/.5/.25',changed_rectangles=len(changed),pin_identity_preserved=True,removed_port_metal_retained_as_obs=True,changes=changed)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--record',type=Path,required=True);a=ap.parse_args()
    out,record=window_export(a.input.read_text());a.output.write_text(out);a.record.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='changes'}))
if __name__=='__main__':main()
