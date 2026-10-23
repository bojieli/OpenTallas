"""Extract every scalar FF/reset/control sink from the unchanged real fabric."""
import json,pathlib,re,collections,sys
import qc_fullm_kit as G
root=G.ROOT/G.PLAN;name=sys.argv[1];v=next(v for v,n in G.KITS.items() if n==name);s=json.loads((root/(name+'_joint_solution.json')).read_text());d=json.loads((root/(name+'_bank_inputs.json')).read_text());assert s['status'] in ['OPTIMAL','FEASIBLE'];txt,X,R=G.fabric_rtl(v);G.BODY[v]=txt;env,_=G.placement(v,X,R);P={n:dict(p,x=s['hard'][n][0],y=s['hard'][n][1]) for n,p in d['hard'].items()};ranges,faces,_=G.pins(v,env)
def fixedbays(*args):
 G.BAYS[v]={};return [f'{n}\t{x+w/2:.3f}\t{y+h/2:.3f}\t{x:.3f}\t{x+w:.3f}\t{y:.3f}\t{y+h:.3f}' for n,(x,y,w,h) in s['bays'].items()]
G.bays=fixedbays;tsv=G.sites(v,env,P,R,G.soft_anchor(txt,P));at={l.split('\t')[0]:list(map(float,l.split('\t')[1:3])) for l in tsv.splitlines() if l and not l.startswith('#')}
par=r'(?:[^()]|\([^()]*\))*';inst_re=re.compile(r'\b(qfd_\w+)\s+(?:#\(('+par+r')\)\s+)?(u_\w+)\s+\(([^;]*?)\);',re.S)
scalar={};qmap={};instances=[]
for mt in inst_re.finditer(txt):
 mod,pa,inst,po=mt.groups();ps=dict(G.PORT_RE.findall(po));pp=dict(G.PORT_RE.findall(pa or ''));n=inst if inst.startswith('u_t_') else 'u_fab.'+inst;instances.append((mod,n,ps))
 if mod=='qfd_q3h_stn' and pp.get('W','1')=='1':
  assert pp.get('N','1')=='1',(n,pp)
  hint=at.get(n)
  if hint is None:
   fm=re.fullmatch(r'u_fab\.u_farq_(\d)_(\d)',n);assert fm,n
   hp=P['u_fab.u_x_'+fm[1]+'_'+fm[2]];ww,hh,_=G.LEFS[hp['kind']];hint=[hp['x']+ww+12,hp['y']+hh/2]
  scalar[n]={'d':ps['d'],'q':ps['q'],'clock':ps['ck'],'hint':hint};qmap[ps['q']]=n
_,_,resolve,widths=G.netlist(txt);inv={}
for mt in re.finditer(r'(?:assign|wire(?:\s+\[[^]]+\])?)\s+(\w+)\s*=\s*~\s*(\w+)\s*;',txt):inv[mt[1]]=mt[2]
def src(e):
 bb=G.split_expr(e);assert len(bb)==1,(e,bb);nm,k=bb[0];k=0 if k is None else k;dr,base=resolve((nm,k));seen=set()
 while dr is None and base[0] in inv:
  assert base not in seen;seen.add(base);dr,base=resolve((inv[base[0]],base[1]))
 if dr:
  x,y=G.pin_at(P,*dr);return {'point':[x,y],'hard':dr}
 if base[0] in qmap:return {'node':qmap[base[0]]}
 if base[0] in ranges:
  if base[0]=='far':return {'static_strap':'far','premise':'actual inherited SDC set_case_analysis0; fixed instance strap, no dynamic data mask'}
  return {'point':G.port_xy(env,ranges,faces,base[0],base[1],widths.get(base[0],1)),'port':base}
 return {'UNKNOWN':e,'resolved':base}
edges=[];unknown=[];static=[]
for n,p in scalar.items():
 a=src(p['d']);z={'src':a,'dst':{'node':n},'kind':'scalar_d'}
 (unknown if 'UNKNOWN' in a else static if 'static_strap' in a else edges).append(z)
for mod,n,ps in instances:
 if n in s['bays']:
  a=src(ps['rsi']);z={'src':a,'dst':{'box':s['bays'][n],'bay':n},'kind':'soft_rsi'}
  (unknown if 'UNKNOWN' in a else static if 'static_strap' in a else edges).append(z)
 elif n in P:
  for pin in ['rsi','rst_n','sidx']:
   if pin not in ps:continue
   for j,bit in enumerate(G.split_expr(ps[pin])):
    nn,kk=bit;expr=nn if kk is None else f'{nn}[{kk}]';a=src(expr);x,y=G.pin_at(P,n,pin,j);z={'src':a,'dst':{'point':[x,y],'hard':[n,pin,j]},'kind':'hard_'+pin}
    (unknown if 'UNKNOWN' in a else static if 'static_strap' in a else edges).append(z)
out={'name':name,'outline':d['outline'],'scalar':scalar,'hard':s['hard'],'bays':s['bays'],'edges':edges,'unknown':unknown,'static_straps':static,'source_scope':'unchanged real fabric scalar FF d/q, all hard reset/sidx and soft ring rsi; static far case premise separately recorded'}
(root/(name+'_control_inputs.json')).write_text(json.dumps(out)+'\n');(root/(name+'_joint_raw_sites.tsv')).write_text(tsv)
print('CONTROL_MODEL',name,'FF',len(scalar),'edges',len(edges),'static',len(static),'unknown',len(unknown));print(unknown[:8]);assert not unknown
