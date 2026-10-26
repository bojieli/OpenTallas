#!/usr/bin/env python3
"""Publish one canonical pin window per replicated HBM type, including turns.

Keeping only type declarations for shared interfaces makes pin snapping happen
in the master frame. Global floating-point tie rounding may not create new
masters. Existing pin/track/capacity/type-identity checks remain in force.
"""
import argparse,collections,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools'/'die_plan'),str(HERE)]
import schema as S


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    p=json.loads((a.src/'die_plan.json').read_text());P=S.Plan(p);counts=collections.Counter(q['type'] for q in p['partitions']);pub=set();report={'types':{},'ports_resolved_from_type':[]}
    for tn,num in counts.items():
        if num<2:continue
        t=p['partition_types'][tn];pn=min((n for n,q in P.parts.items() if q['type']==tn),key=lambda n:(not n.startswith('NW_'),P.orient(n)!='R0',n));part=P.parts[pn];w,h=t['outline_um'];o=P.orient(pn);regular={b['name']:b for b in t.get('buses',[])}
        for pr in P.ports.values():
            for side in ['src','dst']:
                if pr[side]['part']!=pn:continue
                bus=pr[side]['bus'];df=pr['face'] if side=='src' else S.OPP[pr['face']];tf=P.type_face(pn,df);axis=1 if tf in 'EW' else 0;base=part['origin_um'][axis];ext=[w,h][axis]
                lo,hi=[v-base for v in pr['window_um']];order=pr.get('order','lsb_low');flip=o in (('MX','R180') if axis==1 else ('MY','R180'))
                if flip:lo,hi=ext-hi,ext-lo;order='lsb_high' if order=='lsb_low' else 'lsb_low'
                win=[round(lo,6),round(hi,6)]
                if bus in regular:regular[bus].update(face=tf,window_um=win,layers=list(pr['layers']),order=order)
                else:
                    slot=next((s for s in t.get('ft_slots',[]) if bus in [s['name']+'_i',s['name']+'_o']),None)
                    if slot is None:raise ValueError(f'{tn}.{bus}: no declaration')
                    stem='in' if bus.endswith('_i') else 'out';slot[stem+'_face']=tf;slot[stem+'_window_um']=win;slot[stem+'_layers']=list(pr['layers']);slot[stem+'_order']=order
                pub.add((tn,bus))
        report['types'][tn]={'representative':pn,'instances':num,'interfaces':sum(x[0]==tn for x in pub)}
    for pr in p['ports']:
        if any(pr[z]['part'] in P.parts and (P.parts[pr[z]['part']]['type'],pr[z]['bus']) in pub for z in ['src','dst']):
            for k in ['face','window_um','layers','order']:pr.pop(k,None)
            report['ports_resolved_from_type'].append(pr['id'])
    # This is an explicit intended-route obstruction contract, not a claim
    # that a routed view exists. The current hard-core generator's auto ceiling
    # is at least M5 and the highest physical plan pin; never free those layers
    # from a generic M5 fallback.
    report['intended_core_obstructions']=[]
    for tn,t in p['partition_types'].items():
        for h in t.get('hard_cores',[]):
            pf=h.get('pins_file')
            if not pf:continue
            pins=json.loads((a.src/pf).read_text())
            if isinstance(pins,dict):pins=pins.get('pins',[])
            layers=[q['layer'] for q in pins if isinstance(q,dict) and q.get('layer','').startswith('M')]
            if not layers:continue
            top=max(layers+[h.get('obs_max','M5'),'M5'],key=lambda L:int(L[1:]))
            h['obs_max']=top
            report['intended_core_obstructions'].append({'type':tn,'inst':h['inst'],'obs_max':top,'basis':'plan pin layers and gen_core_kit_hbm auto route ceiling; routed-view qualification pending'})
    shutil.copytree(a.src,a.out);(a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'type_pins_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({'types':len(report['types']),'ports':len(report['ports_resolved_from_type'])}))

if __name__=='__main__':main()
