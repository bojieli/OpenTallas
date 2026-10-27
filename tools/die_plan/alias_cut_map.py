#!/usr/bin/env python3
"""Map current split wrapper pins to real parent-elaboration bit aliases.

Body: --mode body --wrapper BODY.sv --top NAME (u_x raw ports are original
hierarchical signal names). Ring/reduce: --mode primitive --wrapper PLAN.sv
--top PLAN --canonical CORE.sv --canonical-top CORE --primitive u_ring|u_reduce
--gold-path u_dut.u_body.u_ring|u_reduce. Only actual pure wire assignments and
instance connections are followed; unsupported logic or missing aliases fails.
No old packed-vector offsets or name-suffix correspondence is used.
"""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_b2'))
from b2_top import parse_expr


class UF:
 def __init__(self):self.p={}
 def root(self,x):
  if x not in self.p:self.p[x]=x
  path=[];r=x
  while self.p[r]!=r:path.append(r);r=self.p[r]
  for n in path:self.p[n]=r
  return r
 def join(self,a,b):
  a,b=self.root(a),self.root(b)
  if a!=b:
   if b[0]=='constant':a,b=b,a
   self.p[b]=a


def module(path,name):
 text=Path(path).read_text();m=re.search(r'(?ms)^module\s+'+re.escape(name)+r'\s*\(.*?^endmodule',text)
 if not m:raise ValueError('literal module missing: '+name)
 return re.sub(r'//[^\n]*','',m[0])


def decls(text):
 widths={};ports={}
 for m in re.finditer(r'\b(input|output|inout|wire)\s+(?:wire\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s*)?([A-Za-z_]\w*)\s*(?=[,;)\n])',text):
  kind,hi,lo,n=m.groups();lo,hi=(int(lo),int(hi)) if hi else (0,0)
  widths[n]=(lo,hi)
  if kind!='wire':ports[n]=dict(direction=kind,bits=list(range(lo,hi+1)))
 return widths,ports


def expr(e,widths,scope):
 out=[]
 for s in parse_expr(e,widths):
  if s[0]=='n':out.extend((scope,s[1],k) for k in range(s[2],s[3]+1))
  else:
   if not isinstance(s[2],int):raise ValueError('unknown constant in wire adapter: '+e)
   out.extend(('constant',(s[2]>>k)&1) for k in range(s[1]))
 return out


def assigns(text,widths,scope,uf):
 for m in re.finditer(r'\bassign\s+(.*?)\s*=\s*(.*?);',text,re.S):
  a,b=expr(m[1],widths,scope),expr(m[2],widths,scope)
  if len(a)!=len(b):raise ValueError('wire assignment width mismatch')
  for x,y in zip(a,b):uf.join(x,y)


def instance(text,name):
 m=re.search(r'\b'+re.escape(name)+r'\s*\((.*?)\);',text,re.S)
 if not m:raise ValueError('instance missing: '+name)
 out={}
 for c in re.finditer(r'\.(\\\S+\s|[A-Za-z_]\w*)\s*\((.*?)\)\s*(?:,|$)',m[1],re.S):out[c[1].strip().lstrip('\\')]=c[2].strip()
 return out


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--mode',choices=['body','primitive'],required=True);ap.add_argument('--wrapper',required=True);ap.add_argument('--top',required=True);ap.add_argument('--canonical');ap.add_argument('--canonical-top');ap.add_argument('--primitive');ap.add_argument('--gold-path');ap.add_argument('--parent-wrapper',required=True);ap.add_argument('--parent-instance',default='u_dut');ap.add_argument('--gold',required=True);ap.add_argument('--gold-prefix',default='u_dut.');ap.add_argument('--nlink',type=int,required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 if Path(a.out).exists():raise ValueError('refusing existing output')
 gold=json.load(open(a.gold));nets=gold['netnames'];w=module(a.wrapper,a.top);ww,wp=decls(w);uf=UF();assigns(w,ww,'plan',uf);associations=collections.defaultdict(set);failed=[]
 def alias(name,k,vector=False):
  full=a.gold_prefix+name
  if full in nets:
   bs=nets[full]['bits']
   if k>=len(bs):raise ValueError('alias bit outside actual parent vector: '+full)
   return bs[k]
  m=re.fullmatch(r'(.*)\[(\d+)\]',name)
  if m and a.gold_prefix+m[1] in nets:
   if k!=0:raise ValueError('split scalar alias unexpectedly vector')
   return nets[a.gold_prefix+m[1]]['bits'][int(m[2])]
  raise ValueError('actual parent alias absent: '+full)
 if a.mode=='body':
  for raw,e in instance(w,'u_x').items():
   for k,wire in enumerate(expr(e,ww,'plan')):
    if wire[0]=='constant':continue  # literal padding has no physical input endpoint
    try:associations[wire].add(alias(raw,k))
    except (ValueError,IndexError) as err:failed.append(dict(raw=raw,bit=k,reason=str(err)))
 else:
  c=module(a.canonical,a.canonical_top);cw,cp=decls(c);assigns(c,cw,'canonical',uf)
  for port,e in instance(w,'u_core').items():
   if port not in cp:raise ValueError('canonical port absent: '+port)
   pb=expr(e,ww,'plan');cb=[('canonical',port,k) for k in cp[port]['bits']]
   if len(pb)!=len(cb):raise ValueError('canonical wrapper connection width mismatch: '+port)
   for x,y in zip(pb,cb):uf.join(x,y)
  for port,e in instance(c,a.primitive).items():
   name=a.gold_path+'.'+port
   for k,wire in enumerate(expr(e,cw,'canonical')):
    if name not in nets:failed.append(dict(primitive_port=port,reason='actual primitive alias absent: '+name));continue
    if k>=len(nets[name]['bits']):failed.append(dict(primitive_port=port,bit=k,reason='actual primitive alias shorter'));continue
    associations[wire].add(nets[name]['bits'][k])
 collapsed=collections.defaultdict(set)
 for wire,ids in associations.items():collapsed[uf.root(wire)].update(ids)
 for wire in list(uf.p):
  if wire[0]=='constant':collapsed[uf.root(wire)].add(str(wire[1]))
 ports={};directions={}
 for port,desc in wp.items():
  ids=[];bad=False
  for k in desc['bits']:
   matched=collapsed.get(uf.root(('plan',port,k)),set())
   if len(matched)!=1:failed.append(dict(port=port,bit=k,reason=f'actual parent aliases have {len(matched)} distinct bit identities'));bad=True;break
   ids.append(next(iter(matched)))
  if not bad:ports[port]=ids;directions[port]=desc['direction']
 sources={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [a.wrapper,a.parent_wrapper]+([a.canonical] if a.canonical else [])}
 out=dict(schema='opentallas.current_parent_cut_alias.v1',module=a.top,variant=dict(nlink=a.nlink),parent_alias_source=True,gold_source=gold['source'],gold_source_sha256=gold['source_sha256'],sources=sources,parent_public_ports={p:nets[a.gold_prefix+p]['bits'] for p in instance(Path(a.parent_wrapper).read_text(),a.parent_instance) if a.gold_prefix+p in nets},parent_alias_bits=ports,directions=directions,failed=failed,verdict='FAIL' if failed else 'PASS',scope='Actual current parent alias bit identities via exact pure-wire wrappers. No literal old ND/NPT offsets; source composition/latency qualification remains separate.')
 Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(a.top,out['verdict'],'mapped_ports',len(ports),'pin_bits',sum(map(len,ports.values())),'failed',len(failed));return bool(failed)
if __name__=='__main__':sys.exit(main())
