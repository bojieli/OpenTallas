`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Streaming pairwise FP32 reducer behind a tensor-core column's lane tree.
//
// A row's K is cut into G groups of L golden chunks; the lane tree turns each
// group into one partial, and the partials of a row arrive here IN GROUP
// ORDER, interleaved with the other rows (slots) the column holds in flight.
// The golden continues the same pairwise tree over the G partials, padded
// with +0 to a power of two (tools/hdc_golden.py matvec, hdc_golden_v41.csum).
//
// Each level keeps, per slot, one pending partial and a `seen` bit:
//   - a non-final partial with nothing pending is held;
//   - a partial meeting a pending one is added to it (one adder per level,
//     LATENCY 5) and the sum goes up a level;
//   - the row's final partial (`last`) meeting nothing pending goes up as
//     x + (+0) -- the golden's +0 pad, exact through the adder's zero bypass
//     -- unless it is the only partial the row ever had at this level: then
//     it IS the row's result and leaves on `ov` from this level.
// Because the row's items enter every level in order through one pipelined
// adder, item order and pairing match the golden tree exactly; a row whose G
// is 1 leaves with no added latency.  At most one item arrives per cycle, so
// one adder per level suffices.  Rows of one op share G and therefore retire
// from the same level; `fault` also flags two levels retiring in one cycle
// (the issue must drain between ops of different G).
// ---------------------------------------------------------------------------
module ot_gpu_stack #(
    parameter integer LEV  = 5,     // levels: G <= 2^LEV groups per row
    parameter integer IL   = 8,     // slots (rows in flight)
    parameter integer TAGW = 8,     // tag travelling with the result (row id)
    parameter integer ALAT = 8      // adder latency (ot_gpu_fadd)
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
    // per-level input bus (level 0 = the lane tree output)
    wire [LEV:0]       lv_v;
    wire [LEV:0]       lv_last;
    wire [32*(LEV+1)-1:0] lv_d;
    wire [SW*(LEV+1)-1:0] lv_slot;
    wire [TAGW*(LEV+1)-1:0] lv_tag;
    wire [LEV:0]       ret_v;          // a level retiring a row result this cycle
    wire [32*(LEV+1)-1:0] ret_d;
    wire [TAGW*(LEV+1)-1:0] ret_tag;
    wire [LEV:0]       lf;
    assign lv_v[0] = iv;
    assign lv_last[0] = ilast;
    assign lv_d[31:0] = d;
    assign lv_slot[SW-1:0] = islot;
    assign lv_tag[TAGW-1:0] = itag;
    genvar l;
    generate
        for (l = 0; l < LEV; l = l + 1) begin : g_lv
            reg [IL-1:0]  pend_v, seen;
            reg [31:0]    pend_d [0:IL-1];
            wire          v_in = lv_v[l];
            wire          last_in = lv_last[l];
            wire [31:0]   d_in = lv_d[32*l +: 32];
            wire [SW-1:0] s_in = lv_slot[SW*l +: SW];
            wire [TAGW-1:0] t_in = lv_tag[TAGW*l +: TAGW];
            wire          have = pend_v[s_in];
            wire          lone = v_in && last_in && !have && !seen[s_in];
            wire          go   = v_in && !lone && (have || last_in);
            wire [31:0]   opa  = have ? pend_d[s_in] : 32'd0;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    pend_v <= {IL{1'b0}};
                    seen <= {IL{1'b0}};
                end else if (v_in) begin
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
            always @(posedge clk) if (v_in && !last_in && !have) pend_d[s_in] <= d_in;
            // the level's adder: pending + incoming, or incoming + (+0) for an unpaired final partial
            wire [31:0] sum;
            ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(go), .a(opa), .b(d_in), .y(sum), .fault(lf[l]));
            wire [ALAT:0] gv;
            ot_hdc_vline #(.D(ALAT)) u_gv (.clk(clk), .rst_n(rst_n), .v(go), .vd(gv));
            wire [SW+TAGW:0] meta_q;
            ot_hdc_delay #(.W(SW+TAGW+1), .D(ALAT)) u_meta (.clk(clk), .rst_n(rst_n),
                                                         .d({last_in, s_in, t_in}), .q(meta_q));
            assign lv_v[l+1] = gv[ALAT];
            assign lv_last[l+1] = meta_q[SW+TAGW];
            assign lv_slot[SW*(l+1) +: SW] = meta_q[SW+TAGW-1:TAGW];
            assign lv_tag[TAGW*(l+1) +: TAGW] = meta_q[TAGW-1:0];
            assign lv_d[32*(l+1) +: 32] = sum;
            assign ret_v[l] = lone;
            assign ret_d[32*l +: 32] = d_in;
            assign ret_tag[TAGW*l +: TAGW] = t_in;
        end
    endgenerate
    // the top level: whatever arrives is a finished row (G = 2^LEV fills every level)
    assign ret_v[LEV] = lv_v[LEV];
    assign ret_d[32*LEV +: 32] = lv_d[32*LEV +: 32];
    assign ret_tag[TAGW*LEV +: TAGW] = lv_tag[TAGW*LEV +: TAGW];
    assign lf[LEV] = 1'b0;
    integer k, nret;
    reg [31:0] y_n;
    reg [TAGW-1:0] t_n;
    always @* begin
        nret = 0; y_n = 32'd0; t_n = {TAGW{1'b0}};
        for (k = 0; k <= LEV; k = k + 1)
            if (ret_v[k]) begin
                nret = nret + 1;
                y_n = ret_d[32*k +: 32];
                t_n = ret_tag[TAGW*k +: TAGW];
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
