#!/usr/bin/env python3
"""plan_pin_change.py (COUNT-ARCHIVE-2 11-10, COORD): advisory list of COUNTED designs whose plan pin table changes,
tracked per die in the hourly count and posted to the die owner.  Run: python3 -m pytest -q test_plan_pin_change.py"""
import gzip, json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import plan_pin_change as C
import release_tree_plan as R


def pins(n, dy=0.0, layer='M4'):
    return [dict(name='d[%d]' % i, layer=layer, x=0.096, y=round(2.0 + 0.144 * i + dy, 4)) for i in range(n)] + \
           [dict(name='clk', layer='M5', x=10.0, y=20.0)]


def plan(cores):
    T = {'t%d' % i: dict(hard_cores=[c]) for i, c in enumerate(cores)}
    return dict(partition_types=T, partitions=[dict(name='p%d' % i, type='t%d' % i) for i in range(len(cores))])


def core(m, pf, outline=(100.0, 50.0)):
    return dict(module=m, outline_um=list(outline), pins_file=pf, inst='u_' + m)


def designs(cores, files):
    return R.plan_designs(plan(cores), '/nonexistent', read=lambda f: files[f])


def test_diff_rows_classes_and_tolerance():
    a = {'a': ('M4', 0, 0), 'b': ('M4', 0, 0), 'c': ('M4', 0, 0), 'd': ('M4', 0, 0)}
    b = {'a': ('M4', 0, 150), 'b': ('M4', 0, 300), 'c': ('M5', 0, 0), 'e': ('M4', 0, 0)}
    assert C.diff_rows(a, b) == dict(moved=['b', 'c'], added=['e'], removed=['d'])


def test_kv_e2_like_68_moved_counted_design_listed_uncounted_not():
    files = {'e2_old.json': pins(68), 'e2_new.json': pins(68, dy=1.0), 'o.json': pins(3), 'o2.json': pins(3, dy=5.0)}
    od, orows = designs([core('kv3_head_eighth_e2', 'e2_old.json'), core('other', 'o.json')], files)
    nd, nrows = designs([core('kv3_head_eighth_e2', 'e2_new.json'), core('other', 'o2.json')], files)
    counted = {'kv3_head_eighth_e2': ['epyc4:/x/signoff/signoff.json src 3e7fccd flow flow-x']}
    f = C.changes('qwen_kvsys', od, orows, nd, nrows, counted=counted, still={}, old_plan='A', new_plan='B')
    assert [x['design'] for x in f] == ['kv3_head_eighth_e2']
    assert len(f[0]['moved']) == 68 and not f[0]['added'] and not f[0]['removed'] and f[0]['still_counted'] is False
    assert f[0]['counted_entry'].startswith('epyc4:/x/signoff')
    line = C.summary(f[0])
    assert '68 pins moved' in line and 'NO LONGER COUNTED' in line and 'epyc4:/x/signoff' in line
    # --all form: every changed design
    assert [x['design'] for x in C.changes('qwen_kvsys', od, orows, nd, nrows)] == ['kv3_head_eighth_e2', 'other']


def test_unchanged_and_within_tolerance_not_listed():
    files = {'a.json': pins(4), 'b.json': pins(4, dy=0.1)}   # 100 nm < 200 nm tolerance
    od, orows = designs([core('m', 'a.json')], files)
    for pf in ('a.json', 'b.json'):
        nd, nrows = designs([core('m', pf)], files)
        assert C.changes('s81', od, orows, nd, nrows, counted={'m': ['r']}) == []


def test_module_gone_outline_change_and_multi_design_pick():
    files = {'a.json': pins(2), 'b.json': pins(2, dy=3.0)}
    od, orows = designs([core('m', 'a.json'), core('g', 'a.json')], files)
    nd, nrows = designs([core('m', 'a.json', outline=(120.0, 50.0))], files)
    f = {x['design']: x for x in C.changes('hbm', od, orows, nd, nrows, counted={'m': ['r1'], 'g': ['r2']})}
    assert f['g']['gone'] and 'gone' in C.summary(f['g'])
    assert f['m']['outline'] == [[100.0, 50.0], [120.0, 50.0]] and not f['m']['moved']
    # module with two designs in the new plan: the same-outline one stands for the old design
    nd, nrows = designs([core('m', 'b.json'), core('m', 'a.json', outline=(80.0, 40.0))], files)
    f = C.changes('hbm', od, orows, nd, nrows, counted={'m': ['r1']})
    assert len(f) == 1 and f[0]['new_design'].startswith('m#100x50/') and f[0]['moved'] == ['d[0]', 'd[1]']


