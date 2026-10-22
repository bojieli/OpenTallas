import pathlib,subprocess,os,json,hashlib,sys
q=sys.argv[1]; R=pathlib.Path.cwd();j=json.load(open('fj'+q+'_job.json'));run=j['run'];label=j['name'].replace('-','_');base=pathlib.Path(j['metrics']['orfs_dir'])/'results/asap7';odb=next(base.glob('*/base/6_final.odb'));image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'job':j['name'],'commit':j['commit_full'],'odb':str(odb),'before_sha256':sha(odb),'timing_scope':j['metrics'],'status_at_launch':j['status']}
args=['docker','run','--rm','-v',str(R)+':/audit','-v',run+':/frozen:ro'];o='/frozen/'+str(odb.relative_to(run));tag='fj'+q+'final'
def call(n,s,py=False,extra=[]):
 env=['-e','AUDIT_ODB='+o,'-e','AUDIT_OUT=/audit/'+tag+'_'+n+'.json','-e','OT_PG_AUDIT_ODB='+o,'-e','OT_PG_AUDIT_REPORT=/audit/'+tag+'_'+n+'.json']+extra
 with open(tag+'_'+n+'.log','w') as f:rc=subprocess.run(args+env+['--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',image,'-exit']+(['-python'] if py else [])+['/audit/'+s],stdout=f,stderr=subprocess.STDOUT).returncode
 print(tag,n,rc,flush=True)
for n,s,py in [('original_pg','audit_native_pg.tcl',False),('classes','classify.py',True),('diagnostic_bind','diagnostic_bind.tcl',False),('sequential_reach','sequential_reach.py',True)]:call(n,s,py)
call('unreached','classify_unreached.py',True,['-e','AUDIT_REACH_REPORT=/audit/'+tag+'_sequential_reach.json'])
call('graph','dump_native_graph_complete.tcl',False,['-e','CELL_GRAPH=/audit/fj'+q+'_native_graph_cells.tsv','-e','PORT_GRAPH=/audit/fj'+q+'_native_graph_ports.tsv'])
cmd='python3 /audit/native_odb.py '+q+' /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib* /frozen/src/physical/asap7_memory_macros/ot_sram_1rw_128x64_m2_r2c2_p192_mir/*_tt.lib'
with open(tag+'_native.log','w') as f:subprocess.run(args+['--entrypoint','bash',image,'-lc',cmd],stdout=f,stderr=subprocess.STDOUT)
manifest['after_sha256']=sha(odb);manifest['immutable']=manifest['before_sha256']==manifest['after_sha256'];pathlib.Path(tag+'_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('IMMUTABLE',manifest['immutable'],flush=True)
