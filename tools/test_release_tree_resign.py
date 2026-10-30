#!/usr/bin/env python3
"""RE-SIGN record path of release_tree_plan.py (FLOW-7, COORD ruling 2026-10-30 02:03 (3b)). Run: python3 -m pytest -q"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

prov = R._PROV_NS['prov']
load = lambda f: json.loads(pathlib.Path(f).read_text())


def mk(tmp, lec='EQUIVALENT', db=True, **over):
    d = tmp / 'resign'; d.mkdir()
    (d / 'signoff.json').write_text(json.dumps({'verdict': 'SIGNED', 'name': 'x'}))
    (d / 'lec.json').write_text(json.dumps({'verdict': lec}))
    if db: (d / '6_final.odb').write_text('db')
    p = dict(kind='resign', verdict='SIGNED', src_commit='275646f85fd8', flow_tag='flow-20261030-a-qc',
             routed_db=str(d / '6_final.odb'), build_commit='a2b2a0808c2', lec='lec.json')
    p.update(over)
    (d / 'PROVENANCE.json').write_text(json.dumps({k: v for k, v in p.items() if v is not None}))
    return str(d / 'signoff.json')


def test_valid_resign_is_versioned(tmp_path):
    r = prov(mk(tmp_path), {'verdict': 'SIGNED'}, load)
    assert r['resign'] and r['src_commit'] == '275646f85fd8' and r['build_commit'] == 'a2b2a0808c2'
    r['versioned'] = bool(r.get('src_commit') and r.get('flow_tag'))
    R.check_resign_tag(r, tag_commit=lambda t: '275646f85fd8c24eff99121721aa20d23ec4f9a9')
    assert r['versioned'] and 'resign_error' not in r


def test_lec_not_equivalent_fails(tmp_path):
    r = prov(mk(tmp_path, lec='NOT_EQUIVALENT'), {'verdict': 'SIGNED'}, load)
    assert not r.get('src_commit') and 'LEC' in r['resign_error']


def test_missing_db_or_field_fails(tmp_path):
    r = prov(mk(tmp_path, db=False), {'verdict': 'SIGNED'}, load)
    assert not r.get('src_commit') and 'routed DB' in r['resign_error']
    r = prov(mk(tmp_path / 'b' if (tmp_path / 'b').mkdir() is None else None, build_commit=None), {'verdict': 'SIGNED'}, load)
    assert not r.get('src_commit') and 'build_commit' in r['resign_error']


def test_tag_must_carry_src_commit(tmp_path):
    r = prov(mk(tmp_path), {'verdict': 'SIGNED'}, load); r['versioned'] = True
    R.check_resign_tag(r, tag_commit=lambda t: '1abb3fcb1e1e778eace6f9954f35087277bfe227')
    assert not r['versioned'] and 'flow_tag' in r['resign_error']
    r = prov(mk(tmp_path / 'c' if (tmp_path / 'c').mkdir() is None else None, flow_tag='my-tag'), {'verdict': 'SIGNED'}, load)
    r['versioned'] = True
    R.check_resign_tag(r, tag_commit=lambda t: '275646f85fd8c24eff99121721aa20d23ec4f9a9')
    assert not r['versioned']


def test_failed_resign_never_legacy(tmp_path):
    r = prov(mk(tmp_path, lec='UNPROVEN'), {'verdict': 'SIGNED'}, load)
    r.update(path='x', generated=0)
    assert not R.is_legacy(r, None)


def test_plain_provenance_unchanged(tmp_path):
    d = tmp_path / 'k'; d.mkdir()
    (d / 'signoff.json').write_text('{}')
    (d / 'PROVENANCE.json').write_text(json.dumps({'verdict': 'SIGNED', 'src_commit': 'abc1234', 'flow_tag': 'flow-20261029-a-qc'}))
    r = prov(str(d / 'signoff.json'), {}, load)
    assert r == {'src_commit': 'abc1234', 'flow_tag': 'flow-20261029-a-qc', 'prov_file': str(d / 'PROVENANCE.json')}
    assert R.check_resign_tag(dict(r)) == r


def test_kit_provenance_is_skipped_for_the_resign_record_above(tmp_path):
    # SIGNOFF-SPRINT-6 10-30: the signed kit dir holds the kit's own build record (schema kit_provenance.v1, no
    # flow_tag); the counter must look past it to the resign PROVENANCE.json of the tag dir above
    sj = pathlib.Path(mk(tmp_path))
    kit = sj.parent / 'kit'; kit.mkdir()
    (kit / 'PROVENANCE.json').write_text(json.dumps({'schema': 'opentallas.kit_provenance.v1', 'provenance': {}}))
    (kit / 'signoff.json').write_text(json.dumps({'verdict': 'SIGNED'}))
    r = prov(str(kit / 'signoff.json'), {'verdict': 'SIGNED'}, load)
    assert r.get('resign') and r['flow_tag'] == 'flow-20261030-a-qc' and r['prov_file'] == str(sj.parent / 'PROVENANCE.json')
    # a kit record alone (nothing above it) stays unversioned, as before
    lone = tmp_path / 'lone'; lone.mkdir()
    (lone / 'PROVENANCE.json').write_text(json.dumps({'schema': 'opentallas.kit_provenance.v1'}))
    assert prov(str(lone / 'signoff.json'), {'verdict': 'SIGNED'}, load) == {}
