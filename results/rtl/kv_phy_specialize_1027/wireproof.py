from pathlib import Path
import json
import sys

sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-kv-phy-specialize-1027/tools/die_plan")
import specialize_serdes_phy as S

root = Path("wireproof")
root.mkdir(exist_ok=True)
for width in (521, 522):
    out = root / str(width); out.mkdir(exist_ok=True)
    master = S.LOGICAL + f"_w{width}"
    decl = "input wire clk, rst_n, output wire tx_up, input wire tx_v, input wire [W-1:0] tx_flit, output wire rx_v, output wire [W-1:0] rx_flit"
    ports = ".clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),.rx_v(rx_v),.rx_flit(rx_flit)"
    model = f"""// Wiring witness only: not an analog PHY behavior model.
module provider_model #(parameter W={width}) ({decl});
 assign tx_up=clk; assign rx_v=rst_n; assign rx_flit=tx_flit^{{W{{tx_v}}}};
endmodule
module {master} ({decl.replace('W-1', str(width-1))});
 provider_model #(.W({width})) u ({ports});
endmodule
module gold #(parameter W={width}) ({decl});
 provider_model #(.W(W)) u ({ports});
endmodule
module gate #(parameter W={width}) ({decl});
 {S.LOGICAL} #(.W(W)) u ({ports});
endmodule
"""
    dispatch = S.dispatcher(width, master)
    (out / "positive.sv").write_text(model + dispatch)
    assert ".tx_v(tx_v)" in dispatch
    (out / "mutant.sv").write_text(model + dispatch.replace(".tx_v(tx_v)", ".tx_v(~tx_v)", 1))
(root / "scope.json").write_text(json.dumps(dict(scope="Exact seven-port wire connection preservation only; physical views remain MODELED", widths=[521,522], expected_physical_instance="u_bound.u_core.u_phy.g_native.u_macro", analog_timing_or_PG_qualification=False), indent=1))
