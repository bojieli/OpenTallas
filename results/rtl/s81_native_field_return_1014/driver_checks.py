from pathlib import Path
import subprocess,json,hashlib
w=Path('/srv/opentallas-scratch/codex/s81-native-field')
r=w/'mut/runs/L0.a_proj.fp8@s0/r000'; im=r/'img'
nom=w/'gate/build/tb'; old=Path('/srv/opentallas-scratch/claude/s81-ftok/r5/field/build/tb')
ops=r/'ops.txt'; fixture=ops.read_text()
def run(exe,op):
 p=subprocess.run([str(exe),str(im),str(op)],text=True,capture_output=True)
 return p, [l for l in p.stdout.splitlines() if l.startswith('W ')], [l for l in p.stdout.splitlines() if l.startswith('OP ')]
p,nw,no=run(nom,ops);q,ow,oo=run(old,ops)
assert p.returncode==q.returncode==0
assert sorted(l.split()[2:] for l in nw)==sorted(l.split()[2:] for l in ow)
cases={}
for name,body,reason in [('empty','', 'no_operations'),('cycle0',fixture.rsplit(' ',1)[0]+' 0\n','scheduled_issue_late'),('overlap',fixture+fixture.replace(' 1\n',' 2\n'),'scheduled_issue_late')]:
 path=w/(name+'.ops');path.write_text(body);a,_,_=run(nom,path)
 assert a.returncode!=0 and reason in a.stdout,(name,a.returncode,a.stdout[-500:])
 cases[name]=dict(returncode=a.returncode,reason=reason,tail=a.stdout.splitlines()[-1:])
out=dict(schema='opentallas.s81.native-field-return.driver.v1',rows=len(nw),words_equal_legacy=True,native_op=no,legacy_op=oo,negative_cases=cases,binary_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (nom,old)})
(w/'driver_checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
