import os,subprocess
case='/srv/opentallas-scratch/claude/ref_gate/dscoll_lane_e_s6c-20261020-051416'
base=['docker','run','--rm','--network','none','-v',os.getcwd()+':/audit','-v',case+':/case:ro','-v',case+'/src:/src:ro','openroad/orfs:asap7lock']
for name,cmd in [('classify_db',['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-exit','/audit/classify.tcl']),('classify',['python3','/audit/classify.py'])]:
 with open(name+'.log','w')as f:rc=subprocess.run(base+cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
 if rc:raise SystemExit(rc)
