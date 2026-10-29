"""Declared PHY pads participate in the exact kit port contract."""
from types import SimpleNamespace

import gen_phys as G
import port_bind_gate as B


def test_head_pma_pads_exact_inventory(monkeypatch):
    pads = [dict(name="pma_tx", dir="out", width=544),
            dict(name="pma_tck", dir="out", width=1, clock=True),
            dict(name="pma_rx", dir="in", width=544),
            dict(name="pma_rck", dir="in", width=1, clock=True)]
    p = SimpleNamespace(types={"t": dict(pads=pads)})
    monkeypatch.setattr(G, "tap_pins", lambda *_: [("clk", 1, 1)])
    monkeypatch.setattr(G, "reset_out_pins", lambda *_: [])
    pins = G.port_bind_pin_records(p, "t", [])
    text = ("module top(clk,pma_tx,pma_tck,pma_rx,pma_rck);\ninput clk;\n"
            "output [543:0] pma_tx;\noutput pma_tck;\n"
            "input [543:0] pma_rx;\ninput [0:0] pma_rck;\nendmodule\n")
    r = B.check(text, "top", pins)
    assert r["verdict"] == "PASS" and r["plan_bits"] == 1091
    # The old inventory rejects all 1090 legitimate PHY bits.
    assert B.check(text, "top", [dict(bus="clk", bit=None)])["extra"] == 1090
    assert B.check(text.replace("input [543:0] pma_rx;", "input [542:0] pma_rx;"),
                   "top", pins)["missing"] == 1
    assert B.check(text.replace("input clk;", "input clk;\ninput rogue;"), "top", pins)["extra"] == 1
