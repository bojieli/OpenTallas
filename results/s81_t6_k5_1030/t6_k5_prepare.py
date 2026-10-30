from pathlib import Path
import json,re,hashlib,collections
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030/t6_k5');old=Path('/srv/opentallas-scratch2/claude/kit-wave/s81/d33fc7e9b90/items/slice_station__t6__cl54a9ceeb/attempt_2/rtl/slice_station__t6__cl54a9ceeb_bound.sv').read_text();new=old
for slot in [0,1]:
 wire=f'    wire [1104:0] ft{slot}_o_s2;';assert old.count(wire)==1;new=new.replace(wire,wire+f'\n    wire [1104:0] ft{slot}_o_s3;')
 line=next(x for x in old.splitlines() if f'u_ft_ft{slot}_o_3 ' in x)
 replaced=line.replace(f'.q(ft{slot}_o[',f'.q(ft{slot}_o_s3[').replace(f'.eq(ft{slot}_o[',f'.eq(ft{slot}_o_s3[')
 fifth=line.replace(f'u_ft_ft{slot}_o_3 ',f'u_ft_ft{slot}_o_4 ').replace(f'.d(ft{slot}_o_s2[',f'.d(ft{slot}_o_s3[').replace(f'.ea(ft{slot}_o_s2[',f'.ea(ft{slot}_o_s3[')
 new=new.replace(line,replaced+'\n'+fifth)
 # Comment update affects ONLY selected port count.
 new=new.replace(f'ft{slot}_o,   // ft ft{slot}: 4 station(s)',f'ft{slot}_o,   // ft ft{slot}: 5 station(s)')
(r/'old_bound.sv').write_text(old);(r/'candidate_bound.sv').write_text(new)
P=json.load(open(r/'original_plan.json'));T=P['partition_types']['slice_station__t6__cl54a9ceeb'];cand=json.loads(json.dumps(T))
for sl in cand['ft_slots']:
 if sl['name'] in ['ft0','ft1']:assert sl['stations']==4;sl['stations']=5
assert [x for x in T['ft_slots'] if x['name'] not in ['ft0','ft1']]==[x for x in cand['ft_slots'] if x['name'] not in ['ft0','ft1']]
(r/'candidate_type.json').write_text(json.dumps(cand,indent=1)+'\n')
counts=collections.Counter();masters=collections.Counter();matrix={}
for line in Path('/srv/opentallas-scratch2/claude/codex-signoff-wave-1030/t6_native/vertical_corrected.tsv').read_text().splitlines():
 a=line.split('\t')
 if a[0]!='C' or a[2]!='S':continue
 m=re.search(r'u_bound\.u_ft_ft([01])_o_([0-3])/',a[8])
 if m:
  key='ft'+m[1]+'_stage'+m[2];counts[key]+=1;masters[(key,a[3])]+=1
  matrix.setdefault(key,[]).append(dict(name=a[8],master=a[3],xy=[float(a[4]),float(a[5])],size=[round(float(a[6])-float(a[4]),6),round(float(a[7])-float(a[5]),6)]))
assert len(counts)==8 and all(n==1105 for n in counts.values()),counts
(r/'actual_old_ff_matrix.json').write_text(json.dumps(matrix,indent=1)+'\n')
(r/'prep.json').write_text(json.dumps(dict(schema='opentallas.t6_k5.prep.v1',instance='s_0S_x07',type='slice_station__t6__cl54a9ceeb',source_plan_commit='0428e13f7f3',old_source_sha256=hashlib.sha256(old.encode()).hexdigest(),candidate_source_sha256=hashlib.sha256(new.encode()).hexdigest(),selected_slots=['ft0','ft1'],unchanged_slots=[f'ft{x}' for x in range(2,13)],added_flops=2210,added_cycles_per_selected_path=1,outline_changed=False,pins_changed=False,clock_roles_changed=False,old_mapped_stage_counts=dict(counts),old_mapped_masters=[dict(stage=k[0],master=k[1],count=v) for k,v in sorted(masters.items())],state='PRIVATE_SOURCE_PREP_NOT_ADOPTED; no fresh physical packet/native sizing/clock qualification',generator_integration='Current approved-main exporter integration remains gated; candidate is surgical private source preparation against immutable native source, not a regenerated current-main binding.'),indent=1)+'\n')
print(counts,'added2210; other11slots unchanged')
