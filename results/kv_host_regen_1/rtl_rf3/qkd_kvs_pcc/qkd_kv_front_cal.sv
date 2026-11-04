`timescale 1ns/1ps
// Q-VMWB 2026-10-16: HBM-side KV calendar leaf (one per landing group, 32 per KV die, ONE master), beside the group's
// four PC elastic fronts (qkd_kv_hbm_elastic_front) at the PHY side, pll_hbm only.
//
// Drives the fronts' blk_go: the release slot of each 8-sector front block, the only compiled input of the elastic
// HBM boundary (owner 0az).  A pass start (kgo_h / vgo_h, already in the HBM domain through the die's fixed compiled
// core -> HBM crossing; the edge that captures it is A) releases block b at HBM edge A + G0 + off(8 b): G0 = H0 - 3
// (front: first put 3 edges after blk_go; H0 = the landing calendar's A -> first put), off(i) = i up to the pass's
// ring-pacing index P0, then GAP more edges before every further block (kv_calendar pc_schedule / pc_schedule_paced:
// identical for every PC, a prefix at any T).  Blocks = ceil(n / 8), n = the group's rows < T (the same closed forms
// as qkd_kv_landing_cal).  All four PCs of the group get the same blk_go.  Fixed function of the pass starts, T and
// the boot constants; no data, readiness or credit input (the front's own hold / fault are its boundary).
// Boot constants (cfg_we / cfg_addr / cfg_data): 0: {stack[1:0], group[2:0]}  2: G0[7:0]  4: K {GAP, P0}  5: V {GAP, P0}
// (the same addresses as qkd_kv_landing_cal; 1 / 3 unused here).  MUT (bench): 1 = blocks = floor(n / 8) (a partial last block never released),
// 2 = pacing gap ignored.
module qkd_kv_front_cal #(parameter integer MUT = 0) (
    input wire hck, rst_n,
    input wire cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    input wire kgo_h, input wire vgo_h, input wire [13:0] ctx_t,
    output reg [3:0] blk_go,
    output reg fault
);
    (* keep *) reg rn;
    always @(posedge hck) rn <= rst_n;
    reg kgo_q, vgo_q, we_q; reg [7:0] ad_q; reg [63:0] cd_q; reg [13:0] ctx_q;
    always @(posedge hck or negedge rn)
        if (!rn) begin kgo_q <= 1'b0; vgo_q <= 1'b0; we_q <= 1'b0; end
        else begin kgo_q <= kgo_h; vgo_q <= vgo_h; we_q <= cfg_we; end
    always @(posedge hck) begin ad_q <= cfg_addr; cd_q <= cfg_data; ctx_q <= ctx_t; end
    reg [1:0] s_c; reg [2:0] e_c; reg [7:0] g0_c; reg [3:0] kg_c, vg_c; reg [8:0] kp_c, vp_c;
    always @(posedge hck or negedge rn)
        if (!rn) begin s_c <= 0; e_c <= 0; g0_c <= 0; kg_c <= 0; vg_c <= 0; kp_c <= 9'h1ff; vp_c <= 9'h1ff; end
        else if (we_q) case (ad_q)
            8'd0: begin s_c <= cd_q[4:3]; e_c <= cd_q[2:0]; end
            8'd2: g0_c <= cd_q[7:0] - 8'd3;
            8'd4: begin kp_c <= cd_q[8:0]; kg_c <= cd_q[12:9]; end
            8'd5: begin vp_c <= cd_q[8:0]; vg_c <= cd_q[12:9]; end
            default: ;
        endcase
    // ---- closed-form stream lengths (the same as qkd_kv_landing_cal) ----
    reg [13:0] t_l;
    wire signed [15:0] xk = $signed({2'b0, (kgo_q ? ctx_q : t_l)}) - $signed({7'b0, s_c, 7'b0}) - $signed({13'b0, e_c});
    wire signed [15:0] xv = $signed({2'b0, t_l}) - $signed({7'b0, s_c, 7'b0}) - $signed({10'b0, e_c[2:1], 4'b0}) - $signed({15'b0, e_c[0]});
    function automatic [8:0] cnt(input signed [15:0] x, input integer sh);
        reg [8:0] r; reg [3:0] c0, c1; reg [9:0] h0, h1;
        begin
            r = x[8:0];
            h0 = ({1'b0, r} + 10'((1 << sh) - 1)) >> sh; h1 = (r > 9'd64) ? ({1'b0, r} - 10'd64 + 10'((1 << sh) - 1)) >> sh : 10'd0;
            c0 = (h0 >= 8) ? 4'd8 : 4'(h0); c1 = (h1 >= 8) ? 4'd8 : 4'(h1);
            cnt = (x <= 0) ? 9'd0 : (x[15:9] >= 7'd16) ? 9'd256 : {x[12:9], 4'b0} + {5'b0, c0} + {5'b0, c1};
        end
    endfunction
    // ---- block releases ----
    reg act, vpass; reg [5:0] b, nb; reg [8:0] w;     // w = HBM edges until block b's release
    wire [8:0] pp = vpass ? vp_c : kp_c; wire [3:0] pg = vpass ? vg_c : kg_c;
    wire [8:0] i1 = {b + 6'd1, 3'b0};                  // first sector of the next block
    wire pace = (MUT != 2) && (i1 >= pp);
    wire start = kgo_q | vgo_q;
    wire [8:0] nk = cnt(xk, 3), nv = cnt(xv, 1);
    wire [8:0] rnd = (MUT == 1) ? 9'd0 : 9'd7;          // MUT 1: blocks = floor(n / 8)
    wire rel = act && (w == 9'd0);
    always @(posedge hck or negedge rn)
        if (!rn) begin act <= 0; vpass <= 0; b <= 0; nb <= 0; w <= 0; t_l <= 0; fault <= 0; blk_go <= 0; end
        else begin
            blk_go <= {4{rel}};
            if (start) begin
                if (act) fault <= 1'b1;
                if (kgo_q && vgo_q) fault <= 1'b1;
                if (kgo_q) t_l <= ctx_q;
                vpass <= vgo_q; b <= 0;
                nb <= kgo_q ? 6'((nk + rnd) >> 3) : 6'((nv + rnd) >> 3);
                act <= kgo_q ? (nk != 0) : (nv != 0);
                w <= {1'b0, g0_c} - 9'd1;               // released on edge A + G0 (A = this capture edge)
            end else if (act) begin
                if (rel) begin
                    b <= b + 6'd1; w <= 9'd7 + (pace ? {5'b0, pg} : 9'd0);
                    if (b + 6'd1 == nb) act <= 1'b0;
                end else w <= w - 9'd1;
            end
        end
endmodule
