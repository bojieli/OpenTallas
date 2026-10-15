#!/usr/bin/env python3
"""Grant actual service-wrapper bits local to their unchanged CLOSED PC endpoints.

The output is geometric planning, never routed clock/timing qualification.  Parse
actual wrapper connections, so a changed ABI or an unmapped bit fails closed.
Run after grants.py, with current per-PC-clock service source already installed.
"""
import argparse, gzip, hashlib, json, math, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PC = 'ot_hbm_svc_static_pc'
STEP = .096
PHY = {'k_v','k_rdy','k_addr','k_len','k_tag','k_we','k_wdata','k_wstrb','k_wr_done','kr_v','kr_rdy','kr_tag','kr_beat','kr_data'}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def grid(v): return round(math.ceil(v / 2.16 - 1e-9) * 2.16, 6)
def track(v): return round(.012 + math.ceil((v - .012) / STEP - 1e-9) * STEP, 6)
def bitname(n, b, widths): return n if widths[n] == 1 else f'{n}[{b}]'


def build(src, lef, width=1036.8, height=399.6):
    text = src.read_text()
    ports = {n: (d, int(hi or 0) + 1) for d,hi,n in re.findall(
        r'\b(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)', text)}
    assert ports, f'no explicit ports {src}'
    widths = {k:v[1] for k,v in ports.items()}
    endpoints = {}
    lt = lef.read_text()
    for name, body in re.findall(r'\n  PIN (\S+)(.*?)\n  END \S+', lt, re.S):
        if 'USE SIGNAL' not in body and 'USE CLOCK' not in body: continue
        rect = re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', body)
        assert rect, name
        a,b,c,d = map(float,rect.groups()); endpoints[name] = ((a+c)/2,(b+d)/2)
    children = re.findall(r'\bot_hbm_svc_static_pc\s+(\w+)\s*\((.*?)\n    \);', text, re.S)
    n = len(children)
    assert 1 <= n <= 5 and all(f'clk_pc{k}' in ports for k in range(n)), 'actual per-PC clocks required'
    cw,ch,gap = 140.4,112.32,32.4
    x0 = round(round((width - (n*cw+(n-1)*gap))/2/43.2)*43.2,6)
    cy = round(math.floor((height-ch-20)/43.2)*43.2,6)
    pins, joins, kids = {}, [], []
    # Shared reset remains a real source fanout; put its entry near the median
    # child WEST pin, above the row, outside all per-PC data windows.
    resetx = track(x0 + (n-1)*(cw+gap)/2)
    for c,(inst,body) in enumerate(children):
        cx = round(x0+c*(cw+gap),6)
        assert abs(cx/43.2-round(cx/43.2))<1e-8 and abs(cy/43.2-round(cy/43.2))<1e-8
        kids.append(dict(name=inst, cell=PC, outline=dict(w=cw,h=ch),
                         origin=dict(x=cx,y=cy,orient='R0'), own_clock_root=True,
                         clock_entry=dict(pin='clk',face='W',layer='M4',offset=19.452)))
        mapped = {'N':[], 'S':[]}
        for cp,expr in re.findall(r'\.(\w+)\(([^()]*)\)',body):
            m = re.fullmatch(r'(\w+)(?:\[(\d+)(?:\s*\+:\s*(\d+))?\])?',expr.strip())
            assert m, (cp,expr)
            parent,lo,length = m.groups(); lo=int(lo or 0)
            leafbits = [k for k in endpoints if k == cp or k.startswith(cp+'[')]
            count = len(leafbits)
            assert count > 0, (cp,src)
            if length: assert int(length)==count
            elif '[' in expr: assert count==1
            else: assert widths[parent]==count
            for b in range(count):
                pn = bitname(parent,lo+b,widths)
                ln = cp if count==1 else f'{cp}[{b}]'
                # A [0:0] leaf is physically scalar in the routed LEF.
                if ln not in endpoints: ln=f'{cp}[{b}]'
                assert ln in endpoints, ln
                ex,ey=endpoints[ln]
                joins.append(dict(port=pn, child=inst, leaf_pin=ln,
                                  endpoint=[round(cx+ex,6),round(cy+ey,6)]))
                if cp=='rst_n': continue
                if cp=='clk':
                    pins[pn]=dict(name=pn,face='N',layer='M5',x=track(cx),y=height)
                else: mapped['S' if cp in PHY else 'N'].append(pn)
        for face,names in mapped.items():
            start=track(cx+cw/2-len(names)*STEP/2)
            for j,pn in enumerate(names):
                assert pn not in pins, f'duplicate {pn}'
                pins[pn]=dict(name=pn,face=face,layer='M5',x=round(start+j*STEP,6),y=height if face=='N' else 0)
    used_n={p['x'] for p in pins.values() if p['face']=='N'}
    candidates=[round(resetx+d*STEP,6) for r in range(2000) for d in ({0} if r==0 else (-r,r))]
    resetx=next(x for x in candidates if 5 <= x <= width-5 and x not in used_n)
    pins['rst_n']=dict(name='rst_n',face='N',layer='M5',x=resetx,y=height)
    expect={bitname(p,b,widths) for p,w in widths.items() for b in range(w)}
    assert set(pins)==expect, (sorted(expect-set(pins)),sorted(set(pins)-expect))
    occupied=set()
    for p in pins.values():
        key=(p['face'],p['x']); assert key not in occupied, ('pin collision',key,p)
        occupied.add(key); assert 5 <= p['x'] <= width-5
    for j in joins:
        p=pins[j['port']]; x,y=j['endpoint']
        j['manhattan_um']=round(abs(p['x']-x)+abs(p['y']-y),6)
    worst=max(joins,key=lambda j:j['manhattan_um'])
    assert worst['manhattan_um']<=500, worst
    face_util={f:round(sum(p['face']==f for p in pins.values())*STEP/width,6) for f in ('N','S')}
    assert max(face_util.values())<=.60
    return dict(source_sha256=sha(src), pc_lef_sha256=sha(lef), children=kids,
                pins=list(pins.values()), joins=joins, face_utilisation=face_util,
                worst=worst, source_ports=ports, pin_count=len(pins))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source-root',type=Path,default=ROOT)
    ap.add_argument('--pc-lef',type=Path,required=True)
    ap.add_argument('--contract',default='results/arch/hier_contract_1015/hbm_v15.json')
    ap.add_argument('--out',default='results/arch/hier_contract_1015/service_pc_windows')
    a=ap.parse_args(); out=ROOT/a.out; out.mkdir(parents=True,exist_ok=True)
    hc=json.loads((ROOT/a.contract).read_text()); plans={}; summary={}; shape_text={}
    for s in hc['slots']:
        if not s.get('cell','').startswith('hfd_svc_v15_'): continue
        cell=s['cell']
        if cell not in plans:
            plan=build(a.source_root/s['source'],a.pc_lef,**{'width':s['outline']['w'],'height':s['outline']['h']})
            plans[cell]=plan
            tcl=['# Actual source-bit to unchanged CLOSED PC endpoint plan. Geometric only.']
            for p in plan['pins']:
                tcl.append(f"place_pin -pin_name {{{p['name']}}} -layer M5 -location {{{p['x']:.6f} {p['y']:.6f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
            shape='n'+str(len(plan['children']))
            pin_text='\n'.join(tcl)+'\n'
            assert shape not in shape_text or shape_text[shape]==pin_text, f'nonidentical pin plans for {shape}'
            shape_text[shape]=pin_text
            (out/f'{shape}.tcl').write_text(pin_text)
            with (out/f'{cell}.json.gz').open('wb') as f:
                f.write(gzip.compress(json.dumps(plan,separators=(',',':')).encode(),mtime=0))
        p=plans[cell]
        grouped=[]
        for x in p['pins']:
            m=re.fullmatch(r'(\w+)\[(\d+)\]',x['name'])
            bn,bi=(m[1],int(m[2])) if m else (x['name'],None)
            if grouped and bi is not None and grouped[-1]['base']==bn and grouped[-1]['hi']==bi-1 and abs(grouped[-1]['end']+STEP-x['x'])<1e-5:
                grouped[-1].update(hi=bi,end=x['x'])
            else: grouped.append(dict(base=bn,lo=bi,hi=bi,start=x['x'],end=x['x'],face=x['face']))
        gp=[dict(name=g['base']+(f"[{g['hi']}:{g['lo']}]" if g['lo'] is not None else ''),face=g['face'],layer='M5',offset=round((g['start']+g['end'])/2,6),span_um=[round(g['start']-.012,6),round(g['end']+.012,6)]) for g in grouped]
        s.update(children=p['children'], pins=gp,
                 clock_entry=dict(pin='clk_pc0',face='N',layer='M5',offset=next(x['x'] for x in p['pins'] if x['name']=='clk_pc0')),
                 clock_entries=[dict(pin=x['name'],face='N',layer='M5',offset=x['x']) for x in p['pins'] if x['name'].startswith('clk_pc')],
                 pg_layer='M7',strap_layer='M8',signal_max_layer='M6',layer_cap='M6',layer_rule='cluster',
                 clock_domain='hbm',clock_period_ps=1024.0,clock_compensation_status='OPEN: per-PC measured insertion and phase homes required',
                 face_utilisation=p['face_utilisation'], io_tcl=str((out/('n'+str(len(p['children']))+'.tcl')).relative_to(ROOT)),
                 source_sha256=p['source_sha256'], geometry_status='EXACT_SOURCE_BIT_PLAN; routed clock/TT/FF/DRC and die joins OPEN',
                 geometric_max_wire_um=p['worst']['manhattan_um'], version=2)
        s.pop('per_pc_root_request',None)
        hc['sub_layouts'][cell]=p['children']
        summary[cell]=dict(pins=p['pin_count'],children=len(p['children']),worst=p['worst'],face_utilisation=p['face_utilisation'],source_sha256=p['source_sha256'])
    hc['version']=2; hc['owner']='H-DIE (Codex)';hc['service_source_prerequisite']='41faf638c per-PC-clock wrappers; every wrapper hash pinned in slot'
    (ROOT/a.contract).write_text(json.dumps(hc,indent=1)+'\n')
    receipt=dict(status='GEOMETRY_ONLY_ALL_BITS_WITHIN_500UM',source_root_ref='00fcd6406',pc_lef_sha256=sha(a.pc_lef),masters=summary,
                 limitations=['No routed timing or clock-insertion qualification.','CLOSED PC L408.99/C508.02/spread104.7 remains a native boundary failure.','Generic n1 terminal TT -220.50/FF +63.16/DRC0; this is a structural slot-change successor.','Complete source contract per-PC root binding and all external links remain open.'])
    (out/'summary.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps({k:(v['pins'],v['children'],v['worst']['manhattan_um']) for k,v in summary.items()}))

if __name__=='__main__':main()
