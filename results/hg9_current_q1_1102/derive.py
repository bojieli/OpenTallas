#!/usr/bin/env python3
"""Derive source-only q1 input metadata and exact existing82-obligation diagnosis; no tools/jobs."""
from pathlib import Path
import collections,hashlib,json,re
p=Path(__file__).resolve().parent
sha=lambda x:hashlib.sha256(x).hexdigest()
rtl=(p/'rtl/qkd_ectlk_columns.sv').read_text()
header=re.search(r'module qkd_ectlk_q1\s*\((.*?)\);',rtl,re.S).group(1)
ports={m[3]:[m[0],int(m[1]),int(m[2])] for m in re.findall(r'\b(input|output)\s+wire\s*\[(\d+):(\d+)\]\s*(\w+)',header)}
assert ports=={'ck':['input',0,0],'rst_n':['input',0,0],'si':['input',282,0],'cfg':['input',4,0],'rsp_data':['input',1023,256],'t0':['output',909,0]}
assert '.QK_ISSUE_AGE(34), .RESPONSE_LAT(18)' in rtl
bits=[f'{n}[{i}]' for n,(dr,hi,lo) in ports.items() for i in range(min(lo,hi),max(lo,hi)+1)]
cl={b:('clk' if b=='ck[0]' else 'in' if ports[b.split('[')[0]][0]=='input' else 'out') for b in bits}
core=dict(schema='opentallas.kv.core_rtl.v1',variant='CURRENT_HG9_Q1_INPUT_PREP_1102',module='qkd_ectlk_q1',type='kv3_hg_v1',inst='ectl_q1',insts=['ectl_q1'],members=['native_leaf'],clocks=['ck'],clock_unknown=[],sameclk=[],ports=len(ports),pin_bits=bits,classes=dict(collections.Counter(cl.values())),port_decl=ports,port_holes={},pin_class=cl,report=dict(added=[],straps=[],gap_bits=[],clock_nets={'ck':'ck[0]'},native_profile={'HXK':13,'MUT':0,'QK_ISSUE_AGE':34,'RESPONSE_LAT':18}),files=[str(x.relative_to(p.parents[1])) for x in sorted((p/'rtl').glob('*.sv'))],source='Exact selected current HG10-file closure copied without edits; no old physical view identity; PREP ONLY.')
(p/'q1_current_core.json').write_text(json.dumps(core,indent=1)+'\n')
plan=(p/'plan/plan_c.json').read_bytes();d=json.loads(plan);hc=next(h for h in d['partition_types']['kv3_hg_v1']['hard_cores'] if h['inst']=='ectl_q1');assert hc['outline_um']==[243.648,172.8]
pinbytes=(p/'plan'/hc['pins_file']).read_bytes();pins=json.loads(pinbytes)['pins'];pinset={x["name"] for x in pins};assert pinset==set(bits),(len(pinset),len(bits))
lec=json.loads((p/'history/old_final_NOT_EQ.json').read_text());points=lec['failing']+lec['unproven_points'];assert len(points)==82 and all(x['status']=='differs' for x in points)
groups=collections.Counter(re.sub(r'\[\d+\]','[]',x['point']) for x in points)
report=dict(status='PREP_ONLY_NO_GEN_OR_JOB',plan_sha256=sha(plan),slot=hc,source_hashes={x.name:sha(x.read_bytes()) for x in sorted((p/'rtl').glob('*.sv'))},macro_asset_hashes={x.name:sha(x.read_bytes()) for x in sorted((p/'macros').iterdir())},actual_current_ABI=dict(ports=len(ports),bits=len(bits),inputs=sum(v=='in' for v in cl.values())+1,outputs=sum(v=='out' for v in cl.values()),current_plan_pin_identity=True),old_proof=dict(counts=lec['counts'],verdict=lec['verdict'],reset_edges=4,hard_differs=64,soft_differs=18,physical_final='f6ba1b08b3115466596d9264aac529d85fd430b89eb85cc0b3a5f9588f3ccb83',groups=dict(groups)),boundary=dict(old_final_view_reusable=False,source_qualified=False,SIGNED=False,added_schedule_cycles='Current source34/18 retained; historical91/80 comparison is not a zero-cycle physical conversion.'))
(p/'PREP.json').write_text(json.dumps(report,indent=2)+'\n')
print('PREP',len(ports),len(bits),'planpins',len(pins),'differs',sum(groups.values()))

# Same normal generator interface as the q0 source canary; exact typed macro assets only.
metadata={'hard_macros':{x.stem:{'lef':str(x.resolve()),'libs':[str(y.resolve()) for y in sorted((p/'macros').glob(x.stem+'*.lib'))]} for x in sorted((p/'macros').glob('*.lef'))}}
assert len(metadata['hard_macros'])==1
(p/'kit_rtl/kv3_hg_v1').mkdir(parents=True,exist_ok=True)
(p/'kit_rtl/kv3_hg_v1/kit_rtl.json').write_text(json.dumps(metadata,indent=2)+'\n')
