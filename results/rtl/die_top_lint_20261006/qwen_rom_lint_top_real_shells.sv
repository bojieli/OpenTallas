// die_top_lint: REAL-INTERFACE shells (port lists parsed from the RTL named in each header; interiors are
// the element owners' lint scope).

// rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv
module ot_qwen_stream4_cdc_pc #(parameter TAGW = 9) (
    input wire [0:0] clk,
    input wire [0:0] c_arst_n,
    output wire [0:0] l_v,
    output wire [16:0] l_sec,
    output wire [7:0] l_row,
    output wire [255:0] l_data,
    input wire [0:0] l_pop,
    input wire [0:0] w_v,
    input wire [23:0] w_sec,
    input wire [255:0] w_data,
    input wire [8:0] w_tag,
    output wire [0:0] w_room,
    output wire [0:0] wd_v,
    output wire [8:0] wd_tag,
    output wire [0:0] c_fault,
    input wire [0:0] hclk,
    input wire [0:0] h_arst_n,
    input wire [0:0] h_lv,
    input wire [16:0] h_lsec,
    input wire [7:0] h_lrow,
    input wire [255:0] h_ldata,
    output wire [2:0] h_cred,
    output wire [0:0] h_wv,
    output wire [23:0] h_wsec,
    input wire [0:0] h_hand,
    input wire [0:0] h_wcon,
    output wire [0:0] h_cv,
    output wire [23:0] h_csec,
    output wire [255:0] h_cdata,
    output wire [8:0] h_ctag,
    input wire [0:0] h_av,
    input wire [8:0] h_atag,
    output wire [0:0] h_fault);
    wire lint_in = ^{^clk, ^c_arst_n, ^l_pop, ^w_v, ^w_sec, ^w_data, ^w_tag, ^hclk, ^h_arst_n, ^h_lv, ^h_lsec, ^h_lrow, ^h_ldata, ^h_hand, ^h_wcon, ^h_av, ^h_atag};
    reg [0:0] r_l_v; always @(posedge clk) r_l_v <= {1{lint_in}}; assign l_v = r_l_v;
    reg [16:0] r_l_sec; always @(posedge clk) r_l_sec <= {17{lint_in}}; assign l_sec = r_l_sec;
    reg [7:0] r_l_row; always @(posedge clk) r_l_row <= {8{lint_in}}; assign l_row = r_l_row;
    reg [255:0] r_l_data; always @(posedge clk) r_l_data <= {256{lint_in}}; assign l_data = r_l_data;
    reg [0:0] r_w_room; always @(posedge clk) r_w_room <= {1{lint_in}}; assign w_room = r_w_room;
    reg [0:0] r_wd_v; always @(posedge clk) r_wd_v <= {1{lint_in}}; assign wd_v = r_wd_v;
    reg [8:0] r_wd_tag; always @(posedge clk) r_wd_tag <= {9{lint_in}}; assign wd_tag = r_wd_tag;
    reg [0:0] r_c_fault; always @(posedge clk) r_c_fault <= {1{lint_in}}; assign c_fault = r_c_fault;
    reg [2:0] r_h_cred; always @(posedge clk) r_h_cred <= {3{lint_in}}; assign h_cred = r_h_cred;
    reg [0:0] r_h_wv; always @(posedge clk) r_h_wv <= {1{lint_in}}; assign h_wv = r_h_wv;
    reg [23:0] r_h_wsec; always @(posedge clk) r_h_wsec <= {24{lint_in}}; assign h_wsec = r_h_wsec;
    reg [0:0] r_h_cv; always @(posedge clk) r_h_cv <= {1{lint_in}}; assign h_cv = r_h_cv;
    reg [23:0] r_h_csec; always @(posedge clk) r_h_csec <= {24{lint_in}}; assign h_csec = r_h_csec;
    reg [255:0] r_h_cdata; always @(posedge clk) r_h_cdata <= {256{lint_in}}; assign h_cdata = r_h_cdata;
    reg [8:0] r_h_ctag; always @(posedge clk) r_h_ctag <= {9{lint_in}}; assign h_ctag = r_h_ctag;
    reg [0:0] r_h_fault; always @(posedge clk) r_h_fault <= {1{lint_in}}; assign h_fault = r_h_fault;
endmodule
