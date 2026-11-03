"""HHP geometry PREP from actual views/source; no kit generation or CAD."""
from pathlib import Path
import hashlib, json, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
I = HERE / 'inputs'
P = json.loads((I/'selected_plan.json').read_text())
TAPS = json.loads((I/'clock_tap_pins.json').read_text())

def ports(path):
    text = path.read_text()
    size = tuple(map(float, re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', text).groups()))
    out = {}
    for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', text, re.M|re.S):
        name, body = m.groups()
        boxes = []
        for b in re.finditer(r'LAYER\s+(\S+)\s*;(.*?)(?=LAYER|END|$)', body, re.S):
            boxes += [(b[1], tuple(map(float, r))) for r in re.findall(r'RECT\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)\s*;', b[2])]
        out[name] = boxes
    return size, out

PSIZE, PC = ports(I/'pc.lef')
SSIZE, SRAM = ports(I/'sram.lef')
assert PSIZE == (397.44, 362.88) and SSIZE == (94.824, 41.064)
assert 'make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048' in (I/'make_tracks.tcl').read_text()
head = json.loads((I/'head_planned_pins.json').read_text())['pins']
bound = (I/'kv3_pc__cl5a95b461_bound.sv').read_text()
group = (I/'group_r2c_native.sv').read_text()
body = (I/'qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv').read_text()
seg = (I/'qkd_static_kv_landing_seg.sv').read_text()
landing = (I/'qkd_static_kv_landing.sv').read_text()
g = re.search(r'\bmodule\s+qkd_kvs_grp_h\b.*?\bendmodule', body, re.S).group()
assert '.actual_data({slg__actual_data__0, slg__actual_data__1, slg__actual_data__2, slg__actual_data__3})' in g
delays = [1, 3, 1, 5]
for q, d in enumerate(delays):
    assert f'wire [255:0] slg__actual_data__{3-q} = i_pc{q}[255:0];' in g
    assert f'.i_pc{q}(c_pc{q})' in group
    assert f'c_pc{q} = {{i_pc{q}[304:291], f1[{q}], i_pc{q}[289:0]}}' in group
    assert f'#(.W(305), .D({d})) u_d{d}_kvpc{q}_o_grp' in bound
assert '.actual_data(actual_data[256*q+:256])' in seg
assert 'ad_q<=actual_data' in landing and 'output reg [255:0] out_data' in landing
assert 'out_data<=(MUT==2)?(mem_q^256\'b1):mem_q;' in landing

rx = r'set di_x0 \[expr \{round\(([-.0-9]+)\*\$di_u\)\}\]; set di_y0 \[expr \{round\(([-.0-9]+)\*\$di_u\)\}\]\nset di_x1 \[expr \{round\(([-.0-9]+)\*\$di_u\)\}\]; set di_y1 \[expr \{round\(([-.0-9]+)\*\$di_u\)\}\]'
islands = [tuple(map(float, v)) for v in re.findall(rx, (I/'die_islands.tcl').read_text())]
assert len(islands) == 126
def hit(a,b): return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
def rect(x,y,w,h,pad=0): return (x-pad,y-pad,x+w+pad,y+h+pad)
pcs = []
for c in P['hard_cores']:
    x,y = c['origin_um']; w,h = c['outline_um']
    pcs.append(rect(x,y,w,h))
assert all(not hit(a,b) for a in pcs for b in islands)

# Genuine BASE pins and separately labelled PLANNED head pins; no head LEF alias.
data_ranges = []
for q,c in enumerate(P['hard_cores']):
    x,y = c['origin_um']; w,h = c['outline_um']
    if q == 0:
        pts = [(p['x']+c['track_offset_um'][0],p['y']+c['track_offset_um'][1]) for p in head
               if (m:=re.fullmatch(r'o_grp\[(\d+)\]',p['name'])) and int(m[1]) < 256]
    else:
        pts = [((r[0]+r[2])/2,(r[1]+r[3])/2) for n,bs in PC.items()
               if (m:=re.fullmatch(r'o_grp\[(\d+)\]',n)) and int(m[1]) < 256 for _,r in bs[:1]]
    assert len(pts) == 256
    pts = [(x+(w-a if c['orient']=='MY' else a),y+b) for a,b in pts]
    data_ranges.append([min(a for a,b in pts),max(a for a,b in pts),min(b for a,b in pts),max(b for a,b in pts)])

sites = [(138.24,600.012),(544.32,600.012),(544.32,873.612),(397.44,873.612)]
rows = []
for q,(x,y) in enumerate(sites):
    box=rect(x,y,*SSIZE); halo=rect(x,y,*SSIZE,pad=4.32)
    assert all(not hit(halo,b) for b in pcs)
    assert all(not hit(halo,b) for b in islands)
    assert all(not (halo[0] <= a <= halo[2] and halo[1] <= b <= halo[3]) for a,b in P['relay_sites'].values())
    off=[]
    for n,bs in SRAM.items():
        if n in {'VDD','VSS'}: continue
        for layer,r in bs:
            assert layer=='M4'
            cy=y+(r[1]+r[3])/2
            err=abs((cy-.024)/.048-round((cy-.024)/.048))*.048
            if err>1e-8: off.append([n,err])
    assert not off
    _,cr=SRAM['clk'][0]; clk=[x+(cr[0]+cr[2])/2,y+(cr[1]+cr[3])/2]
    reach=min((abs(clk[0]-t['x'])+abs(clk[1]-t['y']),t['bus']) for t in TAPS)
    assert reach[0] <= 220
    rows.append(dict(bank=q,instance=f'u_bound.u_slg.u_core.u_slg.g_pc\\[{q}\\].u_pc.u_rows',
                     origin_um=[x,y],orient='R0',size_um=list(SSIZE),box=box,halo=halo,
                     clk_pin_um=clk,nearest_existing_tap=reach[1],tap_Manhattan_um=reach[0],
                     macro_or_island_or_fixed_relay_halo_collision=0,off_M4_pin_centres=0,
                     existing_PC_to_SLG_delay_edges=delays[q]))
assert all(not hit(a['halo'],b['halo']) for i,a in enumerate(rows) for b in rows[i+1:])

# These are candidate soft placement guides for EXISTING state only.
# Bend the lower-right PC's existing D3 link through the actual central channel;
# a straight diagram arrow would incorrectly cross the hard PC body.
relay_centres = [[(185.76,580.5)],[(560,178.2),(524.88,380.16),(518.4,578.34)],
                 [(592,940)],[(445,940),(440,938),(435,936),(430,934),(425,932)]]
write_paths=[]; rr=[]
def length(p): return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(p,p[1:]))
for q,r in enumerate(rows):
    dr=data_ranges[q]; src=((dr[0]+dr[1])/2,(dr[2]+dr[3])/2)
    anchors=relay_centres[q]
    if q==1:
        paths=[[src,(src[0],178.2),anchors[0]],
               [anchors[0],(anchors[1][0],178.2),anchors[1]], [anchors[1],anchors[2]]]
    else:
        paths=[[src,(src[0],anchors[0][1]),anchors[0]]]+[[a,b] for a,b in zip(anchors,anchors[1:])]
    x,y=r['origin_um']
    for dst in [(x-8.64,y+20.52),(x+SSIZE[0]+8.64,y+20.52)]:
        paths.append([anchors[-1],(dst[0],anchors[-1][1]),dst])
    write_paths += paths
    rr += [dict(kind=f'PC{q} existing D{delays[q]} + ad_q',path_um=p,length_um=length(p)) for p in paths]

# Memory has registered read output; landing_pc adds its existing out_data FF,
# then g_hop[q].u_rsp, then rowctl rsp FF and the existing BOUTs. No stage added.
outs=[(397.44,690.12),(648,690.12),(648,835.92),(648,795.96)]
hops=[(648,690.12),(773.28,690.12),(773.28,760.05),(773.28,760.05)]
rowctl=(895.104,610.2); boutK=(986.04,310.5); boutV=(986.04,603.18)
read_paths=[]
for q,r in enumerate(rows):
    x,y=r['origin_um']; bs=[box for n,v in SRAM.items() if n.startswith('rd_out[') for _,box in v]
    yy=[y+(b[1]+b[3])/2 for b in bs]
    # Explicit legal-side dogleg, outside the memory's conservative4.32um halo.
    for sy in [min(yy),max(yy)]:
        p=[(x+.012,sy),(x-4.32,sy),(x-4.32,outs[q][1]),outs[q]]
        rr.append(dict(kind=f'SRAM{q} read -> existing out_data',path_um=p,length_um=length(p)))
    read_paths += [[(x+.012,(min(yy)+max(yy))/2),(x-4.32,(min(yy)+max(yy))/2),(x-4.32,outs[q][1]),outs[q]],
                   [outs[q],hops[q]],[hops[q],rowctl]]
    for k,p in [('out_data -> existing hop295',[outs[q],hops[q]]),('hop295 -> existing rowctl',[hops[q],rowctl])]:
        rr.append(dict(kind=f'bank{q} {k}',path_um=p,length_um=length(p)))
for name,dst in [('KRSP',boutK),('RSP',boutV)]:
    p=[rowctl,(dst[0],rowctl[1]),dst];read_paths.append(p)
    rr.append(dict(kind=f'rowctl -> existing BOUT {name}',path_um=p,length_um=length(p)))
assert max(e['length_um'] for e in rr) <=405
parentpins=json.loads((I/'parent_pins.json').read_text())
pinreach={}
for name,xy in [('o_slg_Q_N_krsp',boutK),('o_slg_Q_N_rsp',boutV)]:
    ps=[p for p in parentpins if p['bus']==name]
    pinreach[name]=max(abs(xy[0]-p['x'])+abs(xy[1]-p['y']) for p in ps)
assert max(pinreach.values()) <=150
guidepoints=[p for pp in relay_centres for p in pp]+outs+hops+[rowctl,boutK,boutV]
for r in rows:
    x,y=r['origin_um'];guidepoints += [(x-8.64,y+20.52),(x+SSIZE[0]+8.64,y+20.52)]
for x,y in guidepoints:
    assert all(not (b[0] < x < b[2] and b[1] < y < b[3]) for b in pcs+islands+[r['halo'] for r in rows])

result=dict(schema='opentallas.hhp.four_sram_geometry_prep.v1',status='PREP_NOT_ADOPTED_NO_CAD',
            source_type=P['type'],outline_um=P['outline_um'],PC_data_pin_ranges=data_ranges,
            SRAMs=rows,source_data_association='selected R2C c_pc preserves payload[255:0]; group_h reverses lanes and concat reverses back, so bankq receives PCq',
            added_FF=0,added_data_edges=0,source_relay_delays=delays,
            existing_state_guide_paths=rr,max_screened_stage_Manhattan_um=max(e['length_um'] for e in rr),
            proposed_BOUT_pin_reach_um=pinreach,
            path_screen_scope='soft guide feasibility only; not placed cells, legal routes or timing; native GEN/PLACE review still required',
            original_soft_SRAM_sites_invalid_inside_hard_lots=True,
            original_soft_SRAM_Y_phase_error_um=.012,
            holds=['genuine head hardview absent; its data pins here are explicitly planned only',
                   'parent FT roles/wiring and coherent source projection remain pending',
                   'complete source-date/programme join and timing qualification pending',
                   'not a generated hard-macro kit; actual GEN render/native PG/pin/access/clock/guides and placement required'],
            inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in I.iterdir() if p.is_file()})
