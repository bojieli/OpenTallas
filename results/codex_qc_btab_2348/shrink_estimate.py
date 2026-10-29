#!/usr/bin/env python3
"""BTAB footprint feasibility only. No adopted plan or routing claim."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def main():
    out=Path(__file__).resolve().parent
    mw,mh=94.824,41.064
    W,H=259.2,138.24
    sites=[(x,y) for y in (17.28,73.44) for x in (17.28,142.56)]
    # 819 pins face the central channel on each SRAM row; M3+M5 vertical
    # supply 48.6 tracks/um, with the project 60% planning capacity.
    centre=142.56-(17.28+mw)
    side=min(17.28,W-(142.56+mw))
    pitch_y=73.44-(17.28+mh)
    report=dict(label='PACKING / TRACK ESTIMATE ONLY; macro/data pin replan still required',outline_um=[W,H],macro_sites_um=sites,
                old_area_um2=354.24*259.2,new_area_um2=W*H,area_reduction_fraction=1-W*H/(354.24*259.2),
                macro_fraction=4*mw*mh/(W*H),central_channel_um=centre,outer_channel_min_um=side,row_gap_um=pitch_y,
                central_track_ratio=819/(48.6*centre),outer_track_ratio=410/(48.6*side),
                S_pin_density_per_um=1036/W,E_pin_density_per_um=281/H,
                clock_entry_candidate_um=[(17.28+mw+142.56)/2,H/2],
                caveats=['Every per-bit pin and macro data path must be regenerated/reviewed before build.',
                         'Clock entry is a geometric candidate; M5/PG pin/driver placement awaits the actual planned tree.',
                         'Pin-column corner escape strips and logic placement are not yet measured.',
                         'This footprint is a successor plan event only; current ev_qc25 is untouched.'])
    (out/'shrink_estimate.json').write_text(json.dumps(report,indent=1)+'\n')
    fig,ax=plt.subplots(figsize=(10,5.5));ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
    for n,(x,y) in enumerate(sites):
        ax.add_patch(Rectangle((x-4.32,y-4.32),mw+8.64,mh+8.64,facecolor='#f5dec0',edgecolor='none'))
        ax.add_patch(Rectangle((x,y),mw,mh,facecolor='#8eaac3',edgecolor='#234766'))
        ax.text(x+mw/2,y+mh/2,f'SRAM {n}\n94.824 x 41.064',ha='center',va='center')
    ax.scatter(*report['clock_entry_candidate_um'],marker='*',s=180,c='red',label='clock-entry candidate (unadopted)')
    ax.set(xlim=(-5,W+5),ylim=(-5,H+5),xlabel='um',ylabel='um',title='BTAB 2x2 footprint proposal: 259.2 x 138.24 um\nPacking/track estimate only; current outline/data pins unchanged')
    ax.set_aspect('equal');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.13));fig.tight_layout();fig.savefig(out/'shrink_estimate.png',dpi=130)
if __name__=='__main__':main()
