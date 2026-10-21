"""Job-authoritative strict PG admission, generated policy and immutable shipping."""
import copy
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ref_tile as RT
import pre_route_gate as G
import source_binding as SB
HO = G.HO


def spec(strict=None):
    out = dict(name='pg_policy', top='top', kind='tile', sources=[], params={},
               macros=[], children=[], pins={'S': ['a'], 'N': ['b']},
               clock_port='ck', clock='cts', inter=[], route={}, reset_ports=[])
    if strict is not None:
        out['pg_strict'] = strict
    return out


def capture(tree, strict=False):
    with mock.patch.object(HO, 'main_head', return_value=None):
        return HO.capture_plan(tree, tree, pg_strict=strict)


def helpers(tree):
    for rel in HO.helper_paths(HO.HELPERS + HO.PG_HELPERS):
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('frozen input ' + rel + '\n')
        p.chmod(0o644)


def test_default_inventory_plan_and_generated_outputs_equal_original(tmp_path, monkeypatch):
    helpers(tmp_path)
    assert capture(tmp_path) == capture(tmp_path, False)
    assert 'pg_strict' not in capture(tmp_path)[0]
    assert not set(HO.helper_paths(HO.PG_HELPERS)) & set(HO.helper_paths())
    lc = {'rlayers': ['M2', 'M5'], 'pg_layer': 'M5'}
    absent, off = spec(), spec(False)
    assert RT.gen_env(absent, 'physical/test_pg', 21.6, 21.6, lc, []) == RT.gen_env(off, 'physical/test_pg', 21.6, 21.6, lc, [])
    assert RT.gen_job(absent, 'physical/test_pg', 'deadbeef', []) == RT.gen_job(off, 'physical/test_pg', 'deadbeef', [])
    assert RT.referenced_paths(absent, 'physical/test_pg') == RT.referenced_paths(off, 'physical/test_pg')
    monkeypatch.setenv('OT_PG_STRICT', '1')
    assert not HO.pg_strict(spec())
    assert G.ship_helpers(spec()) == G.SHIP_HELPERS


def test_actual_spec_generates_policy_freezes_and_ships_pg_inputs(tmp_path, monkeypatch):
    helpers(tmp_path)
    s = spec(True)
    lc = {'rlayers': ['M2', 'M5'], 'pg_layer': 'M5'}
    kit_env = RT.gen_env(s, 'physical/test_pg', 21.6, 21.6, lc, [])
    kit = tmp_path / 'kit.env'
    kit.write_text(kit_env)
    generated = RT.gen_job(s, 'physical/test_pg', 'deadbeef', [])
    assert generated['pg_strict'] is True
    assert HO.pg_strict(generated) is True
    actual = subprocess.check_output(['bash', '-c', 'unset OT_PG_STRICT; source "$1"; printf "%s" "$OT_PG_STRICT"', 'test', str(kit)], env={'PATH': '/usr/bin:/bin'})
    assert actual == b'1'
    plan, payloads = capture(tmp_path, HO.pg_strict(generated))
    HO.validate_pg_policy(plan, pg_strict=True)
    pg_paths = set(HO.helper_paths(HO.PG_HELPERS))
    assert pg_paths <= {r['path'] for r in plan['files']}
    assert set(RT.referenced_paths(s, 'physical/test_pg')) >= {p for p in pg_paths if p.endswith('binding.tcl') or p.endswith('bootstrap.tcl')}
    monkeypatch.setattr(G, 'DAEMON_TREE', tmp_path)
    monkeypatch.setattr(G, 'ROOT', tmp_path)
    archive = G.ship_tar([], payloads, {r['path']: r['mode'] for r in plan['files']}, spec=s)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
        shipped = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    assert set(shipped) == set(G.ship_helpers(s))
    assert pg_paths <= set(shipped)
    for row in plan['files']:
        if row['path'] in shipped:
            assert hashlib.sha256(shipped[row['path']]).hexdigest() == row['sha256']
    missing = tmp_path / HO.helper_paths(HO.PG_HELPERS)[0]
    missing.unlink()
    with pytest.raises(OSError):
        capture(tmp_path, True)


def test_frozen_policy_mutants_and_no_legacy_strict_fallback(tmp_path):
    helpers(tmp_path)
    default, _ = capture(tmp_path)
    strict, _ = capture(tmp_path, True)
    for invalid in (None, default):
        with pytest.raises(ValueError):
            HO.validate_pg_policy(invalid, pg_strict=True)
    with pytest.raises(ValueError):
        HO.validate_pg_policy(strict, pg_strict=False)
    removed = copy.deepcopy(strict)
    removed['files'] = removed['files'][1:]
    removed['content_sha256'] = HO.digest(removed['files'])
    with pytest.raises(ValueError):
        HO.validate_pg_policy(removed, pg_strict=True)
    flipped = dict(strict, pg_strict=False)
    for compare in (lambda a, b: HO.compare_plans(a, b), lambda a, b: HO.compare_plans_sanctioned(a, b, tmp_path)):
        assert not compare(strict, flipped)[0]
        assert not compare(flipped, strict)[0]
    binding = {'schema': SB.SCHEMA, 'route_overlay_plan': default}
    ok, reason = SB.validate(binding, tmp_path, tmp_path, pg_strict=True)
    assert not ok and 'strict PG policy' in reason
    assert default == capture(tmp_path)[0]


@pytest.mark.parametrize('value', [1, 0, 'true', 'false', None, [], {}])
def test_non_boolean_policy_refused(value, tmp_path):
    with pytest.raises(ValueError):
        HO.pg_strict({'pg_strict': value})
    with pytest.raises(ValueError):
        HO.capture_plan(tmp_path, tmp_path, paths=[], head='', pg_strict=value)


def test_strict_old_kit_and_job_spec_mismatch_refused(tmp_path):
    (tmp_path / 'kit.env').write_text('TOP=top\n')
    assert not G.check_pg_kit_policy(G.Gate(), tmp_path, spec(True), spec(True))
    (tmp_path / 'kit.env').write_text('TOP=top\nexport OT_PG_STRICT=1\n')
    assert G.check_pg_kit_policy(G.Gate(), tmp_path, spec(True), spec(True))
    assert not G.check_pg_kit_policy(G.Gate(), tmp_path, spec(True), spec(False))
    assert not G.check_pg_kit_policy(G.Gate(), tmp_path, spec(False), spec(False))
