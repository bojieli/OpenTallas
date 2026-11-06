import json,pathlib,sys,copy,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import station_resite as S
r=pathlib.Path(__file__).resolve().parent
j=json.loads((r/'new.json').read_text());base=json.loads((r/'base.json').read_text());report={}
for tn in ['q_hub_nw','q_hub_ne']:
 t=j['partition_types'][tn];old=base['partition_types'][tn];rects=S.core_rects(t);orects=S.core_rects(old);R=S.HR.Raster(*t['outline_um'],[p[1:] for p in rects]);S._FREE[tn]=R.f;todo=[]
 for i,s in enumerate(t['internal_stations']):
  newhit=any(S.blocked(rects,p) and not S.blocked(orects,p) for p in s.get('regs_um',[]))
  moved_endpoint=any('u_xl_Q_aqhi' in str(s.get(k,'')) for k in ['launch','capture','conn']) and s.get('regs_um') and S.max_hop(s)>405.00001
  if newhit or moved_endpoint:todo.append((tn,i,tuple(s['from_um']),tuple(s['to_um']),len(s.get('regs_um',[])),405.0))
 print(tn,'newly-covered chains',len(todo),flush=True)
 with ProcessPoolExecutor(8,mp_context=mp.get_context('fork')) as ex:results=list(ex.map(S._solve,todo,chunksize=2))
 rows=[];failed=[]
 for item,result in zip(todo,results):
  _,i,a,b,n,_=item;_,k,regs=result;s=t['internal_stations'][i]
  if k is None:failed.append(dict(index=i,conn=s.get('conn'),old=n));continue
  s['regs_um']=regs;s['note']=s.get('note','')+' | p36 WBQ footprint exact-count station resite'
  rows.append(dict(index=i,conn=s.get('conn'),bits=s.get('bits'),old=n,new=k,added=k-n,max_hop=S.max_hop(s)))
 report[tn]=dict(rows=rows,failed=failed,added_cycles=sum(x['added'] for x in rows))
 print(tn,'resited',len(rows),'failed',len(failed),'added cycles',report[tn]['added_cycles'],flush=True)
(r/'plan_resited.json').write_text(json.dumps(j)+'\n');(r/'station_report.json').write_text(json.dumps(report,indent=1)+'\n')
