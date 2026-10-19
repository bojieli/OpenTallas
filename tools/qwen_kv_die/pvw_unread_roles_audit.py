#!/usr/bin/env python3
"""Read-only PVW role audit. Produces evidence, never padding/waiver declarations."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.root/'tools'));import die_port_bind as P
SRC='rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv';GEN='tools/qwen_kv_die/pv_trunk_gen.py'
expected={SRC:'4601aa6d6ccb8b201d2f991a028a972d77f505506bc1ea87d5495738f0a7064d',GEN:'85e6bb225c010e1758b0dbcf8e24ebb20e1ab562b304c3f159ade8c787ba9458'}
for n,h in expected.items():assert hashlib.sha256((a.root/n).read_bytes()).hexdigest()==h,n
r=json.loads(a.report.read_text());source=(a.root/SRC).read_text();sn,_,_,si=P.parse_die(str(a.root/SRC),top='qkd_pvw_die_t')
for m in re.finditer(r'\bwire\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*([^;]+);',source):
 for n in P._split_commas(m[3]):
  if re.fullmatch(r'\w+',n.strip()):sn[n.strip()]=(abs(int(m[1])-int(m[2]))+1,min(int(m[1]),int(m[2])))
sm=next(m for m in P.parse_modules(source,str(a.root/SRC)) if m.name=='qkd_pvw_die_t')
for n in sm.ports:sn[n]=(sm.width(n,sm.env({})),0)
def bits(e,nets):
 b=P.expr_bits(e,nets)
 assert b is not None and not any(x[0]=='UNDECL' for x in b),e[:100]
 return b
sd={}
for line in source.splitlines():
 m=re.fullmatch(r'\s*qkd_rlys_(1|36|296|528)\s+(\w+)\s*\((.*)\);\s*',line)
 if m:
  cm=dict(P._named_conns(m[3]));aa,bb=bits(cm['a'],sn),bits(cm['b'],sn)
  for x,y in zip(aa,bb):assert y not in sd;sd[y]=x
cache={}
def origin(b):
 path=[];seen=set()
 while b in sd and b not in cache:
  assert b not in seen,('cycle',b);seen.add(b);path.append(b);b=sd[b]
 b=cache.get(b,b)
 for k in path:cache[k]=b
 return b
primary={i:(m,cm) for m,i,prm,cm in si if m in ('ot_qwen_tp8_pv_slice_t','ot_qwen_tp8_pv_join_t')}
assert len(primary)==288,len(primary)
checks=collections.Counter();required_roots=set()
for s in range(32):
 H,GS=s//8,s%8
 for bank in range(8):
  name=f'u_s{s}_b{bank}';m,cm=primary[name];pa,pb=bank,bank^4
  wanted={'pv2':[(f'vc{k}_{GS}',b) for k in (pa,pb) for b in range(128)],'pe2':[('in_e',64*k+16*H+b) for k in (pa,pb) for b in range(16)],'bc':[('cmd_w',b) for b in [0,1+bank,9 if bank<4 else 10,*range(11,31)]],'rst_n':[('rst_n',0)]}
  for port,lsb in wanted.items():
   got=[origin(b) for b in bits(cm[port],sn)];assert got==lsb[::-1],(name,port,got[:3],lsb[::-1][:3]);checks[port]+=len(got);required_roots.update(got)
 for port,want in [('join_go',('cmd_w',31)),('rst_n',('rst_n',0))]:
  got=[origin(b) for b in bits(primary[f'u_s{s}_j'][1][port],sn)];assert got==[want];checks['join_'+port]+=1;required_roots.update(got)
print('SOURCE_PRIMARY_PASS',dict(checks),flush=True)
# Actual flattened readers/writers are rebuilt independently from chosen RTL port directions.
an,tin,tout,ai=P.parse_die(r['die_v']);mods={};parsed={}
for master,inst,prm,cm in ai:
 if not any('n_pvw_' in e for e in cm.values()):continue
 if master=='__assign__':raise ValueError('unexpected actual assignment')
 if master not in mods:
  path=r['masters'][master]['rtl']
  if path not in parsed:parsed[path]={m.name:m for m in P.parse_modules(Path(path).read_text(),path)}
  mods[master]=parsed[path][master]
reads=set();writes=set();read_ports=collections.defaultdict(list);actual={i:(m,cm) for m,i,prm,cm in ai}
for master,inst,prm,cm in ai:
 if master not in mods:continue
 for port,e in cm.items():
  if 'n_pvw_' not in e:continue
  bb=[b for b in bits(e,an) if b[0].startswith('n_pvw_')]
  direction=mods[master].ports[port][0]
  if direction=='input':
   reads.update(bb)
   for b in bb:read_ports[b].append(inst+'.'+port)
  elif direction=='output':writes.update(bb)
  else:raise ValueError('unexpected direction')
unread={b for b in writes-reads if b[0] not in tin|tout}
# Confirm every source leaf's entire nonclock interface survived flattening, exactly bit for bit.
actual_checks=collections.Counter()
for parent in ('pvw_0','pvw_1'):
 for inst,(master,cm) in primary.items():
  am,acm=actual[parent+'__'+inst];assert am==master
  for port,e in cm.items():
   if port=='clk':continue
   expected_bits=[('n_'+parent+'__'+n,b) if n not in ('CONST','Z') else (n,b) for n,b in bits(e,sn)]
   got=bits(acm[port],an);assert got==expected_bits,(parent,inst,port)
   actual_checks[master+'.'+port]+=len(got)
print('ACTUAL_PRIMARY_PASS',dict(actual_checks),flush=True)
# cmd[59:32] are reserved-zero outputs, not generated replica padding.
ctl=a.root/'rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_t.sv';ct=ctl.read_text()
cmdwrites=[]
for m in re.finditer(r'\bcmd\s*(\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?\s*<=\s*([^;]+);',ct):
 if m[1]:assert max(int(m[2]),int(m[3] or m[2]))<32
 else:assert m[4].strip()=='0'
 cmdwrites.append(m[0])
assert len(cmdwrites)>10
ledger=[];counts=collections.Counter();zeros=0;unknown=[]
for net,bit in sorted(unread):
 m=re.fullmatch(r'n_(pvw_[01])__(.+)',net)
 if not m:unknown.append([net,bit,'noncanonical PV net']);continue
 parent,snet=m.groups();root=origin((snet,bit))
 if root==('CONST',0):zeros+=1;continue
 role=None;detail={}
 if re.fullmatch(r'w_CP\d+g\d+c[01]_\d+',snet) or re.fullmatch(r'w_X0c[01]',snet):
  assert root in required_roots,(snet,bit,root)
  assert root[0] in ('in_e','cmd_w')
  role='branch_subset_cargo';detail={'source_role':'E' if root[0]=='in_e' else 'C','origin':list(root),'primary_consumer_elsewhere':True}
 elif re.fullmatch(r'w_S\d+b\d',snet):
  assert bit==311 and root==('rst_n',0)
  role='duplicate_reset_cargo';detail={'origin':list(root),'dedicated_slice_reset_and_join_reset_checked':True}
 elif re.fullmatch(r'w_DL\d+',snet):
  assert bit==35
  # Registered shift chain has no wrap: bit35's input is bit34; bit35 is never read.
  assert sd[(snet,35)]==(snet,34)
  role='fixed_width_delay_terminal';detail={'predecessor':[snet,34]}
 elif snet=='cmd_w':
  assert 32<=bit<60
  role='reserved_zero_command';detail={'all_full_word_writes_zero':True,'all_partial_writes_below_bit32':True}
 elif snet in ('busy','out_age'):
  role='unconsumed_public_status';detail={'primary_consumer_completeness':'UNRESOLVED: public status has no actual consumer; owner must define whether integration requires it'}
 else:unknown.append([net,bit,list(root)]);continue
 counts[role]+=1;ledger.append(dict(net=net,bit=bit,role=role,**detail))
assert not unknown,unknown[:10]
expected_classes={k:v for k,v in r['unread_classes'].items() if 'pvw' in k}
assert sum(counts.values())==sum(v['bits'] for v in expected_classes.values())==5356,(counts,len(unread),zeros)
by_net=collections.defaultdict(list)
for row in ledger:by_net[row['net']].append(row['bit'])
roles=[]
for net,bb in by_net.items():
 rows=[x for x in ledger if x['net']==net];orig=collections.Counter(str(x.get('origin')) for x in rows)
 roles.append(dict(net=net,bits=bb,role=rows[0]['role'],source_roles=dict(collections.Counter(x.get('source_role','') for x in rows))))
out=dict(schema='opentallas.pvw_unread_role_audit.v1',qualification='read-only source/consumer evidence; NO padding declaration, tie, or waiver',source_commit='219049242d2656c808ee554b5a9ba8436e76b171',source_sha256={**expected,str(ctl.relative_to(a.root)):hashlib.sha256(ctl.read_bytes()).hexdigest()},report_sha256=hashlib.sha256(a.report.read_bytes()).hexdigest(),die_sha256=hashlib.sha256(Path(r['die_v']).read_bytes()).hexdigest(),receipt_pvw_classes=expected_classes,actual_unread_pvw_bits=len(unread),source_zero_replica_bits=zeros,classified_bits=sum(counts.values()),role_counts=dict(counts),source_primary_checks=dict(checks),actual_primary_checks=dict(actual_checks),cmd_assignments=cmdwrites,nets=roles,bit_ledger=ledger,unknown=unknown)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print('PVW_ROLE_AUDIT_PASS',dict(counts),'raw',len(unread),'replica_zero',zeros,flush=True)
