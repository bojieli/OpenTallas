#!/usr/bin/env python3
"""Plan-of-record sources of release_tree_plan.py (FLOW-12, COORD ruling 2026-10-30 20:13 (3)). Run: python3 -m pytest -q"""
import gzip, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

PLAN = dict(partition_types={'t': dict(module='m', hard_cores=[dict(module='core', pins_file='pins/c.json', outline_um=[10, 20])])},
            partitions=[dict(type='t'), dict(type='t')])
PINS = {'pins': [dict(name='a', layer='M5', x=1.0, y=2.0)]}


def test_label():
    assert R.plan_label('physical/die_plan/hbm/plan_of_record/d41v/die_plan.json.gz') == 'hbm/plan_of_record/d41v/die_plan.json'
    assert R.plan_label('physical/die_plan/s81/plan_h2_2249.json') == 's81/plan_h2_2249.json'
    assert R.plan_label('results/die_head_44_1030/l44/source_plan_l44.json.gz') == 'results/die_head_44_1030/l44/source_plan_l44.json'


def test_gz_plan_in_other_dir_resolves_plan_relative_tables(tmp_path):
    src = 'results/x/l9/source_plan.json.gz'
    (tmp_path / src).parent.mkdir(parents=True)
    (tmp_path / src).write_bytes(gzip.compress(json.dumps(PLAN).encode()))
    pd = tmp_path / 'physical/die_plan/die_x/pins'; pd.mkdir(parents=True); (pd / 'c.json').write_text(json.dumps(PINS))
    pj = R.materialize_plan(tmp_path, 'die_x', src)
    assert pj == tmp_path / 'physical/die_plan/die_x/por__source_plan.json' and json.loads(pj.read_text()) == PLAN
    D, rows = R.plan_designs(json.loads(pj.read_text()), pj.parent)
    assert list(D) == ['core'] and D['core']['instances'] == 2 and not D['core']['pins_sha'].startswith('file:')


def test_plain_plan_in_place_and_no_clobber(tmp_path):
    src = 'physical/die_plan/die_y/plan_of_record/p.json'
    (tmp_path / src).parent.mkdir(parents=True); (tmp_path / src).write_text(json.dumps(PLAN))
    assert R.materialize_plan(tmp_path, 'die_y/plan_of_record', src) == tmp_path / src
    other = 'results/z/p.json'; (tmp_path / other).parent.mkdir(parents=True); (tmp_path / other).write_text('{"x": 1}')
    (tmp_path / 'physical/die_plan/die_y/plan_of_record/por__p.json').write_text('{"x": 2}')
    try:
        R.materialize_plan(tmp_path, 'die_y/plan_of_record', other); assert False
    except RuntimeError: pass


def test_plans_are_plan_of_record_files_on_main():
    """every PLANS source exists on origin/main and parses (the 5 dies, each once)"""
    repo = R.REPO
    assert sorted(k for k, _, _, _ in R.PLANS) == sorted(['s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm'])
    for _, pdir, src, ovl in R.PLANS:
        assert not src.endswith('/die_plan.json') or 'plan_of_record' in src, src
        b = subprocess.run(['git', '-C', str(repo), 'show', 'origin/main:' + src], capture_output=True).stdout
        P = json.loads(gzip.decompress(b) if src.endswith('.gz') else b)
        assert P.get('partition_types'), src


def test_overlay_gz_tables_and_archive_paths(tmp_path):
    """HBM form: plan_of_record/<dNN>/die_plan.json.gz + an older dir holding the gzipped cores/*.json it references"""
    por = tmp_path / 'physical/die_plan/die_z/plan_of_record'
    (por / 'd1/cores').mkdir(parents=True); (por / 'd2').mkdir(parents=True)
    (por / 'd1/cores/c.json.gz').write_bytes(gzip.compress(json.dumps(PINS).encode()))
    (por / 'd1/die_plan.json.gz').write_bytes(gzip.compress(b'{"old": 1}'))
    plan = dict(PLAN, partition_types={'t': dict(module='m', hard_cores=[dict(module='core', pins_file='cores/c.json', outline_um=[10, 20])])})
    (por / 'd2/die_plan.json.gz').write_bytes(gzip.compress(json.dumps(plan).encode()))
    pj = R.materialize_plan(tmp_path, 'die_z/plan_of_record/d2', 'physical/die_plan/die_z/plan_of_record/d2/die_plan.json.gz',
                            ('die_z/plan_of_record/d1',))
    assert pj.name == 'por__die_plan.json' and json.loads(pj.read_text()) == plan
    assert not (pj.parent / 'die_plan.json').exists()          # the older layer's plan is never laid
    D, _ = R.plan_designs(json.loads(pj.read_text()), pj.parent)
    assert not D['core']['pins_sha'].startswith('file:')        # cores/c.json resolved from the overlay
    plans = [('a', 'die_z/plan_of_record/d2', 'physical/die_plan/die_z/plan_of_record/d2/die_plan.json.gz', ()),
             ('b', 'die_h', 'results/x/l1/p.json.gz', ())]
    assert R.plan_archive_paths(plans) == ['physical/die_plan/die_h', 'physical/die_plan/die_z', 'results/x/l1/p.json.gz', 'tools']


