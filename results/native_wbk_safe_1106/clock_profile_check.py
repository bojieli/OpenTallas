"""Fail-closed common-clock prerequisite for the optional native WBK adapter."""
import hashlib,json,re
from pathlib import Path

def clean(s):
 return re.sub(r'/\*.*?\*/|//[^\n]*',' ',s,flags=re.S)
def group(s,i):
 assert s[i]=='('
 d=1;j=i+1
 while d:
  if s[j]=='(':d+=1
  if s[j]==')':d-=1
  j+=1
 return s[i+1:j-1],j

def instances(text,module):
 text=clean(text);out=[]
 for m in re.finditer(r'\b'+re.escape(module)+r'\b',text):
  tail=text[m.end():];i=m.end()
  while text[i].isspace():i+=1
  if text[i]=='#':
   i+=1
   while text[i].isspace():i+=1
   _,i=group(text,i)
  n=re.match(r'\s*(\w+)\s*\(',text[i:])
  if not n:continue
  start=i+n.end()-1;body,_=group(text,start)
  ports={}
  for p in re.finditer(r'\.(\w+)\s*\(',body):
   expr,_=group(body,p.end()-1);ports[p[1]]=re.sub(r'\s+','',expr)
  out.append((n[1],ports))
 return out

def scalar(s):return re.sub(r'\[(\d+):\1\]',r'[\1]',s)
def check(top,kshare,primitive):
 rows=instances(top,'ot_hbm_svc_wb_kport_q');assert rows,'no actual RAW WBK instances'
 found=[]
 for name,p in rows:
  stream=scalar(p['stream_clk']);hbm=scalar(p['hbm_clk']);fifo=p['stream_fifo_clk']
  clocks=[scalar(x) for x in fifo[1:-1].split(',')] if fifo.startswith('{') and fifo.endswith('}') else []
  if fifo.startswith('{4{') and fifo.endswith('}}'):clocks=[scalar(fifo[3:-2])]*4
  if stream!=hbm or clocks!=[stream]*4:raise ValueError(name+': WBK clocks are not the exact common-clock profile')
  if scalar(p['stream_rst_n'])!=scalar(p['hbm_rst_n']):raise ValueError(name+': WBK reset identity differs')
  found.append(dict(instance=name,clock=stream,reset=scalar(p['hbm_rst_n']),fifo_clock_copies=4))
 # Inspect the actual native receiver path, not a promise of ready lead.
 receiver=clean(kshare);cell=clean(primitive)
 want=[p for n,p in instances(receiver,'ot_hbm_svc_pin_skid2') if n=='u_e']
 if len(want)!=1 or want[0].get('clk')!='hbm_clk' or want[0].get('in_r')!='w_k_rdy[l]':
  raise ValueError('actual Kshare WB input skid/clock/ready binding changed')
 if not re.search(r'assign\s+in_r\s*=\s*!tail_valid\s*;',cell):raise ValueError('READY is not solely posedge tail state')
 blocks=re.findall(r'always\s*@\s*\(([^)]*)\)',cell)
 if blocks!=['posedge clk or negedge rst_n']:raise ValueError('actual READY state has unsupported phase/source')
 return dict(status='COMMON_CLOCK_ONLY',instances=found,receiver='ot_hbm_svc_vm_kshare/lane.u_e',
             ready_state='ot_hbm_svc_pin_skid2.tail_valid',ready_update_edge='posedge',
             adapter_capture_edge='negedge',accept_edge='next posedge',
             reset_contract='no acceptance during reset; wait full native profile quarantine after release',
             physical_halfcycle_STA='NOT_RUN',generic_async_compatibility='NOT_CLAIMED')

if __name__=='__main__':
 import sys
 top,kshare,primitive=(Path(x).read_text() for x in sys.argv[1:4])
 r=check(top,kshare,primitive)
 start=re.search(r'\bot_hbm_svc_wb_kport_q\b',top).start();end=top.index(';',start)+1
 bad=top[:start]+re.sub(r'\.hbm_clk\s*\([^)]*\)', '.hbm_clk(wrong_clock)',top[start:end],count=1)+top[end:]
 try:check(bad,kshare,primitive)
 except ValueError:pass
 else:raise AssertionError('wrong-clock mutant did not change the actual fixture or escaped')
 try:check(top,kshare,primitive.replace('posedge clk','negedge clk',1))
 except ValueError:pass
 else:raise AssertionError('wrong receiver edge accepted')
 r['negative_controls']=['wrong actual WBK clock rejected','wrong receiver update edge rejected']
 print(json.dumps(r,indent=1))
