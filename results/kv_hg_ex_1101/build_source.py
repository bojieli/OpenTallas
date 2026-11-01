from pathlib import Path
import re,json,shutil
src=Path('/srv/opentallas-scratch2/claude/kit-wave/qwen_kvsys/event28w_c/items/kv3_hg_v1/attempt_3/gen/kv3_hg_v1/rtl')
out=Path('/srv/opentallas-scratch2/claude/codex-kv-hg-ex-1101/source');out.mkdir(exist_ok=True)
files=list(src.glob('*.sv'))+list(src.glob('*.v'));body={};owner={}
for f in files:
 t=re.sub(r'//.*','',f.read_text());t=re.sub(r'/\*.*?\*/','',t,flags=re.S)
 for m in re.finditer(r'\bmodule\s+(\w+)(.*?)\bendmodule\b',t,re.S):body[m[1]]=m[2];owner[m[1]]=f
kw={'module','if','for','case','assign','always','begin','end','else','function','task','wire','reg','logic','input','output','inout','generate','initial','return','localparam','parameter','genvar'}
seen=set();todo=['qkd_astk_ex_s']
while todo:
 n=todo.pop()
 if n in seen:continue
 seen.add(n)
 for m in re.finditer(r'^\s*([A-Za-z_]\w*)\b(?:\s*#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?\s+(?:[A-Za-z_]\w*|\\\S+\s)\s*\(',body.get(n,''),re.M):
  if m[1] not in kw:todo.append(m[1])
missing=seen-owner.keys();assert all(n.endswith("_must_match_LAT") for n in missing),missing
seen &= owner.keys()
selected=sorted({owner[n] for n in seen})
for f in selected:shutil.copy2(f,out/f.name)
for f in src.glob('*.svh'):shutil.copy2(f,out/f.name)
print('LEAF_SOURCE_MODULES',sorted(seen));print('LEAF_SOURCE_FILES',[p.name for p in selected]);print('SOURCE_BYTES',sum(p.stat().st_size for p in selected))
