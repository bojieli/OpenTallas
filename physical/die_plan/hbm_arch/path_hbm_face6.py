#!/usr/bin/env python3
"""Expand nonfixed HBM shared-face windows to the default pin budget.

Pack each actual shared E/W face in its existing logical order. Fixed hub/root
interfaces stay pinned. Refuse insufficient face length instead of raising the
pin-density limit. Station/clock rebuilding remains an explicit later gate.
"""
import argparse,collections,json,math,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools'/'die_plan'),str(HERE)]
import schema as S


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--pins-per-um',type=float,default=5.5)
    a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    p=json.loads((a.src/'die_plan.json').read_text());T=p['partition_types'];parts={x['name']:x for x in p['partitions']};groups=collections.defaultdict(list)
    fixed={'root','NW_hub','NE_hub','NW_io','NE_io'};r={'not_release_ready':True,'pin_budget':a.pins_per_um,'faces':[],'changed_types':set(),'windows':[]}
    for pr in p['ports']:
        if pr['face'] not in 'EW' or any(pr[z]['part'] not in parts for z in ['src','dst']):continue
        if any(pr[z]['part'] in fixed for z in ['src','dst']):continue
        groups[tuple(sorted(pr[z]['part'] for z in ['src','dst']))].append(pr)
    for ns,prs in groups.items():
        if any(T[parts[n]['type']].get('hard') for n in ns):continue
        if not any(S.port_pins_count(q)/abs(q['window_um'][1]-q['window_um'][0])>6.4 for q in prs):continue
        prs.sort(key=lambda q:(sum(q['window_um']),q['id']))
        lo=max(parts[n]['origin_um'][1] for n in ns)+8.64;hi=min(parts[n]['origin_um'][1]+T[parts[n]['type']]['outline_um'][1] for n in ns)-8.64
        sizes=[math.ceil(max(abs(q['window_um'][1]-q['window_um'][0]),S.window_for(0,S.port_pins_count(q),q['layers'],per_um=a.pins_per_um))/.192-1e-8)*.192 for q in prs]
        lo=math.ceil(lo/.192-1e-8)*.192;hi=math.floor(hi/.192+1e-8)*.192
        need=sum(sizes)+.576*(len(sizes)-1)
        if need>hi-lo+1e-6:raise SystemExit(f'{ns}: needs{need:.3f}um, available{hi-lo:.3f}um')
        latest=[];end=hi
        for L in sizes[::-1]:latest.append(end-L);end-=L+.576
        latest.reverse();end=lo
        for q,L,late in zip(prs,sizes,latest):
            old=list(q['window_um']);want=sum(old)/2-L/2
            begin=max(end,min(want,late));begin=math.ceil(begin/.192-1e-8)*.192
            if begin+L>hi+1e-6:raise SystemExit(f'{ns}: quantized face exhausted')
            q['window_um']=[round(begin,3),round(begin+L,3)];end=begin+L+.576
            if old!=q['window_um']:
                r['windows'].append({'port':q['id'],'before':old,'after':q['window_um']})
                r['changed_types'].update(parts[q[z]['part']]['type'] for z in ['src','dst'])
        r['faces'].append({'parts':ns,'used_um':round(need,3),'available_um':round(hi-lo,3)})
    for t in T.values():
        if isinstance(t.get('face_pins_per_um'),dict):t.pop('face_pins_per_um')
    r['changed_types']=sorted(r['changed_types']);r['required_next']='Re-derive die FT bands, core-free placement, every changed FT/internal station, reset and clock; no route authorized'
    shutil.copytree(a.src,a.out);(a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'face6_report.json').write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({'changed_ports':len(r['windows']),'changed_types':r['changed_types'],'max_face_use':max(z['used_um']/z['available_um'] for z in r['faces'])},indent=1))

if __name__=='__main__':main()
