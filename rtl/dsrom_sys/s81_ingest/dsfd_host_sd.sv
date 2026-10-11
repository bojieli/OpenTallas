`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_host_sd (s81-svceng-1011 host side, 2026-10-11): per-stack decode of the S81 host block's ONE die-face sector
// stream (dsfd_host o_v / o_we / o_addr 32 / o_d 256; the host holds OCRED = 8 credits, o_cr returns one a pulse)
// into one host-write port per HBM stack client (svc_<st> / eng_SE): hw<s> / hc<s>.
//   class   marker (o_addr == 32'hffffffff): o_d[65:64] 3 Engram, 2 RoPE, other = fault;
//           else o_addr[31] = 0 KV, o_addr[31:30] = 2'b10 RoPE, 2'b11 Engram.  o_we = 0 (an RMW read; the DS dies run
//           RMW_EN 0) = fault.
//   route   KV sector -> the k-th KV stack (set bits of KVS, ascending), k = (o_addr >> 5) mod #KV stacks;
//           RoPE sector -> the first KV stack; RoPE marker -> every KV stack; Engram sector / marker -> stack ENG only
//           (ENG < 0: Engram class is a fault).  A faulting word is dropped (its credit returned) and fault is sticky.
//   flow    registered input pins -> 8-entry FIFO (the host's 8 credits; o_cr pulses on every pop) -> one word a cycle
//           in order to its stack(s), only against that stack's credits (SCRED, hc cr returns one); a multicast marker
//           waits for a credit in every destination.
//   hw<s>   = {cls 2 (0 KV, 1 RoPE, 2 Engram), we, addr 32, d 256, v} (292 b) from flops (markers keep addr ffffffff and
//           d; Engram aperture CSR words are Engram markers with d[255] = 1);  hc<s> = {ack 8, cr} (9 b) into pin flops: ack = host
//           sector physical write completions of the cycle (count), summed into host_ack_n (registered; > 255 = fault)
//           for the host's visibility fence (dsfd_host_native ack_n).
// MUT (negative controls): 1 KV stack from o_addr >> 6, 2 every 50th stack credit return dropped, 3 Engram -> stack 0.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_host_sd #(
    parameter integer NS = 2,
    parameter integer KVS = 1,          // bit s: stack s holds KV / RoPE
    parameter integer ENG = 1,          // Engram client stack (-1: none)
    parameter integer SCRED = 8,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire              o_v,
    input  wire              o_we,
    input  wire [31:0]       o_addr,
    input  wire [255:0]      o_d,
    output reg               o_cr,
    output reg  [292*NS-1:0] hw,
    input  wire [9*NS-1:0]   hc,
    output reg  [7:0]        host_ack_n,
    output reg               fault
);
    // ---- reset: the port drives only the relay (design standard); release 3 cycles after the port
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rn));
    // ---- pin flops
    reg iv; reg iwe; reg [31:0] ia; reg [255:0] id; reg [9*NS-1:0] hc_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin iv <= 1'b0; hc_q <= {9*NS{1'b0}}; end
        else begin iv <= o_v; hc_q <= hc; end
    always @(posedge ck) begin iwe <= o_we; ia <= o_addr; id <= o_d; end
    // ---- FIFO
    reg [288:0] f [0:7]; reg [2:0] wp, rp; reg [3:0] n;
    wire [288:0] h = f[rp];
    wire hwe = h[288]; wire [31:0] ha = h[287:256]; wire [255:0] hd = h[255:0];
    // ---- KV stack list
    function automatic integer nkv(input integer m); integer i, c; begin c = 0; for (i = 0; i < NS; i = i + 1) if (m[i]) c = c + 1; nkv = c; end endfunction
    function automatic integer kth(input integer m, input integer k); integer i, c; begin kth = 0; c = 0;
        for (i = 0; i < NS; i = i + 1) if (m[i]) begin if (c == k) kth = i; c = c + 1; end end endfunction
    function automatic integer first(input integer m); integer i; begin first = 0; for (i = NS - 1; i >= 0; i = i - 1) if (m[i]) first = i; end endfunction
    localparam integer NKV = nkv(KVS);
    localparam integer KV0 = first(KVS);
    // ---- head decode
    wire marker = (ha == 32'hffffffff);
    reg [1:0] cls; reg bad; reg [NS-1:0] dst; integer s;
    wire [31:0] kidx = (MUT == 1) ? (ha >> 6) : (ha >> 5);
    integer kk;
    always @* begin
        bad = 1'b0; cls = 2'd0; dst = {NS{1'b0}};
        if (marker) begin
            if (hd[65:64] == 2'd3) cls = 2'd3; else if (hd[65:64] == 2'd2) cls = 2'd2; else bad = 1'b1;
        end else cls = ha[31] ? (ha[30] ? 2'd3 : 2'd2) : 2'd0;
        if (!hwe) bad = 1'b1;
        if (cls == 2'd3) begin
            if (ENG < 0 || ENG >= NS) bad = 1'b1;
            else dst[(MUT == 3) ? 0 : ENG] = 1'b1;
        end else if (NKV == 0) bad = 1'b1;
        else if (cls == 2'd2) begin
            if (marker) dst = KVS[NS-1:0]; else dst[KV0] = 1'b1;
        end else begin
            kk = kidx % NKV;
            dst[kth(KVS, kk)] = 1'b1;
        end
        if (bad) dst = {NS{1'b0}};
    end
    // ---- per-stack credits
    reg [4:0] cr [0:NS-1]; reg [6:0] crn;
    reg ok;
    always @* begin ok = 1'b1; for (s = 0; s < NS; s = s + 1) if (dst[s] && cr[s] == 0) ok = 1'b0; end
    wire pop = (n != 0) && (bad || ok);
    reg [8:0] asum;
    always @* begin asum = 9'd0; for (s = 0; s < NS; s = s + 1) asum = asum + hc_q[9*s + 1 +: 8]; end
    always @(posedge ck or negedge rn)
        if (!rn) begin
            wp <= 0; rp <= 0; n <= 0; o_cr <= 1'b0; fault <= 1'b0; host_ack_n <= 8'd0; crn <= 0;
            for (s = 0; s < NS; s = s + 1) begin cr[s] <= SCRED[4:0]; hw[292*s] <= 1'b0; end
        end else begin
            if (iv) begin f[wp] <= {iwe, ia, id}; wp <= wp + 1'b1; if (n == 8 && !pop) fault <= 1'b1; end
            if (pop) rp <= rp + 1'b1;
            n <= n + iv - pop;
            o_cr <= pop;
            if (pop && bad) fault <= 1'b1;
            for (s = 0; s < NS; s = s + 1) begin
                hw[292*s] <= pop && dst[s];
                cr[s] <= cr[s] - (pop && dst[s]) + (hc_q[9*s] && !(MUT == 2 && crn == 49 && s == 0));
                if (cr[s] - (pop && dst[s]) + hc_q[9*s] > SCRED) fault <= 1'b1;
            end
            if (hc_q[0]) crn <= (crn == 49) ? 0 : crn + 1'b1;
            host_ack_n <= asum[8] ? 8'hff : asum[7:0];
            if (asum[8]) fault <= 1'b1;
        end
    always @(posedge ck)
        for (s = 0; s < NS; s = s + 1) if (pop && dst[s]) hw[292*s + 1 +: 291] <= {(cls == 2'd3) ? 2'd2 : ((cls == 2'd2) ? 2'd1 : 2'd0), hwe, ha, hd};
endmodule

