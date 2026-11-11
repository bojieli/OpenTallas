"""S81-XTIER-FIX 11-11 gate: the compiler's x-tier constants follow the bound u_xr RTL (xtier_land), and every landing form
the compiler can derive has a bench receipt.  Fast (RTL parse only):
    PYTHONDONTWRITEBYTECODE=1 python3 -I -m pytest -q -p no:cacheprovider tools/s81_dv/layer_prog/test_xtier_land.py
The bench half (tb_vpx_ag on the xrt build, stale-constant control) is tools/s81_dv/layer_prog/vpx/xtier_vpx_gate.sh."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent)]
import xtier_land as XT  # noqa: E402

KVT = ('OT_S81SL_KV_TRANSPORT',)
# bench receipts: (u_xr family, lo face edges) -> LO_AFTER_CTL measured on tb_vpx_ag with that form.  A form the RTL
# derives but no bench measured fails here: run vpx/xtier_vpx_gate.sh on it and add the receipt.
LO_RECEIPTS = {('ot_s81sl_xr', 0): 15,     # TOK-DS-9 10-27, results/token_pass/tokds9_1027/bench_vpx (xr sources.f)
               ('ot_s81sl_xrt', 1): 16}    # S81-XTIER-FIX 11-11, xtier_vpx_gate.sh VPX_DEFINES=OT_S81SL_KV_TRANSPORT
# xrt_bench.sh (tb_s81sl_xr against xrt1 / xrt3): p face landing 1 -> the partial sets issued one edge earlier PASS
P_RECEIPTS = {('ot_s81sl_xr', 0): 5, ('ot_s81sl_xrt', 1): 6}


def _env(**kw):
    env = {k: v for k, v in os.environ.items() if not k.startswith('OT_S81_')}
    env.update(kw)
    return env


def _consts(defines):
    """module-level constants of a fresh interpreter with OT_S81_SELECTED_DEFINES = defines"""
    code = ('import sys, json; sys.path[:0] = [sys.argv[1], sys.argv[2]]\n'
            'import lower_vpx as V, leaf_transport as T, dv_layer_compile as D, dv_price as P, norm_nx as N, xtier_land as X\n'
            'print(json.dumps(dict(lo=V.LO_AFTER_CTL, period=V.beat_period(), lo_local=T.LO_LOCAL, xfin=D.XFIN,'
            ' finish=P.FINISH_SEQ_EXTRA, leaf=P.LEAF_PARTIAL_EXTRA, scale=P.LEAF_SCALE_EXTRA, eng=P.ENG_SLICE_EST["eng.hh"],'
            ' nx=N.NX_AFTER_LAST_NORMR, normr=D.BEAT["go_to_partial_normr"], form=X.form())))')
    env = _env(PYTHONDONTWRITEBYTECODE='1')
    if defines is not None:
        env['OT_S81_SELECTED_DEFINES'] = ','.join(defines)
    r = subprocess.run([sys.executable, '-I', '-c', code, str(HERE), str(HERE.parent)], env=env, capture_output=True,
                       text=True, check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_die_form_is_landed_xrt():
    f = XT.form(KVT)
    assert f['family'] == 'ot_s81sl_xrt' and f['masters'] == ['ot_s81sl_xrt1', 'ot_s81sl_xrt3']
    assert f['face_land'] == 1 and f['ring_land'] == 0 and f['ring_edges'] == 0
    assert f['face_edges'] == dict(lo=1, p=1, e=1)


def test_unset_defines_select_the_asbuilt_die_form():
    """DIE_DEFINES (the default when OT_S81_SELECTED_DEFINES is unset) = the form every as-built die manifest selects"""
    want = XT.form(XT.DIE_DEFINES)
    seen = 0
    for p in sorted((ROOT / 'physical/die_plan/s81/bind').glob('asbuilt_*.json')):
        d = json.loads(p.read_text())
        if 'defines' not in d:
            continue
        f = XT.form(d['defines'])
        assert (f['family'], f['face_edges'], f['ring_edges']) == (want['family'], want['face_edges'], want['ring_edges']), p
        seen += 1
    assert seen >= 1


@pytest.mark.parametrize('defines', [None, KVT, ()])
def test_compiler_constants_follow_the_bound_rtl(defines):
    c = _consts(defines)
    f = c['form']
    fam, lo, p, e = f['family'], f['face_edges']['lo'], f['face_edges']['p'], f['face_edges']['e']
    assert (fam, lo) in LO_RECEIPTS, f'no tb_vpx_ag receipt for {fam} lo face {lo}: run vpx/xtier_vpx_gate.sh'
    assert (fam, p) in P_RECEIPTS, f'no xrt_bench receipt for {fam} p face {p}'
    assert c['lo'] == LO_RECEIPTS[(fam, lo)]
    assert c['lo_local'] == c['lo'] - 2 * f['slice_dl']
    assert c['xfin']['collector'] == P_RECEIPTS[(fam, p)] and c['xfin']['dl'] == f['slice_dl']
    assert c['leaf'] == c['normr'] + f['slice_dl'] + c['xfin']['collector'] - 100
    assert c['finish'] == c['xfin']['last_partial_to_rstd'] - 171 and c['scale'] == c['xfin']['rstd_to_xq_ring'] - 76
    assert c['eng'] == 129 + f['slice_dl'] + 5 + e
    assert c['nx'] == 143 + (c['normr'] - 117) + (c['xfin']['collector'] - 6)     # nx_probe_vpx.py on xrt: 143
    if defines is None or defines == KVT:
        assert (c['lo'], c['lo_local'], c['xfin']['collector'], c['nx'], c['eng']) == (16, 8, 6, 143, 139.0)
    else:
        assert (c['lo'], c['lo_local'], c['xfin']['collector'], c['nx'], c['eng']) == (15, 7, 5, 142, 138.0)


def test_rtl_mutants_are_refused_or_change_the_form():
    with pytest.raises(ValueError, match='bit-paths disagree'):          # e_v not landed: faces disagree
        XT.form(KVT + ('OT_S81SL_XRT_MUT_LAND_EVPIN',))
    f = XT.form(KVT + ('OT_S81SL_XRT_RFJ', 'OT_S81SL_XRT_MUT_RFJ_FPOS'))   # RF-J posedge pin flop: one edge more
    assert f['face_edges'] == dict(lo=2, p=2, e=2) and ('ot_s81sl_xrt', 2) not in LO_RECEIPTS
    assert XT.form(KVT + ('OT_S81SL_XRT_RFJ',))['face_edges'] == dict(lo=1, p=1, e=1)   # negedge + posedge = 1
    with pytest.raises(ValueError, match='ring landing'):                  # RING_LAND 1 moves CFG_AT: not measured
        XT.face_edges('lo', KVT + ('OT_S81SL_XRT_RLAND',))


def test_derivation_reads_the_rtl_default(tmp_path):
    """a tree whose xrt default is FACE_LAND 0 derives 0 face edges (the value is read, not assumed)"""
    for rel in (XT.SLICE, XT.XRT, XT.XR):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    p = tmp_path / XT.XRT
    s = p.read_text()
    old = '`else\n`define OT_S81SL_XRT_RLAND_DEF 0\n`define OT_S81SL_XRT_FLAND_DEF 1\n'
    assert s.count(old) == 1
    p.write_text(s.replace(old, '`else\n`define OT_S81SL_XRT_RLAND_DEF 0\n`define OT_S81SL_XRT_FLAND_DEF 0\n'))
    f = XT.form(KVT, root=tmp_path)
    assert f['face_land'] == 0 and f['face_edges'] == dict(lo=0, p=0, e=0)


def test_override_is_recorded():
    old = os.environ.get('OT_S81_XTIER_FACE_OVERRIDE')
    os.environ['OT_S81_XTIER_FACE_OVERRIDE'] = '{"lo": 0}'
    try:
        f = XT.form(KVT)
        assert f['face_edges']['lo'] == 0 and f['face_edges_override'] == {'lo': 0} and f['face_edges']['p'] == 1
    finally:
        if old is None:
            del os.environ['OT_S81_XTIER_FACE_OVERRIDE']
        else:
            os.environ['OT_S81_XTIER_FACE_OVERRIDE'] = old
    assert XT.form(KVT)['face_edges']['lo'] == 1


def test_asbuilt_period_is_the_emitted_leg_period():
    """beat_period() (what _stage_trel(None) / gen_vpx_ag space legs by) == the period leg_program emits"""
    import lower_vpx as LV
    leg = LV.leg_program(0, 'W', 14, LV.a_rows(0), t0=100)
    gaps = {b['cycle'] - a['cycle'] for a, b in zip(leg['sends'], leg['sends'][1:])}
    assert gaps == {LV.beat_period()} == {LV.beat_period(LV.LO_AFTER_CTL)}
    tr = [c['cycle'] for c in leg['ctl'] if c['target'] == 0]
    assert {b - a for a, b in zip(tr, tr[1:])} == {LV.beat_period()}
