"""contract v12 (hbmdie 10-13): granted child slots and the VM8 forwarded-clock die SDC of tools/hbm_accel_die_fp.py"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
_argv = sys.argv
sys.argv = [sys.argv[0]]
import hbm_accel_die_fp as F  # noqa: E402
sys.argv = _argv


class _I:
    def __init__(self, master, w, h):
        self.master, self.w, self.h = master, w, h


PARENTS = [_I('hfd_coll_tkm', *F.TKM_WH), _I('hfd_coll', 1399.656, 1561.68), _I('hfd_su', 2016.144, 2808.0),
           _I('hfd_cmdproc', 1399.656, 1403.976), _I('hfd_quant', 1399.656, F.QUANT_H)]


def test_children_fit_their_parents():
    out = F.child_slots_check(F.r25gq_v12_children(), PARENTS)
    assert sum(c['cell'] == 'ot_hgi_coll_tkm_tile' for c in out['hfd_coll_tkm']) == 32
    assert len(out['hfd_coll']) == 9 and len(out['hfd_su']) == 17
    assert out['hfd_quant'][0]['wh'] == [622.08, 596.16]
    seq = {c['name']: c for c in out['hfd_cmdproc']}
    assert seq['u_seq']['wh'] == [347.76, 272.16]
    assert [seq[n]['wh'] for n in ('u_seq.u_fe', 'u_seq.u_be', 'u_seq.u_au')] == [[248.4, 211.68], [88.56, 272.16], [254.88, 56.16]]


def test_overlapping_children_are_refused():
    ch = F.r25gq_v12_children()
    bad = dict(ch, hfd_cmdproc=ch['hfd_cmdproc'] + [dict(name='x', cell='ot_hgi_seq_au', wh=(50.0, 50.0),
                                                        xy=(F.SEQ_XY[0] + 10.0, F.SEQ_XY[1] + 10.0))])
    with pytest.raises(AssertionError):
        F.child_slots_check(bad, PARENTS)
    out_ = dict(ch, hfd_cmdproc=[dict(c, xy=(c['xy'][0] + 400.0, c['xy'][1])) if c['name'] == 'u_seq.u_be' else c
                                 for c in ch['hfd_cmdproc']])
    with pytest.raises(AssertionError):     # a grandchild outside its cluster slot
        F.child_slots_check(out_, PARENTS)


def test_vm8_forwarded_clocks_are_generated_clocks_and_etms_keep_the_arc():
    ports = F.vm8_fwd_clock_ports()
    assert sorted(ports) == [f'vm_cp_{t}' for t in sorted(F.VM8_FACE_TILES)]
    assert sum(len(v) for v in ports.values()) == 4 * 2 + 4 * 5
    sdc = F.vm8_fwd_clock_sdc()
    assert sdc.count('create_generated_clock') == 8 and sdc.count('-invert') == 8
    assert 'set_false_path' not in sdc.replace('# tile SDC: set_false_path', '')
    arcs = F.vm8_fwd_clock_etm_arcs()
    # 10-13 (v13): the arc must be a CLOCK arc (negative-unate combinational), not write_timing_model's data export:
    # the inverted generated clock read 0.8 ps / -251.7 ps on the raw export (tools/hier_contract/fclk_arc_fix.py)
    wrong = [(c, p, k, v) for c, d in arcs.items() for p, e in d.items() for k, v in e.items() if v != 'clock_arc']
    assert not wrong, wrong


def test_fclk_arc_fix_rewrites_the_data_export_as_one_clock_arc():
    import sys as _sys
    _sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
    import fclk_arc_fix as FA
    tab = lambda v: 'index_1("1, 2");\n          values("%s");' % v
    grp = lambda tt, r, f: ('timing() {\n        related_pin : "ck";\n        timing_type : %s;\n'
                            '        cell_rise(t) {\n          %s\n        }\n        rise_transition(t) {\n          %s\n        }\n'
                            '        cell_fall(t) {\n          %s\n        }\n        fall_transition(t) {\n          %s\n        }\n      }'
                            % (tt, tab(r), tab('10, 11'), tab(f), tab('9, 10')))
    lib = ('library(x) {\n  cell(c) {\n    pin("d[0]") {\n      direction : output;\n      ' + grp('rising_edge', '300, 301', '302, 303') +
           '\n    }\n    pin("f[1]") {\n      direction : output;\n      capacitance : 1.0;\n      ' +
           grp('rising_edge', '591, 592', '168, 169') + '\n      ' + grp('falling_edge', '178, 179', '-252, -251') +
           '\n    }\n    pin("z") {\n      direction : input;\n    }\n  }\n}\n')
    assert FA.arc_state(lib, 'f[1]') == 'data_arcs' and FA.arc_state(lib, 'z') == 'missing' and FA.arc_state(lib, 'd[0]') == 'other'
    out, st = FA.fix(lib, ['f[1]'])
    assert st == {'f[1]': 'data_arcs'} and FA.arc_state(out, 'f[1]') == 'clock_arc'
    blk = out[out.index('pin("f[1]")'):out.index('pin("z")')]
    assert blk.count('timing()') == 1 and 'negative_unate' in blk and 'combinational' in blk
    assert 'values("168, 169")' in blk and 'values("178, 179")' in blk       # the two physical edges
    assert '591' not in blk and '-252' not in blk                              # the re-referenced tables are gone
    assert out[:out.index('pin("f[1]")')] == lib[:lib.index('pin("f[1]")')] and FA.arc_state(out, 'd[0]') == 'other'
    assert FA.fix(out, ['f[1]'])[0] == out                                     # idempotent
