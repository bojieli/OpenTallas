import json,re,hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);modules=json.loads(p.read_text())['modules']
parent=next(v for k,v in modules.items() if 'REGISTER_PARENT=' in k)
def ff(m):return sum(c['type'].startswith('DFF') for c in m['cells'].values())
assert ff(modules['ot_attn_parent_row_bank'])==1618
assert ff(modules['ot_attn_parent_head_bank'])==1619
assert ff(parent)==2164
assert ff(modules['ot_attn_registered_parent_phys'])==1618
rows={k:c for k,c in parent['cells'].items() if c['type']=='ot_attn_parent_row_bank'}
heads={k:c for k,c in parent['cells'].items() if c['type']=='ot_attn_parent_head_bank'}
macros={k:c for k,c in parent['cells'].items() if c['type']=='ot_attn_hgrp_m6h1'}
assert (len(rows),len(heads),len(macros))==(4,16,16)
drivers={}
for name,c in parent['cells'].items():
 if c['type'].startswith(('INV','BUF')):
  ins=[b for port,d in c.get('port_directions',{}).items() if d=='input' for b in c['connections'][port]]
  outs=[b for port,d in c.get('port_directions',{}).items() if d=='output' for b in c['connections'][port]]
  assert len(ins)==len(outs)==1,(name,ins,outs)
  drivers[outs[0]]=ins[0]
def origin(bit):
 seen=set()
 while bit in drivers:
  assert bit not in seen
  seen.add(bit);bit=drivers[bit]
 return bit
clk=parent['ports']['clk']['bits'][0]
def root_vector(name):
 nets=parent['netnames']
 if name in nets and len(nets[name]['bits'])==1618:return nets[name]['bits']
 return [nets[name+'['+str(i)+']']['bits'][0] for i in range(1618)]
launch=root_vector('registered_parent.launch')
all_q=[b for c in heads.values() for b in c['connections']['q']]
assert len(set(all_q))==16*1618 and all(isinstance(b,int) for b in all_q)
assert len({b for c in rows.values() for b in c['connections']['q']})==4*1618
assert len({c['connections']['local_por_n'][0] for c in heads.values()})==16
widths=[('ib',576),('ibank',3),('iv',1),('ld_w2v',1),('ld_w',1024),('ld_grp',8),('ld_bank',3),('ld_mode',1),('ld_v',1)]
# Prove that kept helper outputs are actually FF Qs fed by the corresponding D.
def module_graph(module):
 edges={}
 ff_outputs={}
 for name,cell in module['cells'].items():
  if cell['type'].startswith(('INV','BUF')):
   ins=[b for port,d in cell.get('port_directions',{}).items() if d=='input' for b in cell['connections'][port]]
   outs=[b for port,d in cell.get('port_directions',{}).items() if d=='output' for b in cell['connections'][port]]
   if len(ins)==len(outs)==1:edges[outs[0]]=ins[0]
  if cell['type'].startswith('DFF'):
   ff_outputs[cell['connections']['QN'][0]]=(name,cell['connections'])
 def org(bit):
  seen=set()
  while bit in edges:
   assert bit not in seen;seen.add(bit);bit=edges[bit]
  return bit
 return org,ff_outputs
for name in ['ot_attn_parent_row_bank','ot_attn_parent_head_bank']:
 module=modules[name];org,qff=module_graph(module);seen=set()
 for i,q in enumerate(module['ports']['q']['bits']):
  node=org(q);assert node in qff and node not in seen
  seen.add(node)
  assert org(qff[node][1]['D'][0])==module['ports']['d']['bits'][i]
 assert len(seen)==1618
 if name.endswith('head_bank'):
  por=org(module['ports']['local_por_n']['bits'][0])
  assert por in qff and por not in seen
  tiehi={b for cell in module['cells'].values() if cell['type'].startswith('TIEHI') for bits in cell['connections'].values() for b in bits}
  assert qff[por][1]['D']==['1'] or qff[por][1]['D'][0] in tiehi
# Root launch and producer must carry every payload bit through real FFs.
org,qff=module_graph(parent)
payload_ports=[b for port,w in widths for b in parent['ports'][port]['bits']]
for i,q in enumerate(launch):
 node=org(q);assert node in qff
 assert org(qff[node][1]['D'][0])==payload_ports[i]
physical=modules['ot_attn_registered_parent_phys']
producer_nets=physical['netnames']
producer=(producer_nets['producer']['bits'] if 'producer' in producer_nets
          else [producer_nets['producer['+str(i)+']']['bits'][0] for i in range(1618)])
org,qff=module_graph(physical)
for bit in producer:
 node=org(bit);assert node in qff and isinstance(qff[node][1]['D'][0],int)
