#!/usr/bin/env python3
"""Read-only, fail-closed native clock interval proposal. Never emits SDC."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def collect(paths,source,period):
    scenes={};hashes={}
    for path in paths:
        raw=path.read_bytes();hashes[str(path)]=hashlib.sha256(raw).hexdigest()
        for row in csv.DictReader(raw.decode().splitlines(),delimiter='\t'):
            if row['source']!=source or row['corner'] not in ('tt','ff') or not row['scene']:
                raise ValueError('source/corner/scene receipt mismatch')
            lo,hi=float(row['min_ps']),float(row['max_ps'])
            if not all(map(math.isfinite,(lo,hi))) or lo>hi:raise ValueError('invalid propagated clock interval')
            corner=row['corner'];key=(row['clock'],row['pin'])
            if key in scenes.setdefault(corner,{}):raise ValueError('duplicate clock pin receipt')
            scenes[corner][key]=(lo,hi)
    if set(scenes)!= {'tt','ff'}:raise ValueError('both actual TT and FF receipts required')
    if not scenes['tt'] or set(scenes['tt'])!=set(scenes['ff']):raise ValueError('TT/FF pin population differs or empty')
    result={}
    for corner,rows in scenes.items():
        groups={}
        for (clock,pin),(lo,hi) in rows.items():groups.setdefault(clock,[]).append((lo,hi,pin))
        if len(groups)<2:raise ValueError('two native physical roots required')
        bounds={clock:dict(min_ps=min(v)[0],max_ps=max(v,key=lambda x:x[1])[1],min_pin=min(v)[2],max_pin=max(v,key=lambda x:x[1])[2],pins=len(v)) for clock,v in groups.items()}
        pairs=[]
        for a,aa in bounds.items():
            for b,bb in bounds.items():
                if a==b:continue
                pairs.append(dict(source=a,target=b,min_delta_ps=bb['min_ps']-aa['max_ps'],max_delta_ps=bb['max_ps']-aa['min_ps']))
        phi=max(abs(p[k]) for p in pairs for k in ('min_delta_ps','max_delta_ps'))
        result[corner]=dict(groups=bounds,pairs=pairs,observed_all_pair_abs_delta_ps=phi,within_default_three_quarter_T=phi<=.75*period)
    return dict(schema='opentallas.native_phase_diagnostic.v1',source=source,input_sha256=hashes,period_ps=period,default_phi_ps=.75*period,setup_reserve_ps=210,hold_reserve_ps=175,corners=result,adoption=False,certificate=False,unresolved=['Actual root-source physical phase bound across PVT/clock modes and reset/context states','Hard-child effective boundary intervals and source-pinned child timing metadata','Exact source/netlist/SDC/Liberty/parasitic hashes and complete clock-sink inventory','INIT prefix, full finite programme and global head/table joins'],note='Observed CTS/RC intervals are diagnostic; no SDC constraints emitted or weakened.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--period-ps',type=float,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('receipts',nargs='+',type=Path);a=ap.parse_args()
    if len(a.source)!=40 or any(c not in '0123456789abcdef' for c in a.source):raise ValueError('exact source commit required')
    if not math.isfinite(a.period_ps) or a.period_ps<=0:raise ValueError('period must be finite positive')
    a.out.write_text(json.dumps(collect(a.receipts,a.source,a.period_ps),indent=2)+'\n')
if __name__=='__main__':main()
