#!/usr/bin/env python3
"""Actual-source control-calendar transcription. No ROM data, HDL compiler or arithmetic.
Full NP8192/R128/NBF1024 metadata uses the runtime image source with only the
weight-word materialization loop removed. Every shape/resource remains full.
"""
import ast,collections,hashlib,inspect,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_runtime_v41_die_images as I
import v41_rom_ksplit_bankmap as S
NP,R,NBF=8192,128,1024
LAT=8
def sha(b):return hashlib.sha256(b).hexdigest()
def metadata(fmt,rows,K,active=8192):
 # Strip only ROM payload materialization, preserving original config/fill/class/
 # capacity/placement/round/beat and phase metadata operations byte-source-pinned.
 tree=ast.parse(inspect.getsource(I.add_phase));removed=[]
 class PayloadOnly(ast.NodeTransformer):
  def visit_For(self,node):
   if isinstance(node.target,ast.Name) and node.target.id=='mb':
    removed.append(ast.unparse(node));return None
   return self.generic_visit(node)
 tree=PayloadOnly().visit(tree);ast.fix_missing_locations(tree)
 assert len(removed)==1 and 'field.words' not in ast.unparse(tree) and 'block_word' in removed[0]
 ns=dict(vars(I));exec(compile(tree,'<pinned_metadata_without_ROM_payload>','exec'),ns)
 f=I.Field(NP,R,NBF,active=active);m=SimpleNamespace(name='immutable_metadata_'+fmt,fmt=fmt,rows=rows,K=K,r0=0,k0=0)
 ph=ns['add_phase'](f,[m]);segs,_,_=I._place(I.Field(NP,R,NBF,active=active),[m])
 return f,ph,segs,{'source_sha256':sha(inspect.getsource(I.add_phase).encode()),'excluded_payload_loop_sha256':sha(removed[0].encode()),'metadata_only':True}
def pair_issue(ps,beats,positions=1,bf=False,XF=4):
 words=[];needs=[];seen=set();qcnt={}
 for pos in range(positions):
  for i,u,b,h in S.element_order(ps):
   sg=ps[i];u0,_=S.unit_range(sg['fmt'],sg['e0'],sg['elems']);q=(u-u0)//8
   pk=(pos,q,b,u0,u);rnd=(pos,q,b);slot=qcnt.get(rnd,0);qcnt[rnd]=slot+1
   if pk not in seen:needs.append(pk);seen.add(pk)
   words.append((pk,slot,i,u,b,h,pos))
 # Each needs item is one class/unit x-slice; all its words share one FIFOentry.
 pushed=collections.defaultdict(list);want=0;bn_ready=0
 for pos in range(positions):
  for bi,v in enumerate(beats):
   t=4+pos*len(beats)+bi
   if not v or want==len(needs):continue
   p,q,b,base,u=needs[want]
   units=[(v>>(8+8*k))&255 for k in range(4) if (v>>(4+k))&1] if bf else [(v>>1)&255]
   b_in=(v>>1)&7 if bf else (v>>9)&7
   if p!=pos or b!=b_in or (bf and t<bn_ready):continue
   captured=[]
   while want<len(needs):
    n=needs[want]
    if n[0]!=pos or n[1]!=q or n[2]!=b or n[4] not in units:break
    captured.append(n);want+=1
    if not bf:break
   if captured:
    pushed[t+2]+=captured
    if bf and (want==len(needs) or needs[want][:3]!=(p,q,b)):bn_ready=t+2
 if want!=len(needs):raise ValueError(('CAPTURE_CALENDAR_INCOMPLETE',want,len(needs),needs[want]))
 fifo=collections.deque();last_slot={};wi=0;t=0;last_issue=-100;last_bank=None;addr=0;maxfifo=0;issues=[];overflow=[]
 limit=4+positions*len(beats)+len(words)*LAT+256
 while wi<len(words) or t<=max(pushed,default=0):
  if t>limit:raise ValueError('issue timeout')
  pop=False
  if wi<len(words) and fifo:
   pk,slot,i,u,b,h,pos=words[wi]
   if fifo[0]!=pk:raise ValueError(('FIFO_CLASS_ORDER_DIFF',fifo[0],pk))
   if wi==0 or words[wi-1][-1]!=pos:addr=0
   hazard=t-last_slot.get(slot,-100)<LAT
   bank=addr&1;ppblock=last_issue==t-1 and last_bank==bank
   if not hazard and not ppblock:
    issues.append((t,i,u,b,h,pos,slot));last_slot[slot]=t;last_issue=t;last_bank=bank;addr+=1;wi+=1
    pop=wi==len(words) or words[wi][0]!=pk
  old=len(fifo);incoming=pushed.get(t,[])
  if old+len(incoming)>XF+int(pop):overflow.append({'t':t,'old':old,'push':len(incoming),'pop':pop})
  if pop:fifo.popleft()
  fifo.extend(incoming);maxfifo=max(maxfifo,len(fifo));t+=1
 return issues,{'peak_XFIFO':maxfifo,'overflow':overflow,'last_issue':issues[-1][0] if issues else None,'last_capture_push':max(pushed,default=None),'words':len(words),'captured_slices':len(needs)}
