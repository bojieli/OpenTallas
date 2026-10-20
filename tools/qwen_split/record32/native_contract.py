"""Actual native input terminal weights and transparent output driver provenance."""
import json,pathlib,sys,re,hashlib
sys.path.insert(0,'tools/ref_tile');import native_census as N
r=json.load(open('record32_receipt.json'));c=json.load(open('native/census.json'));mods=N.TL.parse_verilog(pathlib.Path('native/mapped.v').read_text());roles,libs=N.liberty_roles(['native/'+n+'.lib' for n in ['AO','INVBUF','OA','SIMPLE','SEQ']]);mods={k:v for k,v in mods.items() if k==c['top'] or k not in roles};g,top=N.TL.flatten(mods,c['top'])
weights={v['driver']:v['loads'] for v in c['driver_counts'] if v['driver_role']=='input_port'}
ports=r['graph']['ports'];loads={};desc={}
for pn,p in ports.items():
 desc[pn]={'direction':p['direction'],'width':len(p['bits']),'clock':pn=='ck'}
 if p['direction']=='input':loads[pn]=[weights.get(f'{pn}[{i}]',weights.get(pn,0) if len(p['bits'])==1 else 0) for i in range(len(p['bits']))]
# Actual native direct output driver, then traverse only typed unary Liberty functions.
drivers={};trans={}
for master,name,pins in g.cells:
 role=roles[master];ins=[];outs=[]
 for pn,ns in pins.items():
  pin=role['pins'].get(pn) or role['pins'].get(N.TL._base(pn));assert pin,(master,pn)
  for net in ns:
   if pin['direction']=='input':ins.append((pn,net))
   else:
    outs.append((pn,net,pin.get('function')));drivers[net]={'instance':name,'master':master,'pin':pn,'sequential':role['sequential'],'function':pin.get('function')}
 if not role['sequential'] and len(ins)==len(outs)==1:
  ip,net=ins[0];op,out,f=outs[0];f=re.sub(r'[\s()]','',f or '')
  if f in (ip,'!'+ip,'~'+ip,ip+"'"):trans[out]=net
outputs={}
for pn,(direction,net) in g.ports.items():
 if direction!='output':continue
 path=[];seen=set();x=net
 while x in trans:
  assert x not in seen;seen.add(x);path.append(drivers[x]);x=trans[x]
 outputs[pn]={'direct_net':g.net_name[net],'producer_net':g.net_name[x],'producer':drivers.get(x,{'literal_or_input':g.net_name[x]}),'transparent_path':path}
source=pathlib.Path('rtl/qwen_split/qfd_sys_face_record_port_n32.sv').read_bytes();sha=hashlib.sha256(source).hexdigest()
contract={top:{'kind':'soft_child','ports':desc,'input_loads':loads,'load_source_sha256':sha}}
pathlib.Path('native/macro_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
flat={f'{pn}[{i}]' if len(v)>1 else pn:x for pn,v in loads.items() for i,x in enumerate(v)}
pathlib.Path('native/input_weights.json').write_text(json.dumps({'schema':'opentallas.record32.input_weights.v1','module':top,'input_data_terminal_weights':flat,'source_sha256':sha,'mapped_netlist_sha256':c['netlist']['sha256'],'liberty':c['liberty']},indent=2)+'\n')
pathlib.Path('native/output_producers.json').write_text(json.dumps({'module':top,'outputs':outputs,'source_sha256':sha,'mapped_netlist_sha256':c['netlist']['sha256']},indent=2)+'\n')
print('NATIVE_CONTRACT_PASS',len(flat),'inputbits',len(outputs),'outputbits')
