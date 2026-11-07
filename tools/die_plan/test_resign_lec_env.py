"""FLOW-CLASS-25 11-06 (COORD 18:0x (3b)): resign.py (and auto_resign, whose driver it is) passes OT_LEC_PARITY_TERMS
into the LEC container when the caller's env or the kit's config.mk sets it."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resign


def kit(tmp_path, cfg=None):
    k = tmp_path / 'kit'
    base = k / 'run' / 'results' / 'asap7' / 'hc_x' / 'base'
    base.mkdir(parents=True)
    (base / '6_final.v').write_text('module x; endmodule\n')
    if cfg is not None:
        (k / 'config.mk').write_text(cfg)
    return str(k)


def lec_cmd(k, monkeypatch, env=None):
    monkeypatch.delenv('OT_LEC_PARITY_TERMS', raising=False)
    if env is not None:
        monkeypatch.setenv('OT_LEC_PARITY_TERMS', env)
    so, lec = resign.run_cmds(k, k + '/run', k, k + '/out', 'img', 'hc_x', superset=True)
    return lec


def test_default_unchanged(tmp_path, monkeypatch):
    lec = lec_cmd(kit(tmp_path, 'export DESIGN_NAME = hc_x\n'), monkeypatch)
    assert not any('OT_LEC_PARITY_TERMS' in a for a in lec)
    assert 'OT_LEC_SUPERSET_VEC=1' in lec
    assert not any('OT_LEC_PARITY_TERMS' in a for a in lec_cmd(kit(tmp_path / 'n'), monkeypatch))   # no config.mk


def test_kit_config_sets_it(tmp_path, monkeypatch):
    k = kit(tmp_path, 'export DESIGN_NAME = hc_x\noverride export OT_LEC_PARITY_TERMS = 800  # q3 CRC\n')
    lec = lec_cmd(k, monkeypatch)
    i = lec.index('OT_LEC_PARITY_TERMS=800')
    assert lec[i - 1] == '-e' and i < lec.index('img')        # a docker option, before the image


def test_env_wins_over_kit(tmp_path, monkeypatch):
    k = kit(tmp_path, 'export OT_LEC_PARITY_TERMS = 800\n')
    lec = lec_cmd(k, monkeypatch, env='1024')
    assert 'OT_LEC_PARITY_TERMS=1024' in lec and 'OT_LEC_PARITY_TERMS=800' not in lec


def test_bad_value_refused(tmp_path, monkeypatch):
    k = kit(tmp_path, 'export OT_LEC_PARITY_TERMS = lots\n')
    with pytest.raises(resign.ResignError):
        lec_cmd(k, monkeypatch)


def test_dry_run_shows_it(tmp_path, monkeypatch, capsys):
    k = kit(tmp_path, 'export OT_LEC_PARITY_TERMS = 800\n')
    monkeypatch.delenv('OT_LEC_PARITY_TERMS', raising=False)
    monkeypatch.setattr(resign, 'tag_commit', lambda *a: 'x')
    monkeypatch.setattr(resign, 'check_tools', lambda *a: None)
    monkeypatch.setattr(resign, 'export_clock_family', lambda *a: 'present')
    rc = resign.main(['run', '--kit', k, '--tag', 'flow-20261106-de-hbm', '--tools', k, '--out', k + '/out',
                      '--auto', '--dry-run'])
    assert rc == 0 and '-e OT_LEC_PARITY_TERMS=800' in capsys.readouterr().out
