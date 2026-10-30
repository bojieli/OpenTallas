from pathlib import Path
import json,collections
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind/ff_fixture');receipt={'schema':'opentallas.iqf.ff_preservation_fixture.v1','source':['d2740167be3','328e8c36ea3','c05502f95c2'],'physical_adoption':False,'modes':{}}
for mode in ['default','preserve']:
 p=r/mode/'run/results/asap7/dp_iqf__t1/base';a=p/'fixture434_preforced.tsv';b=p/'fixture434_postresize.tsv'
 if not a.exists() or not b.exists():receipt['modes'][mode]={'state':'INCOMPLETE','preforced':a.exists(),'postforced':b.exists()};continue
 def read(x):
  rows=[l.split('\t') for l in x.read_text().splitlines()];assert len(rows)==434 and len({z[0] for z in rows})==434;return {z[0]:z[1:] for z in rows}
 pre,post=read(a),read(b);assert pre.keys()==post.keys()
 base={z[0]:z[1:] for z in (l.split('\t') for l in (r/'fixture434_baseline.tsv').read_text().splitlines())};assert len(base)==434
 wrong=[n for n,z in post.items() if z[0]!='DFFHQNx1_ASAP7_75t_R'];buf=[n for n,z in post.items() if z[2].startswith(('BUF','INV'))];newbuf=[n for n in buf if base[n][1:]!=post[n][1:]];forced_newbuf=[n for n in buf if pre[n][1:]!=post[n][1:]];direct_buf=[n for n in newbuf if post[n][2].startswith('BUF')]
 receipt['modes'][mode]={'state':'COMPLETE','actual_target_count':434,'masters_before_forced':dict(collections.Counter(z[0] for z in pre.values())),'masters_after_forced':dict(collections.Counter(z[0] for z in post.values())),'master_changed_count':len(wrong),'Dpin_BUF_INV_drivers_after':len(buf),'new_Dpin_BUF_INV_driver_count':len(newbuf),'new_Dpin_after_forced_only_count':len(forced_newbuf),'new_direct_Dpin_BUF_count':len(direct_buf),'baseline_Dpin_driver_masters':dict(collections.Counter(z[2] for z in base.values())),'wrong_master_names':wrong,'new_Dpin_buffer_examples':newbuf[:10]}
d=receipt['modes'].get('default',{});p=receipt['modes'].get('preserve',{})
receipt['qualified']=d.get('state')=='COMPLETE' and p.get('state')=='COMPLETE' and d['master_changed_count']>0 and p['master_changed_count']==0 and p['new_direct_Dpin_BUF_count']>0
receipt['conditions']='Default must exhibit real master changes; preserve all434requiredx1 plus force-lawful Dpinbufferrepair. No normalphysicaladoption from fixture alone.'
(r/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt,indent=1)[:3500])
