#!/usr/bin/env python3
"""Count actual leaf pin loads, recursively expanding kept source-copy paramods."""
import argparse,collections,json
from pathlib import Path

def audit(data,top):
    modules=data['modules'];root=modules[top];cells={}
    def expand(mname,prefix,binding):
        m=modules[mname]
        def wire(b):return b if isinstance(b,str) else binding.get(b,(prefix,b))
        for name,c in m['cells'].items():
            n=prefix+'/'+name;con={p:[wire(b) for b in bb] for p,bb in c['connections'].items()}
            sub=modules.get(c['type'])
            if sub and not sub.get('attributes',{}).get('blackbox') and sub.get('cells'):
                mapping={b:v for p,bb in con.items() for b,v in zip(sub['ports'][p]['bits'],bb)}
                expand(c['type'],n,mapping)
            elif c['type']!='$scopeinfo':cells[n]={**c,'connections':con}
    expand(top,'root',{})
    loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
    for n,c in cells.items():
        assert set(c['connections'])==set(c['port_directions']), 'untyped pin '+n
        for p,bb in c['connections'].items():
            for b in bb:
                if isinstance(b,str):continue
                (loads if c['port_directions'][p]=='input' else drivers)[b].append(n+'.'+p)
    inputs={('root',b) for p in root['ports'].values() if p['direction']=='input' for b in p['bits'] if isinstance(b,int)}
    clock=('root',root['ports']['ck']['bits'][0])
    undriven={str(b):nn[:4] for b,nn in loads.items() if b not in drivers and b not in inputs}
    multiple={str(b):nn for b,nn in drivers.items() if len(nn)>1 or b in inputs}
    high={str(b):{'loads':len(nn),'sinks':nn[:4]} for b,nn in loads.items() if b!=clock and len(nn)>32}
    types=collections.Counter(c['type'] for c in cells.values())
    out={'leaf_cells':len(cells),'cell_types':dict(types),'clock_pins':len(loads[clock]),
         'max_nonclock_load':max(len(v) for b,v in loads.items() if b!=clock),
         'undriven':undriven,'multiple_drivers':multiple,'over32':high,
         'native_buffers':types['BUFx2_ASAP7_75t_R'],
         'status':'PASS' if not (undriven or multiple or high) else 'FAIL'}
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('json');ap.add_argument('--top',default='qfd_sys_face_control_safe');ap.add_argument('--out',required=True);a=ap.parse_args()
    out=audit(json.loads(Path(a.json).read_text()),a.top);Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['cell_types','undriven','multiple_drivers','over32']}))
    assert out['status']=='PASS','mapped load/connectivity failed; inspect '+a.out
if __name__=='__main__':main()