def test_track_snapshot_log_and_post_once(tmp_path):
    files = {'a.json': pins(5), 'b.json': pins(5, dy=2.0)}
    od, orows = designs([core('m', 'a.json')], files)
    old_cache = {'plans': {'kv/plan_c': {'die': 'qwen_kvsys', 'signed_designs': {'m': ['h:/r src s flow f']}}}}
    assert C.track('qwen_kvsys', 'kv/plan_c', od, orows, old_cache, state=tmp_path) == []     # first run: snapshot only
    assert (tmp_path / 'plan_pins' / 'qwen_kvsys.json').exists()
    assert C.track('qwen_kvsys', 'kv/plan_c', od, orows, old_cache, state=tmp_path) == []     # no change
    nd, nrows = designs([core('m', 'b.json')], files)
    f = C.track('qwen_kvsys', 'kv/plan_d', nd, nrows, old_cache, still={'m': ['x']}, state=tmp_path)
    assert len(f) == 1 and len(f[0]['moved']) == 5 and f[0]['still_counted'] and f[0]['old_plan'] == 'kv/plan_c'
    rows, mark = C.unposted(tmp_path)
    assert len(rows) == 1
    lines = C.queue_lines(rows, '2026-11-10 19:00 PST')
    assert lines[0].startswith('- 2026-11-10 19:00 PST ADVISORY [COUNT-HOURLY -> DIE-KV owner, COORD]')
    assert 'kv/plan_c -> kv/plan_d' in lines[0] and 'still counted' in lines[1]
    mark()
    assert C.unposted(tmp_path)[0] == []
    # a design not counted on the previous refresh is not listed
    assert C.track('qwen_kvsys', 'kv/plan_e', od, orows, {'plans': {}}, state=tmp_path) == []


def test_cli_plan_relative_pins(tmp_path, capsys):
    for name, ps in (('old', pins(3)), ('new', pins(3, dy=1.0))):
        d = tmp_path / name
        (d / 'cores').mkdir(parents=True)
        (d / 'cores' / 'm.json').write_text(json.dumps(ps))
        (d / 'die_plan.json.gz').write_bytes(gzip.compress(json.dumps(plan([core('m', 'cores/m.json')])).encode()))
    cache = tmp_path / 'c.json'
    cache.write_text(json.dumps({'plans': {'p': {'die': 's81', 'signed_designs': {'m': ['h:/sig src a flow b']}}}}))
    assert C.main(['--old', str(tmp_path / 'old/die_plan.json.gz'), '--new', str(tmp_path / 'new/die_plan.json.gz'),
                   '--die', 's81', '--cache', str(cache)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[1].split('\t')[:4] == ['s81', 'm', 'm', '3'] and out[1].endswith('h:/sig src a flow b')


def test_count_hourly_posts_queue_lines_with_rate_row(tmp_path, monkeypatch):
    import count_hourly as H
    coord = tmp_path / 'coord'; (coord / 'lanes').mkdir(parents=True)
    state = tmp_path / 'state'; state.mkdir()
    cache = state / 'release_tree_plan_cache.json'
    cache.write_text(json.dumps({'generated': time.time(), 'plans': {}}))
    (state / C.LOG).write_text(json.dumps(dict(die='hbm', design='m', module='m', moved=['a'], added=[], removed=[],
                                               outline=None, gone=False, counted_entry='h:/r', old_plan='A', new_plan='B',
                                               id='hbm|m|A|t')) + '\n')
    monkeypatch.setattr(H, 'COORD', coord); monkeypatch.setattr(H, 'CACHE', cache); monkeypatch.setattr(H, 'STATE', state)
    got = []
    assert H.run(scan=lambda: 0, commit=lambda files: got.append(list(files)) or 0) == 0
    assert got == [[H.QUEUE, H.RATE]]
    q = (coord / H.QUEUE).read_text()
    assert 'DIE-HBM owner' in q and 'hbm m: 1 pins moved (a).' in q
    got.clear()
    assert H.run(scan=lambda: 0, commit=lambda files: got.append(list(files)) or 0) == 0
    assert got == [] and (coord / H.QUEUE).read_text() == q                 # posted once; same-hour counts: no commit
