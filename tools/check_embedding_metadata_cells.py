#!/usr/bin/env python3
"""Require separate physical FF storage for complementary embedding metadata.
Accepts the actual mapped netlist (not the RTL), parsed without optimization.
A kept wire or output inverter alone does not satisfy the check.
"""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--netlist',required=True);p.add_argument('--top',required=True);p.add_argument('--out',required=True);a=p.parse_args()
y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
y=str(y) if y.exists() else shutil.which('yosys')
with tempfile.TemporaryDirectory(prefix='embedding-retention-') as d:
 q=Path(d)/'mapped.json'
 subprocess.run([y,'-Q','-T','-p',f'read_verilog "{Path(a.netlist).resolve()}"; write_json "{q}"'],check=True,stdout=subprocess.DEVNULL)
 m=json.loads(q.read_text())['modules'][a.top]
 pairs=[('fault','fault_n'),('wp','wp_n'),('rp','rp_n'),('credits','credits_n'),('phase','phase_n'),('valid_pipe','valid_n'),('addr_q','addr_n'),('ce_q','ce_n'),('iv_q','iv_n'),('cr_q','cr_n')]
 pairs+=[('row_q','row_n')] if 'scale' in a.top else [('ia_q','ia_n')]
 # Require direct FF outputs, never a kept wire driven only by an inverter.
 def storage(name):
  bits=m['netnames'][name]['bits'];found=set()
  for bit in bits:
   drivers=[]
   for cellname,c in m['cells'].items():
    if re.search('DFF|dff',c['type']) and any(bit in c['connections'].get(port,[]) for port in ['Q','QN']):drivers.append(cellname)
   if len(drivers)!=1:raise AssertionError(f'{name} bit {bit}: expected direct FF output, got {drivers}')
   found.update(drivers)
  if len(found)!=len(bits):raise AssertionError(f'{name}: aliased FF storage')
  return found
 checks={}
 for left,right in pairs:
  l,r=storage(left),storage(right)
  assert not l&r,(left,right,'shared FFs')
  checks[left+'/'+right]={'primary_FFs':len(l),'shadow_FFs':len(r),'separate':True}
 # Include FIFO and lane copies: yosys keeps memory word names fifo[0], etc.
 for left in list(m['netnames']):
  if re.fullmatch(r'(fifo|lane_pipe)\[\d+\]',left):
   right=left.replace('fifo[','fifo_n[').replace('lane_pipe[','lane_n[')
   l,r=storage(left),storage(right);assert not l&r,(left,right,'shared FFs')
   checks[left+'/'+right]={'primary_FFs':len(l),'shadow_FFs':len(r),'separate':True}
 capture='capture' if 'scale' in a.top else 'capture_data'
 checks[capture]={'capture_FFs':len(storage(capture))}
 checks['capture_en_q']={'capture_enable_FFs':len(storage('capture_en_q'))}
 Path(a.out).write_text(json.dumps({'top':a.top,'netlist':str(a.netlist),'verdict':'PASS','checks':checks},indent=2)+'\n')
 print('PASS embedding mapped metadata has independent FF storage')
