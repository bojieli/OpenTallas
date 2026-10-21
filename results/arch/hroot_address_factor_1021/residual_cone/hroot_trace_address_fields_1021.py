from pathlib import Path
import json,re,hashlib,importlib.util,sys,collections
root=Path('/srv/opentallas-scratch/claude/codex-hroot-address-1021');sp=importlib.util.spec_from_file_location('T',root/'source/textbook_lint.py');T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
p=root/'hroot-address-map-r2-1021/original.v';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='4c4b1fa2eca4e65190a0203eea33fb2ff871928c9b5e26cbbef3e4952694fbb6';g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None);aliases=collections.defaultdict(list)
for name,n in g.net_id.items():
 if re.match(r'(st_d|st_row|s_ring|s_local|s_rbase|s_pitch|s_raddr|s_stk|s_gs|k_sb|k_q|k_blk|k_code|k_scal|st_sec|st_ph|st_wa|u_raddr|u_kcode|u_kscal|w_addr|af_)($|\[|\$)',name):aliases[g.find(n)].append(name)
r=json.load(open(root/'address_cone_estimate.json'));trace=r['successor_selected_wrapper']['worst_address_traces'][0];records=[]
for node in [dict(instance=trace['start'])]+trace['cone']:
 m=re.search(r'u_eng\.u(\d+)_c\d+\.u_cell',node['instance']);assert m,node;ci=int(m[1]);typ,name,pins=g.cells[ci]
 rec=dict(native=node['instance'],cell=ci,original=name,master=typ,pins={pn:[dict(net=g.net_name[n],aliases=aliases[n]) for n in ns] for pn,ns in pins.items()});records.append(rec)
# Start Q inverse-buffer aliases; pin exact expression provenance without assuming FF-state equality.
ci=records[0]['cell'];leaves=[]
for n in T._out_nets(g,A,ci):
 for c,pn,b in A['loads'].get(n,[]):
  if A['kind'][c]=='buf':
   leaves.append(dict(master=g.cells[c][0],instance=g.cells[c][1],outputs=[dict(net=g.net_name[x],aliases=aliases[x]) for x in T._out_nets(g,A,c)]))
out=dict(mapped_sha256=hashlib.sha256(raw).hexdigest(),parser_sha256=hashlib.sha256((root/'source/textbook_lint.py').read_bytes()).hexdigest(),path_from_completed_estimate=trace,start_inverse_buffer_aliases=leaves,path_cells=records,scope='read-only exact existing mapped primitive path-to-source alias trace; structural sensitization and STA closure not asserted');Path('address_equation_trace.json').write_text(json.dumps(out,indent=2)+'\n')
for q in records:
 outaliases=[v['aliases'] for pn,vals in q['pins'].items() if A['pin_dir'][q['cell']][pn]=='out' for v in vals];print(q['cell'],q['master'],outaliases)
print('ROOT_INVERSE_ALIASES',leaves)

cache={}
def leaves_from(start):
 stack=list(start);seen=set();ff=set();ports=set();mac=set()
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n);dr=A['driver'].get(n)
  if dr is None:continue
  c,pn=dr
  if c<0:ports.add(pn);continue
  kind=A['kind'][c]
  if kind=='ff':ff.add(c);continue
  if kind=='macro':mac.add((c,pn));continue
  for ip,ns in g.cells[c][2].items():
   if A['pin_dir'][c][ip]=='in':stack.extend(ns)
 return ff,ports,mac
def dcone(c):
 if c not in cache:cache[c]=leaves_from(g.cells[c][2].get('D',[]))
 return cache[c]
def label(c):
 ff,pp,_=dcone(c);ports=set(pp)
 for u in ff:ports.update(dcone(u)[1])
 payload=sorted(x for x in ports if x.startswith('d_data[') and int(x[7:-1])>7)
 return dict(cell=c,master=g.cells[c][0],capture_payload=payload,unique_payload_bit=payload[0] if len(payload)==1 else None)
origins={};growth=[]
for q in records[:34]:
 outs=list(T._out_nets(g,A,q['cell']));ff,pp,mac=leaves_from(outs);ll=[]
 for c in sorted(ff):
  if c not in origins:origins[c]=label(c)
  ll.append(origins[c])
 growth.append(dict(cell=q['cell'],master=q['master'],upstream_FFs=ll,primary=sorted(pp),macro_leaves=sorted(mac)))
Path('address_equation_leaf_provenance.json').write_text(json.dumps(dict(mapped_sha256=out['mapped_sha256'],path_growth=growth,root=origins.get(records[0]['cell']),scope='static FF D-capture ancestry; unique descriptor payload bit identifies field ancestry, not universal state reachability or transaction sensitization'),indent=2)+'\n')
for q in growth[:10]:print('GROWTH',q['cell'],len(q['upstream_FFs']),[x['unique_payload_bit'] for x in q['upstream_FFs']])
