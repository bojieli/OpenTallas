`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hgi-1010/d (2026-10-10, N4): the SM record path as it sits on the generic HBM die.
//   ot_hgi_sm_cp   -- inside the CP block (cmdproc view): ot_hgi_sm_record on the CP's SM record bus (sm_rec / sm_ret),
//                     one ot_hgi_sm_leaf_cp per SM onto the die control leaves (c, 112 b a leaf: ot_hgi_sm_leaf.sv layout),
//                     the x-load ot_hgi_sm_xload on the E-group wide VM read lanes (client 0) driving the die x trunk
//                     (2,063 b, broadcast to every SM), and the publication COMMAND link to the publication station.
//   ot_hgi_sm_pub_stn -- the publication station at the SM result trunk ends: ot_hgi_sm_pub (banked-SRAM form) on the
//                     32 SM result leaves (r, 270 b each) and its NPC VM packet clients, behind the command link.
// Publication command link (registered stages of any depth between the two): a one-credit pulse link like the SM leaf:
//   down pc[112:0] = {bf16, p 4, q 13, m 20, space 2, stride 32, base 40, v}: v is a ONE-EDGE pulse with the fields, sent
//        only while no earlier command is unacknowledged;
//   up   pr[3:0]   = {fault, done, ack, smf}: ack = the station handed the command to the unit; done / fault = the
//        unit's pub_done / pub_fault, one-edge pulses; smf = any SM's sticky fault (the fault bit of the result leaves,
//        which end at the station), level -> every SM leaf's fault input in the CP.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_cp #(
    parameter integer NSM = 32,
    parameter integer WLQ = 12,
    parameter integer WD = 8,
    parameter integer MUT_PC = 0           // bench mutant: the publication command is sent without its credit
) (
    input  wire               clk,
    input  wire               rst_n,
    // the CP's SM record bus (ot_hgi_cp_die sm_rec / sm_ret)
    input  wire [938:0]       sm_rec,      // {n_B 21, n_A 21, O 256, B 256, A 256, header 128, valid}
    output wire [2:0]         sm_ret,      // {fault, done, ready}
    // the SM control leaves (one 112-b leaf an SM, ot_hgi_sm_leaf layout), packed by direction for the die binding:
    //   c_dn leaf s = {leaf[110:103], leaf[101:45], leaf[41:0]} (107 b), c_up leaf s = {leaf[111], leaf[102], leaf[44:42]} (5 b)
    output wire [NSM*107-1:0] c_dn,
    input  wire [NSM*5-1:0]   c_up,
    // the x trunk (every SM's x-store write port)
    output wire [2062:0]      x_trunk,     // {xw_data 2048, xw_grp 7, xw_addr 7, xw_en}
    // the E-group wide VM read lanes (x-load = client 0)
    output wire               rg_req,
    input  wire               rg_gnt,
    output wire [32*16-1:0]   wrq,
    input  wire [31:0]        wrq_cr,
    input  wire [32*257-1:0]  wrr,
    // the publication command link
    output reg  [112:0]       pc,
    input  wire [3:0]         pr
);
    wire rec_rdy, rec_done, rec_fault, halted;
    // registered return {fault, done, ready}
    reg [2:0] ret_q; always @(posedge clk or negedge rst_n) if (!rst_n) ret_q <= 3'd0; else ret_q <= {rec_fault, rec_done, rec_rdy};
    assign sm_ret = ret_q;
    wire x_v, x_rdy, x_done, x_fault; wire [39:0] x_base; wire [20:0] x_n; wire [3:0] x_p; wire [31:0] x_stride;
    wire [1:0] x_space, x_fmt;
    wire pub_v, pub_bf16; wire [39:0] pub_base; wire [31:0] pub_stride; wire [1:0] pub_space; wire [19:0] pub_m;
    wire [12:0] pub_q; wire [3:0] pub_p;
    reg pub_rdy_c, pub_done_c, pub_fault_c;
    wire [NSM*106-1:0] sm_cmd; wire [NSM*4-1:0] sm_r; wire cg_en;
    reg pc_out; reg [3:0] pr_q;
    ot_hgi_sm_record #(.NSM(NSM), .LEGACY(0)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(sm_rec[0]),
        .rec_rdy(rec_rdy), .rec_hdr(sm_rec[128:1]), .rec_a(sm_rec[384:129]), .rec_b(sm_rec[640:385]), .rec_o(sm_rec[896:641]),
        .rec_n_a(sm_rec[917:897]), .rec_n_b(sm_rec[938:918]), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space),
        .x_fmt(x_fmt), .x_done(x_done), .x_fault(x_fault), .pub_v(pub_v), .pub_rdy(pub_rdy_c), .pub_base(pub_base),
        .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16),
        .pub_done(pub_done_c), .pub_fault(pub_fault_c), .lg_cmd({NSM*106{1'b0}}), .lg_ret(), .sm_cmd(sm_cmd),
        .sm_ret(sm_r), .sm_cg_en(cg_en));
    // the SM leaves
    genvar s;
    generate for (s = 0; s < NSM; s = s + 1) begin : g_leaf
        ot_hgi_sm_leaf_cp #(.CW(106)) u_lc (.clk(clk), .rst_n(rst_n), .cmd(sm_cmd[s*106 +: 106]), .cg_en(cg_en),
            .fault(pr_q[0]), .ret(sm_r[s*4 +: 4]), .dn(dn), .up(up));
        wire [111:0] dn, up;
        assign c_dn[s*107 +: 107] = {dn[110:103], dn[101:45], dn[41:0]};
        assign up = {c_up[s*5 + 4], 8'd0, c_up[s*5 + 3], 57'd0, c_up[s*5 +: 3], 42'd0};
    end endgenerate
    // the x-load on the E-group lanes (no packet client: NXC 1 tied idle)
    wire xw_en; wire [6:0] xw_addr, xw_grp; wire [2047:0] xw_data;
    ot_hgi_sm_xload #(.NXC(1), .WVM(1), .WLQ(WLQ), .WD(WD)) u_x (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy),
        .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_done(x_done),
        .x_fault(x_fault), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .vmq(),
        .vmr({274{1'b0}}), .rg_req(rg_req), .rg_gnt(rg_gnt), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr));
    assign x_trunk = {xw_data, xw_grp, xw_addr, xw_en};
    // the publication command link (one credit)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pc <= '0; pc_out <= 1'b0; pr_q <= 4'd0; pub_rdy_c <= 1'b0; pub_done_c <= 1'b0; pub_fault_c <= 1'b0; end
        else begin
            pr_q <= pr;
            pc[0] <= 1'b0; pub_rdy_c <= 1'b0;
            // the record holds pub_v and its fields until pub_rdy: ready on the edge the station's ack lands
            if (pub_v && (!pc_out || MUT_PC != 0) && !pc[0] && !pub_rdy_c) begin
                pc <= {pub_bf16, pub_p, pub_q, pub_m, pub_space, pub_stride, pub_base, 1'b1}; pc_out <= 1'b1;
            end
            if (pr_q[1] && pc_out) begin pc_out <= 1'b0; pub_rdy_c <= 1'b1; end
            pub_done_c <= pr_q[2]; pub_fault_c <= pr_q[3];
        end
    end
endmodule

module ot_hgi_sm_pub_stn #(
    parameter integer NSM = 32,
    parameter integer NPC = 2,
    parameter integer NE = 2
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [112:0]       pc,
    output reg  [3:0]         pr,
    // the SM result leaves (r, 270 b an SM: {fault, rdata 256, rrow 12, rv})
    input  wire [NSM*270-1:0] r,
    // VM packet clients
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr
);
    reg c_v; reg [111:0] c_f;                              // the held command
    reg smf;                                               // any SM's fault (registered)
    always @(posedge clk or negedge rst_n) begin : sf
        integer k; reg f; f = 1'b0;
        if (!rst_n) smf <= 1'b0; else begin for (k = 0; k < NSM; k = k + 1) f = f | r[k*270 + 269]; smf <= f; end
    end
    wire pub_rdy, pub_done, pub_fault;
    wire [NSM-1:0] rv; wire [NSM*12-1:0] rrow; wire [NSM*256-1:0] rdata;
    genvar s;
    for (s = 0; s < NSM; s = s + 1) begin : g_r
        assign rv[s] = r[s*270]; assign rrow[s*12 +: 12] = r[s*270 + 1 +: 12]; assign rdata[s*256 +: 256] = r[s*270 + 13 +: 256];
    end
    ot_hgi_sm_pub #(.NSM(NSM), .NC(8), .NPC(NPC), .MEM(1), .NE(NE)) u_pub (.clk(clk), .rst_n(rst_n), .pub_v(c_v),
        .pub_rdy(pub_rdy), .pub_base(c_f[39:0]), .pub_stride(c_f[71:40]), .pub_space(c_f[73:72]), .pub_m(c_f[93:74]),
        .pub_q(c_f[106:94]), .pub_p(c_f[110:107]), .pub_bf16(c_f[111]), .pub_done(pub_done), .pub_fault(pub_fault),
        .sm_rv(rv), .sm_rrow(rrow), .sm_rdata(rdata), .vmq(vmq), .vmr(vmr), .s0_v(), .s0_idx(), .s0_data());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_v <= 1'b0; pr <= 4'd0; end
        else begin
            pr <= {pub_fault, pub_done, 1'b0, smf};
            if (c_v && pub_rdy) begin c_v <= 1'b0; pr[1] <= 1'b1; end
            if (pc[0]) begin
                if (c_v && !pub_rdy) pr[3] <= 1'b1;           // a command onto an unacknowledged one: fail closed
                c_v <= 1'b1; c_f <= pc[112:1];
            end
        end
    end
endmodule
`default_nettype wire
