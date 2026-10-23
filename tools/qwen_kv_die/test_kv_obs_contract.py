"""FT-KV 10-23: OT_KV_OBS_CONTRACT lowers blanket abstract OBS to the kit layer cap; default byte-identical."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qwen_rom_fulldie as F


def _mk(name, w=390.936, h=358.536, top=7):
    m = F.Master(name, w, h, top, 'test')
    m.face('a', 8, 'W', 'M4', h / 2, 1)
    m.face('b', 8, 'N', 'M5', w / 2, 1)
    return m


def _layers(txt):
    obs = txt.split('  OBS', 1)[1]
    return [ln.split()[1] for ln in obs.splitlines() if ln.strip().startswith('LAYER')]


def test_default_unchanged_and_contract():
    import kv_die
    base = _mk('qkd_kvs_pc')
    t0, _ = F.lef_text(base, 1, {})
    assert _layers(t0) == [f'M{i}' for i in range(1, 8)]
    M = {'qkd_kvs_pc': _mk('qkd_kvs_pc'), 'qkd_ectlk': _mk('qkd_ectlk', 725.736, 261.336), 'other': _mk('other')}
    kv_die.apply_obs_contract(M)
    t1, _ = F.lef_text(M['qkd_kvs_pc'], 1, {})
    assert _layers(t1) == ['M1', 'M2', 'M3', 'M4', 'M5']
    t2, _ = F.lef_text(M['qkd_ectlk'], 1, {})
    ls = _layers(t2)
    assert ls[:6] == [f'M{i}' for i in range(1, 7)] and set(ls[6:]) == {'M7'} and len(ls) - 6 == 134
    t3, _ = F.lef_text(M['other'], 1, {})
    assert t3 == F.lef_text(_mk('other'), 1, {})[0]
    # a die pin on M6 of an M5-contract master is refused (never hidden under a lowered OBS)
    bad = {'qkd_kvs_pc': _mk('qkd_kvs_pc')}
    bad['qkd_kvs_pc'].face('c', 4, 'E', 'M6', 100.0, 1)
    try:
        kv_die.apply_obs_contract(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('M6 pin under M5 contract not refused')


if __name__ == '__main__':
    test_default_unchanged_and_contract()
    print('PASS')
