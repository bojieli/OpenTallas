#!/usr/bin/env python3
"""One shared SFU-store F6 candidate: real macro pins, per-pin RTL state anchors.
Only generates a candidate pin table/placement/anchors and images; no P&R or STA.
"""
import argparse, hashlib, json, math, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LEF='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
OLDPINS='physical/die_plan/hbm_arch/B2n/cores/ot_hbm_su_static_sfustore_hw__293.76x354.24__q_hub_u_sfus_Q.json'
W,H=311.04,354.24
CW,CH=1.08,0.270

def mapping(n):
    m=re.fullmatch(r'(wd_in|w_mask_in|rd_out|r_addr_in|w_addr_in)\[(\d+)\]',n)
    if m:
        kind,b=m[1],int(m[2])
        if kind in ('r_addr_in','w_addr_in') and b>=6:return None
        reg={'wd_in':'wd_pin','w_mask_in':'wm_pin','rd_out':'g_rd_cap.rd_raw_cap','r_addr_in':'a_pin','w_addr_in':'wa_pin'}[kind]
        return reg+'['+str(b+3 if kind=='r_addr_in' else b)+']'
    return {'r_ce_in':'r_pin','w_ce_in':'w_pin'}.get(n)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    txt=(ROOT/LEF).read_text();mw,mh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups())
    macro_pins=[]
    for p in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',txt):
        reg=mapping(p[1])
        if reg is None:continue
        q=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',p[2]);assert q,p[1]
        x0,y0,x1,y1=map(float,q.groups());x,y=(x0+x1)/2,(y0+y1)/2
        macro_pins.append(dict(pin=p[1],register=reg,x=x,y=y,face='W' if x<mw/2 else 'E'))
    assert len(macro_pins)==782,len(macro_pins)
    occupied=set();anchors=[];macros=[];maxd=0
    for bank in range(16):
        x=38.88 if bank<8 else 172.8;y=4.32+43.2*(bank%8)
        macros.append(dict(inst=f'g_bank[{bank}].u_bank.u_data.g_read[0].u_m',origin_um=[x,y],outline_um=[mw,mh],orient='R0'))
        for q in sorted(macro_pins,key=lambda q:(q['face'],q['y'],q['pin'])):
            px,py=x+q['x'],y+q['y'];row=round((py-CH/2)/CH);opts=[]
            for k in range(12):
                fx=x-4.32-CW/2-k*CW if q['face']=='W' else x+mw+4.32+CW/2+k*CW
                fx=round(fx/0.054)*0.054;site=round((fx-CW/2)/0.054)
                for dy in range(-16,17):
                    rr=row+dy;fy=rr*CH+CH/2;dist=abs(fx-px)+abs(fy-py)
                    if dist>17.5 or fy<CH/2 or fy>H-CH/2:continue
                    opts.append((dist,abs(dy),k,site,rr,fx,fy))
            for dist,_,_,site,rr,fx,fy in sorted(opts):
                cells={(sx,rr) for sx in range(site,site+20)}
                if cells&occupied:continue
                occupied|=cells;break
            else:raise RuntimeError(f'no legal per-pin FF site bank{bank} {q}')
            maxd=max(maxd,dist)
            anchors.append(dict(bank=bank,macro_pin=q['pin'],register=f'g_bank[{bank}].u_bank.'+q['register'],
                                pin_um=[px,py],center_um=[round(fx,4),round(fy,4)],manhattan_um=round(dist,4),face=q['face']))
    # Preserve all public names; relocate each lane coherently onto its own bank's outer face.
    raw=subprocess.run(['git','-C',str(ROOT),'show','HEAD:'+OLDPINS],check=True,capture_output=True).stdout
    pins=json.loads(raw);lane_count={i:0 for i in range(16)}
    for p in pins:
        m=re.match(r'l(\d\d)_',p['name'])
        if m:
            b=int(m[1]);k=lane_count[b];lane_count[b]+=1
            yy=4.32+43.2*(b%8)+7+0.24*k
            p.update(layer='M4',x=0.018 if b<8 else W-0.018,y=round(0.024+0.048*round((yy-0.024)/0.048),4))
        else:
            common={'clk':155.552,'rst_n':154.152,'qid[0]':156.312,'qid[1]':156.552,'fault':157.032}
            assert p['name'] in common,p['name']
            p.update(layer='M7' if p['name']=='clk' else 'M5',x=common[p['name']],y=0.018)
    assert set(lane_count.values())=={114},lane_count
    summary=dict(scope='GEOMETRY CANDIDATE ONLY; actual synthesized FF association/placement and clock stage pending',
        outline_um=[W,H],macro_outline_um=[mw,mh],macro_instances=16,macro_halo_um=[4.32,1.0],
        active_macro_pins_per_bank=782,anchors=len(anchors),max_pin_to_FF_center_um=round(maxd,4),
        FF_assumed_outline_um=[CW,CH],max_center_distance_plus_cell_um=round(maxd+CW/2+CH/2,4),
        usable_channels_um=[38.88-4.32,172.8-(38.88+mw)-8.64,W-(172.8+mw)-4.32],
        lane_pin_count=lane_count,added_data_cycles=0,added_FF_per_tile=11264,
        plan_delta='ONE common master + pin table for both B2 hub placements; parent per-bit remap/reach and fresh clock review required',
        source_commit=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),
        lef=LEF,lef_sha256=hashlib.sha256(txt.encode()).hexdigest(),old_pin_sha256=hashlib.sha256(raw).hexdigest())
    for name,obj in [('anchors.json',anchors),('macro_placement.json',dict(macro_placement=macros)),('pins.json',pins),('summary.json',summary)]:
        (out/name).write_text(json.dumps(obj,indent=1)+'\n')
    (out/'anchors.tsv').write_text('register\tx_um\ty_um\n'+''.join(f"{r['register']}\t{r['center_um'][0]}\t{r['center_um'][1]}\n" for r in anchors))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,2,figsize=(13,8),gridspec_kw={'width_ratios':[1,1]})
    colors={'wd_pin':'#2a9d8f','wm_pin':'#e9c46a','g_rd_cap':'#e76f51','a_pin':'#457b9d','wa_pin':'#457b9d','r_pin':'#457b9d','w_pin':'#457b9d'}
    for ax in axes:
        ax.add_patch(Rectangle((0,0),W,H,fill=False,color='black'))
        for b,m in enumerate(macros):
            x,y=m['origin_um'];ax.add_patch(Rectangle((x-4.32,y-1),mw+8.64,mh+2,fill=False,edgecolor='#aaa',linestyle=':'))
            ax.add_patch(Rectangle((x,y),mw,mh,facecolor='#cad2c5',edgecolor='#52796f'));ax.text(x+mw/2,y+mh/2,f'bank {b}',ha='center',va='center',fontsize=7,clip_on=True)
        for prefix,col in colors.items():
            rs=[r for r in anchors if r['register'].split('.u_bank.')[1].startswith(prefix)]
            ax.scatter([r['center_um'][0] for r in rs],[r['center_um'][1] for r in rs],s=1.3,c=col,label=prefix)
        ax.scatter([p['x'] for p in pins],[p['y'] for p in pins],s=2,c='#264653')
        ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
    axes[0].set_xlim(-4,W+4);axes[0].set_ylim(-4,H+4);axes[0].set_title('One shared 2x8 macro template; lane faces by bank')
    axes[1].set_xlim(14,190);axes[1].set_ylim(1,92);axes[1].set_title('Actual LEF pins -> named kept interface FF anchors')
    for r in anchors:
        if r['bank'] in (0,1,8,9):
            axes[1].plot([r['pin_um'][0],r['center_um'][0]],[r['pin_um'][1],r['center_um'][1]],lw=.18,color='#777',alpha=.3)
    fig.suptitle(f'SFU store zero-cycle F6 candidate — {len(anchors)} anchors; max centre distance {maxd:.2f}um; no P&R')
    fig.tight_layout();fig.savefig(out/'geometry.png',dpi=180);plt.close(fig)
    print(json.dumps(summary))
if __name__=='__main__':main()
