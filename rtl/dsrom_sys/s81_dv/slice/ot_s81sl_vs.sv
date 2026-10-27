`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17; helper S81-SLICE-SU): vs = the SU lane engine of one BEAT leaf of a DV vector slice
// (x5 per slice, own clock root).  It runs the central S81 SU's element ops on the beat leaf's rows: the leaf store
// lives in vp; vs reads and writes it through vp's extension port (one row-pair read and one row-pair write a cycle at
// most, in compiler slots that never meet a vp op) and streams act-quant inputs to vq's second input (u / um).
// Sub-leaves it drives (each its own master and clock root, registered pins both sides; measured flops in the header of
// tools/s81_slice/vs_bench.sh):
//   ot_s81sl_vsw               one hub SwiGLU lane (ot_s81_su_swl, unchanged: ~14k flops, so it cannot share vs's root)
//   ot_s81_su_rxsf -> _rxsb    the closed hub RA lane pair (sqrt(softplus); front / back leaves dsfd_su_t_rxsf / _rxsb)
//
// Commands: vp forwards ops 8..15 unchanged (s_v / s_d, one edge).  s_d = {imm 128, n 8, a1 10, a0 10, op 4};
//   imm[9:0] ob (result row base)   imm[10] wb (write results)   imm[11] uq (stream to vq)   imm[12] / [13] um_q / um_b
//   imm[21:14] um_i (the vector's global beat index for vq)  imm[24:22] j0 (first vq sub-beat)
//   imm[63:32] lim   imm[95:64] w0 (groups 0..7)   imm[127:96] w1 (groups 8..15)            (SW only)
//   imm[25] wr, imm[28:26] wsel (SW only; TOK-S81-GAPS 10-18): w0 = w1 = FP32 word wsel of the leaf-store row pair a1
//           (the gunit router's weights rows R+1 / R+2, CTL target 5).  The weight row pair is read at step 0, the groups
//           follow 4 edges later on the same SW cadence (fixed timeline, +4 edges; no handshake).  wr = 0: imm w0 / w1.
// ONE op runs at a time, from its command to its last result: a command while busy, op 14 / 15, or a malformed count is
// a sticky fault (the compiler schedules every op on its measured fixed timeline; nothing waits or arbitrates).
// Operand layouts are compiler-fixed: a read is the row pair (a0 + 2 s, a0 + 2 s + 1) = x_qd[127:0], x_qd[255:128].
//   8  SW   n groups (<= 16, 4 elements each), one read every 4 cycles: row a0 + 2 s = g[4 s ..], a0 + 2 s + 1 = u[4 s ..]
//           -> vsw: a = BF16(w * (silu(min(g, lim)) * clip(u, -lim, lim))), the hub lane's units and order.  w = w0 for
//           groups 0..7, w1 for 8..15 (one 32-element act-quant block each; the shared expert: w = 1.0, exact).
//           wb: row ob + s (FP32 words holding BF16);  uq: groups 2 i, 2 i + 1 -> vq sub-beat j0 + i; um at the command.
//   9  QB   n sub-beats (j0 + n <= 8): row pair a0 + 2 s -> vq sub-beat j0 + s unchanged (z_quant: vq's ot_dsrom_aq12
//           is the golden act-quant; su_gate qb() has no other step).  um at the command.
//   10 RA   n elements: rows a0 .. (8 a read, one read every 8 cycles) -> r = sqrt(softplus(x)) one a cycle on the RA
//           lane pair (ra_* pins) -> rows ob + i / 4 (FP32; the last row word-masked).
//   11 RB   n rows: row a0 + 2 s = scores, a0 + 2 s + 1 = bias -> scores + bias (ot_dsrom_qadd, 4 lanes) -> row ob + s.
//   12 QR   n rows, one read every 2 cycles: row a0 + 2 s = q[4 s .. 4 s + 3] (2 adjacent pairs), a0 + 2 s + 1 =
//           {c, s, c', s'} of the two pairs -> rope_tail (re = a c - b s, im = b c + a s: 2 ot_hdc_qmul_lat + 1
//           ot_dsrom_qadd a lane, the hub ot_s81_su_rxqr lane; one pair a cycle on 2 lanes), BF16 -> row ob + s.
//   13 MOE  n = 8 chunks: expert e (0..6, routed in id order then shared) chunk c at rows a0 + 16 e + 2 c, + 1 (8
//           elements) -> (((((e0 + e1) + e2) + e3) + e4) + e5) + e6, every partial binary32 RNE (ot_dsrom_qadd LAT 6 =
//           the hub moe leaf's ot_dsrom_fp32_add_f12_l6), BF16 at the end -> row pair ob + 2 c.  8 lanes, expert-major
//           reads one a cycle: the adder loop is 8 cycles (operand register, LAT 6, acc register), so chunk c's partial
//           meets its next expert exactly; phase 0 passes e0 through the adder as e0 + (-0), an exact identity in RNE
//           for every e0 (a NaN / Inf operand raises the adder fault, as it would in e0 + e1).
//   14 ENG  (RTL-BUILD-S81 2026-10-18) the Engram mix feeder of the beat's ve sub-leaf (ot_s81sl_ve, the 4 HC copies x 64
//           elements of this beat; golden tools/hdc_golden_v41.py engram_layer).  imm[30] = phase.  The beat's h is first
//           copied into the leaf store by vp HSTORE (32 rows at Hb, vn's half-row layout: half row i = rows Hb + 2 i,
//           Hb + 2 i + 1 = elements 4 i .. 4 i + 3 of all 4 copies, copy j element 4 i + e at bits (4 j + e) * 16).
//           K / W / V region (compiler row map results/arch/s81_dv_1016/eng/kv_rowmap.json, A0 per Engram layer): K_j at
//           A0 + 16 j (element 4 r + w at row A0 + 16 j + r, word w), W_j at A0 + 64 + 16 j, V at A0 + 128 (144 rows).
//           phase 0 REDUCE  n = 64, a0 = Hb, a1 = A0: 16 h row-pair reads (one a cycle) into the h stash (4 kb), then
//                   64 reads alternating K_j and W_j row pairs (8 elements = 2 quads each; copy-major) -> ve quads, one a
//                   cycle after the first pair (GAP 0); the 4 ve beat partial triples (hh, kk, dd)
//                   leave the leaf on e_v / e_c / e_d (pin flops, toward xr -> xfin ENG).  Done = 4th triple out.
//                   The gate latch is cleared at the command.
//           gates   g_v / g_c / g_d (eg -> centre -> this leaf): gate of copy g_c latched; a second gate of one copy
//                   before the next REDUCE is a sticky fault.
//           phase 1 ADD  n = 32, a0 = A0, a1 = Hb' (write-back base): all 4 gates must be latched (else fault, command
//                   refused).  32 reads of the V row pairs (A0 + 128 + 2 s = V[8 s .. 8 s + 7], re-read per copy) -> one ve add
//                   beat a cycle (8 elements of copy j = read >> 3, h from the stash, gate j) -> the 32 BF16 results land
//                   in the stash in place (copy j's slots only) -> 16 row-pair writes Hb' + 2 i (the h layout) -> vp HLOAD
//                   moves them back into vn's h store.  Done = last write.
// Pins: every input lands in a flop; every output leaves a flop.  Reset: ot_rst_relay (regional synchronous release).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vs #(
    parameter integer XL = 6,          // qmul / qadd latency (ot_hdc_qmul_lat 6 as rxqr, ot_dsrom_qadd 6 = f12_l6)
    parameter integer MUT = 0          // bench negative controls: 1 SW drops w, 2 RB drops bias, 3 QR inverse rotation,
                                       // 4 MOE rounds every partial to BF16, 5 QB swaps the sub-beat halves, 6 RA returns rows shifted,
                                       // 9 SW wr takes w1 from word wsel ^ 1 of the weight row
                                       // 7 ENG ADD takes the gate of copy j ^ 1, 8 ENG REDUCE feeds K as W
) (
    input  wire          clk,
    input  wire          rst_n,
    // command (from vp)
    input  wire          s_v,
    input  wire [159:0]  s_d,
    // vp leaf-store extension port: row-pair read (data on x_qv / x_qd a fixed number of edges later) and write
    output reg           x_rv,
    output reg  [9:0]    x_ra,
    input  wire          x_qv,
    input  wire [255:0]  x_qd,
    output reg           x_wv,
    output reg  [9:0]    x_wa,
    output reg  [7:0]    x_wm,
    output reg  [255:0]  x_wd,
    // vq second input: 8-lane sub-beats + gather mode
    output reg           u_v,
    output reg  [2:0]    u_i,
    output reg  [255:0]  u,
    output reg           um_v,
    output reg           um_q,
    output reg           um_b,
    output reg  [7:0]    um_i,
    // SW lane sub-leaf (ot_s81sl_vsw): a group {u3..u0, g3..g0} with its weight / limit; 4 BF16 results back
    output reg           sw_v,
    output reg  [255:0]  sw_d,
    output reg  [31:0]   sw_w,
    output reg  [31:0]   sw_lim,
    input  wire          sw_vi,
    input  wire [63:0]   sw_ri,
    input  wire          sw_fi,
    // RA lane pair (closed hub leaves): to ot_s81_su_rxsf, from ot_s81_su_rxsb
    output reg           ra_v,
    output reg  [31:0]   ra_x,
    input  wire          ra_vi,
    input  wire [31:0]   ra_ri,
    input  wire          ra_fi,
    // ve sub-leaf (Engram mix of this beat): reduce quads / add beats out, beat partials / results / fault back
    output reg           ve_rv,
    output reg  [1:0]    ve_rc,
    output reg  [127:0]  ve_rh,
    output reg  [127:0]  ve_rk,
    output reg  [127:0]  ve_rw,
    input  wire          ve_pv,
    input  wire [1:0]    ve_pc,
    input  wire [31:0]   ve_phh,
    input  wire [31:0]   ve_pkk,
    input  wire [31:0]   ve_pdd,
    output reg           ve_av,
    output reg  [1:0]    ve_ac,
    output reg  [255:0]  ve_ah,
    output reg  [255:0]  ve_aval,
    output reg  [31:0]   ve_ag,
    input  wire          ve_ov,
    input  wire [1:0]    ve_oc,
    input  wire [255:0]  ve_oy,
    input  wire          ve_fi,
    // Engram beat partials to the slice centre ({dd, kk, hh}) and gates from it
    output reg           e_v,
    output reg  [1:0]    e_c,
    output reg  [95:0]   e_d,
    input  wire          g_v,
    input  wire [1:0]    g_c,
    input  wire [31:0]   g_d,
    output reg           fault
);
    localparam [3:0] OP_SW = 4'd8, OP_QB = 4'd9, OP_RA = 4'd10, OP_RB = 4'd11, OP_QR = 4'd12, OP_MOE = 4'd13, OP_ENG = 4'd14;
`ifdef OT_S81SL_VS_SRAM
`ifdef OT_S81SL_VS_FP_N32
    wire [135:0] rsv;
    ot_rst_relay_tree3 #(.REGIONS(136),.LEAVES(8)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rsv));
`else
    wire [135:0] rsv;
    ot_rst_relay_tree3 #(.REGIONS(136),.LEAVES(8)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rsv));
