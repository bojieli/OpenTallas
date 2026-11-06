from pathlib import Path
import re,json,hashlib
p=Path(__file__).parent
source=p/'source_readonly.sv'
if not source.exists():source=Path('/srv/opentallas-scratch2/claude/wt/codex-bodyctl-rcp1-1106/rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv')
s0=source.read_text()
assert hashlib.sha256(s0.encode()).hexdigest()=='f732f5b5486b744e0480b9de4833d7d5665b94c5a72117c676c445f76998a318'
lines=[];active=True;stack=[]
for l in s0.splitlines():
 if l.startswith('`ifdef OT_Q3CTL_MUL4_RT'):stack.append(active);active=False;continue
 if stack and l.startswith('`else'):active=stack[-1];continue
 if stack and l.startswith('`endif'):active=stack.pop();continue
 if active:lines.append(l)
s='\n'.join(lines)+'\n';(p/'native_mul4_false.sv').write_text(s)
tok=lambda x:re.findall(r'\\[^\s]+|_\d+_',x)
assigns=list(re.finditer(r'^\s*assign (.*?) = (.*?);$',s,re.M));drivers={}
for i,m in enumerate(assigns):
 for t in tok(m[1]):drivers.setdefault(t,[]).append(i)
decls={}
for l in s.splitlines():
 if re.match(r'^\s*(wire|reg)\s',l):
  ts=tok(l)
  for t in ts:decls[t]=l.strip()
cap={m[1]:m[2] for m in re.finditer(r'^\s*(_\d+_) <= (.*?);$',s,re.M)}
mods=[];manifest={'source_sha256':hashlib.sha256(s0.encode()).hexdigest(),'preprocess':'OT_Q3CTL_MUL4_RT=false only; other directives preserved','fields':{}}
for field,target in [('pb','_237566_'),('pc','_237567_'),('pd','_237568_')]:
 regs={};aliases={}
 for m in assigns:
  names=re.findall(r'u_mul\.'+field+r'\[(\d+)\]\[(\d+)\]',m[1])
  if len(names)==16 and re.fullmatch(r'_\d+_',m[2]):
   indices={int(x[0]) for x in names};assert len(indices)==1
   ix=indices.pop();assert ix not in regs;regs[ix]=m[2];aliases[ix]=m[0].strip()
 assert set(regs)==set(range(7)),regs
 native_D={}
 for ix,r in regs.items():
  pm=[m for m in assigns if re.sub(r'\s+','',m[1])==re.sub(r'\s+','',cap[r])]
  assert len(pm)==1 and ' * ' in pm[0][2],(ix,r,cap[r],pm)
  native_D[ix]=pm[0][2]
 root=cap[target];seen=set();selected=set();stops=set(regs.values())
 def walk(t):
  if t in seen:return
  seen.add(t)
  if t in stops:return
  assert len(drivers.get(t,[]))==1,('unexpected state/unbound/multidriver',field,t,drivers.get(t),decls.get(t))
  idx=drivers[t][0];selected.add(idx)
  for dep in tok(assigns[idx][2]):walk(dep)
 for t in tok(root):walk(t)
 assert seen&stops==stops,(field,seen&stops,stops)
 # Expand declarations to all LHS bits of retained concatenation assignments too.
 allnames=seen|{t for idx in selected for t in tok(assigns[idx][1])}
 assert all(t in decls for t in allnames)
 ports=','.join('input[15:0]p%d'%i for i in range(7))
 text='module actual_'+field+'('+ports+',output[31:0]y);\n'
 text+='\n'.join(sorted({re.sub(r'^reg\b','wire',decls[t]) for t in allnames}))+'\n'
 text+='\n'.join('assign '+r+' = p%d;'%ix for ix,r in sorted(regs.items()))+'\n'
 text+='\n'.join(assigns[i][0].strip() for i in sorted(selected))+'\nassign y = '+root+';\nendmodule\n'
 mods.append(text)
 manifest['fields'][field]={'target':target,'actual_D':root,'product_Q':regs,'native_product_D':native_D,'assign_count':len(selected),'declared_tokens':len(allnames),'unexpected_state_dependencies':[]}
(p/'actual_refs.sv').write_text('\n'.join(mods))
off="{16'd0,p0}+{8'd0,p1,8'd0}+{p2,16'd0}+{p3[7:0],24'd0}+{8'd0,p4,8'd0}+{p5,16'd0}+{p6[7:0],24'd0}"
text='module miter('+','.join('input[15:0]p%d'%i for i in range(7))+',output correct,mutant_correct);wire[31:0]ref='+off+';wire[31:0]pb,pc,pd;\n'
for f in ['pb','pc','pd']:text+='actual_'+f+' u_'+f+'('+','.join('p%d'%i for i in range(7))+','+f+');\n'
text+="assign correct=(pb==ref)&&(pc==ref)&&(pd==ref);assign mutant_correct=((pb^32'h10000)==ref)&&(pc==ref)&&(pd==ref);endmodule\n"
(p/'miter.sv').write_text(text);(p/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2)[:1600])
