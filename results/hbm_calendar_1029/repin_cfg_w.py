#!/usr/bin/env python3
"""Source-aware input face proposal: actual cfg256 -> target -> SRAM W data."""
import argparse,copy,json,shutil
from pathlib import Path

def run(src,out):
 src=Path(src);out=Path(out);out.mkdir(parents=True,exist_ok=False)
 pins=json.load(open(src/'pins.json'));p=copy.deepcopy(pins)
 other=[]
 for r in p:
  if r['name'].startswith('cfg_data['):
   i=int(r['name'].split('[')[1][:-1]);r.update(x=.096,y=round(17.304+i*.288,6),layer='M4')
  elif r['x']<1:other.append(r)
 low=[r for r in other if r['name']=='rst_n' or r['name'].startswith(('rslot_v[','wslot_v['))]
 high=[r for r in other if r not in low]
 assert len(low)==17 and len(high)==56
 for i,r in enumerate(low):r['y']=round(4.344+i*.576,6)
 for i,r in enumerate(high):r['y']=round(92.616+i*.288,6)
 assert len({r['name'] for r in p})==len(p)==558
 peaks={}
 for face,rows in [('N',[r for r in p if r['y']>111]),('S',[r for r in p if r['y']<1]),('W',[r for r in p if r['x']<1])]:
  for ly in {r['layer'] for r in rows}:
   vs=sorted(r['x'] if face!='W' else r['y'] for r in rows if r['layer']==ly)
   peaks[face+'/'+ly]=max(sum(v-1e-8<=w<=v+10+1e-8 for w in vs)/10 for v in vs)
 assert max(peaks.values())<=6
 for n in ['master_slice.json','macros.json','original_slice.json']:shutil.copyfile(src/n,out/n)
 (out/'pins.json').write_text(json.dumps(p,indent=1)+'\n')
 # Existing mapped gate proves all 768 named FFs; the 512 unfixed target data
 # stages can use this inclusive GPL guide, released before legalization.
 guide=dict(name='calendar_cfg_w',prefixes=['u_fcore.u_target.data_q[','u_fcore.u_target.program_cfg_data['],rect_um=[4.32,17.28,17.28,91.8],expected_cells=512,actual_cell_area_um2=512*1.08*.27,estimated_fill=512*1.08*.27/(12.96*(91.8-17.28)),release='before DPL',source_changed=False)
 (out/'data_guide.json').write_text(json.dumps(guide,indent=1)+'\n')
 rep=dict(status='PROPOSAL_NO_PNR',outline_um=[216,112.32],pins=558,cfg_data256_face='W/M4; matched actual SRAM data face',clock_pins='unchanged from compact proposal',cycles_added_core=0,parent_route_cycles='must recompose/price; no zero-total-cycle claim',peak_pins_per_um_10um=peaks,guide=guide,source_providers=['hleaf_SW.a_cfg_data -> NW_hub.u_calendar_Q__q0','hleaf_SE.a_cfg_data -> NE_hub.u_calendar_Q__q0','hleaf_NW.a_cfg_data -> NW_hub.u_calendar_Q__q1','hleaf_NE.a_cfg_data -> NE_hub.u_calendar_Q__q1'],bits='256/256 LSB identity each; no payload reorder')
 (out/'estimate.json').write_text(json.dumps(rep,indent=1)+'\n')
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,ax=plt.subplots(figsize=(11,6));ax.add_patch(Rectangle((0,0),216,112.32,fill=False))
 for m in json.load(open(out/'macros.json')):
  a,b,c,d=m['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='gray',alpha=.4));ax.add_patch(Rectangle((a-4.32,b-4.32),c-a+8.64,d-b+8.64,fill=False,linestyle='--'))
 a,b,c,d=guide['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='cyan',alpha=.3));ax.text(5,54,'512 FF GPL guide',rotation=90,fontsize=7)
 for layer,color in [('M4','green'),('M5','purple')]:
  ps=[r for r in p if r['layer']==layer];ax.scatter([r['x'] for r in ps],[r['y'] for r in ps],c=color,s=3,label=layer)
 for isl in json.load(open(src/'master_slice.json'))['islands']:
  a,b,c,d=isl['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='orange',alpha=.4))
 ax.set_xlim(-5,221);ax.set_ylim(-5,117.32);ax.set_aspect('equal');ax.set_title('VM CAL cfg256 input moved to SRAM W face;512 existing target-data FF guide\n558 ports/unchanged core cycles; parent FT/tap/CA/PG event required');ax.legend();fig.tight_layout();fig.savefig(out/'proposal.png',dpi=150)
 print(json.dumps(rep,sort_keys=True))
def main():
 a=argparse.ArgumentParser();a.add_argument('compact_proposal');a.add_argument('out');x=a.parse_args();run(x.compact_proposal,x.out)
if __name__=='__main__':main()
