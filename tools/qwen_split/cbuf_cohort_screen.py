#!/usr/bin/env python3
"""Finite, source-bound CROM/R3/D3 pin screen; never a route or grant.

Run from the repository root. Reads immutable Git blobs, writes only this
screen's result directory. Every external unknown remains in the receipt.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

BASE = 'dbad6aa247b697b26f42141e596cfef05c82e2a0'
NATIVE = '5b7116662d2d519e300b6fcccdfa2c6902f26377'
OUT = Path('results/arch/qwen_split_compute_1014/native_cbuf_cohort_1103')
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
GX, RIGHT, END, TOP = 19226.592, 19662.912, 19744.968, 17832.96
DW, DH, PITCH = 64.8, 129.6, .096
DX = RIGHT + 8.64
inputs = []


def locked():
    assert json.loads(LOCK.read_text())['owner'].lower() == 'codex', 'Coordinator is not Codex'


def blob(path, rev=BASE):
    data = subprocess.check_output(['git', 'show', f'{rev}:{path}'])
    inputs.append(dict(path=path, commit=rev, sha256=hashlib.sha256(data).hexdigest()))
    return data.decode()


def lef(kit, cell):
    text = blob(f'physical/ref_tile/{kit}/views/{cell}/{cell}.lef')
    w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', text).groups())
    pins, pg = {}, []
    for m in re.finditer(r'  PIN (\S+)\n([\s\S]*?)  END \1\n', text):
        layer = None
        for line in m[2].splitlines():
            if 'LAYER ' in line:
                layer = line.strip().split()[1]
            if 'RECT ' in line:
                q = list(map(float, re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', line).groups()))
                item = dict(pin=m[1], layer=layer, rect=q)
                if m[1] in ('VDD', 'VSS'):
                    pg.append(item)
                else:
                    assert m[1] not in pins
                    pins[m[1]] = item
    return dict(w=w, h=h, pins=pins, pg=pg, symmetry=re.findall(r'SYMMETRY ([^;]+)', text),
                obs_top='M5', pg_top='M5')


def center(pin):
    a, b, c, d = pin['rect']
    return ((a+c)/2, (b+d)/2)


def point(master, name, x, y, orient='MX'):
    a, b = center(master['pins'][name])
    return (x+a, y+(master['h']-b if orient == 'MX' else b))


def md(a, b):
    return round(abs(a[0]-b[0])+abs(a[1]-b[1]), 6)


def rpin(i):
    return 'fault' if i == 512 else f'crom_q[{i}]'


def bpin(i):
    return 'f_fault' if i == 512 else f'f_q[{i}]'


def order(master, port):
    # Both cohorts lie left of D3. Smaller endpoint x => longer horizontal leg.
    return sorted(range(513), key=lambda i: (center(master['pins'][port(i)])[0], i))


def pinmap(a_order, b_order, slot_order, base=3.372):
    # One explicit rectangle per physical logical bit; no logical permutation.
    result = []
    for port, ordered, x in [('a', a_order, 0), ('b', b_order, DW-.084)]:
        for bit, slot in zip(ordered, slot_order):
            y = base + slot*PITCH  # 12nm mod48; two-track spacing
            result.append(dict(pin=f'{port}[{bit}]', bit=bit, face='W' if port=='a' else 'E',
                               layer='M4', rect=[round(x,3),round(y-.012,3),round(x+.084,3),round(y+.012,3)]))
    result += [dict(pin='ck', face='N', layer='M5', rect=[3.360,129.516,3.384,129.6]),
               dict(pin='rst_n', face='N', layer='M5', rect=[3.600,129.516,3.624,129.6])]
    return dict(module='qfd_crom_return3', params={'MUT':0}, outline=[DW,DH], orient='R0', pins=result,
                status='CANDIDATE_NOT_GRANTED_NOT_ROUTED',
                pg='OPEN: no actual D3 PG/OBS view exists; M5 PG and M6 hookup must be built and qualified')


def tracks(lo, hi, pitch, offset):
    return [offset+i*pitch for i in range(math.ceil((lo-offset)/pitch), math.floor((hi-offset)/pitch)+1)]


def cutoff(lo, hi, axis):
    # Conservative track-center exclusion includes PG halfwidth + one pitch
    # for via/spacing. No fictional empty routing plane is credited as free.
    specs = [('M7',.064,.016,.16,8.64,2.16),('M9',.080,.116,.48,9.091,0)] if axis=='V' else [('M6',.064,.016,.16,8.64,2.16),('M8',.080,.116,.48,8.64,0)]
    result={}
    for layer,pitch,off,width,pgpitch,pgoff in specs:
        raw=tracks(lo,hi,pitch,off)
        def clear(v):
            # OpenROAD alternating VSS/VDD stripe centers, half pitch apart.
            phase=(v-pgoff)%(pgpitch/2)
            return min(phase,pgpitch/2-phase)>width/2+pitch
        result[layer]=dict(raw=len(raw),after_known_pg_spacing_bound=sum(clear(v) for v in raw),
                           credited_free=0,unknown='Other nets, actual new macro adapter and via enclosures')
    return result


def write(name, data):
    locked()
    (OUT/name).write_text(json.dumps(data, indent=2)+'\n')


def crossing_peak(legs,axis=1):
    # Every return incident leg must connect its two endpoint y coordinates.
    # This is a cut demand, independent of assumed Manhattan bend location.
    events=[]
    for q in legs:
        if q['group'] not in (0,1):continue  # each row repeats the same topology
        for a,b in [('rom','d3_a'),('d3_b','cbuf')]:
            lo,hi=sorted((q[a][axis],q[b][axis]))
            events.extend([(lo,1),(hi,-1)])
    live=peak=0;where=None
    for y,delta in sorted(events,key=lambda p:(p[0],p[1])):
        live+=delta
        if live>peak:peak,where=live,y
    return dict(peak_nets=peak, coordinate_um=where, axis='y' if axis else 'x',two_track_demand=2*peak,
                scope='Two groups in row0; endpoint-interval cut; not a routing allocation')


def main():
    locked()
    OUT.mkdir(parents=True, exist_ok=True)
    rom = lef('qfd_crom_g_tp8', 'ot_qfd_crom_gr')
    buf = lef('qfd_su_cbuf_native_l0_p13_l12_r3', 'qfd_su_cbuf_native_l0_p13_l12_r3')
    source = blob('rtl/qwen_split/qfd_native_crom8_r3_tp8.sv', NATIVE)
    assert 'module qfd_crom_return3' in source and 'p0<=a;p1<=p0;p2<=p1' in source
    blob('tools/qwen_split/pdn_regroup.py')
    pdn=(OUT/'c19s_r7_pdn.tcl').read_bytes()
    assert hashlib.sha256(pdn).hexdigest()=='97d0521226c4d4ff40eb7c339f93701ab7b8398bbb33470e19719ef325667bb1'
    inputs.append(dict(path=str(OUT/'c19s_r7_pdn.tcl'),sha256=hashlib.sha256(pdn).hexdigest(),
                       source='ot-epyc4 c19s/chain/case_r22k/pdn.tcl SOURCE634b6419b; old-profile diagnostic'))
    ao, bo = order(rom, rpin), order(buf, bpin)
    slots = list(range(513))
    # Same one-master pinmap can be instantiated above and below seam without
    # illegal MX on horizontal M4 pins: longest legs get central slots.
    folded = sorted(slots, key=lambda n: (abs(n-256), n))
    maps = {'shared_folded':pinmap(ao,bo,folded,40.236),
            'above_endpoint':pinmap(ao,bo,slots),
            'below_endpoint':pinmap(ao,bo,list(reversed(slots)),77.100),
            'natural':pinmap(slots,slots,slots)}
    for key, value in maps.items():
        value['proposed_view_identity']='qfd_crom_return3_'+key
        value['source_alias_status']='OPEN: native owner must implement distinct real module/view identities before two variants coexist'
        value['source']={'commit':NATIVE,'path':'rtl/qwen_split/qfd_native_crom8_r3_tp8.sv','module':'qfd_crom_return3'}
        for q in value['pins']:
            xy=center(q)
            axis=xy[1] if q['layer']=='M4' else xy[0]
            assert round(axis*1000)%48==12
        assert len({q['pin'] for q in value['pins']})==1028
        write(f'd3_pins_{key}.json', value)
    arrangements = []
    for scheme in ('single_master_folded', 'two_pin_variants'):
        instances, legs, reqs, incident = [], [], [], []
        for row in range(4):
            ry = 17282.16-row*775.44
            by = 17061.84-row*775.44
            seam = (ry+by+216)/2
            for col in range(2):
                g = row*2+col
                x = GX+col*220.32
                above = col == 0
                # Both origins on 2.16um row lattice; 8.64um D3-to-D3 gap.
                dy = ry+2.16 if above else by+216-2.16-DH
                key = 'shared_folded' if scheme=='single_master_folded' else ('above_endpoint' if above else 'below_endpoint')
                p = {q['pin']:q for q in maps[key]['pins']}
                instances += [dict(n=f'crom_{g}',kind='CROM',x=x,y=ry,w=194.4,h=550.8,orient='MX'),
                              dict(n=f'cbuf_{g}',kind='CBUF',x=x,y=by,w=216,h=216,orient='MX'),
                              dict(n=f'return_{g}',kind=key,x=DX,y=dy,w=DW,h=DH,orient='R0')]
                for i in range(513):
                    a = point(rom,rpin(i),x,ry)
                    b = point(buf,bpin(i),x,by)
                    q = center(p[f'a[{i}]']); u = (DX+q[0],dy+q[1])
                    q = center(p[f'b[{i}]']); v = (DX+q[0],dy+q[1])
                    legs.append(dict(group=g, bit=i, rom_pin=rpin(i), cbuf_pin=bpin(i),
                                     rom=a, d3_a=u, d3_b=v, cbuf=b,
                                     rom_to_d3_um=md(a,u), d3_to_cbuf_um=md(v,b),
                                     sum_um=round(md(a,u)+md(v,b),6),
                                     timing='OPEN: actual D3 launch/capture native costs unavailable'))
                for bp,rp,n in [('f_addr','crom_addr',192),('f_re','crom_re',8),('f_stage','crom_stage',6)]:
                    for i in range(n):
                        a,b=point(buf,f'{bp}[{i}]',x,by),point(rom,f'{rp}[{i}]',x,ry)
                        reqs.append(dict(group=g,bit=i,cbuf_pin=f'{bp}[{i}]',rom_pin=f'{rp}[{i}]',
                                         source=a,target=b,manhattan_um=md(a,b)))
                for kind,master,xx,yy in [('CROM',rom,x,ry),('CBUF',buf,x,by)]:
                    for name in master['pins']:
                        if name in ('clk','rst_n') or (kind=='CBUF' and not name.startswith(('f_addr[','f_re[','f_stage[','f_q[')) and name!='f_fault') or (kind=='CROM' and name.startswith(('crom_lb[','fault_code['))):
                            incident.append(dict(group=g,master=kind,pin=name,xy=point(master,name,xx,yy),
                                                 status='OPEN_PEER_HOME' if name not in ('grp','f_lat_total') else 'OPEN_TIE_SOURCE'))
                for name in ('ck','rst_n'):
                    q=center(p[name]);incident.append(dict(group=g,master='D3',pin=name,xy=[DX+q[0],dy+q[1]],status='OPEN_ROOT_OR_RESET_HOME'))
                for master,xx,yy in [(rom,x,ry),(buf,x,by)]:
                    for pin in master['pins']:
                        xp,yp=point(master,pin,xx,yy)
                        assert round(xp*1000)%48==12, (g,pin,xp)
                for pin in p.values():
                    xp,yp=center(pin)
                    assert round((dy+yp if pin['layer']=='M4' else DX+xp)*1000)%48==12
        overlaps=[]
        for i,a in enumerate(instances):
            for b in instances[i+1:]:
                if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+1e-8 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+1e-8:
                    overlaps.append([a['n'],b['n']])
        assert not overlaps
        assert all(GX<=i['x'] and i['x']+i['w']<=END+1e-8 and 14713.92<=i['y'] and i['y']+i['h']<=TOP+1e-8 for i in instances)
        summary=dict(name=scheme, physical_return_pin_variants=1 if scheme=='single_master_folded' else 2,
                     worst_rom_to_d3=max(q['rom_to_d3_um'] for q in legs),
                     worst_d3_to_cbuf=max(q['d3_to_cbuf_um'] for q in legs),
                     worst_sum=max(q['sum_um'] for q in legs),worst_request=max(q['manhattan_um'] for q in reqs),
                     return_legs_over_500=sum(q[k]>500 for q in legs for k in ['rom_to_d3_um','d3_to_cbuf_um']),
                     overlaps=overlaps, known_return_hops=8208,known_request_hops=1648,
                     verdict='OPEN_NOT_GRANTABLE', mx_grant='OPEN: published CROM/CBUF LEFs omit SYMMETRY',
                     d3_MX_phase='Rejected: height129600nm reflects M4 12mod48 to36mod48; R0 only used',
                     capacity=dict(right_channel_vertical_cut=crossing_peak(legs),
                                   relay_horizontal_cut=crossing_peak(legs,0),
                                   explanation='Exact y-interval sweep of both incident legs of all513bits in bothgroups; two tracks/net',
                                   upper_vertical=cutoff(RIGHT,END,'V'),
                                   relay_window_horizontal=cutoff(17146.08,17413.92,'H'),
                                   all_rows_horizontal={str(r):cutoff(17146.08-r*775.44,17413.92-r*775.44,'H')for r in range(4)},
                                   M5='No overhead credit: actual M5 OBS and PG',
                                   M6='Known r7 stripe exclusion counted; new macro M5 hookup OPEN',
                                   M9='Known r7 9.091um PG pitch counted; actual new occupancy OPEN',
                                   cut_verdict='OPEN: finite raw resources are not routed free capacity'),
                     open=['Actual pair timing reach involving D3 unknown; 500um is diagnostic only',
                           'CROM/R3 phase-compensated clock/root and reset homes unknown',
                           'All SU request/answer peer homes and cbc/cbr sequencer peers unknown',
                           'ready_tpos observation peer and all strap tie sources unknown',
                           'D3 actual PG/OBS/native qualification absent',
                           'Two-pin-variant arrangement requires distinct actual module/view identities from native owner',
                           'Old-profile c19s r7 PG known; new macro M5-to-upper adapter absent',
                           'Existing neighbor/relay occupancy outside supplied envelope not supplied'])
        receipt=dict(summary=summary,instances=instances,return_bits=legs,request_bits=reqs,open_incident_pins=incident)
        vertical=summary['capacity']['upper_vertical']
        available=sum(v['after_known_pg_spacing_bound'] for v in vertical.values())
        demand=summary['capacity']['right_channel_vertical_cut']['two_track_demand']
        summary['capacity']['right_channel_vertical_cut'].update(after_pg_upper_bound_tracks=available,
            residual_tracks=available-demand,
            verdict='TIGHT_UPPER_BOUND_ONLY' if available>=demand else 'FAIL_CONSERVATIVE_TWO_TRACK_SCREEN')
        h=summary['capacity']['relay_horizontal_cut']
        h['minimum_after_pg_upper_bound_tracks']=min(sum(v['after_known_pg_spacing_bound']for v in q.values())for q in summary['capacity']['all_rows_horizontal'].values())
        h['residual_tracks']=h['minimum_after_pg_upper_bound_tracks']-h['two_track_demand']
        h['verdict']='UPPER_BOUND_ONLY' if h['residual_tracks']>=0 else 'FAIL_CONSERVATIVE_TWO_TRACK_SCREEN'
        write(scheme+'.json',receipt)
        arrangements.append(summary)
        svg(scheme,instances,legs)
    arrangements.sort(key=lambda q:max(q['worst_rom_to_d3'],q['worst_d3_to_cbuf']))
    write('receipt.json',dict(schema='qwen.cbuf.cohort.pin_screen.v1',scope='ANALYTIC_CANDIDATE_NO_ROUTE_NO_GRANT',
                             inputs=inputs,envelope=[GX,14713.92,END,TOP],ranked=arrangements,
                             pin_counts={'CROM':len(rom['pins']),'R3':len(buf['pins']),'D3':1028},
                             pinmap_source={'commit':NATIVE,'path':'rtl/qwen_split/qfd_native_crom8_r3_tp8.sv',
                                            'module':'qfd_crom_return3','ordering':'Independent a/b physical bit ordering; logical bit identity unchanged',
                                            'bit512':'fault','bits511_0':'data','pitch_um':PITCH},
                             pg_shapes={'CROM':rom['pg'],'R3':buf['pg']}))
    print(json.dumps(arrangements,indent=2))


def svg(name,instances,legs):
    # Same scale in x/y; no decorative compression of narrow channels.
    X,Y,W,H=GX-20,14713.92-20,558.376,3159.04
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X} {Y} {W} {H}" width="560" height="3160">',
       '<style>text{font:9px sans-serif} .edge{fill:none;stroke-width:.6;opacity:.35}</style>',
       f'<rect x="{X}" y="{Y}" width="{W}" height="{H}" fill="white"/>',
       f'<rect x="{GX}" y="14713.92" width="518.376" height="3119.04" fill="#fafafa" stroke="#555"/>']
    def yy(y):return Y+H-(y-Y)
    colors={'CROM':'#bee0ff','CBUF':'#bfe8be'}
    for i in instances:
        y=yy(i['y']+i['h'])
        s.append(f'<rect x="{i["x"]}" y="{y}" width="{i["w"]}" height="{i["h"]}" fill="{colors.get(i["kind"],"#ffd29d")}" stroke="#333" stroke-width=".7"/>')
        s.append(f'<text x="{i["x"]+2}" y="{y+12}">{i["n"]} {i["orient"]}</text>')
    # Actual c19s r7 core PG stripes: both alternating supplies. Only M8/M9
    # drawn to keep the to-scale overview readable; all M6-M9 counted above.
    for x in tracks(GX,END,9.091/2,0):
        s.append(f'<path d="M{x},{Y} V{Y+H}" stroke="#a21caf" stroke-width=".48" opacity=".25"/>')
    for y in tracks(14713.92,TOP,8.64/2,0):
        s.append(f'<path d="M{GX},{yy(y)} H{END}" stroke="#a21caf" stroke-width=".48" opacity=".25"/>')
    for q in legs:
        if q['bit'] not in (0,127,255,383,511,512):continue
        for a,b in [('rom','d3_a'),('d3_b','cbuf')]:
            p,t=q[a],q[b]
            s.append(f'<path class="edge" stroke="{"#2563eb" if a=="rom" else "#c2410c"}" d="M{p[0]},{yy(p[1])} H{t[0]} V{yy(t[1])}"/>')
    s.append('</svg>')
    locked()
    (OUT/(name+'.svg')).write_text('\n'.join(s))


if __name__=='__main__':
    main()
