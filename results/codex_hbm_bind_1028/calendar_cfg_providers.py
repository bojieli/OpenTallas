"""Emit independent SW/SE configuration-only HOST replicas for actual S-role calendar targets.
NoNorth-Southalias/noabsentstatusprovider. CFG2edges+samethreeedgeresetreleaseasoriginalleafcopyA.
usage calendar_cfg_providers.py INPUT_TOP OUTPUT_TOP OUT_MAP
"""
import json,re,sys
from pathlib import Path
P=[('cfg_v',1),('cfg_target',8),('cfg_addr',12),('cfg_data',256),('desc_v',1),('desc_base',12),('desc_limit',13),('desc_loops',16),('launch_v',1)]
s=Path(sys.argv[1]).read_text();assert s.count('\nendmodule')==1;rm={f'hleaf_{r}__a_{pn}' for r in ('SW','SE') for pn,_ in P}
h=re.search(r'(module hbm_current_native_top \()([^;]+?)(\);)',s,re.S);assert h
ports=[p.strip() for p in h[2].split(',')];assert rm<=set(ports)
s=s[:h.start(2)]+', '.join(p for p in ports if p not in rm)+s[h.end(2):]
for n in rm:
 rx=r'(?m)^(\s*)input wire(\s+\[[^\]]+\])?\s+'+re.escape(n)+r';\s*$'
 s,nsub=re.subn(rx,lambda m:m[1]+'wire'+(m[2] or '')+' '+n+';',s);assert nsub==1,(n,nsub)
parts={};details=[];ins='\n// Independent q0 calendar HOST replicas; globalingress source, no S-role status tie.\n'
for role,part in [('SW','NW_hub'),('SE','NE_hub')]:
 name='hleaf_'+role;assert not re.search(r'\b'+name+r' \(',s)
 ins+=f' ot_hnx_calendar_cfg_leaf {name} (\n .clk(hb_ckgen__pll_stream[0]),.rst_n(hb_ckgen__por_stream[0]),\n'
 cs=[]
 for pn,w in P:cs.append(f' .{pn}(host_cp_ingress__{pn}[{w-1}:0])')
 for pn,w in P:cs.append(f' .a_{pn}(hleaf_{role}__a_{pn}[{w-1}:0])')
 ins+=',\n'.join(cs)+'\n );\n';parts[name]=[part,'u_hleaf_Q__q0'];details.append(dict(instance=name,partition=part,plan_instance='u_hleaf_Q__q0',module='ot_hnx_calendar_cfg_leaf',params={},input_bits=320,output_bits=320,clock_reset_bits=2,config_latency=2,reset_release=3,added_boot_cycles_vs_intended_leaf=0))
s=s.replace('\nendmodule',ins+'\nendmodule',1);Path(sys.argv[2]).write_text(s)
Path(sys.argv[3]).write_text(json.dumps(dict(parts=parts,providers=details,removed_external_inputs=sorted(rm),unchanged_diagnostics=['calendar_SW__tgt_configured','calendar_SW__tgt_fault','calendar_SW__fault','calendar_SE__tgt_configured','calendar_SE__tgt_fault','calendar_SE__fault'],host_status_gap='TheseSrolecalendarstatuspinsremainexplicitdietopoutputs,notfoldedintotheexistingtwoNorthleafhost_statusjoin. TokenbootmustcheckactualSconfigured/faultbeforeSTART; noabsentScomputestatuscoverageclaim.'),indent=2)+'\n')
print('2independentcalendarCFGproviders;18externalcfginputsresolved;642pins/master;0addedcyclesvsintendedleaf')
