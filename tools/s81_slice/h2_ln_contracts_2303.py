#!/usr/bin/env python3
"""H2 plain LN physical contracts from the earlier measured native outline."""
import argparse, copy, importlib.util, json, re, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--old', required=True)
p.add_argument('--interfaces', required=True)
a = p.parse_args()
r, old = Path(a.repo), Path(a.old)
sys.path.insert(0, str(r / 'tools/die_plan'))
import schema as S
q = r / 'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'
sp = importlib.util.spec_from_file_location('h2gen', q)
g = importlib.util.module_from_spec(sp)
sp.loader.exec_module(g)
interfaces = json.loads(Path(a.interfaces).read_text())['masters']
base = json.loads((old / 'pins.json').read_text())
assert base['module'] == 'ot_s81_mu72_lnland_nst_1ck'
assert base['outline_um'] == [112.32, 112.32]
assert len(base['pins']) == 2231
assert [x for x in base['pins'] if x['name'] == 'ck_k'] == [dict(name='ck_k',layer='M5',x=56.172,y=56.16)]
oldspec = json.loads((old / 'spec.json').read_text())
summary = {}
for module in ('ot_s81_mu72_lnland_nst','ot_s81_mu72_lnland'):
    abi = interfaces[module]
    pins = [copy.deepcopy(x) for x in base['pins'] if x['name'] != 'ck_k']
    pins += [dict(name='ck_k',layer='M5',x=56.172,y=.24),dict(name='ck_n',layer='M5',x=56.172,y=112.08)]
    if module == 'ot_s81_mu72_lnland':
        for i,c in enumerate((2.988,3.18)):
            pins += [dict(name=f'k_st[{i}]',layer='M5',x=c,y=.042),
                     dict(name=f'n_st[{i}]',layer='M4',x=112.278,y=c)]
    expected = {b if v['bits'] == 1 else f'{b}[{i}]' for b,v in abi['ports'].items() for i in range(v['bits'])}
    assert {x['name'] for x in pins} == expected
    assert len(pins) == len(expected) == (2232 if module.endswith('_nst') else 2236)
    assert len({(x['layer'],x['x'],x['y']) for x in pins}) == len(pins)
    for x in pins:
        c = x['x'] if x['layer']=='M5' else x['y']
        assert abs((c-.012)/.048-round((c-.012)/.048)) < 1e-7, x
        assert not S.pg_blocked(x['layer'],c), x
    dirs = {x['name']:abi['ports'][re.sub(r'\[\d+\]$','',x['name'])]['direction'].upper() for x in pins}
    clock={'ck_k','ck_n'}
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {module}',
         ' CLASS BLOCK ;',' ORIGIN 0 0 ;',' SIZE 112.32 BY 112.32 ;',' SYMMETRY X Y ;']
    for x in pins:
        n,L,xx,y=x['name'],x['layer'],x['x'],x['y']
        dx,dy=(.024,.24) if n in clock else ((.024,.042) if L=='M5' else(.042,.016))
        assert min(xx-dx,y-dy) >= -1e-7 and max(xx+dx,y+dy) <= 112.32+1e-7
        lef += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;','  USE CLOCK ;' if n in clock else '  USE SIGNAL ;',
                '  PORT',f'   LAYER {L} ;',f'   RECT {xx-dx:.6f} {y-dy:.6f} {xx+dx:.6f} {y+dy:.6f} ;',
                '  END',f' END {n}']
    lef += [f'END {module}','END LIBRARY']
    spec=copy.deepcopy(oldspec)
    spec.update(name=module,top=module,**abi['spec_clock_contract'])
    spec['sources']=[x for x in spec['sources'] if 'lnland_nst_1ck.sv' not in x]
    spec['defines']=[x.removeprefix('-D') for x in abi['defines'] if x!='-DSYNTHESIS']
    spec['note']='H2 existing plain module, two physical related clock roots, original independent resets; no wrapper or added cycles.'
    recipe=dict(ref_tile=f'physical/die_plan/s81/cores/h2/{module}',multi_root=True,insertion_balance=True,
                io_hold='sender_min',suffix='h2',defines=[])
    mr=g.multi_root_contract(module,spec,recipe)
    ii=[n for n,v in abi['ports'].items() if v['direction']=='input' and n not in clock and n not in spec['reset_ports']]
    oo=[n for n,v in abi['ports'].items() if v['direction']=='output']
    g.multi_root_check_io(module,mr,ii,oo,spec['reset_ports'])
    root=r/f'physical/die_plan/s81/cores/h2/{module}'
    root.mkdir(parents=True,exist_ok=True)
    (root/'pins.json').write_text(json.dumps(dict(module=module,outline_um=[112.32,112.32],pins=pins),indent=1)+'\n')
    (root/f'{module}.lef').write_text('\n'.join(lef)+'\n')
    (root/'spec.json').write_text(json.dumps(spec,indent=1)+'\n')
    (root/'recipe.json').write_text(json.dumps(recipe,indent=1)+'\n')
    summary[module]=dict(pins=len(pins),clocks=['ck_k','ck_n'],roots=mr['roots'],
                         spec=str(root.relative_to(r)/'spec.json'),outline_um=[112.32,112.32],
                         added_cycles=0,physical_status='CONTRACT_ONLY; no kit/placement/timing qualification')
(r/'results/s81_h2_interfaces_2258/ln_contracts.json').write_text(json.dumps(summary,indent=1)+'\n')
print(json.dumps(summary))
