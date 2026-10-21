from pathlib import Path
import importlib.util,sys,json,hashlib,collections
root=Path(__file__).resolve().parent
for n,h in json.load(open(root/'readset_sha256.json')).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
P=root/'textbook_lint.py';sp=importlib.util.spec_from_file_location('T',P);T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
g,_=T.flatten(T.parse_verilog((root/'apipe1.v').read_text()),None);A=T.build(g,None);names={name:c for c,(_,name,_) in enumerate(g.cells)}
def leaves(ns):
 todo=list(ns);seen=set();ff=set();ports=set();macro=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n);d=A['driver'].get(n)
  if d is None:continue
  c,pn=d
  if c<0:ports.add(pn);continue
  if A['kind'][c]=='ff':ff.add(c);continue
  if A['kind'][c]=='macro':macro.add((g.cells[c][1],pn));continue
  todo.extend(T._in_nets(g,A,c,False))
 return ff,ports,macro
cache={}
def dcone(c):
 if c not in cache:cache[c]=leaves(g.cells[c][2].get('D',[]))
 return cache[c]
def label(c):
 ff,ports,mac=dcone(c);pp=set(ports)
 for u in ff:pp.update(dcone(u)[1])
 return dict(instance=g.cells[c][1],master=g.cells[c][0],D_FF_leaves=[g.cells[x][1] for x in sorted(ff)],D_primary=sorted(ports),D_macro=sorted(mac),capture_payload=sorted(x for x in pp if x.startswith('d_data[') or x.startswith('in_data[')),self_feedback=c in ff)
r=json.load(open(root/'apipe1_map_estimate.json'));cur=r['apipe1_registered_model'];trace=cur['worst_address_traces'][0];growth=[];labels={}
for node in [dict(instance=trace['start'])]+trace['cone']:
 c=names[node['instance']];ff,ports,mac=leaves(T._out_nets(g,A,c))
 for u in ff:
  if g.cells[u][1] not in labels:labels[g.cells[u][1]]=label(u)
 growth.append(dict(instance=g.cells[c][1],master=g.cells[c][0],FFs=[g.cells[u][1] for u in sorted(ff)],primary=sorted(ports),macro=sorted(mac),pins={pn:[g.net_name[n] for n in ns] for pn,ns in g.cells[c][2].items()}))
rr=cur['reg_to_reg_worst'];start=names[rr['start']];end=names[rr['end'].rsplit('/',1)[0]]
for u in dcone(end)[0]:
 if g.cells[u][1] not in labels:labels[g.cells[u][1]]=label(u)
json.dump(dict(scope='read-only exact existing APIPE1 map primitive/cone/descriptor capture ancestry, not sensitization or new proof/map',input_sha256=json.load(open(root/'readset_sha256.json')),output_trace=trace,path_growth=growth,FF_labels=labels,output_start=label(names[trace['start']]),internal_start=label(start),internal_end=label(end),internal_master_classification=cur['reg_to_reg_endpoint_classification']),open(root/'source_trace.json','w'),indent=2)
print('OUTPUT_START',json.dumps(label(names[trace['start']])));print('INTERNAL_START',json.dumps(label(start)));print('INTERNAL_END',json.dumps(label(end)))
