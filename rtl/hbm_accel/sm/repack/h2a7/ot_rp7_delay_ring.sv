`timescale 1ns/1ps
// Fixed-latency schedule compensation, with eight-bit local one-hot rings.
// There is no backpressure.  After reset, every edge writes one slot and
// reads the next slot: a three-slot ring therefore delays exactly 3 edges.
// Small kept leaves bound each select/write decode even if wr/rd merge.
module ot_rp7_ring_chunk #(parameter integer W=8, ID=0)
 (input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep *) reg [2:0] phase;
    reg [W-1:0] a,b,c;
    always @(posedge clk) begin
        if (!rst_n) phase<=3'b001;
        else phase<={phase[1:0],phase[2]};
        if (phase[0]) a<=d;
        if (phase[1]) b<=d;
        if (phase[2]) c<=d;
    end
    assign q=({W{phase[0]}}&a)|({W{phase[1]}}&b)|({W{phase[2]}}&c);
endmodule

module ot_rp7_delay_ring #(parameter integer W=1,N=3)
 (input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q);
    localparam integer NC=(W+7)/8, NG=(NC+31)/32, ST=N/3;
    wire [W-1:0] stage[0:ST];
    assign stage[0]=d;
    assign q=stage[ST];
    for(genvar s=0;s<ST;s=s+1) begin:g_stage
        wire [NG-1:0] branch;
        wire [NC-1:0] ready;
        for(genvar g=0;g<NG;g=g+1) begin:g_reset_group
            (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(24000+s*NG+g)) u_branch
                (.ck(clk),.d(rst_n),.q(branch[g]));
        end
        for(genvar k=0;k<NC;k=k+1) begin:g_chunk
            localparam integer CW=(W-k*8<8)?W-k*8:8;
            (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(32000+s*NC+k)) u_ready
                (.ck(clk),.d(branch[k/32]),.q(ready[k]));
            (* keep_hierarchy="yes" *) ot_rp7_ring_chunk #(.W(CW),.ID(s*NC+k)) u_ring
                (.clk(clk),.rst_n(ready[k]),.d(stage[s][k*8+:CW]),.q(stage[s+1][k*8+:CW]));
        end
    end
`ifndef SYNTHESIS
    initial if(N<3 || N%3) $fatal(1,"R7 delay requires multiples of three edges");
`endif
endmodule
