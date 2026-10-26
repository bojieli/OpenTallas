#!/usr/bin/env python3
"""Source-bound scorer leaf packing and actual LEF chain-pin audit; no closure claim."""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--leaf-view',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 lef=(a.leaf_view/'ot_hbm_idx_hslice_ready_native.lef').read_text();pins={}
 for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1',lef,re.S):
  n,b=m.groups();rect=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b)
  if rect:
   x,y,u,v=map(float,rect.groups());pins[n]=((x+u)/2,(y+v)/2)
 mapping=[]
 for n,(x,y) in pins.items():
  dst=n.replace('qo_','ql_',1) if n.startswith('qo_') else n.replace('ko_key','k_key',1) if n.startswith('ko_key') else n.replace('cs_out','cs_in',1) if n.startswith('cs_out') else 'cf_in' if n=='cf_out' else None
  if dst:
   assert dst in pins,(n,dst);mapping.append((n,dst,abs(x-pins[dst][0])+20+abs(y)+abs(103.68-pins[dst][1])))
 assert len(mapping)==1146,len(mapping)
 worst=max(mapping,key=lambda z:z[2]);assert worst[2]<500
 # Each scorer: engines4 x chunks4 x keys4 x heads8, preserving every instance.
 # Option A rotates the actual leaf so N inputs become W and S outputs E.
 nodes=[]
 for e in range(4):
  for c in range(4):
   for g in range(4):
    col=(e%2)*2+c//2;row=(e//2)*8+(c%2)*4+g
    for h in range(8):
     nodes.append(dict(name=f'ge[{e}]/engine/g_ch[{c}]/u_c/g_col[{g}]/g_s[{h}]/u_s',engine=e,chunk=c,key=g,head=h,x=round((col*8+h)*123.68,3),y=round(row*192.8,3),w=103.68,h=172.8,orient='R90'))
 assert len(nodes)==512
 W,H=3937.76,3064.8
 assert round(max(n['x']+n['w'] for n in nodes),3)==W
 assert round(max(n['y']+n['h'] for n in nodes),3)==H
 for i,n in enumerate(nodes):
  for m in nodes[i+1:]:
   assert min(n['x']+n['w'],m['x']+m['w'])-max(n['x'],m['x'])<=1e-8 or min(n['y']+n['h'],m['y']+m['h'])-max(n['y'],m['y'])<=1e-8,(n['name'],m['name'])
 options=[dict(name='A_straight_R90_2x2_engines',width_um=W,height_um=H,leaf_orientation='R90',chain_columns=4,chain_rows=16,leaf_count=512,chain_count=64,channels_um=20,area_mm2=W*H/1e6,local_width_delta_um=W-3840.48,local_height_delta_um=H-3008.88,aggregate_oriented_vertical_delta_um=4*(W-3840.48),status='preferred leaf packing; no reserved control area or whole-parent pin/cut/clock proof'),dict(name='B_straight_R0_22x3_chains',width_um=4221.6,height_um=2948.32,leaf_orientation='R0',chain_columns=22,chain_rows=3,chain_sites=66,leaf_count=512,channels_um=20,area_mm2=4221.6*2948.32/1e6,aggregate_oriented_vertical_delta_um=4*(4221.6-3840.48),status='leaf packing fits64chains; vertical extension1524.48um exceeds834.8um die-height headroom absent coherent relocation'),dict(name='C_existing_shape_row_fold',width_um=3836,height_um=3195.68,leaf_orientation='R0',leaf_count=512,grid_columns=20,grid_rows=26,channels_um=20,status='reject simple folding:1146-bit U-turn across20um horizontal channel has insufficient cut; requires new wider return channels/geometry, no assumed timing equivalence')]
 receipt=dict(schema='opentallas.hbm_idx_scorer_layout.v1',scope='Actual512leaf packing and seven1146-net chain seams per64chains only; not full scorer placement, clock delivery, PG or native qualification.',closed_leaf=dict(job='ot_hbm_idx_hslice_ready_native_c0-ready3-2065d438f',w=172.8,h=103.68,lef_sha256=hashlib.sha256(lef.encode()).hexdigest(),params=dict(NB=4,FPL=7,FML=5,QL=5)),counts=dict(scorers=4,engines_per_scorer=4,chunks_per_engine=4,keys_per_chunk=4,heads_per_key=8,metadata_per_scorer=4,total_leafs=2048,total_metadata=16),chain_pins=dict(bits=len(mapping),worst_net=worst[0],capture_pin=worst[1],worst_manhattan_um=round(worst[2],3),seams_per_scorer=448,all_same_orientation=True,relay_stages_on_adjacent_chain_seams=0,compensated_tt_budget_ps=683.333,conservative_launch_ps=211.03,conservative_capture_ps=188.28,estimated_wire_ps=round(.76*worst[2],3),remaining_tt_margin_ps=round(683.333-211.03-188.28-.76*worst[2],3)),options=options,open=['Place and synthesize actual chunk/engine/scorer control and four tail leaves; no control area assumed free.','Bound every query/key/control fanout and all returns to actual pins; add and compile fixed relay stages wherever reach fails.','Deliver phi minus measured insertion to every leaf clock; exported512hslice roots/scorer do not qualify physical clock distribution.','Actual oriented LEF pin-grid legality, parent PG, cut capacity, source-pinned clock/route/TT/FF/DRC proof remain required.','DIE slot change requires H-DIE coherent whole-group integration; current accepted rectangle not silently resized.'],nodes=nodes)
 (a.out/'layout.json').write_text(json.dumps(receipt,indent=2)+'\n')
 scale=.22;vw=W*scale+40;vh=H*scale+95
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}">','<rect width="100%" height="100%" fill="#f5f7fb"/>','<style>text{font-family:Arial,sans-serif;fill:#172035}</style>',f'<text x="20" y="23" font-size="15">IDX scorer: actual 512 CLOSED leaves, 64 straight chains</text>',f'<text x="20" y="43" font-size="11">3937.76 × 3064.80 µm; 20 µm seams; R90; control/clock/PG/whole-parent proof OPEN</text>']
 colors=['#4d79af','#64a795','#ae78a3','#cc9854']
 for n in nodes:svg.append(f'<rect x="{20+n["x"]*scale}" y="{60+n["y"]*scale}" width="{n["w"]*scale}" height="{n["h"]*scale}" fill="{colors[n["engine"]]}" stroke="white" stroke-width=".3"><title>{n["name"]}</title></rect>')
 svg.append(f'<text x="20" y="{vh-10}" font-size="11">Leaf packing only. Every actual pin-pair seam ≤ {worst[2]:.3f} µm Manhattan; no relays assumed outside these seams.</text></svg>');(a.out/'layout.svg').write_text('\n'.join(svg)+'\n')
 print(json.dumps(dict(leafs=len(nodes),pins=len(mapping),worst_seam_um=worst[2],preferred_outline=[W,H],status='CANDIDATE_ONLY')))
if __name__=='__main__':main()
