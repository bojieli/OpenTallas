#!/usr/bin/env python3
"""Native MC H1 candidate BE placement with source-derived EP2 latency/count.

MC H1 meansforwardhop1, retaining EP2, QD4, MD12 and DIE_D6. Fifty-four
cells retain1348 relay bits plus four reset-sync bits. Two rows have32.4um W/E and10.8um N/S
channels. Actual relay/BE pin coordinates and unqualified BGR pin requests are
kept distinct; source/reset clocks require their own actual driver provenance.
The default report exits1 because the candidate is unadopted and unqualified.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/arch/s81_be_native_mc_placement_1014'
W, OLD_H, H, Y, SIZE, PITCH = 1887.384, 136.08, 196.56, 117.72, 32.4, 64.8
SL_PITCH = 475.2
BE_BASE_X = 64.8
BE_PIN_REQUEST = False
BE_LEF = BASE/'inputs/be_sl_c15e2bf6a.lef'
def derive_configuration(ep1):
    src=(ROOT/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv').read_text()
    parent=src[src.index('module dsfd_sp_vm_m'):]
    be=src[src.index('module dsfd_vm_be #'):src.index('module dsfd_sp_vm_m')]
    def parameter(text,name):
        return int(re.search(r'parameter integer '+name+r'\s*=\s*(\d+)',text)[1])
    qd=parameter(parent,'QD');nstg=parameter(parent,'NSTG')
    branch=re.search(r'`ifdef OT_VM28_EP1\s+localparam integer EP = (\d+);\s+`else\s+localparam integer EP = (\d+);',parent)
    ep=int(branch[1 if ep1 else 2]);ed=ep+1 if ep else 0
    expression=re.search(r'localparam integer MD = ([^;]+);',parent)[1]
    assert re.fullmatch(r'[A-Z0-9_+*() \-]+',expression)
    md=eval(expression,{'__builtins__':{}},dict(NSTG=nstg,QD=qd,ED=ed))
    xt=parameter(be,'XT');dr=parameter(be,'DR')
    kx=int(re.search(r'localparam integer KX = (\d+);',be)[1])
    assert 'localparam integer DIE_D = MD - KX - XT' in be
    return dict(QD=qd,NSTG=nstg,EP=ep,ED=ed,MD=md,XT=xt,KX=kx,DR=dr,DIE_D=md-kx-xt,
                defines=['OT_VM28_EP1','OT_SPVM_BE_HARD_RELAYS'] if ep1 else ['OT_SPVM_BE_HARD_RELAYS'],
                derivation=expression+'; DIE_D=MD-KX-XT',adoption='candidate selection requested; production source remains flatBGR')
CONFIG=derive_configuration(False)
QD,EP,XT,KX,DR,ED,MD,DIE_D=[CONFIG[k] for k in ['QD','EP','XT','KX','DR','ED','MD','DIE_D']]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def iop(p):
    return {n: (float(x), float(y)) for n,x,y in re.findall(
        r'place_pin -pin_name (\S+) -layer M4 -location \{([\d.]+) ([\d.]+)\}', p.read_text())}
def lef(p):
    out = {}
    for n,b in re.findall(r'PIN\s+(\S+)(.*?)END\s+\1', p.read_text(), re.S):
        r=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b)
        if r:
            x,y,u,v=map(float,r.groups());out[n]=((x+u)/2,(y+v)/2)
    return out

def build(bindings):
    pins={m:iop(BASE/'inputs'/f'{m}_iop.tcl') for m in
          ['dsfd_be_r55_m5','dsfd_die_r1_m5','dsfd_die_rstsync_m5']}
    sl=lef(BE_LEF)
    cells=[]
    def add(n,m,x,domain,bits):
        cells.append(dict(name=n,master=m,target_x=x,clock=domain,bits=bits))
    # Placement targets interpolate along the actual logical chain. BGR has no
    # qualified source pin abstract yet; x=183.6 is only a search seed, never a pin.
    for s in range(4):
        dest=BE_BASE_X+SL_PITCH*s
        for r in range(DIE_D):add(f'g_s[{s}].g_hard.g_ctl[{r}].u_r','dsfd_be_r55_m5',237.6+(dest-237.6)*(r+1)/DIE_D,'ck',55)
        for d in ['c','s']:
            for r in range(3):add(f'g_s[{s}].g_hard.g_rst[{r}].u_{d}','dsfd_die_r1_m5',W/2+(dest-W/2)*(r+1)/3,'ck' if d=='c' else 'cks',1)
        add(f'g_s[{s}].g_hard.u_ready','dsfd_die_r1_m5',(W/2+dest+sl['c_l0r[0]'][0])/2,'ck',1)
    for n,d in [('u_rs','ck'),('u_rss','cks')]:add(f'g_hrst.{n}','dsfd_die_rstsync_m5',W/2,d,2)
    sites=[(21.6+PITCH*i,Y+43.2*r) for r in range(2) for i in range(27)]
    _,cols=linear_sum_assignment([[abs(c['target_x']-(x+SIZE/2))**2 for x,y in sites] for c in cells])
    for c,k in zip(cells,cols):c.update(x=sites[k][0],y=sites[k][1],w=SIZE,h=SIZE,orient='R0')
    assert len(cells)==4*DIE_D+30 and sum(c['bits'] for c in cells)==4*55*DIE_D+32
    by={c['name']:c for c in cells}
    endpoints={}
    for slice_id in range(4):
        for port,xy in sl.items():
            point=(round(BE_BASE_X+SL_PITCH*slice_id+xy[0],6),round(21.6+xy[1],6))
            endpoints[point]=dict(instance=f'g_s[{slice_id}].u_sl',master='dsfd_vm_be_sl',pin=port,source_scope='UNROUTED genuine interface target request; raw-route ETM pending' if BE_PIN_REQUEST else 'c15e2bf6a actual ETM/LEF; current cap eligibility pending')
    def pin(n,p):
        c=by[n];x,y=pins[c['master']][p];point=[round(c['x']+x,6),round(c['y']+y,6)]
        endpoints[tuple(point)]=dict(instance=n,master=c['master'].removesuffix('_m5'),pin=p,logical_clock=c['clock'],source_scope='actual CTS pin; routed ETM pending')
        return point
    pairs=[];pending=[]
    mc_source=(BASE/'inputs/bgl_mc_cc460927f.sv').read_text()
    actual_mc_ed=int(re.search(r'localparam integer ED = (\d+);',mc_source)[1])
    assert actual_mc_ed==ED==3 and '.CLOCK_SPLIT(1)' in mc_source
    assert 'localparam integer HHL = HL - HOP1' in mc_source
    bgr=json.loads((BASE/'inputs/bgr_cc460927f_pin_request.json').read_text())
    provisional={'g_h[0].g_t[3].u_bg.'+v['pin']:dict(xy=[21.6+v['x_um'],H],launch_clock='ck_req_l7') for v in bgr['pins'] if v['pin'].startswith('f_')}
    def pair(net,a,b,klass):
        pairs.append(dict(net=net,source=a,destination=b,source_endpoint=endpoints.get(tuple(round(x,6) for x in a)),destination_endpoint=endpoints.get(tuple(round(x,6) for x in b)),kind=klass,
                     reach_um=round(abs(a[0]-b[0])+abs(a[1]-b[1]),6)))
    def external(net,dest,kind):
        v=bindings.get('pins',{}).get(net)
        if not v:
            pending.append(dict(net=net,destination=dest.copy(),kind=kind,reason='actual qualified source pin absent'))
            if net in provisional:
                pair(net,provisional[net]['xy'].copy(),dest,kind)
                pairs[-1].update(source_endpoint=dict(instance='g_h[0].g_t[3].u_bg.g_l[7].u_l',master='dsfd_vm_bgl28_mc',pin=net.split('.u_bg.')[1],logical_clock='ck_req_l7',source_scope='UNQUALIFIED cc460927f pin request'),source_qualified=False,source_scope='cc460927f UNQUALIFIED pin request; leaf g_l[7].u_l at parentlocal(21.6,0)',candidate_launch_clock='ck_req_l7',production_launch_clock='ck')
            return
        if not all(v.get(k) for k in ['instance','pin','source_sha256','view_sha256']):
            pending.append(dict(net=net,reason='source/view provenance absent'));return
        pair(net,v['xy'],dest,kind)
    packing=[]
    for s in range(4):
        # Concatenation {vx,wex,mx,v5,we5,m5s}; low bits occupy m5s.
        names=[f'f_m5s[{i}]' for i in range(23)]+['f_we5[0]','f_v5[0]']+[f'f_mx[{i}]' for i in range(20)]+[f'f_wex[{i}]' for i in range(5)]+[f'f_vx[{i}]' for i in range(5)]
        for b,destname in enumerate(names):
            n=lambda r:f'g_s[{s}].g_hard.g_ctl[{r}].u_r'
            if b<23:source=f'g_h[0].g_t[3].u_bg.f_d[{640+23*s+b}]'
            elif b==23:source='g_h[0].g_t[3].u_bg.f_we[5]'
            elif b==24:source='g_h[0].g_t[3].u_bg.f_v[5]'
            else:
                ports=[6,7,2,8,9]
                if b<45:source=f'g_h[0].g_t[3].u_bg.f_d[{128*ports[(b-25)//4]+(b-25)%4}]'
                elif b<50:source=f'g_h[0].g_t[3].u_bg.f_we[{ports[b-45]}]'
                else:source=f'g_h[0].g_t[3].u_bg.f_v[{ports[b-50]}]'
            packing.append(dict(slice=s,bit=b,source=source,destination=destname))
            external(source,pin(n(0),f'i[{b}]'),'control_source')
            for r in range(DIE_D-1):pair(f'ctl_s{s}_b{b}_r{r}',pin(n(r),f'o[{b}]'),pin(n(r+1),f'i[{b}]'),'control_relay')
            x,y=sl[destname];pair(f'ctl_s{s}_b{b}_sink',pin(n(DIE_D-1),f'o[{b}]'),[BE_BASE_X+SL_PITCH*s+x,21.6+y],'control_sink')
        for d,root,out in [('c','u_rs','rn_in[0]'),('s','u_rss','rns_in[0]')]:
            n=lambda r:f'g_s[{s}].g_hard.g_rst[{r}].u_{d}'
            pair(f'rn{d}_s{s}_0',pin('g_hrst.'+root,'rn'),pin(n(0),'i'),'reset_relay')
            for r in range(2):pair(f'rn{d}_s{s}_{r+1}',pin(n(r),'o'),pin(n(r+1),'i'),'reset_relay')
            x,y=sl[out];pair(f'rn{d}_s{s}_sink',pin(n(2),'o'),[BE_BASE_X+SL_PITCH*s+x,21.6+y],'reset_sink')
        n=f'g_s[{s}].g_hard.u_ready';external('sp_vm.c_l0r[0]',pin(n,'i'),'ready_source')
        x,y=sl['c_l0r[0]'];pair(f'ready_s{s}_sink',pin(n,'o'),[BE_BASE_X+SL_PITCH*s+x,21.6+y],'ready_sink')
    for n,reset in [('u_rs','rst'),('u_rss','rss')]:
        external(f'sp_vm.{reset}[0]',pin('g_hrst.'+n,'rst'),'async_reset_source')
    # Discrete 2D swaps optimize actual relay/sink and explicitly provisional
    # source pin geometry. Slots retain32.4um W/E face channels throughout.
    origin=np.array([[c['x'],c['y']] for c in cells]);slots=origin.copy()
    def owner(pt):
        for i,c in enumerate(cells):
            if c['x']<=pt[0]<=c['x']+SIZE and c['y']<=pt[1]<=c['y']+SIZE:return i
        return len(cells)
    ia=np.array([owner(p['source']) for p in pairs]);ib=np.array([owner(p['destination']) for p in pairs])
    pa=np.array([p['source'] for p in pairs]);pb=np.array([p['destination'] for p in pairs])
    targets=np.array([[c['target_x']-SIZE/2,Y] for c in cells])
    reach_limits=np.array([130 if p['kind']=='reset_sink' and p['net'].startswith('rns_') else 190 if p['kind']=='reset_sink' else 440 for p in pairs])
    def score(xx):
        shift=np.vstack([xx-origin,[0,0]]);reach=np.abs(pa+shift[ia]-pb-shift[ib]).sum(axis=1)
        return float(np.square(np.maximum(reach-reach_limits,0)).sum()*10000+np.square(xx-targets).sum())
    best=score(slots)
    for sweep in range(12):
        changed=False
        for i in range(len(cells)):
            for j in range(i+1,len(cells)):
                slots[[i,j]]=slots[[j,i]];v=score(slots)
                if v<best:best=v;changed=True
                else:slots[[i,j]]=slots[[j,i]]
        if not changed:break
    shift=np.vstack([slots-origin,[0,0]])
    for k,p in enumerate(pairs):
        p['source']=list(np.round(pa[k]+shift[ia[k]],6))
        p['destination']=list(np.round(pb[k]+shift[ib[k]],6))
        p['reach_um']=round(sum(abs(u-v) for u,v in zip(p['source'],p['destination'])),6)
    for c,xy in zip(cells,slots):c['x'],c['y']=map(float,np.round(xy,6))
    for p in pending:
        if 'destination' in p:
            a=np.array(p['destination']);i=next((i for i,o in enumerate(origin) if all(o<=a) and all(a<=o+SIZE)),len(cells))
            p['destination']=list(np.round(a+shift[i],6))
    clock_debts=[]
    for domain in ['ck','cks']:
        rec=bindings.get('clocks',{}).get(domain,{})
        if not all(rec.get(k) for k in ['driver_instance','driver_pin','source_sha256','reference_clock','period_ps']):
            clock_debts.append(dict(domain=domain,reason='actual clock driver/reference and source absent'))
    reset_debts=[]
    for reset in ['rst','rss']:
        rec=bindings.get('resets',{}).get(reset,{})
        if not all(rec.get(k) for k in ['driver_instance','driver_pin','source_sha256','driver_reference_clock','input_delay_ps']):
            reset_debts.append(dict(reset=reset,reason='actual reset driver reference clock absent; destination clock cannot substitute'))
    violations=[]
    for c in cells:
        if c['x']<0 or c['x']+SIZE>W or c['y']+SIZE>H:violations.append(c['name'])
    channel_violations=[];channel_track_spans=[]
    for i,c in enumerate(cells):
        for d in cells[i+1:]:
            if min(c['y']+SIZE,d['y']+SIZE)>max(c['y'],d['y']):
                gap=max(c['x'],d['x'])-min(c['x']+SIZE,d['x']+SIZE)
                if gap<20-1e-6:channel_violations.append(dict(a=c['name'],b=d['name'],gap_um=gap,required_um=20))
                left=min(c['x']+SIZE,d['x']+SIZE);right=max(c['x'],d['x'])
                snapped=(math.floor((right+1e-9)/.064)-math.ceil((left-1e-9)/.064))*.064
                if 20<=gap<33:channel_track_spans.append(round(snapped,6))
            if min(c['x']+SIZE,d['x']+SIZE)>max(c['x'],d['x']) and min(c['y']+SIZE,d['y']+SIZE)>max(c['y'],d['y']):violations.append([c['name'],d['name']])
    # Route horizontal segments over the M5 relay row on M6; V segments in
    # open space to the W/S pin. Demand is audited per10.8um bin and54um window.
    grid=10.8;nx=math.ceil(W/grid);ny=math.ceil(H/grid)
    dh=np.zeros((ny,nx));dv=np.zeros((ny,nx));ch=np.zeros_like(dh);cv=np.zeros_like(dv)
    for iy in range(ny):
        for ix in range(nx):
            x=(ix+.5)*grid;y=(iy+.5)*grid
            inrelay=any(c['x']<=x<c['x']+SIZE and c['y']<=y<c['y']+SIZE for c in cells)
            inslice=any(BE_BASE_X+SL_PITCH*s<=x<367.2+SL_PITCH*s and 21.6<=y<114.48 for s in range(4))
            width=min(grid,W-ix*grid);height=min(grid,H-iy*grid)
            ch[iy,ix]=height*.8*(0 if inslice else 1/.064 if inrelay else 7/.270/2+1/.048+1/.064)
            cv[iy,ix]=width*.8*(0 if inslice else .85/.064 if inrelay else 1/.036/2+1/.048+.85/.064)
    zero_capacity=[]
    for p in pairs:
        a,b=p['source'],p['destination'];kind=p['kind']
        if kind.endswith('sink'):
            # W sinks approached immediately outside the macro; S ready approached below it.
            if kind=='ready_sink':
                origin=BE_BASE_X+SL_PITCH*int(p['net'].split('_')[1][1:])
                left=min([origin-3.24,origin+302.4+3.24],key=lambda x:abs(a[0]-x)+abs(b[0]-x))
                pts=[a,[left,a[1]],[left,18.36],[b[0],18.36],b]
            else:pts=[a,[b[0]-3.24,a[1]],[b[0]-3.24,b[1]],b]
        else:pts=[a,[b[0],a[1]],b]
        # Use the upper M6 track band where the detour fits the same500um budget.
        # Keeping an actual-pin490um hop straight avoids adding hidden wire reach.
        lane=sum(map(ord,p['net']))%3
        upper=[129.708,164.268,max(a[1],b[1],198.828)][lane] if kind in ['control_source','control_relay'] else max(a[1],b[1],140.508) if not kind.endswith('sink') else a[1]+1.08
        trial=[a,[a[0],upper],[pts[1][0],upper]]+pts[2:] if kind.endswith('sink') else [a,[a[0],upper],[b[0],upper],b]
        trial_len=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(trial,trial[1:]))
        if trial_len<=450:pts=trial
        p['route']=pts
        p['routed_length_um']=round(sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(pts,pts[1:])),6)
        for u,v in zip(pts,pts[1:]):
            if abs(u[1]-v[1])<1e-6:
                iy=min(ny-1,max(0,int(u[1]/grid)))
                for ix in range(max(0,int(min(u[0],v[0])/grid)),min(nx,int(max(u[0],v[0])/grid)+1)):
                    if ch[iy,ix]>0:dh[iy,ix]+=1
                    elif (ix,iy) not in [(int(a[0]/grid),int(a[1]/grid)),(int(b[0]/grid),int(b[1]/grid))]:zero_capacity.append(dict(net=p['net'],axis='H',cell=[ix,iy]))
            else:
                ix=min(nx-1,max(0,int(u[0]/grid)))
                for iy in range(max(0,int(min(u[1],v[1])/grid)),min(ny,int(max(u[1],v[1])/grid)+1)):
                    if cv[iy,ix]>0:dv[iy,ix]+=1
                    elif (ix,iy) not in [(int(a[0]/grid),int(a[1]/grid)),(int(b[0]/grid),int(b[1]/grid))]:zero_capacity.append(dict(net=p['net'],axis='V',cell=[ix,iy]))
    def ratio(d,c):return float((d/np.maximum(c,1e-9)).max())
    cuts=dict(full_vertical=ratio(dh.sum(axis=0),ch.sum(axis=0)),full_horizontal=ratio(dv.sum(axis=1),cv.sum(axis=1)),
        window_vertical=max(ratio(dh[i:i+5].sum(axis=0),ch[i:i+5].sum(axis=0)) for i in range(ny-4)),
        window_horizontal=max(ratio(dv[:,i:i+5].sum(axis=1),cv[:,i:i+5].sum(axis=1)) for i in range(nx-4)))
    worst=[]
    for i in range(ny-4):
        r=dh[i:i+5].sum(axis=0)/np.maximum(ch[i:i+5].sum(axis=0),1e-9)
        if r.max()>=cuts['window_vertical']-1e-9:worst.append(dict(x_um=float(r.argmax()*grid),y_um=i*grid,demand=float(dh[i:i+5,r.argmax()].sum()),capacity=float(ch[i:i+5,r.argmax()].sum())))
    cuts['worst_vertical_windows']=worst
    over=[p for p in pairs if p['reach_um']>500]
    return dict(schema='opentallas.be_native_placement_request.v1',status='requested_not_adopted',
        selected_BE_LEF=dict(path=str(BE_LEF.relative_to(ROOT)),sha256=digest(BE_LEF),eligibility='capM6 stillINVALID; candidateM7 export requiresactualparentaccessprobe/acceptedlegacyviewcap'),source_commit='4beabe410d050e61103985cd44aa7725a1f141ae',candidate_pin_request_commit='cc460927f',MC_source_facts=dict(source_snapshot='results/arch/s81_be_native_mc_placement_1014/inputs/bgl_mc_cc460927f.sv',ED=actual_mc_ed,QD=QD,HL=QD+4+actual_mc_ed,HOP1=1,HHL=QD+3+actual_mc_ed,return_minus_forward_skew=MD,defines=['OT_VMBGL_HOP1'],CLOCK_SPLIT=1,source_integration='native MC parent notyetbuilt; plannedleafg_l[7].u_l'),selected_candidate_support='proven MC H1 meansforwardhop1, retainsEP2/ED3/HL11; noOT_VM28_EP1. Actualnativeparent sourceintegration pending',source_files={p:digest(ROOT/p) for p in ['rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv','rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv']},configuration=dict(NS=4,HARD_RELAYS=1,**CONFIG),production_default_configuration=derive_configuration(False),inputs={str(p.relative_to(ROOT)):digest(p) for p in sorted((BASE/'inputs').iterdir())},
        slot_request=dict(requested_BE_base_x_um=BE_BASE_X,BE_origin_manufacturing_grid_request=BE_BASE_X!=64.8,BE_origin_allocator_lattice_acceptance="OPEN" if BE_BASE_X!=64.8 else "baseline",current_be_height_um=OLD_H,requested_be_height_um=H,delta_height_um=round(H-OLD_H,6),north_band_um=round(H-114.48,6),
            current_vm_outline_um=[1541.784,3952.776],superseded_h1_vm_request_um=[W,3970.056],requested_vm_outline_um=[W,round(3952.776+H-OLD_H,6)],move_bgq_fe_y_um=round(H-OLD_H,6),
            preserve='BE_SL y21.6 and MC EP2/MD12 six control stages; x64.8+475.2s perwidecandidate; no added latency',extra_height_over_h1_request_um=round(H-153.36,6),column_pitch_um=PITCH,face_channel_um=PITCH-SIZE,vertical_gap_um=10.8,rows=2,adopted=False),
        state_epochs=dict(standalone_MD9=dict(DIE_D=3,cells=42,relay_bits=688,total_bits=692,selected=False,channel_rule_valid=False),production_EP2=dict(EP=2,ED=3,MD=12,DIE_D=6,cells=54,relay_bits=1348,total_bits=1352),unqualified_EP1_variant=dict(EP=1,ED=2,MD=11,DIE_D=5,cells=50,relay_bits=1128,total_bits=1132,selected=False),candidate_MC_H1=dict(EP=2,ED=3,MD=12,DIE_D=6,cells=54,relay_bits=1348,total_bits=1352),geometry_latency_delta_cycles=0,candidate_MC_vs_production_control_stage_delta=0),
        placement_lattice=dict(site_um=.054,row_um=.270,channel_grid_um=.064,min_channel_width_tracks=505,cell_outline_site_steps=600,cell_outline_row_steps=120,valid=all(abs(c['x']/.054-round(c['x']/.054))<1e-6 and abs(c['y']/.270-round(c['y']/.270))<1e-6 for c in cells)),
        cells=cells,ownstate=dict(control=4*55*DIE_D,reset_ready=28,relay_bits=4*55*DIE_D+28,reset_synchronizers=4,total_bits=4*55*DIE_D+32,
            convention='proven MC H1 retainsEP2 and six control stages per slice; EP1 fiftycellplan unqualifiedseparatevariant'),channel_rule=dict(source='contract seam_rules.channels',actual_pin_faces=['W','E'],required_min_gap_um=20,planned_gap_um=32.4,min_snapped_M7_track_span_um=min(channel_track_spans),NS_gap_um=10.8,NS_basis='10.8 explicitreservedrowgap; actualrelayIOP hasonlyW/Epins; finalmacroPG/pinhaloqualification stillrequiresroutedLEF',violations=channel_violations),
        pin_sources=dict(relay='actual CTS IOP TCL (candidate, route pending)',be_sl='UNROUTED target contacts; all electrical route/ETM/source-slot binding OPEN' if BE_PIN_REQUEST else 'actual c15e2bf6a LEF; die must bind selected source/view'),
        control_bit_mapping=packing,pairs=pairs,pending_source_pairs=pending,
        placement_violations=violations,reach_over_500=over,routed_length_over_500=[p for p in pairs if p['routed_length_um']>500],zero_capacity_crossings=zero_capacity,cuts=cuts,cut_limit=.6,
        cut_scope='partial candidate ownstate:1356 actual relay/BE pairs plus220 UNQUALIFIED BGR requested pin pairs;6 boundary sources and all BE unrelated buses excluded; endpoint macro landings excluded',pair_counts=dict(actual_relay_be=1356,unqualified_bgr_source=220,actual_qualified_source_debt=len(pending)),candidate_clock_obligations=dict(control_source='ck_req_l7 candidate root fromg_l[7].u_l.u.rb0_*; actualproductionlaunch clock remainsck',capture='BE relayck',delivery='R/FFhold/skew require actualroutedviews; destination clock doesnotestablish source/resetdriverreference'),
        clock_bindings=bindings.get('clocks',{}),reset_bindings=bindings.get('resets',{}),clock_debts=clock_debts,reset_debts=reset_debts,
        be_sl_child_lint=dict(report='results/arch/s81_be_native_mc_placement_1014/be_sl_child_lint_m6.json',verdict='FAIL',status='INVALID_AT_M6',qualification='pin coordinates usable for provisionalgeometry only; exactview requiresrepair/reroute'),
        timing_budget=dict(status='UNQUALIFIED',wire_ps_per_um=.76,max_candidate_routed_wire_ps=round(max(p['routed_length_um'] for p in pairs)*.76,6),same_level_available_ps=683.3,across_level_available_ps=623.3,requirements='Useactualroutedsource/sinkETM o/s/L/H, perclockrootR and actualresetdriverreferenceclock; geometry/candidateclocklabels do notestablishtiming'),
        required_before_submit=['die adopts slot and actual per-bit pins','production BGR qualified leaf view','BE_SL selected view/source binding','actual clock/reset source binding','all parent traffic cuts and pin alignment'],
        partial_candidate_geometry_pass=bool(not violations and not channel_violations and not over and not zero_capacity and all(p['routed_length_um']<=500 for p in pairs) and all(cuts[k]<=.6 for k in ['full_vertical','full_horizontal','window_vertical','window_horizontal'])),
        pass_=False)

def main():
    global H,BE_LEF,BE_BASE_X,BE_PIN_REQUEST
    ap=argparse.ArgumentParser();ap.add_argument('--be-lef',type=Path);ap.add_argument('--be-base-x',type=float,default=64.8);ap.add_argument('--be-pin-request',action='store_true');ap.add_argument('--be-height',type=float,default=196.56);ap.add_argument('--bindings',type=Path);ap.add_argument('--out',type=Path,default=BASE/'request.json');a=ap.parse_args()
    H=a.be_height;BE_BASE_X=a.be_base_x;BE_PIN_REQUEST=a.be_pin_request
    if a.be_lef:BE_LEF=a.be_lef.resolve()
    d=build(json.loads(a.bindings.read_text()) if a.bindings else {})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(cells=len(d['cells']),ownstate=d['ownstate'],placement_violations=len(d['placement_violations']),
        candidate_geometry_pairs=len(d['pairs']),pending_source_pairs=len(d['pending_source_pairs']),reach_over_500=len(d['reach_over_500']),
        max_known_reach_um=max(p['reach_um'] for p in d['pairs']),cuts=d['cuts'],pass_=d['pass_']),indent=2))
    return 1
if __name__=='__main__':raise SystemExit(main())
