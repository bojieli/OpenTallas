"""Fresh RLIMIT relink preparation; no container/compiler/RTL execution."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w17_rlimit_bound_relink_plan as new
import w17_manifest_bound_relink_plan as previous
import run_w17_rlimit_bound_native_relink as runner


def test_exact_native_inputs_caps_and_image_preserved():
    old, plan = previous.build(ROOT), new.build(ROOT)
    for name in ('compiler_argv', 'input_sha256', 'input_bytes', 'caps', 'image_binding', 'image'):
        assert plan[name] == old[name]
    assert not plan['runtime_allowed'] and not plan['execution_allowed']
    assert plan['AS_enforcement']['bytes'] == 4 << 30
    assert plan['AS_enforcement']['entry_sha256'] == runner.sha(ROOT / new.ENTRY)


def test_AS_moves_to_source_bound_readonly_entry_without_cap_relaxation():
    plan = new.build(ROOT); cmd = plan['future_container_argv']
    assert not any(x.startswith('as=') for x in cmd)
    assert cmd[cmd.index('--memory') + 1] == '4g'
    assert cmd[cmd.index('--memory-swap') + 1] == '4g'
    assert 'fsize=2147483648:2147483648' in cmd
    assert 'VERIFIED_CAP_ENTRY:/launcher/entry.py:ro' in cmd
    i = cmd.index(plan['image'])
    assert cmd[i+1:i+3] == ['python3', '/launcher/entry.py']
    assert cmd[i+3:] == plan['compiler_argv']


@pytest.mark.parametrize('schema', ['w17.existing_public_ports.relink_GO.v1', previous.GO_SCHEMA])
def test_old_GO_rejected_even_if_planhash_updated(tmp_path, schema):
    plan = new.build(ROOT); pp = tmp_path / 'plan.json'; pp.write_text(json.dumps(plan))
    gp = tmp_path / 'GO.json'
    gp.write_text(json.dumps(dict(schema=schema, scope='NATIVE_RELINK_ONLY',
                                plan_sha256=runner.sha(pp), source_commit=plan['source_commit'],
                                image_binding=plan['image_binding'], execution_allowed=True,
                                runtime_allowed=False)))
    with pytest.raises(ValueError, match='GO'):
        runner.validate(pp, gp, tmp_path / 'absent')


def test_unknown_cap_or_entry_not_accepted_as_same_plan(tmp_path):
    plan = new.build(ROOT); plan['AS_enforcement']['bytes'] = 8 << 30
    pp = tmp_path / 'plan.json'; pp.write_text(json.dumps(plan))
    gp = tmp_path / 'GO.json'; gp.write_text('{}')
    with pytest.raises(ValueError, match='exact enrolled'):
        runner.validate(pp, gp, tmp_path / 'absent')


def test_entry_fails_before_compiler_on_non_native_command(monkeypatch):
    import w17_relink_rlimit_entry as entry
    def forbidden():
        raise AssertionError('cap setup must not start for a runtime command')
    monkeypatch.setattr(entry, 'enforce_limits', forbidden)
    with pytest.raises(ValueError, match='native compiler'):
        entry.main(['/output/v41_existing_port_trace'])
