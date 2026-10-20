import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools/qwen_dv');import ctlm6_snapshot as B
O=Path('/work/proof6');O.mkdir(exist_ok=True);raw=Path('/work/generic3/parent.json').read_bytes();contracts=json.load(open('/work/generic5/contracts.json'))
cells,ports=B.build(raw,'qfd_tt_ctlm_dv_lpf_lp','cut',load_cap=32,transparent_inverters=True,retain_mux=True,shared_helpers=True,retain_all_comb=True,fuse_ao=True,macro_contracts=contracts)
unknown=[]
for name,c in cells.items():
 for pin,bs in c['connections'].items():
  for i,b in enumerate(bs):
   if b in ('x','z'):
    assert c['type']=='$_MUX_' and pin in ('A','B') and len(bs)==1,(name,c)
    other='B' if pin=='A' else 'A';assert all(isinstance(v,int) or v in ('0','1') for v in c['connections'][other]),c
    unknown.append(dict(cell=name,pin=pin,known_pin=other,select=c['connections']['S'][0],known=c['connections'][other][0],source=c.get('attributes',{}).get('src')))
assert len(unknown)==10,len(unknown)
xids={(r['cell'],r['pin']):i for i,r in enumerate(unknown)}
inputs=list(dict.fromkeys(b for p in ports.values() if p['direction']=='input' for b in p['bits'] if isinstance(b,int)))
states=list(dict.fromkeys(b for c in cells.values() if c['type'] in B.FFS for b in c['connections']['Q'] if isinstance(b,int)))
macros=list(dict.fromkeys(b for c in cells.values() if c['type'] in contracts for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)))
mon=[]
def bit(b):return 'n_'+str(b) if isinstance(b,int) else "1'b"+b
for n,c in cells.items():
 if c['type'] in B.FFS:
  x=c['connections'];data=bit(x['D'][0]);typ=c['type']
  if typ!='$_DFF_P_':
   pol,value=typ[-3:-1];active=('!' if pol=='N' else '')+bit(x['R'][0]);data='('+active+" ? 1'b"+value+' : '+data+')';mon.append(bit(x['R'][0]))
  mon.append(data);mon.append(bit(x['C'][0]))
 elif c['type'] in contracts:
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='input':mon.extend(bit(b) for b in bs)
for p in ports.values():
 if p['direction']=='output':mon.extend(bit(b) for b in p['bits'])
allbits={b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int)}|set(inputs)
L=['module cut #(parameter MUT=0)(input wire ['+str(len(inputs)-1)+':0] inp,input wire ['+str(len(states)-1)+':0] states,input wire ['+str(len(macros)-1)+':0] macro_data,input wire [9:0] ux,output wire ['+str(len(mon)-1)+':0] observe);']
for chunk in range(0,len(allbits),64):L.append('wire '+','.join('n_'+str(b) for b in sorted(allbits)[chunk:chunk+64])+';')
for bus,vals in [('inp',inputs),('states',states),('macro_data',macros)]:
 for i,b in enumerate(vals):L.append('assign '+bit(b)+'='+bus+'['+str(i)+'];')
for name,c in cells.items():
 typ=c['type']
 if typ not in B.GATES:continue
 expr=B.GATES[typ]
 for p in ('A','B','S','X'):
  if p not in c['connections']:continue
  val='ux['+str(xids[(name,p)])+']' if (name,p) in xids else bit(c['connections'][p][0])
  # Causal negative: invert the defined context-mask arm at source target8.
  if name==unknown[8]['cell'] and p==unknown[8]['known_pin']:val='(MUT ? ~('+val+') : '+val+')'
  expr=expr.replace(p,'('+val+')')
 L.append('assign '+bit(c['connections']['Y'][0])+'='+expr+';')
for i,expr in enumerate(mon):L.append('assign observe['+str(i)+']='+expr+';')
L.append('endmodule')
L+=['module proof #(parameter MUT=0)(input wire ['+str(len(inputs)-1)+':0] inp,input wire ['+str(len(states)-1)+':0] states,input wire ['+str(len(macros)-1)+':0] macro_data,input wire [9:0] ux,input wire [3:0] target,output wire mismatch);',
 'wire ['+str(len(mon)-1)+':0] a,b; wire[9:0] ux0=ux&~(10\'b1<<target),ux1=ux|(10\'b1<<target);',
 'cut u_a(.inp(inp),.states(states),.macro_data(macro_data),.ux(ux0),.observe(a));',
 'cut #(.MUT(MUT)) u_b(.inp(inp),.states(states),.macro_data(macro_data),.ux(ux1),.observe(b));',
 'assign mismatch=|(a^b); endmodule']
(O/'cut.sv').write_text('\n'.join(L)+'\n');(O/'source_receipt.json').write_text(json.dumps(dict(normalized_graph_sha256=hashlib.sha256(json.dumps(dict(cells=cells,ports=ports),sort_keys=True,separators=(',',':')).encode()).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),unknown=unknown,states=len(states),macro_output_bits=len(macros),input_bits=len(inputs),observed_bits=len(mon),proof='All register effective next-state/reset/clock inputs, physical-macro input terminals and top outputs; equal symbolic current states/macro outputs; no state assumptions, no time exceptions.'),indent=2)+'\n')
print('OBSERVABILITY_CUT',len(cells),len(unknown),len(states),len(mon),flush=True)
