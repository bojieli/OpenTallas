#!/usr/bin/env python3
"""ONE explicitly selected current native RECIP/ZH witness rebuild using the established KV core backend.

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


def prepare(out, leaf="recip"):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert leaf in ('recip', 'zh')
    is_zh = leaf == 'zh'
    module = 'ot_nhb_zh' if is_zh else 'ot_qkh_recip_leaf'
    size = 151.2 if is_zh else 216
    util = .5 if is_zh else .55
    sigmax = 'M5' if is_zh else 'M6'
    typ = leaf + '_native_witness'
    ref = ROOT / 'physical/ref_tile' / ('ot_nhb_zh_m5' if is_zh else 'qkh_recip_ref')
    spec = json.loads((ref / 'spec.json').read_text())
    assert spec['top'] == module and spec['outline'] == {'w': size, 'h': size}
    assert not spec.get('params') and not spec.get('children') and not spec.get('macros')
    lef = ref / 'views' / module / (module + '.lef')
    text = lef.read_text()
    assert tuple(map(float, re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;', text).groups())) == (size, size)
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
    if is_zh:
        ports = dict(clk=['input',None,None], rst_n=['input',None,None], start=['input',None,None],
                     zs_we=['input',127,0], sid=['input',127,0], ziv=['input',3,0], zg=['input',None,None],
                     zp=['input',5,0], root=['output',63,0], zerr=['output',3,0])
    classes = {}
    for name, (direction, hi, lo) in ports.items():
        for bit in ([None] if hi is None else range(lo,hi+1)):
            pin = name if bit is None else f'{name}[{bit}]'
            classes[pin] = 'clk' if name == 'clk' else ('in' if direction == 'input' else 'out')
    assert len(pins) == (338 if is_zh else 69) and {p['name'] for p in pins} == set(classes)
    assert all(p['direction'] == ports[p['name'].split('[')[0]][0] for p in pins)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    source_names = spec['sources']
    if is_zh:
        # Current canonical active cone: no retained snapshot overlays or unrelated SRAM stubs.
        source_names = ['rtl/hdc/nearhbm/ot_nhb_tiles.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv',
                        'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat_nr.sv',
                        'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
                        'rtl/hdc/ot_hdc_delay.sv', 'rtl/lib/ot_rst_relay.sv']
    source_files = [ROOT / p for p in source_names]
    assert all(p.is_file() for p in source_files)
    contract = dict(kind='exact_retained_native_' + leaf.upper() + '_interface', source_lef=str(lef),
                    source_lef_sha256=digest(lef), signal_pins=len(pins), outline_um=[size,size],
                    offsets_um={'M4':.012,'M5':.012}, pin_length_um=.084, core_margin_um=2.16,
                    pg_source=str(ref/'pdn.tcl'), pg_source_sha256=digest(ref/'pdn.tcl'),
                    source_files={str(p.relative_to(ROOT)):digest(p) for p in source_files},
                    source_mutations=False, cycles_added=0, canonical_views_changed=False)
    (out/'native_contract.json').write_text(json.dumps(contract,indent=1)+'\n')
    (out/'pins.json').write_text(json.dumps(dict(schema='opentallas.die_plan.core_pins.v1',core=spec['top'],
        source='Exact retained native LEF rectangles, no pin movement',pins=pins),indent=1)+'\n')
    plan=json.loads((ROOT/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json').read_text())
    plan['partition_types'][typ]={'hard_cores':[dict(inst=leaf,module=module,outline_um=[size,size],pins_file='pins.json')],
        'contents':[dict(inst=leaf,module=module)]}
    plan['clock'].update(period_ps=833.0,insertion_ps=250,common_latency_ps=250,insertion_ff_ps=202.5,insertion_tol_ps=40)
    (out/'plan.json').write_text(json.dumps(plan)+'\n')
    core=dict(schema='opentallas.kv.core_rtl.v1',module=spec['top'],type=typ,inst=leaf,
        files=list(map(str,source_files)),port_decl=ports,pin_class=classes,
        boundary_role=dict(clk='clk',rst_n='reset'),ports=len(ports),pin_bits=len(pins),
        report=dict(added=[],stale=[],straps=[],clock_nets={'clk':'clk'}),native_pin_contract=contract)
    (out/'core.json').write_text(json.dumps(core,indent=1)+'\n')
    recipes=json.loads((HERE/'recipes_kv.json').read_text())
    recipes[module]=dict(sigmax=sigmax,util=util,face_flops=True,source=f'Exact current native {leaf.upper()} retained interface; existing ref_tile layer grant {sigmax}')
    (out/'recipes.json').write_text(json.dumps(recipes,indent=1)+'\n')
    kd=out/'kit_rtl'/typ;kd.mkdir(parents=True,exist_ok=True)
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
    tracks='# Exact retained native M4/M5 phase0.012; standalone prototype only.\n'+tracks
    backend.make_tracks=lambda: tracks
    ordinary_io = backend.io_tcl
    def native_io(*args, **kwargs):
        io, rows = ordinary_io(*args, **kwargs)
        # Retain both overlapping x[31] access rectangles on its one physical pin.
        # The native rectangles overlap electrically; separate dbBPins are
        # rejected by TritonRoute pin_access (DRT-0302).
        extra = ['set nb [ord::get_db_block]', 'set nu [[ord::get_db_tech] getDbUnitsPerMicron]']
        for pin in pins:
            for rect in pin['native_rects'][1:]:
                first = pin['native_rects'][0]
                assert max(first[0],rect[0]) < min(first[2],rect[2]) and max(first[1],rect[1]) < min(first[3],rect[3]), 'native secondary access must overlap its primary conductor'
                coords = ' '.join('[expr {round(' + str(v) + ' * $nu)}]' for v in rect)
                extra += ['set nt [$nb findBTerm {' + pin['name'] + '}]',
                          'if {$nt eq "NULL"} {error "native leaf pin absent"}',
                          'set nr [list ' + coords + ']', 'set nh 0',
                          'foreach pp [$nt getBPins] {foreach bb [$pp getBoxes] {',
                          'if {[list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] eq $nr && [[$bb getTechLayer] getName] eq {' + pin['layer'] + '}} {set nh 1}',
                          '}}', 'if {!$nh} {',
                          'set np [lindex [$nt getBPins] 0]',
                          'if {$np eq "NULL" || $np eq ""} {error "native primary pin absent"}', '$np setPlacementStatus FIRM',
                          'odb::dbBox_create $np [[ord::get_db_tech] findLayer {' + pin['layer'] + '}] ' + coords, '}']
        return io + '\n'.join(extra) + '\n', rows
    backend.io_tcl = native_io
    sys.argv=[str(path),'--core-json',str(out/'core.json'),'--plan',str(out/'plan.json'),'--out',str(out/'gen'),
        '--kit-rtl',str(out/'kit_rtl'),'--recipes',str(out/'recipes.json'),'--tool',str(ROOT/'tools/die_plan'),'--util',str(util),'--sigmax',sigmax,
        '--cts-setup-only','--two-mode-grt','--hold-ff-margin','10','--io-tt-ps','250','--io-ff-ps','202.5',
        '--orfs-var','PLACE_DENSITY='+str(util)]
    backend.main()
    result = out/'gen'/f'{module}__{size:g}x{size:g}'
    runner = (result/'run_kit_kv.sh').read_text()
    marker = '--out "$K/signoff" --image "$IMAGE"'
    assert runner.count(marker) == 1
    # Passive capture reuses the existing TT/FF signoff graph; no second STA walk.
    (result/('run_native_' + leaf + '.sh')).write_text(runner.replace(marker, '--retain-child-clock-witness ' + marker, 1))
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    ap.add_argument('--leaf',choices=('recip','zh'),default='recip')
    args=ap.parse_args();print('NATIVE_'+args.leaf.upper()+'_KIT',prepare(args.out,args.leaf))
