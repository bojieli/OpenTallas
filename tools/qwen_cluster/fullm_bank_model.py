"""Extract all-bit hard/soft endpoint constraints for ordinary-cycle bank paths."""
import collections,json,re,pathlib
import qc_fullm_kit as G
for v in G.K_VARIANTS:
 txt,X,R=G.fabric_rtl(v);G.BODY[v]=txt;env,P=G.placement(v,X,R);ranges,faces,_=G.pins(v,env);rows,un,pairs=G.reach(v,txt,env,P,ranges,faces);G.improve(env,P,pairs);rows,un,pairs=G.reach(v,txt,env,P,ranges,faces)
 drv,sinks,resolve,widths=G.netlist(txt);halves={};unknown=[]
 for m in re.finditer(r'qfd_c_land_([wr])1k #\([^;]*?\)\s+(u_\w+)\s+\(([^;]*?)\);',txt):
  side,name,ps=m[1],m[2],dict(G.PORT_RE.findall(m[3]));name='u_fab.'+name
  halves[name]={'side':side,'ports':ps,'anchor_points':[],'size_um':G.BAY[side]}
 rnet={z['ports']['o']:n for n,z in halves.items() if z['side']=='r'};soft_edges=set()
 def bits(e):
  out=[]
  for n,k in G.split_expr(e):out+= [(n,j) for j in range(widths.get(n,1))] if k is None else [(n,k)]
  return out
 for n,z in halves.items():
  if z['side']=='w':
   for bit in bits(z['ports']['i']):
    d,base=resolve(bit)
    if d:z['anchor_points'].append(G.pin_at(P,*d))
    elif base[0] in ranges:z['anchor_points'].append(G.port_xy(env,ranges,faces,base[0],base[1],widths.get(base[0],1)))
    elif base[0] in rnet:soft_edges.add((rnet[base[0]],n))
    else:unknown.append({'half':n,'bit':bit,'base':base})
  else:
   for dst,bit in sinks:
    if resolve(bit)[1][0]==z['ports']['o']:z['anchor_points'].append(G.pin_at(P,*dst))
 for n,z in halves.items():
  pts=z.pop('anchor_points');z['point_count']=len(pts);z['projection_min_nm']={str((sx,sy)):round(min((sx*x+sy*y for x,y in pts),default=0)*1000) for sx in [-1,1] for sy in [-1,1]} if pts else None
  del z['ports']
 hard={n:dict(p,width=G.LEFS[p['kind']][0],height=G.LEFS[p['kind']][1]) for n,p in P.items()}
 def pt(a):
  if a[0]=='PORT':return {'fixed':a[1]}
  x,y=G.pin_at(P,*a);return {'node':a[0],'offset':[x-P[a[0]]['x'],y-P[a[0]]['y']]}
 hops=[];seen=set()
 for a,b in pairs:
  key=(a[0],None if a[0]=='PORT' else a[1],b[0],None if b[0]=='PORT' else b[1])
  # all endpoints kept; solver may compress signed offsets independently after grouping
  hops.append([pt(a),pt(b)])
 out=G.ROOT/G.PLAN;out.mkdir(parents=True,exist_ok=True)
 data={'variant':v,'outline':[env['W'],env['H']],'hard':hard,'halves':halves,'bank_edges':[[n,n[:-1]+'r'] for n,z in halves.items() if z['side']=='w'],'soft_edges':sorted(soft_edges),'hard_hops':hops,'unknown_writer_bits':unknown,'hard_reach_max':max(x['worst_um'] for x in rows if x['cls']=='single-cycle')}
 (out/(G.KITS[v]+'_bank_inputs.json')).write_text(json.dumps(data)+'\n')
 print(G.KITS[v],'hard',len(hard),'halves',len(halves),'bank',len(data['bank_edges']),'soft',len(soft_edges),'unknown',len(unknown),'max hard',data['hard_reach_max'])
