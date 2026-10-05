"""Default-off full-die power-abstract/PDN preparation. Never launches a flow."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import qwen_rom_fulldie as F

HARD_RETICLE_MM2 = 858.0

def bump_pitch(coverage, bump_um=90.0):
    """Largest exact 1nm-grid pitch with an odd number of pitches per bump."""
    if not 0 < coverage < .5 or bump_um <= 0:
        raise ValueError('invalid coverage/bump pitch')
    nm = round(bump_um * 1000)
    if abs(nm / 1000 - bump_um) > 1e-9:
        raise ValueError('bump off manufacturing grid')
    lower = math.ceil(bump_um / (.48 / coverage))
    for n in range(max(1, lower), nm + 1):
        if n % 2 and nm % n == 0:
            return bump_um / n
    raise ValueError('no representable odd-divisor pitch')

def pg_rects(master, k=1, widths=None):
    """Prospective abstract PG rails; actual child PG handoff remains required."""
    if min(master.w, master.h) < 3:
        raise ValueError('master too small for distinct PG rails')
    signal = F.pin_rects(master, k, widths or {})
    free = []
    for tick in range(math.ceil((.752-.116)/.080), math.floor((master.h-.752-.116)/.080)+1):
        y = .116 + tick*.080
        if any(layer == 'M8' and b < y+.512 and d > y-.512 for _,layer,(_,b,_,d) in signal):
            continue
        if free and y-free[-1] < 1.024:
            continue
        free.append(y)
        if len(free)==2:break
    if len(free)!=2:raise ValueError('no independent M8 PG access rows')
    out = {}
    for net, fraction in [('VDD', 1/3), ('VSS', 2/3)]:
        x = .016 + round((master.w * fraction - .016) / .064) * .064
        y = free[0 if net == 'VDD' else 1]
        out[net] = [('M7', (x-.24, .512, x+.24, master.h-.512)),
                    ('M8', (.512, y-.24, master.w-.512, y+.24))]
    return out

def powered_lef(master, k, widths):
    text, count = F.lef_text(master, k, widths)
    lines = []
    for net, rectangles in pg_rects(master, k, widths).items():
        lines += [f'  PIN {net}', '    DIRECTION INOUT ;',
                  '    USE POWER ;' if net == 'VDD' else '    USE GROUND ;', '    PORT']
        for layer, rect in rectangles:
            lines += [f'      LAYER {layer} ;', '        RECT '+ ' '.join(f'{v:.3f}' for v in rect)+' ;']
        lines += ['    END', f'  END {net}']
    return text.replace('  OBS\n', '\n'.join(lines)+'\n  OBS\n', 1), count

def write_pdn(path, model, bump_um=90.0):
    """Per-instance phase retains die-wide bump alignment through macro origins."""
    lines = ['# Prospective r3 PDN: no installed PG/IR qualification',
             'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
             'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground',
             'global_connect', 'set_voltage_domain -name CORE -power VDD -ground VSS',
             'define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND']
    cp = bump_pitch(F.REGION_PG['tile_field'], bump_um)
    for layer in ['M8', 'M9']:
        lines.append(f'add_pdn_stripe -grid core -layer {layer} -width .48 -pitch {cp:.3f} -offset 0')
    lines.append('add_pdn_connect -grid core -layers {M8 M9}')
    metadata = []
    for i, inst in enumerate(model['insts']):
        if inst.master == 'ot_hbm3e_phy':
            continue  # Source PHY owns its PG pins/grid. No invented replacement.
        region = F.region_at(model, inst.x+inst.w/2, inst.y+inst.h/2)
        coverage = F.REGION_PG.get(region, F.REGION_PG['tile_field']) or F.REGION_PG['strip']
        p = bump_pitch(coverage, bump_um)
        grid = f'pg_{i}'
        lines.append(f'define_pdn_grid -macro -instances {{{inst.name}}} -voltage_domains CORE -name {grid} -starts_with GROUND')
        for layer, origin in [('M8', inst.y), ('M9', inst.x)]:
            offset = (-origin) % p
            lines.append(f'add_pdn_stripe -grid {grid} -layer {layer} -width .48 -pitch {p:.3f} -offset {offset:.3f}')
        lines += [f'add_pdn_connect -grid {grid} -layers {{M7 M8}}',
                  f'add_pdn_connect -grid {grid} -layers {{M8 M9}}']
        metadata.append(dict(instance=inst.name, region=region, per_net_pitch_um=p,
                             alternating_stripe_step_um=p/2, per_net_coverage=.48/p,
                             requested_per_net_coverage=coverage,
                             bump_phase_requires_validation=True))
    Path(path).write_text('\n'.join(lines)+'\n')
    return metadata

def prepare(work, enabled=False, bump_um=90.0, full_case=False):
    if not enabled:
        raise ValueError('r3 is default off; use --enable-pg for preparation')
    work=Path(work)
    if work.exists() and any(work.iterdir()):
        raise ValueError('refuse existing output; preserve historical failures')
    work.mkdir(parents=True,exist_ok=True)
    model=F.build(); master=F.masters(model,1); widths=F.port_widths(model,1)
    parts=[]; pin_inventory={}
    for name,m in master.items():
        text,n=powered_lef(m,1,{q:widths.get((name,q),0) for q in m.order})
        parts.append(text);pin_inventory[name]=dict(signal_pins=n,pg_pins=2,rails=pg_rects(m,1,{q:widths.get((name,q),0) for q in m.order}),
            abstract_only=True,actual_child_pg_bound=False)
    (work/'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'+'\n'.join(parts)+'END LIBRARY\n')
    pdn=write_pdn(work/'pdn.tcl',model,bump_um)
    original=F.plan_record(model)
    original['die'].update(budget_mm2=HARD_RETICLE_MM2,
        margin_mm2=round(HARD_RETICLE_MM2-original['die']['mm2'],3))
    record=dict(schema='QWEN_FULLDIE_PG_R3_PREPARATION_V1',enable_default=False,
        frozen_source_sha256=hashlib.sha256(Path(F.__file__).read_bytes()).hexdigest(),
        original_plan=original,hard_reticle_mm2=858.0,DSpark_ROM_approx_target_mm2=823.0,
        DSpark_added_footprint_source='UNKNOWN: Kant source/abstract/ports required',
        DSpark_installed=False,bump_um=bump_um,bump_policy='90um same-net pitch prospective; original PSM cases retained separately',
        pins=pin_inventory,pdn_instances=pdn,qualification=dict(pdngen=False,IR=False,DRC=False,SSFF=False),
        clock_top='single synchronous tree infeasible; priced CDC/mesh source owned by Claude',
        limitations=['PG ports are feasibility abstracts, not evidence of child installed rails',
          'M7/M8 power pin access, macro OBS, per-instance phase and rotated/mirrored origins require actual pdngen check',
          'Per-net pitch/coverage must be reconciled with original regional coverage before routing iteration',
          'Current k16 runs/source remain unchanged; no flow launched'])
    if full_case:
        case = work/'case'
        F.case_real(model, case)
        (case/'elements.lef').write_bytes((work/'elements.lef').read_bytes())
        (case/'pdn.tcl').write_bytes((work/'pdn.tcl').read_bytes())
        (case/'run_pg.tcl').write_text('read_db /work/floorplan.odb\nsource /work/pdn.tcl\npdngen\nwrite_db /work/pdn.odb\nputs {OT_PDN_R3_GENERATED_ONLY_NO_IR_OR_TIMING_CREDIT}\n')
        record['prepared_full_case'] = str(case)
        record['execution_order'] = ['run.tcl', 'run_pg.tcl']
        record['run_admitted'] = False
    (work/'preparation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',required=True,type=Path)
    ap.add_argument('--enable-pg',action='store_true');ap.add_argument('--full-case',action='store_true');ap.add_argument('--bump-um',type=float,default=90)
    a=ap.parse_args(); r=prepare(a.work,a.enable_pg,a.bump_um,a.full_case)
    print(json.dumps(dict(die=r['original_plan']['die'],masters=len(r['pins']),qualified=False)))
