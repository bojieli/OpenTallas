// Candidate bit-opaque transport primitive. Model: a2a557599.
// ENABLE defaults off. Production links require the separately qualified
// end-to-end identity/checksum/consumer guard; this primitive is not an error
// detector. No selected die or pinned predecessor instantiates it.
module ot_hbm_result_relay_slice #(
    parameter integer W = 64,
    parameter integer ENABLE = 0
) (
    input wire clk,
    input wire rst_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (ENABLE != 0) begin : g_registered
        reg [W-1:0] payload;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) payload <= {W{1'b0}};
            else payload <= d;
        assign q = payload;
    end else begin : g_bypass
        assign q = d;
    end endgenerate
endmodule

module hfd_result_relay64_ew(input wire clk, rst_n,
    input wire [63:0] d, output wire [63:0] q);
    ot_hbm_result_relay_slice #(.W(64),.ENABLE(1)) u_stage(.*);
endmodule
module hfd_result_relay64_ns(input wire clk, rst_n,
    input wire [63:0] d, output wire [63:0] q);
    ot_hbm_result_relay_slice #(.W(64),.ENABLE(1)) u_stage(.*);
endmodule
