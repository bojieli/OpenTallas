from tools import w13_owner_watch as watch


def test_duplicate_runnable_supervisor_is_conflict_but_parked_is_not(tmp_path, monkeypatch):
    for pid in [1, 2]:
        p = tmp_path / str(pid)
        p.mkdir()
        (p / 'cmdline').write_bytes(b'python3\0/tmp/w13_chain_successor.py\0config\0')
    handles = {1: {'pid': 1, 'start_ticks': 'a', 'state': 'S'}, 2: {'pid': 2, 'start_ticks': 'b', 'state': 'T'}}
    monkeypatch.setattr(watch, 'identity', lambda pid: handles.get(pid))
    coord = {'active_successor': handles[1], 'parked_predecessors': [handles[2].copy()]}
    assert not watch.conflicts(coord, tmp_path)
    handles[2]['state'] = 'S'
    reasons = {r['reason'] for r in watch.conflicts(coord, tmp_path)}
    assert reasons == {'other_runnable_supervisor', 'parked_predecessor_changed_or_resumed'}


def test_reused_authorized_pid_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, 'identity', lambda pid: {'pid': pid, 'start_ticks': 'new', 'state': 'S'})
    assert watch.conflicts({'active_successor': {'pid': 1, 'start_ticks': 'old'}}, tmp_path)[0]['reason'] == 'authorized_supervisor_absent_or_reused'
