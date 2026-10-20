from pathlib import Path
import subprocess,os,json,hashlib
R=Path.cwd()
gate=Path('/srv/opentallas-scratch/claude/ref_gate/hv16_dbk_cpl_l1-20261020-065825')
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
suffix='routes/gate/work/orfs/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_banks_cpl_asap7_ref_gate/base/4_1_cts.odb'
p=gate/suffix;before=hashlib.sha256(p.read_bytes()).hexdigest()
base=['docker','run','--rm','-v',str(R)+':/audit','-v',str(gate)+':/frozen:ro']
odb='/frozen/'+suffix
jobs=[('classify',base+['-e','AUDIT_ODB='+odb,'-e','AUDIT_OUT=/audit/l1_CTS_pg_classes.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','-python','/audit/classify.py']),('diagnostic_bind',base+['-e','OT_PG_AUDIT_ODB='+odb,'-e','OT_PG_AUDIT_REPORT=/audit/l1_CTS_diagnostic_post_bind.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','/audit/diagnostic_bind.tcl'])]
for name,cmd in jobs:
 with (R/(name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
assert hashlib.sha256(p.read_bytes()).hexdigest()==before
(R/'receipt_pg_diagnostic.json').write_text(json.dumps(dict(scope='CTS planning diagnostic ONLY, not GRT qualification',odb=str(p),sha256=before,unchanged_after_audit=True,image=img),indent=2)+'\n')
