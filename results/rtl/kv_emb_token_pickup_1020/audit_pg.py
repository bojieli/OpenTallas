import pathlib,subprocess,json,sys,hashlib
p=pathlib.Path.cwd();o=p/'codex_pg_pickup_1020';o.mkdir(exist_ok=True)
bases=list((p/'routes/gate/work/orfs/results/asap7').glob('*/base'));assert len(bases)==1,bases
base=bases[0]
for stage in ['4_1_cts','5_1_grt']:
 db=base/(stage+'.odb');assert db.exists(),db
 script='source /src/physical/common_flow/native_pg_binding.tcl\nread_db /base/'+stage+'.odb\not_pg_audit_snapshot [ord::get_db_block] /out/pg_'+stage+'.json\nexit\n'
 (o/(stage+'.tcl')).write_text(script)
 r=subprocess.run(['docker','run','--rm','--memory=4g','--memory-swap=4g','-v',str(p/'src')+':/src:ro','-v',str(base)+':/base:ro','-v',str(o)+':/out','openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/'+stage+'.tcl'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (o/(stage+'.log')).write_text(r.stdout)
 assert r.returncode==0,r.stdout[-2000:]
 print(stage,json.loads((o/('pg_'+stage+'.json')).read_text()),flush=True)
