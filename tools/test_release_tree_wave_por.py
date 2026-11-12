#!/usr/bin/env python3
"""WAVE-POR (CORES-S81-1, COORD 11-12): the counted plan per die follows the kit wave.  Run: python3 -m pytest -q
OT_COUNT_LIVE_CHECK=1 also runs test_live_counted_plan_equals_wave_plan against the live cache + kit-wave state."""
import gzip, hashlib, json, os, pathlib, subprocess, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

HDR = 'die\titem\tparent_item\tplan_sha\tblock_sha\tevent\tstage\tstatus\tclass\tkit\tevidence\tupdated\tplan_current\treason\n'


def _row(die, sha, upd, cur='yes'):
    return '\t'.join([die, 'x', '', sha, 'b', 'e', 'unit', 'RUNNING', '', '', '', upd, cur, '']) + '\n'


def _wave(tmp, rows, cfg=None):
    (tmp / 'st.tsv').write_text(HDR + ''.join(rows))
    (tmp / 'kw.json').write_text(json.dumps(cfg or {'dies': {}}))
    return R.wave_plan_shas(tmp / 'kw.json', tmp / 'st.tsv')


def test_wave_sha_only_from_config(tmp_path):
    rows = [_row('hbm', 'aaaaaaaaaaaa', '2026-11-12 02:00')] * 9
    w = _wave(tmp_path, rows, {'dies': {'hbm': {'plan': '/x/die_plan.json', 'plan_sha256': 'F' * 64},
                                        's81': {'plan': '/y/plan.json'}}})
    assert w['hbm']['sha'] == 'f' * 12 and w['hbm']['path'] == '/x/die_plan.json' and w['hbm']['rows'] == {'aaaaaaaaaaaa': 9}
    assert w['s81']['sha'] is None and 'no plan_sha256' in w['s81']['source']   # stage votes never pick the plan
    out, drift = R.resolve_plans(PL[:1], w, {})
    assert out[0][:4] == PL[0] and 'no plan_sha256' in drift[0]


PL = [('s81', 's81', 'physical/die_plan/s81/plan_old.json', ()),
      ('hbm', 'hbm/plan_of_record/d1', 'physical/die_plan/hbm/plan_of_record/d1/die_plan.json.gz', ('hbm/plan_of_record/d0',))]


def test_resolve_follows_wave_on_main_and_flags_drift():
    idx = {'111111111111': ['physical/die_plan/s81/events/e1/plan_new.json.gz', 'physical/die_plan/qwen_compute/plan_x.json'],
           '222222222222': ['physical/die_plan/hbm/plan_of_record/d1/die_plan.json.gz']}
    wave = {'s81': dict(sha='111111111111', path='/srv/a/plan.json'), 'hbm': dict(sha='333333333333', path='/srv/t39w/die_plan.json')}
    out, drift = R.resolve_plans(PL, wave, idx)
    assert out[0][:4] == ('s81', 's81', 'physical/die_plan/s81/events/e1/plan_new.json.gz', ())   # pinned dir kept, file follows
    assert out[0][4]['repointed_from'] == 'physical/die_plan/s81/plan_old.json' and 'drift' not in out[0][4]
    assert out[1][:4] == PL[1] and len(drift) == 1 and 'hbm' in drift[0] and '333333333333' in drift[0]   # never a host plan
    out, drift = R.resolve_plans(PL, {'hbm': dict(sha='222222222222')}, idx)
    assert out[1][:4] == PL[1] and 'repointed_from' not in out[1][4] and drift == [out[0][4]['drift']]   # s81: no wave plan


def test_resolve_never_crosses_die_top():
    out, drift = R.resolve_plans(PL[:1], {'s81': dict(sha='111111111111')}, {'111111111111': ['physical/die_plan/hbm/p.json']})
    assert out[0][:4] == PL[0] and drift


def test_main_plan_index_hashes_gz_content(tmp_path):
    repo = tmp_path / 'r'; d = repo / 'physical/die_plan/s81/events/e'; d.mkdir(parents=True)
    body = json.dumps({'partition_types': {}, 'pad': os.urandom(20000).hex()}).encode()
    (d / 'plan_e.json.gz').write_bytes(gzip.compress(body)); (d / 'notes.json').write_bytes(body)
    g = lambda *a: subprocess.run(['git', '-C', str(repo)] + list(a), check=True, capture_output=True)
    g('init', '-q'); g('add', '.'); g('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x')
    idx = R.main_plan_index(['s81'], repo=repo, rev='HEAD', index_path=tmp_path / 'i.json')
    assert idx == {hashlib.sha256(body).hexdigest()[:12]: ['physical/die_plan/s81/events/e/plan_e.json.gz']}
    assert R.main_plan_index(['s81'], repo=repo, rev='HEAD', index_path=tmp_path / 'i.json') == idx   # cached blob


def test_wave_check_and_current_plans(tmp_path):
    c = dict(plans_resolved=[dict(die='s81', pdir='s81', src='physical/die_plan/s81/p.json.gz', overlays=[])],
             plans={'s81/p.json': dict(plan_sha='111111111111')})
    assert R.wave_check(c, {'s81': dict(sha='111111111111')}) == [('s81', '111111111111', '111111111111', True)]
    assert R.wave_check(c, {'s81': dict(sha='222222222222')})[0][3] is False
    (tmp_path / 'c.json').write_text(json.dumps(c))
    assert R.current_plans(tmp_path / 'c.json') == [('s81', 's81', 'physical/die_plan/s81/p.json.gz', ())]
    assert R.current_plans(tmp_path / 'missing.json') == [tuple(p) for p in R.PLANS]


@pytest.mark.skipif(not os.environ.get('OT_COUNT_LIVE_CHECK'), reason='live check: set OT_COUNT_LIVE_CHECK=1')
def test_live_counted_plan_equals_wave_plan():
    """the counted plan sha equals the kit-wave plan sha for every die (fails while a die's wave plan is not merged)"""
    c = json.loads(R.CACHE.read_text())
    rows = R.wave_check(c)
    assert sorted(r[0] for r in rows) == sorted(['s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm'])
    bad = [r for r in rows if not r[3]]
    assert not bad, 'counted != kit-wave plan: %s' % bad


def test_pick_plan_dir(tmp_path):
    dp = tmp_path / 'physical/die_plan'
    plan = {'partition_types': {'t': {'hard_cores': [{'module': 'c', 'pins_file': 'cores/c.json'}]}}}
    (dp / 'hbm/plan_of_record/t39/cores').mkdir(parents=True); (dp / 'hbm/plan_of_record/d1').mkdir(parents=True)
    (dp / 'hbm/plan_of_record/t39/die_plan.json').write_text(json.dumps(plan)); (dp / 'hbm/plan_of_record/t39/cores/c.json').write_text('{}')
    src = 'physical/die_plan/hbm/plan_of_record/t39/die_plan.json'
    assert R.pick_plan_dir(tmp_path, src, 'hbm/plan_of_record/d1', ('hbm/plan_of_record/d0',)) == ('hbm/plan_of_record/t39', ())
    plan2 = {'partition_types': {'t': {'hard_cores': [{'module': 'c', 'pins_file': 'inputs/core_pins/c.json'}]}}}
    (dp / 's81/events/e').mkdir(parents=True); (dp / 's81/inputs/core_pins').mkdir(parents=True)
    (dp / 's81/events/e/plan.json').write_text(json.dumps(plan2)); (dp / 's81/inputs/core_pins/c.json').write_text('{}')
    assert R.pick_plan_dir(tmp_path, 'physical/die_plan/s81/events/e/plan.json', 's81', ()) == ('s81', ())
