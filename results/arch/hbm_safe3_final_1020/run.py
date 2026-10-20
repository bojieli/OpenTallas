from pathlib import Path
import subprocess,os
r=Path.cwd();img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
frozen=Path('/srv/opentallas-scratch/claude/closure-loop/hbm_su_pg_stream_b_safe3_1019-s3-a160833f0')
base='/frozen/routes/hbm_su_pg_stream_b_safe3_1019_s3_a160833f0/work/orfs/results/asap7/opentallas_ot_hbm_su_static_pg_stream_split_safe3_asap7_ref_hbm_su_pg_stream_b_safe3_1019_s3_a160833f0/base/'
docker=['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',str(r)+':/audit','-v',str(frozen)+':/frozen:ro']
op='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
for name in ['reach','sequential_reach','classify']:
 cmd=docker+['-e','AUDIT_ODB='+base+'6_final.odb','-e','AUDIT_OUT=/audit/'+name+'.json','--entrypoint',op,img,'-exit','-python','/audit/'+name+'.py']
 with (r/(name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
cmd=docker+['-e','OT_PG_AUDIT_ODB='+base+'6_final.odb','-e','OT_PG_AUDIT_REPORT=/audit/native_pg.json','--entrypoint',op,img,'-exit','/audit/audit_native_pg.tcl']
with (r/'native_pg.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
print('native_pg',rc,flush=True)
shell="""set -eu
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
LIBS=''
for f in $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_nldm_*.lib*; do LIBS="$LIBS --liberty $f"; done
PYTHONPATH=/audit python3 /audit/native_census.py --netlist """+base+"""6_final.v --top ot_hbm_su_static_pg_stream_split_safe3 --out /audit/native_census_final.json $LIBS
"""
cmd=docker+['--entrypoint','bash',img,'-c',shell]
with (r/'native_census.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
print('native_census',rc,flush=True)
