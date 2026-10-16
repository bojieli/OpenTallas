"""Late-created frames must obey the same immutable-view and pin-layer rules."""
import json
from types import SimpleNamespace
import pytest
import qwen_rom_fulldie_b3r2 as source
from qwen_kv_die import tp8b_v5


def apply(tmp_path, monkeypatch, grant, closed=False):
    path = tmp_path / 'grant.json'
    path.write_text(json.dumps({'late_masters': {'fixture': {'p': grant}}}))
    monkeypatch.setenv('OT_SPLIT_PIN_GRANT', str(path))
    monkeypatch.setattr(tp8b_v5, 'VIEWS', {'fixture': 'real-view'} if closed else {})
    m = SimpleNamespace(w=20, h=30, ports={'p': ('face', 2, 'W', 'M4', 10, 1)})
    v = SimpleNamespace(masters=lambda *args: {'fixture': m})
    source._late_pin_grant(v)
    return v.masters({}, 1, None)['fixture']


def valid():
    return {'face': 'W', 'positions': [5, 6], 'layers': ['M4', 'M6']}


def test_actual_per_bit_layers_preserved(tmp_path, monkeypatch):
    m = apply(tmp_path, monkeypatch, valid())
    assert m.ports['p'][4] == [5, 6]
    assert m.view_pin_layers['p'] == ['M4', 'M6']


def test_closed_view_cannot_be_overridden(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='closed view'):
        apply(tmp_path, monkeypatch, valid(), closed=True)


@pytest.mark.parametrize('field,value', [('face','X'), ('layers',['M4']),
    ('layers',[]), ('layers',['M5','M5']), ('positions',[5]), ('positions',[-1,6])])
def test_malformed_late_grant_refused(tmp_path, monkeypatch, field, value):
    g = valid(); g[field] = value
    with pytest.raises(ValueError):
        apply(tmp_path, monkeypatch, g)