class Segment:
 def __init__(self):
  self.q=collections.deque();self.have={};self.infl=collections.Counter();self.tpos={};self.x=None;self.results={};self.peak=0;self.outputs=[];self.faults=[]
 def step(self,t,incoming):
  # Old registered result priority, old FIFOhead. x decision reads current held
  # state; incoming data writes at this edge cannot be selected at the same edge.
  result=self.results.pop(t,None)
  e=result if result is not None else (self.q[0] if self.q else None)
  fromadd=result is not None
  if result is None and self.q:self.q.popleft();self.tpos[e[0]]=e[4]
  oldx=self.x;self.x=None
  if e:
   tree,level,final,expr,pos=e
   self.x=(tree,level,final,expr,self.tpos.get(tree,pos),fromadd)
  if oldx:
   tree,l,final,expr,pos,xadd=oldx;key=(tree,l);held=self.have.get(key)
   above=any(tr==tree and lev>l for tr,lev in self.have)
   idle=self.infl[tree]==int(xadd)
   early=final and held is None and not above and idle
   top=l==5 or early
   if top:
    if l==5 and not final:self.faults.append(('LV_NONFINAL',t,tree))
    self.outputs.append((t+1,tree,pos,expr)) # o_v consumes t_v on followingedge
   elif held is not None or final:
    expr=(held,expr) if held is not None else expr # +0 padding identity only
    self.have.pop(key,None)
    self.results[t+LAT+2]=(tree,l+1,final,expr,pos)
    self.infl[tree]+=1
   else:self.have[key]=expr
   if xadd:self.infl[tree]-=1
  old=len(self.q)
  if incoming is not None:
   if old==8:self.faults.append(('QD_OVERFLOW',t))
   self.q.append(incoming)
  self.peak=max(self.peak,len(self.q))
 def pending(self):return bool(self.q or self.x or self.results)
def pair_leaves(ps,issues):
 # Producer availability vs consumer capture: issueN -> PP consumerN+3;
 # q bterm11 + chain inputreg1/LAT8 + pair LAT8 => baseenqueueN+31.
 # BF boundary1+mul5+chaininputreg1/LAT8+four LAT8tree => baseenqueueN+50.
 finals={i:S.segment_order(sg['fmt'],sg['e0'],sg['elems'])[-1] for i,sg in enumerate(ps)}
 slot_by_i={};cls={}
 for i,sg in enumerate(ps):cls.setdefault(S.unit_range(sg['fmt'],sg['e0'],sg['elems']),[]).append(i)
 order=[]
 for key in sorted(cls):order+=sorted(cls[key],key=lambda j:(ps[j]['fmt'],ps[j]['row'],ps[j]['mi']))
 slot_by_i={i:k for k,i in enumerate(order)}
 inputs={}
 for t,i,u,b,h,pos,slot in issues:
  if b!=7:continue
  sg=ps[i];tree=slot_by_i[i]+8*(pos&1);final=(u,b,h)==finals[i];offset=50 if sg['fmt']=='bf16' else 31
  when=t+offset
  if when in inputs:raise ValueError('basecollision')
  inputs[when]=(tree,0,final,('base',i,u,h,pos),pos)
 s=Segment();t=0;limit=max(inputs,default=0)+4096
 while t<=max(inputs,default=0) or s.pending():
  if t>limit:raise ValueError('segment drain timeout')
  s.step(t,inputs.get(t));t+=1
 leaves=[]
 inv={v:k for k,v in slot_by_i.items()}
 for t,tree,pos,expr in s.outputs:
  i=inv[tree%8];sg=ps[i]
  for mb in (0,1):
   row=2*sg['row']+mb
   # Caller supplies one-matrix sourcecase; allactive rows verified below.
   leaves.append((t,mb,(pos,row,sg['seg'],0,sg['nseg']),expr))
 return leaves,{'peak_segment_Q':s.peak,'faults':s.faults,'held_at_end':len(s.have),'inflight_at_end':sum(s.infl.values()),'base_events':len(inputs)}
def norm(tag):
 pos,row,lo,k,n=tag
 for _ in range(5):
  if not(lo==0 and 1<<k>=n) and not((lo>>k)&1) and lo+(1<<k)>=n:k=(k+1)&7
 return pos,row,lo,k,n