(HERE/'placement.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'sram_sites_PREP.tcl').write_text('# PREP ONLY: combine with a normally generated, source-closed hard-macro kit; no adoption/CAD approval.\n'+''.join(
    f"place_macro -macro_name {{{r['instance']}}} -location {{{r['origin_um'][0]:.3f} {r['origin_um'][1]:.3f}}} -orientation R0 -exact\n" for r in rows))

fig,ax=plt.subplots(figsize=(11,14));ax.set_aspect('equal')
ax.add_patch(Rectangle((0,0),*P['outline_um'],fill=False,lw=2,color='black'))
for q,(c,b) in enumerate(zip(P['hard_cores'],pcs)):
    ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#fee8c8' if q==0 else '#d7e8f7',edgecolor='#936113' if q==0 else '#28618b',hatch='//' if q==0 else None,lw=1.4))
    ax.text((b[0]+b[2])/2,(b[1]+b[3])/2,f"PC{q} {'genuine head SOFT region' if q==0 else 'real r27c provisional view'}\n{c['orient']} 397.44 x 362.88\n{'planned pins / no hardview' if q==0 else 'timing NOT SIGNED'}",ha='center',va='center',fontsize=8)
    a,z,yy,_=data_ranges[q];ax.plot([a,z],[yy,yy],lw=4,color='#b87813' if q==0 else '#0d73a5')
