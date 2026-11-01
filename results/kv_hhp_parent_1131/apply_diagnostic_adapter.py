#!/usr/bin/env python3
"""Approved geometry-only PC/HHP parent cut; exact existing face mapping plus recovered mesh ports."""
from pathlib import Path
import json,re,hashlib,shutil
R=Path('/srv/opentallas-scratch2/claude/codex-kv-hhp-parent-1131');C=Path('/srv/opentallas-scratch2/claude/codex-kv-pc-cores-1101/parent_abi_census1131');K=R/'geometry_adapted3'
assert not K.exists();shutil.copytree(R/'geometry_current',K,ignore=shutil.ignore_patterns('run','FAIL_*','preflight_history'))
A=json.loads((R/'approved_nonFT_adapter.json').read_text());M=json.loads((C/'ft_connection_manifest.json').read_text());assert M['mesh_sites_sha256']=='d25f60c6f22e6921a36d73a850b3bc8a3822f0e5545879ff05e84bd1755513db'
partmaps={}
for part in M['parts']:
 arcs=[x for x in M['arcs'] if x['part']==part];assert len(arcs)==8
 ns={x['input_net']:x['input_driver_parent_center_um'] for x in arcs};assert len(ns)==4
 names=sorted(ns,key=lambda n:ns[n][1]);aliases={n:f'diag_mesh_pre_{i}' for i,n in enumerate(names)}
 partmaps[part]={'input_aliases':{aliases[n]:{'actual_net':n,'actual_driver':next(x['input_driver'] for x in arcs if x['input_net']==n),'driver_parent_center_um':ns[n]} for n in names},'output_alias':{'diag_mesh_post':'ck_mesh'},'connections':{}}
 for arc in arcs:
  assert arc['output_net']=='ck_mesh'
  c=partmaps[part]['connections'].setdefault('u_'+arc['child'],{})
  assert arc['input_port'] not in c and arc['output_port'] not in c
  c[arc['input_port']]=aliases[arc['input_net']];c[arc['output_port']]='diag_mesh_post'
 assert len(partmaps[part]['connections'])==4
assert set(partmaps)=={'pc_EN_0','pc_WN_0'}
for inst in partmaps['pc_EN_0']['connections']:assert partmaps['pc_EN_0']['connections'][inst]==partmaps['pc_WN_0']['connections'][inst]
T='kv3_pc__cl5a95b461';bound=K/'rtl'/(T+'_bound.sv');s=bound.read_text()
for r in A['instances']:
 i=r['instance'];mod=r['module'];bindings={**r['exact_non_FT_bindings'],**partmaps['pc_EN_0']['connections'][i]}
 bb=next((K/('current_hhp' if i=='u_kvpc0' else 'current_pc')).glob('*.bb.v')).read_text();ports=set(re.findall(r'\b(?:input|output)\s+wire\s+(?:\[[^\]]+\]\s+)?([A-Za-z_]\w*)',bb));assert set(bindings)==ports,(i,set(bindings)^ports)
 pat=rf'(?m)^    {mod} {i} \((.*?)\n    \);';matches=list(re.finditer(pat,s,re.S));assert len(matches)==1
 call='    '+mod+' '+i+' (\n'+',\n'.join('        .'+k+'('+v+')' for k,v in bindings.items())+'\n    );'
 s=re.sub(pat,lambda _:call,s,count=1,flags=re.S)
newdecl=''.join('    input wire diag_mesh_pre_'+str(i)+',\n' for i in range(4))+'    output wire diag_mesh_post,\n'
def ports(s):
 pat=r'(?m)^(\s*)input\s+wire\s+clk,';assert len(re.findall(pat,s))==1
 return re.sub(pat,lambda m:newdecl+m[1]+'input wire clk,',s,count=1)
s=ports(s);bound.write_text(s)
w=K/'rtl'/(T+'.sv');s=w.read_text();assert s.count('u_bound (\n')==1
s=s.replace('u_bound (\n','u_bound (\n'+''.join('        .diag_mesh_pre_'+str(i)+'(diag_mesh_pre_'+str(i)+'),\n' for i in range(4))+'        .diag_mesh_post(diag_mesh_post),\n');w.write_text(ports(s))
ledger={'status':'GEOMETRY ONLY; exact5port die-network extrusion approved; PLACE HELD until actual portgeometry LOOK','representative_part':'pc_EN_0','type':T,'mesh_sha256':M['mesh_sites_sha256'],'source_graph':M['graph_source'],'per_instance_network_cut':partmaps,'downstream_taps_outside_cut':M['downstream_taps'],'canonical_ABI_adoption_STA_EQ':'HELD, no claim','nonFT_contract':'approved_nonFT_adapter.json','geometry_status':'No invented pin locations; actual node/strap geometry to be supplied before PLACE','RTL_bound_sha256':hashlib.sha256(bound.read_bytes()).hexdigest()}
(K/'diagnostic_network_cut.json').write_text(json.dumps(ledger,indent=1)+'\n');print('Exact5port parent extrusion staged; all4 child complete port sets match; no unknown ports or FT ties/dangles; no PLACE yet')
