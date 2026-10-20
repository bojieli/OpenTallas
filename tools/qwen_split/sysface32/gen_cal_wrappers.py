#!/usr/bin/env python3
"""Source-pinned fixed-shape wrappers and exact native input-load contracts."""
import argparse,hashlib,json
from pathlib import Path

def generate(weights_root,source,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);full=[];stubs=[];contracts={}
 for ne in (16,32,64):
  g=ne//16;aw=ne.bit_length()-1;nb=(ne+31)//32
  ins=[('ck',1),('rst_n',3+2*g),('cfg_we',1),('cfg_addr',aw+1),('cfg_data_k',nb*32),('cfg_seg_k',(3*g+1)*aw),('start_k',6+2*g),('halt_k',6+2*g),('seg_k',4+g)]
  outs=[('ev_v',1),('ev_port',3),('ev_kind',4),('ev_beat',5),('running',1),('fault',1)]
  def decl(dr,n,w):return f'  {dr} wire '+(f'[{w-1}:0] ' if w>1 else '')+n
  ports=[decl('input',n,w) for n,w in ins]+[decl('output',n,w) for n,w in outs]
  name=f'qfd_syscal{ne}_n32';header=f'(* keep_hierarchy="yes" *) module {name}(\n'+',\n'.join(ports)+'\n);\n'
  body=f'ot_qwen_d2d_cal_sysface32 #(.NE({ne})) u_cal('+','.join(f'.{n}({n})' for n,w in ins+outs)+');\nendmodule\n'
  full.append(header+body);stubs.append('(* blackbox *) '+header+'endmodule\n')
  wp=Path(weights_root)/f'native{ne}'/'input_weights.json';weights=json.loads(wp.read_text())
  if weights['source_sha256']!=hashlib.sha256(Path(source).read_bytes()).hexdigest():raise ValueError('Actual native weights source changed')
  if weights['parameter_NE']!=ne:raise ValueError('Native parameter identity changed')
  contract=dict(kind='soft_child',ports={n:dict(direction=dr,width=w,clock=(n=='ck')) for dr,pins in [('input',ins),('output',outs)] for n,w in pins},input_loads={},load_source_sha256=hashlib.sha256(wp.read_bytes()).hexdigest(),implementation_source_sha256=weights['source_sha256'],native_odb_sha256=weights['native_odb_sha256'],wrapper_sha256=hashlib.sha256((header+body).encode()).hexdigest())
  for n,w in ins:
   if n=='ck':continue
   contract['input_loads'][n]=[weights['input_data_terminal_weights'][n if w==1 else f'{n}[{i}]'] for i in range(w)]
  contracts[name]=contract
 (out/'qfd_syscal_n32.sv').write_text('\n'.join(full))
 (out/'qfd_syscal_n32_bb.sv').write_text('\n'.join(stubs))
 (out/'calendar_contracts.json').write_text(json.dumps(contracts,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--weights',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();generate(a.weights,a.source,a.out)
