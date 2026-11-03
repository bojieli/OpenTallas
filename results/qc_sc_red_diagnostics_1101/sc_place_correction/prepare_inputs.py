import json,hashlib,re,copy
from pathlib import Path
p=Path('.');plan=json.load(open('core_infra_plan.json'));nodes=plan['cells'];parents={x['name']:x['parent'] for x in nodes};old={s.rsplit('/',1)[0]:l['node'] for l in plan['core_tree']['leaves'] for s in l['sinks']};assign=json.load(open('leaf_sinks_balanced.json'));new={s:leaf for leaf,ss in assign.items() for s in ss};moves=json.load(open('candidate.json'))['ff_moves']
assert len(old)==len(new)==42665 and set(old)==set(new) and len(assign)==1024 and all(1<=len(ss)<=42 for ss in assign.values())
cs={x[-1]:x for s in open('sc_geom.tsv') if (x:=s.rstrip().split('\t'))[0]=='C'}
with open('moves.tsv','w') as f:
 for m in moves:
  oldbb=[round(v*1000) for v in m['old_bbox']];bb=[round(v*1000) for v in m['new_bbox']];assert m['master']==cs[m['instance']][3]
  f.write('\t'.join(map(str,[m['instance'],m['master'],oldbb[0],oldbb[1],bb[0],bb[1],bb[2]-bb[0],bb[3]-bb[1]]))+'\n')
with open('assignment.tsv','w') as f:
 for n in sorted(new):f.write('\t'.join([n,'CLK',new[n],old[n],cs[n][3]])+'\n')
Path('node_names.list').write_text('\n'.join(n+'\t'+p for n,p in parents.items())+'\n')
files=[]
for name in ['core_infra_plan.json','core_infra_slice.json']:
 q=p/name;text=q.read_text();j=json.loads(text);before=copy.deepcopy(j);assert {x['node'] for x in j['core_tree']['leaves']}==set(assign)
 for leaf in j['core_tree']['leaves']:leaf['sinks']=[n+'/CLK' for n in assign[leaf['node']]]
 check=copy.deepcopy(j);check['core_tree']['leaves']=before['core_tree']['leaves'];assert check==before
 q.write_text(json.dumps(j,indent=1)+'\n');files.append(dict(file=name,old_sha=hashlib.sha256(text.encode()).hexdigest(),new_sha=hashlib.sha256(q.read_bytes()).hexdigest()))
q=p/'master_core_infra.tcl';text=q.read_text();seen=set()
def sub(m):
 n=m.group(2).rsplit('/',1)[0];assert n in new and n not in seen;seen.add(n);return 'ot_ci_tree_sink {'+new[n]+'} {'+n+'/CLK}'
q.write_text(re.sub(r'^ot_ci_tree_sink \{([^}]+)\} \{(.+)\}$',sub,text,flags=re.M));assert seen==set(new)
files.append(dict(file=q.name,old_sha=hashlib.sha256(text.encode()).hexdigest(),new_sha=hashlib.sha256(q.read_bytes()).hexdigest()))
Path('SC_CORRECTION_BINDING_OVERLAY.json').write_text(json.dumps(dict(scope='PRIVATE_ONE_PLACE_CORRECTION_NOT_PARENT_ADOPTION',ff_moves=len(moves),public_pin_changes=0,native_ff=42665,fixed_nodes=2389,leaves=1024,leaf_cap=42,depth=7,new_ff=0,new_cycles=0,files=files),indent=2)+'\n');print('SC_PAIRED_PLAN_PASS',len(new),len(assign),len(moves))
