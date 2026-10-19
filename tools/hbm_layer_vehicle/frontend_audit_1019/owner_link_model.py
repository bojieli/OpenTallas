"""Enumerate legal source topology, separately from unproved timing/RTL integration."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[3]
paths=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm4pc_cdc_rel_sram_id.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_prefetch_overlap_owner_rel_id.sv'];sources={p:(root/p).read_text() for p in paths};c,o=sources.values()
for text,needle in [(c,"reserve_pcs={sm_s,2'd3,sm_s,2'd2,sm_s,2'd1,sm_s,2'd0}"),(c,".pc_id({id_sm,2'(pc)})"),(o,"ordinal_q[alloc]<={t[8:0],2'b0}+lane"),(o,"response_ordinal=ordinal_q[ret]+{7'd0,word_offset,2'b0}"),(o,"word_offset=permuted_q[ret]?(kr_beat[1:0]^row_low_q[ret]):2'd0")]:assert needle in text,needle
cases=wronglane=wrongtarget=0
for sm in range(8): # Source pc_id is5 bits: physical SM strap3 + lane2.
 pcs=[(sm<<2)|p for p in range(4)]
 for pc in range(4):
  assert [j for j,x in enumerate(pcs) if x==((sm<<2)|pc)]==[pc]
  for rows in range(1,65):
   total=17*rows;words=(total+3-pc)//4;t=0;ordinals=[]
   while t<words:
    length=4 if words>=t+4 else 1
    for rowlow in range(4):
     for beat in range(length):
      off=(beat^rowlow) if length==4 else 0
      ordinal=((t&511)<<2)+pc+(off<<2);target=ordinal&7
      assert ordinal&3==pc and target in (pc,pc+4)
      assert target>>2==(ordinal>>2)&1
      assert ordinal<total
      wronglane+=((ordinal^1)&3)!=pc
      wrongtarget+=((target>>2)^1)!=((ordinal>>2)&1)
      cases+=1
    ordinals.extend((t+off)*4+pc for off in range(length));t+=length
   assert sorted(ordinals)==list(range(pc,total,4))
assert cases and wronglane==cases and wrongtarget==cases
print(json.dumps(dict(status='PASS',scope='source-bound topology enumeration only; not native timing, miter, tag lifecycle, capacity or reset proof',source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},sm_straps=8,pc_lanes=4,row_counts=[1,64],rowlow_values=4,legal_return_cases=cases,wrong_lane_mutant_rejections=wronglane,wrong_target_mutant_rejections=wrongtarget,payload_bits=285,link_envelope_bits=290,ring_slots=4,runtime_bits_per_link=1160),indent=2))
