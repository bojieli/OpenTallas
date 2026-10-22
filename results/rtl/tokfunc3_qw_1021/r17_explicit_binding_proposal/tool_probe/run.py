from pathlib import Path
import subprocess,hashlib,json
r=Path(__file__).resolve().parent;o=r.parent/'hier_binding_probe';o.mkdir(exist_ok=True)
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
def call(args,name,cwd=r):
 p=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(o/(name+'.log')).write_text(p.stdout);print(name,p.returncode,flush=True);assert p.returncode==0,p.stdout[-3000:]
call([v,'--cc','--hierarchical','-j','1','--top-module','top','--prefix','Vtop','--Mdir',str(o/'original'),str(r/'leaf.sv'),str(r/'top.sv'),str(r/'cut.vlt')],'generate')
children=list((o/'original').glob('Vleaf_*'));children=[p for p in children if p.is_dir()];assert len(children)==1,children
child=children[0];assert child.name=='Vleaf_c',child
call(['make','-j1','-C',str(child),'-f','Vleaf_c.mk'],'archive')
lib=child/'libleaf_c.a';assert lib.is_file()
call([v,'--cc','--exe','--build','-j','1','--top-module','top','--prefix','Vtop','--Mdir',str(o/'explicit'),str(child/'leaf_c.sv'),str(r/'leaf.sv'),str(r/'compare.sv'),str(r/'main.cpp'),'-LDFLAGS',str(lib)],'explicit')
checks=[]
for name,args in [('positive',[]),('input_mutant',['mut'])]:
 p=subprocess.run([str(o/'explicit/Vtop'),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(o/(name+'.log')).write_text(p.stdout)
 ok=(p.returncode==0 and 'REAL_ARCHIVE_BINDING_PASS' in p.stdout) if name=='positive' else p.returncode==1 and 'BINDING_DATA_MISMATCH' in p.stdout
 checks.append(dict(name=name,rc=p.returncode,output=p.stdout,ok=ok));print(checks[-1],flush=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(o/'record.json').write_text(json.dumps(dict(scope='Tool mechanism only, not current Qwen full-vehicle qualification',source_sha={p.name:sha(p)for p in r.iterdir()if p.is_file()},archive_sha256=sha(lib),binary_sha256=sha(o/'explicit/Vtop'),params=dict(N=32),checks=checks),indent=2)+'\n');assert all(c['ok']for c in checks)
