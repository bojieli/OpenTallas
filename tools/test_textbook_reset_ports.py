"""GATE-FRICTION 2026-10-18: declared reset_ports (and power-on-reset names) are resets for the fanout limits."""
import textbook_lint as TL


def test_declared_and_por_resets():
    assert TL.is_reset_net("port por_n", "por_n")                       # power-on reset by name
    assert TL.is_reset_net("port rst_n", "rst_n")
    assert not TL.is_reset_net("port pdata", "pdata")
    assert not TL.is_reset_net("port cfg_load", "cfg_load")
    assert TL.is_reset_net("port sys_clr", "sys_clr", {"reset_ports": "sys_clr,x"})
    assert TL.is_reset_net("port sys_clr[0]", "sys_clr[0]", {"reset_ports": ["sys_clr"]})
    assert not TL.is_reset_net("port sys_clr", "sys_clr", {"reset_ports": "other"})
    assert not TL.is_reset_net("port report", "report")                 # 'por' only as a word
