#!/usr/bin/env python3
"""Actual routed-pin admission of two staged-head placement alternatives.

This is a necessary-constraint solver, not a fabricated physical implementation.
It searches every 5.4-um origin and R0/MX/MY/R180 orientation in each declared
domain for u_t2, retaining the existing 86 connected children. Failure of this
mandatory final input stage rejects that particular candidate before inventing
u_t1/u_s1 sites. It does not claim that moving existing children is impossible.
Every distance uses the worst corners of *matched bit* routed LEF rectangles.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[2]
SIGNS = np.array(list(itertools.product((-1, 1), repeat=2)))
FLIPS = {'R0': (False, False), 'MX': (False, True),
         'MY': (True, False), 'R180': (True, True)}
PITCH = 5.4
CLEAR = 5.4
LIMIT = 500.


def lef(path):
    text = path.read_text()
    size = tuple(map(float, re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups()))
    pins = {}
    for m in re.finditer(r'^  PIN (\S+)\s*$(.*?)^  END \1\s*$', text, re.M | re.S):
        rects = [tuple(map(float, r)) for r in
                 re.findall(r'\bRECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)', m[2])]
        pins[m[1]] = [p for x0, y0, x1, y1 in rects
                      for p in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))]
    assert 'ck' in pins or 'clk' in pins
    return size, pins


def xf(points, xy=(0., 0.), size=(0., 0.), orient='R0'):
    fx, fy = FLIPS[orient]
    return [(xy[0] + (size[0]-x if fx else x),
             xy[1] + (size[1]-y if fy else y)) for x, y in points]


def coefficients(pairs):
    # For translation t of source, worst Manhattan = max_s(s.t + k_s).
    if len({len(p[1])for p in pairs})==1 and len({len(p[2])for p in pairs})==1:
        a=np.array([p[1]for p in pairs]);b=np.array([p[2]for p in pairs])
        return np.max(np.max(a@SIGNS.T,axis=1)-np.min(b@SIGNS.T,axis=1),axis=0)
    return np.array([max(max(sx*x+sy*y for x, y in a)
                         - min(sx*x+sy*y for x, y in b)
                         for _, a, b in pairs) for sx, sy in SIGNS])


def witness(pairs, xy):
    worst = None
    for name, aa, bb in pairs:
        for a, b in itertools.product(aa, bb):
            d = abs(a[0]+xy[0]-b[0])+abs(a[1]+xy[1]-b[1])
            if worst is None or d > worst['um']:
                worst = dict(bit=name, um=round(d, 6),
                             source_corner=[a[0]+xy[0], a[1]+xy[1]], destination_corner=b)
    return worst


def overlap(site, box):
    x, y, w, h = site; a, b, c, d = box
    return not (x+w+CLEAR <= a+1e-6 or a+c+CLEAR <= x+1e-6
                or y+h+CLEAR <= b+1e-6 or b+d+CLEAR <= y+1e-6)


def front_connections(front_pins, t_pins, plan, orient):
    """Exact staged RTL concatenation; row quarter maps to its own front."""
    size = (21.6, 259.2)
    pairs = []
    for q in range(4):
        box = plan['children'][f'front{q}']
        for name, points in front_pins.items():
            m = re.fullmatch(r'(\w+)(?:\[(\d+)\])?', name)
            base, bit = m.groups(); bit = int(bit or 0)
            if base == 'c_in': src = f'ti_b[{1555+bit}]'
            elif base == 'row_in': src = f'ti_b[{531+256*q+bit}]'
            elif base == 'lt_in': src = f'ti_b[{519+bit}]'
            elif base == 'q_valid_in': src = 'ti_b[518]'
            elif base == 'q_beat_in': src = f'ti_b[{512+bit}]'
            elif base == 'q_data_in': src = f'ti_b[{bit}]'
            elif base == 'e_in': src = f'e_b[{bit}]'
            else: continue  # hid is a constant strap; reset and clocks are separate contracts.
            pairs.append((f'{src}->front{q}.{name}', xf(t_pins[src], size=size, orient=orient),
                          xf(points, box[:2])))
    assert len(pairs) == 4*(4+256+12+1+6+512+16)
    return pairs


def solve(plan, stage, front, domain, name):
    w, h = stage[0]; children = plan['children']; candidates = []
    lo_x, hi_x, lo_y, hi_y = domain
    for ix in range(math.ceil(lo_x/PITCH), math.floor((hi_x-w)/PITCH)+1):
        for iy in range(math.ceil(lo_y/PITCH), math.floor((hi_y-h)/PITCH)+1):
            x, y = round(ix*PITCH, 6), round(iy*PITCH, 6)
            if name == 'adjacent_channel' and overlap((x,y,w,h), (0,0,*plan['slot_outline_um'])):
                continue
            candidates.append((x,y))
    sites = np.array(candidates).reshape((-1, 2))
    occupancy = [([k for k, r in children.items() if overlap((*xy,w,h),r)]) for xy in sites]
    free = np.array([not x for x in occupancy])
    answer = dict(domain_um=domain, origin_pitch_um=PITCH, clearance_um=CLEAR,
                  existing_children=len(children), origins=len(sites), free_origins=int(free.sum()),
                  all_four_orientations_checked=True, reach_pass_origins=0,
                  feasible_sites=[], best_free=None, best_reach_only=None)
    for orient in FLIPS:
        pairs = front_connections(front[1], stage[1], plan, orient)
        distances = np.max(sites @ SIGNS.T + coefficients(pairs), axis=1)
        reach = distances <= LIMIT+1e-6
        answer['reach_pass_origins'] += int(reach.sum())
        for i in np.flatnonzero(reach & free):
            answer['feasible_sites'].append(dict(xy=sites[i].tolist(), orient=orient,
                                                worst_um=round(float(distances[i]),6)))
        for key, mask in (('best_free',free), ('best_reach_only',np.ones(len(sites),dtype=bool))):
            indices = np.flatnonzero(mask)
            if not len(indices): continue
            i = indices[np.argmin(distances[indices])]
            if answer[key] is None or distances[i] < answer[key]['worst']['um']:
                answer[key] = dict(xy=sites[i].tolist(), orient=orient,
                                   worst=witness(pairs,sites[i]), blockers=occupancy[i])
    answer['feasible_sites'].sort(key=lambda s:s['worst_um'])
    answer['admitted'] = bool(answer['feasible_sites'])
    answer['constraint'] = ('Mandatory u_t2 -> actual front input rectangles must be <=500 um, '
                            'with no overlap or less than5.4 um clearance against all86 unchanged children. '
                            'Failure rejects this domain on this origin lattice; repacking/rotation90/new views '
                            'are outside this bounded proof, not declared impossible.')
    return answer


def continuous_bound(plan, stage, front, domains):
    """LP lower bound removes packing and origin-grid constraints: stronger refusal."""
    best = None
    for orient in FLIPS:
        pairs=front_connections(front[1],stage[1],plan,orient)
        k=coefficients(pairs)
        for label,bounds in domains.items():
            result=linprog([0,0,1],A_ub=np.column_stack((SIGNS,-np.ones(4))),
                           b_ub=-k,bounds=[bounds[:2],bounds[2:],(0,None)],method='highs')
            if result.success and (best is None or result.fun<best['minimum_um']):
                best=dict(minimum_um=round(float(result.fun),6),xy=result.x[:2].tolist(),
                          orient=orient,domain=label,
                          worst=witness(pairs,result.x[:2]),
                          certificate=dict(signs=SIGNS.tolist(),constants=k.tolist(),
                                           bounds_um=bounds,inequality_duals=result.ineqlin.marginals.tolist(),
                                           lower_bound_duals=result.lower.marginals.tolist(),
                                           upper_bound_duals=result.upper.marginals.tolist()))
    return best


def internal_edges():
    """RTL-exact all incident data/reset nets; straps and clock nets separate."""
    edges={}
    def link(a,pa,b,pb):edges.setdefault((a,b),[]).append((pa,pb))
    for t in range(16):
        f=f'front{t//4}';i=f'stin{t}';lane=f'lane{t}';k=f'stk{t}'
        for bit in range(233):
            link(f,f'f_t{t%4}[{bit}]',i,f'dr_i[{bit}]' if bit<217 else f'cr_i[{bit-217}]')
        for stem,offset,n in [('c_in',None,4),('row_in',152,64),('e_in',136,16),
                              ('lt_in',None,12),('hid',0,2),('q_beat_in',130,6),('q_data_in',2,128)]:
            for bit in range(n):
                if stem=='c_in':src='dr_o[216]' if bit==0 else f'cr_o[{12+bit}]'
                elif stem=='lt_in':src=f'cr_o[{1+bit}]'
                else:src=f'dr_o[{offset+bit}]'
                link(i,src,lane,f'{stem}[{bit}]')
        link(i,'cr_o[0]',lane,'q_valid_in');link(i,'lane_rst_n',lane,'rst_n')
        for bit in range(32):
            link(lane,f'kp[{bit}]',k,f'kp_i[{bit}]')
            link(k,f'kp_o[{bit}]','ktree',f'kp_in[{32*t+bit}]')
        link(lane,'kpv',k,'kpv_i');link(lane,'gf',k,'gf_i')
        link(k,'gf_o','ktree',f'gf_in[{t}]')
        if t==0:link(k,'kpv_o','ktree','kpv_in')
        for bit in range(64):
            link(lane,f'nb[{bit}]',f'nb1_{t}',f'nb_i[{bit}]')
            link(f'nb1_{t}',f'nb_o[{bit}]',f'nb2_{t}',f'nb_i[{bit}]')
    for bit in range(32):link('ktree',f'sc_d[{bit}]','score',f'sc_i[{bit}]')
    link('ktree','sc_f','score','sf_i');link('ktree','g_f','score','gf_i')
    link('score','kt_rst_n','ktree','rst_n')
    for q in range(4):link(f'front{q}','pack_fault','score',f'pack_fault[{q}]')
    return edges


def repack_fronts(plan,leafs,inside_stage=False):
    proposed=json.loads(json.dumps(plan));children=proposed['children']
    for q in range(4):children[f'front{q}']=[388.8+(167.4 if inside_stage else 135)*(q%2),5.4+48.6*(q//2),129.6,43.2]
    children['ktree']=[351.0 if inside_stage else 388.8,102.6,151.2,97.2]
    children['score']=[604.8 if inside_stage else 550.8,151.2,43.2,43.2]
    if inside_stage:children['u_t2']=[529.2,0.,21.6,259.2]
    def kind(n):
        if n.startswith('front'):return 'front'
        if n.startswith('lane'):return 'lane'
        if n.startswith('stin'):return 'stin'
        if n.startswith('stk'):return 'stk'
        if n.startswith('nb'):return 'nb'
        return n
    edges=internal_edges();coefs={}
    for (a,b),bits in edges.items():
        pairs=[(f'{a}.{pa}->{b}.{pb}',leafs[kind(a)][1][pa],leafs[kind(b)][1][pb]) for pa,pb in bits]
        coefs[a,b]=coefficients(pairs)
    # Rehome the eight displaced stations, preserving all16 lane placements.
    protected={f'front{q}'for q in range(4)}|{'ktree','score'}|({'u_t2'}if inside_stage else set())
    hits=[(a,b)for(a,aa),(b,bb)in itertools.combinations(children.items(),2)if overlap(aa,bb)]
    moving_set={b if a in protected else a for a,b in hits}
    for (a,b),k in coefs.items():
        if np.max((np.array(children[a][:2])-children[b][:2])@SIGNS.T+k)>480:
            if a in protected and b not in protected:moving_set.add(b)
            elif b in protected and a not in protected:moving_set.add(a)
    moving=sorted(moving_set,key=lambda n:(-children[n][2]*children[n][3],n))
    pending=set(moving);moves=[]
    for n in moving:
        pending.remove(n);w,h=children[n][2:];W,H=plan['slot_outline_um']
        sites=np.array([(round(x*PITCH,6),round(y*PITCH,6))
                        for x in range(math.ceil(CLEAR/PITCH),math.floor((W-w-CLEAR)/PITCH)+1)
                        for y in range(math.ceil(CLEAR/PITCH),math.floor((H-h-CLEAR)/PITCH)+1)])
        valid=np.ones(len(sites),dtype=bool);worst=np.zeros(len(sites))
        for m,r in children.items():
            if m==n or m in pending:continue
            valid &= ((sites[:,0]+w+CLEAR<=r[0]+1e-6)|(r[0]+r[2]+CLEAR<=sites[:,0]+1e-6)|
                      (sites[:,1]+h+CLEAR<=r[1]+1e-6)|(r[1]+r[3]+CLEAR<=sites[:,1]+1e-6))
        for (a,b),k in coefs.items():
            if n not in (a,b) or a in pending or b in pending:continue
            delta=sites-np.array(children[b][:2]) if n==a else np.array(children[a][:2])-sites
            worst=np.maximum(worst,np.max(delta@SIGNS.T+k,axis=1))
        good=np.flatnonzero(valid & (worst<=480))
        if not len(good):
            return dict(admitted=False,reason=f'No greedy site with20um margin for {n}',moves=moves,
                        initial_conflicts=hits,children=children)
        old=np.array(plan['children'][n][:2]);cost=worst[good]+.01*np.abs(sites[good]-old).sum(axis=1)
        best=good[np.argmin(cost)];children[n]=[*sites[best].tolist(),w,h]
        moves.append(dict(child=n,xy=sites[best].tolist(),incident_max_um=round(float(worst[best]),6)))
    final=[]
    for (a,b),k in coefs.items():
        delta=np.array(children[a][:2])-children[b][:2]
        final.append(dict(source=a,destination=b,um=round(float(np.max(delta@SIGNS.T+k)),6)))
    conflicts=[(a,b)for(a,aa),(b,bb)in itertools.combinations(children.items(),2)if overlap(aa,bb)]
    result=dict(admitted=not conflicts and max(e['um']for e in final)<=500,
                scope='All86 actual leaf rectangles retained; fourfronts,ktree,score and displaced stations rehomed. Every internal data/reset incident bit uses actual routed LEF rectangle corners.',
                moves=moves,initial_conflicts=hits,children=children,internal_edges=final,
                worst_internal_edge=max(final,key=lambda e:e['um']),conflicts=conflicts,
                unresolved='Die input/output pin grants, stage1/score placement, clock track legality and native signoff remain separate obligations.')
    if inside_stage:
        pairs=front_connections(leafs['front'][1],leafs['tstage'][1],proposed,'MX')
        result['stage2']=dict(cell='u_t2',master='qkh_head_tstage',xy=children['u_t2'][:2],orient='MX',
                              worst=witness(pairs,children['u_t2'][:2]),
                              clock_rectangles=xf(leafs['tstage'][1]['ck'],children['u_t2'][:2],(21.6,259.2),'MX'))
        result['admitted'] &= result['stage2']['worst']['um']<=480
        result['child_orientations']={n:'MX'if n=='u_t2'else'R0'for n in children}
        result['clock_pin_rectangles_local_um']={}
        for n,box in children.items():
            k='tstage'if n=='u_t2'else kind(n)
            pin='ck'if k=='tstage'else'clk'
            result['clock_pin_rectangles_local_um'][n]=xf(leafs[k][1][pin],box[:2],box[2:],result['child_orientations'][n])
    return result


def global_stages(insts,repacked,leafs,ectl_leafs):
    """Actual A/B/C->per-head T1->T2 and score->S1->C; conservative other frames."""
    index={i['name']:i for i in insts};obstacles=[];byname={}
    def child_world(parent,box,orient='R0'):
        fx,fy=FLIPS[parent['orient']];lx,ly=FLIPS[orient]
        x=parent['x']+(parent['w']-box[0]-box[2]if fx else box[0])
        y=parent['y']+(parent['h']-box[1]-box[3]if fy else box[1])
        o=next(o for o,v in FLIPS.items()if v==(fx!=lx,fy!=ly))
        return [x,y,*box[2:]],o
    for instance in insts:
        n=instance['name'];m=instance['master']
        if m=='qkd_rhead':
            for child,box in repacked['children'].items():
                r,o=child_world(instance,box,repacked['child_orientations'][child])
                byname[n+'/'+child]=(r,o);obstacles.append((n+'/'+child,r))
        elif m=='qkd_ectl':
            for c,x in [('a',0.),('b',254.88),('c',509.76)]:
                r,o=child_world(instance,[x,0.,*ectl_leafs[c][0]])
                byname[n+'/'+c]=(r,o);obstacles.append((n+'/'+c,r))
        else:obstacles.append((n,[instance[k]for k in ('x','y','w','h')]))
    def points(n,leaf,pin):
        box,o=byname[n];return xf(leaf[1][pin],box[:2],box[2:],o)
    def solve_site(pairs_for_orient,size,margin=0.):
        best=None;blocked_best=None;counts=dict(reach_origins=0,free_origins=0);lower=[]
        for orient in FLIPS:
            pairs=pairs_for_orient(orient);k=coefficients(pairs);cap=LIMIT-margin
            lp=linprog([0,0,1],A_ub=np.column_stack((SIGNS,-np.ones(4))),b_ub=-k,
                       bounds=[(None,None),(None,None),(0,None)],method='highs')
            assert lp.success;lower.append(dict(orient=orient,um=float(lp.fun),xy=lp.x[:2].tolist()))
            # Signs order --,-+,+-,++. Intersect four exact signed half planes.
            ps=(k[0]-cap,cap-k[3]);ms=(k[1]-cap,cap-k[2])
            if ps[0]>ps[1]or ms[0]>ms[1]:continue
            xmin,xmax=(ps[0]+ms[0])/2,(ps[1]+ms[1])/2
            ymin,ymax=(ps[0]-ms[1])/2,(ps[1]-ms[0])/2
            xy=np.array([(round(ix*PITCH,6),round(iy*PITCH,6))
                         for ix in range(math.ceil(xmin/PITCH),math.floor(xmax/PITCH)+1)
                         for iy in range(math.ceil(ymin/PITCH),math.floor(ymax/PITCH)+1)]).reshape((-1,2))
            if not len(xy):continue
            distance=np.max(xy@SIGNS.T+k,axis=1);keep=distance<=cap+1e-6
            xy=xy[keep];distance=distance[keep];counts['reach_origins']+=len(xy)
            free=np.ones(len(xy),dtype=bool);penalty=np.zeros(len(xy));local_obstacles=[]
            w,h=size
            for oname,r in obstacles:
                if r[0]>xmax+w+CLEAR or r[0]+r[2]+CLEAR<xmin or r[1]>ymax+h+CLEAR or r[1]+r[3]+CLEAR<ymin:continue
                clean=((xy[:,0]+w+CLEAR<=r[0]+1e-6)|(r[0]+r[2]+CLEAR<=xy[:,0]+1e-6)|
                       (xy[:,1]+h+CLEAR<=r[1]+1e-6)|(r[1]+r[3]+CLEAR<=xy[:,1]+1e-6))
                free &= clean
                weight=r[2]*r[3]
                if '/'not in oname or oname.endswith(('/u_t2','/u_t1','/u_s1')):weight+=1e8
                penalty+=np.where(clean,0.,weight);local_obstacles.append((oname,r))
            good=np.flatnonzero(free);counts['free_origins']+=len(good)
            if len(good):
                i=good[np.argmin(distance[good])]
                if best is None or distance[i]<best['worst']['um']:
                    best=dict(xy=xy[i].tolist(),size_um=size,orient=orient,worst=witness(pairs,xy[i]))
            if len(xy):
                i=int(np.argmin(penalty+distance*.01))
                if blocked_best is None or penalty[i]<blocked_best['blocked_area_cost_um2']:
                    blocked_best=dict(xy=xy[i].tolist(),orient=orient,size_um=size,
                                      worst=witness(pairs,xy[i]),blocked_area_cost_um2=float(penalty[i]),
                                      blockers=[dict(name=n,box=r)for n,r in local_obstacles if overlap((*xy[i],w,h),r)])
        return dict(site=best,counts=counts,unobstructed_continuous_best=min(lower,key=lambda r:r['um']),
                    minimally_blocked_actual_site=blocked_best)
    results=[]
    for head in (i for i in insts if i['master']=='qkd_rhead'):
        hname=head['name'];parts=hname.split('_');h=int(parts[-1]);group='ectl_'+'_'.join(parts[1:-1]);pair=h//2
        origins=[]
        for bit in range(1559):
            if bit<512:c,p='c',f't{pair}_q[{bit+7}]'
            elif bit<518:c,p='c',f't{pair}_q[{bit-511}]'
            elif bit==518:c,p='c',f't{pair}_q[0]'
            elif bit<531:c,p='b',f't{pair}_cl[{bit-515}]'
            elif bit<1043:c,p='a',f't{pair}_row[{bit-531}]'
            elif bit<1555:c,p='b',f't{pair}_row[{bit-1043}]'
            else:c,p='b',f't{pair}_cl[{bit-1555}]'
            origins.append((f'ti_a[{bit}]',points(group+'/'+c,ectl_leafs[c],p)))
        origins +=[(f'e_a[{bit}]',points(group+'/c',ectl_leafs['c'],f'e{h}[{bit}]'))for bit in range(16)]
        targets=[(p,points(hname+'/u_t2',leafs['tstage'],p.replace('_b[','_a[')))
                 for p in leafs['tstage'][1]if p.startswith(('ti_b[','e_b['))]
        def t_pairs(o):
            return [(f'ECTL->{pin}',xf(leafs['tstage'][1][pin],size=leafs['tstage'][0],orient=o),pts)for pin,pts in origins]+[
                (f'{pin}->T2',xf(leafs['tstage'][1][pin],size=leafs['tstage'][0],orient=o),pts)for pin,pts in targets]
        t=solve_site(t_pairs,leafs['tstage'][0]);
        if t['site']:obstacles.append((hname+'/u_t1',[*t['site']['xy'],*t['site']['size_um']]))
        score_inputs=[('s_a[0]','gf_o'),('s_a[1]','sf_o')]+[(f's_a[{i+2}]',f'sc_o[{i}]')for i in range(32)]
        score_outputs=[('s_b[0]',33),('s_b[1]',32)]+[(f's_b[{i+2}]',i)for i in range(32)]
        def s_pairs(o):
            return [(f'score.{p}->S1.{s}',xf(leafs['sstage'][1][s],size=leafs['sstage'][0],orient=o),points(hname+'/score',leafs['score'],p))for s,p in score_inputs]+[
                (f'S1.{s}->C.s{h}[{i}]',xf(leafs['sstage'][1][s],size=leafs['sstage'][0],orient=o),points(group+'/c',ectl_leafs['c'],f's{h}[{i}]'))for s,i in score_outputs]
        s=solve_site(s_pairs,leafs['sstage'][0])
        if s['site']:obstacles.append((hname+'/u_s1',[*s['site']['xy'],*s['site']['size_um']]))
        results.append(dict(head=hname,ectl=group,tstage1=t,sstage1=s))
    return dict(qualified=False,scope='All128 actual87-child head repacks and all32 actualECTLA/B/C leaves; other current die instances retained as conservative solid obstacles. Full pin rectangles and source-exact field permutations, no transparent fanout copies.',
                placement_origin_pitch_um=PITCH,clearance_um=CLEAR,results=results,
                placed_tstage1=sum(bool(r['tstage1']['site'])for r in results),placed_sstage1=sum(bool(r['sstage1']['site'])for r in results),
                next='If a leaf has zero reach origins, change source/target geometry. If reach origins exist but none free, grant/rehome the connected cluster. Do not admit missing leaf placements.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--insts', type=Path, help='Actual unexpanded current die insts.json for128-copy projection')
    ap.add_argument('--global-stages',action='store_true',help='Solve actual T1/S1 in the current whole-die grant; requires --insts')
    args = ap.parse_args()
    prefix = ROOT/'physical/ref_tile'
    paths = dict(plan=ROOT/'results/arch/qwen_split_1014/head_native_r4_codex_1014/plan.json',
                 staged_rtl=ROOT/'rtl/qwen_sys/split_20261014/qkh_head_stages.sv',
                 front_rtl=ROOT/'rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv',
                 tstage=prefix/'qkh_head_tstage/views/qkh_head_tstage/qkh_head_tstage.lef',
                 sstage=prefix/'qkh_head_sstage/views/qkh_head_sstage/qkh_head_sstage.lef',
                 front=prefix/'qkh_r4_frontq_1014/views/ot_qkh_head_frontq_native/ot_qkh_head_frontq_native.lef',
                 score=prefix/'qkh_r4_score4_1014/views/ot_qkh_head_score4_native/ot_qkh_head_score4_native.lef')
    paths.update(stin=prefix/'qkh_r3_stin_1014/views/ot_qkh_head_stin_native/ot_qkh_head_stin_native.lef',
                 stk=prefix/'qkh_r3_stk_1014/views/ot_qkh_head_stk_native/ot_qkh_head_stk_native.lef',
                 nb=prefix/'qkh_r3_nb_1014/views/ot_qkh_head_nb_native/ot_qkh_head_nb_native.lef',
                 lane=prefix/'ot_qkh_lane8_m5/views/ot_qkh_lane8/ot_qkh_lane8.lef',
                 ktree=prefix/'ot_qkh_ktree_m5/views/ot_qkh_ktree/ot_qkh_ktree.lef')
    plan = json.loads(paths['plan'].read_text()); tstage=lef(paths['tstage']); front=lef(paths['front'])
    assert tstage[0] == (21.6,259.2)
    assert lef(paths['sstage'])[0] == (21.6,21.6)
    assert front[0] == (129.6,43.2)
    w,h=plan['slot_outline_um']
    # Candidate A: add the actual mandatory leaf inside the old parent with all86 children standing.
    # Candidate B: use a new one-stage-deep halo, requiring real die area grants before adoption.
    alternatives = dict(inside_head=solve(plan,tstage,front,(0,w,0,h),'inside_head'),
                        adjacent_channel=solve(plan,tstage,front,(-129.6,w+129.6,-280.8,h+280.8),'adjacent_channel'))
    alternatives['inside_head']['continuous_lower_bound_ignoring_all_obstacles']=continuous_bound(
        plan,tstage,front,dict(inside=(0,w-21.6,0,h-259.2)))
    alternatives['adjacent_channel']['continuous_lower_bound_ignoring_die_obstacles']=continuous_bound(
        plan,tstage,front,dict(below=(-129.6,w+108,-280.8,-264.6),
                              above=(-129.6,w+108,h+5.4,h+21.6),
                              left=(-129.6,-27,-280.8,h+21.6),
                              right=(w+5.4,w+108,-280.8,h+21.6)))
    # A concrete structural fallback: two rows of quarters. It deliberately
    # reports every existing-child collision rather than silently deleting them.
    repack=json.loads(json.dumps(plan))
    for q in range(4):repack['children'][f'front{q}']=[324+135*(q%2),5.4+48.6*(q//2),129.6,43.2]
    pairs=list(itertools.combinations(repack['children'].items(),2))
    repack_conflicts=[(a,b) for (a,aa),(b,bb) in pairs if overlap(aa,bb)]
    repack_lb=continuous_bound(repack,tstage,front,dict(below=(-129.6,w+108,-280.8,-264.6)))
    repacked=repack_fronts(plan,{k:lef(paths[k])for k in ('front','score','stin','stk','nb','lane','ktree')})
    repacked_inside=repack_fronts(plan,{k:lef(paths[k])for k in ('front','score','stin','stk','nb','lane','ktree','tstage')},True)
    if 'children'in repacked:
        repacked['stage2_continuous_lower_bound']=continuous_bound(
            dict(plan,children=repacked['children']),tstage,front,dict(below=(-129.6,w+108,-280.8,-264.6)))
    record = dict(schema='qwen.head_staged_actual_pin_candidates.v1', qualified=False,
                  physical_class='Necessary actual-pin and rectangle feasibility; no new route/timing qualification',
                  source_sha256={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},
                  sources={k:str(p.relative_to(ROOT)) for k,p in paths.items()},
                  rtl_master='ot_qkh_head_native_r4_staged',
                  source_exact_stages_per_head=dict(tstage=2,sstage=1),
                  source_edges=dict(issue=2,score_return=1,per_layer=3),
                  clock_entries=dict(existing=86,added=3,total=89),
                  clock_contract='Each added leaf ck must receive its own compensated1.2GHz entry using its actual insertion.json. No parent/shared stage clock root is inferred.',
                  cuts=dict(input_bits_per_head=1575,score_bits_per_head=34,
                            added_registered_bits_per_head=3184,
                            stage_W_face_track_fraction=round(1576*.096/259.2,6)),
                  alternatives=alternatives,
                  repacked_actual_leaf_plan=repacked,
                  repacked_inside_stage2_actual_leaf_plan=repacked_inside,
                  structural_fallback=dict(front_quarters_2x2={f'front{q}':repack['children'][f'front{q}'] for q in range(4)},
                                           actual_pin_lower_bound=repack_lb,
                                           existing_child_conflicts=repack_conflicts,
                                           admitted=False,
                                           reason='Actual matched-bit distance can improve, but these connected children must really be rehomed and their actual-bit internal hops reverified. No area grant, stage1/score closure or clock legality has been established.'),
                  stage1_contract='One tstage PER HEAD beside ECTL C, not one shared fanout launch. Its1575 input bits actually originate from A(row lower512), B(row upper512 plus c/lt), C(q519 and e16); all three source views must be audited.',
                  return_contract='Staged s_a={sc_d32,sc_f,g_f}; ECTL s={g_f,sc_f,sc_d32}. Wire permutation required; identity bus wiring is incorrect.',
                  qualification_limits=['R0/MX/MY/R180 physical pin track legality still requires real die pin grid replay.',
                                        'Inherited r4 plan contains proposed pins/region bounds for some old leaves; this result only audits added-stage to actual routed front pins.',
                                        'No stage1/score site or128-head die grant is admitted unless the mandatory stage2 domain passes.'])
    if args.insts:
        insts=json.loads(args.insts.read_text());heads=[i for i in insts if i['master']=='qkd_rhead']
        assert len(heads)==128
        record['die_projection']=dict(input=str(args.insts),sha256=hashlib.sha256(args.insts.read_bytes()).hexdigest(),
                                      head_count=len(heads),orientations={o:sum(i['orient']==o for i in heads) for o in FLIPS},
                                      required_added_leaves=384,required_added_clock_entries=384,
                                      total_added_leaf_area_um2=128*(2*21.6*259.2+21.6**2),
                                      admitted=False,reason='Mandatory canonical stage2 geometry is necessary for every mirrored copy; no full cluster grant invented.')
        if repacked_inside.get('admitted'):
            projected=[]
            for head in heads:
                local=repacked_inside['children']['u_t2'];fx,fy=FLIPS[head['orient']]
                x=head['x']+(head['w']-local[0]-local[2] if fx else local[0])
                y=head['y']+(head['h']-local[1]-local[3] if fy else local[1])
                orient=next(o for o,v in FLIPS.items()if v==(fx,not fy))
                clock=xf(tstage[1]['ck'],(x,y),tstage[0],orient)
                projected.append(dict(name=head['name']+'/u_t2',master='qkh_head_tstage',
                                      xy=[x,y],size_um=tstage[0],orient=orient,clock_pin_corners_um=clock,
                                      clock_insertion_source='physical/ref_tile/qkh_head_tstage/views/qkh_head_tstage/insertion.json'))
            record['die_projection']['stage2_inside_existing_head_count']=len(projected)
            record['die_projection']['reason']='Repacked stage2 fits all128 unchanged head parent rectangles. Per-head firststage/score sites, endpoint reach and physical clock/pin grid admission remain open.'
            record['die_projection']['stage2_placements_file']='stage2_die_placements.json'
        else:projected=[]
    else:projected=[]
    # Cross-check the fast signed-plane arithmetic against direct bit-corner
    # enumeration; neither centres nor whole-bus region shortcuts qualify.
    arithmetic=[]
    for orient in FLIPS:
        pairs=front_connections(front[1],tstage[1],plan,orient)
        for xy in ((0.,0.),(459.,0.),(464.4,-264.6)):
            fast=float(np.max(np.array(xy)@SIGNS.T+coefficients(pairs)))
            direct=witness(pairs,xy)['um']
            assert abs(fast-direct)<1e-6
            arithmetic.append(dict(orient=orient,xy=xy,fast_um=round(fast,6),direct_um=direct))
    record['validation']=dict(signed_plane_vs_direct_all_matched_bit_rectangles=arithmetic,
                              source_stage_rtl_binding={})
    for name in ('tstage','sstage'):
        binding=prefix/f'qkh_head_{name}/gate_result.json'
        gate=json.loads(binding.read_text())
        source=next(f for f in gate['source_binding']['files'] if f['path']==str(paths['staged_rtl'].relative_to(ROOT)))
        assert source['sha256']==record['source_sha256']['staged_rtl']
        record['validation']['source_stage_rtl_binding'][name]=dict(
            matches_current=True,sha256=source['sha256'],gate_manifest_sha256=gate['source_binding']['manifest_sha256'])
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'plan.json').write_text(json.dumps(record,indent=2)+'\n')
    if projected:(args.out/'stage2_die_placements.json').write_text(json.dumps(projected,indent=2)+'\n')
    if args.global_stages:
        assert args.insts and repacked_inside['admitted']
        ectl_paths={c:prefix/f'qkd_ectl_{c}_tp8_direct/views/qkd_ectl_{c}_tp8_direct/qkd_ectl_{c}_tp8_direct.lef'for c in 'abc'}
        ectl_paths['a']=prefix/'qkd_ectl_a_tp8_direct/views/qkd_ectl_a_tp8_epoch_direct/qkd_ectl_a_tp8_epoch_direct.lef'
        ectl_leafs={c:lef(p)for c,p in ectl_paths.items()}
        global_result=global_stages(insts,repacked_inside,{k:lef(paths[k])for k in ('tstage','sstage','score')},ectl_leafs)
        global_result['source_sha256']={c:hashlib.sha256(p.read_bytes()).hexdigest()for c,p in ectl_paths.items()}
        (args.out/'global_stages.json').write_text(json.dumps(global_result,indent=2)+'\n')
        print(json.dumps({k:global_result[k]for k in ('placed_tstage1','placed_sstage1')}))
    print(json.dumps({k:{x:v[x] for x in ('origins','free_origins','reach_pass_origins','admitted','best_free','best_reach_only')} for k,v in alternatives.items()},indent=2))


if __name__ == '__main__': main()
