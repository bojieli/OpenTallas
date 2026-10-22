import pathlib,subprocess,os
cases=[('hwin','dsdv_mu_hwin_c21l-20261020-045744','3_5_place_dp-failed.odb'),('lep','s81sl_lepwd-20261020-060447','3_3_place_gp-failed.odb'),('lepnh','s81sl_lepnhwd-20261020-060447','3_3_place_gp-failed.odb')]
status=[]
for label,case,name in cases:
 root=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate')/case;db=list(root.glob('routes/gate/work/orfs/results/**/'+name));assert len(db)==1
 cmd=['docker','run','--rm','--network','none','-v',os.getcwd()+':/audit','-v',os.getcwd()+'/src:/src:ro','-v',str(root)+':/case:ro','-e','AUDIT_DB=/case/'+str(db[0].relative_to(root)),'-e','AUDIT_LABEL='+label,'openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-exit','/audit/candidate_model.tcl']
 with open(label+'_candidate_model_causal5.log','w')as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(label,rc,flush=True);status.append(rc)
raise SystemExit(any(status))
