#!/usr/bin/env python3
"""Search existing3bit PDSK selectors and pack a source-only NORMR candidate."""
import copy,itertools,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[3];sys.path[:0]=[str(ROOT/'tools/s81_dv'),str(ROOT/'tools/s81_dv/layer_prog')]
import dv_layer_compile as D
from layer_prog.entry_write_calendar import encode_unsealed
routes=json.loads((P.parent/'leaf_routes.json').read_text());source=json.loads((P.parent/'norm_control.json').read_text())
assert json.loads((P/'composition.json').read_text())['blocked_sids']==[0,5]
profiles={};choices=[]
for sid in range(16):
 rows=[r for r in routes['leaves']if r['sid']==sid];old=[r['pdsk_edges']for r in rows]
 path=[116+r['xr_command_to_leaf_boundary_edges']+r['vn_b_partial_to_xr_input_edges']for r in rows]
 legal=[]
 if len(set(a+b for a,b in zip(path,old)))==5:profile=old
 else:
  for leaf in range(5):
   for depth in range(8):
    if depth==old[leaf]:continue
    candidate=old.copy();candidate[leaf]=depth;totals=[a+b for a,b in zip(path,candidate)]
    if len(set(totals))!=5:continue
    delta=depth-old[leaf];cost=(1,abs(delta),delta,(depth^old[leaf]).bit_count(),leaf,depth)
    legal.append((cost,candidate,totals))
  if not legal:raise ValueError('existing one-selector options cannot remove ties')
  cost,profile,total=min(legal)
  choices.append(dict(sid=sid,slice=rows[0]['slice'],old_depths=old,candidate_depths=profile,
      changed_fields=cost[0],changed_selector_bits=cost[3],extra_FF=33*cost[2],
      old_max_path=max(a+b for a,b in zip(path,old)),candidate_max_path=max(total),
      old_literal_oct=f"15'o{sum(d<<(3*k)for k,d in enumerate(old)):05o}",
      candidate_literal_oct=f"15'o{sum(d<<(3*k)for k,d in enumerate(profile)):05o}",
      one_field_legal_options=len(legal)))
 profiles[sid]=dict(depths=profile,total=[a+b for a,b in zip(path,profile)])
commands=[];rows=[];templates=[];engine_stats={};alignment={}
for engine in (0,1):
 used=set()
 for sid in range(engine^1,16,2): # engine0 is north/odd SID; engine1 south/even
  total=profiles[sid]['total'];maximum=max(total);offset=[maximum-t for t in total];base=20
  while any(base+o in used for o in offset):base+=1
  for leaf,off in enumerate(offset):
   c=copy.deepcopy(next(c for c in source['commands']if c['kind']=='NORMR'and c['sid']==sid and c['leaf']==leaf));t=copy.deepcopy(source['templates'][c['template']]);ix=len(templates)
   issue=base+off;assert issue not in used;used.add(issue);c.update(template=ix,issue=issue)
   t['i']=ix;templates.append(t);commands.append(c);rows.append(dict(eng=engine,issue=issue,done=issue+5,arg=ix,tix=ix,row76=f'{D.pack_row(issue+5,issue,engine,ix):019x}'))
  alignment[sid]=base+maximum
 engine_stats[engine]=dict(first_issue=min(used),last_issue=max(used),commands=len(used))
rows.sort(key=lambda r:(r['issue'],r['eng']))
assert len(rows)==80 and len({(r['eng'],r['issue'])for r in rows})==80
for sid in range(16):
 cs=sorted((c for c in commands if c['sid']==sid),key=lambda c:c['leaf'])
 assert len({c['issue']+profiles[sid]['total'][c['leaf']]for c in cs})==1
for eng,stats in engine_stats.items():
 stats['max_live_including_ACK']=max(sum(r['eng']==eng and r['issue']<=edge<=r['done']for r in rows)for edge in range(20,max(r['done']for r in rows)+1))
 assert stats['max_live_including_ACK']<=8
candidate=dict(schema='opentallas.s81.norm_pdsk_repair_candidate.v1',status='UNADOPTED_SELECTOR_AND_NORMR_SCHEDULE',
 current_source_top_sha256=routes['source_top_sha256'],selector_changes=choices,extra_FF=sum(c['extra_FF']for c in choices),
 selector_search='minimum changed fields, then depth-distance, then fewer flops, then selector bit flips; existing0..7 selectors only',
 rows=rows,commands=commands,templates=templates,engine_stats=engine_stats,
 per_sid_partial_alignment_relative_to_unqualified_common_CTL_transport=alignment,
 multicast_rejected=dict(xrt_source_sha256='59a53960b2c66851b14fbfcc615e451d380774ac483f2987a5f806abeb0cffa9',xrt_lines=[753,765],
  xrt='one lmask may enable multiple c_v leaves, but all receive identical c_d body',vp_lines=[206,214,215,378],
  vp='NORMR dmq={n[1:0],a1[7:0]} feeds m_q/m_b/m_i; q-only n1 requires distinct globalbeat a1=5sid+leaf. No per-leaf a1 in one body. n0 suppresses required q gather rather than preserving its semantics'),
 GO_emitted=False,KIT_END_emitted=False,native_job_sealed=False,source_adopted=False,
 physical_timing_qualified=False,actual_partial_alignment_executed=False,global_exchange_qualified=False,full_token=False,
 holds=['owner source/physical freeze exception for two PDSK selector changes','actual selected downstream XR collector mechanism for changed selectors',
 'selected seqhost to XR transport and incoming entry residency','actual GO/XFIN/RSTD/VQ K-profile/retirement/globalSTART'])
words=encode_unsealed(candidate);assert len(words)==321
# Decode the actual PW stream independently of the row packer.
cells={};payload={};length=[]
for word in words:
 x=word>>1;op=x&255
 if op==0x11:length.append((x>>32)&255)
 elif op==0x10:
  a=(x>>96)&127;d=(x>>32)&((1<<28)-1);part=d>>26
  assert part<3 and (a,part)not in cells;cells[a,part]=d&((1<<26)-1)
 elif op==0x13:payload[(x>>8)&127]=(x>>16)&((1<<186)-1)
 else:raise ValueError('unexpected HOST operation')
assert length==[80]and len(cells)==240 and len(payload)==80
for i,row in enumerate(rows):
 value=sum(cells[i,k]<<(26*k)for k in range(3))
 assert ((value>>28)&0xffffff,(value>>52)&0xffffff,(value>>24)&15,value&0xffffff)==(row['issue'],row['done'],row['eng'],row['arg'])
assert payload=={t['i']:int(t['payload186'],16)for t in templates}
candidate['HOST_words']=len(words);candidate['HOST_local_reservation_edges']=5*len(words)
(P/'repair_candidate.json').write_text(json.dumps(candidate,indent=1)+'\n');(P/'repair_candidate.unsealed.memh').write_text(D.memh(words,515))
print('UNADOPTED candidate',[(c['sid'],c['candidate_literal_oct'],c['extra_FF'])for c in choices],engine_stats,'321words/noGO')
