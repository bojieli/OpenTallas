import pathlib,subprocess,io,tarfile,base64
w=pathlib.Path(__file__).resolve().parents[3];data={}
for p in ['tools/ref_tile/native_census.py','tools/textbook_lint.py']:data[p]=(w/p).read_bytes()
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:
 for n,x in data.items():i=tarfile.TarInfo(n);i.size=len(x);t.addfile(i,io.BytesIO(x))
root='/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_sr7-20261019-214154'
code='''import pathlib,os,tarfile,io,base64,subprocess,re,json
b=pathlib.Path(__ROOT__);p=b/'codex_native_authority_1020';p.mkdir(exist_ok=True);os.chdir(p)
tarfile.open(fileobj=io.BytesIO(base64.b64decode(__PAYLOAD__)),mode='r:gz').extractall()
w=b/'routes/gate/work/orfs';logs=list((w/'logs/asap7').glob('*/base/1_1_yosys_canonicalize.log'));libs=sorted(set(re.findall(r'Executing Liberty frontend: (.+)',logs[0].read_text())))
net=list((w/'results/asap7').glob('*/base/1_2_yosys.v'))[0];iid=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}'],text=True).strip();args=['python3','/tool/tools/ref_tile/native_census.py','--netlist','/work/'+str(net.relative_to(w)),'--top','qkd_kvs_pc','--out','/out/native_census.json']
for lib in libs:args+=['--liberty',lib]
print('SOURCE_ROOT',p,flush=True)
r=subprocess.run(['docker','run','--rm','--memory=12g','--memory-swap=12g','-v',str(b/'src')+':/src:ro','-v',str(w)+':/work:ro','-v',str(p)+':/tool:ro','-v',str(p)+':/out',iid,*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(p/'run.log').write_text(r.stdout);(p/'tooling.json').write_text(json.dumps(dict(image=iid,liberty_paths=libs,exit_code=r.returncode),indent=1));print(r.stdout,flush=True);raise SystemExit(r.returncode)
'''.replace('__ROOT__',repr(root)).replace('__PAYLOAD__',repr(base64.b64encode(b.getvalue()).decode()))
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','12','--threads','1','--dir',root,'--','python3','-c',code]))