def test_results_ref_regex():
    t = '{"a": "results/die_head_38_1030/hd_ctl_sink_bins.json", "b": "results/arch/kv/g2.json:kv3_hg", "c": "physical/x.lef"}'
    assert R.REF_RE.findall(t) == ['results/die_head_38_1030/hd_ctl_sink_bins.json', 'results/arch/kv/g2.json']


def test_memory_macros_not_designs(tmp_path):
    P = dict(PLAN, partition_types={'t': dict(module='m', hard_cores=[
        dict(module='core', pins_file='pins/c.json', outline_um=[10, 20]),
        dict(module='ot_sram_1r1w_32x64_m1', lef='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/x.lef', outline_um=[5, 5]),
        dict(module='ot_dsrom_lane', lef='physical/ref_tile/x/views/ot_dsrom_lane/ot_dsrom_lane.lef', outline_um=[5, 5])])})
    D, _ = R.plan_designs(P, tmp_path, read=lambda f: PINS)
    assert sorted(D) == ['core', 'ot_dsrom_lane']


def test_head_without_g0c_still_shows_its_counts():
    # FLOW-12 10-30 (COORD 21:2x): G0C NOT RUN must not blank the die ('plan layer missing')
    import release_tree_render as R
    rows = [dict(plan='p', types=25, clean=None, verdict=None, errors=None, bad={}, die_level={}, signed_types=0,
                 cores=4, signed_cores=2, signed_list=[], modules=4, signed_modules=2, stale=None, error='G0C did not run')]
    pc = R.plan_cnt(rows)
    assert pc == dict(types=25, clean=None, signed_types=0, cores=4, signed_cores=2)
    assert R.clean_txt(pc) == 'G0C NOT RUN (25 types)'
    assert R.clean_txt(dict(pc, clean=3)) == '3/25'
    assert 'SIGNED hard-core designs 2/4' in R.plan_html(rows, {})


def test_pin_alias_laid_before_designs_and_sha_checked(tmp_path):
    # FLOW-15: lane-tree pins file named by the plan, byte-identical main copy elsewhere -> laid at the plan path
    import hashlib
    data = json.dumps(PINS).encode()
    al = {'pins/c.json': ('results/x/c_777.json', hashlib.sha256(data).hexdigest())}
    pd = tmp_path / 'plan'; pd.mkdir()
    # the same-name cores/ fallback holds a DIFFERENT (old) table: the alias must win
    (pd / 'cores').mkdir(); (pd / 'cores' / 'c.json').write_text(json.dumps({'pins': [dict(name='old', layer='M5', x=9.0, y=9.0)]}))
    assert R.materialize_pin_aliases(pd, al, read=lambda p: data) == ['pins/c.json']
    D, rows = R.plan_designs(PLAN, pd)
    assert not D['core']['pins_sha'].startswith('file:') and (pd / 'pins/c.json').read_bytes() == data
    assert R.materialize_pin_aliases(pd, al, read=lambda p: b'x') == []          # present -> untouched
    pd2 = tmp_path / 'plan2'; pd2.mkdir()
    try:
        R.materialize_pin_aliases(pd2, al, read=lambda p: b'other'); assert False
    except RuntimeError as e: assert 'sha256' in str(e)


def test_head_lep_pair_alias_matches_main():
    a = R.PIN_ALIASES['s81_head']['core_pins/lep_pair_pins_777.json']
    import hashlib
    r = subprocess.run(['git', '-C', str(R.REPO), 'show', 'origin/main:' + a[0]], capture_output=True)
    if r.returncode: import pytest; pytest.skip('no repo')
    assert hashlib.sha256(r.stdout).hexdigest() == a[1]
