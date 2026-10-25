#!/usr/bin/env python3
"""Generate isolated SerDes-supply IR cases directly from declared die PG domains.

Domain VDDPHY is called VDD inside each electrically isolated PDNSim case.
The shared VSS return is conservatively included at the PHY's own dense mesh,
with no benefit from the surrounding core return mesh. Load is the existing
estimated SerDes energy/bit load, distributed over the declared PHY rectangle.
This checks the planned supply geometry, not transistor-level PHY power.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import hbm_b2_ir as ir
from hbm_b2_power import io_power
from ir_specialnets import materialize


def generate(plan_path, out):
    plan = json.loads(Path(plan_path).read_text())
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    ios = {item['name']: item for item in plan['die']['io']}
    summary = []
    for domain in plan['die']['pg'].get('domains', []):
        if domain['nets'] != ['VDDPHY', 'VSS']:
            continue
        if domain['bumps']['pitch_um'] != ir.ARRAY:
            raise ValueError('unsupported bump pitch')
        if len(domain['grid']) != 2 or {g['layer'] for g in domain['grid']} != {'M8','M9'}:
            raise ValueError('expected M8/M9 domain grid')
        pg = root / domain['name']
        pg.mkdir(parents=True, exist_ok=True)
        x0, y0, x1, y1 = domain['rect_um']
        width, height = x1-x0, y1-y0
        grids = []
        for layer in domain['grid']:
            g = dict(layer)
            g['nets'] = ['VDD', 'VSS']
            g['offset_um'] = (g['offset_um'] - (y0 if g['layer']=='M8' else x0)) % g['pitch_um']
            grids.append(g)
        local_plan = dict(die=dict(outline_um=[width, height], pg=dict(grid=grids)))
        powers = []
        for io_name in domain['io']:
            io = ios[io_name]
            if io['iface'] != 'serdes':
                raise ValueError(f"unsupported domain load {io_name}: {io['iface']}")
            rect = io['rect_um']
            area = (rect[2]-rect[0])*(rect[3]-rect[1])
            power = io_power()['ot_pdie_serdes']['w']
            powers.append(dict(part='domain', rect_um=[rect[0]-x0, rect[1]-y0, rect[2]-x0, rect[3]-y0],
                               w_per_mm2=power/area*1e6, w=power))
        pm = dict(total_w=sum(p['w'] for p in powers),
                  partitions=[dict(name='domain', rect_um=[0,0,width,height], w_per_mm2=0)], regions=powers)
        (pg/'domain_plan.json').write_text(json.dumps(local_plan, indent=1)+'\n')
        (pg/'domain_power.json').write_text(json.dumps(pm, indent=1)+'\n')
        # The plan permits supply bumps only over the declared macro window.
        b = domain['bumps']['rect_um']
        bx0, by0, bx1, by1 = b[0]-x0, b[1]-y0, b[2]-x0, b[3]-y0
        excluded = [0,0,bx0,height, bx1,0,width,height, 0,0,width,by0, 0,by1,width,height]
        ir.generate(SimpleNamespace(plan=str(pg/'domain_plan.json'), power=str(pg/'domain_power.json'),
                                    out=str(pg), window=None, tile=43.2, scale=1, no_bumps=excluded))
        materialize(pg)
        (pg/'run.tcl').write_text((pg/'run_pg.tcl').read_text())
        m = json.loads((pg/'manifest.json').read_text())
        m.update(source_plan=str(plan_path), supply_domain=domain, die_um=[width,height],
                 supply_net_alias={'VDD':'VDDPHY'},
                 scope='Isolated planned PHY mesh plus its own VSS return; surrounding core return omitted.')
        (pg/'manifest.json').write_text(json.dumps(m, indent=1)+'\n')
        summary.append(dict(name=domain['name'], source_rect_um=domain['rect_um'], power_w=pm['total_w'],
                            grid=grids, bumps=m['bumps']['n'], path=str(pg)))
    if not summary:
        raise ValueError('plan has no VDDPHY domains')
    (root/'domains.json').write_text(json.dumps(summary, indent=1)+'\n')
    return summary


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    a=ap.parse_args()
    print(json.dumps(generate(a.plan,a.out),indent=1))
