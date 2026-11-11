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
    assert 'core_live#10x10/abcd' not in st           # COORD 11-10: 'core_live_d85' = a running form of core_live


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




def test_owner_post_groups_and_marks_new():
    st = S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW)
    txt = S.owner_post(st, prev=[{'die': 's81', 'item': 'old_fail'}], stamp='X')
    assert txt.startswith('- X STALE [WAVE-OPS-1 -> KIT-WAVE-1, S81-CORES, COORD, KW-FIX-43, KW-FIX-44]')
    assert 'S81 t old_fail (FAIL 11-09 10:00)' in txt and '+S81 t old_fail' not in txt
    assert 'COORD (unowned)' in txt and '+S81 t t__t4 (no kit-wave row)' in txt
    assert S.owner_post([]) == ''


def test_form_suffix_counts_as_live_but_not_a_sibling_core():
    c = {'plans': {'s81/plan.json': {'designs': {
        'ot_opsa_group1': {'module': 'ot_opsa_group1'}, 'ot_static_front': {'module': 'ot_static_front'},
        'ot_q2nf_rest': {'module': 'ot_q2nf_rest'}, 'ot_q2nf_rest_x': {'module': 'ot_q2nf_rest_x'}},
        'signed_designs': {}, 'plan_types': {'t__t4': 'm'}, 'signed_types': {}}}}
    txt = ('/srv/a/ot_opsa_group1_p3r1109/run\nnew-ot_static_front_w_7a5b26893ab62940\n'
           '/srv/b/ot_q2nf_rest_x_c3/run\n/srv/c/t__t4_b/run\n')
    st = names(S.stale_items(c, [], {}, {}, txt, DIES, now=NOW))
    assert 'ot_opsa_group1' not in st and 'ot_static_front' not in st     # forms <module>_<suffix> are live
    assert 'ot_q2nf_rest_x' not in st                                       # its own form
    assert 'ot_q2nf_rest' in st                                             # sibling core's form is not its form
    assert 't__t4' in st                                                    # types keep whole-name matching


def test_retired_items_dropped(tmp_path):
    p = tmp_path / 'OWNERS-RETIRED.tsv'
    p.write_text('# die\tname\treason\ns81\tcore_b\tNOT-IN-PLAN\ns81\told_*\tNOT-IN-PLAN prefix\nhbm\tt__t4\tother die\n')
    r = S.retired_rows(str(p))
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW, retired=r))
    assert 'core_b' not in st and 'old_fail' not in st
    assert 't__t4' in st and 'core_a' in st


def test_owner_fallback_lane_md(tmp_path):
    d = tmp_path / 'lanes'; d.mkdir()
    (d / 'HBM-CORES-B.md').write_text('# HBM-CORES-B lane file\n- 2026-11-10 22:41 PST OWNER HBM-CORES-B (COORD): core_b, '
                                      't__t4 (forms)\n- 22:50 note: core_x looked at\n')
    (d / 'OLD-LANE.md').write_text('- OWNER OLD-LANE: core_b was mine\n')
    (d / 'GEOM-REVIEW.md').write_text('- GEOM REQ [KIT-WAVE-1 sample s81/old_fail]\n')   # a mention, no OWNER line
    (d / 'COORD-REVIEW-QUEUE.md').write_text('core_a t__t4\n')
    os.utime(d / 'OLD-LANE.md', (NOW - 100 * 3600, NOW - 100 * 3600))   # older than LANE_MD_H: not read
    os.utime(d / 'HBM-CORES-B.md', (NOW - 3600, NOW - 3600))
    os.utime(d / 'COORD-REVIEW-QUEUE.md', (NOW, NOW))
    os.utime(d / 'GEOM-REVIEW.md', (NOW, NOW))
    idx = S.lane_md_index(str(d), now=NOW)
    assert [x[1] for x in idx] == ['HBM-CORES-B'] and 'core_x' not in idx[0][2]
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW, lane_idx=idx))
    assert st['core_b']['owner'] == 'HBM-CORES-B' and st['core_b']['owner_state'] == 'lanes/HBM-CORES-B.md'
    assert st['t__t4']['owner'] == 'HBM-CORES-B'
    assert st['core_a']['owner'] == 'S81-CORES'                             # an OWNERS row still wins
    assert st['old_fail']['owner'] == 'KIT-WAVE-1'                          # OWNERS row; GEOM mention ignored
    st = names(S.stale_items(CACHE, ROWS, {}, STATE, TEXT, DIES, now=NOW, lane_idx=idx))
    assert st['old_fail']['owner'] == 'unowned'                             # mention only -> not an owner


def test_coord_routed_owner_wins(tmp_path):
    p = tmp_path / 'COORD-ROUTED-OWNERS.tsv'
    p.write_text('# die\titem\towner\truling\ns81\tcore_a\tDIE-S81-85\tCOORD 22:31\ns81\tt__*\tDIE-X\tprefix\n'
                 's81\tcore_b\t\tempty owner ignored\n')
    r = S.routed_rows(str(p))
    st = names(S.stale_items(CACHE, ROWS, OWN, STATE, TEXT, DIES, now=NOW, routed=r))
    assert st['core_a']['owner'] == 'DIE-S81-85' and st['core_a']['owner_state'] == 'COORD-ROUTED COORD 22:31'
    assert st['t__t4']['owner'] == 'DIE-X'                     # prefix row; was unowned
    assert st['core_b']['owner'] == 'unowned' and st['old_fail']['owner'] == 'KIT-WAVE-1'

if __name__ == '__main__':
    import tempfile, pathlib
    test_stale_selection(); test_live_text_core_by_module_token(); test_tokens_whole_name()
    test_no_probe_text_means_no_process_filter_and_threshold()
    test_render_and_owner_comment_line(pathlib.Path(tempfile.mkdtemp()))
    test_owner_post_groups_and_marks_new()
    test_form_suffix_counts_as_live_but_not_a_sibling_core()
    test_retired_items_dropped(pathlib.Path(tempfile.mkdtemp()))
    test_owner_fallback_lane_md(pathlib.Path(tempfile.mkdtemp()))
    test_coord_routed_owner_wins(pathlib.Path(tempfile.mkdtemp()))
    print("10 passed")
