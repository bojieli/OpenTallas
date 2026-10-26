#!/usr/bin/env python3
"""Candidate-only native RR -> A0 clock-fold bridge. No stages, source/view adoption, or physical timing credit."""
import argparse,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
def preprocess(text,defines):
 active=True;stack=[];out=[]
 for line in text.splitlines():
  m=re.match(r'\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w+)?',line)
  if not m:
   if active:out.append(line)
   continue
  d,n=m.groups()
  if d in ('ifdef','ifndef'):
   c=(n in defines)==(d=='ifdef');stack.append([active,c]);active=active and c
  elif d=='elsif':
   parent,taken=stack[-1];c=n in defines;active=parent and not taken and c;stack[-1][1]=taken or c
  elif d=='else':
   parent,taken=stack[-1];active=parent and not taken;stack[-1][1]=True
  else:active=stack.pop()[0]
 return '\n'.join(out)
def ports(text,defines):
 header=preprocess(text,defines).partition('\n);')[0];header=re.sub(r'//[^\n]*','',header)
 return {n:(d,int(a)-int(b)+1 if a else 1) for d,a,b,n in re.findall(r'(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',header)}
def clock(n):return n=='ck' or n.startswith('ck_')
def norm(t):return re.sub(r'\s+','',re.sub(r'//[^\n]*|/\*.*?\*/','',t,flags=re.S))
def main():
 p=argparse.ArgumentParser();p.add_argument('input',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--receipt',type=pathlib.Path,required=True);p.add_argument('--negative-drop-clock',action='store_true');a=p.parse_args()
 src=a.input.read_text();profiles={}
 for k in ('nk','nl'):
  spec=json.loads((ROOT/f'tools/qwen_romleaf/a0core/specs/qfd_tile_{k}_a0cv8.json').read_text());defs=(set(spec['defines'])-{'OT_QWEN_LSL_FP1'})|{'SYNTHESIS'}
  rr=(ROOT/f'rtl/physical/a0_rc14_selected_2000/qfd_tile_{k}_rp2_romleaf_rr.sv').read_text();physical=(ROOT/f'rtl/physical/a0_core/qfd_tile_{k}_a0c.sv').read_text();np=ports(rr,defs);pp=ports(physical,defs)
  nd={n:v for n,v in np.items()if not clock(n)};pd={n:v for n,v in pp.items()if not clock(n)}
  if nd!=pd:raise SystemExit(f'DATA_ABI_FAIL {k} {nd} != {pd}')
  rb=rr.partition('\n);\n')[2];pb=physical.partition('\n);\n')[2];pb=re.sub(r'^\s*wire ck_\w+ = ck;\s*$','',pb,flags=re.M)
  if norm(rb)!=norm(pb):raise SystemExit(f'BODY_FAIL {k}')
  for param,value in [('REGROOT_MODE',3),('G4_ROOTS',1)]:
   if not re.search(r'parameter integer '+param+r'\s*=\s*'+str(value)+r'\b',rr):raise SystemExit('PROFILE_DEFAULT_FAIL '+k)
  profiles[k]={'native':np,'physical':pp,'data':nd,'body_sha256':hashlib.sha256(norm(rb).encode()).hexdigest(),'defines':sorted(defs)}
 records=[];replacement=[]
 pattern=re.compile(r'\bqfd_tile_(nk|nl)_rp2_romleaf_rr\s+(\w+)\s*\((.*?)\);',re.S)
 def fix(m):
  k,inst,body=m.groups();profile=profiles[k];pairs=re.findall(r'\.(\w+)\s*\(([^()]*)\)',body);conn=dict(pairs)
  if len(conn)!=len(pairs) or set(conn)!=set(profile['native']):raise SystemExit(f'NATIVE_PORT_FAIL {inst} missing={set(profile["native"])-set(conn)} extra={set(conn)-set(profile["native"])}')
  clocks={conn[n].strip()for n in profile['native']if clock(n)}
  if len(clocks)!=1 or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',next(iter(clocks))):raise SystemExit(f'COMMON_CLOCK_FAIL {inst} {clocks}')
  rootclk=next(iter(clocks));new={n:(rootclk if clock(n)else conn[n])for n in profile['physical']}
  if a.negative_drop_clock:new.pop(next(n for n in new if clock(n)and n!='ck'))
  if set(new)!=set(profile['physical']):raise SystemExit(f'PHYSICAL_CLOCK_BIND_FAIL {inst} missing={sorted(set(profile["physical"])-set(new))}')
  if any(new[n]!=conn[n]for n in profile['data']):raise SystemExit('DATA_BIND_FAIL '+inst)
  text=f'qfd_tile_{k}_a0c {inst} (\n'+',\n'.join(f'        .{n}({v})'for n,v in new.items())+'\n    );'
  replacement.append((m.group(0),text));records.append({'inst':inst,'kind':k,'native_clock_count':sum(map(clock,profile['native'])),'physical_clock_count':sum(map(clock,profile['physical'])),'common_clock_net':rootclk,'functional_bindings':{n:new[n]for n in profile['data']},'physical_clock_bindings':{n:new[n]for n in new if clock(n)},'cycles_added':0,'physical_view_status':'MISSING: new MODE3/noFP1 exact source trial view still required'})
  return text
 out=pattern.sub(fix,src)
 if not records:raise SystemExit('NO_NATIVE_RR_INSTANCES')
 old_rest=src;new_rest=out
 for old,new in replacement:old_rest=old_rest.replace(old,'__A0_INSTANCE__',1);new_rest=new_rest.replace(new,'__A0_INSTANCE__',1)
 if old_rest!=new_rest:raise SystemExit('OUTSIDE_INSTANCE_CHANGED: pads/control must stay byte-identical')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(out);a.receipt.write_text(json.dumps({'status':'SOURCE_BRIDGE_PASS, CANDIDATE ONLY, not a physical view','input':str(a.input),'input_sha256':hashlib.sha256(src.encode()).hexdigest(),'output_sha256':hashlib.sha256(out.encode()).hexdigest(),'outside_instance_bytes_unchanged':True,'instances':records,'physical_dependency':'Actual MODE3/noFP1 A0c42/41 view with real current-source geometry/clock contract. No MODE9/FP1 rename. Native/flop-to-tap ownership still physical proof.','profiles':{k:{'body_sha256':v['body_sha256'],'defines':v['defines'],'data_abi':v['data']}for k,v in profiles.items()}},indent=2)+'\n')
 print('SOURCE_BRIDGE_PASS',len(records),'instances; outside/pad bytes unchanged; physical view still MISSING')
if __name__=='__main__':main()
