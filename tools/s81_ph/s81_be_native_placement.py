#!/usr/bin/env python3
"""Place existing BE hard ownstate; audit real candidate pin pairs without inventing die bindings.

The default report is a slot request and exits 1 while source/view debts remain.
--bindings accepts explicit external pins and clock/reset driver provenance. It never
uses an input's destination clock as its actual reset driver's reference clock.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/arch/s81_be_native_placement_1014'
W, OLD_H, H, Y, SIZE, PITCH = 1541.784, 136.08, 153.36, 117.72, 32.4, 34.56

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
    sl=lef(BASE/'inputs/be_sl_c15e2bf6a.lef')
    cells=[]
    def add(n,m,x,domain,bits):
        cells.append(dict(name=n,master=m,target_x=x,clock=domain,bits=bits))
    # Placement targets interpolate along the actual logical chain. BGR has no
    # qualified source pin abstract yet; x=183.6 is only a search seed, never a pin.
    for s in range(4):
        dest=64.8+388.8*s
        for r in range(3):add(f'g_s[{s}].g_hard.g_ctl[{r}].u_r','dsfd_be_r55_m5',183.6+(dest-183.6)*(r+1)/3,'ck',55)
        for d in ['c','s']:
            for r in range(3):add(f'g_s[{s}].g_hard.g_rst[{r}].u_{d}','dsfd_die_r1_m5',W/2+(dest-W/2)*(r+1)/3,'ck' if d=='c' else 'cks',1)
        add(f'g_s[{s}].g_hard.u_ready','dsfd_die_r1_m5',(W/2+dest+sl['c_l0r[0]'][0])/2,'ck',1)
    for n,d in [('u_rs','ck'),('u_rss','cks')]:add(f'g_hrst.{n}','dsfd_die_rstsync_m5',W/2,d,2)
    xs=[21.6+PITCH*i for i in range(42)]
    _,cols=linear_sum_assignment([[abs(c['target_x']-(x+SIZE/2))**2 for x in xs] for c in cells])
    for c,k in zip(cells,cols):c.update(x=xs[k],y=Y,w=SIZE,h=SIZE,orient='R0')
    assert len(cells)==42 and sum(c['bits'] for c in cells)==692
    by={c['name']:c for c in cells}
    def pin(n,p):
        c=by[n];x,y=pins[c['master']][p];return [round(c['x']+x,6),round(c['y']+y,6)]
    pairs=[];pending=[]
    def pair(net,a,b,klass):
        pairs.append(dict(net=net,source=a,destination=b,kind=klass,
                     reach_um=round(abs(a[0]-b[0])+abs(a[1]-b[1]),6)))
    def external(net,dest,kind):
        v=bindings.get('pins',{}).get(net)
        if not v:pending.append(dict(net=net,destination=dest,kind=kind,reason='actual source pin absent'));return
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
            for r in range(2):pair(f'ctl_s{s}_b{b}_r{r}',pin(n(r),f'o[{b}]'),pin(n(r+1),f'i[{b}]'),'control_relay')
            x,y=sl[destname];pair(f'ctl_s{s}_b{b}_sink',pin(n(2),f'o[{b}]'),[64.8+388.8*s+x,21.6+y],'control_sink')
        for d,root,out in [('c','u_rs','rn_in[0]'),('s','u_rss','rns_in[0]')]:
            n=lambda r:f'g_s[{s}].g_hard.g_rst[{r}].u_{d}'
            pair(f'rn{d}_s{s}_0',pin('g_hrst.'+root,'rn'),pin(n(0),'i'),'reset_relay')
            for r in range(2):pair(f'rn{d}_s{s}_{r+1}',pin(n(r),'o'),pin(n(r+1),'i'),'reset_relay')
            x,y=sl[out];pair(f'rn{d}_s{s}_sink',pin(n(2),'o'),[64.8+388.8*s+x,21.6+y],'reset_sink')
        n=f'g_s[{s}].g_hard.u_ready';external('sp_vm.c_l0r[0]',pin(n,'i'),'ready_source')
        x,y=sl['c_l0r[0]'];pair(f'ready_s{s}_sink',pin(n,'o'),[64.8+388.8*s+x,21.6+y],'ready_sink')
    for n,reset in [('u_rs','rst'),('u_rss','rss')]:
        external(f'sp_vm.{reset}[0]',pin('g_hrst.'+n,'rst'),'async_reset_source')
    # Optimize the exact known pin-pair reach with discrete row swaps.
    # External pins are deliberately absent from this objective until assigned.
    origin=np.array([c['x'] for c in cells]);slots=origin.copy()
    def owner(pt):
        for i,c in enumerate(cells):
            if c['x']<=pt[0]<=c['x']+SIZE and c['y']<=pt[1]<=c['y']+SIZE:return i
        return len(cells)
    ia=np.array([owner(p['source']) for p in pairs]);ib=np.array([owner(p['destination']) for p in pairs])
    ax=np.array([p['source'][0] for p in pairs]);bx=np.array([p['destination'][0] for p in pairs])
    dy=np.array([abs(p['source'][1]-p['destination'][1]) for p in pairs])
    targets=np.array([c['target_x']-SIZE/2 for c in cells])
    def score(xx):
        shift=np.append(xx-origin,0);reach=np.abs(ax+shift[ia]-bx-shift[ib])+dy
        return float(np.square(np.maximum(reach-495,0)).sum()*10000+np.square(xx-targets).sum())
    best=score(slots)
    for sweep in range(8):
        changed=False
        for i in range(len(cells)):
            for j in range(i+1,len(cells)):
                slots[i],slots[j]=slots[j],slots[i];v=score(slots)
                if v<best:best=v;changed=True
                else:slots[i],slots[j]=slots[j],slots[i]
        if not changed:break
    shift=np.append(slots-origin,0)
    for k,p in enumerate(pairs):
        p['source'][0]=round(p['source'][0]+shift[ia[k]],6)
        p['destination'][0]=round(p['destination'][0]+shift[ib[k]],6)
        p['reach_um']=round(abs(p['source'][0]-p['destination'][0])+dy[k],6)
    for c,x in zip(cells,slots):c['x']=round(float(x),6)
    for p in pending:
        if 'destination' in p:
            i=next((i for i,o in enumerate(origin) if o<=p['destination'][0]<=o+SIZE and Y<=p['destination'][1]<=Y+SIZE),len(cells))
            p['destination'][0]=round(p['destination'][0]+shift[i],6)
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
    for i,c in enumerate(cells):
        for d in cells[i+1:]:
            if min(c['x']+SIZE,d['x']+SIZE)>max(c['x'],d['x']) and min(c['y']+SIZE,d['y']+SIZE)>max(c['y'],d['y']):violations.append([c['name'],d['name']])
    # Route horizontal segments over the M5 relay row on M6; V segments in
    # open space to the W/S pin. Demand is audited per10.8um bin and54um window.
    grid=10.8;nx=math.ceil(W/grid);ny=math.ceil(H/grid)
    dh=np.zeros((ny,nx));dv=np.zeros((ny,nx));ch=np.zeros_like(dh);cv=np.zeros_like(dv)
    for iy in range(ny):
        for ix in range(nx):
            x=(ix+.5)*grid;y=(iy+.5)*grid
            inrelay=any(c['x']<=x<c['x']+SIZE and c['y']<=y<c['y']+SIZE for c in cells)
            inslice=any(64.8+388.8*s<=x<367.2+388.8*s and 21.6<=y<114.48 for s in range(4))
            width=min(grid,W-ix*grid);height=min(grid,H-iy*grid)
            ch[iy,ix]=height*.8*(0 if inslice else 1/.064 if inrelay else 7/.270/2+1/.048+1/.064)
            cv[iy,ix]=width*.8*(0 if inslice else .85/.064 if inrelay else 1/.036/2+1/.048+.85/.064)
    zero_capacity=[]
    for p in pairs:
        a,b=p['source'],p['destination'];kind=p['kind']
        if kind.endswith('sink'):
            # W sinks approached immediately outside the macro; S ready approached below it.
            if kind=='ready_sink':
                origin=64.8+388.8*int(p['net'].split('_')[1][1:])
                left=min([origin-3.24,origin+302.4+3.24],key=lambda x:abs(a[0]-x)+abs(b[0]-x))
                pts=[a,[left,a[1]],[left,18.36],[b[0],18.36],b]
            else:pts=[a,[b[0]-3.24,a[1]],[b[0]-3.24,b[1]],b]
        else:pts=[a,[b[0],a[1]],b]
        # Use the upper M6 track band where the detour fits the same500um budget.
        # Keeping an actual-pin490um hop straight avoids adding hidden wire reach.
        upper=140.508
        trial=[a,[a[0],upper],[pts[1][0],upper]]+pts[2:] if kind.endswith('sink') else [a,[a[0],upper],[b[0],upper],b]
        trial_len=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(trial,trial[1:]))
        if trial_len<=500:pts=trial
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
        source_commit='4beabe410d050e61103985cd44aa7725a1f141ae',source_files={p:digest(ROOT/p) for p in ['rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv','rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv']},configuration=dict(NS=4,MD=9,XT=2,KX=4,DIE_D=3,DR=3,HARD_RELAYS=1),inputs={str(p.relative_to(ROOT)):digest(p) for p in sorted((BASE/'inputs').iterdir())},
        slot_request=dict(current_be_height_um=OLD_H,requested_be_height_um=H,delta_height_um=round(H-OLD_H,6),north_band_um=round(H-114.48,6),
            current_vm_outline_um=[W,3952.776],requested_vm_outline_um=[W,round(3952.776+H-OLD_H,6)],move_bgq_fe_y_um=round(H-OLD_H,6),
            preserve='BE_SL origins and all stages; no additional latency',adopted=False),
        cells=cells,ownstate=dict(control=660,reset_ready=28,reset_synchronizers=4,total_bits=692,
            convention='688 relay bits plus two 2-bit reset synchronizers'),
        pin_sources=dict(relay='actual CTS IOP TCL (candidate, route pending)',be_sl='actual c15e2bf6a LEF; die must bind selected source/view'),
        control_bit_mapping=packing,pairs=pairs,pending_source_pairs=pending,
        placement_violations=violations,reach_over_500=over,routed_length_over_500=[p for p in pairs if p['routed_length_um']>500],zero_capacity_crossings=zero_capacity,cuts=cuts,cut_limit=.6,
        cut_scope='partial ownstate traffic only; missing source pairs and all BE unrelated buses excluded; endpoint macro landings excluded',
        clock_bindings=bindings.get('clocks',{}),reset_bindings=bindings.get('resets',{}),clock_debts=clock_debts,reset_debts=reset_debts,
        required_before_submit=['die adopts slot and actual per-bit pins','production BGR qualified leaf view','BE_SL selected view/source binding','actual clock/reset source binding','all parent traffic cuts and pin alignment'],
        partial_known_ownstate_pass=bool(not violations and not over and not zero_capacity and all(p['routed_length_um']<=500 for p in pairs) and all(cuts[k]<=.6 for k in ['full_vertical','full_horizontal','window_vertical','window_horizontal'])),
        pass_=False)

def main():
    global H
    ap=argparse.ArgumentParser();ap.add_argument('--be-height',type=float,default=153.36);ap.add_argument('--bindings',type=Path);ap.add_argument('--out',type=Path,default=BASE/'request.json');a=ap.parse_args()
    H=a.be_height
    d=build(json.loads(a.bindings.read_text()) if a.bindings else {})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(cells=len(d['cells']),ownstate=d['ownstate'],placement_violations=len(d['placement_violations']),
        known_pairs=len(d['pairs']),pending_source_pairs=len(d['pending_source_pairs']),reach_over_500=len(d['reach_over_500']),
        max_known_reach_um=max(p['reach_um'] for p in d['pairs']),cuts=d['cuts'],pass_=d['pass_']),indent=2))
    return 1
if __name__=='__main__':raise SystemExit(main())
