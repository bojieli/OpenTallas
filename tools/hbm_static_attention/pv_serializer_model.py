import json
from pathlib import Path
perm=lambda c:(c&3)|((c&12)<<2)
wb=lambda t,hg,c:(t*4+hg)^perm(c)
assert all(len({wb(t,g,c) for t in range(32) for g in range(4)})==128 for c in range(16))
assert all(len({wb(4*k+d//16,h//4,d%16) for d in range(64)})==64 for h in range(16) for k in range(8))
# A mutant lacking the XOR transpose conflicts at16reads perbank.
assert len({(4*0+d//16)*4 for d in range(64)})==4
p=Path('results/arch/hbm_attention_static_1015/pv_headmajor_serializer_model.json')
p.write_text(json.dumps(dict(schema='opentallas.hbm_attn.pv_serializer_model.v1',qualification=False,canonical_output_layout_pending_HVM=True,source_layout='32tiles x16heads FP32 words per PVbeat c0..15;dim=tile*16+c',candidate_VM_layout='head-major contiguous FP32[16][512],8x256b peredge',physical_memory=dict(data_macro='ot_sram_1r1w_32x128_m1',data_banks=128,depth=32,epochs=2,words_per_record=8192,total_capacity_bytes=65536,macro_area_um2=128*51.408*20.790),write=dict(bank='(tile*4+head//4) XOR ((c&3)|((c&12)<<2))',address='epoch*16+c',word='4 adjacent heads FP32 atfixedtile,c',ports=128,payload_bits_per_edge=16384),read=dict(order='head0..15,64dimension-block k0..7',bank='writebank(tile=4*k+d//16,head//4,c=d%16),d0..63',address='epoch*16+(d%16)',lane='head%4',ports=64,payload_bits_per_edge=2048,commit_edges=128),port_audit=dict(all16writephases_128distinctbanks=True,all128readphases_64distinctbanks=True,untransposedbank_mutant_conflicts_detected=True),fault_sidecar=dict(exact_per_word_flags_required=True,candidate_bits=2*8192,macro_port_assignment=None,possible_flop_implementation='16384 realFF split into>=2 physicalclockroots; notyetpricedormapped'),remaining=['H-VM canonicalheadmajornativeoutputauthority','Exactfaultsidecarcontractandports','Actualtarget49outputprogrammeandWG1bankjoin','RTL fullshape +mutants and measuredprice','Mappedcell/clock/geometry/routing qualification']),indent=2)+'\n')
print('PASS port-conflict model16writephases/128readphases+untransposed mutant; RTL not built')
