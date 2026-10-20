import pathlib,json,subprocess
R=pathlib.Path.cwd();img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
for q in [3,2]:
 j=json.load(open('fj'+str(q)+'_job.json'));run=j['run'];base=pathlib.Path(j['metrics']['orfs_dir'])/'results/asap7';marker=pathlib.Path(run)/'src/SOURCE_COMMIT';trim=pathlib.Path(run)/'src/TRIMMED_SOURCE_SNAPSHOT';(R/('fj'+str(q)+'_source_markers.json')).write_text(json.dumps({'source_commit':marker.read_text().strip(),'trim_receipt':trim.read_text()},indent=2)+'\n')
 for stage in ['1_synth','6_final']:
  odb=next(base.glob('*/base/'+stage+'.odb'));target='/frozen/'+str(odb.relative_to(run));name='fj'+str(q)+'_'+stage+'_constants_r2'
  cmd=['docker','run','--rm','-v',str(R)+':/audit','-v',run+':/frozen:ro','-e','CONST_ODB='+target,'-e','CONST_OUT=/audit/'+name+'.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','-python','/audit/inspect_constant_odb_r2.py']
  with open(name+'.log','w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  print(name,'PASS',flush=True)
subprocess.run(['docker','run','--rm','-v',str(R)+':/audit','--entrypoint','python3',img,'/audit/inspect_tielo_liberty.py'],check=True)
