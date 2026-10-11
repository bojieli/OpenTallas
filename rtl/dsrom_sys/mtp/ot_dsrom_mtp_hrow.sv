`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// Main-model hidden rows for the DSpark seed (mtp-dsbind 2026-10-10).
//
// The seed projection (mtp.0.main_proj, K = 15,360) reads, for every committed position, mh = the BF16 HC means of the
// residual at the input of layers 37, 38 and 39 (3 parts x 5,120 BF16 = 3 x 80 beats of 1,024 b).  Each part is
// captured on the stage die that holds the layer (rank k) and must reach DSpark primary die P.k.
//
// Transport (ds-1010 lane decision: MTP traffic on DEDICATED lanes, never a queue in the collective core): one
// dedicated board lane per part (stage die of layer 37 / 38 / 39, rank k -> P.k; the lane = one more closed lane tile
// dsfd_coll_lane_w LCR 1 on a --mtp-links SerDes, as the head-die MTP lane), carrying the grant-protocol flit stream of
// ot_dsrom_mtp_hrow_tx: a header flit {user, pos, issue epoch, part} then 160 data flits (80 beats x 2 halves).
//
//   ot_dsrom_mtp_hrow_tx   stage die: {header} + 80 beats (valid/ready) -> grant-protocol link, flit {hdr, last, 512}
//   dsfd_mtp_hrow          primary die: 3 RTT-sized part receivers + the ROW STORE + the seed client's read port
//                          (grant-protocol request {epoch, user, pos mod 256, beat}, in-order 1,024-b response), the
//                          port dsfd_mtp_seed_launch reads.  The closed VM keeps its ports: the store holds
//                          MAXU x RS rows x 30 KB (3.9 MB at 8 x 16), far beyond the VM slab.
//
// Exactness by construction (versioned rows).  A row is identified by {user, pos, issue epoch}: positions squashed
// by a rejection are re-issued under epoch + 1, so their old rows (which land first: one in-order lane per part) and
// the re-verified rows differ in the epoch.  A read for {epoch e, user, pos} is served only when ALL THREE parts of
// slot {user, pos mod RS} carry exactly {pos, e} and are complete; otherwise the read waits (a late re-verified row).
// A header landing in a slot whose part holds a DIFFERENT position that was never read is an overrun (ring too small,
// or a dropped part that blocked the slot): sticky fault[0]; a header on the wrong part port: fault[1]; a data flit
// without a header: fault[2].
// Mutants (negative controls): OT_HROW_MUT_NOEPOCH (serve any epoch of the position), OT_HROW_MUT_NOPART (serve when
// the requested beat's own part is complete, ignoring the other two parts).
// ---------------------------------------------------------------------------------------------------------------
module ot_dsrom_mtp_hrow_tx #(parameter integer NW = 21, parameter integer USER_W = 10,
                              parameter integer HW = USER_W + NW + 4 + 2) (
    input  wire          clk, rst_n,
    input  wire          h_v,              // row header {user, pos, issue epoch, part}
    output wire          h_r,
    input  wire [HW-1:0] h_d,
    input  wire          b_v,              // 80 beats of 64 BF16
    output wire          b_r,
    input  wire [1023:0] b_d,
    output wire          l_valid,
    input  wire          l_ready,          // grant from the receiver
    output wire [513:0]  l_data             // {hdr flag, last, 512}
);
    reg [1:0] st;                          // 0 header, 1 lo half, 2 hi half
    reg [6:0] nb;
    reg [511:0] hi;
    wire cv; wire cr; reg [513:0] cd;
    assign cv = (st == 2'd0) ? h_v : (st == 2'd1) ? b_v : 1'b1;
    always @(*) case (st)
        2'd0: cd = {1'b1, 1'b0, {(512-HW){1'b0}}, h_d};
        2'd1: cd = {1'b0, 1'b0, b_d[511:0]};
        default: cd = {1'b0, nb == 7'd80, hi};
    endcase
    assign h_r = (st == 2'd0) && cr;
    assign b_r = (st == 2'd1) && cr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin st <= 2'd0; nb <= 7'd0; end
        else if (cv && cr) case (st)
            2'd0: begin st <= 2'd1; nb <= 7'd0; end
            2'd1: begin st <= 2'd2; hi <= b_d[1023:512]; nb <= nb + 7'd1; end
            default: st <= (nb == 7'd80) ? 2'd0 : 2'd1;
        endcase
    ot_dsrom_mtp_ltx #(.W(514)) u_tx (.clk(clk), .rst_n(rst_n), .c_valid(cv), .c_ready(cr), .c_data(cd),
        .l_valid(l_valid), .l_ready(l_ready), .l_data(l_data));
endmodule

// the row store core (behind the receivers): NP part ingress ports, one in-order read port
module ot_dsrom_mtp_hrow_store #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer NP = 3, parameter integer PB = 80
) (
    input  wire                 clk, rst_n,
    input  wire [NP-1:0]        i_v,
    output wire [NP-1:0]        i_r,
    input  wire [NP*514-1:0]    i_d,
    input  wire                 c_v,                 // host: clear a user's slots
    input  wire [USER_W-1:0]    c_user,
    input  wire                 q_v,                 // read request {epoch 4, user, pos 8, beat 8}
    output wire                 q_r,
    input  wire [AW-1:0]        q_a,
    output reg                  r_v,
    output reg  [1023:0]        r_d,
    output reg  [2:0]           fault
);
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer SB = $clog2(RS);
    localparam integer NS = MAXU * RS;                 // slots
    localparam integer DP = NS * PB;                   // beats a part
    localparam integer NM = (DP + 1023) / 1024;        // macros deep a part (x 4 wide)
    localparam integer DB = $clog2(NM * 1024);
    initial if ((1 << SB) != RS || RS > 256 || NP != 3) $fatal(1, "hrow_store: bad dimensions");
    // ---------------- slot tags, one set per part: {pos[7:0], epoch}, complete, write / read generation
    reg [11:0] tag  [0:NP-1][0:NS-1];
    reg        cmp  [0:NP-1][0:NS-1];
    reg        wg   [0:NP-1][0:NS-1];
    reg        rg   [0:NP-1][0:NS-1];
    reg        ld   [0:NP-1][0:NS-1];                  // a row has ever landed (fault rule)
    // ---------------- ingress: per part, header -> slot, then 160 flits -> 80 beats
    reg [NP-1:0] inh;                                  // inside a row
    reg [UB+SB-1:0] islot [0:NP-1];
    reg [6:0] ibeat [0:NP-1];
    reg ihalf [0:NP-1];
    reg [511:0] ilo [0:NP-1];
    assign i_r = {NP{1'b1}};                           // the receivers' flits are always taken (one write port a part)
    // memory: part p, 4 x 256-b columns, NM macros deep; one write and one read port each
    reg  [NP-1:0] mw_v; reg [DB-1:0] mw_a [0:NP-1]; reg [1023:0] mw_d [0:NP-1];
    wire [1023:0] mr_d [0:NP-1];
    reg  [NP-1:0] mr_v; reg [DB-1:0] mr_a;
    genvar gp, gm, gc;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_part
        wire [1023:0] rdm [0:NM-1];
        reg [$clog2(NM+1)-1:0] rsel;
        always @(posedge clk) rsel <= mr_a[DB-1:10];
        for (gm = 0; gm < NM; gm = gm + 1) begin : g_m
            for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
                ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk),
                    .r_ce_in(mr_v[gp] && mr_a[DB-1:10] == gm), .r_addr_in(mr_a[9:0]), .rd_out(rdm[gm][256*gc +: 256]),
                    .w_ce_in(mw_v[gp] && mw_a[gp][DB-1:10] == gm), .w_addr_in(mw_a[gp][9:0]),
                    .wd_in(mw_d[gp][256*gc +: 256]), .w_mask_in({256{1'b1}}),
                    .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
            end
        end
        assign mr_d[gp] = rdm[rsel];
    end endgenerate
    // ---------------- read side: in-order requests, served when the slot holds the requested version
    wire [3:0] q_ep = q_a[UB+16 +: 4];
    wire [UB-1:0] q_u = q_a[16 +: UB];
    wire [7:0] q_pos = q_a[15:8];
    wire [7:0] q_beat = q_a[7:0];
    wire [UB+SB-1:0] q_slot = {q_u, q_pos[SB-1:0]};
    wire [1:0] q_part = (q_beat < 8'd80) ? 2'd0 : (q_beat < 8'd160) ? 2'd1 : 2'd2;
    wire [6:0] q_pb = q_beat - (q_part == 2'd0 ? 8'd0 : q_part == 2'd1 ? 8'd80 : 8'd160);
    reg q_ok;
    integer pi;
    always @(*) begin
        q_ok = 1'b1;
        for (pi = 0; pi < NP; pi = pi + 1) begin
`ifdef OT_HROW_MUT_NOPART
            if (pi == q_part)
