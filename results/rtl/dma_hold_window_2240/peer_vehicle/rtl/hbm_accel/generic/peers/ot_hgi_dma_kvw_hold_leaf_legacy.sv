`timescale 1ns/1ps
module ot_hgi_dma_kvw_hold #(
    parameter integer NL = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NL*257-1:0] rsp,          // {v, data 256} a lane (the read group's lanes)
    input  wire              act,          // the core's registered busy
    input  wire [2*NL-1:0]   sel0,         // port 0 / 1 one-hot entry selects (entry 2 l + e), registered in the core
    input  wire [2*NL-1:0]   sel1,
    output reg  [NL-1:0]     hv,           // a response landed (registered)
    output reg  [255:0]      d0,
    output reg  [255:0]      d1
);
    reg [NL-1:0] pv, hw; reg [255:0] pd [0:NL-1]; reg [255:0] hd [0:2*NL-1];
    reg act_q; reg [2*NL-1:0] s0_q, s1_q;
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));   // relayed reset (control only)
    always @(posedge clk) begin s0_q <= sel0; s1_q <= sel1; end                                    // selects: no reset
    always @(posedge clk or negedge rr[0])
        if (!rr[0]) begin pv <= '0; hw <= '0; hv <= '0; act_q <= 1'b0; end
        else begin
            act_q <= act; hv <= pv;
            for (integer l = 0; l < NL; l = l + 1) begin
                pv[l] <= rsp[l*257 + 256] && act_q;
                if (pv[l]) hw[l] <= !hw[l];
            end
        end
    always @(posedge clk) begin : dp
        reg [255:0] o0, o1;
        for (integer l = 0; l < NL; l = l + 1) begin
            pd[l] <= rsp[l*257 +: 256];
            if (pv[l]) hd[2*l + hw[l]] <= pd[l];
        end
        o0 = 256'd0; o1 = 256'd0;
        for (integer k = 0; k < 2*NL; k = k + 1) begin
            o0 = o0 | (hd[k] & {256{s0_q[k]}}); o1 = o1 | (hd[k] & {256{s1_q[k]}});
        end
        d0 <= o0; d1 <= o1;
    end
endmodule
