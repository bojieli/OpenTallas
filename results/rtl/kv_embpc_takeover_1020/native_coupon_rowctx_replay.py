import pathlib,subprocess,json,re
p=pathlib.Path.cwd();job=pathlib.Path('/srv/opentallas-scratch/claude/closure-loop/qkd_embedding_row_tx_ctx_c1b-c1b-7ea686674');orfs=job/'routes/qkd_embedding_row_tx_ctx_c1b_c1b_7ea686674/work/orfs'
logs=list((orfs/'logs').rglob('1_*yosys*.log'));text='\n'.join(x.read_text() for x in logs)
libs=sorted(set(re.findall(r'Executing Liberty frontend: (.+)',text)))
net=next((orfs/'results').rglob('1_2_yosys.v'))
args=['python3','/tool/tools/ref_tile/native_census.py','--netlist','/work/'+str(net.relative_to(orfs)),'--top','qkd_embedding_row_tx_ctx','--out','/out/native_census.json']
for lib in libs:args+=['--liberty',lib]
iid=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}'],text=True).strip()
r=subprocess.run(['docker','run','--rm','--memory=4g','--memory-swap=4g','-v',str(p/'src_replay')+':/src:ro','-v',str(orfs)+':/work:ro','-v',str(p)+':/tool:ro','-v',str(p)+':/out',iid,*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(p/'run.log').write_text(r.stdout);(p/'inputs.json').write_text(json.dumps(dict(image=iid,libs=libs,job=str(job),netlist=str(net),exit_code=r.returncode),indent=1));print(r.stdout);raise SystemExit(r.returncode)
