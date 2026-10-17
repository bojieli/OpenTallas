"""Actual count-leaf contacts and die elaboration must agree at the boundary."""
from pathlib import Path
import copy
import json
import re
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


@pytest.mark.parametrize('name', G.PQCNT_MASTERS)
def test_pq_count_consumes_exported_contact_and_rejects_wrong_face(name, monkeypatch):
    rec = json.loads((G.ROOT / 'physical/s81_die_pins/v22_pq_cnt' / (name + '.json')).read_text())
    table = json.loads((G.ROOT / 'results/arch/s81_native_20261013/view_binding_closed_sdie_c26j.json').read_text())
    text = (G.ROOT / table['bound'][name]['files']['lef']['path']).read_text()
    wh = tuple(map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', text).groups()))
    view = dict(w=wh[0], h=wh[1], text=text)
    monkeypatch.setattr(G, 'bound_views', lambda: {name: view})
    ports = {p: ('input', spec['bits']) for p, spec in rec['ports'].items()}
    master = G.Q.Master(name, *wh, 3, 'actual count leaf')
    G._pqcnt_lef_physical_pins(master, ports, rec)
    exported = dict(re.findall(r'\n\s*PIN (\S+)\s*\n(.*?)\n\s*END \1', text, re.S))
    for p, (_, rects) in master.ports.items():
        for pin, layer, coords in rects:
            block = exported.get(pin, exported.get(pin.removesuffix('[0]')))
            assert block is not None, pin
            match = re.search(r'LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', block)
            assert (layer, coords) == (match[1], tuple(map(float, match.groups()[1:])))
    wrong = copy.deepcopy(rec)
    spec = next(iter(wrong['ports'].values()))
    if 'per_bit' in spec:
        spec['per_bit'][0][0] = {'N':'S','S':'N','W':'E','E':'W'}[spec['per_bit'][0][0]]
    else:
        spec['face'] = {'N':'S','S':'N','W':'E','E':'W'}[spec['face']]
    with pytest.raises(SystemExit, match='not on the assigned'):
        G._pqcnt_lef_physical_pins(master, ports, wrong)


def test_wfc_return_override_has_three_actual_clock_and_reset_entries(monkeypatch):
    monkeypatch.chdir(G.ROOT)
    assert G.wfc_return256_params() == {'WFC_RETURN256': 1}
    monkeypatch.setattr(G, 'WFC_RETURN256', True)
    monkeypatch.setattr(G, '_RTL_CLOCK_CACHE', {})
    entries = G.rtl_clock_reset_entries('dsfd_sp_vm')
    clocks = [p for group in entries['clock'].values() for p in group if p.startswith('ck_wfc_return_t')]
    resets = [p for group in entries['reset'].values() for p in group if p.startswith('rss_wfc_return_t')]
    assert clocks == [f'ck_wfc_return_t[{i}:{i}]' for i in range(3)]
    assert resets == [f'rss_wfc_return_t[{i}:{i}]' for i in range(3)]
