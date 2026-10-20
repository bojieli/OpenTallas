#!/usr/bin/env python3
"""Conservative region assignment on the native mapped connectivity census.

No cell behavioral model is used. Clock-role and transparent-cell authority is
the pinned native audit. A passing plan is not placed-wire qualification.
"""
import argparse
import collections
from functools import lru_cache
import itertools
import json
from pathlib import Path
import re
import sys

sys.setrecursionlimit(20000)


def norm(s):
    return s.replace('\\','').strip()


def cell(pin):
    return norm(pin) if pin.startswith('PORT/') else norm(pin).rsplit('/',1)[0]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('model');ap.add_argument('rows');ap.add_argument('out')
    a=ap.parse_args();model=json.loads(Path(a.model).read_text());rows=json.loads(Path(a.rows).read_text())
    pin_plan=json.loads(Path(a.model).with_name('pin_plan.json').read_text())['pins']
    cx,cy=189.648,208.17;cols=[43.2,129.6,216,302.4]
    zones=dict(BULK=model['bulk_region_rectangles'],HEADER=[[cx-13.52,254,cx+13.52,374.8]],
       NCAP=[[cx-13.52,254,cx+13.52,374.8]],RESET=[[cx-10,cy-10,cx+10,cy+10]],
       SCAP=[[cx-11.52,2.16,cx+11.52,12.42]],WCAP=[[2.16,cy-10,12.42,cy+10]],
       ECAP=[[376.38,cy-10,386.64,cy+10]],NFACE=[[177.9,377,201.4,386.64]])
    # The central reset island is a separate exclusive group; remove it from
    # every overlapping bulk rectangle. The remaining union stays connected.
    reset=zones['RESET'][0];bulk=[]
    for x0,y0,x1,y1 in zones['BULK']:
        bulk.extend([[x0,y0,reset[0],y1],[reset[2],y0,x1,y1],
                     [reset[0],y0,reset[2],reset[1]],[reset[0],reset[3],reset[2],y1]])
    zones['BULK']=[r for r in bulk if r[0]<r[2] and r[1]<r[3]]
    for i,x in enumerate(cols):
        zones[f'N{i}']=[[x-14.472,378.54,x+48.168,386.64]]
        zones[f'S{i}']=[[x-14.472,2.16,x+48.168,12.42]]
    macros={norm(m['inst']):m for m in model['macros']}
    masters={cell(r['driver']):r['master'] for r in rows}
    authority=json.loads(Path(a.rows).with_name('summary.json').read_text())['master_roles']
    unary=lambda n: authority.get(masters[n],{}).get('unary',False)
    outputs=collections.defaultdict(list);fanin=collections.defaultdict(set)
    for r in rows:
        src=cell(r['driver']);outputs[src].append(r)
        for p in r['endpoints']:
            if p.startswith('PORT/'):continue
            dst=cell(p)
            if dst!=src:fanin[dst].add(src)
    # The native audit expands transparent chains to their terminal sinks. Recover
    # their physical source role using those same terminals and the Liberty
    # pin-role unary classification; no behavioral model is imported.
    terminal_sources=collections.defaultdict(set)
    for r in rows:
        src=cell(r['driver'])
        if not unary(src):
            for p in r['endpoints']:terminal_sources[norm(p)].add(src)
    for r in rows:
        src=cell(r['driver'])
        if unary(src):
            candidates=[terminal_sources[norm(p)] for p in r['endpoints']]
            common=set.intersection(*candidates) if candidates else set()
            if len(common)==1:fanin[src].update(common)
    def port_zone(p):
        if p[5:] in model.get('port_pin_rects',{}):return model['port_pin_rects'][p[5:]]
        x,y=pin_plan[p[5:]]['at']
        return [[x,y,x,y]]
    def sequential(n):
        m=masters.get(n,'');return ('DFF' in m or 'LATCH' in m or n in macros or n.startswith('PORT/'))
    fixed={}
    for n,m in masters.items():
        clean=norm(n);ix=list(map(int,re.findall(r'\[(\d+)\]',clean)))
        role='BULK'
        if n.startswith('PORT/'):role=n
        elif n in macros:role='MACRO:'+n
        elif m.startswith('TIE') or 'g_rst_forest.u_rst.' in clean or 'g_rst_forest_u_rst_' in clean:role='RESET'
        elif any(t in clean for t in ('sticky','fault_regions_q','pc_fault_regions')) and 'DFF' in m:role='RESET'
        elif 'g_reset_face.rst_l' in clean:role='WCAP'
        elif clean.startswith('u_native.g_kreg.kp_data['):role='N'+str(ix[0]//64)
        elif '.u_kring.mem[' in clean:
            bit=ix[-1];role='N'+str(bit//64) if bit<256 else 'HEADER'
        elif '.u_skid.g_slice[' in clean and ('.h[' in clean or '.t[' in clean):
            bit=ix[0]*8+ix[1];role='N'+str(bit//64) if bit<256 else 'NCAP'
        elif clean.startswith('u_native.g_kreg.'):
            role='NCAP' if any(t in clean for t in ('kp_we','kp_addr','kp_len','kp_tag','kp_strb','kv_regions','k_rdy_q')) else 'HEADER'
        elif clean.startswith('u_native.g_krreg.') or clean.startswith('kr_v$'):role='HEADER'
        elif clean.startswith('u_native.g_phy_return.data['):role='S'+str(ix[0]//64)
        elif clean.startswith('col_data['):role='S'+str(ix[0]//64)
        elif clean.startswith(('row_','col_')) or clean.startswith('u_native.g_phy_return.v$'):role='SCAP'
        elif clean.startswith(('pc_fault_q$','u_native.pc_id_q[','u_native.refresh_reload_q[')):role='ECAP'
        elif clean.startswith('owner_fault_split['):role='WCAP'
        fixed[n]=role
    fixed.update(model.get('fixed_cell_roles',{}))
    def macro_data_role(n):
        m=macros[n];ix=list(map(int,re.findall(r'\[(\d+)\]',n)))
        if m['role']=='response_payload':return 'N'+str(ix[0])
        if m['role']=='write_payload':return 'S'+str(ix[0])
        return None
    @lru_cache(None)
    def data_roots(n):
        if sequential(n):
            r=macro_data_role(n) if n in macros else fixed.get(n,'BULK')
            if n.startswith(('PORT/k_wdata[','PORT/dram_rdata[')):
                r=('N' if '/k_wdata[' in n else 'S')+str(int(re.search(r'\[(\d+)\]',n)[1])//64)
            return frozenset([r]) if r and re.fullmatch('[NS][0-3]',r) else frozenset()
        return frozenset().union(*(data_roots(i) for i in fanin[n]))
    header_needed=set()
    def walk(n,seen):
        if n in seen or sequential(n):return
        seen.add(n);header_needed.add(n)
        for p in fanin[n]:walk(p,seen)
    for n in masters:
        if not sequential(n) and data_roots(n):walk(n,set())
        if sequential(n) and fixed[n] in ('HEADER','NCAP'):
            for p in fanin[n]:walk(p,set())
    assigned={};mixed=[]
    for n,m in masters.items():
        if n in model.get('fixed_cell_roles',{}):assigned[n]=fixed[n];continue
        if sequential(n) or m.startswith('TIE'):assigned[n]=fixed[n];continue
        ds=data_roots(n)
        if len(ds)==1:assigned[n]=next(iter(ds))
        elif len(ds)>1:assigned[n]='HEADER';mixed.append(dict(cell=n,roots=sorted(ds)))
        elif n in header_needed:assigned[n]='HEADER'
        else:assigned[n]='BULK'
    macro_pins=model['local_signal_clock_pin_rects']
    def rects(pin):
        n=cell(pin)
        if n.startswith('PORT/'):return port_zone(n)
        role=assigned.get(n,'BULK')
        if role.startswith('MACRO:'):
            inst=macros[n];pn=norm(pin).rsplit('/',1)[1];x,y=inst['at']
            return [[x+b[0],y+b[1],x+b[2],y+b[3]] for b in macro_pins.get(pn,[[0,0,33.696,27.54]])]
        return zones[role]
    def maxdist(aa,bb):
        return max(abs(x-u)+abs(y-v) for p in aa for q in bb
          for x,y in itertools.product((p[0],p[2]),(p[1],p[3]))
          for u,v in itertools.product((q[0],q[2]),(q[1],q[3])))
    bad=[];maximum=0
    for r in rows:
        if not r['terminals']:continue
        src=r['driver'];sa=rects(src)
        for dst in r['endpoints']:
            d=maxdist(sa,rects(dst));maximum=max(maximum,d)
            if d>405+1e-6:bad.append(dict(driver=norm(src),sink=norm(dst),upper_um=d,
                               source_role=assigned.get(cell(src)),sink_role=assigned.get(cell(dst))))
    out=Path(a.out);out.mkdir(exist_ok=True)
    (out/'role_regions.json').write_text(json.dumps(zones,indent=2)+'\n')
    (out/'cell_roles.json').write_text(json.dumps(assigned,indent=2)+'\n')
    (out/'unbounded_pairs.json').write_text(json.dumps(bad,indent=2)+'\n')
    rec=dict(schema='opentallas.hbm-mc3-native-connectivity-region-plan.v1',
       scope='Planning bounds on native driver/terminal connectivity, not placed qualification; generated hold/CTS cells must be checked after insertion',
       cells=len(assigned),roles=dict(collections.Counter(assigned.values())),mixed_data_cones=mixed,
       max_planned_L1_pin_bbox_um=maximum,over405=len(bad),verdict='PASS' if not bad else 'OPEN')
    (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    brief={k:v for k,v in rec.items() if k not in ('mixed_data_cones','roles')}
    brief['roles']=dict(collections.Counter('PORT' if r.startswith('PORT/') else r for r in assigned.values()))
    print(json.dumps(brief))


if __name__=='__main__':main()
