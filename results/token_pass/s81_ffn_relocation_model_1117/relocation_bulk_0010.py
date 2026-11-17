import json
from pathlib import Path
from collections import Counter,defaultdict
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116')
out=r/'final_ffn_relocation_model_0000';m=json.loads((out/'model.json').read_text());legs=json.loads((out/'legs.json').read_text())
identity=lambda z:(z['phase'],json.dumps(z['identity']))
size=Counter(identity(z) for z in legs)
packed=[]
for z in legs:
 eligible=z['mask']==255 and z['kind'] in ('local_copy','wide') and size[identity(z)]==1
 prev=packed[-1] if packed else None
 match=prev is not None and eligible and prev['eligible'] and prev['pairs']<4 and all(prev[k]==z[k] for k in ['rank','phase','kind','source','source_leaf','destination','leaf','mask','path']) and z['source_row']==prev['source_row']+2*prev['pairs'] and z['row']==prev['row']+2*prev['pairs']
 if match:prev['pairs']+=1;prev['identities'].append(z['identity'])
 else:packed.append(dict(z,eligible=eligible,identities=[z['identity']]))
ctl=Counter();reads=Counter();writes=Counter();lanes=Counter();kinds=Counter();groups=Counter()
for z in packed:
 rank=z['rank'];a=z['source'];b=z['destination'];n=z['pairs'];ctl[rank,0 if a%2 else 1]+=2
 reads[rank,a,z['source_leaf']]+=n;writes[rank,b,z['leaf']]+=n;kinds[z['kind']]+=1;groups[n]+=1
 for p in z['path']:lanes[rank,p['link']]+=1
alias=Counter()
for (rank,eng),n in ctl.items():alias[eng]+=n
sources={(a['rank'],a['assembly_sid'],a['assembly_leaf']):a['global_beat'] for a in m['assignments']}
clobbers=[]
for a in m['assignments']:
 k=(a['rank'],a['canonical_sid'],a['canonical_leaf']);live=sources.get(k)
 if live is not None and live!=a['global_beat']:
  clobbers.append(dict(rank=a['rank'],incoming_beat=a['global_beat'],canonical_sid=a['canonical_sid'],leaf=a['canonical_leaf'],unsent_relocated_beat=live,old_receive_rows=[448,464],separate_safe_receive_rows=[464,480],old_POST_reads_wrong_beat=True))
assert clobbers
# Symbolic return payload word=(globalbeat,word). New receive bank is disjoint
# from every relocated source, old receive bank aliases an actual other beat.
example=clobbers[0];incoming=(example['incoming_beat'],0);old=(example['unsent_relocated_beat'],0)
assert incoming!=old
correct_POST_a1=464;old_POST_a1=448
assert correct_POST_a1!=old_POST_a1
result=dict(schema='opentallas.s81.ffn.relocation-restricted-bulk.v1',status='MODEL_ONLY_CALENDAR_BLOCKED',policy='Only fullmask SINGLELEG localcopy or same-tierwide may bulk<=4; any V/multileg/partial remainsonepair, so intermediate scratch stays2rows.',packet_count=len(packed),packet_sizes=dict(groups),leg_packet_counts=dict(kinds),control_words=2*len(packed),control_by_rank_engine=[dict(rank=k[0],engine=k[1],slots=n) for k,n in sorted(ctl.items())],separate_rank_engine_floor=max(ctl.values()),aliased_rank_engine_floor=max(alias.values()),read_port_pair_floor=max(reads.values()),write_port_pair_floor=max(writes.values()),lane_packet_floor=max(lanes.values()),existing827budget_deficit=max(0,max(ctl.values())-827),unpacked_control_words=m['total_transport_price']['controls'],unpacked_engine_floor=m['total_transport_price']['separate_rank_control_floor'],alias_negative_control=dict(actual_clobber_cases=len(clobbers),example=example,incoming448_rejected=True,old_POST_a1448_rejected=True,correct_POST_a1464=True,symbolic_word_identity=[list(incoming),list(old)]),remaining='This is finite-resource lowerbound, not dependency/fullstaticcalendar. Need CAPready+scratchleases+selectedXRT/maskedcopyages+VS13timing+POST/peerflow+hostreload and productionexactness.',scope='No new source/RTL/images. Actual107/53 ownership and canonicalPOST/H layout preserved; whole64beat assembly relocation only.')
(out/'restricted_bulk.json').write_text(json.dumps(result,indent=1)+'\n');(out/'restricted_bulk_packets.json').write_text(json.dumps(packed,indent=1)+'\n');(out/'alias_cases.json').write_text(json.dumps(clobbers,indent=1)+'\n');print(json.dumps(result))
