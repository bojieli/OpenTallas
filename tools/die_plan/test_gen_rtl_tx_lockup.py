"""TX-face lockup latch (XCHECK-1 11-03): an out bus whose die port lands on a HARD PHY-model partition gets
flop -> ot_dp_lk (negative-level) -> pin; other out buses keep the plain boundary flop; "tx_lockup": false opts out."""
import gen_rtl


class _P:
    def __init__(self, types, parts, ports):
        self.types = types
        self.parts = {p["name"]: p for p in parts}
        self.raw = {"ports": ports}


def _plan(src_flag=None, phy_module="ot_qfd_ucie_x64_phy", phy_hard=True):
    src = {"module": "m_src", "buses": [{"name": "tx", "dir": "out", "width": 8}, {"name": "o", "dir": "out", "width": 4}]}
    if src_flag is not None:
        src["tx_lockup"] = src_flag
    types = {"src": src,
             "phy": {"module": "m_phy", "hard": phy_hard, "contents": [{"inst": "u_phy", "module": phy_module}]},
             "core": {"module": "m_core", "contents": [{"inst": "u", "module": "logic_blk"}]}}
    parts = [{"name": "a", "type": "src"}, {"name": "b", "type": "src"}, {"name": "p0", "type": "phy"},
             {"name": "c0", "type": "core"}]
    ports = [{"id": "1", "src": {"part": "a", "bus": "tx"}, "dst": {"part": "p0", "bus": "tx_flit"}},
             {"id": "2", "src": {"part": "b", "bus": "o"}, "dst": {"part": "c0", "bus": "i"}}]
    return _P(types, parts, ports)


def test_bus_into_hard_phy_is_latched():
    assert gen_rtl.phy_tx_buses(_plan(), "src") == {"tx"}


def test_opt_out_and_non_phy_targets():
    assert gen_rtl.phy_tx_buses(_plan(src_flag=False), "src") == set()
    assert gen_rtl.phy_tx_buses(_plan(phy_module="logic_blk"), "src") == set()
    assert gen_rtl.phy_tx_buses(_plan(phy_hard=False), "src") == set()   # soft wrapper: its own RTL registers


def test_cell_is_negative_level_latch():
    c = gen_rtl.CELLS
    assert "module ot_dp_lk" in c and "always_latch if (!clk) q = d;" in c
