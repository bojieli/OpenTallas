`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_wsched (claude S81 VM owner r8, 2026-10-14): the fixed-rule WRITE service of the static VM.
// NSRC 512-b row sources (SU, HC, landing, collective ...) -> the 32 logical write ports of dsfd_vm_static512_suhc.
// Owner rule 2026-10-14T18:59: no ready, credit, queue head/tail, arbitration or schedule extension.  Every decision is
// a fixed function of the compiled request pattern, so the compiler predicts every edge exactly:
//   P    source pin register (row 14, mask 16 words, data 512, tag 8, valid) sampled at edge P.
//        capture LANE of source c = number of valid sources c' < c whose row hashes to the same bank this edge
//        (bank = row[4:0] ^ {row[7:5], 2'b00}); lane >= 3 is a schedule fault (the record is dropped, fail closed).
//   P+1  dsfd_vm_static_wdispatch128 pin register (4 quarters x 4 slices; storage slot = lane); P+2 records registered
//   P+3  dsfd_vm_static_wstage128 (DEPTH 3) captures
//   DRAIN RULE (fixed): lane c of a bank is drained into the scatter sample at edge P+4+c.  Two lanes of one bank due on
//        one edge (a lane-c capture at edge E and a lane-c' capture at E + c - c') is a schedule fault: the lower lane
//        drains, the other is reported (never delayed).  Earliest scatter sample = source pin + 4 (lane 0).
//   Packet: bank k -> logical write port J = 8 (k mod 4) + k / 4 (row[1:0] = k mod 4 = the scatter lane rule).
// All four 128-b slices run identical control (row / valid / tag from slice 0, mask / data per slice).
// Faults (sticky, bit vector): [0] lane >= 3, [1] drain collision, [2..17] wdispatch, [18..145] wstage.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_wsched #(parameter integer NSRC = 48) (
    input  wire                 ck, rst_n,
    input  wire [NSRC-1:0]      i_v,
    input  wire [14*NSRC-1:0]   i_row,
    input  wire [16*NSRC-1:0]   i_mask,
    input  wire [512*NSRC-1:0]  i_data,
    input  wire [8*NSRC-1:0]    i_tag,
    output wire [31:0]          wq_v,
    output wire [447:0]         wq_row,
    output wire [511:0]         wq_mask,
    output wire [16383:0]       wq_data,
    output wire [255:0]         wq_tag,
    output wire                 fault
);
    reg [1:0] rr;
    always @(posedge ck or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];

    // ---------------------------------------------------------------- W0 pins + fixed lane function
    reg [NSRC-1:0] pv; reg [14*NSRC-1:0] pr; reg [16*NSRC-1:0] pm; reg [512*NSRC-1:0] pd; reg [8*NSRC-1:0] pt;
    always @(posedge ck) begin
        if (!rn) pv <= {NSRC{1'b0}}; else pv <= i_v;
        pr <= i_row; pm <= i_mask; pd <= i_data; pt <= i_tag;
    end
    reg [2*NSRC-1:0] lane; reg [NSRC-1:0] lv; reg lane_bad;
    always @* begin : p_lane integer c, d; reg [4:0] bc, bd; reg [5:0] n;
        lane_bad = 1'b0;
        for (c = 0; c < NSRC; c = c + 1) begin
            bc = pr[14*c +: 5] ^ {pr[14*c+5 +: 3], 2'b00};
            n = 6'd0;
            for (d = 0; d < c; d = d + 1) begin
                bd = pr[14*d +: 5] ^ {pr[14*d+5 +: 3], 2'b00};
                if (pv[d] && bd == bc) n = n + 6'd1;
            end
`ifdef OT_VM_WSCHED_MUT_LANE
            lane[2*c +: 2] = 2'd0;                    // MUTANT: every record on lane 0 (dispatch duplicate)
