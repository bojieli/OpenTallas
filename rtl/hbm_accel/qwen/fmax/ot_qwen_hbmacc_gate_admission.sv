// Default-off held-request admission candidate. Model: qwen_hbm_registered_admission_model.
// ADMISSION_PIPE=1 changes engine-advance cadence (II=3); the inherited comments
// below describe ADMISSION_PIPE=0 only. No measured timing/adoption claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA8 engine-side stream gating of the Qwen3-8B HBM-accelerator die (fmax closure, 2026-10-04).
// The hardware part of rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv ("HA8: stream gating"), as a module:
//   * 2-flop synchroniser of the window's complete-word count (Gray, HBM domain) -> a_bin
//   * the spine's presented code-word read -> segment (host-written table of NSEG segments) -> w_ready -> me_ok
//   * the stage's KV segment end -> kv_ok
//   * consumed words (furthest HBM word read, less LAGW in flight) -> Gray -> HBM domain; read-outside-segments fault
// (The die's cycle-attribution counters are simulation statistics and stay in the die top.)
//
// OPT = 0: the die top's logic, expression for expression (the reference for the lockstep bench).
// OPT = 1: the same function with zero added cycles, restructured for 1.2 GHz (OPT = 2 adds the registered window count
// described at a_bin: +1 cycle of crossing latency, the only behavioural difference):
//   - the segment table's derived constants (segment end base+len, sidx-base, the kind decodes, the KV end) are
//     registered from a capture stage of the quasi-static host configuration (the host writes the table with the
//     stage start, cycles before any read; the registered copy is exact once the table has been stable 3 cycles);
//   - every segment's match, its idx < a_bin test and its idx + 1 > cmax test are evaluated in parallel (idx =
//     addr + (sidx - base), a registered constant) and the LAST matching segment (the original loop's priority) is
//     selected one-hot on the final booleans, instead of selecting idx through an 8-deep priority chain first;
//   - adders and compares are keep-prefix (ot_hdc_kadd / ot_hdc_kge K=1: ABC re-ripples plain adders in context).
// Both forms give identical me_ok / kv_ok / w_c_gray / hbm_fault on every cycle under that protocol.
// ---------------------------------------------------------------------------
module ot_qwen_hbmacc_gate_admission #(
    parameter integer ADMISSION_PIPE = 0,
    parameter integer OPT  = 0,
    parameter integer NSEG = 8,
    parameter integer LAGW = 40,
    parameter integer CW   = 32,
    parameter integer AW   = 24
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               int8_wrom_re,      // the spine's presented code-word read (registered in the spine)
    input  wire [AW-1:0]      int8_wrom_addr,
    input  wire               me_clk_en,         // this edge clocks the engine
    input  wire [NSEG*24-1:0] seg_base,
    input  wire [NSEG*24-1:0] seg_len,
    input  wire [NSEG*CW-1:0] seg_sidx,
    input  wire [NSEG*2-1:0]  seg_kind,          // 0 unused, 1 HBM code words, 2 SRAM-resident code words, 3 KV (HBM)
    input  wire [CW-1:0]      w_a_gray,          // stream words complete in the window (HBM domain, Gray)
    output wire               me_ok,             // = hb_me_ok of the die top
    output wire               kv_ok,             // = hb_kv_ok
    output reg  [CW-1:0]      w_c_gray,          // stream words consumed (to the HBM domain, Gray)
    output reg                hbm_fault
);
    initial if (ADMISSION_PIPE != 0 && OPT != 3)
        $fatal(1, "ADMISSION_PIPE requires OPT=3 and held-request core binding");
    function automatic [CW-1:0] g2b(input [CW-1:0] g);
        integer i; begin g2b[CW-1] = g[CW-1]; for (i = CW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
    endfunction
    reg  [CW-1:0] a_s1, a_s2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_s1 <= 0; a_s2 <= 0; end else begin a_s1 <= w_a_gray; a_s2 <= a_s1; end
    // Gray -> binary.  OPT 0 and 1: the die's expression on the synchroniser output (OPT 1 as a (* keep *) log-depth
    // suffix XOR: synthesis re-serialised plain reductions into the 31-XOR chain).  OPT 2: the same value REGISTERED
    // (a third stage after the 2-flop synchroniser), so the window count reaches me_ok / kv_ok from a flop: +1 cycle of
    // crossing latency on every arrival the engine waits for (re-measured in the HA8 vehicle).
    wire [CW-1:0] a_dec;
    genvar gb, gl;
    generate if (OPT == 0) begin : g_g2b_ref
        assign a_dec = g2b(a_s2);
    end else begin : g_g2b_tree
        localparam integer GL = $clog2(CW);
        (* keep *) wire [CW-1:0] sx [0:GL];
        assign sx[0] = a_s2;
        for (gl = 1; gl <= GL; gl = gl + 1) begin : g_lv
            for (gb = 0; gb < CW; gb = gb + 1) begin : g_b
                if (gb + (1 << (gl - 1)) < CW) begin : g_x
                    assign sx[gl][gb] = sx[gl-1][gb] ^ sx[gl-1][gb + (1 << (gl - 1))];
                end else begin : g_p
                    assign sx[gl][gb] = sx[gl-1][gb];
                end
            end
        end
        assign a_dec = sx[GL];
    end endgenerate
    wire [CW-1:0] a_bin;
    generate if (OPT >= 2) begin : g_abin_reg
        reg [CW-1:0] a_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) a_r <= 0; else a_r <= a_dec;
        assign a_bin = a_r;
    end else begin : g_abin_wire
        assign a_bin = a_dec;
    end endgenerate
    reg  [CW-1:0] cmax;
    wire [CW-1:0] c_bin = (cmax > CW'(LAGW)) ? cmax - CW'(LAGW) : 0;

    generate if (OPT == 0) begin : g_ref
        reg           hit, hit_res, hit_hbm;
        reg  [CW-1:0] idx;
        reg  [CW-1:0] kv_end;
        integer si;
        always @* begin
            hit = 1'b0; hit_res = 1'b0; hit_hbm = 1'b0; idx = 0; kv_end = 0;
            for (si = 0; si < NSEG; si = si + 1) begin
                if (seg_kind[si*2 +: 2] == 2'd3) kv_end = seg_sidx[si*CW +: CW] + CW'(seg_len[si*24 +: 24]);
                if ((seg_kind[si*2 +: 2] == 2'd1 || seg_kind[si*2 +: 2] == 2'd2) &&
                    int8_wrom_addr >= seg_base[si*24 +: 24] && int8_wrom_addr < seg_base[si*24 +: 24] + seg_len[si*24 +: 24]) begin
                    hit = 1'b1;
                    hit_res = (seg_kind[si*2 +: 2] == 2'd2);
                    hit_hbm = (seg_kind[si*2 +: 2] == 2'd1);
                    idx = seg_sidx[si*CW +: CW] + CW'(int8_wrom_addr - seg_base[si*24 +: 24]);
                end
            end
        end
        wire w_ready = !int8_wrom_re || hit_res || (hit_hbm && idx < a_bin);
        assign me_ok = !rst_n || w_ready;
        assign kv_ok = (kv_end == 0) || (kv_end <= a_bin);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cmax <= 0; w_c_gray <= 0; hbm_fault <= 1'b0; end
            else begin
                if (me_clk_en && int8_wrom_re && hit_hbm && idx + 1 > cmax) cmax <= idx + 1;
                w_c_gray <= c_bin ^ (c_bin >> 1);
                if (int8_wrom_re && !hit) hbm_fault <= 1'b1;
            end
    end else if (OPT <= 2) begin : g_opt
        // registered quasi-static table: a capture stage, then the derived constants, then the KV-end select (the host
        // writes the table with the stage start, cycles before the spine's first read or the first KV op)
        reg  [NSEG*24-1:0] r_base, r_len;
        reg  [NSEG*CW-1:0] r_sidx;
        reg  [NSEG*2-1:0]  r_kind;
        always @(posedge clk) begin r_base <= seg_base; r_len <= seg_len; r_sidx <= seg_sidx; r_kind <= seg_kind; end
        reg  [NSEG-1:0] k_code, k_res, k_hbm, k_kv;
        reg  [24-1:0]   s_base [0:NSEG-1];
        reg  [24-1:0]   s_end  [0:NSEG-1];   // base + len, 24-bit wrap exactly as the reference compare
        reg  [CW-1:0]   s_k0   [0:NSEG-1];   // sidx - base: idx = addr + s_k0 whenever addr >= base
        reg  [CW-1:0]   s_k1   [0:NSEG-1];   // sidx - base + 1: idx + 1
        reg  [CW-1:0]   s_kve  [0:NSEG-1];   // sidx + len (the KV segment's end)
        reg  [CW-1:0]   kv_end;
        reg             kv_none;
        integer si;
        always @(posedge clk) begin
            for (si = 0; si < NSEG; si = si + 1) begin
                k_code[si] <= (r_kind[si*2 +: 2] == 2'd1 || r_kind[si*2 +: 2] == 2'd2);
                k_res[si]  <= (r_kind[si*2 +: 2] == 2'd2);
                k_hbm[si]  <= (r_kind[si*2 +: 2] == 2'd1);
                k_kv[si]   <= (r_kind[si*2 +: 2] == 2'd3);
                s_base[si] <= r_base[si*24 +: 24];
                s_end[si]  <= r_base[si*24 +: 24] + r_len[si*24 +: 24];
                s_k0[si]   <= r_sidx[si*CW +: CW] - CW'(r_base[si*24 +: 24]);
                s_k1[si]   <= r_sidx[si*CW +: CW] - CW'(r_base[si*24 +: 24]) + 1'b1;
                s_kve[si]  <= r_sidx[si*CW +: CW] + CW'(r_len[si*24 +: 24]);
            end
        end
        reg  [CW-1:0]   kv_nx;               // the LAST KV segment's end (the reference loop's priority), else 0
        always @* begin
            kv_nx = 0;
            for (si = 0; si < NSEG; si = si + 1) if (k_kv[si]) kv_nx = s_kve[si];
        end
        always @(posedge clk) begin kv_end <= kv_nx; kv_none <= (kv_nx == 0); end
        // per segment, in parallel, keep-prefix adders/compares (ABC must not re-ripple them in context)
        wire [NSEG-1:0] m;                   // the address is in segment si
        wire [NSEG-1:0] avail;               // its stream word has completed: idx < a_bin
        wire [NSEG-1:0] gt;                  // idx + 1 > cmax
        wire [CW-1:0]   idx1 [0:NSEG-1];     // idx + 1
        wire [CW-1:0]   addr_w = CW'(int8_wrom_addr);
        genvar g;
        for (g = 0; g < NSEG; g = g + 1) begin : g_seg
            wire ge_b, ge_e, ge_a, ge_c, co0, co1;
            wire [CW-1:0] idx;
            ot_hdc_kge  #(.W(24), .K(1)) u_gb (.a(int8_wrom_addr), .b(s_base[g]), .ge(ge_b));
            ot_hdc_kge  #(.W(24), .K(1)) u_ge (.a(int8_wrom_addr), .b(s_end[g]),  .ge(ge_e));
            ot_hdc_kadd #(.W(CW), .K(1)) u_i0 (.a(addr_w), .b(s_k0[g]), .cin(1'b0), .s(idx),     .cout(co0));
            ot_hdc_kadd #(.W(CW), .K(1)) u_i1 (.a(addr_w), .b(s_k1[g]), .cin(1'b0), .s(idx1[g]), .cout(co1));
            ot_hdc_kge  #(.W(CW), .K(1)) u_ga (.a(idx), .b(a_bin), .ge(ge_a));
            ot_hdc_kge  #(.W(CW), .K(1)) u_gc (.a(cmax), .b(idx1[g]), .ge(ge_c));
            assign m[g] = k_code[g] && ge_b && !ge_e;
            assign avail[g] = !ge_a;
            assign gt[g] = !ge_c;
        end
        // the LAST matching segment wins (the reference loop's priority), one-hot
        wire [NSEG-1:0] last;
        for (g = 0; g < NSEG; g = g + 1) begin : g_last
            if (g == NSEG - 1) begin : g_top
                assign last[g] = m[g];
            end else begin : g_lo
                assign last[g] = m[g] && !(|m[NSEG-1:g+1]);
            end
        end
        wire hit     = |m;
        wire ok_seg  = |(last & (k_res | (k_hbm & avail)));
        wire up_seg  = |(last & k_hbm & gt);
        reg  [CW-1:0] cand;                  // idx + 1 of the last matching segment
        integer j;
        always @* begin
            cand = 0;
            for (j = 0; j < NSEG; j = j + 1) cand = cand | ({CW{last[j]}} & idx1[j]);
        end
        wire kv_ge;
        ot_hdc_kge #(.W(CW), .K(1)) u_kv (.a(a_bin), .b(kv_end), .ge(kv_ge));
        assign me_ok = !rst_n || !int8_wrom_re || ok_seg;
        assign kv_ok = kv_none || kv_ge;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cmax <= 0; w_c_gray <= 0; hbm_fault <= 1'b0; end
            else begin
                if (me_clk_en && int8_wrom_re && up_seg) cmax <= cand;
                w_c_gray <= c_bin ^ (c_bin >> 1);
                if (int8_wrom_re && !hit) hbm_fault <= 1'b1;
            end
    end else begin : g_opt3
        // OPT 3 (OPT 2's registered window count, restructured so me_ok is a short compare after the spine's register):
        //  * per segment the first UNAVAILABLE code-word address fa = base + (a_bin - sidx) (0 when a_bin < sidx,
        //    saturated at 2^24) is registered from the decoded window count with a_bin's own latency, so the presented
        //    address only meets compares (segment range, addr < fa).  Exact when a segment's stream indexes do not wrap
        //    2^32 (sidx + len <= 2^32: the plan's indexes are < the token's total stream words);
        //  * the consumed-count update (cmax) is computed from registered copies of the read: cmax and w_c_gray lag
        //    OPT 2's by one cycle (one more cycle of the crossing to the HBM domain).
        //  * table arithmetic keep-prefix.
        reg  [NSEG*24-1:0] r_base, r_len;
        reg  [NSEG*CW-1:0] r_sidx;
        reg  [NSEG*2-1:0]  r_kind;
        always @(posedge clk) begin r_base <= seg_base; r_len <= seg_len; r_sidx <= seg_sidx; r_kind <= seg_kind; end
        reg  [NSEG-1:0] k_code, k_res, k_hbm, k_kv;
        reg  [24-1:0]   s_base [0:NSEG-1];
        reg  [24-1:0]   s_end  [0:NSEG-1];
        reg  [CW-1:0]   s_sidx [0:NSEG-1];
        reg  [CW-1:0]   s_k1   [0:NSEG-1];   // sidx - base + 1
        reg  [CW-1:0]   s_kve  [0:NSEG-1];
        reg  [24:0]     s_fa   [0:NSEG-1];   // first unavailable address (registered with a_bin's latency)
        reg  [CW-1:0]   kv_end;
        reg             kv_none;
        integer si;
        genvar g;
        wire [24-1:0] w_end [0:NSEG-1];
        wire [CW-1:0] w_k1 [0:NSEG-1], w_kve [0:NSEG-1];
        wire [24:0]   w_fa [0:NSEG-1];
        for (g = 0; g < NSEG; g = g + 1) begin : g_tab
            wire [CW-1:0] k0; wire c0, c1, c2, c3, c4, c5;
            ot_hdc_kadd #(.W(24), .K(1)) u_end (.a(r_base[g*24 +: 24]), .b(r_len[g*24 +: 24]), .cin(1'b0), .s(w_end[g]), .cout(c0));
            ot_hdc_kadd #(.W(CW), .K(1)) u_k0 (.a(r_sidx[g*CW +: CW]), .b(~{{(CW-24){1'b0}}, r_base[g*24 +: 24]}), .cin(1'b1), .s(k0), .cout(c1));
            ot_hdc_kinc #(.W(CW), .K(1)) u_k1i (.a(k0), .inc(1'b1), .y(w_k1[g]));
            ot_hdc_kadd #(.W(CW), .K(1)) u_kve (.a(r_sidx[g*CW +: CW]), .b({{(CW-24){1'b0}}, r_len[g*24 +: 24]}), .cin(1'b0), .s(w_kve[g]), .cout(c2));
            // fa from the decoded (not yet registered) window count, so s_fa and a_bin are registered on the same edge
            wire [CW-1:0] diff; wire nb;            // a_dec - sidx; nb = no borrow (a_dec >= sidx)
            ot_hdc_kadd #(.W(CW), .K(1)) u_df (.a(a_dec), .b(~s_sidx[g]), .cin(1'b1), .s(diff), .cout(nb));
            wire [24:0] sum;
            ot_hdc_kadd #(.W(25), .K(1)) u_fs (.a({1'b0, s_base[g]}), .b({1'b0, diff[23:0]}), .cin(1'b0), .s(sum), .cout(c3));
            wire big = (|diff[CW-1:24]) || sum[24];
            assign w_fa[g] = !nb ? 25'd0 : big ? 25'h1000000 : sum;
        end
        always @(posedge clk) begin
            for (si = 0; si < NSEG; si = si + 1) begin
                k_code[si] <= (r_kind[si*2 +: 2] == 2'd1 || r_kind[si*2 +: 2] == 2'd2);
                k_res[si]  <= (r_kind[si*2 +: 2] == 2'd2);
                k_hbm[si]  <= (r_kind[si*2 +: 2] == 2'd1);
                k_kv[si]   <= (r_kind[si*2 +: 2] == 2'd3);
                s_base[si] <= r_base[si*24 +: 24];
                s_end[si]  <= w_end[si];
                s_sidx[si] <= r_sidx[si*CW +: CW];
                s_k1[si]   <= w_k1[si];
                s_kve[si]  <= w_kve[si];
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) for (si = 0; si < NSEG; si = si + 1) s_fa[si] <= 0;
            else for (si = 0; si < NSEG; si = si + 1) s_fa[si] <= w_fa[si];
        reg  [CW-1:0]   kv_nx;
        always @* begin
            kv_nx = 0;
            for (si = 0; si < NSEG; si = si + 1) if (k_kv[si]) kv_nx = s_kve[si];
        end
        always @(posedge clk) begin kv_end <= kv_nx; kv_none <= (kv_nx == 0); end
        // the presented read: compares only
        wire [NSEG-1:0] m, avail;
        for (g = 0; g < NSEG; g = g + 1) begin : g_seg
            wire ge_b, ge_e, ge_f;
            ot_hdc_kge #(.W(24), .K(1)) u_gb (.a(int8_wrom_addr), .b(s_base[g]), .ge(ge_b));
            ot_hdc_kge #(.W(24), .K(1)) u_ge (.a(int8_wrom_addr), .b(s_end[g]),  .ge(ge_e));
            ot_hdc_kge #(.W(25), .K(1)) u_gf (.a({1'b0, int8_wrom_addr}), .b(s_fa[g]), .ge(ge_f));
            assign m[g] = k_code[g] && ge_b && !ge_e;
            assign avail[g] = !ge_f;
        end
        wire [NSEG-1:0] last;
        for (g = 0; g < NSEG; g = g + 1) begin : g_last
            if (g == NSEG - 1) begin : g_top
                assign last[g] = m[g];
            end else begin : g_lo
                assign last[g] = m[g] && !(|m[NSEG-1:g+1]);
            end
        end
        wire hit    = |m;
        wire ok_seg = |(last & (k_res | (k_hbm & avail)));
        wire kv_ge;
        ot_hdc_kge #(.W(CW), .K(1)) u_kv (.a(a_bin), .b(kv_end), .ge(kv_ge));
        if (ADMISSION_PIPE == 0) begin : g_direct_admission
            assign me_ok = !rst_n || !int8_wrom_re || ok_seg;
        end else begin : g_registered_admission
            // The spine holds its request while its clock is stopped. SAMPLE
            // binds both vectors to that request; GRANT is valid for one edge.
            // Never re-use the old permission after the engine changes address.
            reg [NSEG-1:0] held_match, held_avail;
            reg held_no_read, grant;
            reg [1:0] phase;
            wire [NSEG-1:0] held_last;
            for (genvar q = 0; q < NSEG; q = q + 1) begin : g_priority
                if (q == NSEG-1) assign held_last[q] = held_match[q];
                else assign held_last[q] = held_match[q] && !(|held_match[NSEG-1:q+1]);
            end
            wire held_ok = held_no_read ||
                |(held_last & (k_res | (k_hbm & held_avail)));
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    phase <= 0; grant <= 0; held_match <= 0;
                    held_avail <= 0; held_no_read <= 0;
                end else begin
                    grant <= 0;
                    case (phase)
                        0: begin
                            held_match <= m; held_avail <= avail;
                            held_no_read <= !int8_wrom_re; phase <= 1;
                        end
                        1: begin
                            grant <= held_ok;
                            phase <= held_ok ? 2 : 0;
                        end
                        2: phase <= 0;
                        default: phase <= 0;
                    endcase
                end
            end
            assign me_ok = !rst_n || grant;
        end

        assign kv_ok = kv_none || kv_ge;
        // consumed count, one cycle behind: registered read, then idx + 1 > cmax
        reg              u_v;
        reg  [NSEG-1:0]  u_last;
        reg  [24-1:0]    u_addr;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin u_v <= 1'b0; u_last <= 0; u_addr <= 0; end
            else begin u_v <= me_clk_en && int8_wrom_re && |(last & k_hbm); u_last <= last & k_hbm; u_addr <= int8_wrom_addr; end
        wire [CW-1:0] idx1 [0:NSEG-1];
        for (g = 0; g < NSEG; g = g + 1) begin : g_c
            wire co;
            ot_hdc_kadd #(.W(CW), .K(1)) u_i1 (.a({{(CW-24){1'b0}}, u_addr}), .b(s_k1[g]), .cin(1'b0), .s(idx1[g]), .cout(co));
        end
        reg  [CW-1:0] cand;
        integer j;
        always @* begin
            cand = 0;
            for (j = 0; j < NSEG; j = j + 1) cand = cand | ({CW{u_last[j]}} & idx1[j]);
        end
        wire ge_cm;
        ot_hdc_kge #(.W(CW), .K(1)) u_cm (.a(cmax), .b(cand), .ge(ge_cm));
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cmax <= 0; w_c_gray <= 0; hbm_fault <= 1'b0; end
            else begin
                if (u_v && !ge_cm) cmax <= cand;
                w_c_gray <= c_bin ^ (c_bin >> 1);
                if (int8_wrom_re && !hit) hbm_fault <= 1'b1;
            end
    end endgenerate
endmodule
