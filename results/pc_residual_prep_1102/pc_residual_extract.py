import re,json,hashlib
from pathlib import Path
K=Path('/srv/opentallas-scratch2/claude/codex-pc-post-0355');B=K/'run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base';O=Path('/srv/opentallas-scratch2/claude/codex-pc-residual-prep-0510');O.mkdir(exist_ok=True)
text=(B/'6_final.v').read_text();cells={}
for m in re.finditer(r'^\s*(\w+_ASAP7_75t_R)\s+(\\?\S+)\s*\((.*?)\);',text,re.M|re.S):
 cells[m[2].lstrip('\\')]={'master':m[1],'pins':{p:n.strip().lstrip('\\') for p,n in re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)',m[3])}}
selected={'_217823_','_217824_','_307349_','_237314_','_218317_','_242024_','place25707','wire41988','fanout41133','place22725','fanout40107','fanout40106','_297796_','_297797_','_297798_','_265548_','place20828','fanout38367'}
assert selected<=cells.keys(),selected-cells.keys()
nets={c['pins']['Y'] for n,c in cells.items() if n in selected}
conn={n:[] for n in nets}
for n,c in cells.items():
 for p,w in c['pins'].items():
  if w in conn:conn[w].append({'instance':n,'master':c['master'],'pin':p})
need=selected|{x['instance'] for v in conn.values() for x in v};defs={};netdefs={};units=None;active=None;buf=[]
with (B/'6_final.def').open() as f:
 for line in f:
  if 'UNITS DISTANCE MICRONS' in line:units=int(line.split()[-2])
  if line.startswith('- '):
   name=line.split()[1].lstrip('\\');active=('cell' if name in need else 'net' if name in nets else None,name);buf=[line] if active[0] else []
  elif active and active[0]:buf.append(line)
  if active and active[0] and ';' in line:
   (defs if active[0]=='cell' else netdefs)[active[1]]=''.join(buf);active=None;buf=[]
# Resolve selected SPEF name-map names, retaining only exact D_NET sections.
ids={};spef={};take=None;buf=[]
with (B/'6_final.spef').open() as f:
 for l in f:
  m=re.match(r'^(\*\d+)\s+(\S+)\s*$',l)
  if m:
   name=m[2].replace('\\','')
   if name in nets:ids[m[1]]=name
  if l.startswith('*D_NET '):
   n=l.split()[1];name=ids.get(n,n.replace('\\',''));take=name if name in nets else None;buf=[l] if take else []
  elif take:buf.append(l)
  if take and l.startswith('*END'):
   spef[take]=''.join(buf);take=None;buf=[]
positions={}
for n,d in defs.items():
 m=re.search(r'\+ (?:PLACED|FIXED|FIRM) \(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)',d)
 if m:positions[n]={'x':int(m[1])/units,'y':int(m[2])/units,'orient':m[3]}
report={'status':'PASSIVE_NATIVE_EXTRACTION','source':str(K),'selected_cells':{n:cells[n] for n in sorted(selected)},'nets':conn,'positions':positions,'DEF_units':units,'SPEF_sections':sorted(spef),'input_sha256':{p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in []}}
# Streaming hashes avoid copying full physical inputs.
for n in ['6_final.v','6_final.def','6_final.spef']:
 h=hashlib.sha256()
 with (B/n).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 report['input_sha256'][n]=h.hexdigest()
(O/'native_query.json').write_text(json.dumps(report,indent=2)+'\n');(O/'selected_components.def').write_text('\n'.join(defs.values()));(O/'selected_nets.def').write_text('\n'.join(netdefs.values()));(O/'selected_nets.spef').write_text('\n'.join(spef.values()));print(json.dumps({'cells':len(cells),'selected':len(selected),'nets':len(nets),'spef_sections':len(spef),'positions':len(positions)}))
