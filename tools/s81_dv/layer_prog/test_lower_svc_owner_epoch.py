"""lower_svc.py CLI --owner-epoch: default 0 (identity-on bench of record), 'none' = identity-off images."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lower_svc as L


def _run(monkeypatch, tmp_path, extra):
    seen = []

    def fake_build(fx, sched=None, die=None, **kw):
        seen.append(kw.get('owner_epoch', 'MISSING'))
        return object(), None

    monkeypatch.setattr(L, 'build', fake_build)
    monkeypatch.setattr(L, 'bench_image', lambda job, s, out: dict(go=0, pv_first=0, done_w=0, done_e=0, frames={}, pio=0))
    L.main(['--fixtures', 'x', '--out', str(tmp_path), '--pio-safe', '5'] + extra)
    return seen


def test_default_owner_epoch_zero(monkeypatch, tmp_path):
    seen = _run(monkeypatch, tmp_path, [])
    assert seen and all(v == 0 for v in seen)


def test_owner_epoch_none_and_value(monkeypatch, tmp_path):
    assert set(_run(monkeypatch, tmp_path, ['--owner-epoch', 'none'])) == {None}
    assert set(_run(monkeypatch, tmp_path, ['--owner-epoch', '2'])) == {2}


def test_cfg_spec_owner_sets_valid_bit():
    spec = L.cfg_spec(owner=(1 << 18) | (L.USER << 8) | 3, tag=3)
    assert spec >> 53 & 1 and (spec >> 33) & 0xfffff == (1 << 18) | (L.USER << 8) | 3
