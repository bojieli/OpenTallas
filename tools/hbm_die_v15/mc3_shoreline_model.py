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
    report = dict(status='MODEL ONLY intended child pins vs actual PHY pins; no routing/closure/binding',
        inputs={k:dict(path=v,sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest())
                for k,v in [('phy_lef',a.phy_lef),('pin_plan',a.pin_plan),('manifest',a.manifest)]},
        pair_basis='Current GEN12PHY/controller ports, lo/hi bit pairing pc*width+bit; no bus-centroid reach claim',
        controllers=64, bits_checked=sum(n for _,n in PORTS)*64,
        phy_outline_um=[phy['w'],phy['h']], child_outline_um=[w,h],
        reservations='Alternating parity two rows; same-rank pitch531.168, clearance142.368; gap10.8 toPHY and21.6 betweenrows',
        max_um=max(r['max_um'] for r in rows), over405=sum(r['over405'] for r in rows), rows=rows,
        qualification='Child pins intended only, not native; no corridor/relay escape/nonoverlap with other die children proof. Lower bound hop counts do not prove legal relay placement. Exact equal-age padding/calendar price, reset and clock producers still OPEN.')
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','rows')}))


if __name__ == '__main__':
    main()
