#!/usr/bin/env python3
"""Plan the exact HEAD gearbox natural child; never add RTL cycles or fabricate views."""
import argparse
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
W,H=129.6,233.28
CORE=4.32
HALO=4.32
MW,MH=31.992,17.304

def tracks(n,layer):
    # M4 every7tracks; M6 repeats5,5,5,6tracks. Both have <=30pins/10um.
    pitch,off=(.048,.024) if layer=='M4' else (.064,.032)
    positions=[0.0]
    for k in range(n-1):
        step=7 if layer=='M4' else (5,5,5,6)[k%4]
        positions.append(positions[-1]+step*pitch)
    start=round(((H-positions[-1])/2-off)/pitch)*pitch+off
    return [round(start+x,6) for x in positions]

def build(profile,source_commit):
    def bits(bus):
        n=profile['ports'][bus]['width']
        return [(bus if n==1 else f'{bus}[{i}]',bus,i) for i in range(n)]
    groups=[('E','M4',['f_tx','f_tx_v','r_tx','r_tx_v']),
            ('E','M6',['f_rx','f_rx_v','r_rx','r_rx_v']),
            ('W','M4',['beat_rx','beat_rx_v']),('W','M6',['beat_tx'])]
    pins=[]
    for face,layer,buses in groups:
        logical=[bit for bus in buses for bit in bits(bus)]
        for (name,bus,index),y in zip(logical,tracks(len(logical),layer)):
            pins.append(dict(name=name,x=W if face=='E' else 0,y=y,layer=layer,
                             face=face,bus=bus,original_bit=index))
    for bus,x in [('locked',60.504),('fault',69.144)]:
        pins.append(dict(name=bus,x=x,y=H,layer='M5',face='N',bus=bus,original_bit=0))
    pins.append(dict(name='clk',x=64.824,y=116.64,layer='M5',face='interior',bus='clk',original_bit=0))
    for i in range(22):
        pins.append(dict(name=f'rst_n[{i}]',x=round(61.8+.288*i,6),y=125.28,
                         layer='M5',face='interior',bus='rst_n',original_bit=i))
    macros=[]
    for k in range(10):
        x=(17.28,82.08)[k%2];y=17.28+43.2*(k//2)
        macros.append(dict(inst=f'u_sf.g_bank[{k}].u_m',module='ot_sram_1r1w2c_32x64_m1',
                           origin_um=[round(x,6),round(y,6)],outline_um=[MW,MH],orient='MY' if k%2==0 else 'R0',halo_um=HALO))
    # Exact admission checks, independent of any later placement or routing result.
    assert len(pins)==sum(v['width'] for v in profile['ports'].values())==2350
    for p in pins:
        step,off=(.048,.024) if p['layer'] in ('M4','M5') else (.064,.032)
        pos=p['y'] if p['face'] in ('W','E') else p['x']
        assert abs((pos-off)/step-round((pos-off)/step))<1e-6,(p,pos)
    rects=[]
    for m in macros:
        x,y=m['origin_um'];r=[x-HALO,y-HALO,x+MW+HALO,y+MH+HALO]
        assert CORE<=r[0]<r[2]<=W-CORE and CORE<=r[1]<r[3]<=H-CORE,r
        for q in rects:
            assert not (max(r[0],q[0])<min(r[2],q[2]) and max(r[1],q[1])<min(r[3],q[3]))
        rects.append(r)
    maxima={}
    for face in ('E','W','N'):
        ys=sorted(p['y'] if face in ('E','W') else p['x'] for p in pins if p['face']==face)
        j=0;peak=0
        for i,v in enumerate(ys):
            while j<len(ys) and ys[j]<v+10-1e-8:j+=1
            peak=max(peak,j-i)
        assert peak<=60,(face,peak)
        maxima[face]=peak
    macro_area=10*MW*MH
    # Coarse gate count from the exact hierarchy, conservative two-input/RVT sizing.
    std_area_est=4042*.2916+10000*.10+300*.2
    model=dict(outline_um=[W,H],core_margin_um=CORE,macro_halo_um=HALO,
               central_channel_um=24.168,interrow_channel_um=17.256,
               west_logic_rail_um=8.64,east_logic_rail_um=6.888,
               full_outline_manhattan_um=W+H,core_r2r_geometric_bound_um=W+H-4*CORE,
               signal_reach_limit_um=405,max_pins_per_10um=maxima,
               pins=len(pins),macro_count=10,ff_bits=4042,
               sram_area_um2=macro_area,stdcell_area_estimate_um2=std_area_est,
               fill_estimate=(macro_area+std_area_est)/(W*H),
               low_fill_reason='pin-limited full1300-bit EPface at<=6pins/um plus4.32halos/clock/data channels; do not pack to routinglimit',
               forward_frames_per_cycle=.75*1023/1024,forward_frame_bits=595,
               reverse_frames_per_cycle=1,reverse_frame_bits=53,
               added_cycles=0,clock_period_ps=833,TT_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
               clock_taps_planned=[[x,y] for x in (8.664,64.824,120.984) for y in (38.88,116.64,194.4)],
               clock_nearest_tap_manhattan_bound_um=66.96,clock_tap_max_sinks=1250,clock_tap_radius_limit_um=80,
               routing_cut_estimate='NOT RUN; pins/halos/reach geometry only; actual graph estimate remains required',
               physical_signoff='NOT RUN')
    spec=dict(schema='opentallas.head.native_core_spec.v1',module='ot_s81ph_link_gbx_safe3',view='ot_s81ph_link_gbx_safe3@head',
              source_commit=source_commit,source_files=profile['source_files'],params=profile['parameters'],
              defines=['OT_COLL_NATIVE32','OT_COLL_NATIVE32_OFF'],outline_um=[W,H],pins_file='pins.json',
              macro_placement=macros,parent_partition='hd_lep0N',parent_instance='u_lane.u.u_gb',
              geometry_review='geometry_review.json',context_mask_file='context_mask.json',
              clock_ports=['clk'],reset_ports=['rst_n'],added_cycles=0)
    return spec,pins,model

def render(d,spec,pins,model):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(7,10),dpi=150)
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
    ax.add_patch(Rectangle((CORE,CORE),W-2*CORE,H-2*CORE,fill=False,ls='--',ec='gray'))
    for m in spec['macro_placement']:
        x,y=m['origin_um']
        ax.add_patch(Rectangle((x-HALO,y-HALO),MW+2*HALO,MH+2*HALO,fc='#eeeeee',ec='gray',lw=.5))
        ax.add_patch(Rectangle((x,y),MW,MH,fc='#9dcbe5',ec='black',lw=.7))
        ax.text(x+MW/2,y+MH/2,f"RAM {m['inst'].split('[')[1].split(']')[0]}\n{m['orient']}",ha='center',va='center',fontsize=7)
        # Actual read/clock face points toward the central channel.
        rx=x+MW if m['orient']=='MY' else x
        ax.plot([rx,rx],[y+1,y+8],c='navy',lw=2)
    colors={'M4':'#1b9e77','M6':'#d95f02','M5':'purple'}
    for layer in colors:
        q=[p for p in pins if p['layer']==layer]
        ax.scatter([p['x'] for p in q],[p['y'] for p in q],s=1,c=colors[layer],label=f'{layer} pins {len(q)}')
    root=(64.824,116.64)
    ax.scatter([root[0]],[root[1]],marker='*',s=90,c='red',label='clock entry / planned tree')
    for x,y in model['clock_taps_planned']:
        ax.plot([root[0],root[0],x],[root[1],y,y],c='red',lw=.6,ls='--')
        ax.add_patch(Rectangle((x-2.16,y-2.16),4.32,4.32,fill=False,ec='red',lw=.8))
    ax.text(W+3,H*.53,'EP\n1300 bits\nM4/M6',ha='left',va='center',fontsize=8)
    ax.text(-3,H*.53,'PHY\n1025 bits\nM4/M6',ha='right',va='center',fontsize=8)
    ax.set_title('PLANNED native HEAD gearbox | 129.6×233.28 µm\n10×32×64 SRAM / 4042 FF | 4.32 µm halos | 0 added cycles',fontsize=9)
    ax.set_xlim(-24,W+27);ax.set_ylim(-7,H+7);ax.set_aspect('equal');ax.set_xlabel('µm');ax.set_ylabel('µm')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.035),fontsize=7,ncol=3)
    fig.tight_layout();fig.savefig(d/'plan.png');plt.close(fig)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',type=Path,required=True);p.add_argument('--source-commit',default='8edc97f13d990f185bc0f9954295af2cc0205359');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    profile=json.loads(a.profile.read_text());spec,pins,model=build(profile,a.source_commit)
    a.out.mkdir(parents=True,exist_ok=True)
    for name,value in [('spec.json',spec),('pins.json',pins),('model.json',model)]:
        (a.out/name).write_text(json.dumps(value,indent=2)+'\n')
    render(a.out,spec,pins,model)
    print(json.dumps(dict(pins=len(pins),halo_overlap=0,pin_density=model['max_pins_per_10um'],geometry='PLANNED_ONLY',added_cycles=0)))
if __name__=='__main__':main()
