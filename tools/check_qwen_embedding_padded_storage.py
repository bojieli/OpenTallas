#!/usr/bin/env python3
"""Check actual independent capture FFs and all ten physical input-pad stages."""
import argparse,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from check_qwen_embedding_ingress_storage import check as check_storage
from check_embedding_metadata_cells import storage
CELL='BUFx2_ASAP7_75t_R'
TOP='ot_qwen_embedding_ingress_padded'

def check(m,width):
 counts=check_storage(m,width);cells=m['cells'];pads={}
 for name,c in cells.items():
  if 'g_pad' not in name:continue
  match=re.search(r'g_pad\[(\d+)\]\.g_stage\[(\d+)\]\.u_pad$',name)
  assert match and c['type']==CELL,('unexpected pad',name,c['type'])
  pair=tuple(map(int,match.groups()));assert pair not in pads
  pads[pair]=c
 assert set(pads)=={(b,s) for b in range(width+3) for s in range(10)},'missing or extra fixed pad stage'
 incoming=m['ports']['address']['bits']+m['ports']['valid']['bits']+m['ports']['credit']['bits']+m['ports']['rst_n']['bits']
 identities={}
 for c in cells.values():
  kind=c['type'].lstrip('\\');co=c['connections']
  if kind=='$_BUF_' or re.fullmatch(r'BUFx(?:[0-9]+(?:p[0-9]+)?|p[0-9]+|[0-9]+f)_ASAP7_75t_R',kind):
   if len(co.get('A',[]))==len(co.get('Y',[]))==1:identities.setdefault(co['Y'][0],[]).append(co['A'][0])
 def connected(bit,wanted,seen=None):
  if bit==wanted:return True
  seen=set() if seen is None else seen
  if bit in seen:return False
  ds=identities.get(bit,[])
  return len(ds)==1 and connected(ds[0],wanted,seen|{bit})
 finals=[]
 for b,root in enumerate(incoming):
  for s in range(10):
   c=pads[b,s]['connections'];assert len(c['A'])==1 and connected(c['A'][0],root),('bypassed/reordered pad',b,s)
   assert len(c['Y'])==1 and c['Y'][0]!=root,('shorted pad',b,s)
   root=c['Y'][0]
  finals.append(root)
 assert len(set(finals))==len(finals),'merged input pad rails'
 drivers={}
 for n,c in cells.items():
  kind=c['type'].lstrip('\\');co=c['connections']
  if kind in ('$_NOT_','$_BUF_') or re.fullmatch(r'(?:INV|BUF)x(?:[0-9]+(?:p[0-9]+)?|p[0-9]+|[0-9]+f)_ASAP7_75t_R',kind):
   if len(co.get('Y',[]))==len(co.get('A',[]))==1:drivers.setdefault(co['Y'][0],[]).append(co['A'][0])
  if kind=='TIEHIx1_ASAP7_75t_R' and len(co.get('H',[]))==1:
   drivers.setdefault(co['H'][0],[]).append('1')
 def origin(bit,seen=None):
  if bit in ('0','1') or bit in finals:return bit
  seen=set() if seen is None else seen
  assert bit not in seen, 'cyclic pad cone'
  ds=drivers.get(bit,[]);assert len(ds)==1,('capture bypasses pad',bit,ds)
  return origin(ds[0],seen|{bit})
 # Inspect each named output bit independently; FF D must originate in its own
 # pad. This rejects intact-but-disconnected pad chains and cross-bit swaps.
 for name,w,offset in [('address_q',width,0),('address_n',width,0),('valid_q',1,width),('valid_n',1,width),('credit_q',1,width+1),('credit_n',1,width+1)]:
  bits=m['ports'][name]['bits']
  assert len(bits)==w
  for i,bit in enumerate(bits):
   local=dict(m);local['netnames']=dict(m['netnames']);local['netnames']['probe']={'bits':[bit]}
   ff=cells[next(iter(storage(local,'probe')))];co=ff['connections']
   assert len(co.get('D',[]))==1 and origin(co['D'][0])==finals[offset+i],('wrong capture source',name,i)
   if w==1:
    reset=[origin(x) for p in ('RESETN','SETN') for x in co.get(p,[])]
    assert len(reset)==2 and reset.count(finals[-1])==1 and reset.count('1')==1,('reset pad bypass or invalid tie',name)
 return dict(verdict='PASS',counts=counts,width=width,input_padding=dict(stages_per_input=10,input_bits=width+3,fixed_buffer_cells=len(pads),cell_type=CELL,connectivity_verified=True))

def main():
 p=argparse.ArgumentParser();p.add_argument('--top',choices=(TOP,'ot_qwen_embedding_ingress_numeric'),default=TOP);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--width',type=int,choices=(12,18),required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys';y=str(y) if y.exists() else shutil.which('yosys')
 with tempfile.TemporaryDirectory(prefix='embedding-pad-check-') as d:
  q=Path(d)/'mapped.json';subprocess.run([y,'-Q','-T','-p',f'read_verilog "{a.netlist.resolve()}"; write_json "{q}"'],check=True,stdout=subprocess.DEVNULL)
  result=check(json.loads(q.read_text())['modules'][a.top],a.width)
 result['netlist_sha256']=hashlib.sha256(a.netlist.read_bytes()).hexdigest();a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('PASS independent capture FFs and every physical input-pad chain')
if __name__=='__main__':main()
