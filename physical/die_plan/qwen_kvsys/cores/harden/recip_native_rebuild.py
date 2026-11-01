#!/usr/bin/env python3
"""ONE current native RECIP witness rebuild using the established KV core backend.

An isolated invocation restores the exact retained native LEF pin/grid/PG
contract. It does not change the backend defaults, canonical plan, RTL or views.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def prepare(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ref = ROOT / 'physical/ref_tile/qkh_recip_ref'
    spec = json.loads((ref / 'spec.json').read_text())
    assert spec['top'] == 'ot_qkh_recip_leaf' and spec['outline'] == {'w': 216, 'h': 216}
    assert not spec.get('params') and not spec.get('children') and not spec.get('macros')
    lef = ref / 'views/ot_qkh_recip_leaf/ot_qkh_recip_leaf.lef'
    text = lef.read_text()
    assert re.search(r'SIZE\s+216(?:\.0)?\s+BY\s+216(?:\.0)?\s*;', text)
    pins = []
    for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', text, re.M | re.S):
        name, body = m[1], m[2]
        use = re.search(r'USE\s+(\w+)', body)
        if use and use[1] in ('POWER', 'GROUND'):
            continue
        direction = re.search(r'DIRECTION\s+(\w+)', body)[1].lower()
        layer = re.search(r'LAYER\s+(M\d+)\s*;', body)[1]
        rects = re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;', body)
        assert rects, name + ': native pin rectangle required'
        assert set(re.findall(r'LAYER\s+(M\d+)\s*;', body)) == {layer}, name + ': mixed native pin layers'
        x0, y0, x1, y1 = map(float, rects[0])
        assert layer in ('M4', 'M5')
        along = (y0 + y1) / 2 if layer == 'M4' else (x0 + x1) / 2
        assert abs((along - .012) / .048 - round((along - .012) / .048)) < 1e-5
        assert sorted([round(x1-x0, 6), round(y1-y0, 6)]) == [.024, .084]
        pins.append(dict(name=name, layer=layer, x=(x0+x1)/2, y=(y0+y1)/2,
                         native_rect=[x0,y0,x1,y1], native_rects=[list(map(float,r)) for r in rects], direction=direction))
    ports = dict(clk=['input',None,None], rst_n=['input',None,None], v=['input',None,None],
                 x=['input',31,0], y=['output',31,0], vo=['output',None,None], fault=['output',None,None])
    classes = {}
    for name, (direction, hi, lo) in ports.items():
        for bit in ([None] if hi is None else range(lo,hi+1)):
            pin = name if bit is None else f'{name}[{bit}]'
            classes[pin] = 'clk' if name == 'clk' else ('in' if direction == 'input' else 'out')
    assert len(pins) == 69 and {p['name'] for p in pins} == set(classes)
    assert all(p['direction'] == ports[p['name'].split('[')[0]][0] for p in pins)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    source_files = [ROOT / p for p in spec['sources']]
    assert all(p.is_file() for p in source_files)
    contract = dict(kind='exact_retained_native_RECIP_interface', source_lef=str(lef),
                    source_lef_sha256=digest(lef), signal_pins=69, outline_um=[216,216],
                    offsets_um={'M4':.012,'M5':.012}, pin_length_um=.084, core_margin_um=2.16,
                    pg_source=str(ref/'pdn.tcl'), pg_source_sha256=digest(ref/'pdn.tcl'),
                    source_files={str(p.relative_to(ROOT)):digest(p) for p in source_files},
                    source_mutations=False, cycles_added=0, canonical_views_changed=False)
    (out/'native_contract.json').write_text(json.dumps(contract,indent=1)+'\n')
    (out/'pins.json').write_text(json.dumps(dict(schema='opentallas.die_plan.core_pins.v1',core=spec['top'],
        source='Exact retained native LEF rectangles, no pin movement',pins=pins),indent=1)+'\n')
    plan=json.loads((ROOT/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json').read_text())
    plan['partition_types']['recip_native_witness']={'hard_cores':[dict(inst='recip',module=spec['top'],outline_um=[216,216],pins_file='pins.json')],
        'contents':[dict(inst='recip',module=spec['top'])]}
    plan['clock'].update(period_ps=833.0,insertion_ps=250,common_latency_ps=250,insertion_ff_ps=202.5,insertion_tol_ps=40)
    (out/'plan.json').write_text(json.dumps(plan)+'\n')
    core=dict(schema='opentallas.kv.core_rtl.v1',module=spec['top'],type='recip_native_witness',inst='recip',
        files=list(map(str,source_files)),port_decl=ports,pin_class=classes,
        boundary_role=dict(clk='clk',rst_n='reset'),ports=7,pin_bits=69,
        report=dict(added=[],stale=[],straps=[],clock_nets={'clk':'clk'}),native_pin_contract=contract)
    (out/'core.json').write_text(json.dumps(core,indent=1)+'\n')
    recipes=json.loads((HERE/'recipes_kv.json').read_text())
    recipes[spec['top']]=dict(sigmax='M6',util=.55,face_flops=True,source='Exact current native RECIP216 retained interface; existing ref_tile layer grant M6')
    (out/'recipes.json').write_text(json.dumps(recipes,indent=1)+'\n')
    kd=out/'kit_rtl'/'recip_native_witness';kd.mkdir(parents=True,exist_ok=True)
    (kd/'kit_rtl.json').write_text(json.dumps(dict(hard_macros={}))+'\n')
    # The backend is reused without a generic default/policy change. These
    # isolated process-local settings reproduce this one native physical ABI.
    path=HERE/'gen_core_kit_kv.py'
    sp=importlib.util.spec_from_file_location('native_recip_backend',path)
    backend=importlib.util.module_from_spec(sp);sp.loader.exec_module(backend)
    backend.OFFS.update(M4=.012,M5=.012)
    backend.PIN_LEN_UM=.084
    backend.CORE_MARGIN_UM=2.16
    backend.PDN=(ref/'pdn.tcl').read_text()
    tracks=backend.make_tracks()
    for layer in ('M4','M5'):
        old=f'make_tracks {layer} -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048'
        assert tracks.count(old)==1
        tracks=tracks.replace(old,old.replace('offset 0.024','offset 0.012'))
    tracks='# Exact retained RECIP native M4/M5 phase0.012; standalone prototype only.\n'+tracks
    backend.make_tracks=lambda: tracks
    ordinary_io = backend.io_tcl
    def native_io(*args, **kwargs):
        io, rows = ordinary_io(*args, **kwargs)
        # Retain secondary access PORT rectangles as well (x[31] has one).
        extra = ['set nb [ord::get_db_block]', 'set nu [[ord::get_db_tech] getDbUnitsPerMicron]']
        for pin in pins:
            for rect in pin['native_rects'][1:]:
                coords = ' '.join('[expr {round(' + str(v) + ' * $nu)}]' for v in rect)
                extra += ['set nt [$nb findBTerm {' + pin['name'] + '}]',
                          'if {$nt eq "NULL"} {error "native RECIP pin absent"}',
                          'set nr [list ' + coords + ']', 'set nh 0',
                          'foreach pp [$nt getBPins] {foreach bb [$pp getBoxes] {',
                          'if {[list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] eq $nr && [[$bb getTechLayer] getName] eq {' + pin['layer'] + '}} {set nh 1}',
                          '}}', 'if {!$nh} {',
                          'set np [odb::dbBPin_create $nt]', '$np setPlacementStatus FIRM',
                          'odb::dbBox_create $np [[ord::get_db_tech] findLayer {' + pin['layer'] + '}] ' + coords, '}']
        return io + '\n'.join(extra) + '\n', rows
    backend.io_tcl = native_io
    sys.argv=[str(path),'--core-json',str(out/'core.json'),'--plan',str(out/'plan.json'),'--out',str(out/'gen'),
        '--kit-rtl',str(out/'kit_rtl'),'--recipes',str(out/'recipes.json'),'--tool',str(ROOT/'tools/die_plan'),'--util','0.55','--sigmax','M6',
        '--cts-setup-only','--two-mode-grt','--hold-ff-margin','10','--io-tt-ps','250','--io-ff-ps','202.5',
        '--orfs-var','PLACE_DENSITY=0.55']
    backend.main()
    return out/'gen'/'ot_qkh_recip_leaf__216x216'


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    args=ap.parse_args();print('NATIVE_RECIP_KIT',prepare(args.out))
