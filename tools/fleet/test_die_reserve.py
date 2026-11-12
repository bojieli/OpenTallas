"""DIE_RESERVE_1101 (FLOW-21, COORD 11-01 16:1x): bounded one-host reservation for a long-waiting die job."""
import json
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock
HERE = Path(__file__).parent
R = SourceFileLoader('rsv_reconcile', str(HERE / 'ot-heavy-reconcile')).load_module()
H = SourceFileLoader('rsv_hub', str(HERE / 'ot-reserve')).load_module()

W = dict(id='otrun-tolerant-swine-2623452-', pid=11, since=1000, mem=360, charge=252, cmd='bash build.sh')


def _file(tmp_path, monkeypatch, r):
    f = tmp_path / 'die_reserve.json'
    if r is not None:
        f.write_text(json.dumps(r))
    monkeypatch.setattr(R, 'RESERVE_FILE', str(f))
    monkeypatch.setattr(R, 'D', str(tmp_path))
    return f


def test_valid_reservation_kept(tmp_path, monkeypatch):
    _file(tmp_path, monkeypatch, dict(id=W['id'], at=5000, charge=252))
    with mock.patch.object(R, 'die_waiter_rows', return_value=[W]):
        assert R.reserve_active({}, now=5000 + 3600)['id'] == W['id']


def test_released_when_waiter_admitted(tmp_path, monkeypatch):
    f = _file(tmp_path, monkeypatch, dict(id=W['id'], at=5000, charge=252))
    with mock.patch.object(R, 'die_waiter_rows', return_value=[]):
        assert R.reserve_active({}, now=5600) is None
    assert not f.exists()
    assert 'DIE-RESERVE RELEASE' in (tmp_path / 'admit.log').read_text()
    assert 'admitted or gone' in (tmp_path / 'die_reserve.log').read_text()


def test_released_after_six_hours(tmp_path, monkeypatch):
    f = _file(tmp_path, monkeypatch, dict(id=W['id'], at=5000, charge=252))
    with mock.patch.object(R, 'die_waiter_rows', return_value=[W]):
        assert R.reserve_active({}, now=5000 + 6 * 3600 + 1) is None
    assert not f.exists() and 'expired after 6 h' in (tmp_path / 'admit.log').read_text()


def test_no_file_is_no_reservation(tmp_path, monkeypatch):
    _file(tmp_path, monkeypatch, None)
    assert R.reserve_active({}) is None


def test_reserve_set_writes_file_and_logs(tmp_path, monkeypatch):
    f = _file(tmp_path, monkeypatch, None)
    with mock.patch.object(R, 'die_waiter_rows', return_value=[W]):
        assert R.reserve_set(W['id'], {}) == 0
        assert R.reserve_set('otrun-x-1-', {}) == 1
    assert json.loads(f.read_text())['id'] == W['id']
    assert 'DIE-RESERVE RESERVE' in (tmp_path / 'admit.log').read_text()


def _gate(monkeypatch, me_die, rsv):
    for k, v in dict(classify=lambda a: 'c', sizes=lambda: {}, admit_size=lambda m, c, t=None, argv=None: None,
                     meminfo=lambda: (1007.0, 600.0), read_units=lambda: [],
                     books=lambda *a, **k: dict(pending=0.0, young=0.0, settled_floor=0.0),
                     floor_gb=lambda t: 100.0, admissible=lambda *a: 400.0, invariant=lambda *a: {}, inv_cap=lambda c, i: c,
                     die_admissible=lambda *a: 450.0, die_hold=lambda *a: 0, charged_growth=lambda b, t: 0.0,
                     inv_text=lambda i: 'inv', die_like=lambda a, c='', e=(): me_die,
                     reserve_active=lambda t, now=None: rsv).items():
        monkeypatch.setattr(R, k, v)
    monkeypatch.delenv('OT_HEAVY_PRIO', raising=False)


def test_gate_blocks_new_non_die_only(monkeypatch, capsys):
    rsv = dict(id=W['id'], at=5000, charge=252)
    _gate(monkeypatch, False, rsv)
    R.gate_locked(8, ['bash', 'kit.sh'])
    out = capsys.readouterr().out
    assert out.startswith('NO 8 ') and 'DIE-RESERVE: host reserved for die waiter' in out
    _gate(monkeypatch, True, rsv)                       # a die request is unchanged
    R.gate_locked(8, ['bash', 'die_grt.sh'])
    assert capsys.readouterr().out.startswith('OK 8 ')
    _gate(monkeypatch, False, None)                     # no reservation: admitted as before
    R.gate_locked(8, ['bash', 'kit.sh'])
    assert capsys.readouterr().out.startswith('OK 8 ')


