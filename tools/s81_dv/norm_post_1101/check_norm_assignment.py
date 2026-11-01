from pathlib import Path
import json,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/norm_assignment_104_56');src=r/'word_map.jsonl';profile=json.loads((r/'profile.json').read_text());spans=profile['source_spans'];records=[json.loads(x)for x in src.read_text().splitlines()]
def check(rows):
 errors=[];seen=set();groups={}
 for m in rows:
  n,e,rank=m['global_element'],m['expert'],m['rank'];key=(e,n)
  if key in seen:errors.append(('duplicate',key))
  seen.add(key);local=n-1280*rank
  source=next(((s,local-a)for s,(a,count)in enumerate(spans)if a<=local<a+count),None)
  if source is None:errors.append(('source_range',key));continue
  s,j=source;want_src=(s,j//64,128+16*e+(j%64)//4,j%4)
  got_src=tuple(m[k]for k in ('source_sid','source_leaf','source_row','source_word'))
  want_dst=(n//320,(n//64)%5,320+16*e+(n%64)//4,n%4,n//64)
  got_dst=tuple(m[k]for k in ('sid','leaf','row','word','beat'))
  if got_src!=want_src:errors.append(('source_address',key,got_src,want_src))
  if got_dst!=want_dst:errors.append(('native_norm_group_or_order',key,got_dst,want_dst))
  if not 0<=e<7 or not 0<=n<5120 or rank!=n//1280:errors.append(('owner',key))
  pos=4*(m['row']-320-16*e)+m['word'];gkey=(e,m['sid'],m['leaf']);g=groups.setdefault(gkey,{})
  if pos in g:errors.append(('destination_duplicate',gkey,pos))
  g[pos]=n
 if seen!={(e,n)for e in range(7)for n in range(5120)}:errors.append(('coverage',len(seen)))
 for e in range(7):
  for sid in range(16):
   for leaf in range(5):
    g=groups.get((e,sid,leaf),{})
    if [g.get(k)for k in range(64)]!=list(range(320*sid+64*leaf,320*sid+64*leaf+64)):errors.append(('ordered64_group',e,sid,leaf))
 return errors
errors=check(records);controls={}
for name,a,b in [('cross64_boundary',63,64),('within64_order',0,1)]:
 rows=[dict(x)for x in records];by={(x['expert'],x['global_element']):x for x in rows}
 for e in range(7):
  x,y=by[e,a],by[e,b]
  for k in ('sid','leaf','row','word','beat'):x[k],y[k]=y[k],x[k]
 controls[name]=dict(rejected=bool(check(rows)),source_values_and_rowforest_unchanged=True,global_value_labels_preserved=True)
assert len(records)==35840 and not errors and all(x['rejected']for x in controls.values())
result=dict(status='PASS_104_56_CANDIDATE_CANONICAL_NORM_GROUP_MAP_ONLY',words=len(records),experts=7,canonical64_word_groups=80,ordered_groups_checked=560,
 source_map_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),source_spans=spans,controls=controls,
 partial_group_formula='sid=n//320;leaf=(n//64)%5;word=n%64; XRT tuple index=5sid+leaf; existing NX80-leaf reduction order retained',
 prerequisites_for_numeric_equivalence=['actual newly emitted source BF16 down values match canonical rowforests/checkpoint for every mapped n','actual RD transport implements this map and lease dates','combined result broadcast preserves exact beat/word to allTP4copies','same residual HCpre/gain indices and nativePOST arithmetic order'],
 actual_new_source_values_qualified=False,actual_RD_transport_qualified=False,actual_new_partial_payloads_generated=False,
 all80_native_VN_inputs_qualified=False,new_RSTD_gold=None,canonical_adopted=False)
(r/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],len(records),'words',controls)
