`timescale 1ns/1ps
// Opt-in typed510-bit bridge packet codec. Caller reserves space before each i_v.
// No clock crossing, transaction ownership, epoch fence or mutable-state protection here.
module ot_qwen_kvc_packet_encode #(parameter integer ENABLE=0)(
    input wire clk,rst_n,i_v,
    input wire [3:0] i_op,
    input wire [7:0] i_epoch,
    input wire [6:0] i_pc,
    input wire [15:0] i_seq,
    input wire [8:0] i_tag,
    input wire [23:0] i_sec,
    input wire [255:0] i_data,
    output reg o_v,o_bad,
    output reg [509:0] o_packet
);
    function automatic [31:0] crc32(input [477:0] body);
        reg [31:0] c; reg feedback; integer bitno;
        begin
            c=32'hffffffff;
            for(bitno=477;bitno>=0;bitno=bitno-1) begin
                feedback=c[31]^body[bitno];
                c={c[30:0],1'b0};
                if(feedback) c=c^32'h04c11db7;
            end
            crc32=c^32'hffffffff;
        end
    endfunction
    wire [477:0] body={4'd1,i_op,i_epoch,i_pc,i_seq,i_tag,i_sec,i_data,150'd0};
    wire legal=(i_op==4'd1) || ((i_op==4'd2) && (i_sec==0) && (i_data==0));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin o_v<=0; o_bad<=0; end
        else begin
            o_v<=(ENABLE!=0) && i_v && legal;
            o_bad<=(ENABLE!=0) && i_v && !legal;
        end
    end
    always @(posedge clk) begin
        if(ENABLE!=0) o_packet<={body,crc32(body)};
        else o_packet<=510'd0;
    end
endmodule

module ot_qwen_kvc_packet_decode #(parameter integer ENABLE=0)(
    input wire clk,rst_n,i_v,
    input wire [509:0] i_packet,
    output reg o_v,o_bad,
    output reg [509:0] o_packet,
    output wire [3:0] o_op,
    output wire [7:0] o_epoch,
    output wire [6:0] o_pc,
    output wire [15:0] o_seq,
    output wire [8:0] o_tag,
    output wire [23:0] o_sec,
    output wire [255:0] o_data
);
    function automatic [31:0] crc32(input [477:0] body);
        reg [31:0] c; reg feedback; integer bitno;
        begin
            c=32'hffffffff;
            for(bitno=477;bitno>=0;bitno=bitno-1) begin
                feedback=c[31]^body[bitno];
                c={c[30:0],1'b0};
                if(feedback) c=c^32'h04c11db7;
            end
            crc32=c^32'hffffffff;
        end
    endfunction
    wire legal_op=(i_packet[505:502]==4'd1) ||
        ((i_packet[505:502]==4'd2) && (i_packet[461:438]==0) && (i_packet[437:182]==0));
    wire legal=(i_packet[509:506]==4'd1) && legal_op &&
        (i_packet[181:32]==0) && (i_packet[31:0]==crc32(i_packet[509:32]));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin o_v<=0; o_bad<=0; end
        else begin
            o_v<=(ENABLE!=0) && i_v && legal;
            o_bad<=(ENABLE!=0) && i_v && !legal;
        end
    end
    always @(posedge clk) begin
        if(ENABLE!=0) o_packet<=i_packet;
        else o_packet<=510'd0;
    end
    assign {o_op,o_epoch,o_pc,o_seq,o_tag,o_sec,o_data}=o_packet[505:182];
endmodule
