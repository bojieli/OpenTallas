#!/usr/bin/env python3
"""Portable source-exact R3k release bench; private mutation shadows preserve source."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[3]
name=sys.argv[1];run=Path(sys.argv[2]).resolve();run.mkdir(parents=True,exist_ok=True)
mutations=json.loads(Path(__file__).with_name('mutations.json').read_text())
bench='results/arch/qw_n59v6_service_1020/bench.sh'
case=name;source=root
if name in mutations:
 m=mutations[name];case=m['case'];source=run/'private_src'
 if source.exists():raise SystemExit('private source exists; choose a new RUN')
 private={m['path'],bench}
 def shadow(src,dst,prefix=''):
  dst.mkdir()
  for x in src.iterdir():
   if x.name=='.git':continue
   rel=prefix+x.name
   if rel in private:dst.joinpath(x.name).write_bytes(x.read_bytes())
   elif any(p.startswith(rel+'/') for p in private):shadow(x,dst/x.name,rel+'/')
   else:dst.joinpath(x.name).symlink_to(x.resolve(),target_is_directory=x.is_dir())
 shadow(root,source)
 p=source/m['path'];s=p.read_text()
 if s.count(m['old'])!=1:raise SystemExit('mutation source mismatch')
 p.write_text(s.replace(m['old'],m['new']))
 (run/'mutation.json').write_text(json.dumps(dict(m,mutated_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=2))
if case not in ('local_rnd','local_reset8','local_mu','local_dv','component'):raise SystemExit('undefined release case')
p=subprocess.run(['bash',str(source/bench),case,str(run/'out')],cwd=source,capture_output=True,text=True)
(run/'bench.log').write_text(p.stdout+p.stderr)
print(p.stdout,end='');print(p.stderr,end='')
wrapper=run/'out/wrapper.log'
if wrapper.is_file():print(wrapper.read_text(),end='')
print('N59_RELEASE_EXIT case='+name+' code='+str(p.returncode))
sys.exit(p.returncode)
