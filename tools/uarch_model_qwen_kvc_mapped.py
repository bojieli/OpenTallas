#!/usr/bin/env python3
"""Combined exact option-M mapper/decoder physical reservation."""
import json
import uarch_model as unified
from uarch_model_qwen_kvc_leaf import model as decoder


def model():
    d=decoder();state=4*(256+17+13+16+22+2+1)+200
    area=d['cell_area_bound_um2']+state*unified.DFF_UM2+8000
    return dict(schema='opentallas.qwen_kvc_mapped.v1',model_precedes_rtl=True,
        status='PROPOSED_NOT_ADOPTED',replicas=128,static_masters=1,
        macs_per_cycle=0,compute_intensity_macs_per_byte=0,
        memory_ports=[dict(name='period96_map_lut',read_bytes_per_cycle=1.125,
            bits=4*96*9,read_only=True,ECC=False)],
        input_bits_per_cycle=d['input_bits_per_cycle']-17+7,
        output_bits_per_cycle=d['output_bits_per_cycle'],
        frame_um=d['frame_um'],cell_area_bound_um2=area,
        frame_fit_at_55pct=area<328.32*370.44*.55,
        routing=d['tracks'],data_bytes_per_cycle=32,
        mux_demux='one384entry9bit constant map lookup; no cross-PC data mux',
        fanout='local context pipeline, no new die broadcast',
        flow=dict(initial_credits=16,receiver_fifo_required=16,
            reason='eight forward edges plus credit return cannot sustain one beat/cycle on eight credits',
            receiver_state_bits_per_pc=16*306,receiver_cell_floor_um2=16*306*unified.DFF_UM2,
            receiver_owned_by_unclosed_row_scheduler=True),
        pipeline_edges=8,latency='four map edges plus existing four decoder edges',
        replaces_decoder_latency=True,added_token_cycles=8*36,
        expected_sector='computed internally from captured port and count; count/fence owner remains upstream',
        remaining=['per-PC ordinal ownership/retirement','per-stack window-limit generation',
            'row arbitration','token writeback','global descriptor and fault fence'])
if __name__=='__main__':print(json.dumps(model(),indent=2))
