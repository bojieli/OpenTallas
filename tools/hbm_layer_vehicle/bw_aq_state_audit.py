#!/usr/bin/env python3
"""Record actual mapped AQ state D/clock/reset pins and bounded-load results."""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--netlist',type=Path,required=True)
p.add_argument('--fanout',type=Path,required=True)
p.add_argument('--contract',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
t=a.netlist.read_text(); contract=json.loads(a.contract.read_text())
families=contract['families']; found={k:[] for k in families}; forbidden=[]; errors=[]
for m in re.finditer(r'\b(\w+)\s+(\\?[^\s()]+)\s*\((.*?)\);',t,re.S):
 typ,cell,body=m.groups()
 if 'DFF' not in typ: continue
 name=cell.lstrip('\\'); prefix='u_ot_pr_core.controller.'
 if not name.startswith(prefix):continue
 suffix=name[len(prefix):]
 base=re.split(r'[\[$]',suffix,1)[0]
 if base in contract['forbidden_families']:forbidden.append(name)
 if base not in found:continue
 pins=dict(re.findall(r'\.(\w+)\(([^()]*)\)',body))
 record={'cell':name,'library':typ,'pins':pins}
 found[base].append(record)
 if pins.get('CLK','').strip()!='clk':errors.append('unexpected clock: '+name)
 if not pins.get('D','').strip():errors.append('missing D: '+name)
 unreset={'head_local','fresh_addr_local','head_bank_local','head_read_global'}
 has_async=bool({'RESETN','SETN'} & pins.keys())
 if base=='row_local':
  bit=int(re.findall(r'\[(\d+)\]',suffix)[-1]); expect_async=bit>=19
 else:expect_async=base not in unreset
 if has_async!=expect_async:errors.append('unexpected reset class: '+name)
for family,n in families.items():
 if len(found[family])!=n:errors.append(f'{family}: expected {n} actual {len(found[family])}')
if forbidden:errors.append('obsolete one-hot state remains')
fan=json.loads(a.fanout.read_text()); netsha=hashlib.sha256(a.netlist.read_bytes()).hexdigest()
if fan['source_sha256']!=netsha:errors.append('fanout/netlist hash mismatch')
nonreset=[r for r in fan['roots'] if not r['reset']]
r={'schema':'opentallas.bw_aq_mapped_state.v1','source_netlist_sha256':netsha,
   'contract_sha256':hashlib.sha256(a.contract.read_bytes()).hexdigest(),
   'pass_copy_structure':not errors,'pass_global_fanout':not nonreset,
   'errors':errors,'families':found,'forbidden_cells':forbidden,
   'nonreset_over32':[{k:x[k] for k in ['label','loads','root_type']} for x in nonreset]}
a.output.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'pass_copy_structure':not errors,'errors':errors,'nonreset_over32':len(nonreset)}))
raise SystemExit(0 if not errors else 1)
