`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX wide adapter, TILED form (ot_hgi_idx_index_wt): LANE leaf, one 4-lane read group (hardened once,
// instantiated twice; it does not know its group index: the request carries sector[14:2], the lane number is local).
// SPEC results/arch/hbm_b2_idx_ixw1_1013/SPEC.md "Tiled redesign".
//   * P2 face: wrr pin capture 4 x 257, wrq launch 4 x 16, lane credits, read-group grant.
//   * local chunk log (LGD entries {slot, count, sector[14:2]}): a descriptor from QCORE is queued, ISSUED when every
//     lane of the chunk has a VM credit (LQ) and a landing reservation (DL), reported READY (one pulse a chunk, log
//     order) when every sector of it has landed, and POPPED by QCORE (one pulse a chunk, log order; QCORE pops only
//     chunks reported ready and only once the consumer slot is reserved, so the beat is never stalled).
//   * landing memory DL x 256 a lane (flops), write / read pointers as registered copies, one a 64-bit slice.
//   * registered 1,024-bit chunk beat (lane l at bits l*256), valid one cycle after the pop lands.
// Every input lands in a flop, every output leaves a flop; only control flops are reset.
// MUT 12 (bench): the read pointer copy of lane 1 slice 2 starts one entry off (must FAIL).
module ot_hgi_idxw_lane #(
    parameter integer MUT = 0,
    parameter integer DL  = 4,      // landing depth a lane (power of 2)
    parameter integer LQ  = 8,      // VM lane queue credits a lane
    parameter integer LGD = 8       // local chunk log depth (power of 2; QCORE sends at most LGD un-popped descriptors)
) (
    input  wire              clk,
    input  wire              rst_n,
    // P2: VM wide read lanes of this group
    input  wire [4*257-1:0]  wrr_i,
    output wire [4*16-1:0]   wrq_o,
    input  wire [3:0]        wrq_cr_i,
    input  wire              gnt_i,
    // S1: QCORE
    input  wire [18:0]       dsc_i,     // {v, slot[1:0], count[2:0], sector[14:2]}
    input  wire              pop_i,
    output wire [1023:0]     ob_o,
    output reg               ob_v_o,
    output reg               rdy_o
);
    localparam integer DLB = $clog2(DL), CB = $clog2(LQ) + 1, LGB = $clog2(LGD);
    integer l;
    genvar gl, gc, ge, gr;
    // ---- reset: 2-flop synchroniser, one output copy a control group
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    wire [2:0] rnc;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rn
        reg r;
        (* keep = "true" *) always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rn;
        assign rnc[gr] = r;
    end endgenerate
    // ---- pin flops
    reg [3:0] rr_v, rcr_q; reg gnt_q, d_v, pop_q;
    reg [1:0] d_slot; reg [2:0] d_cnt; reg [12:0] d_shi; reg [1023:0] rr_d;
    always @(posedge clk or negedge rnc[0])
        if (!rnc[0]) begin rr_v <= 4'd0; rcr_q <= 4'd0; gnt_q <= 1'b0; d_v <= 1'b0; pop_q <= 1'b0; end
        else begin
            rcr_q <= wrq_cr_i; gnt_q <= gnt_i; d_v <= dsc_i[18]; pop_q <= pop_i;
            for (l = 0; l < 4; l = l + 1) rr_v[l] <= wrr_i[l*257 + 256];
        end
    always @(posedge clk) begin
        d_slot <= dsc_i[17:16]; d_cnt <= dsc_i[15:13]; d_shi <= dsc_i[12:0];
        for (l = 0; l < 4; l = l + 1) rr_d[l*256 +: 256] <= wrr_i[l*257 +: 256];
    end
    // ---- chunk log and its four pointers (write, issue, ready scan, pop)
    reg [17:0] lg [0:LGD-1];
    reg [LGB:0] wp, ip, sp, hp;
    wire [17:0] e_i = lg[ip[LGB-1:0]], e_s = lg[sp[LGB-1:0]], e_h = lg[hp[LGB-1:0]];
    function automatic [3:0] mk(input [1:0] slot, input [2:0] cnt);
        integer x;
        begin
            mk = 4'd0;
            for (x = 0; x < 4; x = x + 1) if (x >= {30'd0, slot} && x < {30'd0, slot} + {29'd0, cnt}) mk[x] = 1'b1;
        end
    endfunction
    wire [3:0] m_i = mk(e_i[17:16], e_i[15:13]), m_s = mk(e_s[17:16], e_s[15:13]), m_h = mk(e_h[17:16], e_h[15:13]);
    reg [CB-1:0] rcred [0:3];       // VM lane credits
    reg [DLB:0]  rres  [0:3];       // landing slots reserved (issued, not yet popped)
    reg [DLB:0]  lav   [0:3];       // landed, not yet claimed by a ready chunk
    reg i_ok, s_ok;
    reg [3:0] wq_v; reg [59:0] wq_d;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_wq
        assign wrq_o[gl*16 +: 16] = {wq_v[gl], wq_d[gl*15 +: 15]};
    end endgenerate
    always @* begin
        i_ok = 1'b1; s_ok = 1'b1;
        for (l = 0; l < 4; l = l + 1) begin
            if (m_i[l] && (rcred[l] == '0 || rres[l] == (DLB+1)'(DL))) i_ok = 1'b0;
            if (m_s[l] && lav[l] == '0 && !rr_v[l]) s_ok = 1'b0;
        end
    end
    wire i_go = ip != wp && gnt_q && i_ok;
    wire s_go = sp != ip && s_ok;
    wire [3:0] popm = pop_q ? m_h : 4'd0;
    always @(posedge clk) if (d_v) lg[wp[LGB-1:0]] <= {d_slot, d_cnt, d_shi};
    always @(posedge clk) begin
        if (!rnc[1]) begin
            wp <= '0; ip <= '0; sp <= '0; hp <= '0; ob_v_o <= 1'b0; rdy_o <= 1'b0;
            for (l = 0; l < 4; l = l + 1) begin
                rcred[l] <= CB'(LQ); rres[l] <= '0; lav[l] <= '0; wq_v[l] <= 1'b0;
            end
        end else begin
            rdy_o <= s_go; ob_v_o <= pop_q;
            if (d_v) wp <= wp + 1'b1;
            if (i_go) ip <= ip + 1'b1;
            if (s_go) sp <= sp + 1'b1;
            if (pop_q) hp <= hp + 1'b1;
            for (l = 0; l < 4; l = l + 1) begin
                wq_v[l] <= i_go && m_i[l];
                rcred[l] <= rcred[l] + CB'(rcr_q[l]) - CB'(i_go && m_i[l]);
                rres[l] <= rres[l] + (DLB+1)'(i_go && m_i[l]) - (DLB+1)'(popm[l]);
                lav[l] <= lav[l] + (DLB+1)'(rr_v[l]) - (DLB+1)'(s_go && m_s[l]);
            end
        end
    end
    // request payload (free-running; valid only with the lane's v bit)
    always @(posedge clk) for (l = 0; l < 4; l = l + 1) wq_d[l*15 +: 15] <= {e_i[12:0], 2'(l)};
    // ---- landing memory: one write and one read pointer copy a 64-bit slice; the beat register loads the landing
    //      heads every cycle (the pop only advances the pointers)
    wire [4*DL*256-1:0] lmf;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_l
        for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
            reg [DLB-1:0] wpc, rpc;
            (* keep = "true" *) always @(posedge clk)
                if (!rnc[2]) wpc <= '0; else if (rr_v[gl]) wpc <= wpc + 1'b1;
            (* keep = "true" *) always @(posedge clk)
                if (!rnc[2]) rpc <= (MUT == 12 && gl == 1 && gc == 2) ? DLB'(1) : '0; else if (popm[gl]) rpc <= rpc + 1'b1;
            for (ge = 0; ge < DL; ge = ge + 1) begin : g_e
                reg [63:0] m;
                always @(posedge clk) if (rr_v[gl] && wpc == DLB'(ge)) m <= rr_d[gl*256 + gc*64 +: 64];
                assign lmf[(gl*DL + ge)*256 + gc*64 +: 64] = m;
            end
            reg [63:0] rv, o; integer e;
            always @* begin
                rv = 64'd0;
                for (e = 0; e < DL; e = e + 1) if (rpc == DLB'(e)) rv = rv | lmf[(gl*DL + e)*256 + gc*64 +: 64];
            end
            always @(posedge clk) o <= rv;
            assign ob_o[gl*256 + gc*64 +: 64] = o;
        end
    end endgenerate
endmodule
`default_nettype wire
