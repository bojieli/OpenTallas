`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_croot (s81-suhc-hier-1011, 2026-10-11): an OUTER column root tile of the hierarchical S81 HC slab
// (dsfd_sp_hc HIER=1): 575.992 um wide, above column chain C (0 west, 2 east), beside the combine tile ot_s81_hc_comb
// (its inner face, lower part) and the centre pin tile ot_s81_hc_cpin (inner face, upper part).  It owns the slab pins
// over its third of the face: chain C's y slice (L_C GS 32 b) and four VM write slots (chain 0's tile: 0..3, the y / h
// rows; chain 2's: 4..7, the act-quant codes / exponent rows).
//   y: the slice lands in a pin flop and enters a YD-deep FIFO on the accept pulse of the centre tile (y_v & y_rdy at
//      the pins, two registers away; the slice waits the same two); the chain's POST forward beat pops it into the
//      chain forward bus's data field.  Overflow is a fault (the centre tile's credit count keeps it from happening).
//   forward: the combine tile's bus (seam capture flop, RF relays, the chain output flop where the y slice joins).
//   return: the chain's bus (capture flop) -> this chain's share of the sum tree (ot_s81_hc_stree OWN C: the subtrees
//      wholly inside the chain, exported) -> RT relays -> the seam send flop, rows and exports together.
//   writes: seam capture flop, RW relays, the pin flops.
// The seams are registered both sides; every segment is one relay register apart (<= 500 um at RF = RT = 1, RW = 2).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_croot #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 1, RT = 1, RW = 2, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    // die pins (this third of the face)
    input  wire [YS-1:0]        y_s,
    output reg  [3:0]           wq_v,
    output reg  [4*14-1:0]      wq_row,
    output reg  [4*16-1:0]      wq_mask,
    output reg  [4*512-1:0]     wq_d,
    // centre pin tile: the y accept pulse
    input  wire                 yacc,
    // combine tile seam
    input  wire [FVW-1:0]       s_fv,
    input  wire [FSW-1:0]       s_fd,
    input  wire [4*WSL-1:0]     s_w,
    output reg  [RVW-1:0]       s_rv,
    output reg  [RDW-1:0]       s_rd,
    output reg  [NEX*32-1:0]    s_ex,
    output reg                  s_flt,
    // column chain C
    output wire                 ch_rst,
    output reg  [FVW-1:0]       ch_fv,
    output reg  [FDW-1:0]       ch_fd,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_PI = S_RT + 24 * S_RT, P_D = P_PI + 8, RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
    localparam integer NEX_ = necnt(C);
    localparam integer NEX = (NEX_ > 0) ? NEX_ : 1;
    localparam integer YB = $clog2(YD);

    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    assign ch_rst = rr[1];

    // ---------------------------------------------------------------- y slice FIFO
    reg  [YS-1:0] yp, yp2;
    reg           ya;
    always @(posedge sk) begin yp <= y_s; yp2 <= yp; end
    always @(posedge sk or negedge srs) if (!srs) ya <= 1'b0; else ya <= yacc;
    reg  [YS-1:0] yf [0:YD-1];
    reg  [YB:0]   yn;
    reg  [YB-1:0] yw, yr;
    // ---------------------------------------------------------------- forward: capture, relays, chain output
    reg  [FVW-1:0] fv_c;
    reg  [FSW-1:0] fd_c;
    always @(posedge sk or negedge srs) if (!srs) fv_c <= 0; else fv_c <= s_fv;
    always @(posedge sk) fd_c <= s_fd;
    wire [FVW-1:0] fv_r;
    wire [FSW-1:0] fd_r;
    ot_hdc_delay #(.W(FVW), .D(RF), .RESET(1)) u_rfv (.clk(sk), .rst_n(srs), .d(fv_c), .q(fv_r));
    ot_hdc_delay #(.W(FSW), .D(RF)) u_rfd (.clk(sk), .rst_n(srs), .d(fd_c), .q(fd_r));
    wire pop = fv_r[S_RD];                                        // a POST beat: the chain's y slice joins it
    always @(posedge sk or negedge srs)
        if (!srs) begin ch_fv <= 0; yn <= 0; yw <= 0; yr <= 0; s_flt <= 1'b0; end
        else begin
            ch_fv <= fv_r;
            if (ya) yw <= yw + 1'b1;
            if (pop) yr <= yr + 1'b1;
            yn <= yn + ya - pop;
            if ((ya && !pop && yn == YD) || (pop && yn == 0)) s_flt <= 1'b1;
        end
    always @(posedge sk) begin
        if (ya) yf[yw] <= yp2;
        ch_fd[O_D-1:0] <= fd_r[O_D-1:0];
        begin : dfield
            reg [FDD-1:0] t;
            t = {FDD{1'b0}};
            if (pop) t[YS-1:0] = yf[yr];
            else t[S_RD*512-1:0] = fd_r[O_D +: S_RD * 512];
            ch_fd[O_D +: FDD] <= t;
        end
    end
    // ---------------------------------------------------------------- return: capture, the chain's subtrees, relays
    reg  [RVW-1:0] rv_c;
    reg  [RDW-1:0] rd_c;
    always @(posedge sk or negedge srs) if (!srs) rv_c <= 0; else rv_c <= ch_rv;
    always @(posedge sk) rd_c <= ch_rd;
    wire [NEX*32-1:0] ex;
    wire              tf;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(AL), .OWN(C)) u_tree (.clk(sk), .rst_n(srs), .v(rv_c[S_RT]),
        .pk(rd_c[P_D +: NP * 128]), .im(32'd0), .ex(ex), .r_v(), .r(), .fault(tf));
    wire [RVW-1:0]    rv_r;
    wire [RDW-1:0]    rd_r;
    wire [NEX*32-1:0] ex_r;
    wire [RVW-1:0]    rv_f = {rv_c[RVW-1] , rv_c[RVW-2] | tf, rv_c[RVW-3:0]};    // tree add faults join the chain's
    ot_hdc_delay #(.W(RVW), .D(RT), .RESET(1)) u_rrv (.clk(sk), .rst_n(srs), .d(rv_f), .q(rv_r));
    ot_hdc_delay #(.W(RDW), .D(RT)) u_rrd (.clk(sk), .rst_n(srs), .d(rd_c), .q(rd_r));
    ot_hdc_delay #(.W(NEX * 32), .D(RT)) u_rex (.clk(sk), .rst_n(srs), .d(ex), .q(ex_r));
    always @(posedge sk or negedge srs) if (!srs) s_rv <= 0; else s_rv <= rv_r;
    always @(posedge sk) begin s_rd <= rd_r; s_ex <= ex_r; end
    // ---------------------------------------------------------------- writes: capture, relays, pin flops
    reg  [4*WSL-1:0] w_c;
    always @(posedge sk) w_c <= s_w;
    wire [4*WSL-1:0] w_r;
    ot_hdc_delay #(.W(4 * WSL), .D(RW)) u_rw (.clk(sk), .rst_n(srs), .d(w_c), .q(w_r));
    reg [3:0] wv_c;                                               // the valids on reset flops
    wire [3:0] wv_r;
    always @(posedge sk or negedge srs) if (!srs) wv_c <= 0; else wv_c <= {s_w[3 * WSL], s_w[2 * WSL], s_w[WSL], s_w[0]};
    ot_hdc_delay #(.W(4), .D(RW), .RESET(1)) u_rwv (.clk(sk), .rst_n(srs), .d(wv_c), .q(wv_r));
    integer s;
    always @(posedge sk or negedge srs) if (!srs) wq_v <= 0; else wq_v <= wv_r;
    always @(posedge sk)
        for (s = 0; s < 4; s = s + 1) begin
            wq_row[14 * s +: 14] <= w_r[WSL * s + 1 +: 14];
            wq_mask[16 * s +: 16] <= w_r[WSL * s + 15 +: 16];
            wq_d[512 * s +: 512] <= w_r[WSL * s + 31 +: 512];
        end
endmodule
