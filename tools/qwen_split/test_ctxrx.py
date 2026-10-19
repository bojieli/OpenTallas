#!/usr/bin/env python3
"""MU-DQ-BOOTCTX 10-19 (COORD 0kg (1)): the Qwen compute MU die binds the filler runtime-context leaf qfd_mu_ctx_rx_die
beside qfd_sys_face on the face's existing D2D RX nets and drives qfd_tt_ctlm_dv.ctx_x (CTX_SRC 1).  Tests: the leaf's
RTL ports, the die-case instance / nets (dv_case._ctxrx_inst / _ctxrx_buses, fail closed), die_params assignment.

  python3 tools/qwen_split/test_ctxrx.py      (repository root; also collected by pytest)
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


def test_leaf_ports():
    t = (ROOT / DV.CTXRX[2]).read_text()
    m = {x.name: x for x in DPB.parse_modules(t, DV.CTXRX[2])}[P.CTXRX_MASTER]
    assert m.order == ['ck', 'rst_n', 'prog_context_slot', 'prog_rx_v', 'rx_payload', 'ctx_x', 'ctx_user', 'mu_fault']
    assert m.width('rx_payload', m.env()) == 548 and m.width('ctx_x', m.env()) == 129
    c = {x.name: x for x in DPB.parse_modules((ROOT / 'rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text(), 'c')}['qfd_tt_ctlm_dv']
    assert c.width('ctx_x', c.env()) == 129 and c.env().get('CTX_SRC') == 0


class _I(SimpleNamespace):
    pass


def _keep():
    return [_I(name='tt_ctlm', master='qfd_tt_ctlm_dv', x=216.0, y=20271.224, w=777.6, h=1814.4, kind='k', region='r',
               domain='d'),
            _I(name='sys_face', master='qfd_sys_face', x=216.0, y=18000.0, w=600.0, h=400.0, kind='k', region='r',
               domain='d')]


V = SimpleNamespace(Inst=lambda n, mst, x, y, w, h, **kw: _I(name=n, master=mst, x=x, y=y, w=w, h=h, **kw))


def test_instance_gated_and_placed():
    os.environ.pop('OT_SPLIT_DV_CTXRX_XY', None)
    os.environ['OT_QWEN_MU_NU'] = '1'
    keep, m = _keep(), {}
    assert DV._ctxrx_inst(V, m, keep) is None and len(keep) == 2
    os.environ['OT_QWEN_MU_NU'] = '4'
    i = DV._ctxrx_inst(V, m, keep)
    assert i.name == 'mu_ctxrx' and i.master == P.CTXRX_MASTER and keep[-1] is i and i.y >= 18400.0
    os.environ['OT_SPLIT_DV_CTXRX_XY'] = '300,18100'                          # into sys_face: refused
    try:
        DV._ctxrx_inst(V, {}, _keep())
        raise AssertionError('overlap accepted')
    except ValueError as e:
        assert 'overlaps' in str(e)
    finally:
        os.environ.pop('OT_SPLIT_DV_CTXRX_XY', None)


def test_buses_and_fail_closed():
    os.environ['OT_QWEN_MU_NU'] = '4'
    m = {}
    DV._ctxrx_inst(V, m, _keep())
    base = [('lnk_rx_payload', 'tree_spine', 548, [('d2d_rom', 'rx_payload'), ('sys_face', 'rx_payload')]),
            ('sf_prog_rx_v', 'spine_local', 1, [('d2d_rom', 'prog_rx_v'), ('sys_face', 'prog_rx_v')]),
            ('sf_prog_context_slot', 'spine_local', 1, [('d2d_rom', 'prog_context_slot'), ('sys_face', 'prog_context_slot')])]
    out = [tuple(b) for b in base]
    crt = {('mu_ctxrx', 'ck'): 'clk_d2d', ('mu_ctxrx', 'rst_n'): 'rst_d2d'}
    DV._ctxrx_buses(m, out, crt, lambda i, p: True)
    assert out[0][3][-1] == ('mu_ctxrx', 'rx_payload') and out[1][3][-1] == ('mu_ctxrx', 'prog_rx_v')
    assert out[2][3][-1] == ('mu_ctxrx', 'prog_context_slot')
    assert out[3] == ('dvw_mu_ctxrx_ctx_x', 'spine_local', 129, [('mu_ctxrx', 'ctx_x'), ('tt_ctlm', 'ctx_x')])
    for out2, crt2, has in (([tuple(b) for b in base[:2]], crt, lambda i, p: True),        # no context-slot net
                            ([tuple(b) for b in base], {}, lambda i, p: True),              # no clock / reset
                            ([tuple(b) for b in base], crt, lambda i, p: p != 'ctx_x')):   # ctlm without ctx_x
        try:
            DV._ctxrx_buses(m, list(out2), dict(crt2), has)
            raise AssertionError('accepted')
        except ValueError:
            pass


def test_gen_params_mu():
    os.environ['OT_QWEN_MU_NU'] = '4'
    out, rec = P.gen_params([('tt_ctlm', P.TT_MASTER), ('mu_ctxrx', P.CTXRX_MASTER)], [('dvw_hr_wi', None)])
    assert out[P.TT_MASTER]['CTX_SRC'] == 1 and out[P.CTXRX_MASTER]['NU'] == 4 and rec['ctxrx'] == dict(nu=4)
    os.environ['OT_QWEN_MU_NU'] = '1'
    out, rec = P.gen_params([('tt_ctlm', P.TT_MASTER), ('mu_ctxrx', P.CTXRX_MASTER)], [('dvw_hr_wi', None)])
    assert P.CTXRX_MASTER not in out and 'CTX_SRC' not in out.get(P.TT_MASTER, {})


if __name__ == '__main__':
    for k, f in sorted(globals().items()):
        if k.startswith('test_') and callable(f):
            f()
            print('ok', k)
