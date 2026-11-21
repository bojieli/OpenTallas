"""cland_clock_contract (KV-PLAN-R2 11-20): census session rewrite + clock_contract.json that core_clock_contract.load accepts.
    python3 -m pytest -q tools/die_plan/test_cland_clock_contract.py"""
import json

import pytest

import cland_clock_contract as K
import core_clock_contract as CC

LIB = 'library (x) {\n cell ("kv_cland_t") {\n  pin (clk) { clock : true; direction : input; }\n  pin (fclk) { clock : true; direction : input; }\n }\n}\n'


def _kit(tmp_path, mean_tt=10.0):
    kit, out = tmp_path / 'kit', tmp_path / 'out'
    (kit / 'signoff').mkdir(parents=True)
    rec = dict(verdict='SIGNED', corners={c: dict(insertion_pinflops=dict(n=2, mean=m)) for c, m in (('tt', mean_tt), ('ff', 8.0))})
    (kit / 'signoff' / 'signoff.json').write_text(json.dumps(rec))
    logs = {'tt': ['SO_CK 1 9.00 clk', 'SO_CK 1 11.00 clk', 'SO_CK 0 50.00 clk', 'MK_FCK 1 100.00 fclk', 'MK_FCK 1 104.00 fclk',
                   'MK_FCK 0 7.00 fclk', 'MK_DONE 1'],
            'ff': ['SO_CK 1 7.00 clk', 'SO_CK 1 9.00 clk', 'MK_FCK 1 80.00 fclk', 'MK_DONE 1']}
    for c, ls in logs.items():
        (out / c).mkdir(parents=True)
        (out / c / 'sta.log').write_text('\n'.join(ls) + '\n')
    vd = tmp_path / 'view'
    vd.mkdir()
    (vd / 'kv_cland_t_tt.lib').write_text(LIB)
    return kit, out, vd


def test_session_inserts_census_before_exit():
    s = K.census_session('read_db /base/6_final.odb\nso DONE 1\nexit\n')
    assert s.startswith('read_db /base/6_final.odb\nso DONE 1\n') and s.endswith('MK_DONE 1"\nexit\n') and s.count('\nexit\n') == 1
    with pytest.raises(ValueError):
        K.census_session('so DONE 1\n')


def test_write_contract_loads_per_pin(tmp_path):
    kit, out, vd = _kit(tmp_path)
    doc = K.write(kit, out, vd / 'kv_cland_t_tt.lib')
    assert doc['pins']['clk']['tt']['n'] == 2 and doc['pins']['fclk']['tt'] == dict(
        mean_ps=102.0, n=2, min_ps=100.0, max_ps=104.0, basis='pin_register_mean', source=doc['pins']['fclk']['tt']['source'])
    (vd / 'clock_contract.json').write_text((out / 'clock_contract.json').read_text())
    got = CC.load(dict(inst='u', module='kv_cland_t', lib=str(vd / 'kv_cland_t_tt.lib')), require_signed=True)
    assert got['fclk']['corners']['ff']['mean_ps'] == 80.0 and got['clk']['signed'] is True


def test_clk_census_must_equal_signoff(tmp_path):
    kit, out, vd = _kit(tmp_path, mean_tt=12.0)
    with pytest.raises(ValueError, match='insertion_pinflops'):
        K.write(kit, out, vd / 'kv_cland_t_tt.lib')
