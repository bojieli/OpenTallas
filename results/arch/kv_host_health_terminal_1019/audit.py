#!/usr/bin/env python3
"""Validate immutable source graph premises and causal witness logs; no qualification."""
import gzip,hashlib,json,pathlib,re
P=pathlib.Path(__file__).parent
src=json.load(gzip.open(P/'sources.json.gz'));manifest=json.loads((P/'manifest.json').read_text())
assert set(src)==set(manifest)
for path,text in src.items():assert hashlib.sha256(text.encode()).hexdigest()==manifest[path],path
for line in (P/'transitive_remote.sha256').read_text().splitlines():
 h,path=line.split();matches=[v for k,v in manifest.items() if k.endswith('/'+path)];assert matches==[h],path
get=lambda n:next(t for k,t in src.items() if k.endswith('/'+n))
for line in (P/'final_inputs.sha256').read_text().splitlines():
 h,name=line.split()
 text=(P/name).read_text() if name in ('tb.sv','guard_resetretain.sv') else get(name)
 assert hashlib.sha256(text.encode()).hexdigest()==h,name
g=get('qkd_host_service_guard.sv');p=get('ot_qfd_pkgctl.sv');c=get('qkd_host_ctl_service_pins.sv');f=get('qkd_host_fullcontrol_observed.sv')
assert 'wire bad=protocol_fault||internal_bad||(|next_sticky);' in g
assert 'guarded_tk<={tk_q[92:89],tk_q[88]|bad,tk_q[87:0]};' in g
assert 'physical_diag<=pf_q|' in g and 'transport_diag<=tf_q|' in g
assert 'if (d_done[k] && d_done_gen[k*2 +: 2] == d_gen && d_fault[k]) any_fault_c' in p
assert 'else if (busy && any_fault)' in p
assert '.ready(ready_q&&!pb_q' in c and '.tk(tk_q)' in c
assert 'assign package_abort=eng_fault;' in f and 'assign eng_fault=ctl_res[1]' in f
x=json.loads((P/'source_terminal_graph.json').read_text());assert len(x['raw_service_bits'])==25
assert x['physical_terminal_consumer'] is None and x['transport_terminal_consumer'] is None
assert x['qualified_release'] is False
assert 'PASS host health mechanism checks=21' in (P/'final.run.log').read_text()
for name,witness in [('rawdrop','sticky abort edge3'),('lateadmit','subsequent start rejected fault'),('resetretain','startup')]:
 t=(P/(name+'.run.log')).read_text();assert '%Fatal:' in t and witness in t
assert 'Verilator 5.050' in (P/'version.txt').read_text()
print('PASS immutable19source graph;25rawbits; physical/transport terminal gap;21mechanism checks;3causal mutants. Native/reset/fixedSTATUS unqualified.')
