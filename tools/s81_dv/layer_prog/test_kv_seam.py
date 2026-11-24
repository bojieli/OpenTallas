"""t2 A|B seam dates of the SUKV jobs (FABLE gate (a)): table, programme selection, receipt and binding refusals."""
import copy
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_prog import kv_bank_contract as KC
from layer_prog import kv_program_builder as B
from layer_prog import kv_seam_image as IMG
from layer_prog import lower_kv as K


def test_uncut_dates_unchanged():
    t = KC.kv_timing()
    assert t['done'] == dict(KV=1130, GK=1025, CN=1218, IK=1058, CP=390)
    assert t['first_native_write'] == dict(KV=1030, CN=1030, IK=1030, CP=139)
    assert t['last_read_completion_bound'] == dict(KV=80, CN=80, IK=80, GK=72, CP=378)
    assert (t['native_write_commit_after_done'], t['native_read_ready_after_done']) == (1, 2)


def test_seam_2_2_dates():
    t = KC.kv_timing(2, 2)
    assert t['done'] == dict(KV=1134, GK=1029, CN=1222, IK=1062, CP=398)
    assert t['first_native_write'] == dict(KV=1034, CN=1034, IK=1034, CP=147)
    assert t['last_read_completion_bound'] == dict(KV=84, CN=84, IK=84, GK=76, CP=382)
    s = KC.kv_timing(2, 2, 1)
    assert s['done'] == dict(KV=1134, GK=1029, CN=1222, IK=1062, CP=399)


def test_unmeasured_seam_refused():
    for seam in ((1, 2), (2, 1), (4, 4)):
        with pytest.raises(ValueError):
            KC.kv_timing(*seam)


@pytest.fixture
def chains(tmp_path, monkeypatch):
    monkeypatch.setattr(B, 'derive_profile', B.derive_profile)
    monkeypatch.setattr(K, '_dvc', K._dvc)
    out = {}
    for name, sr in (('sr0', 0), ('sr1', 1)):
        IMG.emit((2, 2), sr, tmp_path / name)
        out[name] = {p.name: (p / 'image.txt').read_text() for p in (tmp_path / name).iterdir()}
    import json
    out['program'] = json.loads((tmp_path / 'sr0/new/program.json').read_text())
    return out


SCHED = dict(ops=[dict(id=f'L14.{n}', op=n, start=10 * i) for i, n in enumerate(IMG.NAMES.values())])


def test_compiled_programme_moves(chains):
    prog = chains['program']
    assert prog['kv_seam'] == {'in': 2, 'out': 2, 'vp_sr': 0}
    K.validate(prog, SCHED)
    for images in (chains['sr0'], chains['sr1']):
        assert all(images[v] != images['new'] for v in images if v != 'new')


@pytest.mark.parametrize('kind', ['KV', 'GK', 'CN', 'IK', 'CP'])
def test_old_date_refused_on_seam_programme(chains, kind):
    bad = copy.deepcopy(chains['program'])
    for j in bad['jobs']:
        if j['kind'] == kind:
            j['done_age'] = KC.ADAPTER_DONE[kind]
    with pytest.raises(ValueError):
        K.validate(bad, SCHED)


def test_seam_must_match_binding(chains):
    bad = copy.deepcopy(chains['program'])
    bad['source_binding']['parameters']['KV_SEAM_OUT'] = 0
    with pytest.raises(ValueError):
        K.validate(bad, SCHED)
    bad = copy.deepcopy(chains['program'])
    del bad['kv_seam']
    with pytest.raises(ValueError):
        K.validate(bad, SCHED)


def seam_receipt(cp=399):
    lines = [f'SUKV_JOB {n} kind={k} finish_edges={e} reads=1' for n, k, e in
             (('KV', 1, 1135), ('GK0', 7, 1030), ('CN', 12, 1223), ('IK', 13, 1063), ('CP', 14, cp))]
    return dict(results=dict(L14=dict(lines=lines)), params=params(4))


def params(vlat):
    p = {('D:' if k.startswith('OT_') else '') + k: str(v) for k, v in B.T2B_V5D.items()}
    return dict(p, VLAT=vlat, HARD_RQ=2, SEAM_IN='2', SEAM_OUT='2')


def test_receipt_must_measure_the_compiled_dates():
    sel = dict(hard_rq=2, seam=(2, 2), vlat=4, parameters=B.T2B_V5D)
    assert B.unit_timing(sel, seam_receipt(), 0)['done']['CP'] == 398
    with pytest.raises(ValueError):
        B.unit_timing(sel, seam_receipt(391), 0)
    short = seam_receipt()
    short['results']['L14']['lines'].pop()
    with pytest.raises(ValueError):
        B.unit_timing(sel, short, 0)
    for k, v in (('KV_KST', "64'h2568123621154115"), ('SEAM_IN', '3'), ('VLAT', 5), ('D:OT_S81_KVLEAF_EXIT_RELAYS', '0')):
        other = seam_receipt()
        other['params'][k] = v
        with pytest.raises(ValueError):
            B.unit_timing(sel, other, 0)
    with pytest.raises(ValueError):                       # VLAT 4 receipt, vp SRAM-register die
        B.unit_timing(sel, seam_receipt(), 1)


def test_receipt_form_must_be_the_bound_leaf():
    sel = dict(hard_rq=2, seam=(2, 2), vlat=4, parameters=B.T2B_V5D)
    good = dict(B.T2B_V5D, KV_SEAM_IN=2, KV_SEAM_OUT=2)
    B.check_unit_profile(sel, good)
    for k, v in (('KV_SEAM_IN', 0), ('KV_CPQ', 3), ('KV_KST', "64'h2568123621154115")):
        with pytest.raises(ValueError):
            B.check_unit_profile(sel, dict(good, **{k: v}))
    with pytest.raises(ValueError):                       # a seam leaf may not use the uncut receipt
        B.check_unit_profile(dict(hard_rq=0, seam=(0, 0)), good)
