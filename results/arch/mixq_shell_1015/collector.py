import hashlib,json,subprocess
from pathlib import Path
base=Path('/srv/opentallas-scratch/codex-mixq-shell-1015');root=base/'src';out=base/'run'
mods=json.loads((out/'census/hierarchical.json').read_text())['modules'];top=mods['ot_s81_engram_mixq']
names={k:mods[c['type']]['attributes'].get('hdlname',c['type']) for k,c in top['cells'].items()}
assert names=={'mix':'ot_s81_engram_mix','shell':'ot_s81_engram_mixq_shell'},names
assert len(top['cells'])==2
shell=mods[top['cells']['shell']['type']]
ports={p:dict(direction=v['direction'],width=len(v['bits'])) for p,v in shell['ports'].items()}
j=json.loads((out/'census/census.json').read_text());assert j['total_flop_bits']==259329;assert len(j['flop_bits_by_clock'])==33;assert j['flop_bits_by_clock']['ck[0]']==6553
old=json.loads((base/'prior_census.json').read_text());assert j['flop_bits_by_clock']==old['flop_bits_by_clock'];assert j['total_flop_bits']==old['total_flop_bits']
gates=json.loads((out/'gate_results.json').read_text());assert len(gates)==6
for g in gates:
 assert g['ok']
 if g['mutant']==0:assert g['rc']==0 and 'cycles=772' in g['stdout'] and 'in-place20480words' in g['stdout']
 else:assert g['rc']!=0 and 'FAIL' in g['stdout'] and ' words' in g['stdout']
res=dict(source_commit='aa021c333',scope='Real MIX4 shell extraction, native arithmetic/production cycles and root-state census. No physical timing/placement qualification.',gate_results=gates,census=j,parent_cell_hdl_names=names,parent_only_two_hierarchical_cells=True,parent_ports={p:dict(direction=v['direction'],width=len(v['bits'])) for p,v in top['ports'].items()},shell_ports=ports,shell_port_count=len(ports),shell_input_bits=sum(v['width'] for v in ports.values() if v['direction']=='input'),shell_output_bits=sum(v['width'] for v in ports.values() if v['direction']=='output'),root_census_identical=True,source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv',root/'rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv')},fixtures_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (base/'fx').glob('*.pkl')},initial_driver_failure=dict(exit=1,reason='Collector compared literal cell type names; Yosys parameterizes both child types. Recovered using exact module hdlname attributes; no RTL changes or rebuilds.',preserved=True))
(out/'report.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps({k:v for k,v in res.items() if k in ('parent_cell_hdl_names','shell_port_count','shell_input_bits','shell_output_bits','root_census_identical','source_sha256')},indent=1))
