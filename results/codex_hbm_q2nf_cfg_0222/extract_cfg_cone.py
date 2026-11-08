from pathlib import Path
import re,json,collections,sys
r=Path('/srv/opentallas-scratch2/claude/codex-q2nf-0222');src=Path(sys.argv[1]) if len(sys.argv)>1 else r/'kit/rtl/ot_q2nf_rest.sv';lines=src.read_text().split('endmodule',1)[0].splitlines();prefix='u_body.g_q2.n_u_fj.u_fj.u.u_program.'
ports={'step':6,'row':8,'assembly':1536,'metadata':64,'draining':1}
stop={};
for p,w in ports.items():
 for b in range(w):stop['\\'+prefix+p+(''if w==1 else'['+str(b)+']')]=(p,b)
ident=re.compile(r'\\\S+|(?<![\w\'])_[A-Za-z0-9_$]+_')
def ids(t):return [x.rstrip(',}')for x in ident.findall(t)]
drivers={};rhs={};decl={};inline=set()
for i,l in enumerate(lines):
 m=re.match(r'\s*assign\s+(.*?)\s*=\s*(.*);$',l)
 n=re.match(r'\s*(wire|reg)\s*(\[[^\]]+\]\s*)?(\\\S+|_[A-Za-z0-9_$]+_)\s*(?:=\s*(.*))?;$',l)
 if n:
  decl[n[3]]='wire '+(n[2]or'')+n[3]+' ;'
  if n[4]is not None:
   drivers[n[3]]=i;rhs[i]=n[4];inline.add(i)
 if m:
  for x in ids(m[1]):drivers[x]=i
  rhs[i]=m[2]
root=next(re.match(r'\s*else _55059_ <= (.*);',x)[1]for x in lines if re.match(r'\s*else _55059_ <= (.*);',x))
need=set();todo=ids(root);chosen=set();unknown=[];used=set()
while todo:
 n=todo.pop()
 if n in need:continue
 need.add(n)
 if n in stop:used.add(n);continue
 if n not in drivers:unknown.append(n);continue
 i=drivers[n]
 if i not in chosen:chosen.add(i);todo+=ids(rhs[i])
assert not unknown,unknown[:20]
# Include all LHS bits in a multi-output expression so declarations stay legal.
for i in chosen:
 if i not in inline:
  m=re.match(r'\s*assign\s+(.*?)\s*=\s*(.*);$',lines[i]);need.update(ids(m[1]))
out=Path(sys.argv[2]) if len(sys.argv)>2 else r/'cfg_cone';out.mkdir(exist_ok=True)
head='module q2nf_cfg_ref(input[5:0]step,input[7:0]row,input[1535:0]assembly,input[63:0]metadata,input draining,output[36:0]y);\n'
text=[head]
inline_keys={n for n,i in drivers.items()if i in chosen and i in inline}
for n in sorted(need-inline_keys):
 if n in stop:
  p,b=stop[n];text+=['wire '+n+' ;','assign '+n+' = '+p+(''if ports[p]==1 else'['+str(b)+']')+';']
 else:
  assert n in decl,n
  text.append(decl[n])
for i in sorted(chosen):text.append(lines[i])
text+=['assign y = '+root+';','endmodule']
(out/'actual_cfg_ref.sv').write_text('\n'.join(text)+'\n');(out/'census.json').write_text(json.dumps(dict(source=str(src),selected_assignments=len(chosen),all_cone_names=len(need),input_bits_used=len(used),unknown_leaves=unknown),indent=1));print((out/'census.json').read_text())
