from pathlib import Path
import re,json,collections
R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106/canary_cbn_97')
def identities(name):
 name=name.strip('{}').replace('\\','')
 pre=r'(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.])'
 for tail,kind in [(r'r\[([0-9]+)\]\[([0-9]+)\]\$_DFF_P','matrix'),(r'r\[([0-9]+)\]\$_DFF_P','scalar'),(r'q\[([0-9]+)\]\$_DFF_P','qmatrix'),(r'q\$_DFF_P','qscalar')]:
  m=re.match('^'+pre+tail,name)
  if not m:continue
  a=m.groups();return (a[0],a[2] if kind=='matrix' else a[1] if kind=='qmatrix' else 'scalar'),('terminal' if kind.startswith('q') else int(a[1]))
 return None
maps=[]
for fn in ['after_A.tsv','after_B.tsv']:
 groups=collections.defaultdict(dict)
 for line in (R/fn).open():
  a=line.split()
  if a[0]!='P' or len(a)<4 or a[2]!='CLK':continue
  ident=identities(a[1])
  if ident:groups[ident[0]][ident[1]]=a[3]
 maps.append(groups)
counts=collections.Counter();examples=[]
for key,stages in maps[0].items():
 b=maps[1][key];indices=sorted(x for x in stages if isinstance(x,int))
 if 'terminal' in stages and indices:
  stages[max(indices)+1]=stages['terminal'];b[max(indices)+1]=b['terminal'];indices.append(max(indices)+1)
 for i,j in zip(indices,indices[1:]):
  if j!=i+1:continue
  aa=stages[i]!=stages[j];bb=b[i]!=b[j];counts['adjacent_edges']+=1;counts['A_cross_tap']+=aa;counts['B_cross_tap']+=bb
  counts['improved']+=aa and not bb;counts['new_boundary']+=not aa and bb
  if bb and len(examples)<8:examples.append({'prefix':key[0],'bit':key[1],'stages':[i,j],'B_taps':[b[i],b[j]]})
report={'assignment_only':True,**dict(counts),'remaining_examples':examples};(R/'edge_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
