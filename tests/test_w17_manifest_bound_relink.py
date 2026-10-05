"""Pure additive image binding and native-only approval checks; no Docker run."""
import copy
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w17_manifest_bound_relink_plan as new
import w17_existing_port_relink_plan as old
import run_w17_manifest_bound_native_relink as runner


def local():
    evidence = ROOT / new.identity.EVIDENCE
    image = json.loads((evidence / 'local_inspect.json').read_bytes())[0]
    raw = (evidence / 'local_config.raw.json').read_bytes()
    return image, raw


def test_compile_inputs_and_caps_preserved_only_explicit_image_binding_added():
    a, b = old.build(ROOT), new.build(ROOT)
    for key in ('compiler_argv', 'input_sha256', 'input_bytes', 'caps', 'source_commit'):
        assert a[key] == b[key]
    assert b['image'] == new.identity.CONFIG
    assert b['image_binding']['expected_OCI_manifest'] == a['image']
    assert not b['runtime_allowed'] and not b['execution_allowed']
    assert not b['owner_cancellation_selected'] and b['full_frontend_runs'] == 0
    assert [new.identity.MANIFEST if x == new.identity.CONFIG else x
            for x in b['future_container_argv']] == a['future_container_argv']


def test_live_metadata_binding_is_explicit_not_alias_relabel():
    image, raw = local()
    result = new.validate_local_identity(new.build(ROOT), image, raw, 'overlay2')
    assert result['OCI_manifest'] != result['loaded_local_ID']
    assert result['config_SHA'] == result['loaded_local_ID']
    assert not result['retagged']


@pytest.mark.parametrize('mutation', ['image_ID', 'config_bytes', 'diff_order', 'config_default', 'store'])
def test_live_mismatch_rejected(mutation):
    image, raw = local(); driver = 'overlay2'
    if mutation == 'image_ID':
        image['Id'] = new.identity.MANIFEST
    elif mutation == 'config_bytes':
        raw += b' '
    elif mutation == 'diff_order':
        image['RootFS']['Layers'].reverse()
    elif mutation == 'config_default':
        image['Config']['Entrypoint'] = ['/unexpected']
    else:
        driver = 'overlayfs'
    with pytest.raises(ValueError):
        new.validate_local_identity(new.build(ROOT), image, raw, driver)


def test_old_GO_rejected_before_any_input_or_Docker_access(tmp_path, monkeypatch):
    plan = tmp_path / 'plan.json'; plan.write_text(json.dumps(new.build(ROOT)))
    go = tmp_path / 'GO.json'
    go.write_text(json.dumps(dict(schema='w17.existing_public_ports.relink_GO.v1',
                                  scope='NATIVE_RELINK_ONLY', plan_sha256=runner.sha(plan),
                                  source_commit=old.build(ROOT)['source_commit'],
                                  execution_allowed=True, runtime_allowed=False)))
    def forbidden(*args, **kwargs):
        raise AssertionError('No external invocation before GO')
    monkeypatch.setattr(runner.subprocess, 'check_output', forbidden)
    with pytest.raises(ValueError, match='GO'):
        runner.validate(plan, go, tmp_path / 'missing-bundle')


def test_GO_cannot_grant_runtime_or_omit_binding(tmp_path):
    p = new.build(ROOT)
    plan = tmp_path / 'plan.json'; plan.write_text(json.dumps(p))
    good = dict(schema=new.GO_SCHEMA, scope='NATIVE_RELINK_ONLY',
                plan_sha256=runner.sha(plan), source_commit=p['source_commit'],
                image_binding=p['image_binding'], execution_allowed=True, runtime_allowed=False)
    for change in ({'runtime_allowed': True}, {'image_binding': {}}, {'execution_allowed': False}):
        g = tmp_path / 'GO.json'; g.write_text(json.dumps({**good, **change}))
        with pytest.raises(ValueError, match='GO'):
            runner.validate(plan, g, tmp_path / 'missing-bundle')


def test_explicit_GO_reaches_enrolled_input_gate_and_rejects_bad_CPU_lease(tmp_path):
    p = new.build(ROOT)
    plan = tmp_path / 'plan.json'; plan.write_text(json.dumps(p))
    tools = ['tools/run_w17_manifest_bound_native_relink.py',
             'tools/w17_manifest_bound_relink_plan.py', 'tools/check_w17_pinned_image_identity.py']
    good = dict(schema=new.GO_SCHEMA, scope='NATIVE_RELINK_ONLY',
                plan_sha256=runner.sha(plan), source_commit=p['source_commit'],
                image_binding=p['image_binding'], execution_allowed=True, runtime_allowed=False,
                tool_sha256={x: runner.sha(ROOT / x) for x in tools},
                host_CPU_ids=sorted(os.sched_getaffinity(0))[:2])
    go = tmp_path / 'GO.json'; go.write_text(json.dumps(good))
    with pytest.raises(ValueError, match='relocated input pin'):
        runner.validate(plan, go, tmp_path / 'missing-bundle')
    for cpus in ([True, 1], [0, 0], [0], [-1, 0]):
        go.write_text(json.dumps({**good, 'host_CPU_ids': cpus}))
        with pytest.raises(ValueError, match='twoCPU'):
            runner.validate(plan, go, tmp_path / 'missing-bundle')
