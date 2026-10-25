"""Measured B2o SerDes supply profile, for batched plan adoption with clock corridors.

Isolated PHY IR PASS5/5 at20.993..28.842mV against35mV. This local dense
mesh requires the clock builder to avoid the full declared PG domains.
"""


def apply_phy_ir_profile(plan, log=print):
    changed = []
    for domain in plan['die']['pg'].get('domains', []):
        if domain.get('nets') != ['VDDPHY', 'VSS']:
            continue
        for grid in domain['grid']:
            if grid['layer'] not in ('M8', 'M9') or grid['pitch_um'] != 8.64:
                raise ValueError('measured PHY profile requires8.64um M8/M9 pitch')
            grid['width_um'] = 3.84
        bumps = domain['bumps']
        if bumps['pitch_um'] != 45.0:
            raise ValueError('measured PHY profile requires45um bump pitch')
        x0, y0, x1, y1 = bumps['rect_um']
        size, pitch = 20.0, 45.0
        nx, ny = int((x1-x0-size)//pitch)+1, int((y1-y0-size)//pitch)+1
        if min(nx, ny) <= 0:
            raise ValueError('PHY bump field is smaller than one20um bump')
        sources = {'VDDPHY': [], 'VSS': []}
        for j in range(ny):
            y = (y0+y1)/2 + (j-(ny-1)/2)*pitch
            for i in range(nx):
                x = (x0+x1)/2 + (i-(nx-1)/2)*pitch
                net = 'VDDPHY' if (i+j)%2 == 0 else 'VSS'
                sources[net].append([round(x,4), round(y,4)])
        bumps.update(pattern='centered axis-aligned checkerboard', size_um=size, sources_um=sources)
        domain['evidence'] = 'results/die_trial_1024/hbm_phy_1025/final_remedy_summary.json'
        domain['note'] += ' |3.84um local rails + explicit45um checkerboard C4s; clock corridors avoid full PGdomain'
        changed.append(domain['name'])
    if not changed:
        raise ValueError('plan has no VDDPHY supply domains')
    log(f'PHY IR profile: {len(changed)} domains,3.84um M8/M9, explicit45um checkerboard C4s; clock corridors required')
    return changed
