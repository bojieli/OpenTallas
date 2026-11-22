"""FLOW-FLEET-R1 11-22: a scan drain never delays a fresh sign-off (spools first, spools re-polled while the scan runs), and an autopilot
closed relocation whose record names another host is exported (dedup stays by ODB sha256)."""
import argparse, json, os, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'die_plan'))
import auto_export as AE  # noqa: E402


def unit(name, via):
    return dict(host='h1', odb='/k/%s/base/6_final.odb' % name, signoff='/k/%s/signoff.json' % name, files=[('/k/%s/base' % name, '6_final.odb')], via=via)


def test_spools_drain_before_and_during_a_slow_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(AE, 'STATE', str(tmp_path))
    monkeypatch.setattr(AE, 'SPOOL_POLL_S', 0.05)
    for f in ('write_guard_exported', 'save_ledger'):
        monkeypatch.setattr(AE, f, lambda *a, **k: None)
    fin = []
    monkeypatch.setattr(AE, 'finish', lambda L, have: fin.append(1))
    monkeypatch.setattr(AE, 'load_ledger', lambda: dict(units={}, last_scan=0))
    monkeypatch.setattr(AE, 'agi_index', lambda: [])
    monkeypatch.setattr(AE, 'infer', lambda u, rows: ('s81', u['odb'].split('/')[2], 't', 'hint'))
    monkeypatch.setattr(AE, 'probe', lambda h, mode, arg, timeout=0: [{p: ('sha-' + p, 10) for p in arg['paths']}])
    exported, release = [], threading.Event()
    monkeypatch.setattr(AE, 'export_agi_meta', lambda u: exported.append((u['element'], u['via'])))
    spools = [[unit('fresh1', 'spool')], [unit('fresh1', 'spool'), unit('fresh2', 'spool')]]

    def collect(hosts, scan, spool=True):
        if scan:
            assert not spool
            release.wait(10)                      # the slow scan
            return [unit('old', 'scan')]
        got = spools[0] if len(spools) == 1 else spools.pop(0)
        if exported and len(spools) == 1:
            release.set()                         # the scan ends only after the second spool unit went out
        return got
    monkeypatch.setattr(AE, 'collect', collect)
    a = argparse.Namespace(hosts='h1', evidence=False, scan=True, list_only=False, budget_s=60)
    t0 = time.time()
    assert AE.drain(a) == 0
    assert exported == [('fresh1', 'spool'), ('fresh2', 'spool'), ('old', 'scan')]
    assert time.time() - t0 < 10
    assert len(fin) >= 3          # start + every export + the spool re-poll while the scan ran


def test_probe_exports_autopilot_closed_copy_of_another_host(tmp_path):
    home = tmp_path / 'home'
    env = dict(os.environ, HOME=str(home))
    for rel in ('autopilot/closed/qwen_compute/sle_x__abc', 'lane/copy_of_x'):
        d = tmp_path / rel
        (d / 'base').mkdir(parents=True)
        (d / 'base' / '6_final.odb').write_bytes(b'\0' * (2 << 20))
        (d / 'kit' / 'signoff').mkdir(parents=True)
        (d / 'kit' / 'signoff' / 'signoff.json').write_text(json.dumps(dict(name='x', generated='2026-11-21T12:00:00+00:00', host='some-other-host',
                                                                         profile='minimal', verdict='SIGNED', inputs=dict(odb='/gone/6_final.odb'))))
    r = subprocess.run([sys.executable, '-I', '-', 'scan', json.dumps(dict(hours=1, roots=[str(tmp_path)]))], input=AE.PROBE, text=True,
                       capture_output=True, env=env, check=True)
    got = {Path(u['signoff']).parts[-4]: u for u in (json.loads(l) for l in r.stdout.splitlines() if l.startswith('{'))}
    closed = [u for k, u in got.items() if 'sle_x__abc' in u['signoff']]
    assert closed and 'err' not in closed[0] and closed[0]['copy_of'] == 'some-other-host'
    assert closed[0]['odb'].endswith('sle_x__abc/base/6_final.odb')
    other = [u for u in got.values() if 'copy_of_x' in u['signoff']]
    assert not other or 'record of host' in other[0].get('err', '')
