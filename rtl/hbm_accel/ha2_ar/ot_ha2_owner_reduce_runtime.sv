`timescale 1ns/1ps
// Additive runtime capacity form of pinned owner reducer. Original unchanged.
// No arrival register added; SLOTREG is the existing one-cycle operand select.
// arm is transaction-local and allowed only after parent queue/pipe/credit quiet.
module ot_ha2_owner_reduce_runtime #(
    parameter integer GS      = 16,
    parameter integer NC      = 8,
    parameter integer PFMAX   = 384,
    parameter integer LANES   = 16,
    parameter integer ONESHOT = 0,
    parameter integer BF16    = 1,
    parameter integer INJ     = 2,
    parameter integer NP      = 20,
    parameter integer LAT     = 7,
    parameter integer SLOTREG = 0,
    parameter integer FW      = 32 * LANES,
    parameter integer PWT     = FW + 25
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           rank,
    input wire [15:0] pf, input wire active, arm, bad_peer,
    output wire quiet,
    input  wire [INJ-1:0]       h_v,             // own partials (hub delay line outputs)
    input  wire [INJ*(16+FW)-1:0] h_d,
    input  wire [NP-1:0]        p_v,             // peer partials popped this cycle (rb_pop && !kind)
    input  wire [NP*PWT-1:0]    p_flit,          // the popped receive-buffer heads
    output reg                  r_v,             // a packed result flit
    output reg  [15:0]          r_m,
    output reg  [FW-1:0]        r_d,
    output reg                  dupe,
    output wire                 issue_o
);
    wire [31:0] RANK = {24'b0, rank};
    wire [31:0] J = RANK % NC;
    wire [31:0] PF = {16'b0,pf};
    wire [31:0] OF = PF / NC;
    localparam integer OFMX = PFMAX / NC;
    localparam integer PCW = $clog2(OFMX+1);
    reg [PCW-1:0] pending;
    wire config_ok = PF > 0 && PF <= PFMAX && PF % NC == 0 && (!BF16 || !(OF & 1));
    assign quiet = pending == 0 && (!active || rptr >= OF);
    always @(posedge clk or negedge rst_n)
      if (!rst_n) pending <= 0;
      else if (arm) pending <= 0;
      else pending <= pending + (issue ? 1 : 0) - (r_v ? (BF16 ? 2 : 1) : 0);
    localparam integer LV   = $clog2(NC);

    reg [FW-1:0] opd [0:NC-1][0:OFMX-1];
    reg [OFMX-1:0] pres [0:NC-1];
    integer rptr;
    reg  [NC-1:0] col;
    always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (rptr < OF) ? pres[c][rptr] : 1'b0;
    wire all_here = &col;
    wire issue = active && config_ok && !dupe && all_here && !arm;
    assign issue_o = issue;

    // level-0 operands
    reg  [FW-1:0] opsel [0:NC-1];
    always @* for (integer c = 0; c < NC; c = c + 1) opsel[c] = opd[c][rptr < OF ? rptr : 0];
    wire [FW-1:0] lvl [0:LV][0:NC-1];
    wire [LV:0] lvv;
    wire        t_v;          // tree issue strobe
    wire [15:0] t_i;          // flit index entering the tree
    generate if (SLOTREG == 0) begin : g_comb
        for (genvar c = 0; c < NC; c = c + 1) begin : g_l0
            assign lvl[0][c] = opsel[c];
        end
        assign t_v = issue;
        assign t_i = 16'(rptr);
    end else begin : g_reg
        reg [FW-1:0] sq [0:NC-1];
        reg          sv;
        reg [15:0]   si;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) sv <= 1'b0;
            else sv <= issue;
        always @(posedge clk) if (issue) begin
            for (integer c = 0; c < NC; c = c + 1) sq[c] <= opsel[c];
            si <= 16'(rptr);
        end
        for (genvar c = 0; c < NC; c = c + 1) begin : g_l0
            assign lvl[0][c] = sq[c];
        end
        assign t_v = sv;
        assign t_i = si;
    end endgenerate
    assign lvv[0] = t_v;
    for (genvar l = 1; l <= LV; l = l + 1) begin : g_lv
        localparam integer NN = NC >> l;
        wire [NN*LANES-1:0] vv;
        /* verilator lint_off UNUSEDSIGNAL */
        wire [NN*2*LANES-1:0] ee;
        /* verilator lint_on UNUSEDSIGNAL */
        for (genvar i = 0; i < NN; i = i + 1) begin : g_n
            for (genvar ln = 0; ln < LANES; ln = ln + 1) begin : g_ln
                ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(lvv[l-1]),
                    .a(lvl[l-1][2*i][32*ln +: 32]), .b(lvl[l-1][2*i+1][32*ln +: 32]),
                    .y(lvl[l][i][32*ln +: 32]), .err(ee[(i*LANES+ln)*2 +: 2]), .valid_out(vv[i*LANES+ln]));
            end
        end
        assign lvv[l] = vv[0];
    end
    // the flit index rides beside the tree
    wire        ti_v;
    wire [15:0] ti_d;
    ot_ha2_delay #(.W(16), .D(LAT * LV)) u_tidx (.clk(clk), .rst_n(rst_n), .v_in(t_v), .d_in(t_i),
        .v_out(ti_v), .d_out(ti_d));
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] s;
        s = {1'b0, b} + 33'h7FFF + {32'b0, b[16]};
        bf16 = s[31:16];
    endfunction
    reg [FW-1:0] hold;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r_v <= 1'b0;
        else begin
            r_v <= 1'b0;
            if (lvv[LV]) begin
                if (BF16) begin
                    if (!ti_d[0]) for (integer ln = 0; ln < LANES; ln = ln + 1)
                        hold[16*ln +: 16] <= bf16(lvl[LV][0][32*ln +: 32]);
                    else begin
                        r_v <= 1'b1;
                        r_m <= ti_d >> 1;
                        for (integer ln = 0; ln < LANES; ln = ln + 1) begin
                            r_d[16*ln +: 16] <= hold[16*ln +: 16];
                            r_d[16*(LANES+ln) +: 16] <= bf16(lvl[LV][0][32*ln +: 32]);
                        end
                    end
                end else begin
                    r_v <= 1'b1; r_m <= ti_d; r_d <= lvl[LV][0];
                end
            end
        end
    // slot writes, the reducer pointer (the endpoint's state-update block, same statement order)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer c = 0; c < NC; c = c + 1) pres[c] <= '0;
            rptr <= 0; dupe <= 1'b0;
        end else if (arm) begin
            for (integer c = 0; c < NC; c = c + 1) pres[c] <= '0;
            rptr <= 0; // no fault/debt reset: arm is permitted only after actual quiet
        end else begin
            if (bad_peer || (active && !config_ok)) dupe <= 1'b1;
            for (integer i = 0; i < INJ; i = i + 1)
                if (active && config_ok && h_v[i]) begin : own
                    integer f, fl;
                    f = integer'(h_d[(16+FW)*i + FW +: 16]);
                    if (f >= PF) dupe <= 1'b1;
                    else if (f / OF == J) begin
                        fl = f % OF;
                        if (pres[J][fl]) dupe <= 1'b1;
                        pres[J][fl] <= 1'b1;
                        opd[J][fl] <= h_d[(16+FW)*i +: FW];
                    end
                end
            for (integer p = 0; p < NP; p = p + 1)
                if (active && config_ok && p_v[p]) begin : peer
                    integer c, fl;
                    c = integer'(p_flit[p*PWT + FW+16 +: 8]);
                    fl = integer'(p_flit[p*PWT + FW +: 16]);
                    if (c >= NC || fl >= OF || pres[c][fl]) dupe <= 1'b1;
                    else begin pres[c][fl] <= 1'b1; opd[c][fl] <= p_flit[p*PWT +: FW]; end
                end
            if (issue) begin
                for (integer c = 0; c < NC; c = c + 1) pres[c][rptr] <= 1'b0;
                rptr <= rptr + 1;
            end
        end
endmodule
