#!/usr/bin/env python3
"""Audit literal SRAM address tables against the independent source-bound model."""
import json,pathlib,re
r=pathlib.Path(__file__).resolve().parents[3]
m=json.loads((pathlib.Path(__file__).with_name('MODEL.json')).read_text())
s=(r/'rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv').read_text()
for fn in ['ca_node','cb_node','node_role','node_rank']:
 b=re.search(r'function automatic \[[^]]+\] '+fn+r'\(.*?endfunction',s,re.S).group()
 cases=re.findall(r'case\(n\)(.*?)endcase',b,re.S)
 assert len(cases)==2,(fn,len(cases))
 for text,profile in zip(cases,['EASSOC','production']):
  spec=m['static_port_enumeration'][profile]
  actual={int(k):int(v) for k,v in re.findall(r"8'd(\d+):\s*"+fn+r"=(?:1|8)'d(\d+)",text)}
  if fn in ['ca_node','cb_node']:
   role='LEFT' if fn=='ca_node' else 'RIGHT'
   expected={v['node']:int(k) for k,v in spec['consumer_map'].items() if v['role']==role}
  elif fn=='node_role':expected={int(k):int(v=='RIGHT') for k,v in spec['role_map'].items()}
  else:expected={n:i for ns in spec['stored_internal_by_role'].values() for i,n in enumerate(ns)}
  assert actual==expected,(fn,profile,actual,expected)
print('PASS exact RTL literals vs independent source-bound model: 8 production/causal operand/colour/rank tables')
