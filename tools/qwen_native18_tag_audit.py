#!/usr/bin/env python3
"""Source-bound arithmetic ABI audit, not a ring/lifecycle RTL qualification."""
import hashlib,json
from pathlib import Path
p=Path('rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv')
s=p.read_text()
assert "assign c_tag      = {tok_r, pos_r[7:0], {(8 - DAW){1'b0}}, seg};" in s
p2=Path('rtl/physical/ot_qwen_coll_xfifo_native.sv')
s2=p2.read_text()
assert '.WSQ(546),.WCQ(517)' in s2
legacy=lambda t,p,g: ((t<<16)|((p&255)<<8)|g)&0xffffffff
compact=lambda t,p,g: (t<<14)|((p&255)<<6)|g
# Distinct proposed minimum full identity: token18, position13, segment6.
full=lambda t,p,g: (t<<19)|(p<<6)|g
samples=[]
for a,b,pos,seg in [(1,65537,8191,0),(65535,131071,8191,63),(20863,151935,8191,63)]:
    assert legacy(a,pos,seg)==legacy(b,pos,seg)
    assert compact(a,pos,seg)!=compact(b,pos,seg)
    samples.append({'token_a':a,'token_b':b,'position':pos,'segment':seg,'legacy_tag':legacy(a,pos,seg),'compact_a':compact(a,pos,seg),'compact_b':compact(b,pos,seg)})
for token in range(151936):
    for seg in (0,1,63):
        v=compact(token,8191,seg)
        assert v>>14==token and ((v>>6)&255)==255 and (v&63)==seg
for pos in range(8192):
    for token in (0,65535,65536,131072,151935):
        v=full(token,pos,63)
        assert v>>19==token and ((v>>6)&8191)==pos and (v&63)==63
assert compact(151935,8191,0)==compact(151935,7935,0)
x={'schema':'native18-tag-source-audit-v1','source_hashes':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (p,p2)},'legacy_truncation_examples':samples,'compact_packing':'token18 + position_low8 + segment6','compact_vocabulary_verified':151936,'compact_full_position_safe':False,'position_collision':{'token':151935,'position_a':8191,'position_b':7935,'segment':0,'tag':compact(151935,8191,0)},'minimum_full_identity_bits':37,'minimum_plus_stage6_epoch16_bits':59,'full_token_position_reconstruction_cases':8192*5,'return_has_tag':False,'required_contract':'A distinct native transport must carry full identity (or prove a source-bound stage/position/epoch/drain fence) and prevent stale return acceptance before native18 TAG32 can qualify.','physical_qualified':False,'ring_lifecycle_qualified':False}
print(json.dumps(x,indent=2))
