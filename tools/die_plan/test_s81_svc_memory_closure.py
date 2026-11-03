"""Fast checks of the S81 svc memory-closure class port (full chain self-check = 12605dc2 is the packet run)."""
import pytest
import s81_svc_memory_closure as c


def test_reference_is_t7_original():
    assert c.sha(c.ref_text()).startswith('61c902f1')


def test_reference_applies_and_ports_with_identity_map():
    ref = c.ref_text()
    assert c.applies(ref)
    rn, tn, m = c.name_map(ref, ref)
    assert rn == tn == 'u_rsv_14_'
    for step in ('pmem', 'pvq', 'land', 'stage'):
        src, _ = c.port_source(c.REF[step].read_text(), tn, m, rn)
        assert 'hash lock -> class port' in src
        compile(src, step, 'exec')


def test_unmapped_reference_net_refuses():
    ref = c.ref_text()
    rn, tn, m = c.name_map(ref, ref)
    m = {k: v for k, v in m.items() if 'procmux_69594' not in k}
    with pytest.raises(ValueError, match='unmapped reference net'):
        c.port_source(c.REF['land'].read_text(), tn, m, rn)


def test_head_detects_wrapper_level():
    assert c.rsv('w_u_rsv_05_u_u_u_att_x w_u_rsv_05_u_y') == 'u_rsv_05_u_'
    assert c.rsv('w_u_rsv_01_u_u_att_x') == 'u_rsv_01_'
    with pytest.raises(ValueError):
        c.rsv('w_u_rsv_01_u_u_att_x w_u_rsv_02_u_u_att_x')


def test_not_applicable_without_helpers():
    assert not c.applies('module m; endmodule\n')
