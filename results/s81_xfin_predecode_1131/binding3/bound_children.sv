module eng_old #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         // tree (0 hh, 1 kk, 2 dd)
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         // one pulse when all three roots are final
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault
);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    function automatic integer ca(input integer n);     // left operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            ca = (n == 4) ? 8 : (n == 5) ? 9 : 2 * n;
`else
            ca = 2 * n;
`endif
        end
    endfunction
    function automatic integer cb(input integer n);     // right operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            cb = (n == 4) ? 10 : (n == 5) ? 11 : 2 * n + 1;
`else
            cb = 2 * n + 1;
`endif
        end
    endfunction
    localparam integer NRS = 8;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= {NRS{1'b0}}; else rsr <= {NRS{rs[0]}};
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    // S81-CORES-KITS-9 10-31 (hard child face rule, raw face_guard): f_v lands RAW in its face flop iv_r; the go clear
    // is applied after the flop with go_t delayed by the same edge (iv = iv_r & ~go_q == old go_t ? 0 : f_v register,
    // cycle-exact, both reset 0 under rstn).
    reg [P-1:0] iv_r; reg go_q; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    wire        wr_v;
    wire [CW-1:0] wr_n;
    wire [31:0] wr_d;
    wire [NC-1:0] rdy, iss_v, win;
    wire [T*NVP-1:0] dup;
    wire [31:0] V  [0:T-1][1:2*NVP-1];
    wire        VD [0:T-1][1:2*NVP-1];
    genvar t, n, p, k;
    generate for (t = 0; t < T; t = t + 1) begin : g_t
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        // ENG flit bases are sid * K by construction (xfin fb), so leaf IX is only ever slot IX % K:
                        // the other slots are not wired (3:1 leaf mux instead of 15:1)
                        if (k == IX % K) begin : g_m
                            assign m[p * K + k] = iv[p] && it[p * 2 +: 2] == t && (ib[p * 8 +: 8] == IX - k);
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pad
                assign dup[t * NVP + IX] = 1'b0;
                assign V[t][n] = 32'd0; assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0;
                    else if (wr_v && wr_n == t * NVP + n) vld <= 1'b1;
                always @(posedge clk) if (wr_v && wr_n == t * NVP + n) val <= wr_d;
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pass
                assign V[t][n] = V[t][2 * n]; assign VD[t][n] = VD[t][2 * n];
            end
        end
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t) iss <= 1'b0; else if (win[t * NVP + n]) iss <= 1'b1;
                assign iss_v[t * NVP + n] = iss;
                assign rdy[t * NVP + n] = VD[t][ca(n)] && VD[t][cb(n)] && !iss && !go_t;
            end else begin : g_n
                assign iss_v[t * NVP + n] = 1'b1; assign rdy[t * NVP + n] = 1'b0;
            end
        end
    end endgenerate
    // two-level registered priority issue (as ot_s81dv_norm_finish): 8-node groups, then the lowest non-empty group
    localparam integer NG8 = NC / 8;
    wire [NC-1:0] oh1; wire [NG8-1:0] ga1;
    genvar q;
    generate for (q = 0; q < NG8; q = q + 1) begin : g_grp
        wire [7:0] r8 = rdy[q * 8 +: 8];
        wire [7:0] o8 = r8 & ~(r8 - 8'd1);
        reg [7:0] o_r; reg g_r;
        always @(posedge clk or negedge rsr[q % NRS])
            if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
            else begin o_r <= o8; g_r <= |r8; end
        assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r;
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
    end endgenerate
    wire fire = |win;
    wire [31:0] oa [0:NC], ob [0:NC];
    wire [CW-1:0] ot [0:NC];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign oa[C + 1] = oa[C] | ({32{win[C]}} & V[t][ca(n)]);
                assign ob[C + 1] = ob[C] | ({32{win[C]}} & V[t][cb(n)]);
                assign ot[C + 1] = ot[C] | ({CW{win[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign oa[C + 1] = oa[C]; assign ob[C + 1] = ob[C]; assign ot[C + 1] = ot[C];
            end
        end
    end endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NC]; b_q <= ob[NC]; t_q <= ot[NC]; end
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    ot_hdc_delay #(.W(CW), .D(LAV)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n));
    assign wr_v = av[LAV];
    // roots: node 1 of each tree
    reg [T-1:0] dn; (* keep = "true" *) reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    // S81-CORES-KITS-9 10-31 (hard child face rule: no output pin flop reads itself): the root values are held in
    // internal registers *_s; the r_* pin flops load the root value on the r_v edge and ZERO otherwise, so r_* equal
    // the old held r_* whenever r_v = 1 (the only cycle ot_s81dv_xfin reads them: ehh/ekk/edd and e_* load under cr_v).
    // fault = its own pin flop loading the next state of the kept sticky flt (same value every cycle, as xfin's fault).
    wire w_hh = wr_v && wr_n == 1, w_kk = wr_v && wr_n == NVP + 1, w_dd = wr_v && wr_n == 2 * NVP + 1;
    wire fin = !go_t && dn != {T{1'b1}} && (dn | {w_dd, w_kk, w_hh}) == {T{1'b1}};   // = the r_v set condition
    reg [31:0] hh_s, kk_s, dd_s;
    always @(posedge clk) begin
        if (w_hh) hh_s <= wr_d;
        if (w_kk) kk_s <= wr_d;
        if (w_dd) dd_s <= wr_d;
        r_hh <= fin ? (w_hh ? wr_d : hh_s) : 32'd0;
        r_kk <= fin ? (w_kk ? wr_d : kk_s) : 32'd0;
        r_dd <= fin ? (w_dd ? wr_d : dd_s) : 32'd0;
    end
    reg flt_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt_o <= 1'b0; else flt_o <= go_t ? 1'b0 : (flt | f_add | (|dup));
    assign fault = flt_o;
endmodule
module eng_new #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         // tree (0 hh, 1 kk, 2 dd)
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         // one pulse when all three roots are final
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault
);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    function automatic integer ca(input integer n);     // left operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            ca = (n == 4) ? 8 : (n == 5) ? 9 : 2 * n;
`else
            ca = 2 * n;
`endif
        end
    endfunction
    function automatic integer cb(input integer n);     // right operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            cb = (n == 4) ? 10 : (n == 5) ? 11 : 2 * n + 1;
`else
            cb = 2 * n + 1;
`endif
        end
    endfunction
    localparam integer NRS = 8;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= {NRS{1'b0}}; else rsr <= {NRS{rs[0]}};
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    // S81-CORES-KITS-9 10-31 (hard child face rule, raw face_guard): f_v lands RAW in its face flop iv_r; the go clear
    // is applied after the flop with go_t delayed by the same edge (iv = iv_r & ~go_q == old go_t ? 0 : f_v register,
    // cycle-exact, both reset 0 under rstn).
    reg [P-1:0] iv_r; reg go_q; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    wire        wr_v;

    wire [31:0] wr_d;
    wire [NC-1:0] rdy, iss_v, win;
    wire [T*NVP-1:0] dup;
    wire [31:0] V  [0:T-1][1:2*NVP-1];
    wire        VD [0:T-1][1:2*NVP-1];
    genvar t, n, p, k;
    generate for (t = 0; t < T; t = t + 1) begin : g_t
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        // ENG flit bases are sid * K by construction (xfin fb), so leaf IX is only ever slot IX % K:
                        // the other slots are not wired (3:1 leaf mux instead of 15:1)
                        if (k == IX % K) begin : g_m
                            assign m[p * K + k] = iv[p] && it[p * 2 +: 2] == t && (ib[p * 8 +: 8] == IX - k);
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pad
                assign dup[t * NVP + IX] = 1'b0;
                assign V[t][n] = 32'd0; assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0;
                    else if (wr_v && wr_onehot[t * NVP + n]) vld <= 1'b1;
                always @(posedge clk) if (wr_v && wr_onehot[t * NVP + n]) val <= wr_d;
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pass
                assign V[t][n] = V[t][2 * n]; assign VD[t][n] = VD[t][2 * n];
            end
        end
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t) iss <= 1'b0; else if (win[t * NVP + n]) iss <= 1'b1;
                assign iss_v[t * NVP + n] = iss;
                assign rdy[t * NVP + n] = VD[t][ca(n)] && VD[t][cb(n)] && !iss && !go_t;
            end else begin : g_n
                assign iss_v[t * NVP + n] = 1'b1; assign rdy[t * NVP + n] = 1'b0;
            end
        end
    end endgenerate
    // two-level registered priority issue (as ot_s81dv_norm_finish): 8-node groups, then the lowest non-empty group
    localparam integer NG8 = NC / 8;
    wire [NC-1:0] oh1; wire [NG8-1:0] ga1;
    genvar q;
    generate for (q = 0; q < NG8; q = q + 1) begin : g_grp
        wire [7:0] r8 = rdy[q * 8 +: 8];
        wire [7:0] o8 = r8 & ~(r8 - 8'd1);
        reg [7:0] o_r; reg g_r;
        always @(posedge clk or negedge rsr[q % NRS])
            if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
            else begin o_r <= o8; g_r <= |r8; end
        assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r;
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
    end endgenerate
    wire fire = |win;
    wire [31:0] oa [0:NC], ob [0:NC];
    wire [CW-1:0] ot [0:NC];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign oa[C + 1] = oa[C] | ({32{win[C]}} & V[t][ca(n)]);
                assign ob[C + 1] = ob[C] | ({32{win[C]}} & V[t][cb(n)]);
                assign ot[C + 1] = ot[C] | ({CW{win[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign oa[C + 1] = oa[C]; assign ob[C + 1] = ob[C]; assign ot[C + 1] = ot[C];
            end
        end
    end endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NC]; b_q <= ob[NC]; t_q <= ot[NC]; end
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    // Private source-bound six-edge write predecode: t_q capture is retained.
    wire [NC-1:0] wr_early, wr_onehot;
    genvar wt, wn;
    generate for (wt=0; wt<T; wt=wt+1) begin : g_predecode_tree
        for (wn=0; wn<NVP; wn=wn+1) begin : g_predecode_node
            if (wn>=1 && isadd(wn)) begin : g_live
                assign wr_early[wt*NVP+wn] = (t_q == wt*NVP+wn);
            end else begin : g_dead
                assign wr_early[wt*NVP+wn] = 1'b0;
            end
        end
    end endgenerate
    wire [NC-1:0] wr_early_bound = wr_early ;
    ot_hdc_delay #(.W(NC), .D(LAV)) u_wr_onehot (.clk(clk), .rst_n(rstn), .d(wr_early_bound), .q(wr_onehot));
    assign wr_v = av[LAV];
    // roots: node 1 of each tree
    reg [T-1:0] dn; (* keep = "true" *) reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_onehot[1])           dn[0] <= 1'b1;
                if (wr_v && wr_onehot[NVP + 1])         dn[1] <= 1'b1;
                if (wr_v && wr_onehot[2 * NVP + 1])     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_onehot[2 * NVP + 1], wr_v && wr_onehot[NVP + 1], wr_v && wr_onehot[1]})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    // S81-CORES-KITS-9 10-31 (hard child face rule: no output pin flop reads itself): the root values are held in
    // internal registers *_s; the r_* pin flops load the root value on the r_v edge and ZERO otherwise, so r_* equal
    // the old held r_* whenever r_v = 1 (the only cycle ot_s81dv_xfin reads them: ehh/ekk/edd and e_* load under cr_v).
    // fault = its own pin flop loading the next state of the kept sticky flt (same value every cycle, as xfin's fault).
    wire w_hh = wr_v && wr_onehot[1], w_kk = wr_v && wr_onehot[NVP + 1], w_dd = wr_v && wr_onehot[2 * NVP + 1];
    wire fin = !go_t && dn != {T{1'b1}} && (dn | {w_dd, w_kk, w_hh}) == {T{1'b1}};   // = the r_v set condition
    reg [31:0] hh_s, kk_s, dd_s;
    always @(posedge clk) begin
        if (w_hh) hh_s <= wr_d;
        if (w_kk) kk_s <= wr_d;
        if (w_dd) dd_s <= wr_d;
        r_hh <= fin ? (w_hh ? wr_d : hh_s) : 32'd0;
        r_kk <= fin ? (w_kk ? wr_d : kk_s) : 32'd0;
        r_dd <= fin ? (w_dd ? wr_d : dd_s) : 32'd0;
    end
    reg flt_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt_o <= 1'b0; else flt_o <= go_t ? 1'b0 : (flt | f_add | (|dup));
    assign fault = flt_o;
endmodule
module eng_mut #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         // tree (0 hh, 1 kk, 2 dd)
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         // one pulse when all three roots are final
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault
);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    function automatic integer ca(input integer n);     // left operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            ca = (n == 4) ? 8 : (n == 5) ? 9 : 2 * n;
`else
            ca = 2 * n;
`endif
        end
    endfunction
    function automatic integer cb(input integer n);     // right operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            cb = (n == 4) ? 10 : (n == 5) ? 11 : 2 * n + 1;
`else
            cb = 2 * n + 1;
`endif
        end
    endfunction
    localparam integer NRS = 8;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= {NRS{1'b0}}; else rsr <= {NRS{rs[0]}};
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    // S81-CORES-KITS-9 10-31 (hard child face rule, raw face_guard): f_v lands RAW in its face flop iv_r; the go clear
    // is applied after the flop with go_t delayed by the same edge (iv = iv_r & ~go_q == old go_t ? 0 : f_v register,
    // cycle-exact, both reset 0 under rstn).
    reg [P-1:0] iv_r; reg go_q; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    wire        wr_v;

    wire [31:0] wr_d;
    wire [NC-1:0] rdy, iss_v, win;
    wire [T*NVP-1:0] dup;
    wire [31:0] V  [0:T-1][1:2*NVP-1];
    wire        VD [0:T-1][1:2*NVP-1];
    genvar t, n, p, k;
    generate for (t = 0; t < T; t = t + 1) begin : g_t
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        // ENG flit bases are sid * K by construction (xfin fb), so leaf IX is only ever slot IX % K:
                        // the other slots are not wired (3:1 leaf mux instead of 15:1)
                        if (k == IX % K) begin : g_m
                            assign m[p * K + k] = iv[p] && it[p * 2 +: 2] == t && (ib[p * 8 +: 8] == IX - k);
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pad
                assign dup[t * NVP + IX] = 1'b0;
                assign V[t][n] = 32'd0; assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0;
                    else if (wr_v && wr_onehot[t * NVP + n]) vld <= 1'b1;
                always @(posedge clk) if (wr_v && wr_onehot[t * NVP + n]) val <= wr_d;
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pass
                assign V[t][n] = V[t][2 * n]; assign VD[t][n] = VD[t][2 * n];
            end
        end
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t) iss <= 1'b0; else if (win[t * NVP + n]) iss <= 1'b1;
                assign iss_v[t * NVP + n] = iss;
                assign rdy[t * NVP + n] = VD[t][ca(n)] && VD[t][cb(n)] && !iss && !go_t;
            end else begin : g_n
                assign iss_v[t * NVP + n] = 1'b1; assign rdy[t * NVP + n] = 1'b0;
            end
        end
    end endgenerate
    // two-level registered priority issue (as ot_s81dv_norm_finish): 8-node groups, then the lowest non-empty group
    localparam integer NG8 = NC / 8;
    wire [NC-1:0] oh1; wire [NG8-1:0] ga1;
    genvar q;
    generate for (q = 0; q < NG8; q = q + 1) begin : g_grp
        wire [7:0] r8 = rdy[q * 8 +: 8];
        wire [7:0] o8 = r8 & ~(r8 - 8'd1);
        reg [7:0] o_r; reg g_r;
        always @(posedge clk or negedge rsr[q % NRS])
            if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
            else begin o_r <= o8; g_r <= |r8; end
        assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r;
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
    end endgenerate
    wire fire = |win;
    wire [31:0] oa [0:NC], ob [0:NC];
    wire [CW-1:0] ot [0:NC];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign oa[C + 1] = oa[C] | ({32{win[C]}} & V[t][ca(n)]);
                assign ob[C + 1] = ob[C] | ({32{win[C]}} & V[t][cb(n)]);
                assign ot[C + 1] = ot[C] | ({CW{win[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign oa[C + 1] = oa[C]; assign ob[C + 1] = ob[C]; assign ot[C + 1] = ot[C];
            end
        end
    end endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NC]; b_q <= ob[NC]; t_q <= ot[NC]; end
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    // Private source-bound six-edge write predecode: t_q capture is retained.
    wire [NC-1:0] wr_early, wr_onehot;
    genvar wt, wn;
    generate for (wt=0; wt<T; wt=wt+1) begin : g_predecode_tree
        for (wn=0; wn<NVP; wn=wn+1) begin : g_predecode_node
            if (wn>=1 && isadd(wn)) begin : g_live
                assign wr_early[wt*NVP+wn] = (t_q == wt*NVP+wn);
            end else begin : g_dead
                assign wr_early[wt*NVP+wn] = 1'b0;
            end
        end
    end endgenerate
    wire [NC-1:0] wr_early_bound = wr_early ^ {{(NC-2){1'b0}},2'b10};
    ot_hdc_delay #(.W(NC), .D(LAV)) u_wr_onehot (.clk(clk), .rst_n(rstn), .d(wr_early_bound), .q(wr_onehot));
    assign wr_v = av[LAV];
    // roots: node 1 of each tree
    reg [T-1:0] dn; (* keep = "true" *) reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_onehot[1])           dn[0] <= 1'b1;
                if (wr_v && wr_onehot[NVP + 1])         dn[1] <= 1'b1;
                if (wr_v && wr_onehot[2 * NVP + 1])     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_onehot[2 * NVP + 1], wr_v && wr_onehot[NVP + 1], wr_v && wr_onehot[1]})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    // S81-CORES-KITS-9 10-31 (hard child face rule: no output pin flop reads itself): the root values are held in
    // internal registers *_s; the r_* pin flops load the root value on the r_v edge and ZERO otherwise, so r_* equal
    // the old held r_* whenever r_v = 1 (the only cycle ot_s81dv_xfin reads them: ehh/ekk/edd and e_* load under cr_v).
    // fault = its own pin flop loading the next state of the kept sticky flt (same value every cycle, as xfin's fault).
    wire w_hh = wr_v && wr_onehot[1], w_kk = wr_v && wr_onehot[NVP + 1], w_dd = wr_v && wr_onehot[2 * NVP + 1];
    wire fin = !go_t && dn != {T{1'b1}} && (dn | {w_dd, w_kk, w_hh}) == {T{1'b1}};   // = the r_v set condition
    reg [31:0] hh_s, kk_s, dd_s;
    always @(posedge clk) begin
        if (w_hh) hh_s <= wr_d;
        if (w_kk) kk_s <= wr_d;
        if (w_dd) dd_s <= wr_d;
        r_hh <= fin ? (w_hh ? wr_d : hh_s) : 32'd0;
        r_kk <= fin ? (w_kk ? wr_d : kk_s) : 32'd0;
        r_dd <= fin ? (w_dd ? wr_d : dd_s) : 32'd0;
    end
    reg flt_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt_o <= 1'b0; else flt_o <= go_t ? 1'b0 : (flt | f_add | (|dup));
    assign fault = flt_o;
endmodule