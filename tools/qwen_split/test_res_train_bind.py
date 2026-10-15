"""The die-name train serializer wrappers expose the exact source ABI the res_train bind relies on."""
from types import SimpleNamespace
import pytest
from qwen_split import res_train_bind as rtb
from qwen_split.source_pin_plan import rtl_ports


def test_wrapper_ports():
    for b in range(3):
        p = rtl_ports(rtb.ROOT / rtb.SOURCE, rtb.master(b))
        assert p['rq'] == (4425, 'input') and p['rb'] == (551, 'output') and p['fault'] == (1, 'output')
        assert all(p[c] == (1, 'input') for c in rtb.CLOCKS)
        assert set(rtb.COMMAND) <= set(p)


def _model():
    I = lambda n, m: SimpleNamespace(name=n, master=m, x=0, y=0, w=777.6, h=518.4)
    insts = [I(f'sp_res_ser_{b}', 'qfd_sp_res_ser') for b in range(3)] + [I(f'sp_port_tiles_{b}', f'qfd_port_tiles_{b}') for b in range(3)]
    buses = [('clk', 'clock_trunk', 1, [(f'sp_res_ser_{b}', 'ck') for b in range(3)]),
             ('rst_spine', 'reset', 1, [(f'sp_res_ser_{b}', 'rst_n') for b in range(3)])]
    for b in range(3):
        buses += [(f'rq_{b}', 'tree_spine', 4425, [(f'sp_port_tiles_{b}', 'rq'), (f'sp_res_ser_{b}', 'i')]),
                  (f'rs_{b}', 'tree_spine', 551, [(f'sp_res_ser_{b}', 'o'), ('sp_vector_memory', f'rb{b}')]),
                  (f'o4_me_en_rs{b}', 'spine_local', 1, [('tt_ctlm', f'mer{b}'), (f'sp_res_ser_{b}', 'me_en')]),
                  (f'rs_fault_{b}', 'spine_local', 1, [(f'sp_res_ser_{b}', 'fault'), ('tt_ctlm', f'rf{b}')])]
    return dict(insts=insts, buses=buses)


def test_apply_rewires_and_enumerates():
    m = _model()
    rec = rtb.apply(m)
    assert [i.master for i in m['insts'][:3]] == [rtb.master(b) for b in range(3)]
    assert rec['retired']['buses'] == [f'o4_me_en_rs{b}' for b in range(3)]
    assert sorted(rec['open_inputs']['sp_res_ser_1']) == sorted(rtb.COMMAND)
    clk = next(e for b, c, n, e in m['buses'] if b == 'clk')
    assert len(clk) == 3 * 25


def test_width_mismatch_refused():
    m = _model()
    m['buses'] = [(b, c, 4424 if b == 'rq_0' else n, e) for b, c, n, e in m['buses']]
    with pytest.raises(ValueError):
        rtb.apply(m)
