`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_rgx (hgi-1010/a 2026-10-10): HARDWARE COLL.ROW_GATHER (spec G25), one record, no LOOP.
//
//   source  ot_hgi_coll_rgx_src : scan the replicated list I, stream this rank's owned rows from HBM (several rows in
//                                 flight), flit f of list entry x tagged gi = x F + f
//   fabric  ot_hbm_accel_tu_endpoint_psg (RGX = 1, DELCRED = 1, bypass): each owned flit multicast once on the existing
//                                 links / credits; every rank of the group receives the K F flits of the selection and
//                                 completes on count + sum + xor of gi = 0 .. K F - 1 (a lost, duplicated or misplaced
//                                 row faults); the own flits through the own delivery queue (inject gated on its room)
//   sink    ot_hgi_coll_rgx_sink: delivery credits, gi -> (row x, flit f), list-order write port (O row x); ranks
//                                 >= destinations drain without writing
//
// Cost (one destination, no stalls): ~ K F / DEL delivery cycles + the fabric / HUBW latency; the per-rank inject (owned
// rows only, one flit a cycle) and the HBM reads (2 sectors a cycle) run under it.  No padding to the group's largest
// owned count (DS K 512 / G 96: 512 rows delivered, not 96 M), no per-slot epochs, no slot-major array, no inverse map.
//
// start (idle, pulse) -> sources and endpoint launched together -> done (pulse) when the endpoint completed AND the
// sink drained (every write accepted).  fault (sticky): configuration, source, endpoint or sink fault.
module ot_hgi_coll_rgx #(
    parameter integer NOG = 12, PFMAX = 512, NPT = 8, INJ = 2, DEL = 4, LANES = 16, FW = 32 * LANES, PWT = FW + 33,
    parameter integer NL = 2, RING = 256, CAP = 64, AW = 35,
    parameter integer MUT_SLOT = 0, MUT_OMAJ = 0, MUT_DUP = 0, MUT_CREDIT = 0, MUT_NOGATE = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    output wire                 ready,
    output reg                  done,
    output wire                 fault,
    input  wire [7:0]           cfg_rank,      // die mod 96 (the endpoint rank)
    input  wire [7:0]           cfg_g,         // group size 1, 2, 4, 8, 96
    input  wire [2:0]           cfg_lb,        // log2 owner block B
    input  wire [11:0]          cfg_k,         // selected rows K (1 .. 2,048)
    input  wire [7:0]           cfg_dests,     // destination ranks 0 .. dests - 1 of the group
    input  wire [AW-1:0]        cfg_abase,
    input  wire [15:0]          cfg_astride,
    input  wire [6:0]           cfg_sec,
    input  wire [31:0]          cfg_lbase,
    output wire                 lq_v,
    input  wire                 lq_rdy,
    output wire [31:0]          lq_addr,
    input  wire                 lr_v,
    input  wire [511:0]         lr_data,
    output wire [NL-1:0]        hq_v,
    input  wire [NL-1:0]        hq_rdy,
    output wire [NL*AW-1:0]     hq_addr,
    output wire [NL*8-1:0]      hq_tag,
    input  wire [NL-1:0]        hr_v,
    input  wire [NL*8-1:0]      hr_tag,
    input  wire [NL*256-1:0]    hr_data,
    output wire [NPT-1:0]       ph_tx_v,
    output wire [NPT*PWT-1:0]   ph_tx_flit,
    input  wire [NPT-1:0]       sw_cr_ret,
    input  wire [NPT-1:0]       ph_rx_v,
    input  wire [NPT*PWT-1:0]   ph_rx_flit,
    output wire [NPT-1:0]       rx_credit,
    output wire [DEL-1:0]       w_v,
    output wire [DEL*11-1:0]    w_x,
    output wire [DEL*5-1:0]     w_f,
    output wire [DEL*40-1:0]    w_addr,
    input  wire [39:0]          cfg_obase,
    input  wire [31:0]          cfg_ostride,
    output wire [DEL*FW-1:0]    w_data,
    input  wire [DEL-1:0]       w_rdy,
    output wire [31:0]          stat_credit_stall
);
    localparam S_IDLE = 2'd0, S_GO = 2'd1, S_RUN = 2'd2, S_HALT = 2'd3;
    reg [1:0] st;
    reg [7:0] rank_q, g_q, rrel_q, dests_q; reg [2:0] lb_q; reg [11:0] k_q; reg [AW-1:0] ab_q; reg [15:0] as_q;
    reg [6:0] sec_q; reg [31:0] lb0_q; reg [5:0] f_q; reg [39:0] ob_q; reg [31:0] os_q;
    reg src_start, sink_start, ep_go, ep_done_ready, cfg_fault;
    wire ep_start_ready, ep_done_valid, ep_fault, src_fault, sink_fault, sink_drained;
    wire rs_v, rs_rdy, rs_end; wire [15:0] rs_gi; wire [FW-1:0] rs_data;
    wire [DEL-1:0] permit, reserve, dv; wire [DEL*PWT-1:0] df;
    wire [5:0] nflit = 6'((cfg_sec + 7'd1) >> 1);
    wire g_ok = (cfg_g == 8'd1 || cfg_g == 8'd2 || cfg_g == 8'd4 || cfg_g == 8'd8 || cfg_g == 8'd96);
    wire bad = !g_ok || cfg_rank >= 8'd96 || cfg_k == 12'd0 || cfg_k > 12'd2048 || cfg_dests == 8'd0 || cfg_dests > cfg_g ||
               cfg_sec == 7'd0 || cfg_sec > 7'd64;
    wire [7:0] rrel = (cfg_g == 8'd96) ? cfg_rank : (cfg_rank & (cfg_g - 8'd1));
    assign ready = (st == S_IDLE);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; cfg_fault <= 1'b0; src_start <= 1'b0; sink_start <= 1'b0; ep_go <= 1'b0; ep_done_ready <= 1'b0;
            rank_q <= 0; g_q <= 8'd96; rrel_q <= 0; dests_q <= 0; lb_q <= 0; k_q <= 12'd1; ab_q <= 0; as_q <= 0; sec_q <= 7'd1; lb0_q <= 0; f_q <= 6'd1;
        end else begin
            done <= 1'b0; src_start <= 1'b0; sink_start <= 1'b0; ep_go <= 1'b0; ep_done_ready <= 1'b0;
            case (st)
                S_IDLE: if (start) begin
                    if (bad) begin cfg_fault <= 1'b1; st <= S_HALT; end
                    else begin
                        rank_q <= cfg_rank; g_q <= cfg_g; rrel_q <= rrel; dests_q <= cfg_dests; lb_q <= cfg_lb; k_q <= cfg_k;
                        ab_q <= cfg_abase; as_q <= cfg_astride; sec_q <= cfg_sec; lb0_q <= cfg_lbase; f_q <= nflit;
                        ob_q <= cfg_obase; os_q <= cfg_ostride;
                        sink_start <= 1'b1; st <= S_GO;
                    end
                end
                S_GO: if (ep_start_ready && sink_drained) begin ep_go <= 1'b1; src_start <= 1'b1; st <= S_RUN; end
                S_RUN: if (ep_done_valid && sink_drained && !ep_done_ready) begin ep_done_ready <= 1'b1; done <= 1'b1; st <= S_IDLE; end
                default: ;
            endcase
            if (fault) st <= S_HALT;
        end
    end
    assign fault = cfg_fault | src_fault | ep_fault | sink_fault;
    ot_hgi_coll_rgx_src #(.NL(NL), .RING(RING), .AW(AW), .FW(FW), .MUT_SLOT(MUT_SLOT), .MUT_OMAJ(MUT_OMAJ), .MUT_DUP(MUT_DUP)) u_src (
        .clk(clk), .rst_n(rst_n), .start(src_start), .cfg_k(k_q), .cfg_lb(lb_q), .cfg_g(g_q), .cfg_rrel(rrel_q),
        .cfg_abase(ab_q), .cfg_astride(as_q), .cfg_sec(sec_q), .cfg_nflit(f_q), .cfg_lbase(lb0_q),
        .lq_v(lq_v), .lq_rdy(lq_rdy), .lq_addr(lq_addr), .lr_v(lr_v), .lr_data(lr_data),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_tag(hq_tag), .hr_v(hr_v), .hr_tag(hr_tag), .hr_data(hr_data),
        .rs_v(rs_v), .rs_gi(rs_gi), .rs_data(rs_data), .rs_rdy(rs_rdy), .rs_end(rs_end), .busy(), .fault(src_fault));
    ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1), .REARM(1), .RGX(1), .DELCRED(1), .MUT_NOGATE(MUT_NOGATE), .PFMAX(PFMAX), .BF16RT(1),
        .NOG(NOG), .NPT(NPT), .INJ(INJ), .DEL(DEL), .LANES(LANES)) u_ep (
        .clk(clk), .rst_n(rst_n), .pclk(clk), .prst_n(rst_n),
        .rank(rank_q), .mcast_group_size(g_q), .mcast_all(g_q == 8'd96),
        .gsz((g_q == 8'd96 || g_q == 8'd8) ? 4'd3 : (g_q == 8'd4) ? 4'd2 : (g_q == 8'd2) ? 4'd1 : 4'd0),
        .byp(1'b1), .res_bf16(1'b0), .pf(16'd1), .go(ep_go), .start_ready(ep_start_ready),
        .done_valid(ep_done_valid), .done_ready(ep_done_ready), .fault_ack(1'b0),
        .inj_idx(), .inj_rd(), .inj_data({INJ*FW{1'b0}}), .ph_tx_v(ph_tx_v), .ph_tx_flit(ph_tx_flit),
        .sw_cr_ret(sw_cr_ret), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit), .rx_credit(rx_credit),
        .del_valid(dv), .del_flit(df),
        .rgx(1'b1), .rgx_total(17'(k_q) * 17'(f_q)), .rs_v(rs_v), .rs_gi(rs_gi), .rs_data(rs_data), .rs_rdy(rs_rdy), .rs_end(rs_end),
        .del_permit(permit), .del_reserve(reserve), .fault(ep_fault), .stat_credit_stall(stat_credit_stall));
    ot_hgi_coll_rgx_sink #(.DEL(DEL), .CAP(CAP), .FW(FW), .PWT(PWT), .MUT_CREDIT(MUT_CREDIT)) u_sink (
        .clk(clk), .rst_n(rst_n), .start(sink_start), .cfg_nflit(f_q), .cfg_k(k_q), .cfg_discard(rrel_q >= dests_q), .cfg_obase(ob_q), .cfg_ostride(os_q), .cfg_ovm(1'b0),
        .del_reserve(reserve), .del_permit(permit), .del_valid(dv), .del_flit(df),
        .w_v(w_v), .w_x(w_x), .w_f(w_f), .w_addr(w_addr), .w_data(w_data), .w_rdy(w_rdy), .drained(sink_drained), .fault(sink_fault));
endmodule
`default_nettype wire
