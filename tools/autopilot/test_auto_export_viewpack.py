"""AUTO-EXPORT step 5 (EXPLORER-STORE-R1): every exported sign-off is queued for its routed-layout pack, cut on its build host
under ot-run and published to the explorer store; at most VIEWPACK_PER_HOST cuts per host; failures retried once."""
import json, os, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_export as AE  # noqa: E402


def unit(el, host='epyc9', die='s81', kind='t', sha='a' * 64):
    return dict(die=die, element=el, kind=kind, host=host, odb='/srv/x/%s/6_final.odb' % el, odb_size=2_000_000_000, odb_sha=sha)


def test_node_id_matches_explorer_scheme():
    assert AE.view_pack_node(unit('col_h9__cl1')) == 's81.t.col_h9__cl1'
    assert AE.view_pack_node(unit('ot_core', kind='c')) == 's81.c.ot_core'
    assert AE.view_pack_node(unit('col_h9__cl1__a2_0130')) == 's81.t.col_h9__cl1'   # a re-sign is the same node


def test_queue_pending_and_retry(tmp_path):
    st = str(tmp_path)
    assert AE.queue_view_packs([unit('a', sha='1' * 64), unit('b', sha='2' * 64), dict(die='s81')], st) == 2
    assert sorted(j['node'] for j in AE.view_pack_pending(st)) == ['s81.t.a', 's81.t.b']
    with open(os.path.join(st, 'viewpack_done.jsonl'), 'a') as f:
        f.write(json.dumps(dict(node='s81.t.a', sha='1' * 64, ok=True)) + '\n')
        f.write(json.dumps(dict(node='s81.t.b', sha='2' * 64, ok=False)) + '\n')
    assert [j['node'] for j in AE.view_pack_pending(st)] == ['s81.t.b']          # one failure: retried
    with open(os.path.join(st, 'viewpack_done.jsonl'), 'a') as f:
        f.write(json.dumps(dict(node='s81.t.b', sha='2' * 64, ok=False)) + '\n')
    assert AE.view_pack_pending(st) == []                                          # two failures: left for the backfill
    AE.queue_view_packs([unit('a', sha='3' * 64)], st)                             # a newer record of a published node: cut again
    assert [j['sha'] for j in AE.view_pack_pending(st)] == ['3' * 64]


def test_cut_and_publish_commands():
    j = dict(node='s81.t.a', host='epyc9', odb='/srv/x/a b/6_final.odb', size=2_000_000_000, label='epyc9:/srv/x/a b/6_final.odb')
    run, pub, w, inc = AE.view_pack_cmds(j)
    assert run[:4] == ['ot-run', '--hosts', 'epyc9', '--dir'] and run[run.index('--mem') + 1] == '48'
    assert run[-3:-1] == ['bash', '-c'] and 'design_export.py cut --node s81.t.a' in run[-1] and "'/srv/x/a b/6_final.odb'" in run[-1]
    assert '--drop-raw' in run[-1] and '--no-timing' in run[-1]
    assert 'design_export.py publish --node s81.t.a' in pub and '$LV_STORE' in pub and inc.endswith('/incoming/s81.t.a')


def test_worker_caps_cuts_per_host(tmp_path):
    st = str(tmp_path)
    AE.queue_view_packs([unit('e%d' % i, host='epyc9', sha=str(i) * 64) for i in range(5)] + [unit('f', host='epyc7', sha='f' * 64)], st)
    live, peak, lk = {}, {}, threading.Lock()

    def one(j):
        with lk:
            live[j['host']] = live.get(j['host'], 0) + 1; peak[j['host']] = max(peak.get(j['host'], 0), live[j['host']])
        time.sleep(0.05)
        with lk:
            live[j['host']] -= 1
        return (j['node'] != 's81.t.e3'), 'published' if j['node'] != 's81.t.e3' else 'cut rc 1'
    assert AE.view_packs(state=st, one=one) == 0
    assert peak['epyc9'] == AE.VIEWPACK_PER_HOST and peak['epyc7'] == 1
    rows = [json.loads(l) for l in open(os.path.join(st, 'viewpack_done.jsonl'))]
    assert len(rows) == 6 and [r['node'] for r in rows if not r['ok']] == ['s81.t.e3']
    assert [j['node'] for j in AE.view_pack_pending(st)] == ['s81.t.e3']


def test_detached_worker_off_under_pytest():
    assert AE.start_view_packs() is None
