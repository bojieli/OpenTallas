`timescale 1ns/1ps
`default_nettype none
// Reusable attention merge leaf. Its inputs are canonical FP32 lane chunk sums
// from the existing SM arithmetic, with the caller's exact last/tag alignment.
// No multipliers or accumulator lanes are instantiated here. Every merge uses
// the same modulo8 barrel, RNE adders and real64x512 stack as the proven tcpv.
// The production hierarchical caller reuses CLOSED tcl halves and provides ev
// at closed tct's LL=16 boundary. The flat component caller retains LL=12.
module ot_hbm_sm_pv_merge #(
    parameter integer L=16, IL=8, TAGW=16, ALAT=7, LV=4, MUT=0
)(
    input wire clk, rst_n,
    input wire ev,
    input wire [L*32-1:0] sum,
    input wire [TAGW-1:0] tag_d,
    output reg pv_v,
    output reg [L*32-1:0] pv_y,
    output reg [TAGW-1:0] pv_tag,
    output wire fault
);
    initial if (L!=16 || IL!=8 || ALAT!=7 || LV<1 || LV>8 || TAGW<6)
        $fatal(1,"PV merge requires16lanes,8slots,LAT7,LV1..8,TAGW>=6");
    genvar l;
    // ---------------- PV: barrel binary-counter merge ----------------
    localparam integer KW = 3;
    reg  [2:0]  bp;                                   // entry whose turn it is
    always @(posedge clk or negedge rst_n) if (!rst_n) bp <= 3'd0; else bp <= bp + 3'd1;
    wire [2:0]  nb = bp + 3'd1;
    reg  [7:0]  e_busy, e_fl, e_fin;                  // busy / flushing / flush after chain
    reg  [KW:0] e_k   [0:7];                          // level of the next turn (chain: carry level; flush: fold level)
    reg  [7:0]  e_c   [0:7];                          // chunk index being merged (chain)
    reg  [8:0]  e_n   [0:7];                          // chunks of the run so far
    reg  [TAGW-1:0] e_tag [0:7];
    // events of this cycle (lane chunk sums of a PV beat)
    // stack read for entry nb, landing at its turn (next cycle)
    wire [KW:0] rk = e_busy[nb] ? e_k[nb] : {(KW+1){1'b0}};
    wire [5:0]  sr_a = {nb, rk[2:0] + ((MUT == 1) ? 3'd1 : 3'd0)};
    wire [L*32-1:0] st_rd;
    reg         sw_ce;
    reg  [5:0]  sw_a;
    reg  [L*32-1:0] sw_d;
    ot_sram_1r1w_64x512_m1_r2c2 u_stack (.clk(clk), .r_ce_in(1'b1), .r_addr_in(sr_a), .rd_out(st_rd),
        .w_ce_in(sw_ce), .w_addr_in(sw_a), .wd_in(sw_d), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // merge adder operands of this turn
    reg  [L*32-1:0] ma, mb;
    reg             mv;
    wire [L*32-1:0] my;
    wire [L-1:0]    mf;
    reg  [L*32-1:0] vreg;                             // adder result, back at the entry's next turn
    generate for (l = 0; l < L; l = l + 1) begin : g_madd
        ot_gpu_fadd #(.LAT(ALAT)) u_m (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma[32*l +: 32]), .b(mb[32*l +: 32]),
                                       .y(my[32*l +: 32]), .fault(mf[l]));
    end endgenerate
    always @(posedge clk) vreg <= my;
    // turn logic (combinational) for entry r = bp
    wire [2:0] r = bp;
    wire       ev_first = tag_d[TAGW-2], ev_last = tag_d[TAGW-3];
    wire [7:0] ev_c = ev_first ? 8'd0 : e_n[r][7:0];
    reg        m_fault;
    always @(*) begin
        mv = 1'b0; ma = {L*32{1'b0}}; mb = {L*32{1'b0}};
        sw_ce = 1'b0; sw_a = {r, 3'd0}; sw_d = sum;
        if (ev) begin
            if (ev_c[0]) begin mv = 1'b1; ma = st_rd; mb = sum; end
            else begin sw_ce = 1'b1; sw_a = {r, 3'd0}; sw_d = sum; end
        end else if (e_busy[r] && !e_fl[r]) begin
            if (e_c[r][e_k[r][2:0]]) begin mv = 1'b1; ma = st_rd; mb = vreg; end
            else begin sw_ce = 1'b1; sw_a = {r, e_k[r][2:0]}; sw_d = vreg; end
        end else if (e_busy[r] && e_fl[r] && e_k[r] < LV) begin
            mv = 1'b1;
            if (e_n[r][e_k[r][2:0]]) begin ma = st_rd; mb = (e_k[r] == 0) ? {L*32{1'b0}} : vreg; end
            else begin ma = (e_k[r] == 0 || (MUT == 2 && e_k[r] == LV - 1)) ? {L*32{1'b0}} : vreg; mb = {L*32{1'b0}}; end
        end
    end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e_busy <= 8'd0; e_fl <= 8'd0; e_fin <= 8'd0; pv_v <= 1'b0; m_fault <= 1'b0;
            for (i = 0; i < 8; i = i + 1) begin e_k[i] <= 0; e_c[i] <= 8'd0; e_n[i] <= 9'd0; end
        end else begin
            pv_v <= 1'b0;
            if (|mf) m_fault <= 1'b1;
            if (ev) begin
                if (e_busy[r]) m_fault <= 1'b1;                       // chunk arrived while the entry still merges
                if (ev_c >= (8'd1 << (LV - 1))) m_fault <= 1'b1;      // run longer than the stack
                e_tag[r] <= tag_d;
                e_n[r] <= {1'b0, ev_c} + 9'd1;
                e_c[r] <= ev_c;
                if (ev_c[0]) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b0; e_k[r] <= 1; e_fin[r] <= ev_last; end
                else if (ev_last) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b1; e_k[r] <= 0; end
            end else if (e_busy[r] && !e_fl[r]) begin
                if (e_c[r][e_k[r][2:0]]) e_k[r] <= e_k[r] + 1;
                else if (e_fin[r]) begin e_fl[r] <= 1'b1; e_k[r] <= 0; end
                else e_busy[r] <= 1'b0;
            end else if (e_busy[r] && e_fl[r]) begin
                if (e_k[r] < LV) e_k[r] <= e_k[r] + 1;
                else begin e_busy[r] <= 1'b0; e_fl[r] <= 1'b0; pv_v <= 1'b1; end
            end
        end
    end
    always @(posedge clk) if (e_busy[r] && e_fl[r] && !(e_k[r] < LV) && !ev) begin pv_y <= vreg; pv_tag <= e_tag[r]; end
    assign fault = m_fault;
endmodule
`default_nettype wire