def test_hub_reserves_oldest_waiter_over_60_min():
    now = 100000
    reports = {'localhost': dict(reserve=None, waiters=[dict(W, since=now - 7.5 * 3600)]),
               'intel1': dict(reserve=None, waiters=[dict(W, id='otrun-tolerant-swine-3160474-', since=now - 2 * 3600)]),
               'epyc2': dict(reserve=None, waiters=[dict(W, id='otrun-y-9-', since=now - 600)])}
    keep, rel, pick = H.decide(reports, {}, now)
    assert keep == [] and rel == [] and pick[0] == 'localhost' and pick[1]['id'] == W['id']
    # a waiter already reserved once (admitted or expired) is never reserved again; the next oldest is
    keep, rel, pick = H.decide(reports, {'localhost|' + W['id']: now - 60}, now)
    assert pick[0] == 'intel1'
    # nobody past 60 min: no reservation
    assert H.decide({'epyc2': reports['epyc2']}, {}, now)[2] is None


def test_hub_at_most_one_host():
    now = 100000
    reports = {'localhost': dict(reserve=dict(id='a', at=10), waiters=[dict(W, since=now - 9000)]),
               'intel1': dict(reserve=dict(id='b', at=20), waiters=[dict(W, id='b', since=now - 9000)])}
    keep, rel, pick = H.decide(reports, {}, now)
    assert [h for h, _ in keep] == ['localhost'] and rel == ['intel1'] and pick is None


def test_hub_tick_end_to_end(tmp_path, monkeypatch):
    now = 100000.0
    calls = []

    def fake(host, args, timeout=90):
        calls.append((host, args))
        if args == ['--die-waiters']:
            return 0, json.dumps(dict(reserve=None, waiters=[dict(W, since=now - 8 * 3600)] if host == 'localhost' else []))
        return 0, 'ok'
    monkeypatch.setattr(H, 'remote', fake)
    monkeypatch.setattr(H, 'STATE', str(tmp_path / 's.json'))
    monkeypatch.setattr(H, 'LOG', str(tmp_path / 'l.log'))
    monkeypatch.setattr(H.time, 'time', lambda: now)
    monkeypatch.setattr(H.sys, 'argv', ['ot-reserve'])
    assert H.main() == 0
    assert ('localhost', ['--reserve-set', W['id']]) in calls
    st = json.loads((tmp_path / 's.json').read_text())
    assert st['active'] == 'localhost|' + W['id'] and 'RESERVE localhost|' in (tmp_path / 'l.log').read_text()


def test_ot_run_passes_wait_since():
    src = (HERE / 'ot-run').read_text()
    assert 'OT_HEAVY_WAIT_SINCE={int(RUN_T0)}' in src


def test_retired_exact_dispatcher_not_generic_pinned_jobs(monkeypatch):
    body = 'DIES = [ physical/die_plan/hbm_arch/B2l/die_plan.json physical/die_plan/s81/die_plan.json ]'
    monkeypatch.setattr(R, 'rd', lambda p: body)
    command = 'export PATH=x; cd /srv/opentallas-scratch2/claude/die-ci/wt && python3 tools/die_plan/die_ci.py run --sha abc --mode nightly --g2 all --dies hbm'
    reason = R.reservation_ineligible(['bash', '-lc', command], '/tmp', {'OT_HEAVY_DISK_GB':'0'})
    assert 'retired nightly dispatcher' in reason
    assert R.reservation_ineligible(['bash', '-lc', command + ' --plan hbm=current.json'], '/tmp', {'OT_HEAVY_DISK_GB':'0'}) is None
    assert R.reservation_ineligible(['bash', '-lc', command + ' --plan=hbm=current.json'], '/tmp', {'OT_HEAVY_DISK_GB':'0'}) is None
    assert R.reservation_ineligible(['bash', '-lc', command.replace('/claude/die-ci/wt','/claude/valid-pinned/wt')], '/tmp', {'OT_HEAVY_DISK_GB':'0'}) is None
    monkeypatch.setattr(R, 'rd', lambda p: 'DIES = [ current_source_adapter ]')
    assert R.reservation_ineligible(['bash', '-lc', command], '/tmp', {'OT_HEAVY_DISK_GB':'0'}) is None


def test_impossible_declared_disk_not_reserved(monkeypatch):
    fake = type('Stat', (), {'f_bavail': 5, 'f_frsize': 1073741824})()
    monkeypatch.setattr(R.os, 'statvfs', lambda p: fake)
    assert 'exceeds actual free' in R.reservation_ineligible(['build'], '/scratch', {'OT_HEAVY_DISK_GB':'6'})
    assert R.reservation_ineligible(['build'], '/scratch', {'OT_HEAVY_DISK_GB':'5'}) is None


def test_ineligible_current_reservation_releases_without_job_stop(tmp_path, monkeypatch):
    f = _file(tmp_path, monkeypatch, dict(id=W['id'], at=5000, charge=252))
    with mock.patch.object(R, 'die_waiter_rows', return_value=[dict(W,reserve_eligible=False,reserve_reason='retired exact dispatcher')]):
        assert R.reserve_active({}, now=5500) is None
    assert not f.exists()
    assert 'reservation ineligible' in (tmp_path/'die_reserve.log').read_text()


def test_hub_skips_ineligible_but_keeps_normal_old_waiter():
    now=100000
    invalid=dict(W, since=1,reserve_eligible=False)
    valid=dict(W,id='valid',since=100,reserve_eligible=True)
    assert H.decide({'localhost':dict(reserve=None,waiters=[invalid,valid])},{},now)[2][1]['id']=='valid'
