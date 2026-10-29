#!/usr/bin/env python3
"""Attach actual emitted START stage geometry to the landing infrastructure graph.

The optional provider contract uses complete emitted flop row rectangles. Reach
is checked conservatively between every endpoint corner, not an invented point
inside an unplaced flop. This does not claim routed timing or clock-load closure.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import schema as S


def corners(rect):
    if len(rect) != 4 or not all(math.isfinite(float(x)) for x in rect) or rect[2] < rect[0] or rect[3] < rect[1]:
        raise ValueError('invalid physical provider rectangle')
    return [(rect[x], rect[y]) for x in (0, 2) for y in (1, 3)]


def hop(a, b):
    return max(sum(abs(x-y) for x,y in zip(p,q)) for p in corners(a) for q in corners(b))


def pin_rect(P, part, name):
    p = next(q for q in P.ptype(part)['clock']['landing_contract']['pins'] if q['name'] == name)
    xy = P.to_die(part, p['xy_um'])
    return list(xy) + list(xy)


def materialize(raw, stages):
    out = copy.deepcopy(raw)
    st = out['clock']['landing_network']['start_tree']
    if 'provider' in st:
        raise ValueError('START provider already materialized; regenerate from the clean plan')
    if stages.get('schema') != 'ot_start_stages/1':
        raise ValueError('unknown START provider manifest')
    P = S.Plan(out)
    by = {s['region']: s for s in stages['stages']}
    ids = {s['id']: s for s in stages['stages']}
    if len(by) != len(stages['stages']) or len(ids) != len(by):
        raise ValueError('duplicate START provider stage')
    nodes = [dict(id=s['id'], region=s['region'], rect_um=s['rect_um'], clock_node=s['node_cell'],
                  clock_node_xy_um=s['node_xy_um'], clock_port=s['clock_port'], module=s['module'],
                  flops=s['flops'], parent=s['parent'], root=s['root']) for s in stages['stages']]
    edges = []
    for s in stages['stages']:
        if s['parent'] in by:
            p=by[s['parent']]
            edges.append(dict(src_stage=p['id'],dst_stage=s['id'],src_rect_um=p['rect_um'],dst_rect_um=s['rect_um']))
    for side in ('die_inputs','die_outputs'):
        for e in stages[side]:
            node=ids[e['stage']]
            part=e['src_part'] if side=='die_inputs' else e['dst_part']
            pin='cland_tstart_out' if side=='die_inputs' else 'cland_tstart_in'
            r=pin_rect(P,part,pin)
            edges.append(dict(net=e['net'],part=part,pin=pin,
                **(dict(dst_stage=node['id'],src_rect_um=r,dst_rect_um=node['rect_um']) if side=='die_inputs' else
                   dict(src_stage=node['id'],src_rect_um=node['rect_um'],dst_rect_um=r))))
    for e in edges:
        e.update(max_hop_um=405,source_registered=True,capture_registered=True)
    st['provider']=dict(form='emitted_start_stage_rows',nodes=nodes,edges=edges,
                        physical_qualified=False,rtl_module='ot_die_start_stages')
    return out


def check(P, contract):
    errors=[]
    nodes=contract.get('nodes',[]);edges=contract.get('edges',[])
    by={n['id']:n for n in nodes};regions={n['region']:n for n in nodes}
    if contract.get('form')!='emitted_start_stage_rows' or len(by)!=len(nodes) or len(regions)!=len(nodes):
        errors.append('invalid/duplicate emitted START provider nodes')
    clock_access=0
    roots=[n for n in nodes if n.get('root')]
    if len(roots)>1 or not nodes:errors.append('START provider requires a nonempty tree with at most one virtual root')
    for n in nodes:
        try:
            corners(n['rect_um'])
            xy=n['clock_node_xy_um']
            clock_access=max(clock_access,hop(list(xy)+list(xy),n['rect_um']))
            if n['flops']<=0 or not n.get('clock_node') or not n.get('clock_port'):raise ValueError('stage lacks flops or clock access')
            if n['parent'] is not None and n['parent'] not in regions:
                # Real-region launch parents are represented by rs_ boundary edges below.
                if not any(e.get('dst_stage')==n['id'] and e.get('pin')=='cland_tstart_out' for e in edges):
                    raise ValueError('stage parent is not materialized')
        except (KeyError,ValueError,TypeError) as ex:errors.append(f"stage {n.get('id')}: {ex}")
    boundary=set();incoming={n:0 for n in by};maximum=0;adj={n:[] for n in by};seeds={n['id'] for n in roots}
    for e in edges:
        try:
            a,b=e['src_rect_um'],e['dst_rect_um']
            for end,r in [('src_stage',a),('dst_stage',b)]:
                if end in e and (e[end] not in by or r!=by[e[end]]['rect_um']):raise ValueError('stage endpoint rectangle mismatch')
            if 'src_stage' in e and 'dst_stage' in e:
                if by[e['dst_stage']]['parent']!=by[e['src_stage']]['region']:raise ValueError('START provider parent edge mismatch')
                adj[e['src_stage']].append(e['dst_stage'])
            if 'part' in e:
                if e['pin'] not in ('cland_tstart_in','cland_tstart_out'):raise ValueError('invalid START boundary pin')
                r=pin_rect(P,e['part'],e['pin'])
                if r!=(b if e['pin']=='cland_tstart_in' else a):raise ValueError('boundary pin geometry mismatch')
                boundary.add((e['part'],e['pin'],e['net']))
                if e['pin']=='cland_tstart_out':seeds.add(e['dst_stage'])
            if not(e.get('source_registered') and e.get('capture_registered')):raise ValueError('unregistered START edge')
            if e.get('max_hop_um')!=405:raise ValueError('START reach contract must retain405um')
            h=hop(a,b);maximum=max(maximum,h)
            if h>405+1e-6:raise ValueError(f'physical START row envelope hop {h:.3f}um exceeds405')
            if 'dst_stage' in e:incoming[e['dst_stage']]+=1
        except (KeyError,ValueError,TypeError,StopIteration) as ex:errors.append(str(ex))
    for n,c in incoming.items():
        if c!=(0 if by[n].get('root') else 1):errors.append(f'START stage {n} incoming edges {c}')
    seen=set();todo=list(seeds)
    while todo:
        n=todo.pop()
        if n not in seen:seen.add(n);todo.extend(adj[n])
    if seen!=set(by):errors.append('START provider has unreachable physical stages')
    declared={(u['part'],u['pin'],u['net']) for u in P.clock['landing_network']['start_tree'].get('uses',[])}
    if boundary!=declared:errors.append('physical START provider boundary differs from declared START uses')
    return dict(errors=errors,stages=len(nodes),edges=len(edges),max_hop_um=maximum,max_clock_access_um=clock_access,physical_qualified=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan');ap.add_argument('stages');ap.add_argument('--out',required=True)
    a=ap.parse_args();raw=materialize(json.load(open(a.plan)),json.load(open(a.stages)));result=check(S.Plan(raw),raw['clock']['landing_network']['start_tree']['provider'])
    Path(a.out).write_text(json.dumps(raw));Path(a.out).with_suffix('.provider.json').write_text(json.dumps(result,indent=1));print(json.dumps(result))
    return bool(result['errors'])


if __name__=='__main__':raise SystemExit(main())
