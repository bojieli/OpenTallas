`timescale 1ns/1ps
// Compiler protocol extension: type14 is a natural row x16FP32 probability
// payload, 1..640 rows. Rewrite header to legacy type5 and ceil(rows/2)
// BF16-pair payload words. All other frames pass with one registered edge.
// Dedicated input and output pin registers enclose the conversion stage.
// Fixed latency is three accepting edges (capture, convert, output); the
// compiler reserves all three. No readiness/backpressure is present.
module ot_s81_svc_probability_frame #(parameter integer MUT=0) (
    input wire clk, rst_n,
    input wire [514:0] q,
    output wire [514:0] q_o,
    output reg fault
);
    reg pin_v, output_v;
    reg [513:0] pin_d, output_d;
    wire [514:0] pin_q={pin_d,pin_v};
    wire iv=pin_v; wire [511:0] id=pin_d[511:0];
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin pin_v<=0;output_v<=0;end
        else begin pin_v<=q[0];output_v<=selected[0];end
    always @(posedge clk)begin pin_d<=q[514:1];output_d<=selected[514:1];end
    assign q_o={output_d,output_v};
    reg in_frame, probability;
    reg [11:0] left;
    reg [9:0] row;
    reg [1:0] meta;
    reg pass_v; reg [513:0] pass_d;
    wire [514:0] pass={pass_d,pass_v};
    wire header=iv&&!in_frame;
    wire native_header=header&&(id[511:508]==4'd14);
    wire pov,pdone,pfault; wire [8:0] pword; wire [511:0] pd;
    ot_s81_svc_probability_pack #(.MUT(MUT)) u_pack (
        .clk(clk),.rst_n(rst_n),.go(native_header),.rows(id[489:480]),
        .in_v(iv&&in_frame&&probability),.in_row(row),.in_d(id),
        .out_v(pov),.out_word(pword),.out_d(pd),.done(pdone),.fault(pfault));
    wire [514:0] selected=pov?{meta,pd,1'b1}:pass;
    reg [511:0] rewritten;
    always @* begin
        rewritten=id;
        rewritten[511:508]=4'd5;
        rewritten[491:480]=(id[491:480]+12'd1)>>1;
    end
    // Payload capture has no reset-dependent enable. Only pass_v controls
    // visibility; keeping reset off this 514-bit data path avoids fanout.
    always @(posedge clk) begin
        if(header) pass_d<=native_header?{pin_q[514:513],rewritten}:pin_q[514:1];
        else if(iv&&!probability) pass_d<=pin_q[514:1];
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin in_frame<=0;probability<=0;left<=0;row<=0;meta<=0;pass_v<=0;fault<=0;end
        else begin
            pass_v<=0;
            if(pfault)fault<=1;
            if(pov&&pass[0])fault<=1; // no two producers may own the output edge
            if(header)begin
                in_frame<=id[491:480]!=0;left<=id[491:480];
                probability<=native_header;row<=0;meta<=pin_q[514:513];
                if(native_header)begin
                    pass_v<=1;
                    if(id[491:480]==0||id[491:480]>640)fault<=1;
                end else pass_v<=iv;
            end else if(iv)begin
                if(!probability)pass_v<=iv;
                if(probability)row<=row+10'd1;
                left<=left-12'd1;
                if(left==1)in_frame<=0;
            end
        end
    end
endmodule
