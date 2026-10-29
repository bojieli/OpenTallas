"""Core obligations need actual parent hold paths, every input, and the same routed view."""
import copy
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import io_hold_parent as parent
import io_hold_qualification as Q
from test_io_hold import _plan, _sta


def core_sta():
    sta = _sta(5)
    sta['instances']['pfb'] = 'cfg7'
    sta['view_evidence']['cfg7'] = copy.deepcopy(next(iter(sta['view_evidence'].values())))
    return sta


def test_core_scope_from_actual_plan_and_receiver_master():
    p = _plan()
    budget = Q.core_kit_budget(p.raw, 'cfg7', 'fb')
    assert budget['die'] == p.name
    assert budget['type'] == 'cfg7' and budget['parent_type'] == 'fb'
    assert budget['io_hold']['plan_sha256'] == Q.plan_digest(p.raw)


def test_core_parent_covers_all_requested_inputs_with_real_views():
    r = parent.check(_plan(), core_sta(), core_receiver='pfb', core_type='cfg7', core_ports=['x_i', 'z_i'])
    assert r['verdict'] == 'PASS' and r['counts']['a_ports'] == 2
    assert {q['dst_type'] for q in r['ports']} == {'cfg7'}
    assert all(q['receiver_netlist_sha256'] == 'fixture' for q in r['ports'])


def test_missing_core_port_and_wrong_master_never_pass():
    for mutation in ['missing', 'wrong_master', 'budget_view', 'hold_fail']:
        sta = core_sta()
        ports = ['x_i', 'z_i']
        if mutation == 'missing': ports.append('q6')
        if mutation == 'wrong_master': sta['instances']['pfb'] = 'other'
        if mutation == 'budget_view': sta['view_evidence']['cfg7']['kind'] = 'budget'
        if mutation == 'hold_fail': sta['corners']['FF']['seams']['pfa->pfb/x_i']['min']['worst'] = -1
        r = parent.check(_plan(), sta, core_receiver='pfb', core_type='cfg7', core_ports=ports)
        assert r['verdict'] != 'PASS', mutation


def test_core_receipt_cli_rejects_stale_plan_and_keeps_missing_port(tmp_path):
    p = _plan()
    kd = tmp_path/'kit'; kd.mkdir()
    (tmp_path/'plan.json').write_text(json.dumps(p.raw))
    (tmp_path/'sta.json').write_text(json.dumps(core_sta()))
    budget = Q.core_kit_budget(p.raw, 'cfg7', 'fb')
    (kd/'budget.json').write_text(json.dumps(budget))
    (kd/'sdc_lint.json').write_text(json.dumps(dict(hold_in_min_ports_ps={'x_i': 12.5, 'z_i': 12.5})))
    cmd = [sys.executable, str(Path(parent.__file__)), str(tmp_path/'plan.json'), str(tmp_path/'sta.json'),
           '--core-instance', 'pfb', '--core-kit', str(kd), '--out', str(tmp_path/'receipt.json')]
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert json.loads((tmp_path/'receipt.json').read_text())['qualification']['complete']
    budget['io_hold']['plan_sha256'] = 'stale'
    (kd/'budget.json').write_text(json.dumps(budget))
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 2 and 'matching option-A die/plan metadata' in run.stderr
