"""Price intended MC3 boundary pins against actual two-PHY 64-PC pin pairs.

Planning only: alternating two-row reservation, no binding or timing authority.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from case_reach import lef, xf

PORTS = [('row_v',1),('row_op',3),('row_bank',5),('row_row',19),
         ('col_v',1),('col_we',1),('col_bank',5),('col_col',5),
         ('col_data',256),('col_strb',32),('dram_rvalid',1),('dram_rdata',256)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phy_lef'); ap.add_argument('pin_plan'); ap.add_argument('manifest'); ap.add_argument('out')
    ap.add_argument('--relay-dir', help='Unqualified template LEFs for bounded upper-row corridor model')
    a = ap.parse_args()
    phy = next(iter(lef(a.phy_lef).values()))
    plan = json.loads(Path(a.pin_plan).read_text())
    manifest = json.loads(Path(a.manifest).read_text())
    w, h = plan['outline_um']
    if (w, h) != (388.8, 388.8):
        raise ValueError('model requires reviewed square388.8 plan')
    centres = [sum(phy['pins'][f'{p}[{pc*width+k}]'][0]
               for p, width in PORTS for k in range(width)) / sum(n for _,n in PORTS) for pc in range(32)]
    rows = []
    for q in ('SW','NW'):
        base = manifest['placement']['phy_'+q]
        pp = dict(x=base['x'], y=base['y'], orient=base['o'])
        for pc in range(32):
            rank = pc % 2
            x = round(round((base['x'] + centres[pc] - w/2)/0.216)*0.216, 3)
            y = (base['y'] + phy['h'] + 10.8 + rank*(h+21.6)) if q=='SW' else (base['y'] - 10.8 - h - rank*(h+21.6))
            cp = dict(x=x, y=y, orient='R0' if q=='SW' else 'MX')
            ports = []
            for p, width in PORTS:
                costs = []
                for bit in range(width):
                    child_pin = p if width==1 else f'{p}[{bit}]'
                    c = xf(cp, w, h, *plan['pins'][child_pin]['at'])
                    ph = xf(pp, phy['w'], phy['h'], *phy['pins'][f'{p}[{pc*width+bit}]'])
                    span = abs(c[0]-ph[0])+abs(c[1]-ph[1])
                    if not math.isfinite(span):
                        raise ValueError('invalid pin geometry')
                    costs.append(span)
                ports.append(dict(port=p, bits=width, max_um=max(costs),
                                  over405=sum(c>405 for c in costs),
                                  minimum_extra_hops_lb=max(0,math.ceil(max(costs)/405)-1)))
            rows.append(dict(instance=f'ctl_{q}_p{pc:02d}', rank=rank, placement=cp,
                             max_um=max(p['max_um'] for p in ports),
                             over405=sum(p['over405'] for p in ports), ports=ports))
    report = dict(status='MODEL ONLY supplied child pins vs actual PHY pins; no routing/closure/binding',
        child_pin_scope=plan['scope'],
        inputs={k:dict(path=v,sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest())
                for k,v in [('phy_lef',a.phy_lef),('pin_plan',a.pin_plan),('manifest',a.manifest)]},
        pair_basis='Current GEN12PHY/controller ports, lo/hi bit pairing pc*width+bit; no bus-centroid reach claim',
        controllers=64, bits_checked=sum(n for _,n in PORTS)*64,
        phy_outline_um=[phy['w'],phy['h']], child_outline_um=[w,h],
        reservations='Alternating parity two rows; same-rank pitch531.168, clearance142.368; gap10.8 toPHY and21.6 betweenrows',
        max_um=max(r['max_um'] for r in rows), over405=sum(r['over405'] for r in rows), rows=rows,
        qualification='Child pin scope is the supplied plan scope; no corridor/relay escape/nonoverlap with other die children proof. Lower bound hop counts do not prove legal relay placement. Exact equal-age padding/calendar price, reset and clock producers still OPEN.')
    if a.relay_dir:
        relays = {f:next(iter(lef(Path(a.relay_dir)/f'hbfd_rly_624_{f}.lef').values())) for f in ('NS','SN')}
        costs, boxes = [], []
        for r in rows:
            if r['rank'] != 1:
                continue
            q, pc = r['instance'].split('_')[1], int(r['instance'][-2:])
            base = manifest['placement']['phy_'+q]
            pp = dict(x=base['x'],y=base['y'],orient=base['o'])
            for direction, flow, height in [('command','NS',194.4),('return','SN',248.4)]:
                v = relays[flow]
                x = round(round((r['placement']['x']+w/2-v['w']/2)/0.216)*0.216,3)
                y = base['y']+phy['h']+height if q=='SW' else base['y']-height-v['h']
                rp = dict(x=x,y=y,orient='R0' if q=='SW' else 'MX')
                packed = 0; segments = []
                for port, width in PORTS:
                    if port.startswith('dram_') != (direction=='return'):
                        continue
                    for bit in range(width):
                        c = xf(r['placement'],w,h,*plan['pins'][port if width==1 else f'{port}[{bit}]']['at'])
                        ph = xf(pp,phy['w'],phy['h'],*phy['pins'][f'{port}[{pc*width+bit}]'])
                        ip = xf(rp,v['w'],v['h'],*v['pins'][f'i[{packed}]'])
                        op = xf(rp,v['w'],v['h'],*v['pins'][f'o[{packed}]'])
                        source, sink = (c, ph) if direction=='command' else (ph,c)
                        segments.extend([abs(source[0]-ip[0])+abs(source[1]-ip[1]),abs(op[0]-sink[0])+abs(op[1]-sink[1])])
                        packed += 1
                name = r['instance']+'_'+direction
                boxes.append((name,x,y,x+v['w'],y+v['h']))
                costs.append(dict(instance=name,placement=rp,bits=packed,max_segment_um=max(segments),over405=sum(s>405 for s in segments)))
        # Exact nonoverlap against these relay templates, all64 intended children and two actual PHYs only.
        obstacles = [(r['instance'],r['placement']['x'],r['placement']['y'],r['placement']['x']+w,r['placement']['y']+h) for r in rows]
        obstacles += [('phy_'+q,v['x'],v['y'],v['x']+phy['w'],v['y']+phy['h']) for q in ('SW','NW') for v in [manifest['placement']['phy_'+q]]]
        conflicts = []
        for i,(name,x0,y0,x1,y1) in enumerate(boxes):
            for other,a0,b0,a1,b1 in obstacles+boxes[:i]:
                # 5.4um halo on BOTH objects (10.8um separation).
                if x0-5.4 < a1+5.4 and x1+5.4 > a0-5.4 and y0-5.4 < b1+5.4 and y1+5.4 > b0-5.4:
                    conflicts.append([name,other])
        report['upper_corridor_model'] = dict(templates='Unqualified legacy624NS/SN; not final relay source/native/clock closure',
            template_sha256={f:hashlib.sha256((Path(a.relay_dir)/f'hbfd_rly_624_{f}.lef').read_bytes()).hexdigest() for f in relays},
            max_segment_um=max(c['max_segment_um'] for c in costs),over405=sum(c['over405'] for c in costs),
            known_object_conflicts=conflicts,rows=costs,
            open='All other die children/corridors, native relay fanout/storage, reset/clock, escapes, lower-row parity compensation and static calendar price remain OPEN.')
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','rows','upper_corridor_model')}))


if __name__ == '__main__':
    main()
