import hard_ip_wrapper_cells as H

NET = """
module wrap (clk, arst_n, tx_up, rx_flit);
  input clk; input arst_n; output [1:0] tx_up; output [4:0] rx_flit;
  BUFx2_ASAP7_75t_R _0_ (
    .A(arst_n),
    .Y(tx_up[1])
  );
  BUFx2_ASAP7_75t_R _1_ (
    .A(arst_n),
    .Y(rx_flit[4])
  );
  BUFx2_ASAP7_75t_R _2_ (
    .A(\\u_bound.w[0] ),
    .Y(tx_up[0])
  );
  macro_x \\u_bound.u_core (
    .clk(clk)
  );
endmodule
"""


def test_epoch_buffers_exempt_other_cells_reported():
    r = H.wrapper_cells(NET, "wrap", "macro_x", {"tx_up[1]", "rx_flit[4]"})
    assert r["macro"] == ["\\u_bound.u_core"]
    assert [y for _, y in r["epoch_buffers"]] == ["tx_up[1]", "rx_flit[4]"]
    assert [o[3] for o in r["other"]] == ["tx_up[0]"]          # a non-epoch buffer is NOT exempt


def test_no_epoch_declared_means_every_buffer_is_reported():
    r = H.wrapper_cells(NET, "wrap", "macro_x", set())
    assert len(r["other"]) == 3 and not r["epoch_buffers"]


def test_epoch_pins_from_plan_flag():
    import schema as S
    P = S.Plan.__new__(S.Plan)
    P.parts = {"io": {"type": "phy"}, "c": {"type": "nb"}}
    P.ports = {"a": {"src": {"part": "c", "bus": "tx"}, "dst": {"part": "io", "bus": "tx_flit"}, "width": 597, "kind": "data"},
               "b": {"src": {"part": "io", "bus": "rx_flit"}, "dst": {"part": "c", "bus": "rx"}, "width": 597, "kind": "data", "epoch": False}}
    assert H.epoch_pins(P, "phy") == {"tx_flit[597]"}


def test_pin_alias_option_exempts_macro_output_buffers_only():
    r = H.wrapper_cells(NET, "wrap", "macro_x", {"tx_up[1]", "rx_flit[4]"}, pin_alias=True)
    assert [y for _, y in r["alias_buffers"]] == ["tx_up[0]"] and not r["other"]
    r = H.wrapper_cells(NET.replace("u_bound.w[0]", "other_net"), "wrap", "macro_x", {"tx_up[1]", "rx_flit[4]"}, pin_alias=True)
    assert len(r["other"]) == 1
