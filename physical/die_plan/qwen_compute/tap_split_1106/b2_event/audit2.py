from pathlib import Path
from itertools import zip_longest
from collections import Counter,defaultdict
import sys,re,json,csv
case=sys.argv[1]
if case=='east':R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-east-1106');d=R/'canary_f870';model=json.loads((R/'east_model.json').read_text());oldpath=None
else:R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106');d=R/'canary_cbn_f870';model=json.loads((R/'ev/model.json').read_text())['cbn_q00__cldbcda913'];oldpath=R/'canary_cbn_0/after.tsv'
def identity(name):
 name=name.strip('{}').replace('\\','');pre=r'(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.])'
 for tail,kind in [(r'r\[([0-9]+)\]\[([0-9]+)\]\$_DFF_P','matrix'),(r'r\[([0-9]+)\]\$_DFF_P','scalar'),(r'q\[([0-9]+)\]\$_DFF_P','qmatrix'),(r'q\$_DFF_P','qscalar')]:
  m=re.match('^'+pre+tail,name)
  if m:
   a=m.groups();return (a[0],a[2] if kind=='matrix' else a[1] if kind=='qmatrix' else 'scalar'),('terminal' if kind.startswith('q') else int(a[1]))
 m=re.match(r'^(.*u_suvm_u_vm8q_u_)(crh|crl|twl|twh)([12])[/.]q\[([0-9]+)\]\$_DFF_P_',name)
 if m:return (m[1]+m[2],m[4]),int(m[3])
def readmap(path):
 groups=defaultdict(dict);loads=Counter();names={}
 for line in path.open():
  a=line.split()
  if a[0]!='P' or len(a)<4:continue
  if a[3].startswith('ot_proto_clk_'):loads[a[3]]+=1
  if a[2]!='CLK':continue
  names[a[1]]=a[3];ident=identity(a[1])
  if ident:groups[ident[0]][ident[1]]=a[3]
 return groups,loads,names
def edge_map(groups):
 out={}
 for key,st in groups.items():
  st=dict(st);ii=sorted(i for i in st if isinstance(i,int))
  if 'terminal' in st and ii:st[max(ii)+1]=st['terminal'];ii.append(max(ii)+1)
  for i,j in zip(ii,ii[1:]):
   if j==i+1:out[(key,i,j)]=(st[i],st[j])
 return out
a,al,an=readmap(d/'after_A.tsv');b,bl,bn=readmap(d/'after_B.tsv');ae=edge_map(a);be=edge_map(b);assert ae.keys()==be.keys()
changed=[];counts=Counter()
for x,y in zip_longest((d/'after_A.tsv').open(),(d/'after_B.tsv').open()):
 assert x is not None and y is not None
 aa=x.split();bb=y.split()
 if x==y:counts['instances_unchanged' if aa[0]=='I' else 'pins_unchanged']+=1;continue
 assert aa[0]=='P' and aa[:3]==bb[:3] and aa[2]=='CLK' and identity(aa[1]) and all(v.startswith('ot_proto_clk_') for v in [aa[3],bb[3]]),(aa,bb)
 changed.append((aa,bb));counts['clock_pins_changed']+=1
oldcross={k for k,(x,y) in ae.items() if x!=y};newcross={k for k,(x,y) in be.items() if x!=y};introduced=newcross-oldcross;assert not introduced,list(introduced)[:4]
assert max(al.values())<=1200 and max(bl.values())<=1200
xy={'ot_proto_clk_'+str(j):(row[1],row[2]) for j,row in enumerate(model['new_tap_rows'])};groups=defaultdict(list);maxreach=0
for row in csv.DictReader((d/'ot_tap_chain_groups.tsv').open(),delimiter='\t'):
 groups[row['group']].append(row);x,y=xy[row['tap']];rr=abs(float(row['x_um'])-x)+abs(float(row['y_um'])-y);assert rr<=200+1e-6;maxreach=max(maxreach,rr)
assert max(map(len,groups.values()),default=0)<=128
report={'source':'f87028ff0c','case':case,'baseline':'measured A density: '+str(len(model['new_tap_rows']))+' taps; same actual3_place','assignment_only':True,**dict(counts),'joined_groups':len(groups),'max_joined_group_size':max(map(len,groups.values()),default=0),'max_joined_group_reach_um':maxreach,'A_max_grid_load':max(al.values()),'B2_max_grid_load':max(bl.values()),'adjacent_edges':len(ae),'A_cross_tap_edges':len(oldcross),'B2_cross_tap_edges':len(newcross),'boundaries_removed':len(oldcross-newcross),'new_boundaries':len(introduced)}
if oldpath:
 oe=edge_map(readmap(oldpath)[0]);ok=set(oe)&set(ae);oc={k for k in ok if oe[k][0]!=oe[k][1]};ac=oldcross&ok;report['old28_port_control_cap1200_to_A97']={'common_edges':len(ok),'old28_cross_tap':len(oc),'A97_cross_tap':len(ac),'removed_by_A':len(oc-ac),'introduced_by_A':len(ac-oc),'B2_changes_not_credited_to_A':True}
if case=='east':
 key=('u_bound.u_u_suvm_u_vm8q_u_crh','87');report['actual_worst_crh87_pair']={'A':a[key],'B2':b[key]}
report['remaining_edge_examples']=[{'prefix':k[0][0],'bit':k[0][1],'stage_pair':k[1:],'taps':be[k]} for k in sorted(newcross,key=str)[:6]]
(d/'audit.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
