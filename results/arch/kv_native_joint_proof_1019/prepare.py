import json, pathlib, shutil, hashlib
root=pathlib.Path(__file__).resolve().parent
old=pathlib.Path('/srv/opentallas-scratch/claude/kv-params-1019')
identity={'old_commit':'dd27f95b8','diagnosis_commit':'bf4e0ee05','physical_reset_receipt':False,'files':{}}
for short,top,n in [('ktree','ot_qkh_ktree',95),('lane8','ot_qkh_lane8',96)]:
 d=root/short; d.mkdir(exist_ok=True)
 for name in ['gate.v','cells.v','gold1.il']:
  src=old/'runs'/top/name; shutil.copy2(src,d/name)
  identity['files'][str(src)]=hashlib.sha256(src.read_bytes()).hexdigest()
 obs=json.loads((root/(top+'_observations.json')).read_text()); assert len(obs)==n
 original=(root/(short+'_original.ys')).read_text()
 assert original.count('equiv_make gold gate equiv')==1
 gold=''; gate='cd gate\n'
 for i,sig in enumerate(obs):
  assert sig.endswith('[1]') and not sig.endswith('.err[1]')
  name='S__proof_meta_%03d'%i
  gold+='add -wire %s 1\nconnect -set %s %s\n'%(name,name,sig)
  gate+="add -wire %s 1\nconnect -set %s 1'0\n"%(name,name)
 gate+='cd\n'
 pre=original.split('equiv_simple -seq 2')[0]
 pre=pre.replace('cd gold\n','cd gold\n'+gold,1)
 pre=pre.replace('setattr -set keep 1 w:S__*',gate+'setattr -set keep 1 w:S__*',1)
 (d/'joint_prelude.ys').write_text(pre)
 (d/'joint_induct.ys').write_text(pre+'equiv_simple -seq 2\nequiv_induct\nequiv_status\nequiv_status -assert\n')
 base=pre+'equiv_miter -assert miter\nhierarchy -top miter\nflatten\nopt_clean\n'
 reset=' '.join('-set-at %d rst_n 0'%i for i in range(1,7))
 (d/'joint_base.ys').write_text(base+'sat -seq 10 -prove-asserts -prove-skip 6 -set-def-inputs '+reset+' -show-inputs -show-outputs -dump_json joint_base_cex.json -verify\n')
 original_names=[x for x in original.splitlines() if x.startswith('add -wire S__')]
 retained=[x for x in pre.splitlines() if x.startswith('add -wire S__') and 'S__proof_meta_' not in x]
 assert original_names==retained
 identity[short]={'original_observations_retained':len(original_names),'additional_observations':n,'observations':obs,'base_reset_low_target_edges':6,'base_checked_steps':[7,8,9,10]}
(root/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
