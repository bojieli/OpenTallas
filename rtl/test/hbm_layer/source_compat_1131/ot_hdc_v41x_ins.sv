`timescale 1ns/1ps
`default_nettype none
// Functional source view: exact existing module, no production/default selection.
module ot_hdc_v41x_ins #(
    parameter integer W = 32,
    parameter integer K = 2,                 // depth choices
    parameter [16*K-1:0] DEPTHS = {16'd3, 16'd0},   // choice k = DEPTHS[16k +: 16]
    parameter integer DMAX = 3,              // max over DEPTHS
    parameter integer RESET_DATA = 0,
    // RING (CLAUDE HBM-ABSTRACTS views agent, default off): the line as a timing wheel of DMAX slots.  An item loaded at
    // edge e with depth p goes to slot (e + p) mod DMAX and is read into the output register at edge e + p - 1, the
    // cycle the shift line presents it in r[1]; a slot still holding an item due in the same cycle is the shift line's
    // collision (rv[p+1] set), the new item wins in both.  Needs every non-zero depth >= 2.  Same vo / q / coll / busy
    // as the shift line for valid items (q while vo = 0 is not defined by either form).
    parameter integer RING = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice
    input  wire [W-1:0] d,
    output wire         vo,
    output wire [W-1:0] q,
    output wire         coll,
    output wire         busy                 // an item is in the line
);
    function automatic has(input integer p, input [K-1:0] s);
        integer k;
        begin
            has = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p && s[k]) has = 1'b1;
        end
    endfunction
    function automatic canbe(input integer p);
        integer k;
        begin
            canbe = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p) canbe = 1'b1;
        end
    endfunction
    generate
        if (DMAX == 0) begin : g_wire
            assign vo = v; assign q = d; assign coll = 1'b0; assign busy = 1'b0;
        end else if (RING >= 3) begin : g_ring3
            // RING 3 (hbm-blocks 2026-10-07): RING 2's timing wheel (per-16-bit-chunk slot-pointer copies) with every
            // rotation written as constant generate wiring.  RING 2 calls rot() inside always @(*) blocks once per
            // (slot, chunk, depth) and ORs the read word bit by bit: at the SFU lane's DMAX/K/W the yosys AST frontend
            // sat > 10 h deriving this module.  Same vo / q / coll / busy as RING 2 cycle for cycle.
            localparam integer N = DMAX;
            initial if (canbe(1) || DMAX < 2) $error("ot_hdc_v41x_ins RING: depth 1 not supported");
            localparam integer CH = 16;
            localparam integer NC = (W + CH - 1) / CH;
            reg [N-1:0] oh;                          // slot e mod N (valid side)
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            wire [N-1:0] ohc [0:NC-1];               // per-chunk kept copies (data side)
            genvar c0;
            for (c0 = 0; c0 < NC; c0 = c0 + 1) begin : g_ohc
                (* keep *) reg [N-1:0] r;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) r <= {{(N-1){1'b0}}, 1'b1};
                    else r <= {r[N-2:0], r[N-1]};
                assign ohc[c0] = r;
            end
            wire [N-1:0] we;                         // valid-side write enables
            wire [N-1:0] rs;                         // slot read at this edge: rot(oh, 1)
            reg  [N-1:0] mv;
            wire [W-1:0] acc [0:N];                  // read word, OR-accumulated over the slots
            assign acc[0] = {W{1'b0}};
            genvar j, c, k;
            for (j = 0; j < N; j = j + 1) begin : g_s
                localparam integer JR = (j - 1 + N) % N;
                assign rs[j] = oh[JR];
                wire [K-1:0] wt;
                for (k = 0; k < K; k = k + 1) begin : g_k
                    localparam integer DK = DEPTHS[16*k +: 16];
                    localparam integer JW = (j - (DK % N) + N) % N;
                    if (DK != 0) begin : g_d
                        assign wt[k] = v && sel[k] && oh[JW];
                    end else begin : g_z
                        assign wt[k] = 1'b0;
                    end
                end
                assign we[j] = |wt;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) mv[j] <= 1'b0;
                    else if (we[j]) mv[j] <= 1'b1;
                    else if (rs[j]) mv[j] <= 1'b0;
                wire [W-1:0] mj;                     // slot j's data
                wire [W-1:0] rmask;                  // per-chunk read select of slot j
                for (c = 0; c < NC; c = c + 1) begin : g_c
                    localparam integer LO = c * CH;
                    localparam integer WC = (W - LO < CH) ? (W - LO) : CH;
                    wire [K-1:0] wtc;
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        localparam integer DK = DEPTHS[16*k +: 16];
                        localparam integer JW = (j - (DK % N) + N) % N;
                        if (DK != 0) begin : g_d
                            assign wtc[k] = v && sel[k] && ohc[c][JW];
                        end else begin : g_z
                            assign wtc[k] = 1'b0;
                        end
                    end
                    wire wec = |wtc;
                    reg [WC-1:0] mc;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) mc <= {WC{1'b0}}; else if (wec) mc <= d[LO +: WC];
                    end else begin : g_nd
                        always @(posedge clk) if (wec) mc <= d[LO +: WC];
                    end
                    assign mj[LO +: WC] = mc;
                    assign rmask[LO +: WC] = {WC{ohc[c][JR]}};
                end
                assign acc[j + 1] = acc[j] | (mj & rmask);
            end
            wire [W-1:0] rd = acc[N];
            wire cw = |(we & mv);
            wire rdv = |(mv & rs);
            reg qv;
            reg [W-1:0] qr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) qv <= 1'b0; else qv <= rdv;
            if (RESET_DATA != 0) begin : g_qrd
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnd
                always @(posedge clk) qr <= rd;
            end
            wire now = v && has(0, sel);
            assign vo = now || qv;
            assign q  = now ? d : qr;
            assign coll = cw || (now && qv);
            assign busy = qv || (|mv);
        end else if (RING != 0) begin : g_ring
            localparam integer N = DMAX;
            initial if (canbe(1) || DMAX < 2) $error("ot_hdc_v41x_ins RING: depth 1 not supported");
            reg [N-1:0] oh;                          // one-hot slot of the current edge e (slot e mod N)
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            // RING 2 (views agent 2026-10-07, SFU lane 67f177d39 oh -> m -24 ps over 304 endpoints, 10 levels): the slot
            // pointer in one kept copy per 16-bit data chunk (reset and rotated identically), each driving only its chunk's
            // write enables and read select.  0 cycles.
            localparam integer CH = 16;
            localparam integer NC = (RING >= 2) ? (W + CH - 1) / CH : 1;
            wire [N-1:0] ohc [0:NC-1];
            genvar c0;
            for (c0 = 0; c0 < NC; c0 = c0 + 1) begin : g_ohc
                (* keep *) reg [N-1:0] r;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) r <= {{(N-1){1'b0}}, 1'b1};
                    else r <= {r[N-2:0], r[N-1]};
                assign ohc[c0] = r;
            end
            // rot(oh, k)[j] = oh[(j - k) mod N]: the slot k edges ahead
            function automatic [N-1:0] rot(input [N-1:0] x, input integer k);
                integer j;
                begin
                    for (j = 0; j < N; j = j + 1) rot[j] = x[(j - (k % N) + N) % N];
                end
            endfunction
            reg [W-1:0] m [0:N-1];
            reg [N-1:0] mv;
            reg [W-1:0] qr;
            reg         qv;
            // write enables: the chosen depth's slot
            reg [N-1:0] we;
            reg         cw;
            integer k;
            always @(*) begin
                we = {N{1'b0}};
                for (k = 0; k < K; k = k + 1)
                    if (DEPTHS[16*k +: 16] != 0 && v && sel[k]) we = we | rot(oh, DEPTHS[16*k +: 16]);
                cw = |(we & mv);
            end
            wire [N-1:0] rs = rot(oh, 1);            // slot read at this edge (due next cycle)
            reg [N-1:0] rsc [0:NC-1];                // RING 2: per-chunk copies of rs
            integer c2;
            always @(*) for (c2 = 0; c2 < NC; c2 = c2 + 1) rsc[c2] = rot(ohc[c2], 1);
            reg [W-1:0] rd;
            reg         rdv;
            integer i, c1;
            always @(*) begin
                rd = {W{1'b0}}; rdv = 1'b0;
                for (i = 0; i < N; i = i + 1) begin
                    if (RING >= 2) begin
                        for (c1 = 0; c1 < W; c1 = c1 + 1) rd[c1] = rd[c1] | (m[i][c1] & rsc[c1 / CH][i]);
                    end else rd = rd | (m[i] & {W{rs[i]}});
                    rdv = rdv | (mv[i] & rs[i]);
                end
            end
            genvar j;
            for (j = 0; j < N; j = j + 1) begin : g_s
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) mv[j] <= 1'b0;
                    else if (we[j]) mv[j] <= 1'b1;
                    else if (rs[j]) mv[j] <= 1'b0;
                if (RING >= 2) begin : g_cw
                    genvar c;
                    for (c = 0; c < NC; c = c + 1) begin : g_c
                        localparam integer LO = c * CH;
                        localparam integer WC = (W - LO < CH) ? (W - LO) : CH;
                        reg wec; reg [N-1:0] rr;
                        integer k2;
                        always @(*) begin
                            wec = 1'b0;
                            for (k2 = 0; k2 < K; k2 = k2 + 1) begin
                                rr = rot(ohc[c], DEPTHS[16*k2 +: 16]);
                                if (DEPTHS[16*k2 +: 16] != 0 && v && sel[k2]) wec = wec | rr[j];
                            end
                        end
                        if (RESET_DATA != 0) begin : g_rd
                            always @(posedge clk or negedge rst_n)
                                if (!rst_n) m[j][LO +: WC] <= {WC{1'b0}}; else if (wec) m[j][LO +: WC] <= d[LO +: WC];
                        end else begin : g_nd
                            always @(posedge clk) if (wec) m[j][LO +: WC] <= d[LO +: WC];
                        end
                    end
                end else if (RESET_DATA != 0) begin : g_rd
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) m[j] <= {W{1'b0}}; else if (we[j]) m[j] <= d;
                end else begin : g_nd
                    always @(posedge clk) if (we[j]) m[j] <= d;
                end
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) qv <= 1'b0; else qv <= rdv;
            if (RESET_DATA != 0) begin : g_qrd
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnd
                always @(posedge clk) qr <= rd;
            end
            wire now = v && has(0, sel);
            assign vo = now || qv;
            assign q  = now ? d : qr;
            assign coll = cw || (now && qv);
            assign busy = qv || (|mv);
        end else begin : g_line
            reg [W-1:0] r  [1:DMAX];
            reg         rv [1:DMAX];
            wire [DMAX+1:1] cl;
            assign cl[DMAX+1] = 1'b0;
            genvar p;
            for (p = 1; p <= DMAX; p = p + 1) begin : g_s
                wire [W-1:0] nx  = (p == DMAX) ? {W{1'b0}} : r[(p == DMAX) ? p : p + 1];
                wire         nxv = (p == DMAX) ? 1'b0 : rv[(p == DMAX) ? p : p + 1];
                if (canbe(p)) begin : g_ld
                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= ld || nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= ld ? d : nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= ld ? d : nx;
                    end
                end else begin : g_sh
                    assign cl[p] = 1'b0;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= nx;
                    end
                end
            end
            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];
            assign coll = (|cl) || (now && rv[1]);
            reg any;
            integer b;
            always @(*) begin
                any = 1'b0;
                for (b = 1; b <= DMAX; b = b + 1) any = any | rv[b];
            end
            assign busy = any;
        end
    endgenerate
endmodule
`default_nettype wire
