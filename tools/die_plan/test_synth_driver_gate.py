import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth_driver_gate as g

LOG = """Warning: Wire top.\\w_core_native_cmd [376] is used but has no driver.
Warning: Wire top.\\w_core_cmd [5] is used but has no driver.
Warning: Wire top.\\w_core_cmd [5] is used but has no driver.
Warning: Wire top.\\spare_tie is used but has no driver.
Found and reported 3 problems.
"""
CLEAN = 'Found and reported 0 problems.\n'


def kit(tmp_path, log=LOG, exc=None):
    d = tmp_path / 'run/logs/asap7/top/base'
    d.mkdir(parents=True)
    if log is not None:
        (d / '1_2_yosys.log').write_text(log)
    if exc is not None:
        (tmp_path / 'undriven_exceptions.json').write_text(json.dumps(exc))
    return tmp_path


def test_scan_dedups_and_normalises():
    assert g.scan(LOG) == ['top.spare_tie', 'top.w_core_cmd[5]', 'top.w_core_native_cmd[376]']


def test_undriven_fails_and_lists(tmp_path, capsys):
    k = kit(tmp_path)
    assert g.main([str(k), '--out', str(k / 'r.json')]) == 1
    r = json.loads((k / 'r.json').read_text())
    assert r['verdict'] == 'FAIL' and r['n_undriven'] == 3
    assert 'NO DRIVER top.w_core_cmd[5]' in capsys.readouterr().out


def test_clean_log_passes(tmp_path):
    assert g.main([str(kit(tmp_path, log=CLEAN))]) == 0


def test_no_log_is_not_run(tmp_path):
    assert g.main([str(kit(tmp_path, log=None))]) == 2


def test_declared_exception_waives_only_that_net(tmp_path):
    k = kit(tmp_path, exc=dict(exceptions=[dict(net='spare_tie', kind='tied', plan='bind_r8', reason='declared tie')]))
    rep = g.gate(g.find_logs(k), *g.load_exceptions(k / 'undriven_exceptions.json'))
    assert rep['verdict'] == 'FAIL' and rep['n_undriven'] == 2 and rep['waived'][0]['exception']['kind'] == 'tied'


def test_all_waived_passes(tmp_path):
    k = kit(tmp_path, exc=dict(exceptions=[dict(net='*', kind='dead', plan='p')]))
    assert g.main([str(k)]) == 0


def test_exception_without_kind_or_plan_is_itself_a_fail(tmp_path):
    k = kit(tmp_path, log=CLEAN, exc=dict(exceptions=[dict(net='x', kind='whatever')]))
    assert g.main([str(k)]) == 1


def test_kv_kit_runs_gate_after_synth_and_gen_copies_it():
    root = Path(__file__).resolve().parents[2] / 'physical/die_plan/qwen_kvsys/cores/harden'
    sh = (root / 'run_kit_kv.sh').read_text()
    assert sh.index('\\$M synth; rc=') < sh.index('synth_driver_gate.py /work') < sh.index('replica_check.py --expect')
    assert 'synth_driver_gate.py", kd / "synth_driver_gate.py"' in (root / 'gen_core_kit_kv.py').read_text()
