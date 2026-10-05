`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Stack endpoint of the local K arbitration partition
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md): the K port of one HBM3E stack.
//   request   a two-entry registered ingress queue (k_rdy = its registered
//             room); pc_of(addr) is decoded at ingress (the monolithic
//             arbiter's global NPC hash); the head goes, as a broadcast
//             payload with one valid per region, to its region's queue when
//             that queue has room (in order: the head waits for its region);
//   response  one CREDITS-entry queue per region, filled by the region's
//             credited sends (every trunk input lands in a register here);
//             the credit loop is 3 cycles (send, pop, registered return), so
//             CREDITS = 3 keeps one response per cycle from a single region;
//             the consumer sees the lowest-index non-empty queue; a pop
//             returns that region's credit through a register;
//   events    registered OR of the regions' K write completions, K grant
//             count at ingress acceptance, B grant and conflict counts
//             accumulated from the regions' registered per-cycle counts.
// Every trunk-facing output is a register or a function of this endpoint's
// registers; no combinational path crosses root -> region -> root.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_stack_ep #(
    parameter integer NPC     = 32,
    parameter integer AW      = 28,
    parameter integer TAGW    = 16,
    parameter integer LENW    = 4,
    parameter integer BEATW   = 4,
    parameter integer DW      = 256,
    parameter integer CREDITS = 3,   // endpoint queue entries per region = region credits
    // regions this endpoint serves (NPC / 4 in the stack; fewer only for a physical cut)
    parameter integer NREG    = NPC / 4
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  k_v,
    output wire                  k_rdy,
    input  wire [AW-1:0]         k_addr,
    input  wire [LENW-1:0]       k_len,
    input  wire [TAGW-1:0]       k_tag,
    input  wire                  k_we,
    input  wire [DW-1:0]         k_wdata,
    input  wire [DW/8-1:0]       k_wstrb,
    output reg                   k_wr_done,
    output wire                  k_rsp_v,
    input  wire                  k_rsp_rdy,
    output wire [TAGW-1:0]       k_rsp_tag,
    output wire [BEATW-1:0]      k_rsp_beat,
    output wire [DW-1:0]         k_rsp_data,
    // trunks
    output wire [NREG-1:0]       rq_v,
    input  wire [NREG-1:0]       rq_rdy,
    output wire [1:0]            rq_lpc,
    output wire [AW-1:0]         rq_addr,
    output wire [LENW-1:0]       rq_len,
    output wire [TAGW-1:0]       rq_tag,
    output wire                  rq_we,
    output wire [DW-1:0]         rq_wdata,
    output wire [DW/8-1:0]       rq_wstrb,
    input  wire [NREG-1:0]       rs_v,
    input  wire [NREG*(TAGW+BEATW+DW)-1:0] rs_d,
    output reg  [NREG-1:0]       rs_cr,
    input  wire [NREG-1:0]       r_kwd,
    input  wire [NREG*3-1:0]     r_bg,
    input  wire [NREG*3-1:0]     r_ct,
    output reg  [31:0]           k_grants,
    output reg  [31:0]           b_grants,
    output reg  [31:0]           contended
);
    localparam integer LPC  = $clog2(NPC);
    localparam integer LREG = (NREG > 1) ? $clog2(NREG) : 1;
    localparam integer PW   = AW + LENW + TAGW + 1 + DW + DW / 8;
    localparam integer RW   = TAGW + BEATW + DW;
    function automatic [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = LPC'(((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1));
    endfunction
    wire           iq_v; wire [LPC+PW-1:0] iq_d;
    wire [LPC-1:0] iq_pc = iq_d[LPC+PW-1 -: LPC];
    // the region of the head (a physical cut with NREG < NPC/4 folds regions onto its NREG)
    wire [LREG-1:0] iq_reg = (NREG > 1) ? LREG'(iq_pc >> 2) : '0;
    ot_chip_v41x_karb_q2 #(.W(LPC + PW)) u_iq (
        .clk(clk), .rst_n(rst_n), .in_v(k_v), .in_rdy(k_rdy),
        .in_d({pc_of(k_addr), k_addr, k_len, k_tag, k_we, k_wdata, k_wstrb}),
        .out_v(iq_v), .out_rdy(rq_rdy[iq_reg]), .out_d(iq_d));
    assign {rq_addr, rq_len, rq_tag, rq_we, rq_wdata, rq_wstrb} = iq_d[PW-1:0];
    assign rq_lpc = iq_pc[1:0];
    genvar g;
    generate for (g = 0; g < NREG; g = g + 1) begin : g_v
        assign rq_v[g] = iq_v && iq_reg == g;
    end endgenerate
    // per-region response queues
    wire [NREG-1:0]    q_v, q_rdy;
    wire [NREG*RW-1:0] q_d;
    reg  [LREG-1:0]    esel; reg eany;
    integer i;
    always @(*) begin
        esel = '0; eany = 1'b0;
        for (i = NREG - 1; i >= 0; i = i - 1) if (q_v[i]) begin esel = LREG'(i); eany = 1'b1; end
    end
    wire [NREG-1:0] pop = {{(NREG-1){1'b0}}, eany && k_rsp_rdy} << esel;
    generate for (g = 0; g < NREG; g = g + 1) begin : g_q
        ot_chip_v41x_karb_qn #(.W(RW), .DEPTH(CREDITS)) u_q (
            .clk(clk), .rst_n(rst_n), .in_v(rs_v[g]), .in_rdy(q_rdy[g]), .in_d(rs_d[g*RW +: RW]),
            .out_v(q_v[g]), .out_rdy(pop[g]), .out_d(q_d[g*RW +: RW]));
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_n && rs_v[g] && !q_rdy[g])
            $error("ot_chip_v41x_karb_stack_ep: region %0d sent without a credit", g);
`endif
    end endgenerate
    assign k_rsp_v = eany;
    assign {k_rsp_tag, k_rsp_beat, k_rsp_data} = q_d[esel*RW +: RW];
    reg [LPC+2:0] bsum, csum;
    always @(*) begin
        bsum = '0; csum = '0;
        for (i = 0; i < NREG; i = i + 1) begin
            bsum = bsum + (LPC+3)'(r_bg[i*3 +: 3]);
            csum = csum + (LPC+3)'(r_ct[i*3 +: 3]);
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rs_cr <= '0; k_wr_done <= 1'b0; k_grants <= 0; b_grants <= 0; contended <= 0;
        end else begin
            rs_cr <= pop;
            k_wr_done <= |r_kwd;
            if (k_v && k_rdy) k_grants <= k_grants + 1;
            b_grants  <= b_grants + 32'(bsum);
            contended <= contended + 32'(csum);
        end
endmodule
