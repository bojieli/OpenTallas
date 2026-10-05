#!/usr/bin/env python3
"""Sizing before the additive canonical-layout nearHBM memory adapter RTL."""
import json
import ast
from pathlib import Path
# Read the pinned unified constant without importing unrelated physical studies.
_src = Path(__file__).with_name("uarch_model.py").read_text()
DFF_UM2 = next(ast.literal_eval(n.value) for n in ast.parse(_src).body
    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DFF_UM2" for t in n.targets))

def model(r=8, dq=32, ctx=8192):
    # K: two heads x 16 live tiles. V: per-engine chunk ring, 16 four-row chunks.
    ks, vs = 32, r * 16
    coded_bits = 4 * ((ks*64+vs*16)*288 + r*dq*72 + (ks+vs)*216 + r*216 + r*1024 + 512*72 + 3*72)
    mux_bits = 4*r*128*16*8
    area = (coded_bits*DFF_UM2 + mux_bits*0.2 + 4*8192)/1e6
    b = 2*2*ctx*128
    # 16 sectors/request, same maximum burst/beat interface as actual REAL_MEM.
    commands = 2*ctx//4 + 2*((ctx+15)//16)*4
    return dict(schema='opentallas.qwen-nearhbm-memory-adapter-sizing.v1', default_off=True,
      actual_interfaces='unchanged REAL_MEM kvd/kv_we and kv_ok/kv_write_drained; HBM tagged request/response + WR_ACK',
      layout='canonical sector owner bits[10:9]; K 16-position tile/64 sectors, V four-position chunk/16 sectors',
      replicas=4, row_engines_per_stack=r, credits_per_engine=dq,
      storage=dict(k_tiles_per_stack=ks,v_chunks_per_stack=vs,queue_entries_per_stack=r*dq,coded_bits_die=coded_bits),
      protection='SECDED72 per64 payload/control bits; no new ROM ECC; immutable tag/kind/gen/beat validation',
      compute=dict(macs_per_cycle=0,macs_per_byte=0),
      ports_bytes_per_cycle=dict(HBM_per_stack_max=32*32,request_payload_max=16*32,row_return_per_stack=r*128),
      boundary_bits_per_cycle=dict(row_request=4*r*15,row_return=4*r*(1024+1),HBM_return=4*32*(256+14+4+1)),
      mux_bit_equivalents=mux_bits,fanout='stack-local tile sharing; no new die-wide data bus',
      area_mm2_die_estimate=area,area_basis='DFF upper bound and 0.2um2/mux bit; macro banking/loaded timing unmeasured',
      slot_mm2_each_estimate=area/4,slot_fit='reserve in nearHBM stack slot; actual route/SSFF required',
      routing=dict(required_tracks_local=8192,capacity_tracks='requires physical owner measured channel; no fit claim'),
      context=ctx,bytes_layer_die=b,read_commands_layer_die=commands,
      composed_latency=dict(layer_memory_lower_bound_hclk_cycles=max(b//(4*1024),commands//4),
       first_K_tile='4 accepted bursts + actual HBM bank/refresh latency, then registered exact row extraction',
       refill='finite credits/coalesced landing; actual cycles required, no old ideal bucket timing credit',
       added_row_extract_cycles=1,model_owner='Peirce composes measured token contribution; unified model untouched'),
      adoption=False)
if __name__=='__main__': print(json.dumps(model(),indent=2))
