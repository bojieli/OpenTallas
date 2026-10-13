`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_stack: ot_gpu_stack (rtl/gpu/ot_gpu_stack.sv) with every level's pending-partial lookup taken off the
// adder's first stage, for 1.2 GHz SS.  Same pairing, order, results and fault as the original, one cycle later.
//
// In ot_gpu_stack a level reads its pending slot (pend_v / seen / pend_d [slot]) with the arriving slot number and
// feeds the selected partial straight into the FP32 adder's decode / compare stage.  Here each level looks one cycle
// ahead: the slot of the item arriving next cycle is known a cycle early (level 0: the stack's input, now registered
// once; level l >= 1: the previous level's valid / slot delay lines one tap early), so `have`, `seen` and the adder's
// pending operand are registered from that slot's NEXT state (forwarding this cycle's own update of the same slot).
// The level's decisions then use registered values only.
// Cycles: +1 per row result (the input register), independent of the levels a row climbs.
// ---------------------------------------------------------------------------
module ot_hbm_accel_stack #(
    parameter integer LEV  = 5,
    parameter integer IL   = 8,
    parameter integer TAGW = 8,
    parameter integer ALAT = 7
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,
    input  wire [31:0]       d,
    input  wire              ilast,
    input  wire [$clog2(IL)-1:0] islot,
    input  wire [TAGW-1:0]   itag,
    output reg               ov,
    output reg  [31:0]       y,
    output reg  [TAGW-1:0]   otag,
    output reg               fault
);
    localparam integer SW = $clog2(IL);
    localparam integer MW = SW + TAGW + 1;          // meta: last, slot, tag
    // ---- the stack's input register (level 0's look-ahead tap is the unregistered input) ----
    reg              iv_q, ilast_q;
    reg [31:0]       d_q;
    reg [SW-1:0]     islot_q;
    reg [TAGW-1:0]   itag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) iv_q <= 1'b0;
        else iv_q <= iv;
    always @(posedge clk) begin d_q <= d; ilast_q <= ilast; islot_q <= islot; itag_q <= itag; end
    wire [LEV:0]          lv_v, lv_ev;              // valid now / valid next cycle
    wire [LEV:0]          lv_last;
    wire [32*(LEV+1)-1:0] lv_d;
    wire [SW*(LEV+1)-1:0] lv_slot, lv_eslot;        // slot now / slot next cycle
    wire [TAGW*(LEV+1)-1:0] lv_tag;
    wire [LEV:0]          ret_v;
    wire [32*(LEV+1)-1:0] ret_d;
    wire [TAGW*(LEV+1)-1:0] ret_tag;
    wire [LEV:0]          lf;
    assign lv_v[0] = iv_q;
    assign lv_ev[0] = iv;
    assign lv_last[0] = ilast_q;
    assign lv_d[31:0] = d_q;
    assign lv_slot[SW-1:0] = islot_q;
    assign lv_eslot[SW-1:0] = islot;
    assign lv_tag[TAGW-1:0] = itag_q;
    genvar l;
    generate
        for (l = 0; l < LEV; l = l + 1) begin : g_lv
            reg [IL-1:0]  pend_v, seen;
            reg [31:0]    pend_d [0:IL-1];
            wire          v_in = lv_v[l];
            wire          last_in = lv_last[l];
            wire [31:0]   d_in = lv_d[32*l +: 32];
            wire [SW-1:0] s_in = lv_slot[SW*l +: SW];
            wire [SW-1:0] es = lv_eslot[SW*l +: SW];
            wire [TAGW-1:0] t_in = lv_tag[TAGW*l +: TAGW];
            // registered look-ahead of slot s_in's state (valid whenever v_in)
            reg           have_q, seen_q;
            reg  [31:0]   opa_q;
            wire          have = have_q;
            wire          lone = v_in && last_in && !have && !seen_q;
            wire          go   = v_in && !lone && (have || last_in);
            wire          wr   = v_in && !last_in && !have;          // this cycle parks d_in in slot s_in
            wire          upd  = v_in && (s_in == es);
            wire          n_pend = upd ? wr : pend_v[es];
            wire          n_seen = upd ? !last_in : seen[es];
            wire [31:0]   n_d    = (upd && wr) ? d_in : pend_d[es];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    pend_v <= {IL{1'b0}};
                    seen <= {IL{1'b0}};
                    have_q <= 1'b0;
                    seen_q <= 1'b0;
                end else begin
                    have_q <= n_pend;
                    seen_q <= n_seen;
                    if (v_in) begin
                        if (last_in) begin
                            pend_v[s_in] <= 1'b0;
                            seen[s_in] <= 1'b0;
                        end else if (have) begin
                            pend_v[s_in] <= 1'b0;
                            seen[s_in] <= 1'b1;
                        end else begin
                            pend_v[s_in] <= 1'b1;
                            seen[s_in] <= 1'b1;
                        end
                    end
                end
            end
            always @(posedge clk) begin
                opa_q <= n_pend ? n_d : 32'd0;
                if (wr) pend_d[s_in] <= d_in;
            end
            wire [31:0] sum;
            ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(go), .a(opa_q), .b(d_in), .y(sum), .fault(lf[l]));
            wire [ALAT:0] gv;
            ot_hdc_vline #(.D(ALAT)) u_gv (.clk(clk), .rst_n(rst_n), .v(go), .vd(gv));
            // meta delay line with every tap (the next level's look-ahead reads tap ALAT - 1)
            reg [MW-1:0] meta [1:ALAT];
            integer k;
            always @(posedge clk) begin
                meta[1] <= {last_in, s_in, t_in};
                for (k = 2; k <= ALAT; k = k + 1) meta[k] <= meta[k-1];
            end
            wire [MW-1:0] meta_q = meta[ALAT];
            wire [MW-1:0] meta_e = (ALAT >= 2) ? meta[ALAT-1] : {last_in, s_in, t_in};
            assign lv_v[l+1] = gv[ALAT];
            assign lv_ev[l+1] = gv[ALAT-1];
            assign lv_last[l+1] = meta_q[SW+TAGW];
            assign lv_slot[SW*(l+1) +: SW] = meta_q[SW+TAGW-1:TAGW];
            assign lv_eslot[SW*(l+1) +: SW] = meta_e[SW+TAGW-1:TAGW];
            assign lv_tag[TAGW*(l+1) +: TAGW] = meta_q[TAGW-1:0];
            assign lv_d[32*(l+1) +: 32] = sum;
            assign ret_v[l] = lone;
            assign ret_d[32*l +: 32] = d_in;
            assign ret_tag[TAGW*l +: TAGW] = t_in;
        end
    endgenerate
    assign ret_v[LEV] = lv_v[LEV];
    assign ret_d[32*LEV +: 32] = lv_d[32*LEV +: 32];
    assign ret_tag[TAGW*LEV +: TAGW] = lv_tag[TAGW*LEV +: TAGW];
    assign lf[LEV] = 1'b0;
    integer kk, nret;
    reg [31:0] y_n;
    reg [TAGW-1:0] t_n;
    always @* begin
        nret = 0; y_n = 32'd0; t_n = {TAGW{1'b0}};
        for (kk = 0; kk <= LEV; kk = kk + 1)
            if (ret_v[kk]) begin
                nret = nret + 1;
                y_n = ret_d[32*kk +: 32];
                t_n = ret_tag[TAGW*kk +: TAGW];
            end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov <= 1'b0; y <= 32'd0; otag <= {TAGW{1'b0}}; fault <= 1'b0;
        end else begin
            ov <= |ret_v;
            y <= y_n;
            otag <= t_n;
            fault <= fault | (|lf) | (nret > 1);
        end
    end
endmodule
