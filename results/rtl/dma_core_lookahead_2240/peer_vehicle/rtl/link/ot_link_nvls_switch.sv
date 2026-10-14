`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_nvls_switch: the core of one NVLink-class switch tier with
// deterministic in-switch reduction (NVLS / SHARP-style), for W15's
// measurement of the V4.1 HBM comparator's TP-96 collectives.
//
// P ports, one per two-die package.  Records {tag, mode, last, data} arrive on
// each port's receive link (ot_link_rx) and leave on every port's transmit link
// (ot_link_tx): the switch multicasts.
//
//   ALL-REDUCE (mode 0)  per word index, the P ports' records are popped
//                        together and added lane by lane in a FIXED pairwise
//                        tree over the port (package) index: level l adds
//                        elements (2i, 2i+1) of level l-1; an odd last element
//                        passes through (delayed to stay aligned).  Binary32
//                        RNE adds (ot_hdc_fp32_add_fast, 3 cycles), so every
//                        package receives the same bits whatever the arrival
//                        order.  The result is multicast to all ports.
//   ALL-GATHER (mode 1)  records are forwarded, one a cycle, to every port;
//                        ports with a waiting gather record are served in a
//                        fixed rotation.  Receivers place records by the
//                        source die in the tag, so the result does not depend
//                        on the rotation.
//
// Every output then passes SW_PIPE register stages: the rest of the switch's
// port-to-port cut-through latency (crossbar, buffering, the switch's own port
// logic), set so the core's total is the cited switch latency (see
// tools/w15_collectives.py HBM_SWITCH).  Only one collective is in the switch
// at a time (blocking COLL, as the engines).
// ---------------------------------------------------------------------------
module ot_link_nvls_switch #(
    parameter integer P       = 48,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 512,
    parameter integer SW_PIPE = 200,
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [P-1:0]      in_valid,
    input  wire [P*PW-1:0]   in_rec,
    output wire              out_valid,           // multicast to every port
    output wire [PW-1:0]     out_rec,
    output reg               fault                // FIFO overflow or an arithmetic error (fail closed)
);
    localparam integer ADD_LAT = 3;
    localparam integer DB = $clog2(DEPTH);
    localparam integer PB = (P > 1) ? $clog2(P) : 1;
    // tree geometry
    function automatic integer nlev(input integer l);   // elements at level l
        integer k, n;
        begin
            n = P;
            for (k = 0; k < l; k = k + 1) n = (n + 1) / 2;
            nlev = n;
        end
    endfunction
    localparam integer L = $clog2(P);                    // levels (P > 1)

    // ---- input FIFOs ----------------------------------------------------------------------------------
    reg  [PW-1:0] m [0:P*DEPTH-1];
    reg  [DB:0]   cnt [0:P-1];
    reg  [DB-1:0] wp [0:P-1], rp [0:P-1];
    wire [PW-1:0] head [0:P-1];
    reg  [P-1:0]  ne, hmode;
    genvar g, l, i;
    generate for (g = 0; g < P; g = g + 1) begin : g_in
        assign head[g] = m[g*DEPTH + rp[g]];
    end endgenerate
    integer r;
    always @(*) for (r = 0; r < P; r = r + 1) begin
        ne[r] = cnt[r] != 0;
        hmode[r] = head[r][FW + 1];
    end
    wire pop_red = (&ne) && !(|hmode);
    // gather: the next port in rotation with a waiting gather record
    reg  [PB-1:0] rot;
    reg           gsel_v;
    reg  [PB-1:0] gsel;
    integer k2, pp;
    always @(*) begin
        gsel_v = 1'b0; gsel = 0;
        for (k2 = P - 1; k2 >= 0; k2 = k2 - 1) begin
            pp = (rot + k2) % P;
            if (ne[pp] && hmode[pp]) begin gsel_v = 1'b1; gsel = pp[PB-1:0]; end
        end
    end
    wire pop_gat = gsel_v && !pop_red;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (r = 0; r < P; r = r + 1) begin cnt[r] <= 0; wp[r] <= 0; rp[r] <= 0; end
            rot <= 0;
        end else begin
            for (r = 0; r < P; r = r + 1) begin
                if (in_valid[r]) begin
                    m[r*DEPTH + wp[r]] <= in_rec[r*PW +: PW];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (pop_red || (pop_gat && gsel == r)) rp[r] <= rp[r] + 1'b1;
                cnt[r] <= cnt[r] + (in_valid[r] ? 1'b1 : 1'b0) - ((pop_red || (pop_gat && gsel == r)) ? 1'b1 : 1'b0);
            end
            if (pop_gat) rot <= (gsel == P - 1) ? 0 : gsel + 1'b1;
        end
    end

    // ---- reduction tree -------------------------------------------------------------------------------
    wire [FW-1:0] lv [0:L][0:P-1];
    wire          vv [0:L];
    wire [L:0]    ev;                                    // an arithmetic error at or below level l
    reg  [TAGW+1:0] t0;                                  // {tag, mode, last} of the popped index (port 0)
    generate
        for (i = 0; i < P; i = i + 1) begin : g_l0
            reg [FW-1:0] d;
            always @(posedge clk) if (pop_red) d <= head[i][FW-1:0];
            assign lv[0][i] = d;
        end
        reg v0;
        always @(posedge clk or negedge rst_n) if (!rst_n) v0 <= 1'b0; else v0 <= pop_red;
        assign vv[0] = v0;
        assign ev[0] = 1'b0;
        for (l = 1; l <= L; l = l + 1) begin : g_lev
            localparam integer NP = nlev(l - 1), NL = nlev(l);
            wire [NL-1:0] vo;
            wire [NL-1:0] eo;
            for (i = 0; i < NL; i = i + 1) begin : g_el
                if (2 * i + 1 < NP) begin : g_add
                    wire [LANES-1:0] lvv;
                    wire [2*LANES-1:0] le;
                    for (genvar ln = 0; ln < LANES; ln = ln + 1) begin : g_lane
                        ot_hdc_fp32_add_fast u_add (.clk(clk), .rst_n(rst_n), .valid_in(vv[l-1]),
                            .a(lv[l-1][2*i][32*ln +: 32]), .b(lv[l-1][2*i+1][32*ln +: 32]),
                            .y(lv[l][i][32*ln +: 32]), .err(le[2*ln +: 2]), .valid_out(lvv[ln]));
                    end
                    assign vo[i] = lvv[0];
                    assign eo[i] = |le;
                end else begin : g_pass
                    reg [FW*ADD_LAT-1:0] dl;
                    always @(posedge clk) dl <= {dl[FW*(ADD_LAT-1)-1:0], lv[l-1][2*i]};
                    assign lv[l][i] = dl[FW*ADD_LAT-1 -: FW];
                    assign vo[i] = 1'b0;
                    assign eo[i] = 1'b0;
                end
            end
            // the level's valid: the first adder's (level 1 always has one: P >= 2)
            reg [ADD_LAT-1:0] vd;
            always @(posedge clk or negedge rst_n) if (!rst_n) vd <= 0; else vd <= {vd[ADD_LAT-2:0], vv[l-1]};
            assign vv[l] = vd[ADD_LAT-1];
            reg [ADD_LAT-1:0] ed;
            always @(posedge clk or negedge rst_n) if (!rst_n) ed <= 0; else ed <= {ed[ADD_LAT-2:0], ev[l-1]};
            assign ev[l] = ed[ADD_LAT-1] | (|eo);
        end
    endgenerate
    always @(posedge clk) if (pop_red) t0 <= head[0][PW-1 -: TAGW + 2];
    reg [(TAGW+2)*(L*ADD_LAT)-1:0] td;                   // the popped index's tag, aligned with the tree
    always @(posedge clk) td <= {td[(TAGW+2)*(L*ADD_LAT-1)-1:0], t0};
    wire [TAGW+1:0] tr = td[(TAGW+2)*(L*ADD_LAT)-1 -: TAGW + 2];

    // ---- output: reduce result or forwarded gather record, then SW_PIPE stages -------------------------
    reg          gv;
    reg [PW-1:0] gr;
    always @(posedge clk or negedge rst_n) if (!rst_n) gv <= 1'b0; else gv <= pop_gat;
    always @(posedge clk) if (pop_gat) gr <= head[gsel];
    wire          ov0 = vv[L] || gv;
    wire [PW-1:0] or0 = vv[L] ? {8'hFF, tr[TAGW-7:2], tr[1:0], lv[L][0]} : gr;
    reg [SW_PIPE-1:0] pv;
    reg [PW-1:0]      pd [0:SW_PIPE-1];
    integer s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) pv <= 0;
        else begin
            pv[0] <= ov0;
            for (s = 1; s < SW_PIPE; s = s + 1) pv[s] <= pv[s-1];
        end
    always @(posedge clk) begin
        pd[0] <= or0;
        for (s = 1; s < SW_PIPE; s = s + 1) pd[s] <= pd[s-1];
    end
    assign out_valid = pv[SW_PIPE-1];
    assign out_rec = pd[SW_PIPE-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else begin
            if (vv[L] && ev[L]) fault <= 1'b1;
            if (vv[L] && gv) fault <= 1'b1;                // a reduce and a gather in the switch at once
            for (r = 0; r < P; r = r + 1) if (cnt[r] > DEPTH) fault <= 1'b1;
        end
    end
endmodule