for b in islands:ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#ae3e4f',alpha=.5))
for name,(x,y) in P['relay_sites'].items():ax.plot(x,y,'x',color='#b62020',ms=5)
for t in TAPS:ax.plot(t['x'],t['y'],'^',color='#8b46a5',ms=6)
for r in rows:
    x,y=r['origin_um'];w,h=r['size_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#a7dca6',edgecolor='#1c6628',lw=1.5))
    ax.add_patch(Rectangle(r['halo'][:2],r['halo'][2]-r['halo'][0],r['halo'][3]-r['halo'][1],fill=False,edgecolor='#56895d',ls=':',lw=.7))
    ax.text(x+w/2,y+h/2,f"SRAM{r['bank']}\nR0",ha='center',va='center',fontsize=8)
    ax.plot(*r['clk_pin_um'],'o',ms=3,color='#613c84')
for p in write_paths:ax.plot(*zip(*p),color='#207d5a',ls='--',lw=.9,alpha=.85)
for q,pp in enumerate(relay_centres):
    ax.plot(*zip(*pp),'o',color='#207d5a',ms=3)
    ax.text(pp[0][0]+6,pp[0][1]+5,f'existing D{delays[q]}',fontsize=7,color='#1b654c')
for p in read_paths:ax.plot(*zip(*p),color='#7556a7',ls=':',lw=.8,alpha=.7)
for xy,label in [(rowctl,'existing rowctl\nguide'),(boutK,'BOUT K'),(boutV,'BOUT V')]:
    ax.plot(*xy,'s',color='#7556a7',ms=4);ax.text(xy[0]+5,xy[1]+5,label,fontsize=7,color='#59417f')
ax.text(10,1510,'HHP 4-SRAM dataflow PREP • real BASE LEF / planned genuine-head pins',va='top',fontsize=12)
ax.text(10,-45,'All SRAMs outside PC lots and126 clock reservations; M4 pin phase corrected.\nDashed/dotted paths are candidate guides for EXISTING state, not routes/placed FFs.\nNo new FF/cycle or head alias. FT/programme/native GEN+PG/clock/place/timing HOLD.',fontsize=9)
ax.set_xlim(-25,1060);ax.set_ylim(-100,1545);ax.set_xlabel('um');ax.set_ylabel('um');ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(HERE/'hhp_four_sram_prep.png',dpi=160);plt.close(fig)
print(json.dumps({'status':result['status'],'SRAM_clock_reach_max_um':max(r['tap_Manhattan_um'] for r in rows),'data_edges':delays,'all_halo_collisions':0,'all_SRAM_M4_phase_errors':0}))
