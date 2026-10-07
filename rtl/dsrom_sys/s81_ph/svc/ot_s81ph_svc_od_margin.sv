`timescale 1ns/1ps
// Opt-in S81 OD successor. Source: 41c34fce0; default tile remains unchanged.
// Model: uarch_model.dsrom_s81_svcio_od_margin_price().
// The queue includes accepted-but-not-yet-written pin data in its credit count.
// Three queued words are sufficient for a one-edge input capture at II=1.
module ot_s81ph_pin_queue #(parameter W=512)(
    input wire clk, rst_n, input wire i_v, input wire [W-1:0] i_d,
    output reg i_r, output wire o_v, output wire [W-1:0] o_d, input wire o_r);
    reg [W-1:0] pin_d;
    reg pin_v;
    reg [W-1:0] mem [0:2];
    reg [1:0] wp, rp, stored, total;
    wire take=i_v && i_r;
    wire pop=o_v && o_r;
    wire [1:0] total_next=total + take - pop;
    assign o_v=stored != 0;
    localparam NS=(W+31)/32;
    (* keep *) reg [2:0] wen [0:NS-1];
    (* keep *) reg [2:0] rsel [0:NS-1];
    wire [1:0] wp_next=pin_v ? (wp==2 ? 0 : wp+1'b1) : wp;
    wire [1:0] rp_next=pop ? (rp==2 ? 0 : rp+1'b1) : rp;
    generate for (genvar sl=0; sl<NS; sl=sl+1) begin : g_slice
        localparam SW=(W-sl*32<32) ? W-sl*32 : 32;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wen[sl]<=0; rsel[sl]<=1; end
            else begin
                wen[sl]<=take ? (3'b001 << wp_next) : 0;
                rsel[sl]<=3'b001 << rp_next;
            end
        assign o_d[sl*32 +: SW] =
            ({SW{rsel[sl][0]}} & mem[0][sl*32 +: SW]) |
            ({SW{rsel[sl][1]}} & mem[1][sl*32 +: SW]) |
            ({SW{rsel[sl][2]}} & mem[2][sl*32 +: SW]);
        for (genvar row=0; row<3; row=row+1) begin : g_row
            always @(posedge clk) if (wen[sl][row]) begin
`ifdef S81PH_SVC_MUT_SKID
                if (row != 1) mem[row][sl*32 +: SW] <= pin_d[sl*32 +: SW];
`else
                mem[row][sl*32 +: SW] <= pin_d[sl*32 +: SW];
`endif
            end
        end
    end endgenerate
    // No enable or data logic between the input pin and its capture flop.
    always @(posedge clk) pin_d <= i_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pin_v<=0; i_r<=0; wp<=0; rp<=0; stored<=0; total<=0;
        end else begin
            pin_v<=take;
            total<=total_next;
            i_r<=total_next < 3;
            stored<=stored + pin_v - pop;
            if (pin_v) wp <= wp==2 ? 0 : wp+1'b1;
            if (pop) rp <= rp==2 ? 0 : rp+1'b1;
        end
    end
endmodule

module ot_s81ph_fmerge_margin #(parameter integer N = 4, parameter integer LMAX = 255) (   // LMAX: the collector's frame buffer
    input  wire           clk, rst_n,
    input  wire [N-1:0]   s_v, input wire [512*N-1:0] s_d, output wire [N-1:0] s_r,
    output wire           o_v, output reg [511:0] o_d,
    output reg            bad
);
    reg emit_v, valid_d;
    assign o_v = valid_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_d <= 0; else valid_d <= emit_v;
    wire [N-1:0] k_v; wire [512*N-1:0] k_d; reg [N-1:0] k_r;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_s
        ot_s81ph_pin_queue #(.W(512)) u_k (.clk(clk), .rst_n(rst_n), .i_v(s_v[g]), .i_d(s_d[512*g +: 512]), .i_r(s_r[g]),
            .o_v(k_v[g]), .o_d(k_d[512*g +: 512]), .o_r(k_r[g]));
    end endgenerate
    localparam integer SW = (N > 1) ? $clog2(N) : 1;
    reg busy, hdr; reg [SW-1:0] cur; reg [11:0] rem; reg [SW-1:0] rr;
    // next source: registered round-robin pick among valid skid heads (only at a frame boundary)
    reg [SW-1:0] pick; reg pick_v; integer j;
    always @* begin
        pick = rr; pick_v = 1'b0;
        for (j = N - 1; j >= 0; j = j - 1)
            if (k_v[(rr + j) % N]) begin pick = (rr + j) % N; pick_v = 1'b1; end
    end
    wire [511:0] cd = k_d[512*cur +: 512];          // control only (header len, 12 b)
    (* keep *) reg [N-1:0] sel_c [0:15];            // one-hot copies of cur, 32 data bits each
    // A masked-source register removes the observed select->AND/OR cone.
    // Four banks, each driven by kept one-hot replicas (32 data bits/copy).
    reg [511:0] masked [0:N-1];
    reg [511:0] o_dn;
    integer b, t;
    generate for (genvar src=0; src<N; src=src+1) begin : g_mask
        for (genvar sl=0; sl<16; sl=sl+1) begin : g_sl
            always @(posedge clk)
                masked[src][32*sl +: 32] <=
                    {32{sel_c[sl][src]}} & k_d[512*src+32*sl +: 32];
        end
    end endgenerate
    always @* begin
        o_dn=0;
        for (t=0; t<N; t=t+1) o_dn=o_dn | masked[t];
    end
    always @* begin k_r = {N{1'b0}}; if (busy) k_r[cur] = 1'b1; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin busy <= 1'b0; hdr <= 1'b0; cur <= 0; rem <= 0; rr <= 0; emit_v <= 1'b0; bad <= 1'b0; end
        else begin
            emit_v <= 1'b0;
            if (!busy) begin
                if (pick_v) begin busy <= 1'b1; hdr <= 1'b1; cur <= pick; for (b = 0; b < 16; b = b + 1) sel_c[b] <= {{(N-1){1'b0}}, 1'b1} << pick; end   // header next
            end else if (k_v[cur]) begin
                emit_v <= 1'b1;
                if (hdr) begin                                                    // header word
                    hdr <= 1'b0; rem <= cd[491:480];
                    if (cd[491:480] > LMAX) bad <= 1'b1;
                    if (cd[491:480] == 12'd0) begin busy <= 1'b0; rr <= (cur == N - 1) ? 0 : cur + 1'b1; end
                end else begin
                    rem <= rem - 1'b1;
`ifdef S81PH_SVC_MUT_NOATOM
                    if (1'b1) begin busy <= 1'b0;                            // MUTANT: re-arbitrate every word
`else
                    if (rem == 12'd1) begin busy <= 1'b0;
`endif rr <= (cur == N - 1) ? 0 : cur + 1'b1; end
                end
            end
        end
    always @(posedge clk) o_d <= o_dn;
endmodule
