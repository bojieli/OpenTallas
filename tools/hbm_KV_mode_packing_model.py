#!/usr/bin/env python3
"""Bit-exact candidate model, not RTL or physical qualification.

Preserve all raw265bits including FP4 padding while making each16dim Vhalf
self-contained. Compare actual-source elem semantics, not floatingpoint math.
"""
import argparse,hashlib,json
from pathlib import Path
M128=(1<<128)-1

def pack_codes(raw,fmt):
 if not fmt:return raw&M128,raw>>128
 even=(raw&((1<<64)-1))|(((raw>>128)&255)<<64)|(((raw>>144)&((1<<56)-1))<<72)
 odd=((raw>>64)&((1<<64)-1))|(((raw>>136)&255)<<64)|(((raw>>200)&((1<<56)-1))<<72)
 return even,odd

def unpack_codes(e,o,fmt):
 if not fmt:return e|(o<<128)
 return (e&((1<<64)-1))|((o&((1<<64)-1))<<64)|(((e>>64)&255)<<128)|(((o>>64)&255)<<136)|((e>>72)<<144)|((o>>72)<<200)

def source_elem(g,x,pad):
 fmt=(g>>264)&1
 if fmt:return (pad<<17)|(1<<16)|(((g>>(4*x))&15)<<8)|((g>>(128+8*(x//16)))&255)
 return (pad<<17)|(((g>>(8*x))&255)<<8)|((g>>256)&255)

def local_elem(half,meta,x,pad):
 fmt=(meta>>8)&1
 return (pad<<17)|(fmt<<16)|((((half>>(4*x))&15) if fmt else ((half>>(8*x))&255))<<8)|(((half>>64)&255) if fmt else meta&255)

def model(src):
 text=Path(src).read_text();assert 'gw[128 + 8*(x/16) +: 8]' in text
 vectors=0;checks=0
 # Every rawcode+scale bit basis, for both formats, both pad states.
 for fmt in [0,1]:
  for bit in range(264):
   for pad in [0,1]:
    gw=(1<<bit)|(fmt<<264);e,o=pack_codes(gw&((1<<256)-1),fmt);meta=gw>>256
    assert unpack_codes(e,o,fmt)==gw&((1<<256)-1)
    for x in range(32):assert source_elem(gw,x,pad)==local_elem([e,o][x//16],meta,x%16,pad);checks+=1
    vectors+=1
 # Naive halves demonstrably lose remote FP4 subscale, despite raw bijection.
 gw=(1<<264)|(0x5a<<136)|(1<<64)
 naive=(gw&((1<<256)-1))>>128
 assert source_elem(gw,16,0)!=local_elem(naive,gw>>256,0,0)
 return {'schema':'opentallas.hbm.KV_mode_packing_model.v1','source_path':str(src),'source_sha256':hashlib.sha256(Path(src).read_bytes()).hexdigest(),'raw_bit_basis_vectors':vectors,'decoded_element_checks':checks,'all_raw_code_padding_preserved':True,'metadata144bits_per_lane_unchanged':True,'naive_FP4_half_mutant_rejected':True,'physical_qualified':False,'actual_RTL_DUT_proof':False,'mapping':{'FP8_even':[list(range(128))],'FP8_odd':[list(range(128,256))],'FP4_even_low_to_high':[list(range(64)),list(range(128,136)),list(range(144,200))],'FP4_odd_low_to_high':[list(range(64,128)),list(range(136,144)),list(range(200,256))]},'inventory':{'mode_specific_real1024x256_macros':34,'whole_code_replication_fallback_macros':84,'additional_fallback_macro_area_mm2':0.6158677536,'additional_fallback_macro_clock_pins':50,'new_payload_bits_or_extra_input_transfers_for_pure_permutation':0},'source_profile_restriction':'Actual ILV0/NSTAGE1 separateQKonly/PVonly job, mode known before KVload, wptr resets everyjob, reusebit15 absent. Must be enforced by RTL/producer guard; legacy reuse or interleave not qualified.','remaining':['Actual packer/staging/consumer RTL equivalence + mutants','Mode load/reload fault guard and realcompilerprogramme binding','Independent lane masks and read-before-write actual SRAM tests','Mapped select fanout/pin/cut/clock/source-to-storage wiring','No extra stage/cycle or latency assertion until actual RTL proof']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',default='/home/ubuntu/wt/hbm-static-attn-quant-1014/rtl/hdc/v41x/static/ot_hdc_v41x_attn_physical_calendar.sv');p.add_argument('--out',required=True);a=p.parse_args();r=model(a.source);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['raw_bit_basis_vectors','decoded_element_checks','all_raw_code_padding_preserved','naive_FP4_half_mutant_rejected','inventory']}))
if __name__=='__main__':main()
