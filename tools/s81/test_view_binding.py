#!/usr/bin/env python3
"""Fast unit test of the S81 by-name view binding (no die build): the generator's table loader and the LEF-pin /
netlist-port check, on a fixture in a temporary directory.  python3 tools/s81/test_view_binding.py
(The die-level self-check -- unchanged outputs with nothing bound, one master bound, the hard errors on a built die --
is recorded in results/arch/s81_native_20261013/BINDING.md.)"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402

MST = 'dsfd_rly_15_SN'
PORTS = dict(i=('input', 15), o=('output', 15), ck=('input', 1), rs=('input', 1))


def lef(pins, w=15.12, h=15.12, macro=MST):
    L = [f'MACRO {macro}', f'  SIZE {w} BY {h} ;']
    for nm, d in pins:
        L += [f'  PIN {nm}', f'    DIRECTION {d} ;', '    PORT', '      LAYER M4 ;', '        RECT 0 0 0.2 0.024 ;', '    END',
              f'  END {nm}']
    L += ['  PIN VDD', '    USE POWER ;', '  END VDD', f'END {macro}', '']
    return '\n'.join(L)


def pins(scalar_ck=False, drop=None, flip=None):
    out = []
    for p_, (d_, n_) in PORTS.items():
        for i in range(n_):
            nm = p_ if (scalar_ck and p_ == 'ck') else f'{p_}[{i}]'
            if nm != drop:
                out.append((nm, ('OUTPUT' if d_ == 'input' else 'INPUT') if nm == flip else d_.upper()))
    return out


def table(d, lef_text, verdict='QUALIFIED', edit=False):
    d.mkdir(parents=True)
    (d / f'{MST}.lef').write_text(lef_text)
    for c in ('tt', 'ff', 'ss'):
        (d / f'{MST}_{c}.lib').write_text(f'library (x) {{\n  cell ({MST}) {{ }}\n}}\n')
    files = {k: dict(path=str(d / f), sha256=hashlib.sha256((d / f).read_bytes()).hexdigest())
             for k, f in [('lef', f'{MST}.lef')] + [(c, f'{MST}_{c}.lib') for c in ('tt', 'ff', 'ss')]}
    if edit:
        (d / f'{MST}_ss.lib').write_text('changed')
    (d / 'table.json').write_text(json.dumps(dict(schema=S.VIEW_BINDING_SCHEMA, bound={MST: dict(verdict=verdict, files=files)})))
    return str(d / 'table.json')


def load(tab):
    S.VIEW_BINDING = tab
    S._BOUND.clear()
    return S.bound_views()


def fails(tab, text):
    try:
        load(tab)
    except SystemExit as ex:
        assert text in str(ex), str(ex)
        return
    raise AssertionError('no hard error: ' + text)


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        assert load('none') == {}
        dflt = load(S.VIEW_BINDING_DEFAULT)                      # the committed table loads and verifies
        print('committed table:', len(dflt), 'bound masters')
        v = load(table(td / 'ok', lef(pins())))[MST]
        assert (v['w'], v['h']) == (15.12, 15.12) and len(v['pins']) == 32 and 'VDD' not in v['pins']
        assert S.bound_view_pin_faults(MST, v, PORTS) == []
        v = load(table(td / 'sck', lef(pins(scalar_ck=True))))[MST]
        assert S.bound_view_pin_faults(MST, v, PORTS) == []      # a 1-bit die port binds a scalar LEF pin
        v = load(table(td / 'drop', lef(pins(drop='o[7]'))))[MST]
        assert any('missing' in f for f in S.bound_view_pin_faults(MST, v, PORTS))
        v = load(table(td / 'extra', lef(pins() + [('scan_en', 'INPUT')])))[MST]
        assert any('no die port' in f for f in S.bound_view_pin_faults(MST, v, PORTS))
        v = load(table(td / 'flip', lef(pins(flip='i[2]'))))[MST]
        assert any('DIRECTION' in f for f in S.bound_view_pin_faults(MST, v, PORTS))
        fails(table(td / 'nq', lef(pins()), verdict='NOT_ESTABLISHED'), 'without a QUALIFIED verdict')
        fails(table(td / 'sha', lef(pins()), edit=True), 'sha256 differs')
        fails(table(td / 'name', lef(pins(), macro='dsfd_rly_15_NS')), 'defines MACRO')
        fails(str(td / 'absent.json'), 'not found')
    print('PASS test_view_binding')
    return 0


if __name__ == '__main__':
    sys.exit(main())
