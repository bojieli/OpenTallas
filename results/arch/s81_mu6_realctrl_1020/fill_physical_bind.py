from pathlib import Path
import subprocess,hashlib,json
D=Path.cwd();G='/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git';R='804d68ef69adab4aca463317d74bbed100da330d'
a=subprocess.check_output(['git','--git-dir='+G,'ls-tree','-r','--name-only',R,'physical'],text=True).splitlines()
a=[s for s in a if s.endswith(('.v','.sv','.vh')) or s.endswith('/spec.json')]
print('PHYSICAL_SOURCE_FILES',len(a),flush=True)
p=subprocess.Popen(['git','--git-dir='+G,'archive',R,'--',*a],stdout=subprocess.PIPE)
z=subprocess.run(['tar','-xf','-','-C',str(D/'src')],stdin=p.stdout);p.stdout.close();assert z.returncode==0 and p.wait()==0
r=[dict(path=q,sha256=hashlib.sha256((D/'src'/q).read_bytes()).hexdigest()) for q in a]
(D/'physical_source_manifest.json').write_text(json.dumps(dict(ref=R,files=r),indent=2)+'\n')
print('PHYSICAL_SOURCE_READY',len(r),flush=True)
