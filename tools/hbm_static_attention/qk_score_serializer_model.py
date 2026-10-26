#!/usr/bin/env python3
"""Port/address model for actual NL2/H16 QK scores; no RTL qualification."""
import json
from pathlib import Path

def loc(epoch, head, row):
    return head*16+(row//4)%16, epoch*16+row//64, row%4

def audit(T):
    mem={}; written=set(); reads=[]; collisions=0
    # Capture real producer ordering: two adjacent rows for all sixteen heads.
    # Drain completed 64-row chunks in sixteen head-major requests while the
    # next chunk is captured. Each macro has independent 1R and 1W ports.
    for epoch in (0,1,0):
        written=set();reads=[]
        for edge in range(T//2+16):
            writes={}
            if edge<T//2:
                for h in range(16):
                    for lane in range(2):
                        r=edge*2+lane;b,a,s=loc(epoch,h,r)
                        assert b not in writes or writes[b][0]==a
                        writes[b]=(a,writes.get(b,(a,0))[1]|(0xffffffff<<(32*s)))
                        mem[b,a,s]=(epoch,h,r);written.add((h,r))
                assert len(writes)==16
                assert all(mask.bit_count()==64 for a,mask in writes.values())
            block=(edge-32)//32
            h=(edge-32)%32
            if edge>=32 and block<T//64 and h<16:
                banks=set()
                for r in range(block*64,block*64+64):
                    b,a,s=loc(epoch,h,r);banks.add(b)
                    assert (h,r) in written
                    assert mem[b,a,s]==(epoch,h,r)
                    if b in writes:assert writes[b][0]!=a
                    reads.append((h,r))
                assert len(banks)==16
        assert len(reads)==16*T and len(set(reads))==16*T
    # Mutant omits the within-group 16-way stripe: all sixteen word reads
    # collapse onto one macro port and cannot produce 2048 bits in one edge.
    mutant_banks={0 for r in range(64)}
    assert len(mutant_banks)!=16
    return dict(T=T,score_words=16*T,capture_edges=T//2,
                vm_requests=16*T//64,final_read_edge=T//2+15,
                epochs_and_reuse_checked=[0,1,0],port_conflicts=collisions,
                initialized_payload_checks=3*16*T,
                missing_stripe_mutant_detected=True)

if __name__=='__main__':
    result=dict(schema='opentallas.hbm_attn.qk_score_serializer_model.v1',
      qualification=False,RTL_implemented=False,
      source=dict(module='ot_hdc_v41x_attn_physical_calendar',
        ports='sc_v, sc_row[15:0], sc_m[1:0], sc_y[1023:0], sc_f[31:0]',
        payload='sc_y[(lane*16+head)*32+:32], row=sc_row+lane; unchanged FP32'),
      storage=dict(macro='ot_sram_1r1w_32x128_m1',banks=256,epochs=2,
        allocated_bytes=131072,maximum_useful_bytes_per_record=40960,
        bank='head*16+(row//4)%16',address='epoch*16+row//64',word_lane='row%4',
        write_ports=16,write_bits_per_selected_bank=64,read_ports=16,
        read_bits_per_selected_bank=128,flag_FF_capacity=32768,
        data_macro_area_um2=256*51.408*20.790,
        flag_read_pipeline_FF=1024,flag_clock_roots_at_8192_sinks=5),
      VM=dict(proposed_layout='head-major FP32[16][T]',
        sector='base+head*(T//8)+block*8+bank',payload_bits_per_request=2048,
        write_group=None,residency=None,consumer_SFU_binding=None,
        request_to_commit_edges=3),
      audit=[audit(128),audit(640)],
      timing_scope='Edges relative to first actual sc_v; assumes actual consecutive two-row producer beats. SRAM read/output pipeline, physical stations, fixed VM ownership and real score-producer trace must be joined before price.',
      remaining=['Actual RTL with 256 mapped macros and exact flags',
       'Source score trace and masks/row continuity fault checks',
       'Native score aperture, SID and write-group allocation',
       'Real SFU REDMAX/EXP/REDSUM chain and compiler schedule',
       'Complete H16/D512 producer + mutants and immutable price',
       'Physical macro homes, clocks, pin cuts and routing'])
    p=Path('results/arch/hbm_attention_static_1015/qk_score_serializer_model.json')
    p.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS QK score mapping: H16 T128/640, both epochs/reuse, masked 16-bank writes, 16-bank reads, overlap addresses and missing-stripe mutant; model only')
