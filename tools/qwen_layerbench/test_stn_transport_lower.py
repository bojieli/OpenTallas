"""QC-TRANSPORT-FIX-4 11-09: the bound-plan station result shift (DV_STN_TRANSPORT) in the matvec lowering."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_lower as D  # noqa: E402
import dv_lower_mat as M  # noqa: E402
import stn_transport_params as P  # noqa: E402

AGES = dict(l8_ar=30, ar_hop=2, amax_ami=3, arx_after_amv=20, xc_cc=1)   # placeholder (structure tests only)
# the 282ca18ef6cc final second-switch values (stn_transport_params on its bind2)
FINAL = dict(W5=(42, 4), W4=(42, 3), W3=(42, 3), W2=(42, 4), W1=(42, 3), W0=(41, 3),
             E0=(55, 3), E1=(54, 3), E2=(55, 4), E3=(54, 3), E4=(55, 3), E5=(54, 3))
BUSY = dict(W5=32, W4=32, W3=32, W2=32, W1=32, W0=31, E0=33, E1=32, E2=33, E3=32, E4=33, E5=32)


def _write(table, schema=P.SCHEMA):
    f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump(dict(schema=schema, slices={s: dict(result=r, cfg=c, busy=BUSY[s] if r else 0) for s, (r, c) in table.items()}), f)
    f.close()
    return f.name


def _with(path, fn):
    saved = os.environ.pop('DV_STN_TRANSPORT', None)
    try:
        if path is not None:
            os.environ['DV_STN_TRANSPORT'] = path
        return fn()
    finally:
        os.environ.pop('DV_STN_TRANSPORT', None)
        if saved is not None:
            os.environ['DV_STN_TRANSPORT'] = saved


def _mv(name):
    return lambda: M.lower_matvec(name, 900, AGES, M.Chain(D.slice_map()))


def test_default_is_none():
    assert _with(None, D.stn_transport) is None
    assert _with(None, lambda: M.stn_result_shift(3)) == 0


def test_zero_table_is_identical():
    z = _write({s: (0, 0) for s in FINAL})
    for name in ('o', 'qkv', 'gu'):
        assert _with(None, _mv(name)) == _with(z, _mv(name))


def test_bad_schema_raises():
    b = _write(FINAL, schema='x')
    try:
        _with(b, D.stn_transport)
    except D.LowerError:
        return
    raise AssertionError('bad schema accepted')


def test_ar_results_keep_their_edges_far_moves_earlier():
    f = _write(FINAL)
    a, b = _with(None, _mv('o')), _with(f, _mv('o'))
    assert a['expected_ar'] == b['expected_ar']           # the AR word edges at W5 are the XC contract
    names = D.slice_map()['names']
    for da, db in zip(a['deliveries'], b['deliveries']):
        sh = FINAL[names[da['slice']][4:]][0]
        assert [x - sh for x in da['far']] == db['far']
    for sa, sb in zip(a['stn'], b['stn']):
        r, c = FINAL[names[sa['slice']][4:]]
        assert sb['land'] <= sa['land'] - r + c          # the config moves with the earliest word, never later
    assert _with(f, lambda: M.ar_collisions(b, AGES)) == []


def test_one_off_shift_is_seen():
    f = _write(FINAL)
    g = _write({**FINAL, 'E0': (FINAL['E0'][0] + 1, FINAL['E0'][1])})
    assert _with(f, _mv('o'))['deliveries'] != _with(g, _mv('o'))['deliveries']


def test_vm_far_unchanged():
    f = _write(FINAL)
    a, b = _with(None, _mv('qkv')), _with(f, _mv('qkv'))
    assert [d['far'] for d in a['deliveries']] == [d['far'] for d in b['deliveries']]
    assert a['expected_vm'] == b['expected_vm']


def test_params_tool_on_record():
    rows = {str(r): dict(E=25 if r < 4 else 36, SKEW_S=9, SKEW_N=6, HI_PAD=17 if r < 4 else 28,
                         RD_PAD=0 if r < 4 else 1) for r in range(8)}
    rec = dict(slices={s: dict(regions=rows) for s in P.SLICES})
    lanes = {(s, r): (17 if r < 4 else 5) for s in P.SLICES for r in range(8)}
    cpin = {s: 4 for s in P.SLICES}
    out = P.derive(rec, lanes, cpin)
    assert out['W5']['result'] == 42 and out['W5']['cfg'] == 4 and out['W5']['busy'] == 32
    try:                                                   # config later than the first word -> fail closed
        P.derive(rec, lanes, dict(cpin, W5=9))
        raise AssertionError('late STN config accepted')
    except P.ParamError:
        pass
    bg = dict(landing=[dict(sink=f'dvs_{s}.u_core.u_sub.u_r{r}', members=[dict(sink_port=p, landed_stages=4 + int((s, r, p) == ('E3', 5, 'cfg_v_p')), asbuilt_stages=0) for p in P.CFG_PINS]) for s in P.SLICES for r in range(8)])
    try:                                                   # one config pin with another shift -> fail closed
        P.cfg_lanes(bg)
        raise AssertionError('non-uniform config pin shift accepted')
    except P.ParamError:
        pass
    lanes[('W5', 4)] = 6                                   # RD_PAD no longer matches -> fail closed
    try:
        P.derive(rec, lanes, cpin)
    except P.ParamError:
        return
    raise AssertionError('RD_PAD mismatch accepted')