def complete(t):return t[2]==0 and 1<<t[3]>=t[4]
def siblings(a,b):return a[:2]==b[:2] and a[3:]==b[3:] and a[2]^b[2]==1<<a[3]
def parent(a,b):return norm((a[0],a[1],min(a[2],b[2]),a[3]+1,a[4]))
class ReturnNode:
 def __init__(self):self.q=[collections.deque(),collections.deque()];self.age=[0,0];self.addcycles=set();self.peak=[0,0];self.faults=[]
 def step(self,t,arrivals):
  a=self.q[0][0] if self.q[0] else None;b=self.q[1][0] if self.q[1] else None
  add=a is not None and b is not None and siblings(a[0],b[0]);free=t-4 not in self.addcycles
  fa=not add and a is not None and free and (complete(a[0]) or b is not None or self.age[0]>=2 or len(self.q[0])==64)
  fb=not add and not fa and b is not None and free and (complete(b[0]) or self.age[0]>=2 or self.age[1]>=2 or len(self.q[1])==64)
  output=None
  if add:
   left,right=sorted((a,b),key=lambda x:x[0][2]);output=(t+5,(parent(a[0],b[0]),(left[1],right[1])));self.addcycles.add(t)
  elif fa or fb:output=(t+1,a if fa else b)
  for side,pop in enumerate((add or fa,add or fb)):
   old=len(self.q[side]);v=arrivals.get(side)
   if v is not None and old==64 and not pop:self.faults.append((t,side,'FIFO_OVERFLOW'))
   self.age[side]=0 if pop or not old else min(31,self.age[side]+1)
   if pop:self.q[side].popleft()
   if v is not None:self.q[side].append((norm(v[0]),v[1]))
   self.peak[side]=max(self.peak[side],len(self.q[side]))
  self.addcycles={x for x in self.addcycles if x>=t-4}
  return output
class ReturnRoot:
 def __init__(self):self.q=collections.deque();self.buf={};self.results={};self.peakq=0;self.peakbuf=0;self.faults=[];self.rows=[]
 def step(self,t,arrivals):
  result=self.results.pop(t,None);candidate=result if result is not None else (self.q[0] if self.q else None)
  if result is None and self.q:self.q.popleft()
  if candidate:
   tag,expr=candidate;tag=norm(tag)
   if complete(tag):self.rows.append((t,tag,expr))
   else:
    hits=[i for i,x in self.buf.items() if siblings(x[0],tag)]
    if hits:
     other=self.buf.pop(min(hits));left,right=sorted((other,(tag,expr)),key=lambda x:x[0][2]);self.results[t+6]=(parent(other[0],tag),(left[1],right[1]))
    else:
     free=[i for i in range(128) if i not in self.buf]
     if not free:self.faults.append((t,'ROOT_BUFFER_OVERFLOW'))
     else:self.buf[min(free)]=(tag,expr)
  if arrivals:
   if len(self.q)==128:self.faults.append((t,'ROOT_Q_OVERFLOW'))
   self.q.append(arrivals)
  self.peakq=max(self.peakq,len(self.q));self.peakbuf=max(self.peakbuf,len(self.buf))