`endif
            begin
`ifdef OT_HROW_MUT_NOEPOCH
                if (!(cmp[pi][q_slot] && tag[pi][q_slot][11:4] == q_pos)) q_ok = 1'b0;
`else
                if (!(cmp[pi][q_slot] && tag[pi][q_slot] == {q_pos, q_ep})) q_ok = 1'b0;
`endif
            end
        end
    end
    assign q_r = q_ok;                                 // the head request waits until its row version is complete
    reg rv2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r_v <= 1'b0; rv2 <= 1'b0; mr_v <= '0; end
        else begin
            mr_v <= '0; rv2 <= |mr_v; r_v <= rv2;
            if (q_v && q_ok) begin
                mr_v[q_part] <= 1'b1;
                mr_a <= DB'(q_slot) * DB'(PB) + DB'(q_pb);
            end
        end
    reg [1:0] rp1, rp2;
    always @(posedge clk) begin
        rp1 <= (q_v && q_ok) ? q_part : rp1; rp2 <= rp1;
        if (rv2) r_d <= mr_d[rp2];
    end
    // ---------------- ingress state machines
    integer p, s;
    reg [UB-1:0] hu; reg [NW-1:0] hp; reg [3:0] he; reg [1:0] hq; reg [UB+SB-1:0] hs;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            inh <= '0; mw_v <= '0; fault <= 3'd0;
            for (p = 0; p < NP; p = p + 1) for (s = 0; s < NS; s = s + 1) begin
                tag[p][s] <= 12'd0; cmp[p][s] <= 1'b0; wg[p][s] <= 1'b0; rg[p][s] <= 1'b0; ld[p][s] <= 1'b0;
            end
        end else begin
            mw_v <= '0;
            for (p = 0; p < NP; p = p + 1) begin
                if (i_v[p]) begin
                    if (i_d[p*514 + 513]) begin
                        // header {user, pos, epoch, part} in the low bits
                        hq = i_d[p*514 +: 2]; he = i_d[p*514 + 2 +: 4]; hp = i_d[p*514 + 6 +: NW];
                        hu = i_d[p*514 + 6 + NW +: UB];
                        hs = {hu, hp[SB-1:0]};
                        if (hq != p[1:0] || inh[p]) fault[1] <= 1'b1;
                        if (ld[p][hs] && tag[p][hs][11:4] != hp[7:0] && rg[p][hs] != wg[p][hs]) fault[0] <= 1'b1;
                        tag[p][hs] <= {hp[7:0], he}; cmp[p][hs] <= 1'b0; wg[p][hs] <= ~wg[p][hs]; ld[p][hs] <= 1'b1;
                        islot[p] <= hs; ibeat[p] <= 7'd0; ihalf[p] <= 1'b0; inh[p] <= 1'b1;
                    end else if (!inh[p]) fault[2] <= 1'b1;
                    else if (!ihalf[p]) begin ilo[p] <= i_d[p*514 +: 512]; ihalf[p] <= 1'b1; end
                    else begin
                        mw_v[p] <= 1'b1; mw_a[p] <= DB'(islot[p]) * DB'(PB) + DB'(ibeat[p]);
                        mw_d[p] <= {i_d[p*514 +: 512], ilo[p]};
                        ihalf[p] <= 1'b0; ibeat[p] <= ibeat[p] + 7'd1;
                        if (i_d[p*514 + 512]) begin                       // last flit: the part is complete
                            inh[p] <= 1'b0; cmp[p][islot[p]] <= 1'b1;     // (its write lands before any read can)
                            if (ibeat[p] != 7'd79) fault[2] <= 1'b1;
                        end
                    end
                end
            end
            if (q_v && q_ok && q_pb == 7'd79) rg[q_part][q_slot] <= wg[q_part][q_slot];   // part read through: consumed
            if (c_v && c_user < MAXU)
                for (p = 0; p < NP; p = p + 1) for (s = 0; s < RS; s = s + 1) begin
                    cmp[p][{c_user[UB-1:0], SB'(s)}] <= 1'b0; ld[p][{c_user[UB-1:0], SB'(s)}] <= 1'b0;
                end
        end
endmodule

// dsfd_mtp_hrow: the primary-die master.  Part links in through RTT-sized receivers (FWD_P / RET_P stations each), the
// seed client's request link in through an RTT-sized receiver (FWD_Q / RET_Q), responses and faults from flops.
module dsfd_mtp_hrow #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer FWD_Q = 6, parameter integer RET_Q = 6
) (
    input  wire [0:0]     ck, rst,
    input  wire [514:0]   f_hp0, f_hp1, f_hp2,     // part links {flit 514, valid} (lane adapters)
    output wire [2:0]     t_hpg,                   // their grants
    input  wire [AW:0]    f_vrq,                   // seed client request {addr, valid} (= seedl t_vrq)
    output wire [0:0]     t_vrq,                   // grant (= seedl f_vrq)
    output wire [1024:0]  t_vrs,                   // response {data, valid} (= seedl f_vrs)
    input  wire [USER_W:0] f_clr,
    output wire [2:0]     t_flt
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    wire [2:0] pv, pr; wire [3*514-1:0] pd;
    wire [514:0] fin [0:2];
    assign fin[0] = f_hp0; assign fin[1] = f_hp1; assign fin[2] = f_hp2;
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_rx
        ot_dsrom_mtp_lrx_rtt #(.W(514), .D(FWD_P + RET_P + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                               .FORWARD_HOPS(FWD_P), .RETURN_HOPS(RET_P)) u_p (
            .clk(ck[0]), .rst_n(rn), .l_valid(fin[g][0]), .l_ready(t_hpg[g]), .l_data(fin[g][514:1]),
            .c_valid(pv[g]), .c_ready(pr[g]), .c_data(pd[514*g +: 514]));
    end endgenerate
    wire qv, qr; wire [AW-1:0] qa;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(FWD_Q + RET_Q + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_Q), .RETURN_HOPS(RET_Q)) u_q (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_vrq[0]), .l_ready(t_vrq[0]), .l_data(f_vrq[AW:1]),
        .c_valid(qv), .c_ready(qr), .c_data(qa));
    reg [USER_W:0] i_clr;
    always @(posedge ck[0] or negedge rn) if (!rn) i_clr[0] <= 1'b0; else i_clr[0] <= f_clr[0];
    always @(posedge ck[0]) i_clr[USER_W:1] <= f_clr[USER_W:1];
    wire rv; wire [1023:0] rd; wire [2:0] flt;
    ot_dsrom_mtp_hrow_store #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .RS(RS), .AW(AW)) u_st (
        .clk(ck[0]), .rst_n(rn), .i_v(pv), .i_r(pr), .i_d(pd), .c_v(i_clr[0]), .c_user(i_clr[USER_W:1]),
        .q_v(qv), .q_r(qr), .q_a(qa), .r_v(rv), .r_d(rd), .fault(flt));
    reg [1024:0] o_rs; reg [2:0] o_flt;
    always @(posedge ck[0] or negedge rn) if (!rn) begin o_rs[0] <= 1'b0; o_flt <= 3'd0; end
                                          else begin o_rs[0] <= rv; o_flt <= flt; end
    always @(posedge ck[0]) o_rs[1024:1] <= rd;
    assign t_vrs = o_rs; assign t_flt = o_flt;
endmodule
