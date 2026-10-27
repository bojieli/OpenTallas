`timescale 1ns/1ps
// Hardened children of qkd_ctrl_pc_host_static (Q-KVSYS-DIE KVCTRL split 2026-10-16). Each is its own HBM-clock root.
// Every input lands in a pin flop (or the wrapped module's own first register stage); every output is flop-driven.

// PC port child: the actual ot_qfd_emb_pcport (KVW 2, RQD = controller TQD) plus the pin flops that fed it in the
// monolithic controller: KV write data (ci[28] / ci[308:53]) and PHY read data (pi[0] / pi[288:1]) are captured here,
// edge-for-edge identical to the historical cv_q / cdata_q / rv_q / rd_q; the column arrives one edge early from the
// remainder (dv[LW-2]) and is captured at this pin (= dv[LW-1]).
module qkd_ctrl_pc_port_child #(
    parameter integer CORE_CLOCK = 0,
    parameter integer RQD = 64,
    parameter integer MUT = 0
) (
    input  wire         hclk,
    input  wire         hrst,
    input  wire         col_v_e, col_we_e, col_sr_e,   // one edge early
    input  wire         w_v,                           // remainder flops; re-captured at this pin (s3: native capture <= 190 ps)
    input  wire [255:0] w_d,
    input  wire         kw_vi,                         // ci[28]
    input  wire [255:0] kw_di,                         // ci[308:53]
    input  wire [288:0] pi,
    output wire [287:0] wd,
    output wire         kv_v,
    output wire [287:0] kv_d,
    output wire         em_v,
    output wire [257:0] em_d,
    output wire         fault
);
    // CORE833 PHY write latency is7 cycles (ceil5x1024/833).
    // The legacy controller data path is5 cycles; add2 data-only stages.
    wire [287:0] wd_raw;
    generate if(CORE_CLOCK)begin:g_wdata2
        reg [287:0] wd_q1,wd_q2;
        always @(posedge hclk)begin wd_q1<=wd_raw;wd_q2<=wd_q1;end
        assign wd=wd_q2;
    end else begin:g_wdata0
        assign wd=wd_raw;
    end endgenerate
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    wire h_rn = hr_q;
    (* keep *) reg cv_q, rv_q, col_v_q, col_we_q, col_sr_q;
    (* keep *) reg [255:0] cdata_q;
    (* keep *) reg [287:0] rd_q;
    (* keep *) reg w_v_q;
    (* keep *) reg [255:0] w_d_q;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin cv_q <= 1'b0; rv_q <= 1'b0; col_v_q <= 1'b0; col_we_q <= 1'b0; col_sr_q <= 1'b0; w_v_q <= 1'b0; end
        else begin cv_q <= kw_vi; rv_q <= pi[0]; col_v_q <= col_v_e; col_we_q <= col_we_e; col_sr_q <= col_sr_e; w_v_q <= w_v; end
    always @(posedge hclk) begin cdata_q <= kw_di; rd_q <= pi[288:1]; w_d_q <= w_d; end
    ot_qfd_emb_pcport #(.KVW(2), .RQD(RQD), .MUT(MUT)) u_port (
        .clk(hclk), .rst_n(h_rn), .col_v(col_v_q), .col_we(col_we_q), .col_sr(col_sr_q),
        .w_v(w_v_q), .w_d(w_d_q), .wd(wd_raw), .kw_v(cv_q), .kw_d(cdata_q),
        .r_v(rv_q), .r_d(rd_q), .kv_v(kv_v), .kv_d(kv_d), .em_v(em_v), .em_d(em_d), .fault(fault));
endmodule

// Landing ECC child: the actual ot_qfd_kv_landing_ecc (ENABLE 1, INTERLEAVED 1, PIPE 2). Its PIPE stage 0 is the input
// pin register of i_v / i_code / i_sec / i_row; outputs are its corrected / sec / row flops (o_v = dv & !du & !sticky).
module qkd_ctrl_pc_ecc_child (
    input  wire         hclk,
    input  wire         hrst,
    input  wire         i_v,
    input  wire [287:0] i_code,
    input  wire [16:0]  i_sec,
    input  wire [7:0]   i_row,
    output wire         o_v,
    output wire [255:0] o_data,
    output wire [16:0]  o_sec,
    output wire [7:0]   o_row,
    output wire         fault
);
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (
        .hclk(hclk), .h_rst_n(hr_q), .i_v(i_v), .i_code(i_code), .i_sec(i_sec), .i_row(i_row),
        .o_v(o_v), .o_data(o_data), .o_sec(o_sec), .o_row(o_row), .ce(), .ue(), .fault(fault), .ce_count());
endmodule

// KV-NATIVE 2026-10-17: ECC child paired with qkd_ctrl_pc_sched PINREG 2 (sched_s10), whose e_sec / e_row arrive ONE hclk
// after the beat (i_v / i_code) they belong to.  ot_qfd_kv_landing_ecc (unchanged, PIPE 2) carries section / row through
// P0 -> P1 -> the output register untouched by the decode; here they enter at P1 instead: s1 / r1 capture the late i_sec /
// i_row on the edge the P1 registers capture the beat, and o_sec / o_row load from them under the same f_v (= i_v two
// edges late, own reset copy).  o_v / o_data / fault and o_sec / o_row are cycle-identical to qkd_ctrl_pc_ecc_child fed
// i_sec / i_row on the beat's own edge (tb_sched_esecreg_equiv).  MUT 1 (bench only): o_sec / o_row skip s1 / r1.
module qkd_ctrl_pc_ecc_child_sl #(parameter integer MUT = 0) (
    input  wire         hclk,
    input  wire         hrst,
    input  wire         i_v,
    input  wire [287:0] i_code,
    input  wire [16:0]  i_sec,
    input  wire [7:0]   i_row,
    output wire         o_v,
    output wire [255:0] o_data,
    output reg  [16:0]  o_sec,
    output reg  [7:0]   o_row,
    output wire         fault
);
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (
        .hclk(hclk), .h_rst_n(hr_q), .i_v(i_v), .i_code(i_code), .i_sec(17'd0), .i_row(8'd0),
        .o_v(o_v), .o_data(o_data), .o_sec(), .o_row(), .ce(), .ue(), .fault(fault), .ce_count());
    reg v1, v2;
    reg [16:0] s1;
    reg [7:0]  r1;
    always @(posedge hclk or negedge hr_q) if (!hr_q) begin v1 <= 1'b0; v2 <= 1'b0; end else begin v1 <= i_v; v2 <= v1; end
    always @(posedge hclk) begin
        s1 <= i_sec; r1 <= i_row;
        if (v2) begin o_sec <= (MUT == 1) ? i_sec : s1; o_row <= (MUT == 1) ? i_row : r1; end
    end
endmodule
