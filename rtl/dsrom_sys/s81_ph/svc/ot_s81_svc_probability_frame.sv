`timescale 1ns/1ps
// Compiler protocol extension: type14 is a natural row x16FP32 probability
// payload, 1..640 rows. Rewrite header to legacy type5 and ceil(rows/2)
// BF16-pair payload words. All other frames pass with one registered edge.
// Headers and payload advance on a fixed registered edge. The conversion
// emits one payload for every two input rows, with no readiness/backpressure.
module ot_s81_svc_probability_frame #(parameter integer MUT=0) (
    input wire clk, rst_n,
    input wire [514:0] q,
    output wire [514:0] q_o,
    output reg fault
);
    wire iv=q[0]; wire [511:0] id=q[512:1];
    reg in_frame, probability;
    reg [11:0] left;
    reg [9:0] row;
    reg [1:0] meta;
    reg [514:0] pass;
    wire header=iv&&!in_frame;
    wire native_header=header&&(id[511:508]==4'd14);
    wire pov,pdone,pfault; wire [8:0] pword; wire [511:0] pd;
    ot_s81_svc_probability_pack #(.MUT(MUT)) u_pack (
        .clk(clk),.rst_n(rst_n),.go(native_header),.rows(id[489:480]),
        .in_v(iv&&in_frame&&probability),.in_row(row),.in_d(id),
        .out_v(pov),.out_word(pword),.out_d(pd),.done(pdone),.fault(pfault));
    assign q_o=pov?{meta,pd,1'b1}:pass;
    reg [511:0] rewritten;
    always @* begin
        rewritten=id;
        rewritten[511:508]=4'd5;
        rewritten[491:480]=(id[491:480]+12'd1)>>1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin in_frame<=0;probability<=0;left<=0;row<=0;meta<=0;pass<=0;fault<=0;end
        else begin
            pass<=0;
            if(pfault)fault<=1;
            if(pov&&pass[0])fault<=1; // no two producers may own the output edge
            if(header)begin
                in_frame<=id[491:480]!=0;left<=id[491:480];
                probability<=native_header;row<=0;meta<=q[514:513];
                if(native_header)begin
                    pass<={q[514:513],rewritten,1'b1};
                    if(id[491:480]==0||id[491:480]>640)fault<=1;
                end else pass<=q;
            end else if(iv)begin
                if(!probability)pass<=q;
                if(probability)row<=row+10'd1;
                left<=left-12'd1;
                if(left==1)in_frame<=0;
            end
        end
    end
endmodule
