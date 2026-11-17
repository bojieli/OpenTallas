from pathlib import Path
import os,json,sys,re
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116');code=r/'code_bf_components_2240';source=r/'source_bf_components_2240';b=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1')
a=json.loads((source/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(source),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(source),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN='/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json',OT_XS_ASB_SCHEDULE_DIR=str(r/'profiles'),OT_GUNIT_BF_DEFINES='OT_GUNIT_BF_M1REG,OT_GUNIT_BF_C1REG,OT_GUNIT_BF_SVREG,OT_GUNIT_BF_FWPIPE')
sys.path[:0]=[str(code/'tools/s81_dv/layer_prog'),str(code/'tools/s81_dv'),str(code/'tools')]
os.environ['OT_S81_SELECTED_CHILD_FILES']='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv'
import dv_layer_compile as C
from layer_prog import bound_data as BD,bound_ctl_lanes as BCL,lower_gu as GU,lower_vpx as VPX
B=BD.load_bind(b/'out',str(b/'asbuilt_run.json'),code)
die=C.Die(code,netlist=B['netlist_path'],netlist_sha=B['netlist_sha256'],bound_rtl=b/'out/rtl');BD.rebind_links(die,B)
from layer_prog import xs_place as XP,final_ffn as FF,xs_calendar as XC
fx=XP.Fix(r/'L0')
from collections import Counter,defaultdict
from cap_model import decode
import hashlib
os.environ.pop('OT_XS_FINAL_FFN_PAIR_ROWS',None)
groups=XP.op_groups(fx,'ffn.down')
deal=[sorted(j for frame in sl for j in frame) for sl in groups[0]['groups']]
assert len(deal)==16
flat=[j for sl in deal for j in sl]
assert flat==list(range(1280))
spans=[(min(sl),len(sl)) for sl in deal]
for group in groups:
 assert [sorted(j for frame in sl for j in frame) for sl in group['groups']]==deal
phases=len(XP.phase_list(fx,['ffn.down']))
CAPTURE_STRIDE=72
CAPTURE_BASE=4*FF.CAPTURE
SCRATCH_ROW=304
store={};frags={};descriptors=[];capfaults=0
for rank in range(4):
 for group in groups:
  expert=FF.expert_slot(group['expert'],fx.meta['experts'])
  for sid,(start,count) in enumerate(spans):
   cfg=dict(obase=CAPTURE_BASE+CAPTURE_STRIDE*expert+(start%8),ops=0,np=0,fmt=2,rbase=start,rcnt=count,rsplit=0,lo32=0,hi32=0)
   descriptors.append(dict(rank=rank,expert=expert,source_sid=sid,actual_start=start,actual_count=count,cfg=cfg))
   for row in (start-1,start+count):
    assert decode((row&65535)<<13,0,cfg)[0],(sid,row,'foreign row accepted')
   for local in range(start,start+count):
    bad,leaf,port,addr,data=decode(local<<13,0x3f800000,cfg)
    assert not bad and data==0x3f800000
    assert addr%8==local%8,(sid,local,addr)
    sk=(rank,expert,sid,leaf,addr)
    assert sk not in store
    store[sk]=(rank,expert,local)
    global_word=1280*rank+local
    dst=FF.owner(global_word)
    source_pair_row=(addr//8)*2
    destination_pair_row=FF.ASSEMBLED+16*expert+2*(dst['word']//8)
    key=(rank,expert,sid,leaf,source_pair_row,dst['sid'],dst['leaf'],destination_pair_row)
    rec=frags.setdefault(key,dict(rank=rank,expert=expert,source_sid=sid,source_leaf=leaf,source_row=source_pair_row,sid=dst['sid'],leaf=dst['leaf'],row=destination_pair_row,mask=0,global_pair_first=global_word//8*8))
    assert rec['global_pair_first']==global_word//8*8
    bit=1<<(addr%8);assert not rec['mask']&bit;rec['mask']|=bit
# Read raw words at their actual CAP addresses. Poison every padding position.
received={};coverage=defaultdict(int);counts=Counter();route_counts=Counter();scratch=Counter()
fragments=[]
for key,rec in sorted(frags.items()):
 rank,expert,source_sid,source_leaf,source_pair_row,sid,leaf,destination_pair_row=key
 pair=(rank,expert,sid,leaf,destination_pair_row)
 mask=rec['mask'];assert mask
 assert not coverage[pair]&mask,('overlapping masked writers',pair)
 coverage[pair]|=mask
 payload=[store.get((rank,expert,source_sid,source_leaf,4*source_pair_row+word),('poison',source_sid,source_leaf,word)) for word in range(8)]
 for word in range(8):
  if mask>>word&1:
   wanted=(rank,expert,rec['global_pair_first']-1280*rank+word)
   assert payload[word]==wanted,('word shuffle needed',rec,word,payload[word],wanted)
   dest=(rank,expert,sid,leaf,destination_pair_row,word)
   assert dest not in received
   received[dest]=payload[word]
 full=mask==255
 counts['source_row_pair_fragments']+=1
 counts['full_fragments' if full else 'partial_fragments']+=1
 # Existing unmasked transport carries the partial raw pair into private scratch;
 # candidate local masked copy applies it to the final row pair. No mask on V.
 steps=[]
 if source_sid==sid:
  steps.append('local_copy' if full else 'local_masked_copy')
 elif (source_sid^sid)==1:
  steps.append('v_pair')
  if not full:steps.append('local_masked_copy')
 elif (source_sid%2)==(sid%2):
  steps.append('wide_tier')
  if not full:steps.append('local_masked_copy')
 else:
  steps+=['wide_tier','v_pair']
  scratch[(sid^1,leaf)]=max(scratch[(sid^1,leaf)],2)
  if not full:steps.append('local_masked_copy')
 if not full and source_sid!=sid:scratch[(sid,leaf)]=max(scratch[(sid,leaf)],2)
 for step in steps:route_counts[step]+=1
 rec=dict(rec,mask_hex=f'{mask:02x}',pairs=1,steps=steps,unmasked_transport=True)
 fragments.append(rec)
assert len(coverage)==4*7*160
assert all(m==255 for m in coverage.values())
assert len(received)==4*7*1280
assert CAPTURE_BASE+7*CAPTURE_STRIDE <= 4*SCRATCH_ROW
assert SCRATCH_ROW+2 <= FF.ASSEMBLED
# Independent legacy pair-aligned equal80 fixture is comparison only, not current placement.
# Candidate current full-mask adjacent source+destination pairs can be packed up to four.
packed=[]
for rec in fragments:
 if packed:
  prev=packed[-1]
  same=all(prev.get(k)==rec.get(k) for k in ['rank','expert','source_sid','source_leaf','sid','leaf','mask_hex','steps'])
  contiguous=rec['source_row']==prev['source_row']+2*prev['pairs'] and rec['row']==prev['row']+2*prev['pairs']
  if same and contiguous and prev['mask']==255 and rec['mask']==255 and prev['pairs']<4:
   prev['pairs']+=1;continue
 packed.append(dict(rec))
packed_routes=Counter()
for p in packed:
 for step in p['steps']:packed_routes[step]+=1
# Mutation controls affect only model copies, never production/source arrays.
mutants={}
first_partial=next(x for x in fragments if x['mask']!=255)
mutants['legacy_force_all_words_would_overwrite']=first_partial['mask']!=255
mutants['missing_complement_detected']=any((m & ~first_partial['mask'])!=255 for pair,m in coverage.items() if pair==(first_partial['rank'],first_partial['expert'],first_partial['sid'],first_partial['leaf'],first_partial['row']))
mutants['old_no_pad_breaks_global_word_slot']=any(((local-start)%64)%8!=local%8 for start,count in spans for local in range(start,start+count))
# Old64-word stride with a nonzero capture pad overlaps a following expert's block.
mutants['old_stride_overlaps_padded_full_chunk']=any(start%8 and count>=64 for start,count in spans)
assert all(mutants.values()),mutants
out=r/'final_ffn_mask_map_2320';out.mkdir(exist_ok=True)
plan=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json')
model=dict(schema='opentallas.s81.final-ffn-actual-span-masked-copy-model.v1',status='MODEL_ONLY_NOT_ADOPTED',source_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),topology=XP.TP.describe(),actual_source_spans=spans,actual_counts=[len(sl) for sl in deal],rom_ownership_changed=False,row_tags_changed=False,checkpoint_values_changed=False,down_phases_before=phases,down_phases_after=phases,phase_delta=0,rank_count=4,expert_slots=7,rank_words=1280,exact_raw_words=len(received),destination_pair_count=len(coverage),descriptor_count=len(descriptors),capture=dict(old_stride_words=64,proposed_stride_words=72,old_rows_per_expert=16,proposed_rows_per_expert=18,old_rows_per_leaf=112,proposed_rows_per_leaf=126,extra_rows_per_leaf=14,old_capture_rows=[128,240],proposed_capture_rows=[128,254],per_source_padding=[start%8 for start,count in spans],rbase_rcnt_unchanged=True,capacity_increase_bytes_per_leaf=14*4*4),scratch=dict(rows=[SCRATCH_ROW,SCRATCH_ROW+2],max_rows_per_leaf=2,unique_leaf_slots=len(scratch),bytes_all_named_leaf_slots=sum(scratch.values())*16,lease_qualified=False,reuse='one fragment at a time; must book transport then local masked copy before reuse'),counts=dict(counts),unpacked_transport_steps=dict(route_counts),full_mask_bulk_max_pairs=4,bulk_packed_packet_count=len(packed),bulk_packed_transport_steps=dict(packed_routes),mutants_caught=mutants,scope='actual source107/53 ownership and numeric row tags retained; CAP mutable-address padding + reserved capture stride + candidate local masked copy only; no new RTL, images, physical timing, SRAM lifetime or token-rate qualification',required_gates=['actual VPX/capture scratch leases','model-priced new mask metadata register/bit-liveness path','smallest full107/53 CAP-XR-VP masked-store exactness with miter/mutant','full-shape context TT setup/FF hold','actual static transport/issuer/control reservation calendar'])
(out/'model.json').write_text(json.dumps(model,indent=1)+'\n')
(out/'descriptors.json').write_text(json.dumps(descriptors,indent=1)+'\n')
(out/'fragments.json').write_text(json.dumps(fragments,indent=1)+'\n')
(out/'bulk_packets.json').write_text(json.dumps(packed,indent=1)+'\n')
print('FFN_ACTUAL_SPAN_MASK_MODEL',json.dumps({k:model[k] for k in ['actual_counts','exact_raw_words','destination_pair_count','counts','unpacked_transport_steps','bulk_packed_packet_count','bulk_packed_transport_steps','mutants_caught']}))
