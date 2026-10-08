#!/usr/bin/env python3
"""Generic mapped preservation gate; actual ORFS/cell-mapped qualification remains required."""
from pathlib import Path
import json,re,subprocess,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE='rtl/hbm_accel/control_20261007/'
SOURCES=[BASE+'protected/ot_hbm_sm_serial_protected.sv',BASE+'protected/ot_hbm_sm_serial_protected_core.sv',BASE+'ot_hbm_sm_seq_ingress.sv','rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
def gate_levels(module,modules):
 levels={'0':0,'1':0,'x':0,'z':0}
 for p in module['ports'].values():
  if p['direction']=='input':levels.update({b:0 for b in p['bits']})
 pending=[]
 for c in module['cells'].values():
  ins=[b for n,v in c['connections'].items() if c['port_directions'][n]=='input' for b in v]
  outs=[b for n,v in c['connections'].items() if c['port_directions'][n]=='output' for b in v]
  if 'DFF' in c['type'].upper() or c['type'] in modules:levels.update({b:0 for b in outs})
  else:pending.append((ins,outs))
 while pending:
  left=[]
  for ins,outs in pending:
   if all(b in levels for b in ins):levels.update({b:1+max([levels[x] for x in ins] or [0]) for b in outs})
   else:left.append((ins,outs))
  if len(left)==len(pending):break
  pending=left
 return levels

def main():
 with tempfile.TemporaryDirectory(prefix='sm-protected-map-') as tmp:
  work=Path(tmp);parts=[]
  for path,names in [(SOURCES[-2],['ot_hbm_accel_smv_pipe','ot_hbm_accel_smv_chain','ot_hbm_accel_smv_chan']),(SOURCES[-1],['ot_hbm_accel_bc_kreg'])]:
   text=(ROOT/path).read_text()
   parts.extend(re.search(r'module '+name+r'\b.*?endmodule',text,re.S)[0] for name in names)
  helper=work/'helpers.sv';helper.write_text('\n'.join(parts))
  mapped=work/'mapped.json'
  script='read_verilog -sv '+' '.join(str(ROOT/p) for p in SOURCES[:3])+' '+str(helper)+'\nhierarchy -top ot_hbm_sm_serial_protected -chparam ENABLE 1 -chparam PROTECT 1\nsynth -top ot_hbm_sm_serial_protected -flatten\ncheck\nwrite_json '+str(mapped)+'\n'
  ys=work/'run.ys';ys.write_text(script)
  with (work/'yosys.log').open('w') as log:subprocess.run(['yosys','-Q','-T','-s',str(ys)],stdout=log,stderr=subprocess.STDOUT,check=True)
  modules=json.loads(mapped.read_text())['modules'];top=modules['ot_hbm_sm_serial_protected']
  owners={n:c for n,c in top['cells'].items() if 'protected_core' in c['type']}
  assert set(owners)=={'a','g_secondary.b'},'independent owner copies merged or missing'
  def flops(module):
   return sum(1 if 'DFF' in c['type'].upper() else flops(modules[c['type']]) if c['type'] in modules else 0 for c in module['cells'].values())
  ports=[]
  for cell in owners.values():
   assert cell['attributes'].get('keep') and cell['attributes'].get('keep_hierarchy')
   ports.append({b for n,bs in cell['connections'].items() if cell['port_directions'][n]=='output' for b in bs if isinstance(b,int)})
  assert not ports[0]&ports[1], 'duplicate owners share driven state nets'
  level=gate_levels(top,modules);core=modules[next(iter(owners.values()))['type']];cl=gate_levels(core,modules)
  blocked=top['netnames']['blocked']['bits'];assert all(isinstance(b,int) for b in blocked)
  fanout=sum(sum(b in blocked for b in bs) for c in top['cells'].values() for n,bs in c['connections'].items() if c['port_directions'][n]=='input')
  return dict(scope='local generic Yosys mapped netlist; NOT actual fleet ORFS/ASAP7 or physical timing',
   tool=subprocess.check_output(['yosys','-V'],text=True).strip(),
   source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
   helper_extraction='exact selected module text; unrelated original modules omitted for old local parser compatibility',
   recipe='read_verilog -sv SOURCES; hierarchy -top ot_hbm_sm_serial_protected -chparam ENABLE 1 -chparam PROTECT 1; synth -top ot_hbm_sm_serial_protected -flatten; check; write_json',
   mapped_owner_banks={n:dict(flops=flops(modules[c['type']]),attributes=c['attributes']) for n,c in owners.items()},
   total_mapped_flops=flops(top),driven_owner_nets_disjoint=True,
   wrapper_generic_gate_depth=max(level.values()),state_parity_generic_gate_depth=max(cl[b] for b in core['ports']['state_parity']['bits']),
   blocked_gate_depth=max(level[b] for b in blocked),blocked_direct_cell_pin_fanout=fanout,
   target_clock_qualified=False,actual_flow_preservation_qualified=False,passed=True)
if __name__=='__main__':print(json.dumps(main(),indent=2))