def full_return(leaves):
 # Allocate every source node and root, no smaller return surrogate.
 levels=[[ReturnNode() for _ in range(16384>>(l+1))] for l in range(7)];roots=[ReturnRoot() for _ in range(128)]
 events=collections.defaultdict(dict);active=set();rootactive=set();outputs=[]
 for t,leaf,tag,expr in leaves:
  key=(0,leaf//2);events[t+1].setdefault(key,{})[leaf%2]=(tag,expr)
 lastleaf=max((x[0] for x in leaves),default=0);t=0
 while events or active or rootactive:
  if t>lastleaf+100000:raise ValueError('return timeout')
  incoming=events.pop(t,{})
  for k in incoming:
   if k[0]==7:rootactive.add(k[1])
   else:active.add(k)
  for l,g in sorted(active):
   n=levels[l][g];out=n.step(t,incoming.get((l,g),{}))
   if out:
    at,v=out;key=(l+1,g//2) if l<6 else (7,g);side=g%2 if l<6 else 0
    bucket=events[at+1].setdefault(key,{})
    if side in bucket:raise ValueError(('OUTPUT_COLLISION',at,key))
    bucket[side]=v
  active={k for k in active if any(levels[k[0]][k[1]].q)}
  for g in sorted(rootactive):
   root=roots[g];root.step(t,incoming.get((7,g),{}).get(0))
  rootactive={g for g in rootactive if roots[g].q or roots[g].results}
  t+=1
 return roots,{'nodes':sum(len(x) for x in levels),'roots':len(roots),'peak_node_queues_by_level':[max(max(n.peak) for n in lv) for lv in levels],'node_faults':[(l,g,n.faults) for l,lv in enumerate(levels) for g,n in enumerate(lv) if n.faults],'peak_root_Q':max(r.peakq for r in roots),'peak_root_buffer':max(r.peakbuf for r in roots),'root_faults':[(g,r.faults) for g,r in enumerate(roots) if r.faults],'root_held_end':sum(len(r.buf) for r in roots),'retired_rows':sum(len(r.rows) for r in roots),'last_leaf':lastleaf,'last_root_retire':max((x[0] for r in roots for x in r.rows),default=None),'calendar_terminal':t}
def case(fmt,rows,K,positions=1,active=8192):
 f,ph,segs,source=metadata(fmt,rows,K,active);by=collections.defaultdict(list)
 for sg in segs:by[sg['pair']].append(sg)
 all_leaves=[];pair_records=[];gold_tokens=collections.defaultdict(list)
 for p,ps in sorted(by.items()):
  issues,w=pair_issue(ps,f.stream,positions,bf=fmt=='bf16',XF=8 if f.bf[p] else 4)
  leaves,s=pair_leaves(ps,issues)
  for i,sg in enumerate(ps):
   for u,b,h in S.segment_order(sg['fmt'],sg['e0'],sg['elems']):
    if b!=7:continue
    for pos in range(positions):
     for mb in (0,1):
      row=2*sg['row']+mb
      if row<rows:gold_tokens[pos,row].append((u,h,('base',i,u,h,pos)))
  for t,mb,tag,expr in leaves:
   if tag[1]<rows and tag[1]<32768:all_leaves.append((t,2*p+mb,tag,expr))
  pair_records.append({'pair':p,**w,**s,'last_leaf':max((x[0] for x in leaves),default=None),'last_walk_busy_bound':w['last_issue']+3 if w['last_issue'] is not None else None})
 roots,ret=full_return(all_leaves)
 retired=[(tag[0],tag[1]) for r in roots for t,tag,expr in r.rows]
 expected={(p,row) for p in range(positions) for row in range(rows)}
 def golden(a):
  if len(a)==1:return a[0]
  mid=len(a)//2;left=golden(a[:mid]);right=golden(a[mid:])
  return left if right is None else (right if left is None else (left,right))
 gold={}
 for key,tokens in gold_tokens.items():
  a=[x[2] for x in sorted(tokens,key=lambda x:x[:2])];width=1<<(len(a)-1).bit_length()
  gold[key]=golden(a+[None]*(width-len(a)))
 mismatches=[];matches=0
 for g,r in enumerate(roots):
  for t,tag,expr in r.rows:
   key=tag[:2]
   if g!=(tag[1]//2)%R or gold.get(key)!=expr:mismatches.append({'region':g,'t':t,'tag':list(tag),'kind':'SYMBOLIC_TREE_OR_REGION_DIFF'})
   else:matches+=1
 posttail=max((x['last_leaf']-x['last_walk_busy_bound'] for x in pair_records if x['last_leaf'] is not None),default=0)
 return {'sourcecase':{'fmt':fmt,'rows':rows,'K':K,'positions':positions,'active':active,'NP':NP,'R':R,'NBF':NBF},'metadata':source,'phase':ph,'populated_pairs':len(by),'declared_NP':NP,'peak_XFIFO':max(x['peak_XFIFO'] for x in pair_records),'XFIFO_overflow_pairs':[(x['pair'],x['overflow'][:1]) for x in pair_records if x['overflow']],'peak_segment_Q':max(x['peak_segment_Q'] for x in pair_records),'segment_fault_pairs':[(x['pair'],x['faults']) for x in pair_records if x['faults']],'max_leaf_minus_last_walk_busy':posttail,'observed_case_DRAIN127_sufficient':posttail<=127,'return':ret,'retire_tag_exact':set(retired)==expected and len(retired)==len(expected),'independent_symbolic_padded_tree_matches':matches,'independent_symbolic_tree_DIFF':mismatches,'scope':'Static source control/event transcription fullgeometry, immutablemetadata only, allactivationbeats available tospine(noavailabilitystalls). NotactualHDL/arithmetic/clock/fulltokenqualification; arbitraryspine stalls/alllegalconfig universalbound stillrequiresproof. Symbolicgolden asserts exactunchanged grouping/padding andregion order, not FP32 values/flags.'}
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--fmt',choices=['fp8','fp4','bf16'],required=True);ap.add_argument('--rows',type=int,required=True);ap.add_argument('--K',type=int,required=True);ap.add_argument('--positions',type=int,default=1);a=ap.parse_args();print(json.dumps(case(a.fmt,a.rows,a.K,a.positions),indent=2,sort_keys=True))
