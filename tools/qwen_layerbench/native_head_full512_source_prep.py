#!/usr/bin/env python3
"""Bounded genuine mask/code join and public ROM/PART1 source frontier; no simulation."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mask-rows',type=Path,required=True);p.add_argument('--code-crop',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads(a.mask_rows.read_text());c=json.loads(a.code_crop.read_text());assert c['code_bytes']==720896
records={(x['tile'],x['column']):x for x in m['records']};checked=0;pad_checked=0;contexts=[]
for block,tilefirst,words in [(0,0,list(range(64))),(148,512,[1536+8*k+s for k in range(8)for s in range(3)])]:
 crop={x['word']:x for x in c['records']if x['block']==block};assert set(crop)==set(words)
 for tile in range(tilefirst,tilefirst+128):
  cols=[records[(tile,col)]for col in [0,1]]
  for col in cols:
   assert col['bank']==4 and len(col['rows'])==8
   assert all(int(row,16)>>2048==0 for row in col['rows'])
  for word in words:
   resident=18432+word;local=resident-4*4096;row=local//8;slot=local%8
   vals=[]
   for col in cols:
    mask=int(col['rows'][row-col['physical_row_first']],16)
    vals.append(sum(((mask>>(8*b+slot))&1)<<b for b in range(256)))
   actual=vals[0]|(vals[1]<<256);rec=crop[word];shift=128*(4*tile-rec['group_first']);assert 0<=shift<=128*(512-4)
   expected=(int(rec['hex'],16)>>shift)&((1<<512)-1)
   assert actual==expected,('GENUINE_MASK_CODE_DIFF',tile,word)
   checked+=64
  if block==148:
   for word in range(1536,1600):
    if word in crop:continue
    local=2048+word;row=local//8;slot=local%8
    for col in cols:
     mask=int(col['rows'][row-col['physical_row_first']],16)
     assert sum(((mask>>(8*b+slot))&1)<<b for b in range(256))==0,('NONZERO_GENUINE_PAD',tile,word)
     pad_checked+=32
  contexts.append(dict(native_fetch_words=64,block=block,tile=tile,i_gbase=4*tile,group_interval=[4*tile,4*tile+4],local_code_words=len(words),code_bytes=64*len(words),masks=[{k:x[k]for k in ['column','source','manifest_sha256','file_bytes','physical_row_first']}for x in cols]))
assert checked==720896 and pad_checked==327680
root=Path('/home/ubuntu/OpenTallas');paths=['rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv','rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_romleaf_rr.sv','rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv','rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv','rtl/physical/ot_qwen_tile_romleaf.sv','physical/asap7_memory_macros_v2/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v']
readset={str(root/f):hashlib.sha256((root/f).read_bytes()).hexdigest()for f in paths}
passed=Path('/home/ubuntu/coord/tmp/codex-native-head-leaf-packet4/src')
for f in paths:
 choices=list(passed.glob('*_'+Path(f).name));assert len(choices)==1,f
 assert hashlib.sha256(choices[0].read_bytes()).hexdigest()==readset[str(root/f)],('PASSED_NATIVE_SOURCE_DIFF',f)

result=dict(status='SOURCE_PREP_AND_USED_MASK_CODE_JOIN_ONLY_NO_EXECUTION',used_code_bytes_compared=checked,actual_padded_code_bytes_observed_zero=pad_checked,contexts=contexts,context_count=256,perblock_contexts=128,genuine_masks=dict(files=512,existing_file_bytes=m['mask_file_bytes'],physical_row_bytes_read=m['physical_row_bytes_read'],wholemask_hash_qualification='manifest-declared only; used physicalrows checked against SHAguardedgenuine crop; full files must hashguard before future execution',manifest=m['manifest'],manifest_sha256=m['manifest_sha256']),counts=dict(count_scope='actual IL8 one-round reads64 forbothcontexts; referenceusefulsubset64block0/24tail, notnativefetchcount; full4IBwould1600readspercontext',actual_ROMconverter_BF16_response_payload_bytes=2097152,minimum_transcript_bytes_with16byte_metadata_perword=2359296,PART1_code_reads=16384,raw_TG4_vectors=16384,raw_TG4_scalar_prefix_values=262144,reference_required_TG4_vectors=11264,reference_required_TG4_scalar_prefix_values=180224,logical_L6_stream_contexts=16,logical_L6_vectors=704,logical_L6_scalar_prefix_values=11264),public_boundary=dict(executor='unchanged ot_qwen_w12_matvec_part PART1 G4/W16/IL8/GT3072/GBASE_PORT1/NX0/NW18/SMIN7/WCONV1/MEM_EXTRA8; i_gbase immutable per fresh process',rom_producer='unchanged ot_qwen_romleaf_logic with original req_m→actual ot_rom_4096x266_m8→rd[255:0] wiring for each column',macro_binding='actual public macro VIAMAP parameter may use fixed component filenames in distinct immutable fresh-process contexts; full genuine source path/tile/column/hash recorded; INSTANCE remains empty. This is generic macro content-context ABI, NOT selected ROM_TILE fullleaf identity retarget or wrapper proof',ROM_latency='wromrequest publicationM→preseamrelayM+1→nativeleafMPRM+2→actualmacroM+3→capM+4→expandAM+5→expandBM+6→groupgM+7→relayrM+8→RQR M+9; MEM_EXTRA8 means returnM+1+8. Exact REGROOT3/RPH3/ROM_ARELAY2/CAP2=1/CAPX2/RQR1; noL1extra',X_latency='selected NX0 gives NPX0: no x_re/x_addr generation. Keep NX0 and sourcejoin context c=(i_gbase+g)%512,k from realwromaddress, Hindex8*c+k; one registeredHread+actualdelay8 gives x_q returnM+9; BF16RNEH expanded low16zero. No invented Xrequest or fittedXLoffset',transcript='must record contextid/requestordinal/wromaddr/launchcount/returncount1024bitBF16response; consumer rejects wrong request/address/date/context. Replay actual executed ROMproducer data only, never substitute expectedoracle code/weights',clocks='functional single-region clock cut only where exactselected39literal clk binding proves it; no physicalphase/START claim'),limitations=['No RTL/elaboration/simulation/build performed','One selected fullleaf ELF cannot change ROM_TILE or maskINSTANCE at runtime; its static guard stays unchanged','Public ROM macro+converter boundary avoids identity recompile only by explicitly changing component scope; it cannot be called selected fullleaf execution','PART1 numeric executable cannot be claimed identical selected timing until source closure/actual settings pinned and authenticatedROM/X returns proved','Exact actual L6 outer faces/node and source clock countframes remain separate parent-owned composition'],readset=readset,input_sha256={str(a.mask_rows):hashlib.sha256(a.mask_rows.read_bytes()).hexdigest(),str(a.code_crop):hashlib.sha256(a.code_crop.read_bytes()).hexdigest()})
a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],'contexts',len(contexts),'bytes',checked)
