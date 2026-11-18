import io,json,hashlib,tarfile,sys
from pathlib import Path
run=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4')
man=run/'asbuilt_run.json';original=man.read_bytes();a=json.loads(original);base=Path(a['base']);files={};mapping={}
def remap(v):
 if isinstance(v,dict):return {k:remap(x) for k,x in v.items() if k!='base'}
 if isinstance(v,list):return [remap(x) for x in v]
 if isinstance(v,str) and '\n' not in v and len(v)<4096:
  q=Path(v);p=q if q.is_absolute() else base/q
  if p.is_file():
   rel=p.relative_to(base).as_posix() if p.is_relative_to(base) else 'ext'+p.as_posix()
   files[rel]=p;mapping[v]={'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()};return rel
 return v
out=remap(a);out['base']='../../../..'
for pat in ['results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_h*_schedule.json','rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h*_l4_lp_plan_map.json','rtl/dsrom_sys/s81_dv/frame_lp/vgcs/col_h*_l4_lp_rf3r.sv']:
 for p in base.glob(pat):files[p.relative_to(base).as_posix()]=p
receipt={'schema':'opentallas.token.actual-source-closure.v1','source_manifest':str(man),'source_manifest_sha256':hashlib.sha256(original).hexdigest(),'base':str(base),'mapping':mapping,'file_count':len(files),'bytes':sum(p.stat().st_size for p in files.values())}
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for rel,p in sorted(files.items()):t.add(p,arcname=rel,recursive=False)
 for name,data in [('physical/die_plan/s81/bind/frame_asbuilt.json',json.dumps(out,indent=1).encode()),('source_asbuilt_original.json',original),('source_closure.json',json.dumps(receipt,indent=1).encode())]:
  info=tarfile.TarInfo(name);info.size=len(data);t.addfile(info,io.BytesIO(data))
 t.add('/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4.json',arcname='selected_plan.json')
