#!/usr/bin/env python3
"""Offline provenance restoration of original VE inputs; never launches EDA or changes daemon state."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path.cwd(); OUT=pathlib.Path(sys.argv[1]).resolve()
if OUT.exists(): raise SystemExit('Refuse existing recovery root')
receipt=ROOT/'results/rtl/s81_ve_postretire_1021'; job=json.load(open(receipt/'cancelled_job.json')); gate=json.load(open(ROOT/'physical/ref_tile/s81sl_ve_r5/gate_result.json'))['source_binding']
sha=job['commit_full']; tree={}
for row in subprocess.check_output(['git','ls-tree','-rz','--full-tree',sha]).split(b'\0'):
 if row:
  meta,path=row.split(b'\t',1);mode,kind,blob=meta.decode().split();tree[path.decode()]=(int(mode,8)&0o777,blob)
p=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
def get(blob):
 p.stdin.write((blob+'\n').encode());p.stdin.flush();head=p.stdout.readline().split()
 if len(head)!=3 or head[1]!=b'blob':raise RuntimeError('missing exact blob '+blob)
 n=int(head[2]);raw=p.stdout.read(n);assert len(raw)==n and p.stdout.read(1)==b'\n';return raw
def write(path,blob,mode,expected=None):
 q=OUT/path;assert not pathlib.PurePosixPath(path).is_absolute() and '..' not in pathlib.PurePosixPath(path).parts
 raw=get(blob);actual=hashlib.sha256(raw).hexdigest()
 if expected and actual!=expected:raise RuntimeError('SHA mismatch '+path)
 q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);q.chmod(mode);return actual
OUT.mkdir(parents=True)
source_delta=[]
for f in gate['files']:
 mode,blob=tree[f['path']];h=write(f['path'],blob,mode)
 if h!=f['sha256']:source_delta.append(f['path'])
assert source_delta==['tools/orfs_hold_mm.tcl'],source_delta
for f in job['route_overlay_plan']['files']:write(f['path'],f['git_blob'],f['mode'],f['sha256'])
p.stdin.close();assert p.wait()==0
before={str(q.relative_to(OUT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in OUT.rglob('*') if q.is_file()}
assert before['tools/orfs_hold_mm.tcl']==next(f['sha256'] for f in gate['files'] if f['path']=='tools/orfs_hold_mm.tcl')
proof={'source_commit':sha,'gate_consumed_files':len(gate['files']),'source_delta_before_frozen_overlay':source_delta,'frozen_overlay_files':len(job['route_overlay_plan']['files']),'frozen_overlay_content_sha256':job['route_overlay_plan']['content_sha256'],'source_root':str(OUT),'before_tt_transform':before}
sequence=['hold_corners_patch.py','tt_overlay.py','hold_corners_patch.py'] if '--final-eco-transform' in sys.argv else ['tt_overlay.py']
proof['transform_sequence']=[]
for script in sequence:
 log=subprocess.run([sys.executable,str(OUT/'tools/closure_loop'/script),str(OUT)],capture_output=True,text=True)
 proof['transform_sequence'].append({'script':script,'exit':log.returncode,'stdout':log.stdout,'stderr':log.stderr,'script_sha256':before['tools/closure_loop/'+script]})
 if log.returncode:break
proof['tt_transform']={'exit':log.returncode,'stdout':log.stdout,'stderr':log.stderr,'script_sha256':before['tools/closure_loop/tt_overlay.py']}
after={str(q.relative_to(OUT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in OUT.rglob('*') if q.is_file()}
proof['post_tt_changed']={k:{'before':before.get(k),'after':v} for k,v in after.items() if before.get(k)!=v}
(receipt/('verified_archive/FINAL_ECO_SOURCE.json' if '--final-eco-transform' in sys.argv else 'verified_archive/RESTORED_SOURCE.json')).write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'files':len(before),'tt_exit':log.returncode,'tt_changed':len(proof['post_tt_changed']),'source_root':str(OUT),'stdout':log.stdout},indent=2))
if log.returncode:raise SystemExit(log.returncode)
