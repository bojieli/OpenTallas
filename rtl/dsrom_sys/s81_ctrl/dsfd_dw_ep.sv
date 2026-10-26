`timescale 1ns/1ps
// dsfd_dw_ep_s / dsfd_dw_ep_c (s81-ctl-1011, 2026-10-11): the sel (engine 5) / col (engine 6) command endpoint TILES of the
// selector / collector slabs (ADAPTER_CONTRACT_1011): ot_s81_done_word on a snoop of the slab's vd output (the word stream
// to the VM), so the closed vd-driving tiles (dsfd_selt_c / dsfd_colt_mrg) stay unchanged: the slab composition fans the
// snooped bits out to this tile too.
//   vh = {vd[513:502] (type 4, tag 8), vd[493:482] (frame length 12), vd[1] (valid), vd[0] (slab rst_n)} 26 b in,
//   c_cmd 85 in, c_done 9 out, c_st 2 out.
// FRAMED (collector): a header word of type 1..3 is followed by `length` raw data words, which are NOT typed words (a data
// word may carry any value in [511:508]); the endpoint skips them, so only real DONE / FAULT words are seen.
// _s: selector (typed words only; its DONE word sent once after reset precedes any job: SKIP_FIRST 1);
// _c: collector (FRAMED, SKIP_FIRST 0).
module dsfd_dw_ep #(parameter integer SKIP_FIRST = 0, parameter integer FRAMED = 0,
                    parameter integer MUT = `ifdef OT_S81_DW_MUT `OT_S81_DW_MUT `else 0 `endif) (
    input wire [0:0] ck, input wire [0:0] rst,
    input wire [25:0] vh,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    wire [3:0] ty = vh[25:22]; wire [11:0] len = vh[13:2]; wire v = vh[1];
    reg [1:0] rs_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    reg [11:0] left;
    wire in_frame = (FRAMED != 0) && left != 0;
    always @(posedge ck[0] or negedge rs_s[1])
        if (!rs_s[1]) left <= 12'd0;
        else if (FRAMED != 0 && v) begin
            if (left != 0) left <= left - 1'b1;
            else if (ty >= 4'd1 && ty <= 4'd3) left <= len;
        end
    wire [513:0] vd = {vh[25:14], 500'd0, v && !in_frame, vh[0]};
    ot_s81_done_word #(.SKIP_FIRST(SKIP_FIRST), .MUT(MUT)) u_dw (.ck(ck[0]), .rst(rst[0]), .vd(vd), .c_cmd(c_cmd),
        .c_done(c_done), .c_st(c_st));
endmodule
module dsfd_dw_ep_s (input wire [0:0] ck, input wire [0:0] rst, input wire [25:0] vh,
                     input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st);
    dsfd_dw_ep #(.SKIP_FIRST(1), .FRAMED(0)) u (.ck(ck), .rst(rst), .vh(vh), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
module dsfd_dw_ep_c (input wire [0:0] ck, input wire [0:0] rst, input wire [25:0] vh,
                     input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st);
    dsfd_dw_ep #(.SKIP_FIRST(0), .FRAMED(1)) u (.ck(ck), .rst(rst), .vh(vh), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
