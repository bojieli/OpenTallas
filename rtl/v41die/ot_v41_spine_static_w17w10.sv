// Additive current serialized baseline provider hook; exact RT_CUT-compatible engine.
// Experimental companion: FAST/PP/BP default off; no adoption or clock claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_spine_w17w10: the ROM-field front end of an experimental V4.1 FAST/PP runtime baseline (W17; root decisions 2026-09-30
// (a)-(c)).  One weight PHASE at a time (tools/v41_rom_ksplit_bankmap.py: one or more matrices that share
// one x vector and one x family):
//
//   CFG     broadcast {cfg_go, phase, positions - 1}; every element loads its own configuration from its
//           configuration ROM (ot_v41_pair_w17w10) in CW + 2 cycles, in parallel.
//   GO      pulse go / go_bf to every element.
//   LOAD    read x from the vector memory, VRD elements a cycle (the model's vm_read_elems = 64), in K
//           order, one position after another; FP8 family: quantise every 32-block exactly as golden
//           quant_fp8 (two ot_hdc_actquant, II = 1) into the block buffer {codes, exponent}; BF16 family:
//           round to BF16 (RNE) into the lane buffer.
//   STREAM  from the phase's STREAM ROM (a static schedule, the bank map's rounds: tools/v41_die_images.py)
//           one x beat a cycle; a beat waits (idle beat) until every x element it carries is loaded.
//           Elements only consume beats, so an idle beat is always safe.
//   RETURN  the R region roots' finished rows are written to the vector memory, one row per root per cycle:
//           row n of position p at obase + rbase(n) + n + p*ops, as BF16 (upper half of the 32-bit word,
//           the golden's to_bf16 value) or FP32 by the phase's row format.
//   DONE    when the phase's rows * positions have all been written.
//
// The broadcast (cfg and beats) passes BST wire register stages before it leaves the spine; the field
// sees it at the stage outputs (so a flat field and the runtime composition see the same wires).
//
// PHASE ROM word (64 bits): [0] bf16 family, [13:1] K, [29:14] stream beats per position,
//   [45:30] stream ROM base, [61:46] rows per position, [62] fmt of rows < rsplit (1 = FP32),
//   [63] fmt of rows >= rsplit.  PHASE ROM word 2 (at 2*ph + 1): [15:0] rsplit.
// STREAM ROM word (48 bits): FP8/FP4 {[0] v, [8:1] pair u, [11:9] block b, [13:12] slot valids};
//   BF16 {[0] v, [3:1] b, [7:4] slot valids, [39:8] four 8-bit units}.
// ---------------------------------------------------------------------------
module ot_v41_spine_static_w17w10 #(
    parameter integer PHW = 10,
    parameter integer STATIC_CONTROLS = 0,
    parameter integer CONTROL_STAGE = 37,
    parameter integer SAW = 14,          // stream ROM words (log2)
    parameter integer R = 2,             // return regions
    parameter integer VAW = 19,          // vector memory element address
    parameter integer VRD = 64,          // x elements read a cycle
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer NSEG = 8,
    // derived: broadcast bus width
    parameter integer BW = 1 + PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024
) (
    input  wire              clk,
    input  wire              rst_n,
    // op
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,         // positions - 1
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    input  wire [1:0]        i_fmt,        // row format: 0 the phase ROM's, 1 all FP32, 2 all BF16
    output wire              ready,
    output wire              idle,
    // vector memory: x read (VRD consecutive elements, registered response next cycle)
    output reg               x_re,
    output reg  [VAW-1:0]    x_addr,
    input  wire [VRD*32-1:0] x_q,
    // vector memory: row writes, one per region
    output reg  [R-1:0]      w_we,
    output reg  [R*VAW-1:0]  w_addr,
    output reg  [R*32-1:0]   w_data,
    // field broadcast (after the BST stages)
    output wire              f_cfg_go,
    output wire [PHW-1:0]    f_cfg_ph,
    output wire [2:0]        f_cfg_np,
    output wire              f_go,
    output wire              f_go_bf,
    output wire              f_xs_v,
    output wire [7:0]        f_xs_p,
    output wire [2:0]        f_xs_b,
    output wire [1:0]        f_xs_sv,
    output wire [255:0]      f_xs_q0,
    output wire [9:0]        f_xs_e0,
    output wire [255:0]      f_xs_q1,
    output wire [9:0]        f_xs_e1,
    output wire [2:0]        f_xs_pos,
    output wire [2:0]        f_xb_pos,
    output wire              f_xb_v,
    output wire [2:0]        f_xb_b,
    output wire [3:0]        f_xb_sv,
    output wire [31:0]       f_xb_u,
    output wire [1023:0]     f_xb_d,
    output wire [BW-1:0]     f_bus,        // the same broadcast as one bus (runtime-composition cut)
    // field return (region roots)
    input  wire [R-1:0]      r_v,
    input  wire [16*R-1:0]   r_row,
    input  wire [3*R-1:0]    r_pos,
    input  wire [32*R-1:0]   r_fp32,
    input  wire [16*R-1:0]   r_bf16,
    input  wire [R-1:0]      r_e,
    input  wire              f_fault,
    output reg               fault,
    output reg  [31:0]       phase_cycles     // cycles of the last phase (go to done)
);
    localparam integer CW = 3 * NSEG + 1;
    localparam integer NBLK = KMAX / 32;
    localparam integer BAW = $clog2(NBLK);
    localparam integer NBU = KMAX / 128;         // BF16 units (16 lanes x 8 elements)
    // ------------------------------------------------------------------ ROMs
    reg [63:0] phrom [0:(2 << PHW)-1] /*verilator public_flat_rw*/;
    reg [47:0] strom [0:(1 << SAW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial if (STATIC_CONTROLS == 0) begin
        for (ii = 0; ii < (2 << PHW); ii = ii + 1) phrom[ii] = 64'd0;
        for (ii = 0; ii < (1 << SAW); ii = ii + 1) strom[ii] = 48'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) begin
            $readmemh({rom_dir, "/spine_phase.hex"}, phrom);
            $readmemh({rom_dir, "/spine_stream.hex"}, strom);
        end
    end
    // ------------------------------------------------------------------ op state
    localparam [2:0] S_IDLE = 3'd0, S_CFG = 3'd1, S_GO = 3'd2, S_RUN = 3'd3;
    reg [2:0] st;
    reg [PHW-1:0] ph;
    reg [2:0] np;
    reg [VAW-1:0] xbase, xps, obase, ops;
    reg [1:0] fmt;
    reg [63:0] pw;
    reg [15:0] rsplit;
    wire       fam = pw[0];
    wire [13:0] kk = {1'b0, pw[13:1]};
    wire [15:0] nbeat = pw[29:14];
    wire [15:0] sbase = pw[45:30];
    wire [15:0] nrow = pw[61:46];
    reg [5:0] cfg_cnt;
    reg [31:0] cyc;
    reg [18:0] rows_left;
    assign ready = st == S_IDLE;
    assign idle = st == S_IDLE;

    // ------------------------------------------------------------------ loader
    reg        ld_run;
    reg [2:0]  ld_pos;
    reg [13:0] ld_k;                             // next element to read in this position
    reg        rq_v;                             // read issued last cycle
    reg [2:0]  rq_pos;
    reg [13:0] rq_k;
    reg [13:0] is_k;                             // read being issued (x_re)
    reg [2:0]  is_pos;
    // quantisers (FP8 family): two 32-blocks a cycle
    wire [1:0] aq_vo, aq_f;
    wire [511:0] aq_q;
    wire [19:0]  aq_e;
    genvar gq;
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_aq
        wire [511:0] unused_y;
        wire signed [9:0] e1;
        ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(rq_v && !fam), .fp4(1'b0),
            .x(x_q[1024*gq +: 1024]), .vo(aq_vo[gq]), .q(aq_q[256*gq +: 256]), .e(e1), .y(unused_y),
            .fault(aq_f[gq]));
        assign aq_e[10*gq +: 10] = e1;
    end endgenerate
    // the quantiser's block index and position, in step with its 13-cycle pipe
    wire [BAW-1:0] aq_blk;
    wire [2:0]     aq_pos;
    ot_hdc_delay #(.W(BAW + 3), .D(13)) u_aqi (.clk(clk), .rst_n(rst_n), .d({rq_k[BAW+4:5], rq_pos}),
                                              .q({aq_blk, aq_pos}));
    // buffers: position-major (one position's x at a time is streamed; positions reuse by parity)
    reg [255:0] qb [0:2*NBLK-1];                 // [parity][block] codes
    reg [9:0]   eb [0:2*NBLK-1];
    reg [15:0]  bb [0:2*KMAX-1];                 // [parity][element] BF16
    // loaded counts (elements available) per position parity
    reg [14:0] have [0:1];
    // ------------------------------------------------------------------ streamer
    reg        sm_run;
    reg [2:0]  sm_pos;
    reg [15:0] sm_i;
    reg [47:0] sw;                               // current stream word (registered ROM read)
    reg        sw_v;                             // sw holds beat sm_i of sm_pos
    // elements a beat needs loaded (exclusive bound)
    wire [7:0] u  = sw[8:1];
    wire [2:0] b  = sw[11:9];
    wire [1:0] sv = sw[13:12];
    wire [14:0] need_q = sv[1] ? ({u, 1'b1, b, 5'd0} + 15'd32) : ({u, 1'b0, b, 5'd0} + 15'd32);
    reg [7:0] umax;
    integer kb;
    always @* begin
        umax = 8'd0;
        for (kb = 0; kb < 4; kb = kb + 1) if (sw[4 + kb] && sw[8 + 8*kb +: 8] > umax) umax = sw[8 + 8*kb +: 8];
    end
    wire [14:0] need_b = {umax, 7'd0} + 15'd128;
    wire        s_ok = !sw[0] || ((fam ? need_b : need_q) <= have[sm_pos[0]]);
    wire        s_adv = sm_run && sw_v && s_ok;
    wire        s_last = sm_i + 16'd1 == nbeat;
    wire [63:0] control_pq0, control_pq1;
    wire [47:0] control_sq;
    wire [SAW-1:0] control_sa=SAW'(sbase)+SAW'(!sw_v ? sm_i : (s_last ? 16'd0 : sm_i+16'd1));
    generate if (STATIC_CONTROLS != 0) begin : g_static_controls
        if (PHW != 10 || SAW != 14) begin : g_bad_shape
            initial $fatal(1,"Static canonical field controls require PHW10 SAW14");
        end
        if (CONTROL_STAGE == 37) begin : g_stage37
            ot_v41_stage37_control_rom u_controls(.phase(i_ph),.stream_addr(control_sa),.pq0(control_pq0),.pq1(control_pq1),.sq(control_sq));
        end else if (CONTROL_STAGE == 38) begin : g_stage38
            ot_v41_stage38_control_rom u_controls(.phase(i_ph),.stream_addr(control_sa),.pq0(control_pq0),.pq1(control_pq1),.sq(control_sq));
        end else begin : g_bad_stage
            initial $fatal(1,"Static canonical stage not source-bound");
        end
    end else begin : g_runtime_controls
        assign control_pq0=phrom[{i_ph,1'b0}];assign control_pq1=phrom[{i_ph,1'b1}];
        assign control_sq=strom[control_sa];
    end endgenerate

    // beat assembly
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p;
    reg [2:0]   bt_b;
    reg [1:0]   bt_sv;
    reg [255:0] bt_q0, bt_q1;
    reg [9:0]   bt_e0, bt_e1;
    reg [2:0]   bt_pos;
    reg [3:0]   bt_bsv;
    reg [31:0]  bt_u;
    reg [1023:0] bt_d;
    reg         bt_go, bt_gobf, bt_cfg;
    // block (2u + h) * 8 + b of the streamer's position parity
    wire [15:0] blk0 = (sm_pos[0] ? 16'(NBLK) : 16'd0) + {5'd0, u, 1'b0, b};
    wire [15:0] blk1 = (sm_pos[0] ? 16'(NBLK) : 16'd0) + {5'd0, u, 1'b1, b};
    integer kl, ku;
    always @(posedge clk) begin
        bt_p <= u; bt_b <= fam ? sw[3:1] : b; bt_sv <= sv; bt_pos <= sm_pos;
        bt_q0 <= sv[0] ? qb[blk0] : 256'd0; bt_e0 <= sv[0] ? eb[blk0] : 10'd0;
        bt_q1 <= sv[1] ? qb[blk1] : 256'd0; bt_e1 <= sv[1] ? eb[blk1] : 10'd0;
        bt_bsv <= sw[7:4];
        bt_u <= sw[39:8];
        for (ku = 0; ku < 4; ku = ku + 1)
            for (kl = 0; kl < 16; kl = kl + 1)
                bt_d[256*ku + 16*kl +: 16] <= sw[4 + ku] ?
                    bb[(sm_pos[0] ? 16'(KMAX) : 16'd0) + {1'b0, sw[8 + 8*ku +: 8], 7'd0} + 16'(kl * 8) + {13'd0, sw[3:1]}] : 16'd0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin bt_xs_v <= 1'b0; bt_xb_v <= 1'b0; end
        else begin
            bt_xs_v <= s_adv && sw[0] && !fam;
            bt_xb_v <= s_adv && sw[0] && fam;
        end
    end
    // ------------------------------------------------------------------ broadcast wire stages
    wire [BW-1:0] bc_in = {bt_cfg, ph, np, bt_go, bt_gobf, bt_xs_v, bt_p, bt_b, bt_sv, bt_q0, bt_e0, bt_q1, bt_e1,
                           bt_pos, bt_pos, bt_xb_v, bt_b, bt_bsv, bt_u, bt_d};
    wire [BW-1:0] bc;
    generate if (BST > 0) begin : g_bst
        ot_hdc_delay #(.W(BW), .D(BST), .RESET(1)) u_bst (.clk(clk), .rst_n(rst_n), .d(bc_in), .q(bc));
    end else begin : g_nobst
        assign bc = bc_in;
    end endgenerate
    assign {f_cfg_go, f_cfg_ph, f_cfg_np, f_go, f_go_bf, f_xs_v, f_xs_p, f_xs_b, f_xs_sv, f_xs_q0, f_xs_e0, f_xs_q1,
            f_xs_e1, f_xs_pos, f_xb_pos, f_xb_v, f_xb_b, f_xb_sv, f_xb_u, f_xb_d} = bc;
    assign f_bus = bc;

    // ------------------------------------------------------------------ control
    integer kr;
    reg [R-1:0] rv_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; fault <= 1'b0; bt_go <= 1'b0; bt_gobf <= 1'b0; bt_cfg <= 1'b0;
            ld_run <= 1'b0; rq_v <= 1'b0; sm_run <= 1'b0; sw_v <= 1'b0; x_re <= 1'b0;
            have[0] <= 15'd0; have[1] <= 15'd0; w_we <= {R{1'b0}}; phase_cycles <= 32'd0; cyc <= 32'd0;
            rows_left <= 19'd0;
        end else begin
            bt_go <= 1'b0; bt_gobf <= 1'b0; bt_cfg <= 1'b0;
            cyc <= cyc + 32'd1;
            if (f_fault || (|aq_f)) fault <= 1'b1;
            // rows still to write: loaded when the elements start, then one per written row
            if (st == S_CFG && cfg_cnt == 6'(CW + 1)) rows_left <= 19'(nrow) * (19'(np) + 19'd1);
            else rows_left <= rows_left - 19'($countones(r_v));
            case (st)
                S_IDLE: if (go) begin
                    ph <= i_ph; np <= i_np; xbase <= i_xbase; xps <= i_xps; obase <= i_obase; ops <= i_ops; fmt <= i_fmt;
                    pw <= control_pq0; rsplit <= control_pq1[15:0];
                    st <= S_CFG; bt_cfg <= 1'b1; cfg_cnt <= 6'd0; cyc <= 32'd0;
                end
                S_CFG: begin
                    cfg_cnt <= cfg_cnt + 6'd1;
                    // the elements load CW words (ROM read + register): go after the last one is written
                    if (cfg_cnt == 6'(CW + 1)) begin
                        st <= S_GO; bt_go <= 1'b1; bt_gobf <= fam;
                    end
                end
                S_GO: begin
                    st <= S_RUN;
                    ld_run <= 1'b1; ld_pos <= 3'd0; ld_k <= 14'd0; have[0] <= 15'd0; have[1] <= 15'd0;
                    sm_run <= 1'b1; sm_pos <= 3'd0; sm_i <= 16'd0; sw_v <= 1'b0;
                end
                S_RUN: if (rows_left == 19'd0 && !sm_run && !ld_run) begin
                    st <= S_IDLE; phase_cycles <= cyc;
                end
                default: st <= S_IDLE;
            endcase
            // loader: VRD elements a cycle in K order, position after position; the streamer's position
            // parity buffer is reused only after its beats are all sent (positions are streamed in order)
            // rq_*: the read issued last cycle (its data arrives this cycle)
            x_re <= 1'b0; rq_v <= x_re; rq_k <= is_k; rq_pos <= is_pos;
            if (ld_run && !(ld_pos != sm_pos && ld_pos[0] == sm_pos[0])) begin
                x_re <= 1'b1; is_k <= ld_k; is_pos <= ld_pos;
                x_addr <= xbase + VAW'(ld_pos) * xps + VAW'(ld_k);
                if (ld_k + 14'(VRD) >= kk) begin
                    ld_k <= 14'd0;
                    if (ld_pos == np) ld_run <= 1'b0;
                    ld_pos <= ld_pos + 3'd1;
                end else ld_k <= ld_k + 14'(VRD);
            end
            // loaded counts: BF16 on the read response, FP8 on the quantiser output (two blocks)
            if (fam && rq_v) have[rq_pos[0]] <= 15'(rq_k) + 15'(VRD);
            if (!fam && aq_vo[0]) have[aq_pos[0]] <= {aq_blk, 5'd0} + 15'd64;
            // streamer: ROM word register, then the beat when its x is loaded
            if (sm_run) begin
                if (!sw_v) begin
                    sw <= control_sq; sw_v <= 1'b1;
                end else if (s_ok) begin
                    if (s_last) begin
                        sm_i <= 16'd0;
                        if (sm_pos == np) sm_run <= 1'b0;
                        else begin
                            sm_pos <= sm_pos + 3'd1;
                            have[sm_pos[0]] <= 15'd0;
                        end
                    end else sm_i <= sm_i + 16'd1;
                    sw <= control_sq;
                end
            end
            // rows
            w_we <= {R{1'b0}};
            for (kr = 0; kr < R; kr = kr + 1) if (r_v[kr]) begin
                w_we[kr] <= 1'b1;
                w_addr[VAW*kr +: VAW] <= obase + VAW'(r_row[16*kr +: 16]) + VAW'(r_pos[3*kr +: 3]) * ops;
                w_data[32*kr +: 32] <= ((fmt == 2'd1) || (fmt == 2'd0 && ((r_row[16*kr +: 16] < rsplit) ? pw[62] : pw[63])))
                                       ? r_fp32[32*kr +: 32]
                                                                                         : {r_bf16[16*kr +: 16], 16'd0};
                if (r_e[kr]) fault <= 1'b1;
            end
        end
    end
    // buffers
    integer kw;
    always @(posedge clk) begin
        if (!fam && aq_vo[0]) begin
            qb[(aq_pos[0] ? NBLK : 0) + 32'(aq_blk)] <= aq_q[255:0];       eb[(aq_pos[0] ? NBLK : 0) + 32'(aq_blk)] <= aq_e[9:0];
            qb[(aq_pos[0] ? NBLK : 0) + 32'(aq_blk) + 1] <= aq_q[511:256]; eb[(aq_pos[0] ? NBLK : 0) + 32'(aq_blk) + 1] <= aq_e[19:10];
        end
        if (fam && rq_v)
            for (kw = 0; kw < VRD; kw = kw + 1)
                bb[(rq_pos[0] ? KMAX : 0) + 32'(rq_k) + kw] <= x_q[32*kw + 16 +: 16] +
                    {15'd0, x_q[32*kw + 15] & ((x_q[32*kw +: 15] != 15'd0) | x_q[32*kw + 16])};
    end
endmodule
