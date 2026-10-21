"""Text-only selected parent ABI transform and every retained connection proof."""
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/qwen_kv_die'))
import kv_grp_private0 as gp
inp,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
ledger=json.loads((Path(__file__).resolve().parents[1]/'grp_private_model_1019/consumer_ledger.json').read_text())
records={}
for filename,key in [('gen7_die_bound.v','GEN7_BOUND'),('gen8_die_prep.v','GEN8_PREP_NOT_FINAL')]:
 raw=(inp/filename).read_bytes(); text=raw.decode()
 assert hashlib.sha256(raw).hexdigest()==ledger['graphs'][key]['sha256']
 renamed=re.sub(r'^(  qkd_kvs_grp(?:_h)?) (slg_\w+) \(',lambda m:m[1]+'_private0 '+m[2]+' (',text,flags=re.M)
 private=gp.parent_connections(renamed)
 old_lines=text.splitlines();new_lines=private.splitlines();assert len(old_lines)==len(new_lines)
 changed=[]
 for line, (a,b) in enumerate(zip(old_lines,new_lines),1):
  if a==b:continue
  ma=re.match(r'  (qkd_kvs_grp(?:_h)?) (slg_\w+) \((.*)\);',a)
  assert ma,(line,a)
  typ,inst,old=ma.groups(); new=re.match(r'  \w+ \w+ \((.*)\);',b)[1]
  old=dict(re.findall(r'\.(\w+)\(([^()]*)\)',old));new=dict(re.findall(r'\.(\w+)\(([^()]*)\)',new))
  expected={p:e for p,e in old.items() if p not in gp.DELETED and not(typ.endswith('_h') and p=='o_dn')}
  expected['x__est']=re.sub(r'\[\d+:0\]$','',old['x__est'])+'[0:0]'
  if typ.endswith('_h'):expected['i_ctl']=re.sub(r'\[\d+:0\]$','',old['i_ctl'])+'[193:0]'
  assert new==expected,(inst,new,expected)
  changed.append(dict(instance=inst,module=typ+'_private0',line=line,connections=new))
 assert len(changed)==32
 # Producers/declarations and all 128 downstream EST consumers are byte-identical.
 assert sum(x['module'].endswith('_h_private0') for x in changed)==4
 records[key]=dict(input_sha256=hashlib.sha256(raw).hexdigest(),adapted_sha256=hashlib.sha256(private.encode()).hexdigest(),changed_instances=changed,all_other_lines_byte_identical=True,final_GEN8_binding_qualified=False)
(out/'parent_receipt.json').write_text(json.dumps(records,indent=2)+'\n')
print('GRP_PRIVATE_PARENT PASS GEN7_BOUND=32 GEN8_PREP_ONLY=32 unchanged_producers_and_other_consumers=PASS')
