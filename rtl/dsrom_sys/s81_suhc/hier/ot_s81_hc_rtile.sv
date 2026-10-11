`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_rtile (s81-suhc-hier-1011, 2026-10-11): the ROOT TILE of the hierarchical S81 HC slab (dsfd_sp_hc HIER=1),
// placed at the slab end next to the c_cmd / VM / y pins.  It holds everything of dsfd_sp_hc that is not per element:
// the dsfd_sp_ctrl engine adapter (ot_s81_engine_adapter QD 8), the die pin flops (VM responses, inp, y skid), the root
// (ot_s81_hc_hroot: job sequencing, VM read / write slots, the norm scalar tail, the root act-quant), and the column
// chain ports: per chain c the forward bus (the data field = the VM rows, or the chain's y slices during a POST beat)
// and the return bus, each through RR relay registers (the S-face chain ports sit up to 1.2 mm from the root logic:
// RR = 2 keeps every root <-> chain segment under 500 um), and a chain shorter than NP sub-tiles gets 3 registers a
// missing hop on both buses so every chain runs in lockstep.  The chain resets leave through two relay flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_rtile #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, NCOL = 3, GS = 8, S_RT = 4, RR = 2
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    input  wire                y_v,
    output wire                y_rdy,
    input  wire [NG*32-1:0]    y_d,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode,
    // column chains
    output wire [NCOL-1:0]     ch_rst,
    output wire [NCOL*FVW-1:0] ch_fv,
    output wire [NCOL*FDW-1:0] ch_fd,
    input  wire [NCOL*RVW-1:0] ch_rv,
    input  wire [NCOL*RDW-1:0] ch_rd
);
    localparam integer NS   = NG / GS;
    localparam integer NP   = (NS + NCOL - 1) / NCOL;
    localparam integer YW   = NP * GS * 32;
    localparam integer FDD  = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D  = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD;
    localparam integer RDW  = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
    localparam integer FVW  = S_RD + 5, RVW = S_RT + 4;
    localparam integer HOP  = 3;                                  // registers a sub-tile hop (each bus)

    wire [NCOL*RVW-1:0] ch_rv_q;
    wire [NCOL*RDW-1:0] ch_rd_q;
    wire e_v, e_r, d_v, a_flt, c_flt;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    reg inp_q;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    wire [31:0] jobs;
    wire        bsy;
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge srs) if (!srs) rs_v_q <= 0; else rs_v_q <= rs_v;
    wire yq_v, yq_r, y_ov, y_un;
    wire [NG*32-1:0] yq_d;
    ot_skid_buffer #(.WIDTH(NG*32), .DEPTH(2)) u_ysk (.clk(sk), .rst_n(srs), .in_valid(y_v), .in_ready(y_rdy),
        .in_data(y_d), .out_valid(yq_v), .out_ready(yq_r), .out_data(yq_d), .overflow(y_ov), .underflow(y_un));
    wire [FVW-1:0]   r_fv;
    wire [FDW-1:0]   r_fd;
    wire [NG*32-1:0] r_y;
    ot_s81_hc_hroot #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
                      .MUT(MUT)) u_root (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(yq_v), .y_rdy(yq_r), .y_d(yq_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs), .fv(r_fv), .fd(r_fd), .yo(r_y), .rv_in(ch_rv_q), .rd_in(ch_rd_q));
    assign flt = a_flt | c_flt | y_ov | y_un;

    genvar c;
    generate for (c = 0; c < NCOL; c = c + 1) begin : g_c
        localparam integer LC = (NS - c * NP >= NP) ? NP : (NS - c * NP > 0) ? NS - c * NP : 0;
        localparam integer EQ = RR + HOP * (NP - LC);            // relay + lockstep padding registers
        // chain reset: two relay flops from the slab reset
        reg [1:0] rq_;
        always @(posedge sk) rq_ <= {rq_[0], srs};
        assign ch_rst[c] = rq_[1];
        if (LC > 0) begin : g_live
            wire [FDW-1:0] fd_c;
            assign fd_c[O_D-1:0] = r_fd[O_D-1:0];
            // data field: the chain's y slices during a POST beat (fv bit S_RD), the VM rows otherwise
            assign fd_c[O_D +: FDD] = r_fv[S_RD] ? {{(FDD - LC * GS * 32){1'b0}}, r_y[c * YW +: LC * GS * 32]} : r_fd[O_D +: FDD];
            ot_hdc_delay #(.W(FVW), .D(EQ), .RESET(1)) u_fv (.clk(sk), .rst_n(srs), .d(r_fv), .q(ch_fv[c * FVW +: FVW]));
            ot_hdc_delay #(.W(FDW), .D(EQ)) u_fd (.clk(sk), .rst_n(srs), .d(fd_c), .q(ch_fd[c * FDW +: FDW]));
            ot_hdc_delay #(.W(RVW), .D(EQ), .RESET(1)) u_rv (.clk(sk), .rst_n(srs), .d(ch_rv[c * RVW +: RVW]), .q(ch_rv_q[c * RVW +: RVW]));
            ot_hdc_delay #(.W(RDW), .D(EQ)) u_rd (.clk(sk), .rst_n(srs), .d(ch_rd[c * RDW +: RDW]), .q(ch_rd_q[c * RDW +: RDW]));
        end else begin : g_none
            assign ch_fv[c * FVW +: FVW] = 0;
            assign ch_fd[c * FDW +: FDW] = 0;
            assign ch_rv_q[c * RVW +: RVW] = 0;
            assign ch_rd_q[c * RDW +: RDW] = 0;
        end
    end endgenerate
endmodule
