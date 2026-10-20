import json,re,sys,collections
from pathlib import Path
base=Path('/srv/opentallas-scratch/claude/kv-params2-1019')
m=json.load(open(base/'work/ot_qkh_ktree/gold1.json'))['modules']['gold']
names=collections.defaultdict(list)
for n,w in m['netnames'].items():
 if n.startswith('$') or w.get('hide_name'):continue
 for i,b in enumerate(w['bits']):
  if isinstance(b,int):names[b].append(n if len(w['bits'])==1 and w.get('offset',0)==0 else f'{n}[{i+w.get("offset",0)}]')
regs={}; drivers={}
for n,c in m['cells'].items():
 for p,bits in c['connections'].items():
  if c['port_directions'][p]=='output':
   for i,b in enumerate(bits):drivers[b]=(n,c,p,i)
 if c['type'] in ('$dff','$adff','$sdff','$dffe','$adffe','$sdffe'):
  for i,b in enumerate(c['connections']['Q']):regs[b]=(n,c,i)
pre=(base/'base_ktree/joint_prelude.ys').read_text().split('cd gold\n',1)[1].split('\ncd\n',1)[0]
paired_names=re.findall(r'^connect -set (S__\S+) (\S+)$',pre,re.M)
paired_names=[n for s,n in paired_names if not s.startswith('S__proof_')]
paired_names=[n for n in paired_names if not n.startswith("1'")]
bit_of={n:b for b,ns in names.items() for n in ns}
paired={bit_of[n] for n in paired_names if n in bit_of}
print('source_reg_bits',len(regs),'paired_source_bits',len(paired),'source_only',len(set(regs)-paired))
only=sorted(set(regs)-paired)
print('source_only_sample',[(names[b][:3],regs[b][1]['type']) for b in only[:15]])
# Pure register data copies are exact dependencies. Computed cones are recorded and not guessed.
def predecessor(b):
 n,c,i=regs[b]; d=c['connections']['D'][i]
 return d
for target in ['g_n[0].u_a.u_cc.g_r.r[64]','g_n[0].u_a.u_cc.g_r.r[32]','g_n[0].u_a.u_cc.g_r.r[31]']:
 b=bit_of.get(target);print('\nTARGET',target,'bit',b)
 for depth in range(9):
  if b not in regs:
   print('STOP',depth,'constant' if not isinstance(b,int) else 'combinational_or_input',b,names.get(b,[])[:8]);break
  n,c,i=regs[b]
  print('DEPTH',depth,'PAIRED' if b in paired else 'UNPAIRED','Q',names[b][:8],'cell',n,'type',c['type'],'D',c['connections']['D'][i], 'CLK',c['connections'].get('CLK'),'ARST',c['connections'].get('ARST'))
  b=predecessor(b)
# Identify source-only registers whose D is identical to a native-corresponding source register's D.
byd=collections.defaultdict(list)
for b,(n,c,i) in regs.items():
 key=(c['type'],tuple(c['connections'].get('CLK',[])),c['connections']['D'][i],tuple(c['connections'].get('ARST',[])),c.get('parameters',{}).get('ARST_POLARITY'))
 byd[key].append(b)
dups=[]
for bs in byd.values():
 ps=[b for b in bs if b in paired]; us=[b for b in bs if b not in paired]
 if ps and us:
  dups.extend({'unpaired':names[b],'paired':names[ps[0]],'D':predecessor(b)} for b in us)
print('\nEXACT_DUPLICATE_D_WITH_PAIRED',len(dups))
print(json.dumps(dups[:30],indent=1))
Path('state_cone.json').write_text(json.dumps(dict(source_reg_bits=len(regs),paired_source_bits=len(paired),source_only=len(set(regs)-paired),same_d_unpaired=dups),indent=1)+'\n')
