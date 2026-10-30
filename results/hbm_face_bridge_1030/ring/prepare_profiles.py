"""Preprocess actual selected source profiles, then extract only reachable preferred modules."""
import json,re,subprocess,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;O=P/'prepared';O.mkdir(exist_ok=True)
x=json.loads((P/'native_source_manifest.json').read_text());rows=x['closure']['rows'];root=x['closure']['root'];receipts={}
def masked(s):return re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',lambda m:''.join('\n'if c=='\n'else' 'for c in m[0]),s,flags=re.S)
def modules(s):
 clean=masked(s);found={}
 for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',clean,re.S):
  assert m[1] not in found,m[1];found[m[1]]=s[m.start():m.end()]
 return found
def preprocess(path,defines,label):
 out=O/f'{label}.pre.sv';cmd=['iverilog','-g2012','-E',*[f'-D{d}'for d in defines],'-I',str(path.parent),'-o',str(out),str(path)]
 r=subprocess.run(cmd,text=True,capture_output=True);(O/f'{label}.pre.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(f'preprocessing failed {path}: {r.stderr}')
 return modules(out.read_text())
cache={};native={};todo=[root]
while todo:
 name=todo.pop()
 if name in native:continue
 if name not in rows:raise ValueError('missing preferred module '+name)
 src=rows[name]['source'];path=P/'native_sources'/x['files'][src]
 if src not in cache:cache[src]=preprocess(path,[*x['closure']['defines'],'SYNTHESIS'],f'native_{len(cache)}')
 text=cache[src][name];native[name]=text;clean=masked(text)
 for child in rows:
  if child!=name and re.search(r'\b'+re.escape(child)+r'\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()',clean):todo.append(child)
physical={}
for i,p in enumerate(sorted((P/'physical_rtl').glob('*.sv'))):
 for n,t in preprocess(p,['SYNTHESIS'],f'physical_{i}').items():
  assert n not in physical,n;physical[n]=t
used={};todo=[root]
while todo:
 name=todo.pop()
 if name in used:continue
 text=physical[name];used[name]=text;clean=masked(text)
 for child in physical:
  if child!=name and re.search(r'\b'+re.escape(child)+r'\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()',clean):todo.append(child)
for label,mods in [('native',native),('physical',used)]:
 text='\n'.join(mods.values())
 for name in sorted(mods,key=len,reverse=True):text=re.sub(r'\b'+re.escape(name)+r'\b',label+'_'+name,text)
 (O/f'{label}.sv').write_text(text+'\n');receipts[label]={'modules':list(mods),'sha256':hashlib.sha256(text.encode()).hexdigest()}
receipts['source_profile_defines']={'native':[*x['closure']['defines'],'SYNTHESIS'],'physical':['SYNTHESIS']}
(O/'selected_modules.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('USED_NATIVE',len(native),list(native));print('USED_PHYSICAL',len(used),list(used))
