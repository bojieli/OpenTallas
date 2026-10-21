from pathlib import Path
import shutil,gzip,hashlib,json
r=Path('results/rtl/qw_head_safe32_1020');o=r/'evidence_r5';o.mkdir(exist_ok=True)
items=[]
def take(src,dst,compress=False):
 p=Path(src)
 if not p.exists():return
 q=o/dst;q.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
 with p.open('rb')as f,(gzip.open(q,'wb',compresslevel=1)if compress else q.open('wb'))as z:
  while b:=f.read(1024*1024):h.update(b);z.write(b)
 items.append(dict(source=str(p),archive=dst,source_bytes=p.stat().st_size,source_sha256=h.hexdigest(),archive_sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
for tag in ['generate_r2','generate_r3','generate_r4','generate_r5']:
 for name in ['generation.log','input.sha256','native32.json.record.json','native32.json.growth.json','parent_binding.json']:
  take(r/tag/name,tag+'/'+name)
for name in ['native32.v','native32_param.v']:take(r/'generate_r5'/name,'source/'+name)
for tag in ['native_parent_r5','native_parent_r5b','native_parent_r5c']:
 for name in ['img0.out','imgh.out','imgh_b3.out']:take(r/tag/name,tag+'/'+name)
 for img in ['img0','imgh','imgh_b3']:
  for n in ['events.txt','rtl.log','report.json','bench.json']:take(r/tag/img/n,tag+'/'+img+'/'+n)
p=Path('safe32_native_synth_out/safe32r5b/work/orfs')
for name in ['native_census_current.json','source_summary.json','1_2_yosys.raw.v','orfs_synth.log','audit_current.log','audit_current_r1_glob_error.log']:
 take(p/name,'native/'+name+'.gz',True)
(o/'index.json').write_text(json.dumps(items,indent=2)+'\n')
