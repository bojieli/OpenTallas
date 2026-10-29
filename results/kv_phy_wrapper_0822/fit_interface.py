#!/usr/bin/env python3
"""MODELED PHY pin-macro + analog-reserve decomposition; no parent-plan edit.
Native data pin mapping is decoded from the real bound concatenations, not
inferred from PC names (the return words deliberately straddle output buses).
"""
import argparse,gzip,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
sys.path.insert(0,str(ROOT/'tools/qwen_kv_die'))
import schema as S,gen_phys as G,phy_pc4_gen as PHY

def subtract(a,b):
    x0,y0,x1,y1=a;u0,v0,u1,v1=b
    u0=max(x0,u0);u1=min(x1,u1);v0=max(y0,v0);v1=min(y1,v1)
    if u0>=u1 or v0>=v1:return [a]
    return [r for r in [(x0,y0,u0,y1),(u1,y0,x1,y1),(u0,y0,u1,v0),(u0,v1,u1,y1)] if r[2]-r[0]>.001 and r[3]-r[1]>.001]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--rtl',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--islands',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    P=S.Plan(json.loads(gzip.open(a.plan,'rt').read()) if a.plan.suffix=='.gz' else S.load(a.plan),a.plan);t=P.types['kv3_phy'];w,h=t['outline_um'];sv=a.rtl.read_text()
    pin={(bus,bit):(layer,x,y,f) for bus,bit,layer,x,y,f in G.type_pins(P,'kv3_phy')}
    outpins={};legs=[];origin=[806.76,4.32];mw,mh=30.24,1512
    def put(name,bus,bit):
        layer,x,y,f=pin[bus,bit]
        if f!='E':raise ValueError(f'{bus}[{bit}] no longer E-facing')
        yy=round(y-origin[1],6);half=G.LAYER_W.get(layer,.024)/2
        outpins[name]=dict(layer=layer,face='E',rects_um=[[mw-.192,round(yy-half,6),mw,round(yy+half,6)]])
        legs.append(dict(pin=name,boundary=f'{bus}[{bit}]',layer=layer,source_um=[x,y],macro_um=[origin[0]+mw,y],distance_um=round(x-origin[0]-mw,6)))
    inst=re.search(r'qkd_hbm3e_phy_pc4\s+u_core\s*\((.*?)\);',sv,re.S)[1]
    conns=dict(re.findall(r'\.(\w+)\(([^()]*)\)',inst))
    for k in range(4):
        sig=re.fullmatch(r'(\w+)\[327:0\]',conns[f'po{k}'])[1]
        match=re.search(r'ot_dp_st #\(\.W\(328\)\) u_bin_(\w+) .*?\.q\('+re.escape(sig)+r'\)',sv)
        if not match:raise ValueError('missing native po source')
        bus=match[1]
        for bit in range(328):put(f'po{k}[{bit}]',bus,bit)
    for bus,expr in re.findall(r'u_bout_(\w+)\s*\(.*?\.d\((\{[^}]+\})\),\s*\.ea',sv):
        tokens=re.findall(r'w_core_(\w+)\[(\d+):(\d+)\]',expr)
        bit=0
        for n,hi,lo in reversed(tokens):
            for b in range(int(lo),int(hi)+1):put(f'{n}[{b}]',bus,bit);bit+=1
    outpins['clk']=dict(layer='M7',face='W',rects_um=[[0,755.904,.024,756.096]])
    outpins['rst_n']=dict(layer='M7',face='W',rects_um=[[0,755.52,.024,755.712],[0,1485.984,.024,1486.176]])
    layout=dict(pins=outpins,obstruction_layers=[1,2,3],grade='MODELED',basis='Existing HBM analog-field + digital pin-macro abstraction; upper digital routing layers are explicit modeled access, no PHY implementation claim')
    (a.out/'digital_layout.json').write_text(json.dumps(layout,indent=2)+'\n')
    PHY.generate(a.out/'views',mw,mh,layout)
    # Whole PHY window stays reserved: utilities retain their existing sites.
    # Gray polygons are off-model analog body/power reserve, not free space.
    forbidden=[]
    native=[]
    if a.islands:
        iw=json.loads(a.islands.read_text())["windows"]
        native=sorted({tuple(r) for tn in ["kv3_phy","kv3_phy_v1"] for r in iw[tn]})
        forbidden.extend(native)
        for r in native:
            if min(r[2],origin[0]+mw)>max(r[0],origin[0]) and min(r[3],origin[1]+mh)>max(r[1],origin[1]):
                raise ValueError(f"digital macro covers actual native provider/clock body {r}")
    for r in t['clock']['die_islands_um']:
        forbidden.append([r[0]-4.32,r[1]-4.32,r[2]+4.32,r[3]+4.32])
    forbidden += [[427.32,0,436.64,h], [427.32,755.46,806.76,765.18],
                  [427.32,1485.54,806.76,1495.26], [802.44,0,w,h]]
    for r in t['clock']['landing_contract'].get('bands',{}).values():
        q=r['rect_um'];forbidden.append([q[0]-4.32,q[1]-4.32,q[2]+4.32,q[3]+4.32])
    for r in t['clock']['landing_contract']['collector_tree']['relays']:
        x,y=r['xy'];forbidden.append([x-8.64,y-8.64,x+8.64,y+8.64])
    analog=[[4.32,4.32,802.44,h-4.32]]
    for obstacle in forbidden:
        analog=[r for q in analog for r in subtract(q,obstacle)]
    analog=[list(map(lambda x:round(x,6),r)) for r in analog]
    overlap=[]
    for q in t['clock']['die_islands_um']:
        if min(q[2],origin[0]+mw)>max(q[0],origin[0]) and min(q[3],origin[1]+mh)>max(q[1],origin[1]):overlap.append(q)
    summary=dict(grade='MODELED/G1 proposal, not routed or signed',type='kv3_phy/kv3_phy_v1',gross_phy_window_um2=w*h,
        gross_phy_window_unchanged=True,cycles_added=0,parent_pins_changed=0,clock_islands_moved=0,
        digital_macro_origin_um=origin,digital_macro_outline_um=[mw,mh],digital_macro_area_um2=mw*mh,
        analog_offmodel_reserve_rects_um=analog,analog_reserve_area_um2=sum((r[2]-r[0])*(r[3]-r[1]) for r in analog),
        utilities_and_edge_channels_um2=w*h-mw*mh-sum((r[2]-r[0])*(r[3]-r[1]) for r in analog),
        data_bits=len(legs),max_data_hop_um=max(r['distance_um'] for r in legs),
        core_clock_hop_um=374.772,reset_hops_um=dict(host_landing=374.8119,v1_reset=36.012),
        macro_clock_island_body_overlaps=overlap,native_provider_clock_windows=len(native),
        power='Existing separate PHY supply and full-window PG retained. Analog rectangles remain PG/power reserve; no IR qualification or analog-area reduction.',
        limitations=['Upper-layer permeability is MODELED licensed-IP interface assumption, matched to existing HBM pin-macro form; no physical PHY signoff.',
          'Real wrapper placement/CTS/full r2r and FF hold remain required after current event27f bind.',
          'Global PHY cost remains the original full window; analog vs digital vs utility decomposition is not an area saving.'])
    (a.out/'fit.json').write_text(json.dumps(summary,indent=2)+'\n');(a.out/'data_legs.json').write_text(json.dumps(legs,indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axs=plt.subplots(1,2,figsize=(11,10),gridspec_kw={'width_ratios':[2,1]})
    for ax in axs:
        for x0,y0,x1,y1 in analog:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#c5ced5',linewidth=0))
        ax.add_patch(Rectangle(origin,mw,mh,facecolor='#e4ac64',edgecolor='#995500',alpha=.8))
        for x0,y0,x1,y1 in native:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#9b62bf'))
        for x0,y0,x1,y1 in t['clock']['die_islands_um']:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#157344'))
        for r in legs:ax.plot([r['source_um'][0],r['macro_um'][0]],[r['source_um'][1]]*2,color='#3170aa',alpha=.1,lw=.3)
        ax.plot([432,806.76],[760.32]*2,color='#d52244',lw=2)
        for x,y in [(842.4,760.32),(452.147,760.32),(431.96,1130.387)]:ax.scatter([x],[y],marker='s',color='#652d90',s=20)
        ax.set_aspect('equal');ax.set_xlabel('um');ax.grid(alpha=.1)
    axs[0].set_xlim(0,w);axs[0].set_ylim(0,h);axs[0].set_title('Same full PHY window; gray = analog/PG reserve\ngreen = unchanged clock islands; orange = pin macro')
    axs[1].set_xlim(770,870);axs[1].set_ylim(0,700);axs[1].set_title('E face: all2500 native bit legs27.0um')
    fig.suptitle('MODELED PHY interface fit / G1 proposal only / 0 added cycles');fig.tight_layout();fig.savefig(a.out/'geometry.png',dpi=130)
    print(json.dumps({k:summary[k] for k in ['data_bits','max_data_hop_um','gross_phy_window_um2','analog_reserve_area_um2','macro_clock_island_body_overlaps']}))
if __name__=='__main__':main()
