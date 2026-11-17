from pathlib import Path
import re,json,hashlib,sys,collections
R=Path('/srv/opentallas-scratch2/claude/qc-types-r/aliasprep')
S=Path('/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/w1_44868/src')
sha=lambda b:hashlib.sha256(b).hexdigest()
ROLES={'exp':'ot_hdc_sfu_exp_t','head':'qfd_dv_lane_h_su_mem9','lrly':'qfd_dv_s5_lrly','rcp':'ot_hdc_sfu_rcp_t','rsq':'ot_hdc_sfu_rsq_t'}
FILES={'exp':'rtl/hdc/ot_hdc_vstream_sfu_t.sv','head':'rtl/physical/qfd_dv_lane_h_su_mem9.sv','lrly':'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv','rcp':'rtl/hdc/ot_hdc_vstream_sfu_t.sv','rsq':'rtl/hdc/ot_hdc_vstream_sfu_t.sv'}
def header(raw,mod):
 # Preserve the exact real parameter and ANSI-port header. Comments do not affect parentheses.
 s=re.sub(r'//[^\n]*|/\*.*?\*/','',raw,flags=re.S)
 m=re.search(r'\bmodule\s+'+re.escape(mod)+r'\b',s);assert m,mod
 depth=0
 for k in range(m.end(),len(s)):
  if s[k]=='(':depth+=1
  elif s[k]==')':depth-=1
  elif s[k]==';' and depth==0:return s[m.start():k+1]
 raise ValueError('unterminated header '+mod)
def prepare():
 refs=[];heads=[]
 for role,mod in ROLES.items():
  p=S/FILES[role];b=p.read_bytes();h=header(b.decode(),mod);heads.append('(* blackbox *) '+h+'\nendmodule\n')
  refs.append(dict(role=role,module=mod,path=str(p),source_sha256=sha(b),exact_header_sha256=sha(h.encode()),header=h))
 (R/'leaf_headers.v').write_text('\n'.join(heads));(R/'leaf_header_receipt.json').write_text(json.dumps(refs,indent=2)+'\n')
 wrappers=[];sources=[]
 for lane in range(1,8):
  p=S/f'rtl/physical/qfd_qc_su_lane_w_l{lane}_m44s1.sv';b=p.read_bytes();wrappers.append(b.decode());sources.append(dict(lane=lane,path=str(p),sha256=sha(b)))
 m=(R/'mutant_swap_inputs.sv').read_text().replace('qfd_qc_su_lane_w_l1_m44s1','qfd_qc_su_lane_w_l1_mutant_m44s1');wrappers.append(m)
 (R/'actual_wrappers.v').write_text('\n'.join(wrappers));(R/'source_wrapper_receipt.json').write_text(json.dumps(sources,indent=2)+'\n')
 (R/'frontend.ys').write_text('read_verilog -sv -lib /out/leaf_headers.v\nread_verilog -sv /out/actual_wrappers.v\nhierarchy -check\nproc\nwrite_json /out/actual_wrappers.json\n')
 print('PREPARED actual full wrappers+real leaf headers')
def role_from_inst(name):
 m=re.fullmatch(r'u_u_(exp|head|lrly|rcp|rsq)[1-7]',name);assert m,name;return m[1]
def read_module(j,name):
 m=j['modules'][name];assert len(m['cells'])==5,(name,m['cells'].keys())
 assert set(m['ports'])=={'clk','rst_n','c_i','c_o'},(name,m['ports'].keys())
 assert [(p,len(m['ports'][p]['bits'])) for p in ['clk','rst_n','c_i','c_o']]==[('clk',1),('rst_n',1),('c_i',760),('c_o',248)]
 cells={role_from_inst(n):c for n,c in m['cells'].items()};assert set(cells)==set(ROLES)
 config={};outs={};ins={}
 for role,c in cells.items():
  leaf=j['modules'][c['type']];assert leaf.get('attributes',{}).get('blackbox'),(name,role,c['type'])
  assert not leaf.get('cells'),(role,'leaf body elaborated')
  assert set(c['connections'])==set(leaf['ports']),(role,'missing leaf port')
  config[role]=dict(type=c['type'],parameters=c.get('parameters',{}),ports={p:dict(direction=x['direction'],width=len(x['bits'])) for p,x in leaf['ports'].items()})
  for port,conn in c['connections'].items():
   direction=leaf['ports'][port]['direction'];assert len(conn)==len(leaf['ports'][port]['bits']),(role,port)
   assert direction in ('input','output'),(role,port,direction)
   (outs if direction=='output' else ins)[(role,port)]=conn
 return m,config,outs,ins
