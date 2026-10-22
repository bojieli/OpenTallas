from pathlib import Path
import json,sys,re,hashlib
root=Path(sys.argv[1])
for n in ['qfd_dv_s5_ctl5-ctl5a-041b89783','qfd_dv_s5_btab_s4-btab-s4-3f0f4b600']:
 p=root/n;s=json.loads((p/'native/summary.json').read_text());rs=json.loads((p/'native/rows.json').read_text());roles=s['master_roles'];seq={m:v for m,v in roles.items()if 'ff'in v};masters={r['driver'].rsplit('/',1)[0]:r['master']for r in rs if r['master']!='PORT'};errors=[];inputs=[];outputs={};clocks=[];reset=[]
 def seqpin(ep):
  inst,pin=ep.rsplit('/',1);m=masters.get(inst);v=seq.get(m)
  if v is None:return None
  cps=[k for k,q in v['pins'].items()if q.get('clock')];ns=re.sub(r'[()!\s]','',v['ff']['next_state']or'');co=v['ff']['clocked_on']
  return {'instance':inst,'master':m,'pin':pin,'data_pin':ns,'clock_pin':inst+'/'+cps[0]if len(cps)==1 else None,'clocked_on':co,'next_state':v['ff']['next_state']}
 for r in rs:
  if r['master']=='PORT':
   if r['clock_terminals']and not r['terminals']:clocks.append(r['driver']);continue
   if r['driver']=='PORT/rst_n':reset.append({'port':r['driver'],'endpoints':r['endpoints']});continue
   a=[seqpin(ep)for ep in r['endpoints']];good=bool(a)and all(x and x['pin']==x['data_pin']and x['clock_pin']for x in a)
   inputs.append({'port':r['driver'],'first_captures':a,'PASS':good})
   if not good:errors.append('input capture '+r['driver'])
  for ep in r['endpoints']:
   if ep.startswith('PORT/'):
    if r['master']in seq:outputs.setdefault(ep,[]).append({'producer':r['driver'],'master':r['master'],'ff':seq[r['master']]['ff']})
 allout={ep for r in rs for ep in r['endpoints']if ep.startswith('PORT/')};missing=sorted(allout-set(outputs));errors+=['output no FF '+x for x in missing]
 for ep,v in outputs.items():
  if len(v)!=1:errors.append('ambiguous source FF '+ep)
 cps=set(x['clock_pin']for r in inputs for x in r['first_captures']if x and x['clock_pin'])
 for ep,vs in outputs.items():
  for v in vs:
   inst=v['producer'].rsplit('/',1)[0];m=v['master'];cp=[k for k,q in seq[m]['pins'].items()if q.get('clock')]
   if len(cp)==1:cps.add(inst+'/'+cp[0])
 d={'scope':'Postprocess existing actual-Lib native rows; no ODB mutation or native re-audit. First capture/last launch FF determined by actual ff()/next_state/clock:true, through actual-function BUF/INV transparency. Reset contacts reported separately; reset edge-age proof belongs source.','ODB_sha256':s['odb_sha256'],'input_bits':len(inputs),'output_bits':len(allout),'registered_output_bits':len(outputs),'unique_boundary_clocks':len(cps),'clock_ports':clocks,'reset_root_endpoints':reset,'errors':errors,'PASS':not errors,'per_input':inputs,'per_output':outputs,'boundary_clock_pins':sorted(cps)}
 (p/'port_audit.json').write_text(json.dumps(d,indent=2)+'\n');print(n,{k:d[k]for k in ['input_bits','output_bits','registered_output_bits','unique_boundary_clocks','errors','PASS']})
