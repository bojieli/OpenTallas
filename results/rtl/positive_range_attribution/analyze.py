"""Locate retained RTL register bits behind the mapped positive-engine path."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BUILD=ROOT/'build/positive_range_attribution'
module='ot_a3_fp32_exp_pos_cr_rne'
after=json.loads((BUILD/'mapped.json').read_text())['modules'][module]
before=json.loads((BUILD/'before_abc.json').read_text())['modules'][module]
text=(BUILD/'mapped.raw.v').read_text()
original=(ROOT/'build/positive_range_pipeline_synth/mapped.raw.v').read_text()
norm=lambda s:Counter(l.strip() for l in s.splitlines() if l.strip())
# Saving pre-ABC names changes alias selection; use a fresh STA run on this netlist.
report=(BUILD/'setup_path.rpt').read_text()
raw=list(re.finditer(r'^  (\w+) (\w+) \((.*?)\n  \);',text,re.M|re.S))
assert len(raw)==len(after['cells'])
bit_names={};name_bits={};cell_names={}
for match,name in zip(raw,sorted(after['cells'])):
 cell=after['cells'][name];assert match[1]==cell['type']
 pins=dict(re.findall(r'\.(\w+)\((.*?)\)',match[3]));assert set(pins)==set(cell['connections'])
 for pin,net in pins.items():
  bits=cell['connections'][pin];assert len(bits)==1
  bit=bits[0];net=net.strip()
  assert bit_names.setdefault(bit,net)==net
  assert name_bits.setdefault(net,bit)==bit
 cell_names[match[2]]=name
results=[]
for timing in re.findall(r'(?:Startpoint|Endpoint): (_\d+_)', report)[1:]:
 name=cell_names[timing];cell=before['cells'][name]
 bits=set(cell['connections']['QN']);initial=set(bits)
 for other in before['cells'].values():
  if other['type']=='$_NOT_' and set(other['connections'].get('A',[]))&initial:
   bits.update(other['connections']['Y'])
 signals={n:[i for i,b in enumerate(v['bits']) if b in bits] for n,v in before['netnames'].items() if not n.startswith('$') and set(v['bits'])&bits}
 assert signals
 results.append(dict(timing_cell=timing,synthesis_cell=name,signals=signals))
files=[BUILD/'mapped.json',BUILD/'before_abc.json',BUILD/'mapped.raw.v',BUILD/'setup_path.rpt',BUILD/'sta.tcl',BUILD/'constraint.sdc',ROOT/'build/positive_range_pipeline_synth/mapped.raw.v']
out=dict(scope='Fresh STA on attributed netlist; prelayout only, not original cell-name reuse or routed timing.',mapped_connectivity_verified=True,endpoints=results,input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(ROOT/'results/rtl/positive_range_attribution/finding.json').write_text(json.dumps(out,indent=2)+'\n')
print(results)
