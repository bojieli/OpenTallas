`timescale 1ns/1ps
// Fixed-cycle physical staging for the ECTL -> native head and score -> ECTL
// seams. Every bit advances every edge. No readiness, credit, enable or queue.
// A stage adds exactly one data edge after the common reset release window.
module ot_qkh_packet_pipe #(parameter integer W=519, parameter integer MUT=0)(
    input wire clk, rst_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer REGIONS=(W+127)/128;
    wire [REGIONS-1:0] local_reset_n;
    ot_rst_relay #(.REGIONS(REGIONS),.SYNC_STAGES(2),.TREE_STAGES(1)) u_reset
        (.clk(clk),.rst_n_in(rst_n),.rst_n(local_reset_n));
    (* keep = "true" *) reg [W-1:0] data_q;
    genvar r;
    generate for(r=0;r<REGIONS;r=r+1) begin:g_region
        localparam integer RW=((W-128*r)<128)?(W-128*r):128;
        always @(posedge clk or negedge local_reset_n[r])
            if(!local_reset_n[r]) data_q[128*r +:RW] <= {RW{1'b0}};
            else data_q[128*r +:RW] <= d[128*r +:RW];
    end endgenerate
    // Negative controls are elaboration parameters; the production value is 0.
    assign q=(MUT==1)?d:(MUT==2)?(data_q ^ {{(W-1){1'b0}},1'b1}):data_q;
endmodule

module ot_qkh_packet_fork2 #(parameter integer W=519, parameter integer MUT=0)(
    input wire clk0, clk1, rst_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q0, q1
);
    // Independent scalar clock roots are in the same compiler cycle family,
    // each delivered at phi-R. Distinct clock pins preserve both physical
    // launch banks through synthesis, instead of merging equal-value copies.
    ot_qkh_packet_pipe #(.W(W),.MUT(MUT==1?1:0)) u_branch0
        (.clk(clk0),.rst_n(rst_n),.d(d),.q(q0));
    ot_qkh_packet_pipe #(.W(W),.MUT(MUT==2?2:0)) u_branch1
        (.clk(clk1),.rst_n(rst_n),.d(d),.q(q1));
endmodule
