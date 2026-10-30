#!/usr/bin/env python3
"""Prepare the owner-authorized local LP H2 physical event; never edit its input.

The output is a candidate, requiring landing/reset recomposition, G0C, strict
bind, die clock and visual review before adoption. Child timing views remain
absent until their own sign-off. No RTL or arithmetic changes are made here.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import schema as S

TYPES = ('dsdv_slice_lepw_mus_LP__t2', 'dsdv_slice_lepw_mu_LP__t2',
         'dsdv_slice_lepe_mu_LP__t2', 'dsdv_slice_lepe_nh_mus_LP__t1')
LANE_X = (8.64, 319.68, 820.8, 1131.84)
LANE_WH = (295.92, 444.96)
LN_WH = (112.32, 112.32)


def overlap(a, b, gap=0):
    return a[0] < b[2]+gap and b[0] < a[2]+gap and a[1] < b[3]+gap and b[1] < a[3]+gap


def box(c):
    x, y = c['origin_um']; dx, dy = c.get('track_offset_um', [0, 0]); w, h = c['outline_um']
    return x+dx, y+dy, x+dx+w, y+dy+h


def pin(c, p):
    x, y = p['x'], p['y']; w, h = c['outline_um']
    if c['orient'] == 'MX': y = h-y
    dx, dy = c['track_offset_um']
    return [round(c['origin_um'][0]+dx+x, 4), round(c['origin_um'][1]+dy+y, 4)]


def core(inst, module, origin, wh, orient, pins, lef):
    return dict(inst='u_bound.'+inst, module=module, origin_um=origin,
                outline_um=list(wh), orient=orient,
                track_offset_um=[.108, .012 if orient == 'R0' else .036],
                pins_file=pins, lef=lef, obs_max='M5',
                note='H2 LP existing module boundary; prospective view, no SIGNED/timing claim')


def bus_entries(t):
    out = {b['name']: (b, 'window_um', 'face') for b in t['buses']}
    for ft in t.get('ft_slots', []):
        out[ft['name']+'_i'] = (ft, 'in_window_um', 'in_face')
        out[ft['name']+'_o'] = (ft, 'out_window_um', 'out_face')
    return out


def update_geometry(t, name, window, layers=None, order=None):
    b, wk, fk = bus_entries(t)[name]
    b[wk] = [round(float(x), 6) for x in window]
    stem = wk.split('_window')[0] if wk != 'window_um' else ''
    if layers is not None: b[stem+'_layers' if stem else 'layers'] = list(layers)
    if order is not None: b[stem+'_order' if stem else 'order'] = order


def local_geom(P, part, die_face, window, layers, order):
    tf = P.type_face(part, die_face)
    p = P.parts[part]; w, h = P.ptype(part)['outline_um']; o = p.get('orient', 'R0')
    flip = (tf in 'NS' and o in ('MY', 'R180')) or (tf in 'EW' and o in ('MX', 'R180'))
    axis = 0 if tf in 'NS' else 1; span = w if axis == 0 else h; off = p['origin_um'][axis]
    a, b = window[0]-off, window[1]-off
    if flip: a, b, order = span-b, span-a, 'lsb_high' if order == 'lsb_low' else 'lsb_low'
    return tf, [round(a, 6), round(b, 6)], layers, order


def pack_parent(t, face):
    """Preserve exact 45/25 parent SRAM identities, masters and track phases."""
    rows = [c for c in t['contents'] if c.get('lef')]
    blocks = [box(c) for c in t['hard_cores']]
    bands = t.get('clock', {}).get('landing_contract', {}).get('bands', {})
    blocks += [tuple(b['rect_um']) for b in bands.values()]
    # All LP FT trunks are placed in one street; leave the whole street clear.
    blocks += [(615.708, 0, 820.908, t['outline_um'][1])]
    W, H = t['outline_um']; placed=[]
    for c in sorted(rows, key=lambda c: (-c['outline_um'][0]*c['outline_um'][1], c['inst'])):
        w, h = c['outline_um']; ox, oy = c['origin_um']
        px, py = round(ox % 8.64, 6), round(oy % 8.64, 6)
        found = None
        # Put the LEP/MU SRAMs beside the LN-facing parent logic, rather than
        # collecting them against the far outside edge of the parent slot.
        if face == 'S':
            ys = range(math.ceil(730.08/8.64), int((H-h-43.2)/8.64)+1)
        else:
            ys = reversed(range(5, int((488.16-h)/8.64)+1))
        for yi in ys:
            y = yi*8.64+py
            for xi in range(5, int((W-w-43.2)/8.64)+1):
                x = xi*8.64+px; b=(x, y, x+w, y+h)
                if not any(overlap(b, q, 10.8) for q in blocks+placed):
                    found=(x, y); break
            if found: break
        if found is None: raise ValueError('no legal parent SRAM site: '+c['inst'])
        c['origin_um']=[round(v, 6) for v in found]; placed.append(box(c))
    return len(rows)


def prepare(raw, plan_path):
    P=S.Plan(raw, plan_path); out=copy.deepcopy(raw); changed={}; receipts={}
    for tn in TYPES:
        t=out['partition_types'][tn]; n=2 if 'nh_mus' in tn else 4
        face=next(b['face'] for b in t['buses'] if b['name']=='coll_i0')
        orient='R0' if face=='S' else 'MX'; side='w' if 'lepw' in tn else 'e'
        y=129.6 if face=='S' else 648.0; ly=596.16 if face=='S' else 509.76
        hc=[]; taps=[]
        for i in range(n):
            mod=f'dsfd_coll_lane_{side}_safe8_ntf'; base=f'h2_2249/coll_{side}'
            c=core(f'u_u_ln{i}', mod, [LANE_X[i], y], LANE_WH, orient,
                   base+'/plan_pins.json', 'physical/die_plan/s81/'+base+'/lane.lef'); hc.append(c)
            pp=json.loads((HERE/c['pins_file']).read_text())['pins']; cp=next(p for p in pp if p['name']=='ck[0]')
            taps.append(dict(name=c['inst'], kind='core', xy=pin(c,cp), insertion_ps=250, insertion_ff_ps=202.5,
                             note='H2 prospective core clock budget, measured view pending'))
            lm='ot_s81_mu72_lnland' if 'lepe_mu_' in tn and i<2 else 'ot_s81_mu72_lnland_nst'
            lb=f'cores/h2/{lm}'; l=core(f'u_u_lnl{i}', lm, [LANE_X[i]+86.4, ly], LN_WH, orient,
                                      lb+'/pins.json', 'physical/die_plan/s81/'+lb+'/'+lm+'.lef'); hc.append(l)
            lp=json.loads((HERE/l['pins_file']).read_text())['pins']
            for ck in ('ck_k','ck_n'):
                cp=next(p for p in lp if p['name']==ck)
                taps.append(dict(name=l['inst']+'.'+ck,kind='core',xy=pin(l,cp),insertion_ps=250,
                                 insertion_ff_ps=202.5,note='H2 same-parent-clock dual-input LN; measured view pending'))
        # The lane SRAMs move inside those actual source masters; never duplicate them at parent level.
        old=t['contents']; t['contents']=[c for c in old if not re_lane_macro(c)]
        removed=len(old)-len(t['contents'])
        if removed != 55*n: raise ValueError(f'{tn}: expected {55*n} child SRAM rows, got {removed}')
        t['hard_cores']=hc; t['clock']['core_taps']='early'; t['clock']['taps']=taps
        # Align each outside collective bundle with its own macro's actual pins.
        for b in t['buses']:
            if not b['name'].startswith(('coll_i','coll_o')): continue
            i=int(b['name'][-1]); modulepins=json.loads((HERE/hc[2*i]['pins_file']).read_text())['pins']
            pn='rx[1]' if b['name'].startswith('coll_i') else 'tx[0]'
            q=next(q for q in modulepins if q['name']==pn); x=pin(hc[2*i], q)[0]
            b.update(window_um=[x,round(x+b['width']*.24,6)],layers=['M5'],order='lsb_low')
            changed[(tn,b['name'])]=True
        # Existing slot buses share a straight central street on both faces.
        cursor=627.072
        for ft in t.get('ft_slots',[]):
            width=math.ceil((ft['width']+1)/5.5/.048)*.048
            for end in ('in','out'):
                if ft[end+'_face'] in 'NS':
                    ft[end+'_window_um']=[round(cursor,6),round(cursor+width,6)]
                    changed[(tn,ft['name']+('_i' if end=='in' else '_o'))]=True
            cursor+=width+1.728
        for b in t['buses']:
            if b['face']!=face or b['name'].startswith('coll_'): continue
            width=math.ceil((b['width']+1)/5.5/.048)*.048
            b['window_um']=[round(cursor,6),round(cursor+width,6)];cursor+=width+1.728
            changed[(tn,b['name'])]=True
        if cursor>810.108: raise ValueError(f'{tn}: street windows exceed clear street ({cursor})')
        # The opposite outside face has no hard-lane row. Its unchanged buses
        # may overlap the newly straightened FT street; move only those actual
        # conflicts into a free interval on that opposite face.
        opposite=S.OPP[face]
        opp=[b for b in t['buses'] if b['face']==opposite]
        ft_windows=[ft[end+'_window_um'] for ft in t.get('ft_slots',[]) for end in ('in','out')
                    if ft[end+'_face']==opposite]
        for b in opp:
            old=b['window_um'];width=old[1]-old[0]
            def clash(win,other): return win[0]<other[1]+1.728 and other[0]<win[1]+1.728
            if not any(clash(old,q) for q in ft_windows): continue
            occupied=ft_windows+[z['window_um'] for z in opp if z is not b]
            for xi in range(1,166):
                win=[round(xi*8.64,6),round(xi*8.64+width,6)]
                if win[1]<1434.24 and not any(clash(win,q) for q in occupied):
                    b['window_um']=win;changed[(tn,b['name'])]=True;break
            else: raise ValueError(tn+': no opposite-face interval for '+b['name'])
        # Relocate local input rings with their declared bus windows.
        for name,b in t['clock']['landing_contract'].get('bands',{}).items():
            if name.startswith('monitor_'): continue
            es=bus_entries(t)
            if name not in es or (tn,name) not in changed: continue
            obj,wk,fk=es[name];a,z=obj[wk];r=b['rect_um'];width=r[2]-r[0]
            b['rect_um']=[round((a+z-width)/2,6),r[1],round((a+z+width)/2,6),r[3]]
        macro_count=pack_parent(t,face)
        receipts[tn]=dict(lanes=n,hard_cores=len(hc),parent_sram=macro_count,child_sram=removed,
                          std_parent_estimate=dict(zip(TYPES,(186027,148007,138723,117900)))[tn],
                          child_clock_budget_ps=dict(TT=250,FF=202.5),cycle_delta_hardening=0,
                          status='CANDIDATE: landing/reset recomposition and physical gates required')
    # Couple each moved endpoint to its immediate neighbour, cloning a shared type only for this local neighbour.
    counts={}
    for p in out['partitions']: counts[p['type']]=counts.get(p['type'],0)+1
    parts={p['name']:p for p in out['partitions']}; neighbours={}; changed_ports=[]
    for pr in out['ports']:
        hits=[s for s in ('src','dst') if pr[s]['part']!='@die' and
              (parts[pr[s]['part']]['type'],pr[s]['bus']) in changed]
        if not hits: continue
        side=hits[0]; ep=pr[side]; tn=parts[ep['part']]['type']; e=bus_entries(out['partition_types'][tn])[ep['bus']]
        ob,wk,fk=e; lays=ob.get(wk.split('_window')[0]+'_layers',ob.get('layers')) if wk!='window_um' else ob['layers']
        order=ob.get(wk.split('_window')[0]+'_order',ob.get('order','lsb_low')) if wk!='window_um' else ob.get('order','lsb_low')
        g=P.geom_to_die(ep['part'],(ob[fk],ob[wk],lays,order));df,win,layers,order=g
        pr.update(window_um=win,layers=layers,order=order,face=df if side=='src' else S.OPP[df]);pr.pop('segments',None)
        other='dst' if side=='src' else 'src';ne=pr[other]
        if ne['part']!='@die':
            np=parts[ne['part']]; nt=np['type']
            if counts.get(nt,0)>1:
                nn=nt+'__h2_'+ne['part'];out['partition_types'][nn]=copy.deepcopy(out['partition_types'][nt]);np['type']=nn;counts[nn]=1;nt=nn
            tf,lw,ll,lo=local_geom(P,ne['part'],S.OPP[df],win,layers,order)
            update_geometry(out['partition_types'][nt],ne['bus'],lw,ll,lo)
            neighbours[ne['part']]=nt
        changed_ports.append(pr['id'])
    # Price, rather than hide, the extra neighbour relay depth caused by the
    # moved face windows. Existing stages are never removed in this event.
    station_changes=[]
    for tn in set(TYPES) | set(neighbours.values()):
        t=out['partition_types'][tn];w,h=t['outline_um']
        def point(face,z): return {'N':(z,h),'S':(z,0),'E':(w,z),'W':(0,z)}[face]
        for ft in t.get('ft_slots',[]):
            a=list(ft['in_window_um']);b=list(ft['out_window_um'])
            if ft.get('in_order',ft.get('order','lsb_low'))=='lsb_high': a.reverse()
            if ft.get('out_order',ft.get('order','lsb_low'))=='lsb_high': b.reverse()
            length=max(sum(abs(x-y) for x,y in zip(point(ft['in_face'],x),point(ft['out_face'],y)))
                       for x,y in zip(a,b))
            old=ft['stations'];new=max(old,math.ceil(length/405))
            if new!=old:
                ft['stations']=new
                # No old explicitly sited relay path can survive a depth change.
                if ft.get('regs_um') or ft.get('bit_sites_um'):
                    raise ValueError(f'{tn}/{ft["name"]}: explicit relay resiting needed')
                station_changes.append(dict(type=tn,slot=ft['name'],old=old,new=new,
                                            added_cycles=new-old,max_bit_manhattan_um=round(length,3)))
    import gen
    old_latency={lid:P.lane_latency(lid)['cycles'] for lid in P.lanes}
    newP=S.Plan(out,plan_path);out['latency']['lanes']=gen.latency_table(newP)
    priced=[dict(lane=lid,old=old_latency[lid],new=newP.lane_latency(lid)['cycles'],
                 added_cycles=newP.lane_latency(lid)['cycles']-old_latency[lid])
            for lid in newP.lanes if old_latency[lid]!=newP.lane_latency(lid)['cycles']]
    return out,dict(types=receipts,neighbours=neighbours,ports=changed_ports,
                    station_changes=station_changes,lane_cycle_changes=priced,
                    pending=['landing/reset contracts and sidecar','exact bitwise FT reach recheck',
                             'G0C','strict bind','die clock','measured hard-child views'])


def re_lane_macro(c):
    return bool(c.get('lef') and any(c['inst'].startswith(f'u_bound.u_u_ln{i}.') for i in range(4)))


def recompose_local(old, new, sidecar, report, plan_path):
    """Retain crossing identities and recompute only the moved local contracts.

    A missing old reset node is an error: this must never silently invent a
    different reset relation or treat a new clock tap as an old reset output.
    """
    import clock_landing_plan as CLP
    import gen_phys as GP
    import reset_tree as RT
    P=S.Plan(new,plan_path)
    audit={}
    for tn in set(TYPES)|set(report['neighbours'].values()):
        t=new['partition_types'][tn];lc=t['clock'].get('landing_contract')
        if not lc: continue
        ot=old['partition_types'][tn]
        roots=GP.clock_pins(P,tn)
        for pinrec in lc.get('pins',[]):
            nm=pinrec['name'];base=None
            for prefix in ('fclk_in_','fclk_out_','cland_fstart_in_','cland_fstart_out_'):
                if nm.startswith(prefix): base=nm[len(prefix):];break
            if base not in bus_entries(t): continue
            oldxy=CLP._bus_xy(ot,base);newxy=CLP._bus_xy(t,base)
            delta=[b-a for a,b in zip(oldxy,newxy)]
            if any(abs(x)>1e-8 for x in delta):
                candidate=[a+b for a,b in zip(pinrec['xy_um'],delta)]
                pinrec['xy_um']=list(GP._snap_tap(P,*candidate))
                for edge in t['clock'].get('edge_clocks',[]):
                    if edge['port']==nm: edge['tap_um']=list(pinrec['xy_um'])
            if pinrec['kind']=='clock' and pinrec['dir']=='out':
                tap=min(roots,key=lambda r:abs(r[1]-pinrec['xy_um'][0])+abs(r[2]-pinrec['xy_um'][1]))[0]
                if 'source_clock_tap' in pinrec:pinrec['source_clock_tap']=tap
                else:pinrec['source_clock_port']=tap
        tree=RT.for_type(P,tn)
        nodes={r['q']:r['xy'] for r in tree['relays']}
        nodes.update(rst_root_n=tree['root'])
        names=[lc.get('collector_root_node')]+[c.get('node') for c in lc.get('collector_children',[])]
        if any(n and n not in nodes for n in names):
            raise ValueError(f'{tn}: moved tree loses declared collector reset node {names}')
        tapnodes={int(n[7:]):xy for n,xy in nodes.items() if n.startswith('rst_n_t')}
        for source in lc.get('collector_local_sources',[]):
            name=source['name']
            if name not in bus_entries(t):continue
            xy=CLP._bus_xy(t,name);source['pin_xy_um']=xy
            source['band']=copy.deepcopy(lc['bands'][name])
            tap=min(tapnodes,key=lambda i:abs(tapnodes[i][0]-xy[0])+abs(tapnodes[i][1]-xy[1]))
            if abs(tapnodes[tap][0]-xy[0])+abs(tapnodes[tap][1]-xy[1])>405:
                r=source['band']['rect_um'];xy=[(r[0]+r[2])/2,(r[1]+r[3])/2]
                tap=min(tapnodes,key=lambda i:abs(tapnodes[i][0]-xy[0])+abs(tapnodes[i][1]-xy[1]))
            source['xy_um']=xy;source['tap']=tap
        lc['collector_tree']=copy.deepcopy(tree)
        for child in lc.get('collector_children',[]):
            if child.get('node'):child['xy_um']=copy.deepcopy(nodes[child['node']])
        bt=sidecar['collector']['types'][tn]
        bt.update(tree=copy.deepcopy(tree),bands=copy.deepcopy(lc['bands']),
                  local_sources=copy.deepcopy(lc['collector_local_sources']),
                  children=copy.deepcopy(lc['collector_children']))
        if lc.get('collector_root_node'):
            bt['collector_root_xy']=copy.deepcopy(nodes[lc['collector_root_node']])
        audit[tn]=dict(old_depth=(ot['clock'].get('landing_contract',{}).get('collector_tree')or{}).get('depth'),
                       new_depth=tree['depth'],reset_consumers=RT.consumer_count(tree),
                       physical_pins=len(lc.get('pins',[])),reset_nodes='ALL_PRESERVED',
                       source_namespace='u_bound.<exact bound child name>',data_cycles_added=0)
    report['local_contracts']=audit
    # The two longer local reset trees must be visible to boot scheduling.
    # Reuse compose()'s graph-distance/deadline law, without regenerating any
    # unrelated landing topology or inventing a fixed ready date.
    from collections import defaultdict
    W=RT.wf_plan(P);collector=sidecar['collector'];budget=collector['boot_budget']
    before_max=collector['reset_max_release'];before_ready=budget['ready_at_glue_max_cycles']
    depths=dict(budget['local_registered_depths'])
    for pn,row in collector['parts'].items():
        tn=P.parts[pn]['type']
        if tn not in audit or not row['active']:continue
        inf=collector['types'][tn];tree=inf['tree'];root=inf['collector_root_node']
        adj=defaultdict(list)
        for relay in tree['relays']:
            adj[relay['q']].append(relay['d']);adj[relay['d']].append(relay['q'])
        dist={root:0};todo=[root]
        while todo:
            v=todo.pop()
            for z in adj[v]:
                if z not in dist:dist[z]=dist[v]+1;todo.append(z)
        wanted=[f"rst_n_t{s['tap']}" for s in inf['local_sources']]+[c['node'] for c in inf['children']]
        depths[pn]=max([dist[n]+1 for n in wanted]or[0])
    deadlines={}
    def deadline(pn):
        if pn in deadlines:return deadlines[pn]
        inf=collector['types'][P.parts[pn]['type']]
        kids=[deadline(c['part'])+(21 if c['seam'] else CLP.STATUS_FACE_CYCLES) for c in inf['children']]
        deadlines[pn]=max([W['max_release']+21]+kids)+depths[pn]
        return deadlines[pn]
    collector['reset_max_release']=W['max_release']
    budget.update(raw_reset_release_max_cycles=W['max_release'],local_registered_depths=depths,
                  ready_at_glue_max_cycles=deadline(collector['root']),physical_clock_phase_qualified=False)
    report['boot_price']=dict(reset_max_old=before_max,reset_max_new=W['max_release'],
                              ready_max_old=before_ready,ready_max_new=budget['ready_at_glue_max_cycles'],
                              local_reset_K_changes={tn:dict(old=r['old_depth'],new=r['new_depth'])
                                                     for tn,r in audit.items()if r['old_depth']!=r['new_depth']},
                              basis='exact reset_tree.wf_plan + compose graph-distance law; real ready still gates START')
    report['pending']=[x for x in report['pending'] if x!='landing/reset contracts and sidecar']
    report['pending'].append('built CA/START phase and release-offset checks')
    return new,sidecar,report


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('out');a.add_argument('--report',required=True)
    a.add_argument('--sidecar-in');a.add_argument('--sidecar-out');x=a.parse_args()
    old=json.loads(Path(x.plan).read_text());out,report=prepare(old,x.plan)
    if bool(x.sidecar_in)!=bool(x.sidecar_out):a.error('both sidecar paths required')
    if x.sidecar_in:
        out,side,report=recompose_local(old,out,json.loads(Path(x.sidecar_in).read_text()),report,x.plan)
        Path(x.sidecar_out).write_text(json.dumps(side,separators=(',',':'))+'\n')
    Path(x.out).write_text(json.dumps(out,separators=(',',':'))+'\n')
    Path(x.report).write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:len(v) for k,v in report.items() if isinstance(v,(list,dict))}))
