`timescale 1ns/1ps
// Physical composition of one four-bank VM slice, 64-lane FP32->BF16
// converter, one MP=1 ME activation store, and four registered consumers.
// Primary I/O is a test envelope; the timing gate false-paths only primary
// I/O and times every internal SRAM and producer/consumer register path.
module ot_v41_vm_me_neighborhood4 #(
    parameter integer DEPTH_GROUPS=3,
    parameter integer AW=15
) (
    input wire clk,
    input wire rst_n,
    input wire vm_rd_v,
    input wire [AW-1:0] vm_rd_base_word,
    input wire [12:0] vm_pre_e,
    input wire vm_pre_p,
    input wire [3:0] vm_wr_v,
    input wire [4*AW-1:0] vm_wr_word_addr,
    input wire [2047:0] vm_wr_word_data,
    input wire [1:0] me_rd_rot,
    input wire [7:0] me_rq_v,
    input wire [111:0] me_rq_q,
    input wire [31:0] me_rq_plg,
    input wire [3:0] sink_ce,
    output reg [4095:0] sink_data,
    output wire vm_rd_fault,
    output wire vm_wr_fault,
    output wire vm_collision_fault,
    output wire cv_fault,
    output wire cv_saturated
);
    wire vm_v;
    wire [1:0] vm_rot;
    wire [2047:0] vm_words;
    wire cv_v;
    wire cv_p;
    wire [12:0] cv_e;
    wire [1023:0] cv_words;
    wire [1023:0] store_words;
    reg [1:0] me_rd_rot_q;
    reg [7:0] me_rq_v_q;
    reg [111:0] me_rq_q_q;
    reg [31:0] me_rq_plg_q;
    reg [3:0] sink_ce_q;
    reg [12:0] e_delay [0:6];
    reg p_delay [0:6];
    integer i;
    always @(posedge clk) begin
        me_rd_rot_q <= me_rd_rot;
        me_rq_v_q <= me_rq_v;
        me_rq_q_q <= me_rq_q;
        me_rq_plg_q <= me_rq_plg;
        sink_ce_q <= sink_ce;
        e_delay[0] <= vm_pre_e;
        p_delay[0] <= vm_pre_p;
        for (i=1;i<7;i=i+1) begin
            e_delay[i] <= e_delay[i-1];
            p_delay[i] <= p_delay[i-1];
        end
    end

    ot_v41_vm_bank4_registered_neighbor #(.DEPTH_GROUPS(DEPTH_GROUPS),.AW(AW)) u_vm (
        .clk(clk),.rst_n(rst_n),.rd_v(vm_rd_v),.rd_base_word(vm_rd_base_word),
        .wr_v(vm_wr_v),.wr_word_addr(vm_wr_word_addr),.wr_word_data(vm_wr_word_data),
        .rd_out_v(vm_v),.rd_out_rot(vm_rot),.rd_out_bank_words(vm_words),
        .rd_fault(vm_rd_fault),.wr_fault(vm_wr_fault),
        .rw_collision_fault(vm_collision_fault)
    );
    ot_hdc_v41x_fp32_bf16_preload64_pipe2 #(.PW(1)) u_cv (
        .clk(clk),.rst_n(rst_n),.in_v(vm_v),.in_p(p_delay[6]),
        .in_e(e_delay[6]),.in_d(vm_words),.out_v(cv_v),.out_p(cv_p),
        .out_e(cv_e),.out_d(cv_words),.out_fault(cv_fault),
        .out_saturated(cv_saturated)
    );
    ot_hdc_v41x_me_xbank_macro_inreg_readreg_writepipe #(.MP(1)) u_store (
        .clk(clk),.wr_v(1'b0),.wr_p(1'b0),.wr_e(13'b0),.wr_d(64'b0),
        .pre_v(cv_v),.pre_p(cv_p),.pre_e(cv_e),.pre_d(cv_words),
        .rd_rot(me_rd_rot_q),.rq_v(me_rq_v_q),.rq_q(me_rq_q_q),
        .rq_plg(me_rq_plg_q),.rd_x(store_words)
    );

    genvar c;
    generate for (c=0;c<4;c=c+1) begin : g_sink
        // Independent capture enables keep all four full-width consumers
        // observable through synthesis; they cannot collapse to one bank.
        always @(posedge clk)
            if (sink_ce_q[c]) sink_data[c*1024 +:1024] <= store_words;
    end endgenerate
endmodule
