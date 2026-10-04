#!/usr/bin/env python3
"""Read-only frozen W6 source/port check for peer integration; no job launcher."""
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv':'f86ac8c22c4ac33c7cee959ead1b04b59279bacef1d99c737e21c84ed8a8a396',
 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv':'4cb22a293abd6891d5fa0b3a2ac1f41074a08ef4a4e664d06fa23162e2e58e39',
 'tools/hbm_w6_local_rtl_model.py':'a24b7da94174eb631cb11fe068af88ed2542b42f8ced7f7e98c89bd08a214e06',
 'tools/hbm_w6_fullwidth_model.py':'d4509b638f860975768e157bf696bb9e9565e771b75b8dcfdfb90aa1621cac82'}
RTL=next(iter(PINS))
def need(ok,message):
 if not ok:raise ValueError(message)
def ports(source):
 header=source.split(')(\n',1)[1].split('\n);',1)[0];result={};direction=None;width=None
 for part in header.split(','):
  part=part.strip();m=re.fullmatch(r'(input|output)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)',part)
  if m:
   direction=m[1];width=1 if m[2] is None else abs(int(m[2])-int(m[3]))+1;name=m[4]
  else:
   need(direction is not None and re.fullmatch(r'\w+',part),'unsupported port declaration');name=part
  need(name not in result,'duplicate port');result[name]=dict(direction=direction,bits=width)
 return result

def verify(peer_root=ROOT):
 peer_root=Path(peer_root);checked={};verified={}
 for path,expected in PINS.items():
  raw=(peer_root/path).read_bytes();actual=hashlib.sha256(raw).hexdigest();need(actual==expected,'frozen W6 source drift: '+path);checked[path]=actual;verified[path]=raw
 source=verified[RTL].decode();p=ports(source)
 need("parameter bit ENABLE=1'b0" in source,'defaultoff parameter')
 return dict(schema='W6_FROZEN_PEER_INTERFACE_R1',verdict='PASS_FROZEN_SOURCE_AND_INTERFACE_ONLY',pins=checked,ports=p,
  identity_layout_MSB_to_LSB=[dict(field='physical_PC',bits=7),dict(field='client',bits=3),dict(field='original_tag',bits=32),dict(field='generation',bits=4),dict(field='RFslot',bits=9)],
  clients=6,KV_client=5,default_ENABLE=0,retained_raw_bits_per_SM=71,retained_protected_bits_per_SM=144,
  actual_join_qualified=False,physical_qualified=False,
  caller_obligations=[
   'req handshake retains exact owner46+slot9 and req_internal_SIMD origin; one active owner per instantiated fence.',
   'host_ack must originate from both-copy write visibility with retained55bit source identity. Bare legacy ACK plus fence-local epoch is insufficient.',
   'simd_ack_retire is actual internal SIMD retirement, separately retained from host ACK; do not substitute host sink acceptance.',
   'visible handshake precedes actual consumer handshake, aggregate validated child reverse, parent reverse and matched reverseCDC.',
   'Assert completion valid only in its ordered phase. Foreign, duplicate, wrong-origin and premature valids latch fault, rather than harmlessly queueing until ready.',
   'Drive alldrain_live[8:0] from CURRENT scoped source debt under admission-stop, including bothCDCs and pending certificates; match55bit identity, has_owner and reset_scope.',
   'Runtime rst_n is synchronous quarantine retaining owner; hold across edges, synchronize release and drain before reuse. por_n is coordinated global cold reset only.',
   'Retain all frame/child identities beyond assembler data reuse. One fence is not an8-frame/128-child directory; source caller must price and implement sequencing/storage.',
   'No static PC order, software ledger or bench-created receipt is an installed source producer.' ])
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--peer-root',type=Path,default=ROOT);a=ap.parse_args();print(json.dumps(verify(a.peer_root),indent=2,sort_keys=True))
