"""WAVE-OPS-1 11-10: STALE list (stale_list.py). Run: python3 -I tools/tests/test_stale_list.py (or pytest)."""
import importlib.util, os, time
spec = importlib.util.spec_from_file_location('sl', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'stale_list.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)

NOW = time.mktime(time.strptime('2026-11-10 18:00', '%Y-%m-%d %H:%M'))
DIES = [('s81', 'S81')]
CACHE = {'plans': {'s81/plan.json': {
    'designs': {'core_a': {'module': 'core_a', 'wave_keys': ['core_a__v0123456789ab']},
                'core_b': {'module': 'core_b'}, 'core_signed': {'module': 'core_signed'},
                'core_live#10x10/abcd': {'module': 'core_live'}},
    'signed_designs': {'core_signed': 1},
    'plan_types': {'t__t4': 'm', 't__t45': 'm', 'old_fail': 'm', 'fresh': 'm', 'wave_run': 'm', 'own_live': 'm',
                   'sig_t': 'm', 'cls__t1': 'm'},
    'signed_types': {'sig_t': 1}}}}


def row(item, upd, status='FAIL', stage='route', cls='FLOW', plan_current='yes'):
    return dict(die='s81', item=item, status=status, stage=stage, **{'class': cls}, updated=upd,
                plan_current=plan_current, parent_item='')


ROWS = [row('old_fail', '2026-11-09 10:00'), row('fresh', '2026-11-10 15:00'),
        row('fresh', '2026-11-08 10:00'),
        row('core_a__v0123456789ab', '2026-11-09 12:00', 'CANCELLED', 'geom', 'SUPERSEDED', 'no'),
        row('cls__t1__cl0123abcd', '2026-11-10 14:00'),          # a class of the plan type: its row change counts
        row('t__t45', '2026-11-08 00:00')]
OWN = {('s81', 'old_fail'): {'owner': 'KIT-WAVE-1', 'live_job': 'none', 'state': 'NEEDS-KIT'},
       ('s81', 'own_live'): {'owner': 'X', 'live_job': 'kit-wave unit kw-1 (geom)', 'state': 'NEEDS-KIT'},
       ('s81', 'core_a'): {'owner': 'S81-CORES', 'live_job': 'none', 'state': 'NEEDS-KIT'}}
STATE = {'items': {'k': {'die': 's81', 'item': 'wave_run', 'status': 'RUNNING', 'parent_item': 'None'}}}
TEXT = '/srv/x/runs/s81/items/t__t45/attempt_3/gen\n/srv/y/kits/core_live_d85\nkw-s81-abc\n'


def names(st):
    return {s['item']: s for s in st}


def test_stale_selection():
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW))
    assert 'old_fail' in st and st['old_fail']['owner'] == 'KIT-WAVE-1' and st['old_fail']['age_h'] == 32.0
    assert st['old_fail']['last_status'] == 'FAIL' and st['old_fail']['last_time'] == '2026-11-09 10:00'
    assert 'fresh' not in st                          # latest row 3 h old
    assert 'cls__t1' not in st                        # its class row changed 4 h ago
    assert 'sig_t' not in st and 'core_signed' not in st      # signed
    assert 'wave_run' not in st                       # RUNNING wave record
    assert 'own_live' not in st                       # OWNERS live_job
    assert 't__t45' not in st                         # a process names its attempt dir
    assert 't__t4' in st and st['t__t4']['last_status'] == 'no kit-wave row' and st['t__t4']['owner'] == 'unowned'
    assert 'core_a' in st and st['core_a']['last_status'] == 'CANCELLED' and st['core_a']['owner'] == 'S81-CORES'
    assert 'core_b' in st
    assert 'core_live#10x10/abcd' in st               # 'core_live_d85' is another name, not this module


def test_live_text_core_by_module_token():
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, TEXT + '/srv/z/core_live/attempt_1\n', DIES, now=NOW))
    assert 'core_live#10x10/abcd' not in st


def test_tokens_whole_name():
    t = S.Tokens('/a/x__t45/b /c/y__t4_b /d/z__t1__cl99/e /f/core_a__v0123456789ab')
    assert not t.hit('x__t4') and t.hit('x__t45')
    assert not t.hit('y__t4')
    assert t.hit('z__t1') and t.hit('z__t1__cl99')
    assert t.hit('core_a')


def test_no_probe_text_means_no_process_filter_and_threshold():
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, '', DIES, now=NOW))
    assert 't__t45' in st                             # nothing seen running
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, '', DIES, now=NOW, stale_h=40))
    assert 'old_fail' not in st and 't__t45' in st


def test_render_and_owner_comment_line(tmp_path):
    st = S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW)
    out = S.render(st, ['epyc6'], 'hub')
    assert out[0].startswith('### STALE') and 'NOT SEEN: epyc6' in out[0]
    assert out[1].startswith('- [ ] STALE.S81 %d ' % len(st))
    assert any('type old_fail · FAIL route FLOW @ 2026-11-09 10:00 (32h) · owner KIT-WAVE-1' in l for l in out)
    p = tmp_path / 'OWNERS.tsv'
    p.write_text('# OWNERS -- stamp\ndie\titem\tkind\tstate\towner\tlive_job\n s81\tx\ttype\tNEEDS-KIT\tL\tnone\n'.replace('\n s81', '\ns81'))
    assert S.owners_rows(str(p))[('s81', 'x')]['owner'] == 'L'
    S.write_tsv(st, str(tmp_path / 'STALE.tsv'))
    assert len((tmp_path / 'STALE.tsv').read_text().splitlines()) == len(st) + 2


if __name__ == '__main__':
    import tempfile, pathlib
    test_stale_selection(); test_live_text_core_by_module_token(); test_tokens_whole_name()
    test_no_probe_text_means_no_process_filter_and_threshold()
    test_render_and_owner_comment_line(pathlib.Path(tempfile.mkdtemp()))
    print('5 passed')