def make_miter():
 j=json.loads((R/'actual_wrappers.json').read_text());names=[f'qfd_qc_su_lane_w_l{n}_m44s1' for n in range(1,8)]+['qfd_qc_su_lane_w_l1_mutant_m44s1']
 items={n:read_module(j,n) for n in names};base=items[names[0]];config=base[1]
 for name,item in items.items():assert item[1]==config,(name,'leaf params/widths/directions differ')
 outkeys=sorted(base[2]);inkeys=sorted(base[3]);outwidth=sum(len(base[2][k]) for k in outkeys)
 obswidth=248+sum(len(base[3][k]) for k in inkeys)
 designs=[];maps={}
 for number,name in enumerate(names):
  m,_,outs,ins=items[name];drivers={};evidence={}
  def driver(bit,symbol):
   assert isinstance(bit,int),(name,bit,'constant output/input source')
   assert bit not in drivers or drivers[bit]==symbol,(name,bit,'multiple distinct drivers',drivers.get(bit),symbol)
   drivers[bit]=symbol
  for port,offset in [('clk',760),('rst_n',761),('c_i',0)]:
   for i,bit in enumerate(m['ports'][port]['bits']):driver(bit,f'top_i[{offset+i}]')
  off=0
  for k in outkeys:
   for i,bit in enumerate(outs[k]):driver(bit,f'leaf_i[{off+i}]')
   evidence['.'.join(k)]=dict(symbol_offset=off,width=len(outs[k]));off+=len(outs[k])
  def expr(bit):
   if isinstance(bit,str):assert bit in ('0','1'),(name,'X/Z in wiring',bit);return "1'b"+bit
   assert bit in drivers,(name,'undriven observed bit',bit)
   return drivers[bit]
  obs=[expr(x) for k in inkeys for x in ins[k]]+[expr(x) for x in m['ports']['c_o']['bits']]
  assert len(obs)==obswidth
  mn=f'cut_{number}';designs.append(f'module {mn}(input wire [761:0] top_i,input wire [{outwidth-1}:0] leaf_i,output wire [{obswidth-1}:0] obs);\nassign obs={{'+','.join(reversed(obs))+'};\nendmodule\n')
  maps[name]=dict(outputs=evidence,observation_bits=obswidth,observation_order=[dict(role=k[0],port=k[1],width=len(ins[k])) for k in inkeys]+[dict(role='TOP',port='c_o',width=248)],driven_net_bits=len(drivers),obs_expression_sha256=sha('\n'.join(obs).encode()))
 for i in range(1,8):
  designs.append(f'module miter_{i}(input wire [761:0] top_i,input wire [{outwidth-1}:0] leaf_i,output wire ok);\nwire [{obswidth-1}:0] a,b;cut_0 A(top_i,leaf_i,a);cut_{i} B(top_i,leaf_i,b);assign ok=(a==b);endmodule\n')
 (R/'cutpoint_miters.v').write_text('\n'.join(designs))
 (R/'cutpoint_maps.json').write_text(json.dumps(dict(symbolic_leaf_output_bits=outwidth,observation_bits=obswidth,leaf_config=config,modules=maps),indent=2)+'\n')
 for i in range(1,8):
  # A fresh design per proof; mutant is i7.
  (R/f'sat_{i}.ys').write_text(f'read_verilog /out/cutpoint_miters.v\nhierarchy -check -top miter_{i}\nflatten\nopt_clean\nsat -verify -prove ok 1 -show-inputs -show-outputs\n')
 print(json.dumps(dict(symbolic_leaf_output_bits=outwidth,observation_bits=obswidth,miter_count=7)))
def summarize():
 results=[]
 for i in range(1,8):
  log=(R/f'sat_{i}.log').read_text();passed='SAT proof finished - no model found: SUCCESS!' in log
  failed='proof did fail' in log or 'model found: FAIL!' in log
  assert passed if i<7 else failed,(i,'unexpected SAT result')
  results.append(dict(actual_lane=i+1 if i<7 else 'W1 input-bit-swap mutant',expected='EQUIVALENT' if i<7 else 'NOT EQUIVALENT',proved_equal=passed,mutant_refused=failed,log=f'sat_{i}.log'))
 sources=json.loads((R/'source_wrapper_receipt.json').read_text());unchanged=all(sha(Path(x['path']).read_bytes())==x['sha256'] for x in sources);assert unchanged
 maps=json.loads((R/'cutpoint_maps.json').read_text())
 r=dict(verdict='PASS_WIRING_CONGRUENCE',strict_alpha_result='FAIL_NON_ALPHA preserved separately in alpha_receipt.json',scope='Full production wrappers parsed by Yosys frontend with exact real leaf-module parameter/port headers, then all five leaf outputs replaced by shared arbitrary symbolic bits; SAT compares every leaf input and all248 topoutputs for all762 topinput bits includingclk/reset',stateful_semantic_basis='For arbitrary identical initial leaf states, equal inputs and equal leaf module+parameters give equal next states and outputs; the SAT wiring congruence supplies the induction step. No datapath body reimplementation or arithmetic simulation.',parameters_and_literals_preserved=True,source_files_unchanged=unchanged,symbolic_leaf_output_bits=maps['symbolic_leaf_output_bits'],observation_bits=maps['observation_bits'],results=results,inputs=sources,leaf_headers='leaf_header_receipt.json',frontend_log='frontend.log',tool_helper_sha256=sha(Path(__file__).read_bytes()))
 (R/'wiring_congruence_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(verdict=r['verdict'],proofs=6,mutant_refused=True,observations=r['observation_bits'])))
if __name__=='__main__':globals()[sys.argv[1]]()
