"""Exact selected r10/PAGE_AW1 native GEN/SYNTH proposal. Never routes."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/'results/hbm_programme_source_frontier_0146'
OUT = ROOT/'results/hbm_programme_native_intake_0450'
TOP = 'ot_hgi_sfu_programme_store_r10'
MASTER = 'ot_sram_1r1w_512x256_m1_r2c2'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ports = []
    text = (SRC/(TOP+'.sv')).read_text().split(');', 1)[0]
    for line in text.splitlines():
        m = re.fullmatch(r'\s*(input|output) (?:wire|reg)\s*(\[[^]]+\])?\s*(.*?)\s*,?\s*', line)
        if not m:
            continue
        direction, rng, names = m.groups()
        width = 1
        if rng:
            hi, lo = rng[1:-1].replace('AW', '11').split(':')
            width = int(eval(hi, {'__builtins__': {}}, {}))-int(lo)+1
        for name in names.rstrip(',').split(','):
            assert re.fullmatch(r'\w+', name)
            ports.append(dict(name=name, direction=direction, width=width, is_vector=bool(rng)))
    assert sum(p['width'] for p in ports) == 2904
    files = [SRC/(TOP+'.sv'), SRC/'ot_hgi_sfu_store_stripe_leaf_r10.sv', SRC/(MASTER+'.sv')]
    macros = []
    for i in range(44):
        row, col = divmod(i, 5)
        x, y = 17.28+col*105.192, 17.28+row*78.3
        macros.append(dict(inst=f'g_leaf[{i//4}].u_leaf.g_page[{i%4}].u_program', master=MASTER,
                           origin_um=[round(x, 6), round(y, 6)], outline_um=[96.552, 69.66]))
    pins = []
    flat = []
    for p in ports:
        side = 'W' if p['direction'] == 'input' else 'E'
        for bit in range(p['width']):
            name = p['name']+f'[{bit}]' if p['is_vector'] else p['name']
            flat.append((name, p['direction'], side))
    # M4 is the vertical layer at E/W edges; pitch .048, offset .024.
    # Inventory proposals stay inside the outline. Clock is explicitly planned
    # near face centre; no old native entry point is reused or qualified.
    clock_y = .024+round((738.72/2-.024)/.048)*.048
    reset_y = clock_y+8.64
    for side in ('W', 'E'):
        ordinary = [x for x in flat if x[2] == side and x[0] not in ('clk','rst_n')]
        tracks = [.024+i*.048 for i in range(15400) if 17.28 <= .024+i*.048 <= 738.72-17.28]
        if side == 'W':
            tracks = [y for y in tracks if abs(y-clock_y)>4.32 and abs(y-reset_y)>4.32]
        assert len(tracks) >= len(ordinary)
        for i,(name,direction,_) in enumerate(ordinary):
            y=tracks[round(i*(len(tracks)-1)/(len(ordinary)-1))]
            pins.append(dict(name=name,direction=direction,face=side,layer='M4',
                             x=.024 if side=='W' else 574.536,y=round(y,6)))
    for name,y in [('clk',clock_y),('rst_n',reset_y)]:
        pins.append(dict(name=name,direction='input',face='W',layer='M4',x=.024,y=round(y,6)))
    assert len({(p['layer'],p['x'],p['y']) for p in pins}) == 2904
    (OUT/'r10_pins.json').write_text(json.dumps(pins, indent=2)+'\n')
    rects = [dict(name=m['inst'], master=MASTER, rect_um=m['origin_um']+
                  [round(m['origin_um'][0]+96.552,6),round(m['origin_um'][1]+69.66,6)], orient='R0') for m in macros]
    core = dict(schema='opentallas.core_macros.v1', cores={TOP:dict(status='KNOWN',
                basis='SOURCE_ONLY_GEN_PROPOSAL_NOT_PLACED_PROVIDER', macros=rects)})
    (OUT/'core_macros.json').write_text(json.dumps(core, indent=2)+'\n')
    template = json.loads((ROOT/'results/hbm_storeB_native_capsule_0136/GEN_plan.json').read_text())
    template['die']['pg']['domains'] = []
    template['partition_types'] = {'native_provider_slot':dict(outline_um=[574.56,738.72],
       hard_cores=[dict(inst='u_selected_r10',module=TOP,origin_um=[0,0],outline_um=[574.56,738.72],pins_file='r10_pins.json')])}
    (OUT/'GEN_plan.json').write_text(json.dumps(template, indent=2)+'\n')
    view = TOP+'@'+sha(OUT/'r10_pins.json')[:12]
    views = dict(schema='opentallas.hbm_arch.views.v1',plan='GEN_plan.json',plan_sha256=sha(OUT/'GEN_plan.json'),
      view_list=[dict(view=view,module=TOP,outline_um=[574.56,738.72],pins_file='r10_pins.json',
      pins_sha256=sha(OUT/'r10_pins.json'),pins=2904,recipe_keys=[TOP],family='SOURCE13_SELECTED_R10_PAGE_AW1',
      canonical_type=None,instances=['B113.DISABLED_moved_r10'],placed=0)])
    (OUT/'views.json').write_text(json.dumps(views,indent=2)+'\n')
    model = dict(status='MODEL_FOR_ONE_NATIVE_GEN_SYNTH_SOURCEPROOF_INTAKE',top=TOP,params=dict(PAGE_AW=1),
      files=[dict(file=str(p.relative_to(ROOT)),sha256=sha(p))for p in files],ports=ports,
      external_bits=2904,declared_preopt_soft_FF=22922,native_master_count=44,native_capacity_bits=5767168,
      macros=macros,outline_um=[574.56,738.72],macro_body_area_um2=44*96.552*69.66,
      macro_halo_area_um2=44*(96.552+8.64)*(69.66+8.64),
      area_outside_macros_and_halos_um2=574.56*738.72-44*(96.552+8.64)*(69.66+8.64),
      context_only_other_source=dict(top_sha256='f9ee5065debf3c65386aabcf1e36e7efc93665aae4417dc0b75d7a90de8bf383',
         soft_std_cells=66275,soft_area_um2=9506.7,source_equivalence_transfer=False),
      requested_resources=dict(memory_GB=12,threads=2,disk_GB=8,
       basis='Other r10 source contextual66k mappedcells; selected body22922declaredFF/44same512masters. TwelveGB also covers two opposite-frontends; no inherited proof.'),
      collar='Separate exact native collar source/mapping remains required; this first intake maps selected r10 only.',
      held=['No PLACE/P&R','Actual mapped FF/logic area','Legal provider internal rows and leaf clock/reset pin placement',
       '44native SRAM access/PG streets','Actual two reset-route/START66 closure','Collar rows/clock',
       'Parent5106existingXO plus2304upstream rows/clockloads','Actual provider-output→B113capture405reach',
       'No current parent/source event adoption'],release_eligible=False)
    (OUT/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    print('PREP_ONLY exact2904ABI/44masters; native sourceproof and physical placement not inferred')


if __name__ == '__main__':
    main()
