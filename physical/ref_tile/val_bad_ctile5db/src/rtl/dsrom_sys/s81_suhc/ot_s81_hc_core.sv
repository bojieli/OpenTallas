`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_core (stream s81-suhc-1011, 2026-10-11): the engine of the S81 HC slab master (dsfd_sp_hc), driven by
// the stage sequencer through the dsfd_sp_ctrl engine adapter (ot_s81_engine_adapter, engine port ENG hc = 2;
// physical/s81_ctrl/ADAPTER_CONTRACT_1011.json).  Engine side of the adapter:
//   e_cmd_v / e_cmd_d[83:0] = {slot[83], user[82:73], pos[72:52], tok[51:31], arg[30:7], op[6:0]} / e_cmd_ready
//   e_done_v / e_done_tag[7:0] = {slot, op}: pulsed when the job's LAST result has been committed (resident h written
//   back, or the last VM write issued: the VM applies ops in issue order, so a later reader sees it).
//
// Dataflow (owner-approved fix 2026-10-11, results/arch/s81_suhc_20261011/transport_model.json): the residual stream
// h (4 copies x D BF16) of each job slot is RESIDENT here.  hc_post rewrites it in place at NG x 4 elements a cycle
// (ot_dsrom_su_hcpost, the unit the token path prices), and the fused hc_pre -> RMSNorm -> FP8 act-quant
// (ot_dsrom_su_norm HC=1, N = 4 NG lanes, the priced attn.quant / ffn.norm.scale unit) reads it locally at 4 N
// elements a cycle.  The all-reduce result y arrives on a direct collective -> HC bus (NG words a beat); the VM
// carries only narrow traffic: stage-boundary h load / store (BF16 packed), the coefficient rows, the gain sets,
// and the norm's results.
//
// Resident h: row b (b = 0 .. NR-1, NR = D / NG) holds elements b*NG .. b*NG+NG-1, element g's copy k at
// [16*(4g+k)] (BF16).  Row b sits in bank b%4 at index slot*NV + b/4 (NV = NR/4), so a norm vector v (elements
// v*N .. v*N+N-1) is index v of the four banks read together.
//
// Job descriptor arg[23:0] (compiler-owned, tools/s81_ctrl/native_registry.json schema hc_core):
//   [23:20] kind   0 H_LOAD     h of the slot <- VM rows base .. base+NR*NG/8-1 (32 BF16 a row: element-major,
//                               element e copy k at [16*((e%8)*4+k)] of row e/8)
//                  1 H_STORE    the same layout, h of the slot -> VM
//                  2 COEF_LOAD  2 VM rows: row base = comb[16] (c[j][k] at word 4j+k); row base+1 = pre[4] (words
//                               0..3), post[4] (4..7), eps (8)
//                  3 POST       h <- hc_post(h, y, comb, post): NR y beats from the y port
//                  4 NORM       x = hc_pre(h, pre); y = rmsnorm(x, gain set gsel); outputs to VM rows from base:
//                               codes (QUANT) NV*N/64 rows, exps NV*ceil(N/1024) rows, then y (YOUT, BF16 packed 32
//                               a row) NV*N/32 rows
//                  5 GAIN_LOAD  gain set gsel <- VM rows base .. base + D/16 - 1 (binary32)
//   [19:18] gsel   [15] YOUT   [14] QUANT   [13:0] VM row base
//
// MUT (bench negative controls, 0 in silicon): 1 POST does not write h back (stale resident h); 2 POST / NORM use the
// other slot's h; 3 NORM skipped (done without running the norm); 4 done one write early; 5 done tag op bit flipped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_core #(
    parameter integer NG    = 256,          // hc_post element groups (row width); norm lanes N = 4 NG
    parameter integer D     = 5120,
    parameter integer S_RD  = 2,            // VM read row slots
    parameter integer S_WR  = 8,            // VM write row slots
    parameter integer LVM   = 10,           // VM read latency (request -> response), fixed
    parameter integer WIN   = 2,            // hc_post / norm operand register stages (resident memory -> lanes)
    parameter integer WOUT  = 2,
    parameter integer ML    = 5,
    parameter integer AL    = 4,
    parameter integer OQ    = 512,          // norm output row FIFO depth (rows)
    parameter integer MUT   = 0
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // engine side of ot_s81_engine_adapter
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output reg                    e_done_v,
    output reg  [7:0]             e_done_tag,
    // direct collective -> HC y bus (POST operand): NG binary32 words a beat
    input  wire                   y_v,
    output wire                   y_rdy,
    input  wire [NG*32-1:0]       y_d,
    // VM read slots: request {v, row}, response {v, data} LVM cycles later
    output reg  [S_RD-1:0]        rq_v,
    output reg  [S_RD*14-1:0]     rq_row,
    input  wire [S_RD-1:0]        rs_v,
    input  wire [S_RD*512-1:0]    rs_d,
    // VM write slots
    output reg  [S_WR-1:0]        wq_v,
    output reg  [S_WR*14-1:0]     wq_row,
    output reg  [S_WR*16-1:0]     wq_mask,
    output reg  [S_WR*512-1:0]    wq_d,
    // status
    output wire                   busy,
    output reg                    fault,
    output reg  [3:0]             fault_code,
    output reg  [31:0]            st_jobs
);
    localparam integer N    = 4 * NG;
    localparam integer NR   = D / NG;                 // resident rows a slot
    localparam integer NV   = NR / 4;                 // norm vectors
    localparam integer RW_H = NG * 4 * 16;            // resident row bits
    localparam integer HROWS = NR * NG / 8;           // VM rows of a BF16-packed h
    localparam integer PPR  = NG / 8;                 // VM rows a resident row
    localparam integer CROWS = (N / 64) > 0 ? N / 64 : 1;          // code rows a vector
    localparam integer EROWS = (N + 1023) / 1024;                  // exp rows a vector
    localparam integer YROWS = N / 32;                             // y rows a vector
    localparam integer GROWS = D / 16;                             // gain rows
    localparam integer GPV  = N / 16;                              // gain rows a norm vector
    localparam integer OW   = 14 + 512;
    localparam integer OQB  = $clog2(OQ);
`ifndef SYNTHESIS
    initial begin
        if (D % N != 0) $fatal(1, "ot_s81_hc_core: D a multiple of 4 NG");
        if (NG % 64 != 0 && NG != 16 && NG != 32) $fatal(1, "ot_s81_hc_core: NG a multiple of 64 (or 16 / 32 for reduced benches)");
        if (S_RD < 1 || S_WR < 1) $fatal(1, "ot_s81_hc_core: slots >= 1");
    end
