#!/usr/bin/env python3
"""HBM SU-row corridor candidate: add 535.68um, retain NS windows with a bottom H jog, pack outside it.

The matching PATH-HBM helper snapshot is required for internal/FT station and
wavefront regeneration. Every changed cycle is published, not hidden.
"""
import argparse,copy,importlib,json,math,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools'/'die_plan'),str(HERE)]
import schema as S


def pack_columns(t,spans):
    w,h=t['outline_um']; merged=[]
    for a,b in sorted(spans):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    bounds=[8.64]+[v for a,b in merged for v in [max(8.64,a-8.64),min(w-8.64,b+8.64)]]+[w-8.64]
    cols=[]
    for a,b in zip(bounds[::2],bounds[1::2]):
        x=math.ceil(a/8.64-1e-8)*8.64
        while x+164.16<=b+1e-6:
            cw=440.64 if x+440.64<=b+1e-6 else 164.16
            cols.append([round(x,3),cw,449.28]);x+=cw+8.64
    pos={}
    for c in sorted(t['hard_cores'],key=lambda c:(-c['outline_um'][1],-c['outline_um'][0])):
        cw,ch=c['outline_um'];opts=[z for z in cols if z[1]>=cw-1e-6 and z[2]+ch<=h-8.64+1e-6]
        if not opts:raise ValueError(f"no corridor-safe slot for {c['inst']}; columns {cols}")
        z=min(opts,key=lambda z:(z[1]-cw,z[2]));pos[c['inst']]=[z[0],round(z[2],3)];z[2]+=ch+8.64
    return pos,merged,cols


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--helper',type=Path,required=True)
    ap.add_argument('--grow',type=float,default=535.68);ap.add_argument('--repair',action='store_true');a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    sys.path.insert(0,str(a.helper.resolve()));E=importlib.import_module('path_hbm_edge');B=importlib.import_module('b2o');BN=importlib.import_module('b2n')
    p=json.loads((a.src/'die_plan.json').read_text());before=S.Plan(copy.deepcopy(p),a.src/'die_plan.json');r={'not_release_ready':True,'moves':{},'aligned':[]}
    E.CUT=10022.4;_,stretched,shifted=E.grow(p,a.grow,r)
    T=p['partition_types'];parts={q['name']:q for q in p['partitions']};affected=set(stretched);defs={'q_su00':['L28x3'],'q_su01':['L29x1'],'q_su11':['L30x1','L31x1']}
    for tn,slots in defs.items():
        t=T[tn];pn=next(n for n,q in parts.items() if q['type']==tn and q.get('orient','R0')=='R0');ox=parts[pn]['origin_um'][0];spans=[]
        for slot in slots:
            po=next(pr for pr in p['ports'] if pr['src']=={'part':pn,'bus':slot+'_o'})
            lo,hi=po['window_um'];local=[lo-ox,hi-ox];spans.append([local[0]-8.64,local[1]+8.64])
        pos,merged,cols=pack_columns(t,spans);moves=[]
        for c in t['hard_cores']:
            old=list(c['origin_um']);new=pos[c['inst']];moves.append({'inst':c['inst'],'before':old,'after':new});c['origin_um']=new
            for ct in t.get('contents',[]):
                if ct['inst']==c['inst'] and 'origin_um' in ct:ct['origin_um']=new
            for tap in t.get('clock',{}).get('taps',[]):
                if (tap['name']==c['inst'] or tap['name'].startswith(c['inst']+'.')):tap['xy']=[round(tap['xy'][i]+new[i]-old[i],3) for i in [0,1]]
        t['die_ft_bands']=[z for z in t.get('die_ft_bands',[]) if z['dir']!='NS']+[
            {'dir':'EW','span_um':[8.64,440.64],'layers':['M4','M6'],'die_share':1.0,'note':'SU bottom core-free H jog preserves legal neighboring NS windows'}]+[
            {'dir':'NS','span_um':[round(v,3) for v in sp],'layers':['M5','M7'],'die_share':1.0,'note':'SU row: core-free vertical FT run; bottom H jog preserves neighbor abutment'} for sp in merged]
        r['moves'][tn]={'cores':moves,'corridors':merged,'columns':cols}
    shutil.copytree(a.src,a.out)
    if a.repair:
        log=[];r['internal_unroutable']=B.internal_stations(p,a.out,sorted(affected),log)
        import hbm_bit_stations as HBS
        try:fr=HBS.repair(p,log=lambda m:None,only_types=sorted(affected))
        except HBS.RepairFailure as e:fr=e.report
        r['ft_repair']=fr
        BN.reset_wavefront(p,log);r['repair_log']=log
    else:r['repair']='NOT RUN; stations/reset/clock regeneration required'
    after=S.Plan(p,a.out/'die_plan.json');p['latency']['lanes']={lid:after.lane_latency(lid) for lid in after.lanes}
    r['lane_cycle_delta']={lid:p['latency']['lanes'][lid]['cycles']-before.lane_latency(lid)['cycles'] for lid in after.lanes if p['latency']['lanes'][lid]['cycles']!=before.lane_latency(lid)['cycles']}
    r['clock_pending']='Full die Htree and moved-core local trees must be regenerated; no STA/route authorized'
    (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'die_io.json').write_text(json.dumps(p['die'].get('io',[]),indent=1)+'\n');(a.out/'su_corridor_report.json').write_text(json.dumps(r,indent=1,default=str)+'\n')
    print(json.dumps(r,indent=1,default=str))

if __name__=='__main__':main()
