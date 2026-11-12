import json,sys,os
W=sys.argv[1]
P=json.load(open(W+'/src28/physical/die_plan/qwen_compute/plan_of_record/plan_qc99_s27.json'))
T=P['partition_types']; out={}
for tn in sorted(os.listdir(W+'/dump')):
    rows=[l.split('\t') for l in open(f'{W}/dump/{tn}/cores.tsv').read().splitlines()]
    pl={h['inst']:(h['origin_um'],h.get('orient','R0')) for h in T[tn].get('hard_cores',[])}
    od={r[0].split('.')[-1]:(float(r[2]),float(r[3]),r[4]) for r in rows}
    mv=[]
    for i,((ox,oy),o) in pl.items():
        k=next((c for c in (i,'u_'+i,'u_cland_'+i[3:]) if c in od),None)
        if k is None: mv.append((i,'missing in odb')); continue
        x,y,oo=od[k]
        if abs(x-ox)>1 or abs(y-oy)>1: mv.append((i,[round(x,2),round(y,2),oo],[ox,oy,o]))
    out[tn]=mv
    print(tn,'plan cores',len(pl),'drift>1um',len(mv),mv[:9])
json.dump(out,open(W+'/drift.json','w'),indent=1)
