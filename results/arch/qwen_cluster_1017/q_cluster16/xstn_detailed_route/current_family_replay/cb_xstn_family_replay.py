from pathlib import Path
import subprocess,json,hashlib
records=[]
for n in ['qfd_c_xstn_safe','qfd_c_xstnw_safe']:
 job=n+'-safe1-ac5cc8826';r=Path('/srv/opentallas-scratch/claude/closure-loop')/job;route=r/'routes'/job.replace('-','_');base=next((route/'work/orfs/results/asap7').glob('*/base'))
 cmd=['python3','ck_insertion.py','--base',str(base),'--clock','core_clk','--routed','--route-corner','TC','--raw-source','--output',n+'_current_family.json']
 with Path(n+'_current_family.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 records.append(dict(component=n,source_main='59835e962ec617f79ad2ca57daf58cf479ac8487',inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [base/'6_final.odb',base/'6_final.sdc',base/'6_final.spef',Path('ck_insertion.py'),Path('clock_family.tcl')]}))
 print('CURRENT_FAMILY_DONE',n,flush=True)
Path('current_family_sources.json').write_text(json.dumps(records,indent=1)+'\n')
