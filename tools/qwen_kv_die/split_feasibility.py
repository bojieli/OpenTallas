#!/usr/bin/env python3
"""Packing-only Qwen TP8 split candidate; never a contract or route qualification."""
import argparse, hashlib, json
from pathlib import Path

def analyze(source):
    # Current parent request and expanded station allowance, not accepted hard views.
    tw, th, pitch, sh = 399.6, 1442.88, 472.608, 103.68
    margin, rowgap, spine, south = 21.6, 43.2, 5200., 1963.816
    stations_w = 64.8
    positions = []
    for col in range(48):
        x = margin + col * pitch + (spine if col >= 24 else 0)
        for row in range(16):
            y = margin + south + row * (th + rowgap)
            positions.extend([
                dict(name=f't_{col}_{row}', role='tile_request', x=x,y=y,w=tw,h=th),
                dict(name=f's_{col}_{row}', role='station_allowance',x=x+tw+4.104,y=y+(th-sh)/2,w=stations_w,h=sh)])
    width, height = 2*margin + 48*pitch + spine, 2*margin+south+16*th+15*rowgap
    # Grid construction gives disjoint rows and columns; independently check every rectangle pair.
    overlap = []
    for k,p in enumerate(positions):
        for q in positions[k+1:]:
            if p['x'] < q['x']+q['w']-1e-8 and q['x'] < p['x']+p['w']-1e-8 and p['y'] < q['y']+q['h']-1e-8 and q['y'] < p['y']+p['h']-1e-8:
                overlap.append([p['name'],q['name']])
    outside=[p['name'] for p in positions if p['x']<0 or p['y']<0 or p['x']+p['w']>width or p['y']+p['h']>height]
    return dict(schema='opentallas.qwen.split_feasibility.v1',status='PARTIAL_PACKING_ONLY_NOT_ADOPTED',
        source=dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        compute_die=dict(width_um=width,height_um=height,area_mm2=width*height/1e6,
           tiles=768, tile_request_um=[tw,th], column_pitch_um=pitch,
           station_allowance_um=[stations_w,sh],row_channel_um=rowgap,
           spine_reservation_um=spine,south_io_and_word_channel_um=south,
           overlap_count=len(overlap),outside_count=len(outside),positions=positions),
        tp8_link_payload_lower_bound=dict(q_bf16_values=512,new_kv_fp8_values=256,result_fp32_values=512,
           rom_to_kv_bytes_per_layer=1280,kv_to_rom_bytes_per_layer=2048,
           rom_to_kv_512bit_words_per_layer=20,kv_to_rom_512bit_words_per_layer=32,
           raw_payload_bytes_per_cycle=64,control_framing_stalls_excluded=True),
        historical_interface_reference=dict(path='results/arch/qwen_kv_die_20261009/CONTRACT.md',
           phy_area_mm2_per_endpoint=.6047,phy_shoreline_um_per_endpoint=777.6,
           adapter_frame_um=[777.6,518.4],reference_tp=4,current_tp8_verified=False),
        missing_gates=[
            'Exact current tile request and station pins/three-corner timing must close.',
            'All spine hard children, native slab groups, IO hard children and D2D endpoints must constructively fit reserved rectangles.',
            'Tree grouping, 32 X roots, instruction broadcast and clock/reset actual-pin cuts and per-pair reach must pass.',
            '43.2-um row channels are geometric allowances; actual tracks, PG occupancy and cut need proof.',
            'Separate KV/system die must be regenerated from current real 128 head views, 96 controller leaves and other real masters.',
            'TP8 native D2D exactness, credit backpressure, finite buffers and critical-path cycles must be measured.',
            'Actual package PHY/bump availability, HBM topology and energy/cost must be priced.',
            'Full die GRT, SS/FF internal and boundary timing, DRT regions and workload IR remain required.'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    result=analyze(a.source);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result['compute_die'].items() if k!='positions'},indent=2))