`endif

    // ------------------------------------------------------------------ job intake
    localparam [2:0] K_HLOAD = 0, K_HSTORE = 1, K_COEF = 2, K_POST = 3, K_NORM = 4, K_GAIN = 5;
    reg         run;
    reg  [2:0]  kind;
    reg         jslot;
    reg  [7:0]  jtag;
    reg  [13:0] base;
    reg  [1:0]  gsel;
    reg         f_q, f_y;
    assign e_cmd_ready = !run && !fault;
    assign busy = run;
    wire take = e_cmd_v && e_cmd_ready;
    wire [23:0] c_arg = e_cmd_d[30:7];
    // h slot used by the job (MUT 2: the compute jobs -- POST / NORM -- address the other slot's h; H_LOAD / H_STORE
    // keep the right one, so the mutant is not a consistent renaming of the slots)
    wire        hs = (MUT == 2 && (kind == K_POST || kind == K_NORM)) ? ~jslot : jslot;

    // ------------------------------------------------------------------ resident state
    reg [RW_H-1:0] hb0 [0:2*NV-1];
    reg [RW_H-1:0] hb1 [0:2*NV-1];
    reg [RW_H-1:0] hb2 [0:2*NV-1];
    reg [RW_H-1:0] hb3 [0:2*NV-1];
    reg [16*32-1:0] cf_comb [0:1];
    reg [4*32-1:0]  cf_pre  [0:1];
    reg [4*32-1:0]  cf_post [0:1];
    reg [31:0]      cf_eps  [0:1];
    reg [N*32-1:0]  gtab [0:4*NV-1];                     // gain set s, vector v at s*NV + v

    // resident row read (combinational index, registered data)
    function automatic [RW_H-1:0] hrow_rd(input integer b, input integer s);
        integer ix;
        begin
            ix = s * NV + b / 4;
            case (b % 4)
                0: hrow_rd = hb0[ix];
                1: hrow_rd = hb1[ix];
                2: hrow_rd = hb2[ix];
                default: hrow_rd = hb3[ix];
            endcase
        end
    endfunction

    // ------------------------------------------------------------------ counters
    reg [15:0] ci;          // issue counter (rows / beats / vectors)
    reg [15:0] cr;          // completion counter (responses / outputs)
    reg [15:0] cw;          // writes issued
    reg [15:0] nw;          // writes expected

    // ------------------------------------------------------------------ VM read responses (in order, slot = index % S_RD)
    // a response of request n lands in slot n % S_RD; responses of one cycle are taken in slot order
    reg [512*32-1:0] asm_r;                              // up to 32 VM rows of one resident row
    // ------------------------------------------------------------------ hc_post
    reg               hp_go, hp_in_v;
    reg [NG*4*32-1:0] hp_r;
    reg [NG*32-1:0]   hp_y;
    wire              hp_out_v, hp_fault;
    wire [NG*4*32-1:0] hp_out;
    reg [16*32-1:0]   hp_comb;
    reg [4*32-1:0]    hp_post;
    ot_dsrom_su_hcpost #(.NG(NG), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u_post (
        .clk(clk), .rst_n(rst_n), .go(hp_go), .comb(hp_comb), .post(hp_post), .in_v(hp_in_v), .in_r(hp_r), .in_y(hp_y),
        .out_v(hp_out_v), .out_d(hp_out), .fault(hp_fault));
    // ------------------------------------------------------------------ fused hc_pre -> RMSNorm -> act-quant
    reg               nm_go, nm_in_v, nm_wl_v;
    reg [7:0]         nm_wl_i;
    reg [N*32-1:0]    nm_wl_d;
    reg [4*N*32-1:0]  nm_x;
    reg [127:0]       nm_pre;
    reg [31:0]        nm_eps;
    wire              nm_y_v, nm_r_v, nm_q_v, nm_ro_v, nm_fault;
    wire [7:0]        nm_y_i, nm_q_i;
    wire [N*32-1:0]   nm_y, nm_ro;
    wire [31:0]       nm_r;
    wire [(N/32)*256-1:0] nm_qc;
    wire [(N/32)*10-1:0]  nm_qe;
    wire [(N/32)*512-1:0] nm_qy;
    localparam [31:0] NF = (D == 5120) ? 32'h45A00000 : (D == 1280) ? 32'h44A00000 : (D == 2560) ? 32'h45200000 :
                           (D == 640) ? 32'h44200000 : (D == 320) ? 32'h43A00000 : 32'h0;
    ot_dsrom_su_norm #(.N(N), .D(D), .HC(1), .RD(0), .QUANT(1), .LM(ML), .LA(AL)) u_norm (
        .clk(clk), .rst_n(rst_n), .go(nm_go), .in_v(nm_in_v), .in_x(nm_x), .pre(nm_pre), .n_f(NF), .eps(nm_eps),
        .wl_v(nm_wl_v), .wl_i(nm_wl_i), .wl_d(nm_wl_d), .cos_t(32'd0), .sin_t(32'd0),
        .y_v(nm_y_v), .y_i(nm_y_i), .y(nm_y), .r_v(nm_r_v), .r(nm_r), .q_v(nm_q_v), .q_i(nm_q_i), .q_codes(nm_qc),
        .q_e(nm_qe), .q_y(nm_qy), .ro_v(nm_ro_v), .ro(nm_ro), .fault(nm_fault));

    // norm x operand: lane l = j*NG + g of vector v is bank j's row index v, element g; copy k at [(k*N + l)*32]
    function automatic [4*N*32-1:0] norm_x(input [RW_H-1:0] r0, input [RW_H-1:0] r1, input [RW_H-1:0] r2,
                                           input [RW_H-1:0] r3);
        integer j, g, k;
        reg [RW_H-1:0] rr;
        begin
            norm_x = 0;
            for (j = 0; j < 4; j = j + 1) begin
                rr = (j == 0) ? r0 : (j == 1) ? r1 : (j == 2) ? r2 : r3;
                for (g = 0; g < NG; g = g + 1)
                    for (k = 0; k < 4; k = k + 1)
                        norm_x[(k * N + j * NG + g) * 32 +: 32] = {rr[16 * (4 * g + k) +: 16], 16'h0000};
            end
        end
    endfunction
    function automatic [NG*4*32-1:0] widen(input [RW_H-1:0] rr);
        integer q;
        begin
            for (q = 0; q < 4 * NG; q = q + 1) widen[32 * q +: 32] = {rr[16 * q +: 16], 16'h0000};
        end
    endfunction
    function automatic [RW_H-1:0] narrow(input [NG*4*32-1:0] w);
        integer q;
        begin
            for (q = 0; q < 4 * NG; q = q + 1) narrow[16 * q +: 16] = w[32 * q + 16 +: 16];
        end
    endfunction
    function automatic lo_nz(input [NG*4*32-1:0] w);
        integer q;
        begin
            lo_nz = 1'b0;
            for (q = 0; q < 4 * NG; q = q + 1) lo_nz = lo_nz | (|w[32 * q +: 16]);
        end
    endfunction

    // ------------------------------------------------------------------ norm output row FIFO
    reg [OW-1:0]  oq [0:OQ-1];
    reg [OQB:0]   oq_n;
    reg [OQB-1:0] oq_w, oq_r;

    // ------------------------------------------------------------------ main sequencer
    integer s, q, k, gg;
    reg [15:0] post_ob;                                    // POST output beats written back
    reg [15:0] norm_out_vecs;
    assign y_rdy = run && (kind == K_POST) && (ci < NR) && !fault;
    wire y_take = y_v && y_rdy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; kind <= 0; jslot <= 0; jtag <= 0; base <= 0; gsel <= 0; f_q <= 0; f_y <= 0;
            e_done_v <= 1'b0; e_done_tag <= 0; fault <= 1'b0; fault_code <= 0; st_jobs <= 0;
            ci <= 0; cr <= 0; cw <= 0; nw <= 0;
            rq_v <= 0; wq_v <= 0; hp_go <= 0; hp_in_v <= 0; nm_go <= 0; nm_in_v <= 0; nm_wl_v <= 0; nm_wl_i <= 0;
            oq_n <= 0; oq_w <= 0; oq_r <= 0; post_ob <= 0; norm_out_vecs <= 0;
        end else begin
            e_done_v <= 1'b0;
            rq_v <= 0; wq_v <= 0; hp_go <= 1'b0; hp_in_v <= 1'b0; nm_go <= 1'b0; nm_in_v <= 1'b0; nm_wl_v <= 1'b0;
            if (hp_fault || nm_fault) begin fault <= 1'b1; if (!fault) fault_code <= 4'd1; end
            if (rs_v != 0 && !(run && (kind == K_HLOAD || kind == K_COEF || kind == K_GAIN))) begin
                fault <= 1'b1; if (!fault) fault_code <= 4'd2;           // a VM response nobody asked for
            end
            if (y_v && !y_rdy && !(run && kind == K_POST)) begin
                // y offered while no POST runs: held by the producer (valid/ready), not an error
            end
            // ---------------------------------------------------------- accept
            if (take) begin
                run <= 1'b1; kind <= c_arg[22:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                base <= c_arg[13:0]; gsel <= c_arg[19:18]; f_q <= c_arg[14]; f_y <= c_arg[15];
                ci <= 0; cr <= 0; cw <= 0; post_ob <= 0; norm_out_vecs <= 0;
                if (c_arg[23] || c_arg[22:20] > 3'd5 || (c_arg[22:20] == K_NORM && !c_arg[14] && !c_arg[15])) begin
                    fault <= 1'b1; fault_code <= 4'd3;
                end
                nw <= (c_arg[22:20] == K_HSTORE) ? HROWS :
                      (c_arg[22:20] == K_NORM) ? (c_arg[14] ? NV * (CROWS + EROWS) : 0) + (c_arg[15] ? NV * YROWS : 0) : 0;
            end
            // ---------------------------------------------------------- per kind
            if (run && !fault) begin
                case (kind)
                K_HLOAD, K_COEF, K_GAIN: begin
                    // issue
                    for (s = 0; s < S_RD; s = s + 1)
                        if (ci + s < ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            rq_v[s] <= 1'b1; rq_row[14 * s +: 14] <= base + ci + s;
                        end
                    ci <= ci + S_RD;
                    // complete (responses in slot order)
                    begin : rsp
                        reg [15:0] c;
                        c = cr;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin
                                if (kind == K_HLOAD) begin
                                    asm_r[512 * (c % PPR) +: 512] = rs_d[512 * s +: 512];
                                    if (c % PPR == PPR - 1)
                                        case ((c / PPR) % 4)
                                            0: hb0[hs * NV + (c / PPR) / 4] <= asm_r[RW_H-1:0];
                                            1: hb1[hs * NV + (c / PPR) / 4] <= asm_r[RW_H-1:0];
                                            2: hb2[hs * NV + (c / PPR) / 4] <= asm_r[RW_H-1:0];
                                            default: hb3[hs * NV + (c / PPR) / 4] <= asm_r[RW_H-1:0];
                                        endcase
                                end else if (kind == K_COEF) begin
                                    if (c == 0) cf_comb[jslot] <= rs_d[512 * s +: 512];
                                    else begin
                                        cf_pre[jslot]  <= rs_d[512 * s +: 128];
                                        cf_post[jslot] <= rs_d[512 * s + 128 +: 128];
                                        cf_eps[jslot]  <= rs_d[512 * s + 256 +: 32];
                                    end
                                end else begin
                                    gtab[gsel * NV + c / GPV][512 * (c % GPV) +: 512] <= rs_d[512 * s +: 512];
                                end
                                c = c + 1;
                            end
                        cr <= c;
                        if (c == ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                            st_jobs <= st_jobs + 1;
                        end
                    end
                end
                K_HSTORE: begin
                    for (s = 0; s < S_WR; s = s + 1)
                        if (cw + s < HROWS) begin
                            wq_v[s] <= 1'b1; wq_row[14 * s +: 14] <= base + cw + s; wq_mask[16 * s +: 16] <= 16'hFFFF;
                            wq_d[512 * s +: 512] <= hrow_rd((cw + s) / PPR, hs) >> (512 * ((cw + s) % PPR));
                        end
                    cw <= cw + S_WR;
                    if (cw + S_WR >= HROWS - ((MUT == 4) ? S_WR : 0)) begin
                        run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                        st_jobs <= st_jobs + 1;
                    end
                end
                K_POST: begin
                    if (y_take) begin
                        hp_in_v <= 1'b1; hp_go <= (ci == 0);
                        hp_r <= widen(hrow_rd(ci, hs)); hp_y <= y_d;
                        hp_comb <= cf_comb[jslot]; hp_post <= cf_post[jslot];
                        ci <= ci + 1;
                    end
                    if (hp_out_v) begin
                        if (lo_nz(hp_out)) begin fault <= 1'b1; fault_code <= 4'd4; end   // hc_post output not BF16
                        if (MUT != 1)
                            case (post_ob % 4)
                                0: hb0[hs * NV + post_ob / 4] <= narrow(hp_out);
                                1: hb1[hs * NV + post_ob / 4] <= narrow(hp_out);
                                2: hb2[hs * NV + post_ob / 4] <= narrow(hp_out);
                                default: hb3[hs * NV + post_ob / 4] <= narrow(hp_out);
                            endcase
                        post_ob <= post_ob + 1;
                        if (post_ob + 1 == NR - ((MUT == 4) ? 1 : 0)) begin
                            run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                            st_jobs <= st_jobs + 1;
                        end
                    end
                end
                K_NORM: begin
                    if (MUT == 3) begin
                        run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= jtag; st_jobs <= st_jobs + 1;
                    end else begin
                        // gain load (NV cycles), then the NV operand vectors
                        if (ci < NV) begin
                            nm_wl_v <= 1'b1; nm_wl_i <= ci[7:0]; nm_wl_d <= gtab[gsel * NV + ci];
                            ci <= ci + 1;
                        end else if (ci == NV) begin
                            // go a cycle ahead of the first vector (ot_dsrom_su_norm clears its vector index on go)
                            nm_go <= 1'b1; nm_pre <= cf_pre[jslot]; nm_eps <= cf_eps[jslot];
                            ci <= ci + 1;
                        end else if (ci < 2 * NV + 1) begin
                            nm_in_v <= 1'b1;
                            nm_x <= norm_x(hb0[hs * NV + ci - NV - 1], hb1[hs * NV + ci - NV - 1],
                                           hb2[hs * NV + ci - NV - 1], hb3[hs * NV + ci - NV - 1]);
                            ci <= ci + 1;
                        end
                        // outputs -> row FIFO
                        begin : outp
                            reg [OQB:0] n_in;
                            reg [OQB-1:0] wp;
                            n_in = 0; wp = oq_w;
                            if (nm_q_v && f_q) begin
                                for (q = 0; q < CROWS; q = q + 1) begin
                                    oq[wp] <= {base + nm_q_i * CROWS + q, nm_qc[512 * q +: 512]}; wp = wp + 1; n_in = n_in + 1;
                                end
                                for (q = 0; q < EROWS; q = q + 1) begin
                                    reg [511:0] er;
                                    er = 0;
                                    for (gg = 0; gg < 32 && q * 32 + gg < N / 32; gg = gg + 1)
                                        er[16 * gg +: 16] = {6'd0, nm_qe[10 * (q * 32 + gg) +: 10]};
                                    oq[wp] <= {base + NV * CROWS + nm_q_i * EROWS + q, er}; wp = wp + 1; n_in = n_in + 1;
                                end
                            end
                            if (nm_y_v && f_y) begin
                                for (q = 0; q < YROWS; q = q + 1) begin
                                    reg [511:0] yr;
                                    for (gg = 0; gg < 32; gg = gg + 1) yr[16 * gg +: 16] = nm_y[32 * (32 * q + gg) + 16 +: 16];
                                    oq[wp] <= {base + (f_q ? NV * (CROWS + EROWS) : 0) + nm_y_i * YROWS + q, yr};
                                    wp = wp + 1; n_in = n_in + 1;
                                end
                            end
                            // drain S_WR rows a cycle
                            begin : drn
                                reg [OQB:0] n_out;
                                reg [OQB-1:0] rp;
                                n_out = 0; rp = oq_r;
                                for (s = 0; s < S_WR; s = s + 1)
                                    if (n_out < oq_n) begin
                                        wq_v[s] <= 1'b1; wq_row[14 * s +: 14] <= oq[rp][OW-1:512]; wq_mask[16 * s +: 16] <= 16'hFFFF;
                                        wq_d[512 * s +: 512] <= oq[rp][511:0]; rp = rp + 1; n_out = n_out + 1;
                                    end
                                oq_r <= rp;
                                oq_n <= oq_n + n_in - n_out;
                                if (oq_n + n_in > OQ) begin fault <= 1'b1; fault_code <= 4'd5; end
                                cw <= cw + n_out;
                                if (cw + n_out >= nw - ((MUT == 4) ? S_WR : 0) && ci == 2 * NV + 1) begin
                                    run <= 1'b0; e_done_v <= 1'b1; e_done_tag <= (MUT == 5) ? (jtag ^ 8'h01) : jtag;
                                    st_jobs <= st_jobs + 1;
                                end
                            end
                            oq_w <= wp;
                        end
                    end
                end
                default: ;
                endcase
            end
        end
    end
endmodule
