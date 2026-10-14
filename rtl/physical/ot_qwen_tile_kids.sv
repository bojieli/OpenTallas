`timescale 1ns/1ps
// q18 (2026-10-13): the hardened children of the THIN Qwen ROM die tile and their wiring -- nothing else.  The tile is
//   ot_qwen_tile_ctl (control leaf = ot_qwen_rom_tile_logic_w12 CEXT 1: every tile register that is not inside a
//   hardened child) + this module: CODE_BANKS x ot_qwen_tile_rpair (bank rows), 8 x ot_qwen_tile_lsl (lane slices),
//   ot_qwen_tile_node (tree node + the t_out pin registers).  No register and no gate here: wires between child pins,
//   the control leaf's cx_* seams and the tile pins (n_a / n_b / n_va / n_y / n_vy / t_out / t_vout are the node's own
//   pins).  The array bench instantiates this same module next to the control logic (ot_qwen_me_array_w12 CTH 1), so the
//   wiring that is routed is the wiring that is simulated.
//   RPS 1 (bench): the bank rows as ot_qwen_rpair_logic with the macros outside (rom_req_m / rom_rd, the bench's hash
//   images); RPS 0 (silicon): the hardened leaf ot_qwen_tile_rpair, which owns its two macros.
//   CMUT (bench mutants of THIS wiring, each must fail the exact bench): 1 = bank row 0's relay word with its two
//   column halves swapped; 2 = lane-slice leaves 0 and 1 fed each other's transmit rung; 3 = lane-slice leaves 2 and 3
//   returning each other's results; 4 = invert the node fault seam (observed by the assembled array fault checker).
module ot_qwen_tile_kids #(
    parameter integer CODE_BANKS = 5,
    parameter integer RPS = 0,
    parameter integer ROM_MUT = 0,
    parameter integer TMUT = 0,
    parameter integer CMUT = 0,
    parameter integer MCLK = 0,
    parameter integer SPLIT = 0
) (
    input  wire          clk,
    input  wire [CODE_BANKS-1:0] clk_rp,
    input  wire [7:0] clk_sl,
    input  wire clk_node,
    input wire [7:0] clk_tx,
    input wire [1:0] clk_rqr,
    input  wire          rst_n,
    // control-leaf seams
    input  wire [CODE_BANKS*14-1:0]   cx_rreq,
    output wire [CODE_BANKS*1024-1:0] cx_rq,
    output wire [2047:0] cx_rqr,
    input  wire [8*391-1:0]  cx_ld,
    output wire [8*73-1:0]   cx_lq,
    input  wire [511:0]      cx_td,
    input  wire              cx_tvd,
    output wire              cx_nfault,
    // tile pins of the node leaf
    input  wire [511:0]      n_a,
    input  wire [511:0]      n_b,
    input  wire              n_va,
    output wire [511:0]      n_y,
    output wire              n_vy,
    output wire [511:0]      t_out,
    output wire              t_vout,
    // RPS 1: the macros' pins (column p, bank b at p*CODE_BANKS+b)
    output wire [2*CODE_BANKS*13-1:0]  rom_req_m,
    input  wire [2*CODE_BANKS*266-1:0] rom_rd
);
    wire [511:0] node_td;
    genvar b, g;
    generate
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_rb
            wire row_clk = (MCLK != 0) ? clk_rp[b] : clk;
            wire [1023:0] r_q;
            wire          ce_d  = cx_rreq[14*b];
            wire          any_d = cx_rreq[14*b + 1];
            wire [11:0]   ad_d  = cx_rreq[14*b + 2 +: 12];
            if (RPS != 0) begin : g_sf
                wire [25:0] rq;
                ot_qwen_rpair_logic #(.PWB(256), .ROM_CAP2(1), .ROM_CAPX(2), .ROM_MUT(ROM_MUT),
                    .MUT3((TMUT == 3 && b == 0) ? 1 : 0), .MUT5((TMUT == 5 && b == 0) ? 1 : 0)) u_rp (
                    .clk(row_clk), .rst_n(rst_n), .ce_d(ce_d), .any_d(any_d), .ad_d(ad_d), .req_m(rq),
                    .rd({rom_rd[(CODE_BANKS + b)*266 +: 256], rom_rd[b*266 +: 256]}), .r_q(r_q));
                assign rom_req_m[13*b +: 13] = rq[12:0];
                assign rom_req_m[13*(CODE_BANKS+b) +: 13] = rq[25:13];
            end else begin : g_hd
                ot_qwen_tile_rpair u_rp (.clk(row_clk), .rst_n(rst_n), .ce_d(ce_d), .any_d(any_d), .ad_d(ad_d), .r_q(r_q));
                assign rom_req_m[13*b +: 13] = 13'd0;
                assign rom_req_m[13*(CODE_BANKS+b) +: 13] = 13'd0;
            end
            if (CMUT == 1 && b == 0) begin : g_m1
                assign cx_rq[1024*b +: 1024] = {r_q[511:0], r_q[1023:512]};
            end else begin : g_ok
                assign cx_rq[1024*b +: 1024] = r_q;
            end
        end
        for (g = 0; g < 8; g = g + 1) begin : g_sl
            localparam integer GS = (CMUT == 2 && g < 2) ? (1 - g) : g;      // transmit source
            localparam integer GR = (CMUT == 3 && (g == 2 || g == 3)) ? (5 - g) : g;   // result destination
            wire [390:0] raw_ld = {cx_ld[391*g + 390], cx_ld[391*GS +: 390]};
            wire [390:0] ld;
            if (SPLIT != 0) begin : g_tx_leaf
                ot_qwen_tile_tx u_tx (.clk((MCLK != 0) ? clk_tx[g] : clk), .rst_n(raw_ld[390]), .d((CMUT == 6 && g == 0) ? (raw_ld[389:0] ^ (390'd1 << 31)) : raw_ld[389:0]), .q(ld));
            end else begin : g_tx_wire
                assign ld = raw_ld;
            end
            wire [63:0]  t;
            wire [7:0]   lf;
            wire         tf;
            ot_qwen_tile_lsl u_lh (.clk((MCLK != 0) ? clk_sl[g] : clk), .rst_n(ld[390]), .v_d(ld[389]), .first_d(ld[388]), .split_d(ld[387:384]),
                                   .w_d(ld[383:128]), .x_d(ld[127:0]), .t_out(t), .lfault(lf), .tfault(tf));
            assign cx_lq[73*GR +: 73] = {tf, lf, t};
            assign node_td[64*GR +: 64] = t;
        end
    endgenerate
    generate if (SPLIT != 0) begin : g_return_leaves
        localparam integer SB = (CODE_BANKS+1)/2;
        wire [1023:0] rs, rn;
        ot_qwen_tile_rqr #(.NR(SB)) u_s (.clk((MCLK != 0) ? clk_rqr[0] : clk), .d(cx_rq[1024*SB-1:0]), .q(rs));
        ot_qwen_tile_rqr #(.NR(CODE_BANKS-SB)) u_n (.clk((MCLK != 0) ? clk_rqr[1] : clk), .d(cx_rq[1024*CODE_BANKS-1:1024*SB]), .q(rn));
        assign cx_rqr = {(CMUT == 5) ? 1024'd0 : rn, rs};
    end else begin : g_return_unused
        assign cx_rqr = 2048'd0;
    end endgenerate
    wire node_fault;
    assign cx_nfault = (CMUT == 4) ? ~node_fault : node_fault;
    ot_qwen_tile_node u_node (.clk((MCLK != 0) ? clk_node : clk), .rst_n(rst_n), .a(n_a), .b(n_b), .va(n_va), .y(n_y), .vy(n_vy), .fault(node_fault),
                              .t_d(node_td), .t_vd(cx_tvd), .t_out(t_out), .t_vout(t_vout));
endmodule

// Last original XTX rung only: the control leaf retains the first rung and reset relay.
module ot_qwen_tile_tx(input wire clk,input wire rst_n,input wire [389:0] d,output wire [390:0] q);
    wire [389:0] out;
    ot_qwen_tx_ff #(.W(390)) u_r (.clk(clk),.rst_n(rst_n),.d(d),.q(out));
    assign q = {rst_n,out};
endmodule
module ot_qwen_tile_rqr #(parameter integer NR=3)(input wire clk,input wire [NR*1024-1:0] d,output reg [1023:0] q);
    reg [1023:0] combined; integer i;
    always @* begin combined=1024'd0; for(i=0;i<NR;i=i+1) combined=combined|d[1024*i+:1024]; end
    always @(posedge clk) q <= combined;
endmodule
module ot_qwen_tile_rqr_s(input wire clk,input wire [3071:0] d,output wire [1023:0] q);
    ot_qwen_tile_rqr #(.NR(3)) u_r (.clk(clk),.d(d),.q(q));
endmodule
module ot_qwen_tile_rqr_n(input wire clk,input wire [2047:0] d,output wire [1023:0] q);
    ot_qwen_tile_rqr #(.NR(2)) u_r (.clk(clk),.d(d),.q(q));
endmodule
