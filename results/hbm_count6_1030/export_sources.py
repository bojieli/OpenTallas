#!/usr/bin/env python3
"""Six current-native WHOLE masters, actual selected source bodies/parameters. No hard-child stubs."""
import hashlib,json,pathlib,re,sys
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-su-native-1030');sys.path.insert(0,str(W/'tools/die_plan'));import bind_elab as E
A=pathlib.Path('/srv/opentallas-scratch2/claude/die-hbm-31/b31t/asbuilt.json');a=json.load(open(A));base=pathlib.Path(a['base']);idx=E.module_index(a['rtl_roots'],a['files'],str(base));pr=[str(base/f)if not pathlib.Path(f).is_absolute()else f for f in a['prefer']]
J=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-31/b31t/out/asbuilt.json'));facts=json.load(open('/srv/opentallas-scratch2/claude/codex-hbm-bind-1030/current_top_abi_facts.json'))
instances=sys.argv[1:] or ['hb_dbk_NE','vmks_NW0','ctl_NW_p00','wbk_NW','wbc_NW','vmfc_NW'];selected=[];exports={};pack=D/'native';pack.mkdir(exist_ok=True)
def raw_module(p,name):
 text=p.read_text();mask=re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:''.join('\n'if c=='\n'else' 'for c in m[0]),text,flags=re.S)
 m=re.search(r'\bmodule\s+'+re.escape(name)+r'\b',mask);assert m,(p,name);start=m.start();attr=re.search(r'(\(\*(?:(?!\*\)).)*\*\)\s*)$',mask[:start],re.S)
 if attr:start=attr.start()
 end=re.search(r'\bendmodule\b',mask[m.end():]);assert end
 return text[start:m.end()+end.end()]+'\n'
for inst in instances:
 row=next(r for r in facts if r['instance']==inst);top=row['module'];closure={};todo=[top]
 while todo:
  n=todo.pop()
  if n in closure:continue
  f,amb=E.pick(idx,n,pr)
  if f is None:closure[n]={'MISSING':True};continue
  p=pathlib.Path(f);body=E.module_body(p,n);kids=sorted(E.instantiated(body,idx));raw=raw_module(p,n);out=pack/(n+'.sv')
  if out.exists():assert out.read_text()==raw,n
  else:out.write_text(raw)
  r=dict(source=str(p),file_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),module_body_sha256=hashlib.sha256(body.encode()).hexdigest(),export_sha256=hashlib.sha256(raw.encode()).hexdigest(),children=kids)
  closure[n]=r;exports[n]=r;todo.extend(kids)
 ports=J['modules'][top]['ports'];assert set(row['ports'])==set(ports),(inst,set(row['ports'])^set(ports))
 expected={n:dict(direction=ports[n]['direction'],width=width)for n,width in row['ports'].items()}
 params={k:int(v,2)for k,v in row['parameters'].items()};selected.append(dict(instance=inst,module=top,actual_plan=row['plan'],params=params,actual_parameter_bits=row['parameters'],ports=expected,closure=closure,status='SOURCE_READY'if not any(r.get('MISSING')for r in closure.values())else'BLOCKED_MISSING_SOURCE'))
(D/('source_manifest_'+ '_'.join(instances)+'.json' if sys.argv[1:] else 'source_manifest.json')).write_text(json.dumps(dict(status='CURRENT_NATIVE_WHOLE_SOURCE_PREP_NO_PNR_NO_LEC',manifest=str(A),native_defines=a.get('defines',[]),selected=selected,exports=exports),indent=1)+'\n');print('NATIVE_SOURCE',[ (r['instance'],r['module'],r['params'],len(r['closure']),r['status'])for r in selected],flush=True)
