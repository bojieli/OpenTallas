import sys,json,importlib.util
from pathlib import Path
r,out=map(Path,sys.argv[1:3]);mut=int(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('S',r/'tools/qwen_split/sys_face_image.py');S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
m=json.loads((r/'results/arch/sysface_sram_players_1019/cold_manifest.json').read_text())
w=[dict(x) for x in m['face_prefix_cfg_writes']]+[dict(target=4,addr=0,data=S.entry(2,1,1,0,0)),dict(target=4,addr=1,data=S.entry(2,1,1,0,0)),dict(target=6,addr=0,data=20000)]
if mut==1:
 for x in w:
  if x['target']==5 and x['addr']==128:x['data']=0
if mut==2:
 for x in w:
  if x['target']==3 and x['addr']==47:x['data']|=32
programme=S.bench_program();rows={i:x for i,x in enumerate(programme)}
for k,x in enumerate(w):rows[S.BOOT_BASE+k]=(x['target']<<68)|(x['addr']<<60)|x['data']
rows[S.BOOT_BASE+len(w)]=15<<68
(out/'sys_face_cfg.viamap.hex').write_text(S.viamap(rows))
(out/'program.memh').write_text(''.join(f'{x:016x}\n' for x in programme))
(out/'cfg_writes.memh').write_text(''.join(f"{x['target']:x}{x['addr']:02x}{x['data']:08x}\n" for x in w))
# Steady D2D lists are not executed by this scoped selector bench.
for n in ['tx','rx']:(out/f'ovl_c_{n}.viamap.hex').write_text('0'*144+'\n')
