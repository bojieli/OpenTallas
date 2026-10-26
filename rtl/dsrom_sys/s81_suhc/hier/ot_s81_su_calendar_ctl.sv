`timescale 1ns/1ps
// Fixed compiled microinstruction at edge `cycle`. Calendar ABI (LSB first):
// [15:0] request mask; [239:16] 16 x row14;
// [255:240] expected VM response mask at the EXTERNAL slab pins;
// [271:256] expected write mask; [495:272] 16 x write-row14;
// [751:496] 16 x word-mask16; [752] job announce;
// [756:753] kind; [758:757] gain-set; [759] FP4; [767:760] job-id;
// [768] done; [776:769] done-tag; [777] check-alive;
// [778] check-den; [779] check-ready; [787:780] ready-job-id;
// [788] fixed halt; [789] MOE operand pulse; [803:790] MOE output row;
// [1023:804] reserved zero. Requests/announce/done are registered on this edge;
// response/write expectations compare signals PRESENT BEFORE the same edge.
// Diagnostics never alter cycle, issue, data or completion timing, even on fault.
module ot_s81_su_calendar_ctl (
    input wire clk, rst_n, arm,
    input wire calendar_valid,
    input wire [31:0] calendar_cycle,
    input wire [1023:0] calendar_word,
    output reg [31:0] cycle,
    output reg [15:0] rq_v,
    output reg [223:0] rq_row,
    input wire [15:0] rs_v, wq_v,
    input wire [223:0] wq_row,
    input wire [255:0] wq_mask,
    output reg dn_st,
    output reg [3:0] dn_kind,
    output reg [1:0] dn_gsel,
    output reg dn_fp4,
    output reg [7:0] dn_jid,
    output reg moe_v,
    output reg [13:0] moe_row,
    output reg done,
    output reg [7:0] done_tag,
    input wire up_fu, up_fo, up_alive, up_den, up_rdy,
    input wire [7:0] up_rjid,
    output reg fault,
    output reg [3:0] fault_code,
    output reg running
);
    reg bad_write;
    always @* begin
        bad_write = (wq_v != calendar_word[271:256]);
        for (integer j=0; j<16; j=j+1)
            if (wq_v[j] && (wq_row[14*j+:14] != calendar_word[272+14*j+:14] ||
                           wq_mask[16*j+:16] != calendar_word[496+16*j+:16])) bad_write=1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle<=0; running<=0; fault<=0; fault_code<=0;
            moe_v<=0; moe_row<=0; rq_v<=0; rq_row<=0; dn_st<=0; dn_kind<=0; dn_gsel<=0;
            dn_fp4<=0; dn_jid<=0; done<=0; done_tag<=0;
        end else begin
            rq_v<=0; dn_st<=0; done<=0; moe_v<=0;
            if (arm) begin
                if (running) begin fault<=1; fault_code<=1; end
                else begin running<=1; cycle<=0; end
            end
            if (running) begin
                cycle<=cycle+1;
                if (calendar_word[788]) running<=0;
                moe_v<=calendar_word[789]; moe_row<=calendar_word[803:790];
                rq_v<=calendar_word[15:0]; rq_row<=calendar_word[239:16];
                dn_st<=calendar_word[752]; dn_kind<=calendar_word[756:753];
                dn_gsel<=calendar_word[758:757]; dn_fp4<=calendar_word[759];
                dn_jid<=calendar_word[767:760]; done<=calendar_word[768];
                done_tag<=calendar_word[776:769];
                // Latch the first observed failure, continue the compiled timeline.
                if (!fault) begin
                    if (!calendar_valid || calendar_cycle!=cycle || |calendar_word[1023:804]) begin fault<=1; fault_code<=2; end
                    else if (rs_v!=calendar_word[255:240]) begin fault<=1; fault_code<=3; end
                    else if (bad_write) begin fault<=1; fault_code<=4; end
                    else if (up_fu || up_fo) begin fault<=1; fault_code<=5; end
                    else if (calendar_word[777] && !up_alive) begin fault<=1; fault_code<=6; end
                    else if (calendar_word[778] && !up_den) begin fault<=1; fault_code<=7; end
                    else if (calendar_word[779] && (!up_rdy || up_rjid!=calendar_word[787:780])) begin fault<=1; fault_code<=8; end
                end
            end
        end
    end
endmodule