tile=next(c for c in physical['cells'].values() if 'REGISTER_PARENT=' in c['type'])
assert [org(b) for port,w in widths for b in tile['connections'][port]]==[org(b) for b in producer]
records=[];outputs_all=[]
for r in range(4):
 row=rows['registered_parent.row['+str(r)+'].u_row_launch']['connections']
 assert [origin(b) for b in row['d']]==[origin(b) for b in launch]
 assert row['clk']==[clk]
 for c in range(4):
  prefix='registered_parent.row['+str(r)+'].head['+str(c)+']'
  h=heads[prefix+'.u_macro_launch']['connections']
  a=macros[prefix+'.u_g']['connections']
  assert [origin(b) for b in h['d']]==[origin(b) for b in row['q']]
  assert h['clk']==a['clk']==[clk]
  assert origin(a['rst_n'][0])==origin(h['local_por_n'][0])
  off=0
  for port,w in widths:
   assert len(a[port])==w
   assert [origin(b) for b in a[port]]==[origin(b) for b in h['q'][off:off+w]],(prefix,port)
   off+=w
  assert off==1618
  constants={'0':'0','1':'1'}
  for cell in parent['cells'].values():
   if cell['type'].startswith(('TIEHI','TIELO')):
    value='1' if cell['type'].startswith('TIEHI') else '0'
    for bits in cell['connections'].values():
     for bit in bits:constants[bit]=value
  assert [constants[origin(bit)] for bit in a['gid']]==[str(((r*4+c)>>i)&1) for i in range(8)]
  expected=a['oy']+a['oflt']+a['ov']
  assert len(expected)==34 and all(isinstance(b,int) for b in expected)
  captures={}
  for k,v in parent['cells'].items():
   match=re.fullmatch(re.escape(prefix)+r'\.capture\[(\d+)\]\$_DFF_PN0_',k)
   if match:captures[int(match[1])]=v['connections']
  assert set(captures)==set(range(34)),prefix
  for i in range(34):
   assert origin(captures[i]['D'][0])==origin(expected[i]),(prefix,i)
   assert captures[i]['CLK']==[clk]
   assert origin(captures[i]['RESETN'][0])==origin(h['local_por_n'][0])
  outputs_all+=expected
  records.append(dict(head=r*4+c,macro_instance=prefix+'.u_g',row_FF=1618,local_FF=1619,
      captured_FF=34,payload_port_bits=1618,nonconstant_payload_bits=1618,
      per_bit_bank_order_verified=True,all34_macro_outputs_to_own_receiver_D=True,
      local_POR_to_macro_and_receiver_association=True,common_root_clock_port_verified=True))
assert len(set(outputs_all))==544
result=dict(verdict='PASS',source='e5624a88a',mapped_json_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    total_FF=36158,producer_FF=1618,parent_root_and_capture_FF=2164,row_instances=4,
    row_FF_per_instance=1618,local_instances=16,local_FF_per_instance=1619,
    macros=16,nonconstant_macro_payload_bits=25888,unique_macro_output_bits=544,
    receiver_FF=544,heads=records,clock_insertion_qualified=False,SS_FF_qualified=False,
    scope='actual mapped connectivity and retained per-block FFs, not timing or enclosing engine proof')
# Verify the actual mapped clock phase, not an RTL annotation.
def phase_check(module,negative):
 clock=module['ports']['clk']['bits'][0]
 edges={}
 for cell in module['cells'].values():
  if cell['type'].startswith(('INV','BUF')):
   ins=[b for port,d in cell.get('port_directions',{}).items() if d=='input' for b in cell['connections'][port]]
   outs=[b for port,d in cell.get('port_directions',{}).items() if d=='output' for b in cell['connections'][port]]
   if len(ins)==len(outs)==1:edges[outs[0]]=(ins[0],int(cell['type'].startswith('INV')))
 count=0
 for cell in module['cells'].values():
  if not cell['type'].startswith('DFF'):continue
  bit=cell['connections']['CLK'][0];parity=0;seen=set()
  while bit in edges:
   assert bit not in seen;seen.add(bit)
   bit,flip=edges[bit];parity^=flip
  assert bit==clock and parity==negative
  count+=1
 return count
assert phase_check(modules['ot_attn_parent_head_bank'],1)==1619
assert phase_check(modules['ot_attn_parent_row_bank'],0)==1618
assert phase_check(parent,0)==2164
assert phase_check(modules['ot_attn_registered_parent_phys'],0)==1618
result['actual_FF_Q_to_payload_D_reach_verified']=True
result['actual_producer_to_root_to_four_rows_to_sixteen_heads_verified']=True
result['literal_gid_per_head_verified']=True
result['mapped_clock_phase_verified']=dict(positive_FF=10254,negative_FF=25904,
    actual_SEQ_CLK_pin_graph=True,macro_ports_positive=True,own_capture_CLK_positive=True,
    insertion_from_CTS_still_pending=True)
out=Path(sys.argv[2]);out.write_text(json.dumps(result,indent=2)+'\n')
print('PASS actual mapped: 36158FF,4x1618row,16x1619local,16x34receiver,25888nonconstant ordered macro input bits,544own receiver D associations')
