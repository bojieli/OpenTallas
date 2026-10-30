import collections,hashlib,json,re,sys
from pathlib import Path
k=Path(sys.argv[1]);scope=json.loads((k/'count_scope.json').read_text()) if (k/'count_scope.json').exists() else {}
t=k.name;p=k/'run/results/asap7'/('dp_'+t)/'base/1_2_yosys_native_metadata.json';j=json.loads(p.read_text());mods=j['modules'];tops=[n for n,m in mods.items() if str(m.get('attributes',{}).get('top','')).endswith('1')];top=t+'_part' if t+'_part' in mods else tops[0]
hards=scope.get('original_physical_children',{}).get('hard_cores',[]);hardnames={h['inst']:h['module'] for h in hards};hc=collections.Counter();std=collections.Counter();macros=collections.Counter();unknown=collections.Counter();ignored=collections.Counter();bad_hard=[]
contents={x.get('inst') for x in scope.get('original_physical_children',{}).get('contents',[])}
owner_prefixes={n:[n] for n in hardnames}
for h in hards:
 note=h.get('note','')
 segment=note.split(':',1)[1].split(';',1)[0] if ':' in note else ''
 members=[v.strip() for v in segment.split('+')]
 if members and all(v in contents for v in members):owner_prefixes[h['inst']]+=members
emitted_aliases={}
bound_text='\n'.join(x.read_text() for x in (k/'rtl').glob('*_bound.sv'))
for h in hards:
 inst=h['inst'];mod=h['module']
 pat=r'(?m)^\s*'+re.escape(mod)+r'\s+(?:#\([^;]*?\)\s*)?('+re.escape(inst)+r'|u_'+re.escape(inst)+r')\s*\('
 matches=sorted(set(re.findall(pat,bound_text)))
 if len(matches)==1:
  owner_prefixes[inst]+=matches
  emitted_aliases[inst]={'declared_module':mod,'actual_emitted_instance':matches[0],'source':'rtl/*_bound.sv'}
patterns={n:[re.compile(r'(?:^|[./])'+re.escape(v)+r'(?:[./]|__|$)') for v in vv] for n,vv in owner_prefixes.items()}
def matching(path):
 return [n for n,qq in patterns.items() if any(q.search(path) for q in qq)]
def walk(n,path,stack=()):
 if '_ASAP7_75t_' in n:
  std[n]+=1;ss=matching(path)
  if len(ss)==1:hc[ss[0]]+=1
  elif len(ss)>1:unknown['overlapping_hard_ownership']+=1
  return
 if n=='$scopeinfo':ignored[n]+=1;return
 m=mods.get(n)
 if m is None:unknown[n]+=1;return
 attrs=m.get('attributes',{});bb=str(attrs.get('blackbox','')).endswith('1')
 if bb:
  macros[n]+=1
  if matching(path) or any(h in n for h in hardnames.values()):bad_hard.append(dict(path=path,module=n))
  return
 if n in stack:unknown['recursive:'+n]+=1;return
 cs=m.get('cells',{})
 if not cs:unknown['empty_nonstandard:'+n]+=1;return
 for q,c in cs.items():walk(c['type'],path+'.'+q if path else q,stack+(n,))
walk(top,'')
complete=not unknown and not bad_hard
allattributed=all(hc[n]>0 for n in hardnames) and complete
out=dict(type=t,complete_native=complete,stdcells=sum(std.values()),std_ff=sum(v for n,v in std.items() if 'DFF' in n),source_total_mapped_leaves=sum(std.values())+sum(macros.values()),external_macro_instances=dict(macros),unknown=dict(unknown),ignored_metadata=dict(ignored),opaque_declared_hardcores=bad_hard,declared_hard_children=hardnames,hard_child_std_counts=dict(hc),validated_plan_member_prefixes=owner_prefixes,parent_physical_residual_std=(sum(std.values())-sum(hc.values())) if allattributed else (sum(std.values()) if not hardnames else None),residual_status='exact actual scope attribution' if allattributed or not hardnames else 'NOT AVAILABLE: complete total must not be treated as soft FF/load or single physical-run size',native_json_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),native_json_path=str(p),top=top,defines='actual GEN VERILOG_DEFINES from config.mk',physical_gates='NOT RUN: SYNTH/count only')
(k/'count_result.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
