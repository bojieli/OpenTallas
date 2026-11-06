#!/usr/bin/env python3
"""Link existing Verilator PIC hierarchical objects as DSOs; never mutate cache."""
from pathlib import Path
import argparse
import concurrent.futures,subprocess,json,re,time
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--obj',type=Path,required=True,help='completed hierarchical object directory (read only)')
ap.add_argument('--out',type=Path,required=True,help='new output directory, outside the source cache')
ap.add_argument('--prefix',default='Vtb_s81_die')
ap.add_argument('--jobs',type=int,default=4)
ap.add_argument('--expect-libs',type=int)
a=ap.parse_args()
O=a.obj.resolve(); W=a.out.resolve(); P=a.prefix
if W==O or O in W.parents: ap.error('--out must be outside the source cache')
if a.jobs<1: ap.error('--jobs must be positive')
if W.exists() and any(W.iterdir()): ap.error('--out must be a new or empty directory')
S=W/'so';S.mkdir(parents=True,exist_ok=True)
text=(O/(P+'_hier.mk')).read_text()
section=text.split('VM_HIER_LIBS :=',1)[1].split('\n\n',1)[0]
libs=[O/x for x in re.findall(r'(\S+/\S+\.a)',section)]
if not libs: ap.error('no hierarchical archives found')
if a.expect_libs is not None and len(libs)!=a.expect_libs: ap.error('unexpected hierarchical archive count')
if not all(x.is_file() for x in libs): ap.error('one or more hierarchical archives are incomplete')
if len({x.stem for x in libs})!=len(libs): ap.error('duplicate shared-library basenames')
rows=[]
def link(a):
 name=a.stem+'.so'; dst=S/name; objs=sorted(a.parent.glob('*.o'))
 assert objs,a
 assert all(not p.name.startswith('verilated') for p in objs),a
 cmd=['g++','-shared','-Wl,-soname,'+name,'-o',str(dst)]+list(map(str,objs))
 start=time.time()
 with (W/(a.stem+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 row=dict(archive=str(a),objects=len(objs),output=str(dst),rc=r.returncode,elapsed_s=round(time.time()-start,2))
 print(json.dumps(row),flush=True)
 if r.returncode:raise RuntimeError(row)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as ex:
 for row in ex.map(link,libs): rows.append(row)
(W/'shared_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
topobjs=sorted(O.glob('*.o'))
assert all(p.name.startswith((P,'verilated')) for p in topobjs)
cmd=['g++','-rdynamic','-Wl,--no-as-needed','-Wl,-rpath,$ORIGIN/so','-o',str(W/P)]+list(map(str,topobjs))+[r['output'] for r in rows]+['-pthread','-lpthread','-latomic']
with (W/'link.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(W/'link.rc').write_text(str(r.returncode)+'\n')
print('TOP_LINK_RC',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
# Loader resolution only: does not execute the whole-die model.
with (W/'ldd.log').open('w') as f:q=subprocess.run(['ldd','-r',str(W/P)],stdout=f,stderr=subprocess.STDOUT)
print('LOADER_RC',q.returncode,flush=True)