`else
            lane[2*c +: 2] = (n > 6'd2) ? 2'd3 : n[1:0];
`endif
            lv[c] = pv[c] && n <= 6'd2;
            if (pv[c] && n > 6'd2) lane_bad = 1'b1;
        end
    end

    // ---------------------------------------------------------------- P+1..P+3 dispatch + storage, per slice
    wire [4*96-1:0] cap_v;                 // slice-major, 96 = 32 banks x 3 lanes
    wire [15:0] dflt; wire [127:0] sflt;
    wire [32*4-1:0] sv;                    // per slice drain output valid (bank-major)
    wire [32*14-1:0] srow; wire [32*8-1:0] stag;
    wire [4*32*4-1:0] smask; wire [4*32*128-1:0] sdata;
    reg  [31:0] dr_v; reg [63:0] dr_s;     // drain (shared by the 4 slices)
    genvar s, z, b, c;
    generate for (s = 0; s < 4; s = s + 1) begin : slice
        wire [4*NSRC-1:0] m4; wire [128*NSRC-1:0] d128;
        for (c = 0; c < NSRC; c = c + 1) begin : src
            assign m4[4*c +: 4] = pm[16*c + 4*s +: 4];
            assign d128[128*c +: 128] = pd[512*c + 128*s +: 128];
        end
        wire [95:0] cv; wire [191:0] cs; wire [1343:0] cr; wire [383:0] cm; wire [12287:0] cd; wire [767:0] ct;
        for (z = 0; z < 4; z = z + 1) begin : quarter
            dsfd_vm_static_wdispatch128 #(.NSRC(NSRC), .NBANK(8), .BANK_BASE(8*z)) u_d (
                .ck(ck), .rst_n(rst_n), .i_v(lv), .i_row(pr), .i_mask(m4), .i_data(d128), .i_tag(pt),
                .i_capture_lane(lane), .i_storage_slot(lane),
                .o_v(cv[24*z +: 24]), .o_slot(cs[48*z +: 48]), .o_row(cr[336*z +: 336]), .o_mask(cm[96*z +: 96]),
                .o_data(cd[3072*z +: 3072]), .o_tag(ct[192*z +: 192]), .fault(dflt[4*s + z]));
        end
        assign cap_v[96*s +: 96] = cv;
        for (b = 0; b < 32; b = b + 1) begin : bank
            wire [13:0] orow; wire [7:0] otag;
            dsfd_vm_static_wstage128 #(.DEPTH(3)) u_w (
                .ck(ck), .rst_n(rst_n),
                .capture_v(cv[3*b +: 3]), .capture_slot(cs[6*b +: 6]), .capture_row(cr[42*b +: 42]),
                .capture_mask(cm[12*b +: 12]), .capture_data(cd[384*b +: 384]), .capture_tag(ct[24*b +: 24]),
                .drain_v(dr_v[b]), .drain_slot(dr_s[2*b +: 2]),
                .o_v(sv[32*s + b]), .o_row(orow), .o_mask(smask[128*s + 4*b +: 4]),
                .o_data(sdata[4096*s + 128*b +: 128]), .o_tag(otag), .fault(sflt[32*s + b]));
            if (s == 0) begin : ctl
                assign srow[14*b +: 14] = orow; assign stag[8*b +: 8] = otag;
            end
        end
    end endgenerate

    // ---------------------------------------------------------------- fixed drain rule (from slice 0's captures)
    // h1 = dispatch o_v sampled at P+3 (the storage capture edge): lane 0 drains into the P+4 scatter sample, h2 lane 1
    // at P+5, h3 lane 2 at P+6
    reg [95:0] h1, h2, h3; reg drain_bad;
    always @(posedge ck) begin
        if (!rn) begin h1 <= 96'd0; h2 <= 96'd0; h3 <= 96'd0; end
        else begin h1 <= cap_v[95:0]; h2 <= h1; h3 <= h2; end
    end
    always @* begin : p_drain integer k; reg l0, l1, l2;
        drain_bad = 1'b0;
        for (k = 0; k < 32; k = k + 1) begin
            l0 = h1[3*k]; l1 = h2[3*k+1]; l2 = h3[3*k+2];
`ifdef OT_VM_WSCHED_MUT_DRAIN
            l1 = h1[3*k+1];                              // MUTANT: lane 1 drains one edge early (P+4, not P+5)
`endif
            dr_v[k] = l0 | l1 | l2;
            dr_s[2*k +: 2] = l0 ? 2'd0 : l1 ? 2'd1 : 2'd2;
            if ((l0 && l1) || (l0 && l2) || (l1 && l2)) drain_bad = 1'b1;
        end
    end

    // ---------------------------------------------------------------- packet: bank k -> port 8 (k mod 4) + k / 4
    genvar k;
    generate for (k = 0; k < 32; k = k + 1) begin : packet
        localparam integer J = 8 * (k % 4) + k / 4;
        assign wq_v[J] = sv[k];
        assign wq_row[14*J +: 14] = srow[14*k +: 14];
        assign wq_tag[8*J +: 8] = stag[8*k +: 8];
        for (s = 0; s < 4; s = s + 1) begin : sl
            assign wq_mask[16*J + 4*s +: 4] = smask[128*s + 4*k +: 4];
            assign wq_data[512*J + 128*s +: 128] = sdata[4096*s + 128*k +: 128];
        end
    end endgenerate

    reg [1:0] own;
    always @(posedge ck) if (!rn) own <= 2'b00; else own <= own | {drain_bad, lane_bad};
    assign fault = |own | |dflt | |sflt;
endmodule
`default_nettype wire
