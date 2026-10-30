import sys,json,math
from pathlib import Path
sys.path[:0]=['/home/ubuntu/OpenTallas/tools/die_plan','/home/ubuntu/OpenTallas/tools/s81_head']
import schema as S, landed_phase_ocv as L, clk_aocv as CA
D=Path(__file__).parent;p=json.load(open(D/'plan_qc45.json'));t=json.load(open(D/'tree.json'));P=S.Plan(p);T=CA.load('/home/ubuntu/OpenTallas/tools/die_plan/clk_aocv_table_g021.json')
a0types={k for k,v in p['partition_types'].items() if any('a0c' in c.get('module','') for c in v.get('hard_cores',[]))};parts={r['name'] for r in p['partitions'] if r['type'] in a0types}; taps={}
for a in t['taps']:taps.setdefault(a['part'],[]).append(a)
cache={};rows=[];fallback=[]
for pr in p['ports']:
 s,d=pr['src']['part'],pr['dst']['part']
 if not ({s,d}&parts) or s==d or s not in taps or d not in taps:continue
 sel=[]
 for side,part in [('src',s),('dst',d)]:
  key=(part,pr[side]['bus'],pr['width'],pr.get('epoch'),pr.get('kind'))
  if key not in cache:
   try:cache[key]=L.endpoint_taps(P,pr,side,taps[part])
   except ValueError as e:cache[key]=taps[part];fallback.append({'key':key,'reason':str(e)})
  sel.append(cache[key])
 for a in sel[0]:
  for b in sel[1]:
   ca=L.chain(t,a.get('driver',t['node_buf'][str(a['node'])]));cb=L.chain(t,b.get('driver',t['node_buf'][str(b['node'])]));lc,ia,ib=L.lca(ca,cb);pts=[a['xy'],b['xy'],t['sites'][lc]];dist=math.hypot(max(q[0] for q in pts)-min(q[0] for q in pts),max(q[1] for q in pts)-min(q[1] for q in pts))
   rows.append(dict(port=pr['id'],src=s,dst=d,a=a['port'],b=b['port'],lca=lc,ia=ia,ib=ib,dist=dist,aff=s in parts,bff=d in parts))
out={'scope':'all actual declared endpoint-nearest die-tap pairs touching A0-containing partitions; conservative all taps of containing partition, not a claimed per-core binding','fallback_missing_pin_geometry':fallback,'a0_types':len(a0types),'a0_partitions':len(parts),'pairs':len(rows),'clock_cell':t['meta']['clock_cell'],'calibration':'raw actual GRT late arrivals; Ainv class; classB internal NLDM latency. Raw and uniform signed-cal-factor envelope disclosed separately. No OCV or signed gate claim.','corners':{}}
for c,new,old in [('TT',1633.2096,250),('FF',1242.6721,202.5)]:
 arr,nd=L.arrivals(D/f'arr_{c}.txt');A=T['classes']['Ainv'][c];B=T['classes']['B'][c];cr=[]
 for r in rows:
  aa,ab=arr[r['a']],arr[r['b']];u,v=aa-nd[r['lca']],ab-nd[r['lca']]
  def br(u,n,lat):return dict(cell_ps=A['cell_share']*u+B['cell_share']*lat,net_ps=(1-A['cell_share'])*u+(1-B['cell_share'])*lat,stages={'Ainv':n,'B':round(lat/B['mu_stage_ps'])})
  la=new if r['aff'] else old;lb=new if r['bff'] else old
  bs=[br(u,r['ia'],la),br(v,r['ib'],lb)];base=[br(u,r['ia'],old),br(v,r['ib'],old)]
  result=dict(r,u=u,v=v,advance_a=new-old if r['aff'] else 0,advance_b=new-old if r['bff'] else 0,raw_die_delta=ab-aa,uncompensated_delta=ab+lb-aa-la)
  for same in [True,False]:
   key='same' if same else 'regions'
   pess=max(CA.branch_pessimism(T,c,*bs,r['dist'],same,z) for z in ['setup','hold']);bp=max(CA.branch_pessimism(T,c,*base,r['dist'],same,z) for z in ['setup','hold'])
   result[key+'_pess']=pess;result[key+'_increment']=pess-bp;result[key+'_ideal_margin']=416.5-abs(ab-aa)-pess
  result['advance_below_lca_possible']=(u>=result['advance_a'] and v>=result['advance_b']);cr.append(result)
 out['corners'][c]={'internal_latency_ps':new,'advance_ps':new-old,'pairs':len(cr),'below_lca_advance_impossible':sum(not r['advance_below_lca_possible'] for r in cr),'min_a0_unshared_die_ps':min(u for r in cr for flag,u in [(r['aff'],r['u']),(r['bff'],r['v'])] if flag),'max_same_pess_ps':max(r['same_pess'] for r in cr),'max_regions_pess_ps':max(r['regions_pess'] for r in cr),'max_increment_regions_ps':max(r['regions_increment'] for r in cr),'ideal_phase_aligned_worst_margin_ps':min(r['regions_ideal_margin'] for r in cr),'ideal_phase_aligned_under100':sum(r['regions_ideal_margin']<100 for r in cr),'worst':sorted(cr,key=lambda r:r['regions_ideal_margin'])[:12]}
json.dump(out,open(D/'a0_latency_impact.json','w'),indent=2);print(json.dumps({k:v for k,v in out.items() if k!='corners'}));print(json.dumps({c:{k:v for k,v in r.items() if k!='worst'} for c,r in out['corners'].items()},indent=2))
