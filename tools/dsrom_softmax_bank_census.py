#!/usr/bin/env python3
"""Source-bound bank pin census; trial rectangle is not route admission."""
import argparse,collections,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    lef=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
    tracks=ROOT/'results/uarch/dsrom_MTP_selected_parent_containment_20261003/inputs/tracks.txt'
    s=lef.read_text(); w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',s).groups())
    pitch=float(re.search(r'make_tracks M4[^\n]*-y_pitch ([\d.]+)',tracks.read_text())[1])
    groups=collections.defaultdict(lambda:collections.Counter()); pins=[]
    for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n',s,re.S):
        name,b=m.groups()
        if not re.search(r'USE (SIGNAL|CLOCK)',b):continue
        x0,y0,x1,y1=map(float,re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',b).groups())
        edge='left' if x0==0 else 'right' if abs(x1-w)<1e-6 else 'other'
        family=name.split('[')[0];groups[family][edge]+=1
        pins.append(dict(name=name,edge=edge,layer=re.search(r'LAYER (\S+)',b)[1],center_um=[(x0+x1)/2,(y0+y1)/2]))
    # Serpentine is only a candidate local bank order; all macro orientations remain R0.
    banks=[]
    for n in range(36):
        row,col=divmod(n,6); col=col if row%2==0 else 5-col
        x,y=col*(w+30),row*(h+32)
        banks.append(dict(bank=n,orientation='R0',bbox_um=[x,y,x+w,y+h]))
    dec=[]
    for i in range(128):
        lo,hi=i*72,(i+1)*72-1
        dec.append(dict(lane=i,banks=list(range(lo//256,hi//256+1)),code_bit_range=[lo,hi]))
    assert sum(len(x['banks'])>1 for x in dec)==32
    width,height=6*w+5*30,6*h+5*32
    return dict(schema='opentallas.softmax_bank_pin_census.v1',adopted=False,route_admitted=False,
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (lef,tracks)},
      macro=dict(width_um=w,height_um=h,signal_clock_pins=len(pins),groups=dict(groups),pins=pins,
                 read_bits=256,write_data_bits=256,write_mask_bits=256,replicas=36),
      candidate=dict(banks=banks,width_um=width,height_um=height,area_mm2=width*height/1e6,
         macro_area_mm2=36*w*h/1e6,logic_and_route_area_um2=width*height-36*w*h,
         macro_only_occupancy=36*w*h/(width*height),gaps_um=[30,32],slot_reserved=False),
      ECC=dict(full_width_read_lanes=128,codewords=dec,cross_bank_codewords=32,read_register_bits=128*221,
         capture_station_required=True,station_locations=None,
         reason='All read pins face left in R0. Serpentine adjacency alone does not prove short wires; cross-bank codewords require explicit capture/codec placement.'),
      tracks=dict(M4_pitch_um=pitch,gross_tracks_per_macro_height=math.floor(h/pitch),
         edge_pin_count=dict(collections.Counter(p['edge'] for p in pins)),
         aggregate_read_wires=9216,aggregate_write_data_wires=9216,aggregate_write_mask_pins=9216,
         mask_dynamic_wires=0,mask_basis='Current SRAM join ties all write masks active; constant rail and pin access still required.',
         capacity_after_PG_clock_vias_obstructions=None,physical_pin_access_proven=False),
      missing=['Mapped serial/codec combinational area','128 codec/station placement and actual longest routes',
        'Parent slot allocation and PG/clock/via exclusions','SS/FF native input/output clock budgets'],
      schedule='Existing command-to-first5 and II1 replay retained only if no added capture station latency; any added stage must update composed model before RTL.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
    if a.output:a.output.write_text(s)
    else:print(s,end='')
