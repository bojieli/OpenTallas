#!/usr/bin/env python3
"""Refresh derived HEAD raw-export descriptors against the emitting reset tree.

Writes a separate candidate. Port/net names, physical pin positions and all
latency/clock/reset structures remain unchanged. No plan-of-record update.
"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
import reset_tree as RT
ROLES={'raw','boot','bootstrap_transport'}

def actual_source(tree,row):
    rel=RT.start_relays(tree) if tree.get('start') else tree['relays']
    matches=[r for r in rel if r.get('q')==row['net'] and (not tree.get('start') or r.get('role') in ROLES)]
    if len(matches)!=1:
        raise ValueError(f"{row['port']}: expected exactly one eligible producer of {row['net']}, found {len(matches)}")
    return matches[0]

def refresh(raw,plan_path,types=None):
    out=copy.deepcopy(raw);P=S.Plan(out,path=Path(plan_path));ledger=[]
    for tn,t in out['partition_types'].items():
        if types is not None and tn not in types:continue
        rows=t.get('reset_start_raw_exports',[])
        if not rows:continue
        tree=RT.for_type(P,tn);pins={p['name']:p for p in t.get('clock',{}).get('landing_contract',{}).get('pins',[])}
        for row in rows:
            if row.get('existing_port'):continue
            source=actual_source(tree,row)
            if row['port'] not in pins:raise ValueError(f"{tn}.{row['port']}: declared output pin missing")
            pin=pins[row['port']]
            if (pin.get('dir'),pin.get('kind'),pin.get('source_registered'))!=('out','ctl',True):
                raise ValueError(f"{tn}.{row['port']}: not a registered control output")
            old=copy.deepcopy(row);row.update(instance=source['name'],xy_um=list(source['xy']))
            pin['source_instance']=source['name']
            if t.get('private_reset_start_exports'):
                pin.update(source_net=row['port'],source_copy_from_net=row['net'],source_output_pin='export_q')
            else:pin['source_net']=row['net']
            ledger.append(dict(type=tn,port=row['port'],old=old,new=copy.deepcopy(row),depth=source['depth'],role=source.get('role'),changed=old!=row))
    # Fail closed if descriptors themselves influence the tree being declared.
    Q=S.Plan(out,path=Path(plan_path));checked={}
    for e in ledger:
        if e['type'] not in checked:checked[e['type']]=RT.for_type(Q,e['type'])
        row=e['new'];a=actual_source(checked[e['type']],row)
        if (a['name']!=row['instance'] or a['q']!=row['net'] or list(a['xy'])!=row['xy_um']):
            raise ValueError(f"{e['type']}.{row['port']}: reset tree changed while refreshing descriptors")
    return out,ledger

def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--types');ap.add_argument('--ledger',required=True);a=ap.parse_args()
    source=Path(a.plan).resolve();target=Path(a.out).resolve()
    if source==target or target.exists():raise ValueError('a fresh candidate output path is required')
    raw=json.loads(source.read_text());out,ledger=refresh(raw,source,set(a.types.split(',')) if a.types else None)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(out,indent=1)+'\n');Path(a.ledger).write_text(json.dumps(ledger,indent=2)+'\n')
    print('HEAD_RAW_EXPORT_CANDIDATE',target,'rows',len(ledger),'changed',sum(e['changed'] for e in ledger))
if __name__=='__main__':main()
