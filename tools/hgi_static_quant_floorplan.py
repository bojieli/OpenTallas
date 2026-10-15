#!/usr/bin/env python3
"""Geometry and real closed-decoder pin audit for the static Quant prototype.
This is an admission model, never a physical closure gate. New transport/programme
pins and PG/timing are still unmeasured. Closed decoder LEFs are immutable inputs.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/hbm_static_quant_1015/physical_prototype.json'


def main():
    dims={'transport':(432.,324.),'programme':(216.,129.6),'dxl':(120.96,120.96),
          'dbq':(120.96,120.96),'daq':(129.6,129.6)}
    pos={'transport':(432.,162.),'programme':(162.,216.),'dxl':(918.,324.),
         'dbq':(1051.92,324.),'daq':(918.,180.)}
    parent=(1399.656,648.);halo=5.4;pins={};sources={};clocks={}
    for n in ['dxl','dbq','daq']:
        base=ROOT/f'physical/ref_tile/qw_{n}_ref/views/ot_hgi_qw_{n}'
        lef=base/f'ot_hgi_qw_{n}.lef'
        text=lef.read_text();actual=tuple(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups()))
        assert actual==dims[n]
        sources[str(lef.relative_to(ROOT))]=hashlib.sha256(lef.read_bytes()).hexdigest()
        sources[str((base/'insertion.json').relative_to(ROOT))]=hashlib.sha256((base/'insertion.json').read_bytes()).hexdigest()
        clocks[n]=json.loads((base/'insertion.json').read_text())
        pins[n]={}
        for pin,body in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\bEND\s+\1',text,re.S):
            rect=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)
            if rect:
                x0,y0,x1,y1=map(float,rect[0]);pins[n][pin]=(pos[n][0]+(x0+x1)/2,pos[n][1]+(y0+y1)/2)
    boxes={n:[*pos[n],pos[n][0]+dims[n][0],pos[n][1]+dims[n][1]] for n in dims}
    for n,b in boxes.items():assert b[0]>=halo and b[1]>=halo and b[2]<=parent[0]-halo and b[3]<=parent[1]-halo,(n,b)
    overlap=[]
    names=list(boxes)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            aa,bb=boxes[a],boxes[b]
            if min(aa[2]+halo,bb[2]+halo)>max(aa[0]-halo,bb[0]-halo) and min(aa[3]+halo,bb[3]+halo)>max(aa[1]-halo,bb[1]-halo):overlap.append([a,b])
    assert not overlap
    links=[]
    for a,ap,b,bp,count in [('dxl','xs','dbq','xs',1024),('dxl','xs','daq','xs',1024),
       ('dxl','xb','dbq','xb',1024),('dxl','xa','daq','xa',1024),('dbq','byo','daq','byo',512),
       ('dbq','bvo','daq','bvo',1),('dbq','bfo','daq','bfo',1)]:
        lengths=[]
        for i in range(count):
            pin_a=ap if count==1 else f'{ap}[{i}]';pin_b=bp if count==1 else f'{bp}[{i}]'
            p,q=pins[a][pin_a],pins[b][pin_b];lengths.append(abs(p[0]-q[0])+abs(p[1]-q[1]))
        links.append(dict(source=f'{a}.{ap}',target=f'{b}.{bp}',bits=count,max_manhattan_um=max(lengths),mean_manhattan_um=sum(lengths)/count))
    assert max(l['max_manhattan_um'] for l in links)<500
    result=dict(schema='opentallas.hbm-static-quant-physical-prototype.v1',qualified=False,
        parent=dict(origin_um=[14736.384,15958.08],outline_um=list(parent),orientation='R0',assignment='H-DIE provisional'),
        child_bboxes_um=boxes,child_halo_um=halo,halo_overlaps=overlap,
        decoder_pin_links=links,decoder_sources_sha256=sources,
        transport_pins=dict(N='8xrq17+8xrr257=2192',S='8xwq281=2248',E='dec_x1024+header128+valid1+result512+vo/fault/decode3=1668',W='programme48'),
        assumed_signal_track_pitch_um=0.096,max_track_utilization=0.60,
        transport_cut_N=2192/(432/.096),transport_cut_S=2248/(432/.096),transport_cut_E=1668/(324/.096),
        programme_macro=dict(outline_um=[174.744,70.470],local_origin_um=[21.6,21.6],halo_um=5.4),
        clock_entries=['ck_program','ck_transport','ck_dxl','ck_dbq','ck_daq'],
        closed_clock_delivery={n:dict(TT_R_ps=clocks[n]['tt']['boundary']['mean'],
            TT_boundary_spread_ps=clocks[n]['tt']['boundary']['max']-clocks[n]['tt']['boundary']['min'],
            policy='deliver phi-R at this child clock pin') for n in clocks},
        outstanding=['source-matched child ABI/reset/phase/pin-register audit',
                     'new leaf synthesis/CTS/TT/FF/DRC/PG closure','actual pin assignment and channel-layer capacity',
                     'new programme/transport pins to closed decoder pins timing/reach',
                     'actual NW bank station latency and channels','host/global launch programme target binding'])
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(halo_overlaps=0,max_existing_decoder_hop_um=max(l['max_manhattan_um'] for l in links),qualified=False)))


if __name__=='__main__':main()
