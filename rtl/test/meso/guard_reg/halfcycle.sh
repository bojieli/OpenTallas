#!/bin/bash
# Structural half-cycle census of one ring (W=64 DEPTH 4, KV kit form: CSC WREG WFALL): every rclk-domain path between
# flops of opposite edges, with its combinational depth (generic gates after synth -flatten).  usage: halfcycle.sh OUT
# Expected: STATUS_REG 0 oh -> glo0/ghi0 (rise -> fall, logic); STATUS_REG 1 w_n/lap_n -> glo1/ghi1 (fall -> rise, logic);
# GUARD_REG 1 only w_n -> w_p / lap_n -> lap_p (fall -> rise, 0 gate levels).
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"; cd "$OUT" || exit 2
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for v in "0 0" "1 0" "1 1"; do set -- $v
cat > hc_$1$2.sv <<EOT
module hc_top(input fclk, t_rst_n, clk, rst_n, input [5:0] k, input [63:0] d, output [63:0] q, output ready, fault);
  ot_dp_clk_landing_cas #(.W(64),.DEPTH(4),.CONTROL_STATUS_COPY(1),.WREG(1),.WFALL(1),.STATUS_REG($1),.GUARD_REG($2)) u (
    .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(rst_n),.rst_xn(1'b1),.strap_k(k),.d(d),.q(q),.ready(ready),.fault(fault));
endmodule
EOT
yosys -q -p "read_verilog -sv -DSYNTHESIS hc_$1$2.sv $R/rtl/common/ot_dp_clk_landing_ca.sv $R/rtl/common/ot_dp_clk_landing.sv $R/rtl/common/ot_meso_fifo.sv;
  hierarchy -top hc_top; setattr -mod -unset keep_hierarchy *; synth -flatten -top hc_top; opt_clean; write_json hc_$1$2.json" > hc_$1$2.ylog 2>&1
python3 -I "$H/halfcycle.py" hc_$1$2.json "STATUS_REG=$1 GUARD_REG=$2"
done