`endif
`else
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
`endif
    wire rs_c = rsv[0], rs_r = rsv[1], rs_x = rsv[2], rs_o = rsv[3];
`ifdef OT_S81SL_VS_SRAM
    wire rs_ra=rsv[4],rs_kra=rsv[5],rs_eng=rsv[6],rs_flush=rsv[7],rs_out=rsv[24],rs_fault=rsv[25];
`else
    wire rs_ra=rs_o,rs_kra=rs_o,rs_eng=rs_o,rs_flush=rs_o,rs_out=rs_o,rs_fault=rs_o;
`endif
    integer i, k, e2;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction

`ifdef OT_S81SL_VS_SRAM
`define S81_VS_CONTROL_KEEP (* keep="true" *)
`else
`define S81_VS_CONTROL_KEEP
`endif
    // ---------------------------------------------------------------- input pin flops
    `S81_VS_CONTROL_KEEP reg sv_c, xqv_c, rav_c, raf_c, swv_c, swf_c; `S81_VS_CONTROL_KEEP reg [159:0] sd_c; reg [255:0] xq_c; reg [31:0] rar_c; reg [63:0] swr_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin sv_c <= 1'b0; xqv_c <= 1'b0; rav_c <= 1'b0; raf_c <= 1'b0; swv_c <= 1'b0; swf_c <= 1'b0; end
        else begin sv_c <= s_v; xqv_c <= x_qv; rav_c <= ra_vi; raf_c <= ra_fi; swv_c <= sw_vi; swf_c <= sw_fi; end
    always @(posedge clk) begin sd_c <= s_d; xq_c <= x_qd; rar_c <= ra_ri; swr_c <= sw_ri; end
    `S81_VS_CONTROL_KEEP reg vpv_c, vov_c, vef_c, gv_c; reg [1:0] vpc_c, voc_c, gc_c; reg [95:0] vpd_c; reg [255:0] voy_c; reg [31:0] gd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin vpv_c <= 1'b0; vov_c <= 1'b0; vef_c <= 1'b0; gv_c <= 1'b0; end
        else begin vpv_c <= ve_pv; vov_c <= ve_ov; vef_c <= ve_fi; gv_c <= g_v; end
    always @(posedge clk) begin
        vpc_c <= ve_pc; vpd_c <= {ve_pdd, ve_pkk, ve_phh}; voc_c <= ve_oc; voy_c <= ve_oy; gc_c <= g_c; gd_c <= g_d;
    end

    // ---------------------------------------------------------------- command register and checks
    wire [3:0] c_op = sd_c[3:0]; wire [9:0] c_a0 = sd_c[13:4]; wire [7:0] c_n = sd_c[31:24]; wire [127:0] c_imm = sd_c[159:32];
    wire [2:0] c_j0 = c_imm[24:22];
    wire [9:0] c_a1 = sd_c[23:14]; wire c_ph = c_imm[30];
    reg  [3:0] gmask;                                                     // ENG gates latched (copy mask)
    wire [7:0] c_nsb = (c_op == OP_QB) ? c_n : {1'b0, c_n[7:1]};          // vq sub-beats of a streaming op
    wire c_uq = c_imm[11] || c_op == OP_QB;
    wire c_bad = (c_op != OP_SW && c_op != OP_QB && c_op != OP_RA && c_op != OP_RB && c_op != OP_QR && c_op != OP_MOE &&
                  c_op != OP_ENG) ||
                 (c_op == OP_ENG && (c_ph ? (c_n != 8'd32 || gmask != 4'hF) : c_n != 8'd64)) ||
                 (c_n == 8'd0) || (c_op == OP_SW && c_n > 8'd16) || (c_op == OP_MOE && c_n != 8'd8) ||
                 (c_uq && (c_op == OP_SW || c_op == OP_QB) && ((c_op == OP_SW && c_n[0]) || ({5'd0, c_j0} + c_nsb) > 8'd8));
    `S81_VS_CONTROL_KEEP reg busy, done; reg [3:0] op; reg [9:0] a0, a1, ob; reg [7:0] n; reg wb, uq, ph, wr; reg [2:0] j0, wsel; reg [31:0] lim, w0, w1;
    wire c_wr = c_op == OP_SW && c_imm[25];
    wire acc_cmd = sv_c && !busy && !c_bad;
`ifdef OT_S81SL_VS_SRAM
`define S81_VS_ACC(i) cmd_accept[i]
    wire rs_command=rsv[36];
`else
`define S81_VS_ACC(i) acc_cmd
    wire rs_command=rs_c;
`endif

    always @(posedge clk or negedge rs_command)
        if (!rs_command) begin busy <= 1'b0; op <= 4'd0; end
        else if (acc_cmd) begin busy <= 1'b1; op <= c_op; end
        else if (done) busy <= 1'b0;
`ifdef OT_S81SL_VS_SRAM
    // Predict the command acceptance at the input-capture edge. This is the
    // same edge already used for sd_c/sv_c, with busy/gmask after that edge.
    wire busy_after=rs_c && (acc_cmd || (busy && !done));
    wire [3:0] gmask_after=!rs_eng?4'd0:(acc_cmd && c_op==OP_ENG && !c_ph)?4'd0:gv_c?(gmask | (4'b1<<gc_c)):gmask;
    wire [127:0] cmd_accept;
    wire [6:0] incoming_op={s_d[3:0]==OP_ENG,s_d[3:0]==OP_MOE,s_d[3:0]==OP_QR,s_d[3:0]==OP_RB,s_d[3:0]==OP_RA,s_d[3:0]==OP_QB,s_d[3:0]==OP_SW};
    wire [1:0] stream_bad={(({5'd0,s_d[56:54]}+s_d[31:24]) > 8'd8),
                         (s_d[24] || ({5'd0,s_d[56:54]}+{1'b0,s_d[31:25]}) > 8'd8)};
    genvar acr;
    generate for(acr=0;acr<4;acr=acr+1) begin:g_accept_region
      ot_s81sl_vs_accept32 u_accept(.clk(clk),.rst_n(rsv[30+acr]),.packet(s_d),.incoming_op(incoming_op),.stream_bad(stream_bad),.sv(s_v),.busy_after(busy_after),.gmask_after(gmask_after),.q(cmd_accept[32*acr+:32]));
    end endgenerate
    (* keep="true" *) reg [3:0] regional_packet_op[0:19];
    integer cpr;
    always @(posedge clk) for(cpr=0;cpr<20;cpr=cpr+1) regional_packet_op[cpr]<=s_d[3:0];
`ifndef SYNTHESIS
    always @(posedge clk) if(rs_c && cmd_accept!=={128{acc_cmd}}) $fatal(1,"VS predicted command acceptance differs from original control");
`endif
    wire [23:0] region_busy;
    genvar bg;
    generate for(bg=0;bg<4;bg=bg+1) begin:g_busy_region
      ot_s81sl_vs_busy6 u_busy(.clk(clk),.rst_n(rsv[35]),.sv(sv_c),.bad(c_bad),.done(done),.q(region_busy[6*bg+:6]));
    end endgenerate
    wire [79:0] cmd_payload={c_a0,c_a1,c_ph,c_n,c_imm[9:0],c_imm[10],c_uq,c_j0,c_imm[63:32],c_wr,c_imm[28:26]};
    wire [79:0] cmd_latched;
    assign {a0,a1,ph,n,ob,wb,uq,j0,lim,wr,wsel}=cmd_latched;
    genvar cb;
    generate for(cb=0;cb<10;cb=cb+1) begin:g_cmd_byte
      ot_s81sl_vs_cmd8 u_cmd(.clk(clk),.accept(cmd_accept[80+cb]),.d(cmd_payload[8*cb+:8]),.q(cmd_latched[8*cb+:8]));
    end endgenerate
`else
    always @(posedge clk)
        if (acc_cmd) begin
            a0 <= c_a0; a1 <= c_a1; ph <= c_ph; n <= c_n; ob <= c_imm[9:0]; wb <= c_imm[10]; uq <= c_uq; j0 <= c_j0;
            lim <= c_imm[63:32]; wr <= c_wr; wsel <= c_imm[28:26];
        end
`endif
    // SW weights: from the immediate, or (wr) from word wsel of the row pair a1 = the op's first arrival
    wire w_arr;
`ifdef OT_S81SL_VS_SRAM
    genvar wb0;
    generate for(wb0=0;wb0<8;wb0=wb0+1) begin:g_weight_byte
      wire [7:0] wi;
      if(wb0<4) assign w0[8*wb0+:8]=wi;
      else assign w1[8*(wb0-4)+:8]=wi;
      ot_s81sl_vs_weight8 #(.BYTE(wb0%4),.SECOND(wb0>=4),.MUT(MUT)) u_byte(.clk(clk),.accept({cmd_accept[98+wb0],cmd_accept[90+wb0]}),.sel(s_d[60:58]),.imm(wb0<4?c_imm[64+8*(wb0%4)+:8]:c_imm[96+8*(wb0%4)+:8]),.arr(region_arr[18]),.op(region_op_c[18][27:24]),.wr(wr),.ka(region_ka_c[18][23:16]),.row(xq_c),.w(wi));
    end endgenerate
`else
    always @(posedge clk)
        if (acc_cmd) begin w0 <= c_imm[95:64]; w1 <= c_imm[127:96]; end
        else if (w_arr) begin
            w0 <= xq_c[32 * wsel +: 32]; w1 <= (MUT == 9) ? xq_c[32 * (wsel ^ 3'd1) +: 32] : xq_c[32 * wsel +: 32];
        end

`endif

    // ---------------------------------------------------------------- read issue (fixed cadence per op)
    //   QB / RB: one pair a cycle;  QR: every 2 cycles;  SW: every 4 cycles (the lane takes a group in 4);
    //   RA: every 8 cycles (8 elements);  MOE: 56 pairs, one a cycle, step 8 e + c at a0 + 16 e + 2 c
    reg rrun; reg [8:0] rs, rn; reg [2:0] cad;       // read step, last step, cadence mask (step & cad == 0 issues)
    wire [8:0] c_nr = (c_op == OP_RA) ? {4'd0, c_n[7:3]} + {8'd0, |c_n[2:0]} : {1'b0, c_n};   // reads
`ifdef OT_S81SL_VS_SRAM
    always @(posedge clk or negedge rs_r)
      if(!rs_r) begin rrun<=0;cad<=0;x_rv<=0;end
      else begin
        x_rv<=0;
        if(cmd_accept[106]) begin
          rrun<=1;
                cad <= (c_op == OP_RA) ? 3'd7 : (c_op == OP_SW) ? 3'd3 : (c_op == OP_QR) ? 3'd1 : 3'd0;
        end else if(rrun) begin
          if(rs==rn) rrun<=0;
          x_rv<=(rs[2:0]&cad)==0;
        end
      end
    always @(posedge clk or negedge rs_r)
      if(!rs_r) rs<=0;else if(cmd_accept[107]) rs<=0;else if(rrun) rs<=rs+1'b1;
    // the last-step count decodes its own kept opcode copy (same edge as sd_c): bounded c_op fanout
    (* keep="true" *) reg [3:0] rn_op;
    always @(posedge clk) rn_op <= s_d[3:0];
    wire [8:0] rn_nr = (rn_op == OP_RA) ? {4'd0, c_n[7:3]} + {8'd0, |c_n[2:0]} : {1'b0, c_n};
    wire rn_wr = rn_op == OP_SW && c_imm[25];
    always @(posedge clk or negedge rs_r)
      if(!rs_r) rn<=0;else if(cmd_accept[108]) begin
        rn <= (rn_op == OP_ENG) ? (c_ph ? 9'd31 : 9'd79) : (rn_op == OP_MOE) ? 9'd55 : (rn_op == OP_RA) ? {rn_nr[5:0], 3'd0} - 9'd8 :
                       (rn_op == OP_SW) ? {rn_nr[6:0], 2'd0} - (rn_wr ? 9'd0 : 9'd4) : (rn_op == OP_QR) ? {rn_nr[7:0], 1'b0} - 9'd2 : rn_nr - 9'd1;
      end
`else
    always @(posedge clk or negedge rs_r)
        if (!rs_r) begin rrun <= 1'b0; rs <= 9'd0; rn <= 9'd0; cad <= 3'd0; x_rv <= 1'b0; end
        else begin
            x_rv <= 1'b0;
            if (acc_cmd) begin
                rrun <= 1'b1; rs <= 9'd0;
                cad <= (c_op == OP_RA) ? 3'd7 : (c_op == OP_SW) ? 3'd3 : (c_op == OP_QR) ? 3'd1 : 3'd0;
                rn  <= (c_op == OP_ENG) ? (c_ph ? 9'd31 : 9'd79) : (c_op == OP_MOE) ? 9'd55 : (c_op == OP_RA) ? {c_nr[5:0], 3'd0} - 9'd8 :
                       (c_op == OP_SW) ? {c_nr[6:0], 2'd0} - (c_wr ? 9'd0 : 9'd4) : (c_op == OP_QR) ? {c_nr[7:0], 1'b0} - 9'd2 : c_nr - 9'd1;
            end else if (rrun) begin
                rs <= rs + 9'd1;
                if (rs == rn) rrun <= 1'b0;
                x_rv <= (rs[2:0] & cad) == 3'd0;
            end
        end
`endif
    wire [8:0] rs_e = rs - 9'd16;                    // ENG REDUCE K / W read r: copy r[6:4], pair r[3:1], W when r[0]
`ifdef OT_S81SL_VS_SRAM
    // second latched copy of the read base (same accept edge) for the MOE / RA / SW / QR address adders
    (* keep="true" *) reg [9:0] a0_b;
    always @(posedge clk) if(cmd_accept[118]) a0_b <= c_a0;
    // and of the read step (same reset / accept edge / increment as rs)
    (* keep="true" *) reg [8:0] rs_b;
    // own reset leaf rsv[38] (otherwise unused; same tree depth / release edge as rs_r)
    always @(posedge clk or negedge rsv[38])
      if(!rsv[38]) rs_b<=0;else if(cmd_accept[124]) rs_b<=0;else if(rrun) rs_b<=rs_b+1'b1;
`else
    wire [9:0] a0_b = a0;
    wire [8:0] rs_b = rs;
`endif
    always @(posedge clk)
        case (op)
            OP_MOE: x_ra <= a0_b + {3'd0, rs_b[5:3], 4'd0} + {6'd0, rs_b[2:0], 1'b0};
            OP_RA:  x_ra <= a0_b + {2'd0, rs_b[8:3], 1'b0};
            OP_SW:  x_ra <= (wr && rs_b == 9'd0) ? a1 : a0_b + {1'b0, rs_b[8:2] - {6'd0, wr}, 1'b0};
            OP_QR:  x_ra <= a0_b + {rs_b[8:1], 1'b0};
            OP_ENG: x_ra <= ph ? a0 + 10'd128 + {6'd0, rs[2:0], 1'b0} :
                           (rs < 9'd16) ? a0 + {rs[8:0], 1'b0} :
                           a1 + {3'd0, rs_e[0], 6'd0} + {3'd0, rs_e[6:4], 4'd0} + {6'd0, rs_e[3:1], 1'b0};
            default: x_ra <= a0 + {rs[8:0], 1'b0};
        endcase

    // arrivals: the k-th read's row pair is at xq_c in arrival k (x_qv marks it, a fixed number of edges after x_rv)
`ifdef OT_S81SL_VS_SRAM
    wire arr = xqv_c && region_busy[20];                               // region-3 busy copy (bit 20) == busy
`else
    wire arr = xqv_c && busy;
`endif
    wire [31:0] xw [0:7];
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_xw
        assign xw[gl] = xq_c[32 * gl +: 32];
    end endgenerate
    `S81_VS_CONTROL_KEEP reg [7:0] ka;                                    // arrivals of the running op
    always @(posedge clk or negedge rs_c)
        if (!rs_c) ka <= 8'd0;
        else if (`S81_VS_ACC(109)) ka <= 8'd0;
        else if (arr) ka <= ka + 8'd1;
`ifdef OT_S81SL_VS_SRAM
    wire [3:0] region_op[0:19];
    wire [7:0] region_ka[0:19];
    wire [31:0] region_op_c[0:19],region_ka_c[0:19];
    wire [19:0] region_arr;
    genvar cr;
    generate for(cr=0;cr<20;cr=cr+1) begin:g_data_region
      ot_s81sl_vs_lane_ctl u_ctl(.clk(clk),.rst_n(rsv[cr<16?40+cr:26+cr-16]),.rst_v(rsv[39]),.accept(cmd_accept[4*cr+:4]),.busy(region_busy[cr]),.cop(regional_packet_op[cr]),.xqv(x_qv),.op(region_op[cr]),.ka(region_ka[cr]),.op_copy(region_op_c[cr]),.ka_copy(region_ka_c[cr]),.arr(region_arr[cr]));
    end endgenerate
`endif
    // ENG stash-read index replicas (gate high_fanout: one 16 x 256-b stash read select drove 4,100 loads): 4 identical
    // copies of the arrival and flush counters, one per 64-b column group of the stash (keep: not merged by synthesis)
    integer rq;
`ifndef OT_S81SL_VS_SRAM
    (* keep = "true" *) reg [7:0] ka_q [0:3];
    (* keep = "true" *) reg [3:0] fl_q [0:3];
    (* keep = "true" *) reg [3:0] eqp_q [0:3];
    (* keep = "true" *) reg       ep_q [0:3];
    always @(posedge clk or negedge rs_c)
        if (!rs_c) for (rq = 0; rq < 4; rq = rq + 1) ka_q[rq] <= 8'd0;
        else for (rq = 0; rq < 4; rq = rq + 1)
            if (acc_cmd) ka_q[rq] <= 8'd0; else if (arr) ka_q[rq] <= ka_q[rq] + 8'd1;

`endif
    // ================================================================ SW: groups to the lane sub-leaf
    assign w_arr = arr && op == OP_SW && wr && ka == 8'd0;
    wire [7:0] kg = ka - {7'd0, wr};                 // SW group index of this arrival (wr: arrival 0 = the weight row)
    always @(posedge clk or negedge rs_r) if (!rs_r) sw_v <= 1'b0; else sw_v <= arr && op == OP_SW && !w_arr;
    always @(posedge clk) begin
        sw_d <= xq_c; sw_lim <= lim;
`ifndef OT_S81SL_VS_SRAM
        sw_w <= (MUT == 1) ? 32'h3F800000 : (kg >= 8'd8 ? w1 : w0);
`endif
    end

`ifdef OT_S81SL_VS_SRAM
    genvar swb;
    generate for(swb=0;swb<4;swb=swb+1) begin:g_sw_weight_byte
      ot_s81sl_vs_swweight8 #(.BYTE(swb),.MUT(MUT)) u_weight(.clk(clk),.ka(region_ka_c[19][31:24]),.wr(wr),.w0(w0[8*swb+:8]),.w1(w1[8*swb+:8]),.q(sw_w[8*swb+:8]));
    end endgenerate
`endif
    // ================================================================ X lanes: 8 x ot_dsrom_qadd, 4 x ot_hdc_qmul_lat
    // QR: a read carries 2 rotation pairs; pair 0 (q0, q1; c, s at words 4, 5) issues on arrival, pair 1 (q2, q3; c', s'
    // at words 6, 7) one cycle later from a stash.  QR lane l (0, 1): mine = q[l], pair = q[l ^ 1]; muls 2 l (mine * c),
    // 2 l + 1 (pair * (l ? s : -s)); its adder sums them (the hub rxqr lane: ODD lanes add b c + a s).
    wire qr_a = arr && op == OP_QR;
    reg  qr_b; reg [127:0] qr_st;                  // pair 1 stash {s', c', q3, q2}
    always @(posedge clk or negedge rs_x) if (!rs_x) qr_b <= 1'b0; else qr_b <= qr_a;
`ifdef OT_S81SL_VS_SRAM
    (* keep="true" *) reg [15:0] qr_capture, qr_phase;
    always @(posedge clk) begin
      qr_capture <= {16{rs_c && x_qv && hbusy_n && hop_n == OP_QR}};
      qr_phase <= {16{qr_a}};
    end
    wire [127:0] qr_second = {xw[7],xw[6],xw[3],xw[2]};
    wire [127:0] qr_first = {xw[5],xw[4],xw[1],xw[0]};
    wire [127:0] qr_pair;
    genvar qg;
    generate for(qg=0;qg<16;qg=qg+1) begin:g_qr_byte
      always @(posedge clk) if(qr_capture[qg]) qr_st[8*qg+:8] <= qr_second[8*qg+:8];
      assign qr_pair[8*qg+:8] = qr_phase[qg] ? qr_st[8*qg+:8] : qr_first[8*qg+:8];
    end endgenerate
    wire [31:0] qm0=qr_pair[31:0],qm1=qr_pair[63:32],qc=qr_pair[95:64],qs=qr_pair[127:96];
`else
    always @(posedge clk) if (qr_a) qr_st <= {xw[7], xw[6], xw[3], xw[2]};
    wire [31:0] qm0 = qr_b ? qr_st[31:0] : xw[0], qm1 = qr_b ? qr_st[63:32] : xw[1];
    wire [31:0] qc  = qr_b ? qr_st[95:64] : xw[4], qs = qr_b ? qr_st[127:96] : xw[5];
`endif
    wire qr_in = qr_a || qr_b;
    wire [31:0] mp [0:3]; wire [3:0] mf; wire [XL:0] vmq;
    ot_hdc_vline #(.D(XL)) u_vmq (.clk(clk), .rst_n(rs_x), .v(qr_in), .vd(vmq));
    generate for (gl = 0; gl < 2; gl = gl + 1) begin : g_qm
        wire [31:0] mine = gl ? qm1 : qm0, pair = gl ? qm0 : qm1;
        wire [31:0] sg = ((gl != 0) ^ (MUT == 3)) ? qs : {~qs[31], qs[30:0]};
`ifdef OT_S81SL_VS_SRAM
`ifdef OT_S81SL_VS_FP_N32
        wire [5:0] qm_rst0=rsv[56+12*gl+:6],qm_rst1=rsv[62+12*gl+:6];
`else
        wire qm_rst0=rsv[8+2*gl],qm_rst1=rsv[9+2*gl];
`endif
`else
        wire qm_rst0=rs_x,qm_rst1=rs_x;
`endif
`ifdef OT_S81SL_VS_FP_N32
        ot_s81sl_qmul_n32 #(.LAT(XL)) u_p (clk, qm_rst0, qr_in, mine, qc, mp[2 * gl], mf[2 * gl]);
        ot_s81sl_qmul_n32 #(.LAT(XL)) u_q (clk, qm_rst1, qr_in, pair, sg, mp[2 * gl + 1], mf[2 * gl + 1]);
`else
        ot_hdc_qmul_lat #(XL) u_p (clk, qm_rst0, qr_in, mine, qc, mp[2 * gl], mf[2 * gl]);
        ot_hdc_qmul_lat #(XL) u_q (clk, qm_rst1, qr_in, pair, sg, mp[2 * gl + 1], mf[2 * gl + 1]);
`endif
    end endgenerate
    // adder operand registers (one stage after the source mux): RB lanes 0..3, QR lanes 0..1, MOE lanes 0..7
    wire moe_in = arr && op == OP_MOE;
    wire [2:0] moe_e = ka[5:3];                      // expert of this arrival (8 e + c)
`ifdef OT_S81SL_VS_SRAM
    wire [31:0] xa [0:7],xb [0:7];
`else
    reg [31:0] xa [0:7],xb [0:7];
`endif
    reg x_iv;
    wire [31:0] ay [0:7]; wire [7:0] af; wire [XL:0] vx;
    reg  [31:0] acc1 [0:7];
    // (MUT 4 rounds every partial to BF16, the hub moe leaf's EARLY_BF16 control; an expert-order reversal is NOT
    // visible on the 1M token's moe_sum rows: its FP32 differences vanish under the final BF16 rounding)
    always @(posedge clk or negedge rs_x)
        if (!rs_x) x_iv <= 1'b0;
        else x_iv <= (arr && op == OP_RB) || vmq[XL] || moe_in;
`ifdef OT_S81SL_VS_SRAM
    genvar ol,obn;
    generate for(ol=0;ol<8;ol=ol+1) begin:g_operand_lane
      wire [3:0] lane_op=region_op[ol];
      wire [7:0] lane_ka=region_ka[ol];
      wire [31:0] lane_acc=(MUT==4)?bf16(acc1[ol]):acc1[ol];
      for(obn=0;obn<8;obn=obn+1) begin:g_nibble
        ot_s81sl_vs_operand4 #(.NEG(obn==7?4'h8:4'h0),.MUT(MUT)) u_sel(
          .clk(clk),.op(region_op_c[ol][4*(obn/2)+:4]),.expert(region_ka_c[ol][8*(obn/2)+3+:3]),.ra(xw[ol&3][4*obn+:4]),.rb(xw[4+(ol&3)][4*obn+:4]),
          .m0(mp[2*(ol&1)][4*obn+:4]),.m1(mp[2*(ol&1)+1][4*obn+:4]),.x(xw[ol][4*obn+:4]),.acc(lane_acc[4*obn+:4]),
          .a(xa[ol][4*obn+:4]),.b(xb[ol][4*obn+:4]));
      end
    end endgenerate
`else
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1)
            if (op == OP_RB) begin
                xa[i] <= xw[i & 3]; xb[i] <= (MUT == 2) ? 32'd0 : xw[4 + (i & 3)];
            end else if (op == OP_QR) begin
                xa[i] <= mp[2 * (i & 1)]; xb[i] <= mp[2 * (i & 1) + 1];
            end else begin
                xa[i] <= (moe_e == 3'd0) ? xw[i] : (MUT == 4) ? bf16(acc1[i]) : acc1[i];
                xb[i] <= (moe_e == 3'd0) ? 32'h80000000 : xw[i];
            end
`endif
    ot_hdc_vline #(.D(XL)) u_vx (.clk(clk), .rst_n(rs_x), .v(x_iv), .vd(vx));
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_xa
`ifdef OT_S81SL_VS_SRAM
`ifdef OT_S81SL_VS_FP_N32
        wire [5:0] xa_rst=rsv[80+6*gl+:6];
`else
        wire xa_rst=rsv[16+gl];
`endif
`else
        wire xa_rst=rs_x;
`endif
`ifdef OT_S81SL_VS_FP_N32
        ot_s81sl_qadd_n32 #(.LAT(XL)) u_a (clk, xa_rst, x_iv, xa[gl], xb[gl], ay[gl], af[gl]);
`else
        ot_dsrom_qadd #(.LAT(XL)) u_a (clk, xa_rst, x_iv, xa[gl], xb[gl], ay[gl], af[gl]);
`endif
    end endgenerate
    // adder results: MOE phases 0..5 loop back (acc1 -> operand register: 8 cycles a turn), phase 6 / RB / QR leave
    reg [7:0] k_xo;
    always @(posedge clk or negedge rs_x)
        if (!rs_x) k_xo <= 8'd0;
        else if (`S81_VS_ACC(112)) k_xo <= 8'd0;
        else if (vx[XL]) k_xo <= k_xo + 8'd1;
    always @(posedge clk) for (i = 0; i < 8; i = i + 1) acc1[i] <= ay[i];
    reg xo_v; reg [255:0] xo_d; reg [127:0] qr_h;  // QR: pair 0's two results wait for pair 1's
    always @(posedge clk or negedge rs_x)
        if (!rs_x) xo_v <= 1'b0;
        else xo_v <= vx[XL] && (op == OP_RB || (op == OP_QR && k_xo[0]) || (op == OP_MOE && k_xo >= 8'd48));
    always @(posedge clk) begin
`ifndef OT_S81SL_VS_SRAM
        if (vx[XL] && op == OP_QR && !k_xo[0]) qr_h <= {64'd0, bf16(ay[1]), bf16(ay[0])};
`endif
`ifndef OT_S81SL_VS_SRAM
        for (i = 0; i < 8; i = i + 1) xo_d[32 * i +: 32] <= (op == OP_RB) ? ay[i] : bf16(ay[i]);
        if (op == OP_QR) xo_d[127:0] <= {bf16(ay[1]), bf16(ay[0]), qr_h[63:0]};
`endif
    end

`ifdef OT_S81SL_VS_SRAM
    wire [127:0] qr_half_data={64'd0,bf16(ay[1]),bf16(ay[0])};
    genvar qhb;
    wire [7:0] qr_en;
    generate for(qhb=0;qhb<8;qhb=qhb+1) begin:g_qr_en
      ot_s81sl_vs_qren u_en(.v(vx[XL]),.op(region_op_c[19][27:24]),.odd(k_xo[0]),.en(qr_en[qhb]));
    end
    for(qhb=0;qhb<16;qhb=qhb+1) begin:g_qr_half_byte
      ot_s81sl_vs_qrhold8 u_hold(.clk(clk),.en(qr_en[qhb/2]),.d(qr_half_data[8*qhb+:8]),.q(qr_h[8*qhb+:8]));
    end endgenerate
    wire [127:0] xo_qr={bf16(ay[1]),bf16(ay[0]),qr_h[63:0]};
    genvar xb0;
    generate for(xb0=0;xb0<32;xb0=xb0+1) begin:g_xresult_byte
      wire [31:0] bf=bf16(ay[xb0/4]);
      ot_s81sl_vs_xresult8 #(.LOW(xb0<16)) u_byte(.clk(clk),.op(region_op_c[xb0/2][24+4*(xb0%2)+:4]),.full(ay[xb0/4][8*(xb0%4)+:8]),.bf(bf[8*(xb0%4)+:8]),.qr(xo_qr[8*(xb0%16)+:8]),.y(xo_d[8*xb0+:8]));
    end endgenerate
`endif
    // ================================================================ RA: serialise to the lane pair, collect rows
    reg [223:0] ras; reg [3:0] rasn; reg [7:0] ra_left;
    wire ra_ld = arr && op == OP_RA;
    wire ra_go = (rasn != 4'd0 || ra_ld) && ra_left != 8'd0;
    always @(posedge clk or negedge rs_ra)
        if (!rs_ra) begin ra_v <= 1'b0; rasn <= 4'd0; ra_left <= 8'd0; end
        else begin
            if (`S81_VS_ACC(110)) ra_left <= (c_op == OP_RA) ? c_n : 8'd0;
            else if (ra_go) ra_left <= ra_left - 8'd1;
            rasn <= ra_ld ? 4'd7 : (rasn != 4'd0) ? rasn - 4'd1 : 4'd0;
            ra_v <= ra_go;
        end
`ifdef OT_S81SL_VS_SRAM
    (* keep="true" *) reg [31:0] ra_capture;
    always @(posedge clk) ra_capture <= {32{rs_c && x_qv && hbusy_n && hop_n == OP_RA}};
    genvar rb;
    generate for(rb=0;rb<28;rb=rb+1) begin:g_ra_byte
      always @(posedge clk) ras[8*rb+:8] <= ra_capture[rb] ? xq_c[32+8*rb+:8] : (rb<24 ? (ras >> (32+8*rb)) : 8'd0);
    end
    for(rb=0;rb<4;rb=rb+1) begin:g_ra_xbyte
      always @(posedge clk) ra_x[8*rb+:8] <= ra_capture[28+rb] ? xq_c[8*rb+:8] : ras[8*rb+:8];
    end endgenerate
`else
    always @(posedge clk) begin
        if (ra_ld) begin ras <= xq_c[255:32]; ra_x <= xq_c[31:0]; end
        else begin ras <= {32'd0, ras[223:32]}; ra_x <= ras[31:0]; end
    end
`endif
    `S81_VS_CONTROL_KEEP reg [7:0] k_ra; reg [95:0] rad;                // results returned; the row being assembled (words 0..2)
    always @(posedge clk or negedge rs_kra)
        if (!rs_kra) k_ra <= 8'd0;
        else if (`S81_VS_ACC(111)) k_ra <= 8'd0;
        else if (rav_c) k_ra <= k_ra + 8'd1;
`ifdef OT_S81SL_VS_SRAM
    (* keep="true" *) reg [11:0] ra_result_capture;
    wire [7:0] kra_n=(!rs_kra || `S81_VS_ACC(111))?8'd0:k_ra+{7'd0,rav_c};
    wire [1:0] kra_output[0:15];
    for(genvar krb=0;krb<16;krb=krb+1) begin:g_kra_output
      ot_s81sl_vs_count2 u_copy(.clk(clk),.rs(rsv[130+krb/6]),.d(kra_n[1:0]),.q(kra_output[krb]));
    end
    genvar rrb;
    generate for(rrb=0;rrb<12;rrb=rrb+1) begin:g_ra_result_byte
      always @(posedge clk) begin
        ra_result_capture[rrb] <= rs_c && ra_vi && kra_n[1:0]==rrb/4;
        if(ra_result_capture[rrb]) rad[8*rrb+:8] <= rar_c[8*(rrb%4)+:8];
      end
    end endgenerate
`else
    always @(posedge clk) if (rav_c) for (i = 0; i < 3; i = i + 1) if (k_ra[1:0] == i) rad[32 * i +: 32] <= rar_c;
`endif
    wire ra_row = rav_c && op == OP_RA && (k_ra[1:0] == 2'd3 || k_ra + 8'd1 == n);

    // ================================================================ ENG: h stash, ve feeder, gate latch, write-back
`ifndef OT_S81SL_VS_SRAM
    reg [255:0] hst [0:15];                          // the beat's h half rows (vn layout), updated in place by ADD
`endif
    `S81_VS_CONTROL_KEEP reg [2:0] kp_e; reg [5:0] ko_e; reg [4:0] fl_e; reg fl_on;
    reg [31:0]  gate [0:3];
`ifdef OT_S81SL_VS_SRAM
    wire eng_r=arr && region_op_c[19][31:28]==OP_ENG && !ph,eng_a=arr && region_op_c[19][31:28]==OP_ENG && ph;
`else
    wire eng_r = arr && op == OP_ENG && !ph, eng_a = arr && op == OP_ENG && ph;
`endif
    wire [7:0] er = ka - 8'd16;                      // REDUCE K / W arrival r (16 .. 79): K pair even r, W pair odd r
    `S81_VS_CONTROL_KEEP reg  [255:0] kst; reg [127:0] wst; (* keep *) reg epend;    // K pair stash, W upper half, second quad pending
    wire [5:0] eq0 = {er[6:4], er[3:1], 1'b0}; reg [5:0] eqp;
    wire [5:0] eq = epend ? eqp : eq0;              // quad 16 j + i (W arrival: even quad; next cycle: odd)
    reg [255:0] hrow, hra, hrb, xwsel; reg [31:0] gsel;
`ifdef OT_S81SL_VS_SRAM
    // Eight parity/copy banks replace the runtime-indexed 4 kb flop stash.
    // Addresses predict the counters at this edge, absorbing the SRAM read
    // into the existing counter edge; external ENG latency is unchanged.
    wire [7:0] hka_n = !rs_c || `S81_VS_ACC(117) ? 8'd0 : ka + {7'd0,arr};
    wire hep_n = rs_o && eng_r && ka >= 8'd16 && er[0];
    wire hfl_start = vov_c && ko_e == 6'd31;
    wire hfl_on_n = rs_o && !`S81_VS_ACC(119) && (hfl_start || (fl_on && fl_e != 5'd15));
    wire [4:0] hfl_n = !rs_o || `S81_VS_ACC(120) ? 5'd0 : fl_e + {4'd0,fl_on};
    wire hph_n = `S81_VS_ACC(121) ? c_ph : ph;
    wire [2:0] haddr_n = hfl_on_n ? hfl_n[3:1] :
                               hph_n ? hka_n[2:0] : hep_n ? ka[3:1] : hka_n[3:1];
`ifdef OT_S81SL_VS_SRAM
    wire hbusy_n = rs_c && (`S81_VS_ACC(122) || (region_busy[21] && !done));
`else
    wire hbusy_n = rs_c && (`S81_VS_ACC(122) || (busy && !done));
`endif
    wire [3:0] hop_n = `S81_VS_ACC(123) ? c_op : region_op_c[19][31:28];
    (* keep="true" *) reg [15:0] hfl_parity;
    wire [19:0] hpend_data;
    (* keep="true" *) reg [31:0] k_capture;
    (* keep="true" *) reg [15:0] w_capture;
    wire hq_pre_k,hq_pre_b;                                             // x_qv && hbusy_n && hop_n==ENG && !hph_n, shared
    ot_s81sl_vs_hqpre u_hqpre_k(.qv(x_qv),.busy_next(hbusy_n),.op_next(hop_n),.ph_next(hph_n),.q(hq_pre_k));
    ot_s81sl_vs_hqpre u_hqpre_b(.qv(x_qv),.busy_next(hbusy_n),.op_next(hop_n),.ph_next(hph_n),.q(hq_pre_b));
    for(genvar kc=0;kc<6;kc=kc+1) begin:g_capture_group
      wire [7:0] capture;
      ot_s81sl_vs_kcapture8 #(.ODD(kc>=4)) u_capture(.clk(clk),.rs(rsv[133+kc/3]),.pre(hq_pre_k),.ka(region_ka_c[18+kc/3][8*(kc%3)+:8]),.arr(region_arr[18+kc/3]),.accept(cmd_accept[117]),.q(capture));
      if(kc<4) assign k_capture[8*kc+:8]=capture;
      else assign w_capture[8*(kc-4)+:8]=capture;
    end
    always @(posedge clk) hfl_parity <= {16{hfl_n[0]}};
    wire [63:0] hbank [0:7];
    wire [15:0] hep_s;
    ot_s81sl_vs_pending #(.N(20)) u_pending_data(.clk(clk),.rs(rs_o),.arr(arr),.op(region_op_c[16][3:0]),.ph(ph),.ka(region_ka_c[16][31:24]),.q(hpend_data));
    ot_s81sl_vs_pending #(.N(16)) u_pending_sel(.clk(clk),.rs(rs_o),.arr(arr),.op(region_op_c[17][3:0]),.ph(ph),.ka(region_ka_c[17][31:24]),.q(hep_s));
    genvar hj,hp,hs;
    generate for(hj=0;hj<4;hj=hj+1) begin:g_hcopy
      for(hp=0;hp<2;hp=hp+1) begin:g_parity
        wire [7:0] fill_b,add_b;
        ot_s81sl_vs_bankctl8 #(.PARITY(hp),.COPY(hj)) u_ctl(.clk(clk),.rs(rsv[128+hj/2]),.pre(hq_pre_b),.op_next(hop_n),.ph_next(hph_n),.ka(region_ka_c[18+hj/2][23:16]),.arr(region_arr[18+hj/2]),.accept(cmd_accept[117]),.ov(ve_ov),.oc(ve_oc),.fill(fill_b),.add(add_b));
        wire we = fill_b[0] || add_b[0];
        wire [2:0] wa = fill_b[0] ? ka[3:1] : ko_e[2:0];
        wire [63:0] wd;
        for(hs=0;hs<8;hs=hs+1) begin:g_word
          assign wd[8*hs+:8] = fill_b[hs] ? xq_c[64*hj+8*hs+:8] : voy_c[32*(4*hp+hs/2)+16+8*(hs%2)+:8];
        end
        wire [127:0] raw;
        ot_sram_1r1w_32x128_m1 u_hst(.clk(clk),.r_ce_in(1'b1),.r_addr_in({2'd0,haddr_n}),.rd_out(raw),
          .w_ce_in(we),.w_addr_in({2'd0,wa}),.wd_in({64'd0,wd}),.w_mask_in({64'd0,64'hffffffffffffffff}));
        // Read-during-write bypass reproduces the original post-edge stash.
        for(hs=0;hs<4;hs=hs+1) begin:g_bypass
          (* keep="true" *) reg hit;
          reg [15:0] forwarded;
          always @(posedge clk) begin hit <= we && wa == haddr_n; forwarded <= wd[16*hs+:16]; end
          assign hbank[2*hj+hp][16*hs+:16] = hit ? forwarded : raw[16*hs+:16];
        end
      end
      for(hs=0;hs<4;hs=hs+1) begin:g_read
        always @(*) begin
          hrow[64*hj+16*hs+:16] = hep_s[4*hj+hs] ? hbank[2*hj+1][16*hs+:16] : hbank[2*hj][16*hs+:16];
          hra[64*hj+16*hs+:16] = hbank[2*hj][16*hs+:16];
          hrb[64*hj+16*hs+:16] = hbank[2*hj+1][16*hs+:16];
          xwsel[64*hj+16*hs+:16] = hfl_parity[4*hj+hs] ? hbank[2*hj+1][16*hs+:16] : hbank[2*hj][16*hs+:16];
        end
      end
    end endgenerate
    (* keep="true" *) reg [15:0] gate_capture;
    genvar gr;
    generate for(gr=0;gr<16;gr=gr+1) begin:g_gate_byte
      always @(posedge clk) begin
        gate_capture[gr] <= rsv[34] && g_v && g_c==gr/4;
        if(gate_capture[gr]) gate[gr/4][8*(gr%4)+:8] <= gd_c[8*(gr%4)+:8];
      end
    end
    for(gr=0;gr<4;gr=gr+1) begin:g_reduce_select
      wire [7:0] local_er0=region_ka_c[16+gr][7:0]-8'd16,local_er1=region_ka_c[16+gr][15:8]-8'd16;
      (* keep="true" *) reg [1:0] prev_copy0,prev_copy1;
      wire [1:0] copy_sel0=hpend_data[16+gr]?prev_copy0:local_er0[5:4],copy_sel1=hpend_data[16+gr]?prev_copy1:local_er1[5:4];
      always @(posedge clk) begin
        prev_copy0<=local_er0[5:4];prev_copy1<=local_er1[5:4];
        ve_rh[32*gr+:32]<={hw8(hrow,copy_sel1,gr,1),hw8(hrow,copy_sel0,gr,0),16'd0};
      end
    end endgenerate
    // gate select from regional ka copies (region 16/17 byte 2 = ka), one copy per two gate bytes: no 32-load ka decode
    genvar gb;
    wire [31:0] gsel_r;
    for(gb=0;gb<4;gb=gb+1) begin:g_gsel
      wire [1:0] gk=region_ka_c[16+gb/2][20:19] ^ ((MUT == 7) ? 2'd1 : 2'd0);
      ot_s81sl_vs_gsel8 u_gsel(.k(gk),.g0(gate[0][8*gb+:8]),.g1(gate[1][8*gb+:8]),.g2(gate[2][8*gb+:8]),.g3(gate[3][8*gb+:8]),.y(gsel_r[8*gb+:8]));
    end
    always @(*) gsel = gsel_r;
`else
    always @(*) begin
        for (rq = 0; rq < 4; rq = rq + 1) begin
            hrow[64 * rq +: 64] = hst[ep_q[rq] ? eqp_q[rq] : {ka_q[rq][3:1], 1'b0}][64 * rq +: 64];
            hra[64 * rq +: 64] = hst[{ka_q[rq][2:0], 1'b0}][64 * rq +: 64];
            hrb[64 * rq +: 64] = hst[{ka_q[rq][2:0], 1'b1}][64 * rq +: 64];
            xwsel[64 * rq +: 64] = hst[fl_q[rq]][64 * rq +: 64];
        end
        gsel = gate[(MUT == 7) ? ka[4:3] ^ 2'd1 : ka[4:3]];
    end
`endif
    function automatic [31:0] hw32(input [255:0] r, input [1:0] j, input [1:0] e);
        hw32 = {r[(4 * j + e) * 16 +: 16], 16'd0};
    endfunction
    function automatic [3:0] hw4(input [255:0] r,input [1:0] j,input [1:0] e,input integer part);
      hw4=r[(4*j+e)*16+4*part+:4];
    endfunction
    function automatic [7:0] hw8(input [255:0] r,input [1:0] j,input [1:0] e,input integer half);
      hw8=r[(4*j+e)*16+8*half+:8];
    endfunction
    always @(posedge clk or negedge rs_eng)
        if (!rs_eng) begin ve_rv <= 1'b0; ve_av <= 1'b0; gmask <= 4'd0; epend <= 1'b0;

`ifndef OT_S81SL_VS_SRAM
for (rq = 0; rq < 4; rq = rq + 1) ep_q[rq] <= 1'b0;
`endif
 end
        else begin
            ve_rv <= (eng_r && ka >= 8'd16 && er[0]) || epend;
            epend <= eng_r && ka >= 8'd16 && er[0];

`ifndef OT_S81SL_VS_SRAM
for (rq = 0; rq < 4; rq = rq + 1) ep_q[rq] <= eng_r && ka >= 8'd16 && er[0];
`endif

            ve_av <= eng_a;
            if (`S81_VS_ACC(113) && c_op == OP_ENG && !c_ph) gmask <= 4'd0;
            else if (gv_c) gmask <= gmask | (4'd1 << gc_c);
        end
    always @(posedge clk) begin
`ifndef OT_S81SL_VS_SRAM
        if (gv_c) gate[gc_c] <= gd_c;
`endif
        // REDUCE: arrivals 0..15 = h half rows into the stash; 16..79 = K / W of quad q -> ve
`ifndef OT_S81SL_VS_SRAM
        if (eng_r && ka < 8'd16) hst[ka[3:0]] <= xq_c;
`endif
        ve_rc <= eq[5:4];
`ifndef OT_S81SL_VS_SRAM
        for (i = 0; i < 4; i = i + 1) ve_rh[32 * i +: 32] <= hw32(hrow, eq[5:4], i[1:0]);
`endif
`ifdef OT_S81SL_VS_SRAM
        for(i=0;i<32;i=i+1) if(k_capture[i]) kst[8*i+:8] <= xq_c[8*i+:8];
        for(i=0;i<16;i=i+1) if(w_capture[i]) wst[8*i+:8] <= xq_c[128+8*i+:8];
`else
        if (eng_r && ka >= 8'd16 && !er[0]) kst <= xq_c;
        if (eng_r && ka >= 8'd16 && er[0]) wst <= xq_c[255:128];
`endif
        eqp <= eq0 | 6'd1;

`ifndef OT_S81SL_VS_SRAM
for (rq = 0; rq < 4; rq = rq + 1) eqp_q[rq] <= {ka_q[rq][3:1], 1'b1};
`endif

`ifdef OT_S81SL_VS_SRAM
        for(i=0;i<16;i=i+1) begin
          ve_rk[8*i+:8] <= hpend_data[i] ? kst[128+8*i+:8] : kst[8*i+:8];
          ve_rw[8*i+:8] <= (MUT == 8) ? (hpend_data[i] ? kst[128+8*i+:8] : kst[8*i+:8]) :
                                             (hpend_data[i] ? wst[8*i+:8] : xq_c[8*i+:8]);
        end
`else
        ve_rk <= epend ? kst[255:128] : kst[127:0];
        ve_rw <= (MUT == 8) ? (epend ? kst[255:128] : kst[127:0]) : (epend ? wst : xq_c[127:0]);
`endif
        // ADD: arrival s (copy j = ka[4:3], elements 8 s' .. 8 s' + 7, s' = ka[2:0]) = V row pair; h from half rows 2 s', 2 s' + 1
        ve_ac <= ka[4:3];
        for (i = 0; i < 4; i = i + 1) begin
`ifdef OT_S81SL_VS_SRAM
            ve_ah[32*i+:32] <= {hw4(hra,region_ka_c[8+i][28:27],i[1:0],3),hw4(hra,region_ka_c[8+i][20:19],i[1:0],2),hw4(hra,region_ka_c[8+i][12:11],i[1:0],1),hw4(hra,region_ka_c[8+i][4:3],i[1:0],0),16'd0};
            ve_ah[32*(i+4)+:32] <= {hw4(hrb,region_ka_c[12+i][28:27],i[1:0],3),hw4(hrb,region_ka_c[12+i][20:19],i[1:0],2),hw4(hrb,region_ka_c[12+i][12:11],i[1:0],1),hw4(hrb,region_ka_c[12+i][4:3],i[1:0],0),16'd0};
`else
            ve_ah[32 * i +: 32] <= hw32(hra, ka[4:3], i[1:0]); ve_ah[32 * (i + 4) +: 32] <= hw32(hrb, ka[4:3], i[1:0]);
`endif
        end
        ve_aval <= xq_c;
        ve_ag <= gsel;
        // ADD results: copy j's slots of half rows 2 s, 2 s + 1
        // (decoded constant-index slices: one-hot row pair x copy, no runtime part-select)
`ifndef OT_S81SL_VS_SRAM
        if (vov_c && op == OP_ENG && ph)
            for (i = 0; i < 16; i = i + 1)
                for (k = 0; k < 4; k = k + 1)
                    if ((i >> 1) == ko_e[2:0] && k == voc_c)
                        for (e2 = 0; e2 < 4; e2 = e2 + 1)
                            hst[i][(4 * k + e2) * 16 +: 16] <= voy_c[32 * (4 * (i & 1) + e2) + 16 +: 16];
`endif
    end
    // partial triples out; result / flush counters
    always @(posedge clk or negedge rs_flush)
        if (!rs_flush) begin e_v <= 1'b0; kp_e <= 3'd0; ko_e <= 6'd0; fl_e <= 5'd0; fl_on <= 1'b0;

`ifndef OT_S81SL_VS_SRAM
for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= 4'd0;
`endif
 end
        else begin
            e_v <= vpv_c;
            if (`S81_VS_ACC(114)) begin kp_e <= 3'd0; ko_e <= 6'd0; fl_e <= 5'd0; fl_on <= 1'b0;

`ifndef OT_S81SL_VS_SRAM
for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= 4'd0;
`endif
 end
            else begin
                if (vpv_c) kp_e <= kp_e + 3'd1;
                if (vov_c) begin ko_e <= ko_e + 6'd1; if (ko_e == 6'd31) fl_on <= 1'b1; end
                if (fl_on) begin fl_e <= fl_e + 5'd1; if (fl_e == 5'd15) fl_on <= 1'b0; end

`ifndef OT_S81SL_VS_SRAM
if (fl_on) for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= fl_q[rq] + 4'd1;
`endif

            end
        end
    always @(posedge clk) begin e_c <= vpc_c; e_d <= vpd_c; end

    // ================================================================ results: leaf-store write port, vq stream, done
    `S81_VS_CONTROL_KEEP reg [7:0] k_out; reg [127:0] sw_prev;
    wire [127:0] sw_w32 = {swr_c[63:48], 16'd0, swr_c[47:32], 16'd0, swr_c[31:16], 16'd0, swr_c[15:0], 16'd0};
    always @(posedge clk or negedge rs_out)
        if (!rs_out) begin x_wv <= 1'b0; u_v <= 1'b0; um_v <= 1'b0; k_out <= 8'd0; done <= 1'b0; end
        else begin
            x_wv <= 1'b0; u_v <= 1'b0; done <= 1'b0;
            um_v <= `S81_VS_ACC(115) && c_uq && (c_op == OP_SW || c_op == OP_QB);
            if (`S81_VS_ACC(115)) k_out <= 8'd0;
            else if (busy && !done) case (op)
                OP_SW: if (swv_c) begin
                    x_wv <= wb; u_v <= uq && k_out[0]; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_QB: if (arr) begin
                    u_v <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_RA: if (ra_row) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_ra + 8'd1 == n) done <= 1'b1;
                end
                OP_RB, OP_QR: if (xo_v) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_MOE: if (xo_v) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out == 8'd7) done <= 1'b1;
                end
                OP_ENG: if (!ph) begin
                    if (vpv_c && kp_e == 3'd3) done <= 1'b1;
                end else if (fl_on) begin
                    x_wv <= 1'b1;
                    if (fl_e == 5'd15) done <= 1'b1;
                end
                default: ;
            endcase
        end
`ifdef OT_S81SL_VS_SRAM
    (* keep="true" *) reg [15:0] swprev_capture;
    genvar spb;
    generate for(spb=0;spb<16;spb=spb+1) begin:g_swprev_byte
      always @(posedge clk) begin
        swprev_capture[spb]<=rsv[37] && sw_vi;
        if(swprev_capture[spb]) sw_prev[8*spb+:8]<=sw_w32[8*spb+:8];
      end
    end endgenerate
    wire [255:0] out_sw={128'd0,sw_w32};
    wire [255:0] out_usw={sw_w32,sw_prev};
    wire [255:0] out_qb=(MUT==5)?{xq_c[127:0],xq_c[255:128]}:xq_c;
    wire [255:0] out_rb={128'd0,xo_d[127:0]};
    genvar oby;
    generate for(oby=0;oby<32;oby=oby+1) begin:g_output_byte
      wire [7:0] ra_byte;
      if(oby<12) assign ra_byte=rad[8*oby+:8];
      else assign ra_byte=8'd0;
      ot_s81sl_vs_output8 #(.RWORD(oby/4)) u_byte(.clk(clk),.op(region_op_c[oby/2][16+4*(oby%2)+:4]),.sw(out_sw[8*oby+:8]),.usw(out_usw[8*oby+:8]),.qb(out_qb[8*oby+:8]),.rk(kra_output[oby]),.rar(rar_c[8*(oby%4)+:8]),.ra(ra_byte),.rb(out_rb[8*oby+:8]),.eng(xwsel[8*oby+:8]),.moe(xo_d[8*oby+:8]),.wd(x_wd[8*oby+:8]),.u(u[8*oby+:8]));
    end endgenerate
    always @(posedge clk) begin
        if (`S81_VS_ACC(116)) begin um_q <= c_imm[12]; um_b <= c_imm[13]; um_i <= c_imm[21:14]; end

        case (op)
            OP_SW: begin
                x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F;
 u_i <= j0 + k_out[3:1];
            end
            OP_QB: begin
 u_i <= j0 + k_out[2:0];
            end
            OP_RA: begin
                x_wa <= ob + {4'd0, k_ra[7:2]} + ((MUT == 6) ? 10'd1 : 10'd0);
                x_wm <= (k_ra[1:0] == 2'd3) ? 8'h0F : (k_ra[1:0] == 2'd2) ? 8'h07 : (k_ra[1:0] == 2'd1) ? 8'h03 : 8'h01;
            end
            OP_RB, OP_QR: begin x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F; end
            OP_ENG: begin x_wa <= a1 + {4'd0, fl_e[4:0], 1'b0}; x_wm <= 8'hFF; end
            default: begin x_wa <= ob + {1'b0, k_out[7:0], 1'b0}; x_wm <= 8'hFF; end   // MOE
        endcase
    end

`else
    always @(posedge clk) begin
        if (`S81_VS_ACC(116)) begin um_q <= c_imm[12]; um_b <= c_imm[13]; um_i <= c_imm[21:14]; end
        if (swv_c) sw_prev <= sw_w32;
        case (op)
            OP_SW: begin
                x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F; x_wd <= {128'd0, sw_w32};
                u <= {sw_w32, sw_prev}; u_i <= j0 + k_out[3:1];
            end
            OP_QB: begin
                u <= (MUT == 5) ? {xq_c[127:0], xq_c[255:128]} : xq_c; u_i <= j0 + k_out[2:0];
            end
            OP_RA: begin
                x_wa <= ob + {4'd0, k_ra[7:2]} + ((MUT == 6) ? 10'd1 : 10'd0);
                x_wm <= (k_ra[1:0] == 2'd3) ? 8'h0F : (k_ra[1:0] == 2'd2) ? 8'h07 : (k_ra[1:0] == 2'd1) ? 8'h03 : 8'h01;
                x_wd <= {128'd0, rar_c, rad};
                for (i = 0; i < 3; i = i + 1) if (k_ra[1:0] == i) x_wd[32 * i +: 32] <= rar_c;
            end
            OP_RB, OP_QR: begin x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F; x_wd <= {128'd0, xo_d[127:0]}; end
            OP_ENG: begin x_wa <= a1 + {4'd0, fl_e[4:0], 1'b0}; x_wm <= 8'hFF; x_wd <= xwsel; end
            default: begin x_wa <= ob + {1'b0, k_out[7:0], 1'b0}; x_wm <= 8'hFF; x_wd <= xo_d; end   // MOE
        endcase
    end

`endif

    // ---------------------------------------------------------------- faults (sticky)
    reg f_cmd, f_unit;
    always @(posedge clk or negedge rs_fault)
        if (!rs_fault) begin fault <= 1'b0; f_cmd <= 1'b0; f_unit <= 1'b0; end
        else begin
            f_cmd <= (sv_c && (busy || c_bad)) || (xqv_c && !busy) || (swv_c && op != OP_SW) || (rav_c && op != OP_RA) ||
                     (vpv_c && !(busy && op == OP_ENG && !ph)) || (vov_c && !(busy && op == OP_ENG && ph)) ||
                     (vov_c && voc_c != ko_e[4:3]) || (gv_c && gmask[gc_c]);
            f_unit <= (|mf) | (|af) | raf_c | swf_c | vef_c;
            fault <= fault | f_cmd | f_unit;
        end
`undef S81_VS_ACC
`undef S81_VS_CONTROL_KEEP
endmodule


`ifdef OT_S81SL_VS_SRAM
// Regional state and nibble operators remain separate synthesis hierarchies:
// equivalent source decodes must not merge into a single 512-bit mux select.
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_lane_ctl(input wire clk,rst_n,rst_v,busy,xqv,input wire[3:0]accept,cop,output wire[3:0]op,output wire[7:0]ka,output wire[31:0]op_copy,ka_copy,output wire arr);
  // Payload op captures and arrival counters own their decode in kept scopes.
  reg packet_xqv;
  always @(posedge clk or negedge rst_v) if(!rst_v) packet_xqv<=0;else packet_xqv<=xqv;
  genvar c;
  generate for(c=0;c<8;c=c+1) begin:g_op
    ot_s81sl_vs_op4 u_op(.clk(clk),.accept(accept[c/2]),.cop(cop),.q(op_copy[4*c+:4]));
  end
  for(c=0;c<4;c=c+1) begin:g_ka
    ot_s81sl_vs_ka8 u_ka(.clk(clk),.rst_n(rst_n),.accept(accept[c]),.busy(busy),.xqv(packet_xqv),.q(ka_copy[8*c+:8]));
  end endgenerate
  assign arr=packet_xqv && busy;
  assign op=op_copy[3:0];assign ka=ka_copy[7:0];
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_op4(input wire clk,accept,input wire[3:0]cop,output reg[3:0]q);
  always @(posedge clk) if(accept) q<=cop;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_ka8(input wire clk,rst_n,accept,busy,xqv,output reg[7:0]q);
  always @(posedge clk or negedge rst_n)
    if(!rst_n) q<=0;
    else if(accept) q<=0;
    else if(xqv && busy) q<=q+1'b1;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_busy6(input wire clk,rst_n,sv,bad,done,output wire[5:0]q);
  (* keep="true" *) reg [5:0] state;
  assign q=state;
  wire accept=sv && !state[0] && !bad;                     // state == busy (same accept/done/reset edges)
  always @(posedge clk or negedge rst_n)
    if(!rst_n) state<=0;
    else if(accept) state<=6'h3f;
    else if(done) state<=0;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_operand4 #(parameter [3:0]NEG=0,parameter integer MUT=0)(input wire clk,input wire[3:0]op,input wire[2:0]expert,input wire[3:0]ra,rb,m0,m1,x,acc,output reg[3:0]a,b);
  always @(posedge clk)
    if(op==4'd11) begin a<=ra;b<=(MUT==2)?4'd0:rb;end
    else if(op==4'd12) begin a<=m0;b<=m1;end
    else begin a<=expert==0?x:acc;b<=expert==0?NEG:x;end
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_output8 #(parameter integer RWORD=0)(input wire clk,input wire[3:0]op,input wire[1:0]rk,input wire[7:0]sw,usw,qb,rar,ra,rb,eng,moe,output reg[7:0]wd,u);
  // opcode decoded once in a kept leaf (one-hot), so the op copy bits drive the decoder, not every result-bit mux
  // two decoders: one for the wd byte, one for the u byte (each flag <= ~16 mux loads)
  wire d8,d9,d10,d11,d14,e8,e9,e10,e11,e14;
  ot_s81sl_vs_odec8 u_dec(.op(op),.d8(d8),.d9(d9),.d10(d10),.d11(d11),.d14(d14));
  ot_s81sl_vs_odec8 u_decu(.op(op),.d8(e8),.d9(e9),.d10(e10),.d11(e11),.d14(e14));
  wire [7:0] rsel=RWORD<3?(rk==RWORD?rar:ra):RWORD==3?rar:8'd0;
  always @(posedge clk) begin
    if(d8) wd<=sw;
    else if(d9) wd<=wd;
    else if(d10) wd<=rsel;
    else if(d11) wd<=rb;
    else if(d14) wd<=eng;
    else wd<=moe;
    if(e8) u<=usw;
    else if(e9) u<=qb;
  end
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_odec8(input wire[3:0]op,output wire d8,d9,d10,d11,d14);
  assign d8=op==4'd8; assign d9=op==4'd9; assign d10=op==4'd10; assign d11=op==4'd11 || op==4'd12; assign d14=op==4'd14;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_weight8 #(parameter integer BYTE=0,SECOND=0,MUT=0)(input wire clk,input wire[1:0]accept,input wire[2:0]sel,input wire[7:0]imm,input wire arr,input wire[3:0]op,input wire wr,input wire[7:0]ka,input wire[255:0]row,output reg[7:0]w);
  wire weight_arr=arr && op==4'd8 && wr && ka==0;
  reg [2:0] sel_c;
  always @(posedge clk) sel_c<=sel;
  (* keep="true" *) reg [2:0] ws[0:7];
  genvar b;
  generate for(b=0;b<8;b=b+1)begin:g_bit
    always @(posedge clk)
      if(accept[b/4]) begin ws[b]<=sel_c;w[b]<=imm[b];end
      else if(weight_arr) w[b]<=row[32*(ws[b] ^ ((MUT==9 && SECOND)?3'd1:3'd0))+8*BYTE+b];
  end endgenerate
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_xresult8 #(parameter integer LOW=0)(input wire clk,input wire[3:0]op,input wire[7:0]full,bf,qr,output reg[7:0]y);
  always @(posedge clk) y<=(LOW && op==4'd12)?qr:(op==4'd11)?full:bf;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_cmd8(input wire clk,accept,input wire[7:0]d,output reg[7:0]q);
  always @(posedge clk) if(accept) q<=d;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_accept32(input wire clk,rst_n,sv,busy_after,input wire[159:0]packet,input wire[6:0]incoming_op,input wire[1:0]stream_bad,input wire[3:0]gmask_after,output wire[31:0]q);
    wire [159:0] sd_c=packet;
    wire [3:0] gmask=gmask_after;
    wire is_qb=incoming_op[1];
    wire bad;
    (* keep="true" *) reg [31:0] accepted;
    assign q=accepted;
    always @(posedge clk or negedge rst_n)
      if(!rst_n) accepted<=0;
      else accepted<={32{sv && !busy_after && !bad}};
    localparam [3:0] OP_SW=8,OP_QB=9,OP_RA=10,OP_RB=11,OP_QR=12,OP_MOE=13,OP_ENG=14;
    wire [3:0] c_op=sd_c[3:0];
    wire [7:0] c_n=sd_c[31:24];
    wire [127:0] c_imm=sd_c[159:32];
    wire [2:0] c_j0=c_imm[24:22];
    wire c_ph=c_imm[30];
    wire [7:0] c_nsb = (is_qb) ? c_n : {1'b0, c_n[7:1]};          // vq sub-beats of a streaming op
    wire c_uq = c_imm[11] || is_qb;
    assign bad = (!incoming_op[0] && !is_qb && !incoming_op[2] && !incoming_op[3] && !incoming_op[4] && !incoming_op[5] &&
                  !incoming_op[6]) ||
                 (incoming_op[6] && (c_ph ? (c_n != 8'd32 || gmask != 4'hF) : c_n != 8'd64)) ||
                 (c_n == 8'd0) || (incoming_op[0] && c_n > 8'd16) || (incoming_op[5] && c_n != 8'd8) ||
                 (incoming_op[0] && c_imm[11] && stream_bad[0]) || (is_qb && stream_bad[1]);
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_pending #(parameter integer N=16)(input wire clk,rs,arr,input wire[3:0]op,input wire ph,input wire[7:0]ka,output wire[N-1:0]q);
  (* keep="true" *) reg [N-1:0] state;
  always @(posedge clk) state<={N{rs && arr && op==4'd14 && !ph && ka>=8'd16 && ka[0]}};
  assign q=state;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_qrhold8(input wire clk,en,input wire[7:0]d,output reg[7:0]q);
  always @(posedge clk) if(en) q<=d;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_qren(input wire v,input wire[3:0]op,input wire odd,output wire en);
  assign en=v && op==4'd12 && !odd;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_swweight8 #(parameter integer BYTE=0,MUT=0)(input wire clk,input wire[7:0]ka,input wire wr,input wire[7:0]w0,w1,output reg[7:0]q);
  localparam [31:0] MUT_WEIGHT=32'h3f800000;
  wire hi;
  ot_s81sl_vs_kge8 u_kge(.ka(ka),.wr(wr),.hi(hi));
  always @(posedge clk) q<=MUT==1?MUT_WEIGHT[8*BYTE+:8]:(hi ? w1 : w0);
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_kge8(input wire[7:0]ka,input wire wr,output wire hi);
  wire [7:0] kg=ka-{7'd0,wr};
  assign hi=kg >= 8'd8;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_bankctl8 #(parameter integer PARITY=0,COPY=0)(input wire clk,rs,pre,input wire[3:0]op_next,input wire ph_next,input wire[7:0]ka,input wire arr,accept,input wire ov,input wire[1:0]oc,output wire[7:0]fill,add);
  (* keep="true" *) reg [7:0] f,a;
  wire[7:0] ka_next=(!rs || accept)?8'd0:ka+{7'd0,arr};
  always @(posedge clk) begin
    f<={8{rs && pre && ka_next<8'd16 && ka_next[0]==PARITY}};
    a<={8{rs && ov && op_next==4'd14 && ph_next && oc==COPY}};
  end
  assign fill=f;assign add=a;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_kcapture8 #(parameter integer ODD=0)(input wire clk,rs,pre,input wire[7:0]ka,input wire arr,accept,output wire[7:0]q);
 // 8 kept flag copies (one per captured byte group of 16 loads); an un-kept output reg merged them into one 128-load FF.
 (* keep="true" *) reg [7:0] s;
 wire[7:0] kn=(!rs || accept)?8'd0:ka+{7'd0,arr};
 always @(posedge clk) s<={8{rs && pre && kn>=8'd16 && kn[0]==ODD}};
 assign q=s;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_dec2(input wire[1:0]k,output wire[3:0]y);
  assign y={k==2'd3,k==2'd2,k==2'd1,k==2'd0};
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_gsel8(input wire[1:0]k,input wire[7:0]g0,g1,g2,g3,output wire[7:0]y);
  wire [3:0] h;
  ot_s81sl_vs_dec2 u_dec(.k(k),.y(h));
  assign y=({8{h[0]}}&g0)|({8{h[1]}}&g1)|({8{h[2]}}&g2)|({8{h[3]}}&g3);
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_hqpre(input wire qv,busy_next,input wire[3:0]op_next,input wire ph_next,output wire q);
 assign q=qv && busy_next && op_next==4'd14 && !ph_next;
endmodule

`endif

(* keep_hierarchy="yes" *)
module ot_s81sl_vs_count2(input wire clk,rs,input wire[1:0]d,output reg[1:0]q);
 always @(posedge clk or negedge rs) if(!rs) q<=0;else q<=d;
endmodule
