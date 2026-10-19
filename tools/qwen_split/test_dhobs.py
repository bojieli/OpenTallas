#!/usr/bin/env python3
"""MU-DQ-DHUSER 10-19 (COORD 0kg item 2): the Qwen compute MU die drives qfd_tt_ctlm_dv.dh_user from the observer
qfd_sys_face_mu_dhobs (no strap).  Tests: the observer's RTL lists == the compiled calendar, the die-case instance / nets
(dv_case._dhobs_inst / _dhobs_buses), die_params assignment + audit (e).

  python3 tools/qwen_split/test_dhobs.py      (repository root; also collected by pytest)
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools' / 'qwen_split')]
import die_port_bind as DPB  # noqa: E402
import die_params as P       # noqa: E402
from qwen_split import dv_case as DV  # noqa: E402
from qwen_static_schedule import mu_opcal as O  # noqa: E402

SRC = 'rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv'


def _mod(text=None):
    t = text if text is not None else (ROOT / SRC).read_text()
    return {m.name: m for m in DPB.parse_modules(t, SRC)}[P.DHOBS_MASTER]


def test_lists_match_compiled_calendar():
    d = O.dhobs_lists(O.compile_frame(16))
    assert d['NS'] == 45 and d['USER_SEQ'] == 0 and d['RES_SEQ'] == 1 << 44, d
    stg = [(d['STG_SEQ'] >> (6 * k)) & 63 for k in range(d['NS'])]
    assert stg == list(range(1, 37)) + [37] * 8 + [0], stg
    assert P.dhobs_check(_mod()) == []
    m = _mod()
    assert m.width('seq_dh', m.env()) == 187 and m.order == ['ck', 'rst_n', 'seq_dh', 'dh_user', 'res_user', 'mu_fault']


def test_stale_list_fails():
    t = (ROOT / SRC).read_text().replace("384'h9659659659659238a1", "384'h9659659659659238a2")
    f = P.dhobs_check(_mod(t))
    assert len(f) == 1 and 'STG_SEQ' in f[0], f
    t = (ROOT / SRC).read_text().replace("128'h0,", "128'h1,")
    assert any('USER_SEQ' in x for x in P.dhobs_check(_mod(t)))


class _I(SimpleNamespace):
    pass


def _keep():
    return [_I(name='tt_ctlm', master='qfd_tt_ctlm_dv', x=216.0, y=20271.224, w=777.6, h=1814.4, kind='k', region='r',
               domain='d'),
            _I(name='native59', master='qfd_native59_dv_service', x=216.0, y=22193.624, w=777.6, h=518.4, kind='k',
               region='r', domain='d')]


V = SimpleNamespace(Inst=lambda n, mst, x, y, w, h, **kw: _I(name=n, master=mst, x=x, y=y, w=w, h=h, **kw))


def test_instance_gated_and_placed():
    os.environ.pop('OT_SPLIT_DV_DHOBS_XY', None)
    os.environ['OT_QWEN_MU_NU'] = '1'
    keep, m = _keep(), {}
    assert DV._dhobs_inst(V, m, {}, keep) is None and len(keep) == 2         # single-user die: nothing added
    os.environ['OT_QWEN_MU_NU'] = '4'
    i = DV._dhobs_inst(V, m, {}, keep)
    assert i.name == 'mu_dhobs' and i.master == 'qfd_sys_face_mu_dhobs' and keep[-1] is i
    assert i.x + i.w <= 216.0 + 777.6 - 86.4 + 1e-6 and i.y >= 20271.224 + 1814.4 and i.y + i.h <= 22193.624, vars(i)
    os.environ['OT_SPLIT_DV_DHOBS_XY'] = '300,22170'                          # into native59: refused
    try:
        DV._dhobs_inst(V, {}, {}, _keep())
        raise AssertionError('overlap accepted')
    except ValueError as e:
        assert 'overlaps' in str(e)
    finally:
        os.environ.pop('OT_SPLIT_DV_DHOBS_XY', None)


def test_buses_and_fail_closed():
    os.environ['OT_QWEN_MU_NU'] = '4'
    m = {}
    DV._dhobs_inst(V, m, {}, _keep())
    out = [('dvw_sys_face_seq_dh', 'spine_local', 187, [('sys_face', 'seq_dh'), ('tt_ctlm', 'dh')])]
    crt = {('mu_dhobs', 'ck'): 'clk_x', ('mu_dhobs', 'rst_n'): 'rst_x'}
    DV._dhobs_buses(m, out, crt, lambda i, p: True)
    assert out[0][3][-1] == ('mu_dhobs', 'seq_dh') and out[0][2] == 187
    assert out[1] == ('dvw_mu_dhobs_dh_user', 'spine_local', 2, [('mu_dhobs', 'dh_user'), ('tt_ctlm', 'dh_user')])
    assert m['q3h']['dv_dhobs']['open_outputs'] == ['res_user', 'mu_fault']
    for out2, crt2, has in (([], crt, lambda i, p: True),                                   # no seq_dh bus
                            ([tuple(out[0])], {}, lambda i, p: True),                       # no clock / reset
                            ([tuple(out[0])], crt, lambda i, p: p != 'dh_user')):           # ctlm without dh_user
        try:
            DV._dhobs_buses(m, list(out2), dict(crt2), has)
            raise AssertionError('accepted')
        except ValueError:
            pass


def test_gen_params_mu():
    os.environ['OT_QWEN_MU_NU'] = '4'
    out, rec = P.gen_params([('tt_ctlm', P.TT_MASTER), ('mu_dhobs', P.DHOBS_MASTER)], [('dvw_hr_wi', None)])
    assert out[P.TT_MASTER]['NU'] == 4 and out[P.DHOBS_MASTER]['NU'] == 4 and rec['dhobs'] == dict(nu=4)
    os.environ['OT_QWEN_MU_NU'] = '1'
    out, rec = P.gen_params([('tt_ctlm', P.TT_MASTER), ('mu_dhobs', P.DHOBS_MASTER)], [('dvw_hr_wi', None)])
    assert P.DHOBS_MASTER not in out


if __name__ == '__main__':
    for k, f in sorted(globals().items()):
        if k.startswith('test_') and callable(f):
            f()
            print('ok', k)
