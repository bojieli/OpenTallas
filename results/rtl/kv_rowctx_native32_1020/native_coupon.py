import pathlib,subprocess,json,re,hashlib
base=pathlib.Path.cwd();tool=base/'coupon';receipts=[]
for name,nick,top in [(base.name,'codex_rowctx_native32','qkd_embedding_row_tx_ctx_native32')]:
 src=base.parent/name;dest=tool/name;dest.mkdir(exist_ok=True)
 libs=sorted(set(re.findall(r'Executing Liberty frontend: (.+)',(src/'synth.log').read_text())))
 args=['python3','/tool/tools/ref_tile/native_census.py','--netlist','/src/work/results/asap7/'+nick+'/base/1_2_yosys.v','--top',top,'--out','/out/native_census.json']
 for lib in libs:args+=['--liberty',lib]
 iid=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}'],text=True).strip()
 r=subprocess.run(['docker','run','--rm','--memory=4g','--memory-swap=4g','-v',str(src)+':/src:ro','-v',str(src/'work')+':/work:ro','-v',str(tool)+':/tool:ro','-v',str(dest)+':/out',iid,*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (dest/'run.log').write_text(r.stdout);(dest/'tooling.json').write_text(json.dumps(dict(image=iid,liberty_paths=libs,tool_sha256=hashlib.sha256((tool/'tools/ref_tile/native_census.py').read_bytes()).hexdigest(),exit_code=r.returncode),indent=1));print(name,r.returncode,r.stdout,flush=True)
