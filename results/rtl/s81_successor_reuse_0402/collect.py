from pathlib import Path
import re,shlex,json,hashlib,collections
R=Path('/srv/opentallas-scratch2/claude/codex-ds-archive-reuse-0402')
F=Path('/srv/opentallas-scratch2/claude/codex-ds-service-hier-0340/fs')
anchors={'dsfd_bf_col','dsfd_bf_front_roots','ot_s81sl_xs4','ot_s81sl_xgt_xo','ot_s81sl_xg_xo','ot_rom_4096x274_m8'}
mods=collections.defaultdict(list);file_hashes={};context=[]
comment=re.compile(r'/\*.*?\*/|//[^\n]*',re.S)
module=re.compile(r'\bmodule\s+([a-zA-Z_][\w$]*)\b.*?\bendmodule\b',re.S)
for p in F.rglob('*'):
 if not p.is_file() or p.suffix not in ('.sv','.v','.vh','.svh'):continue
 raw=p.read_bytes();text=raw.decode(errors='replace');clean=comment.sub('',text)
 rel=str(p.relative_to(F));file_hashes[rel]=hashlib.sha256(raw).hexdigest()
 spans=list(module.finditer(clean))
 for m in spans:
  body=m.group();mods[m[1]].append(dict(file=rel,file_sha256=file_hashes[rel],module_sha256=hashlib.sha256(body.encode()).hexdigest(),body=body))
 outside=module.sub('',clean).strip()
 if outside:context.append((rel,hashlib.sha256(outside.encode()).hexdigest()))
known=set(mods);edges={}
for name,variants in mods.items():
 deps=set()
 for v in variants:
  body=re.sub(r'"(?:\\.|[^"\\])*"','',v['body'])
  deps.update(set(re.findall(r'\b[a-zA-Z_][\w$]*\b',body)) & known)
 deps.discard(name);edges[name]=deps

def decode(n):return n.replace('___05F','__')
def closure(n):
 seen=set();todo=[n]
 while todo:
  v=todo.pop()
  if v in seen:continue
  seen.add(v);todo.extend(edges.get(v,())-seen)
 return seen
inv=json.loads((R/'args/archive_inventory.json').read_text());byargs={x['args']:x for x in inv['rows']}
rows=[]
for p in sorted((R/'args').glob('*__hierMkArgs.f')):
 t=shlex.split(p.read_text())
 if '--top-module-encoded' not in t:continue
 key=t[t.index('--top-module-encoded')+1]
 bs=[t[i+1] for i,x in enumerate(t[:-1]) if x=='--hierarchical-block']
 self=[x for x in bs if x.split(',')[1]==key]
 if len(self)!=1:raise ValueError((key,self))
 bits=self[0].split(',');orig=decode(bits[0]);desc=[bits[0],*bits[2:]]
 defs=[x for x in t if x.startswith(('+define+','+undef+','-D','-U'))]
 cl=closure(orig) if orig in mods else set()
 actual_anchors=sorted(cl&anchors)
 selected=[dict(module=n,definitions=[{k:v for k,v in d.items() if k!='body'} for d in mods[n]]) for n in sorted(cl)]
 identity=dict(original_source_type=orig,encoded_parameters=bits[2:],defines=defs,module_definitions=selected)
 digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 archive=byargs[p.name]['archive']
 status='MISSING_ARCHIVE' if not archive else 'UNRESOLVED_SOURCE_TYPE' if not cl else 'REBUILD_BF_XS_NAMESPACE_CLOSURE' if actual_anchors else 'CONDITIONAL_REUSE_EXACT_FRESH_IDENTITY'
 rows.append(dict(class_key=key,source_type=orig,self_hierarchy_option=self[0],parameters=bits[2:],defines=defs,archive=archive,args_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_parameter_identity_sha256=digest,source_closure_modules=sorted(cl),affected_anchor_modules=actual_anchors,status=status))
(R/'module_definitions.json').write_text(json.dumps({n:[{k:v for k,v in d.items() if k!='body'} for d in vs] for n,vs in sorted(mods.items())},indent=2)+'\n')
(R/'archive_reuse.json').write_text(json.dumps(dict(scope='Conservative source graph before coherent successor selection; zero archives adopted',source_snapshot=inv['snapshot_unix'],tool_binary_sha256='dc79ac155e00a73862529b68aa28c498355ea063ce5a2282047ebc30bcfde1ed',source_files=file_hashes,global_preprocessor_context=context,changed_anchors=sorted(anchors),classifications=dict(collections.Counter(x['status'] for x in rows)),archives=rows),indent=2)+'\n')
print(json.dumps(dict(module_types=len(mods),source_files=len(file_hashes),classifications=dict(collections.Counter(x['status'] for x in rows)),unresolved=[x['source_type'] for x in rows if not x['source_closure_modules']]),indent=2))
