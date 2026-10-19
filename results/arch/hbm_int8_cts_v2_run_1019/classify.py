import json,csv,re,collections
from pathlib import Path
p=Path(__file__).parent/'output'; raw=json.loads((p/'native/raw.json').read_text());mod=next(iter(raw['modules'].values())); cells=mod['cells']; pre=json.loads((p/'pre_native/raw.json').read_text());old=next(iter(pre['modules'].values()))['cells']; new=set(cells)-set(old)
clockpins={r['pin'] for r in csv.DictReader((p/'clock_pins_TT.tsv').open(),delimiter='\t')};cn=set()
for cp in clockpins:
 n,pn=cp.rsplit('/',1);cn.update(cells[n]['connections'][pn])
# Only actual NEW CTS cells upstream of actual native FF clock pins, never name filtered.
changed=True
while changed:
 changed=False
 for n in new:
  c=cells[n];outs=[b for q,bs in c['connections'].items() if c['port_directions'][q]=='output' for b in bs]
  if set(outs)&cn:
   before=len(cn);cn.update(b for q,bs in c['connections'].items() if c['port_directions'][q]=='input' for b in bs);changed|=len(cn)!=before
bn={b for q in mod['ports'].values() if q['signal_type']=='SIGNAL' for b in q['bits']};rn=set()
for c in cells.values():
 if c['type']=='DFFASRHQNx1_ASAP7_75t_R':
  for q in ('RESETN','SETN'):rn.update(c['connections'][q])
rows=[]
for corner,log in [('TT','cts.log'),('FF','ff.log')]:
 kind=None
 for line in (p/log).read_text().splitlines():
  if line.strip() in ('max slew','max capacitance','max fanout'):kind=line.strip();continue
  if not kind:continue
  m=re.match(r'^(.+?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+\(VIOLATED\)',line)
  if not m:continue
  pin=m[1].strip();master='TOP_PORT';net=set();owner=''
  if '/' in pin:
   owner,pn=pin.rsplit('/',1);c=cells[owner];master=c['type'];net=set(c['connections'][pn])
  else:net=set(mod['ports'][pin]['bits'])
  classes=[]
  if net&cn:classes.append('clock')
  if net&rn:classes.append('native_async_reset_set')
  if net&bn:classes.append('boundary')
  if not classes:classes=['internal']
  rows.append(dict(corner=corner,check=kind,pin=pin,master=master,classes=classes,limit=float(m[2]),actual=float(m[3]),slack=float(m[4]),net_ids=sorted(net)))
(p/'electrical_all_rows.json').write_text(json.dumps(rows,indent=2)+'\n')
groups=collections.defaultdict(list)
for r in rows:groups[(r['corner'],r['check'],'+'.join(r['classes']))].append(r)
summary=[]
for k,rs in sorted(groups.items()):
 w=min(rs,key=lambda r:r['slack']);summary.append(dict(corner=k[0],check=k[1],role=k[2],count=len(rs),worst=w,masters=dict(collections.Counter(r['master'] for r in rs))))
opennew=[]
for n in sorted(new):
 c=cells[n];out=[(q,b) for q,b in c['connections'].items() if c['port_directions'][q]=='output'];ins=[b for q,bs in c['connections'].items() if c['port_directions'][q]=='input' for b in bs]
 if out and all(not bs for q,bs in out):opennew.append(dict(instance=n,master=c['type'],all_input_nets_on_proven_clock_graph=bool(ins) and set(ins)<=cn,input_nets=ins))
result=dict(electrical=summary,all_row_count=len(rows),new_cell_count=len(new),open_new_outputs=opennew,new_masters=dict(collections.Counter(cells[n]['type'] for n in new)),clock_nets_backward_native_sink_graph=len(cn))
(p/'electrical_summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'groups':summary,'new_masters':result['new_masters'],'open_outputs':len(opennew),'open_outputs_all_inputs_clock_proven':all(r['all_input_nets_on_proven_clock_graph'] for r in opennew)},indent=2))

(p/"new_clock_graph.json").write_text(json.dumps({"root_source":"clk", "native_sink_clock_pins":sorted(clockpins), "proven_clock_net_ids":sorted(cn), "cells":[dict(instance=n,master=cells[n]["type"],connections=cells[n]["connections"],port_directions=cells[n]["port_directions"],all_inputs_on_proven_clock_graph=all(b in cn for q,bs in cells[n]["connections"].items() if cells[n]["port_directions"][q]=="input" for b in bs),all_connected_outputs_on_proven_clock_graph=all(b in cn for q,bs in cells[n]["connections"].items() if cells[n]["port_directions"][q]=="output" for b in bs)) for n in sorted(new)]},indent=2)+"\n")
