`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM x-load (hgi-adapters, 2026-10-09): the peer of ot_hgi_sm_record's x port.  Reads the activation rows of
// A (P slots, K elements each, VM FP32) through NXC hfd_hgi_vm packet clients and writes the SM x store over the
// EXISTING x-write port of every SM (xw_en / xw_addr / xw_grp / xw_data 2,048 b, broadcast to the 32 SMs), in the
// smh fragment layout (tools/dshbm_matched_sm_seq.gen_op, BF16 / INT8 front):
//   fragment address a = g x 8 + t (g < op_g = ceil(K / 512), t < 8); column p (slot) lane j (< 64) at bit
//   p x XC + LB x 266 + 16 j (XC = 3,152, LB x 266 = 2,128) holds to_bf16(x_p[k]), k = (g x 64 + j) x 8 + t (0 past K);
//   beat b (xw_grp) of address a carries fragment bits [b x 2,048 +: 2,048], b < ceil(P x XC / 2,048) (= op_xb).
// One VM sector = the 8 t values of one lane j, so a group g is 64 x P sector reads into a P x 64 x 8 BF16 tile, then
// 8 x op_xb beats.  to_bf16 = RNE (hdc_golden; the golden of SM.MATVEC fmt 0 / 3 rounds x to BF16).
// BLOCK-DOT x (fmt 1 FP8 / fmt 2 FP4 weights; hgi-1010/d, the DS activation path): x is quantised HERE, exactly as the
//   golden's linear_q (hdc_golden_v41.quant_fp8: per 32-block amax, E4M3 codes + block exponent) by the qualified r25
//   activation quantiser ot_hdc_actquant (one block an edge), and laid out as the smh block-dot fragment
//   (tools/dshbm_matched_sm_seq.gen_op): lane j (< LA = 4 FP8 / 8 FP4) of column p at bit p XC + 266 j holds block
//   b = (g LA + j) 8 + t: 32 codes (8 b each) then the exponent (10 b); lanes past K / 32 blocks are 0.  Per fragment
//   address (g, t): the P x LA blocks are read (4 sectors each, two assembling at a time on the packet clients),
//   quantised into a P x 2,128-b register file (cleared per address), then the address's beats leave on the xw pins.
// Refusals (x_fault): A not VM (STREAM x enters from the SU stream, not here), A.base / A.stride not 8-word aligned,
//   block-dot K not a multiple of 32 (or 0), a non-finite element in a block-dot block (the quantiser's fault).
// STORAGE (FILL-9 2026-10-10): 32 ot_sram_1r1w_128x256_m1 macros m[t][q] (t < 8 fragment row, q < 4 lane quarter):
// word p (slot) of m[t][q] holds lanes 16q .. 16q + 15 of slot p, t-value t, as 16 x BF16.  A landing sector (p, j) is
// ONE masked word write in each of the 8 macros m[t][j >> 4] (16-b mask at slice j & 15); a beat reads the 4 macros
// m[t][*] at word p (1,024 b).
// PIPELINE (fe-push-hgi-1010, 2026-10-10; root cause of the fc210e160 routes: TT -545 post-CTS a / -109 routed b):
//   (1) macro out -> 8:1 t-select (s2_t binary select fanning out to 1,024 mux bits, 24 levels) -> rw in ONE cycle
//       across the macro field.  Now: a gated capture flop at each macro (cap = rd AND its own registered read
//       enable, zero otherwise), a registered OR-4 per (macro half, quarter) and a registered OR-2 into rw: no select
//       net, every stage local to its macros (no single-cycle wire > 504 um).
//   (2) held response -> priority select -> 4:1 x 274 mux -> 8 x RNE adders + a 21-b range compare -> write pins in
//       ONE cycle (hv -> wq_d 24 levels).  Now: L1 registers the selected sector, L2 converts (the range compare is
//       against a per-group running remainder, not g x 512 + ...), W1 per-quarter copy, W2 per-macro pin flops.
//   (3) read command: central decision -> per-quarter copy -> per-macro pin flops (enable / address replicated per
//       macro, kept), so no register drives the 32 macros' pins across the field.
//   (4) beat assembly registered (xb), xw_* are pure pin flops.
// BDW8 (smmv-b, 2026-10-12; physical spec el1011-hbm-smmv-b.log 10-12 07:25): BW8 = 1 routes block-dot x (fmt 1 / 2)
//   over the cluster's LOCAL VM slice 8-lane group (B2 lanearb slot 4; lane b <-> local bank b) on the low 8 lanes of
//   the rg_* / wrq* / wrr ports (ot_hgi_vm_wrd NL 8, GATHER).  Wave = 8 consecutive sectors = blocks (j, t), (j, t + 1)
//   (t even) of group g, slot p -> two ot_hdc_actquant (one block an edge each) -> registered lane write into a
//   ping-pong pair of TPAIR buffers (each = the two fragment addresses (g, t), (g, t + 1), as NBQ beat registers in
//   the BD layout above) -> the buffer's 2 nb beats leave on the xw pins (shift chain, as BD) while the next tpair
//   lands.  Order: per command g < Gn, tp < 4 (t = 2 tp), j < LA, p < P.  Same fragment layout and refusals as BD;
//   COMMAND-PIPELINED: the next command is taken as soon as the wave cursor is free (x_done pulses in command order).
//   Every stage registered: cursor -> 4-deep wave FIFO -> wrd -> R (rotate) -> 2 x actquant -> W (per buffer x
//   parity write copy) -> fragment -> E (beat) -> xw pins.  BW8 = 0 (default): unchanged.
//   bx (10-12): the cursor no longer claims a buffer before issuing (that held each buffer for the whole VM round trip,
//   ~3.3 edges a wave); it issues on landing credits into an LD 32 landing FIFO (after the quantisers) and a per-tpair
//   meta FIFO; THREE tpair buffers in a ring are opened by the write stage at the FIFO head, and emission chains buffer
//   to buffer, so the slice group sustains one wave an edge.  Mutant MUT_B8E: a buffer emits after its FIRST landing (still filling).
// The x-store write SEQUENCE is unchanged (tb_hgi_xload_lock vs the flop x-load ot_hgi_sm_xload_old); latency +6
// edges a beat (pipelined) and +3 edges a landing (once a group: emission waits for the write pipe to drain).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_xload #(
    parameter integer XW_FLOW = 0,        // opt-in finite retained x-write transport
    parameter integer NXC = 4,            // VM packet clients (reads in flight)
    parameter integer PMAX = 8,
    parameter integer MUT_M = 0,          // mutant (FILL-9): a landing sector's write mask on lane slice (j ^ 1) of its quarter
    parameter integer MUT_T = 0,          // mutant: lane j takes t from the wrong half (k = (g 64 + j) 8 + (7 - t))
    parameter integer MUT_BD = 0,         // mutant: a block-dot block lands in the neighbouring lane (j ^ 1)
    parameter integer BD = 0,             // hbm-relaunch-1011/xfp: 1 = native block-dot x (fmt 1 / 2); 0 = refuse (as main)
    parameter integer WVM = 0,            // smmv 3b: 1 = BF16 x (fmt 0 / 3) over a 32-lane VM wide READ group (die contract
                                          //   r25gq v7 D19: lane group lgE slot 0, ot_hgi_vm_lanearb client): one burst a
                                          //   column p a super-block of <= 16 groups, 32 sectors (= lanes j of one half
                                          //   group) land in ONE edge as full 256-b rows of 16 macros; emission of group g
                                          //   overlaps the landing of g + 1 (x word {g mod 16, p}).  Block-dot: packet path.
    parameter integer WLQ = 16,           // wide-lane credits a lane (the lane-group round trip)
    parameter integer WD = 8,             // waves outstanding (ot_hgi_vm_wrd response FIFO depth)
    parameter integer MUT_WV = 0,         // mutants: 1 the wave lands rotated one lane too far; 2 / 3 = ot_hgi_vm_wrd MUT 1 / 2
    parameter integer BW8 = 0,            // smmv-b BDW8: 1 = block-dot x over the local 8-lane slice group (needs BD, WVM 0)
    parameter integer W8D = 16,           // BW8: waves outstanding (>= the local group round trip for 1 wave an edge)
    parameter integer W8LQ = 16,          // BW8: credits a lane
    parameter integer MUT_B8 = 0,         // BW8 mutant: 1 = the gathered wave is rotated one lane too far
    parameter integer MUT_B8E = 0         // BW8 mutant (bx): a tpair buffer emits as soon as its FIRST wave landed
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output wire               x_rdy,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,          // smmv 3a: x-store slot base (fragment address offset; compiler-allocated)
    input wire                xw_ready,
    output wire               xw_last,
    output wire               x_done,
    output reg                x_fault,
    output wire               xw_en,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data,
    output wire [NXC*338-1:0] vmq,   // {v, payload 337}: v from a reset flop, payload from a data flop
    input  wire [NXC*274-1:0] vmr,
    // smmv 3b: the VM wide read lane group (WVM = 1; lanearb client: rg_req held a burst, lane b {v, sector15}, credits,
    // responses {v, data256} in order a lane).  WVM = 0: rg_req / wrq stay 0.
    output wire               rg_req,
    input  wire               rg_gnt,
    output wire [32*16-1:0]   wrq,
    input  wire [31:0]        wrq_cr,
    input  wire [32*257-1:0]  wrr
);
    reg px_en, px_last, legacy_done;
    reg [6:0] px_addr, px_grp; reg [2047:0] px_data;
    // Four transport credits cover two registered enable propagation stages, the pin beat in flight,
    // and an accepted seat. Credits are charged BEFORE the pin beat launches. The existing read/emit
    // pipeline retains all other operands. No command-sized FIFO and no reset on payload registers.
    reg go_ctl, go_em; wire transport_fault;
    wire emit_go = (XW_FLOW == 0) || (go_em && !transport_fault);
    wire emit_next = rv[RD-1] || be_v || k_bev;
    wire pin_last_next = k_xdone || (rv[RD-1] && rm_addr[RD-1] == {4'(gn-1),3'd7} && rm_b[RD-1] == nb-1) ||
        (be_v && be_a == {4'(gn-1),3'd7} && be_g == nb-1);
    generate if (XW_FLOW != 0) begin : g_xw_flow
        localparam integer W=2064, NS=(W+63)/64;
        reg [2:0] credits, count; reg hv, flow_done, flow_fault; wire [W-1:0] head;
        wire pop = hv && xw_ready;
        wire grant = emit_go && emit_next;
        wire [3:0] cr_next = {1'b0,credits} + 4'(pop) - 4'(grant);
        wire [3:0] cn_next = {1'b0,count} + 4'(px_en) - 4'(pop);
        wire [W-1:0] payload={px_last,1'b1,px_addr,px_grp,px_data};
        assign transport_fault=flow_fault;
        assign xw_en=hv && !flow_fault; assign xw_last=head[2063];
        assign xw_addr=head[2061:2055]; assign xw_grp=head[2054:2048]; assign xw_data=head[2047:0];
        // Transport completion is acceptance only. The native adapter must wait for matching final
        // native_release before reporting committed completion to the SM engine.
        assign x_done=flow_done;
        always @(posedge clk or negedge rst_c) begin
            if(!rst_c)begin credits<=4;count<=0;hv<=0;go_ctl<=0;go_em<=0;flow_done<=0;flow_fault<=0;end
            else begin
                flow_done<=pop && xw_last && !flow_fault;
                credits<=cr_next[2:0];count<=cn_next[2:0];hv<=cn_next!=0;
                go_ctl<=cr_next>2;go_em<=go_ctl;
                if(cr_next>4 || cn_next>4)flow_fault<=1;
`ifndef SYNTHESIS
                if(cr_next>4 || cn_next>4) $fatal(1,"XW_FLOW transport credit/seat invariant failed");
`endif
            end
        end
        genvar r;
        for(r=0;r<NS;r=r+1)begin:g_region
            localparam integer LO=r*64, WS=(W-LO<64)?W-LO:64;
            (* keep *) reg [2:0] local_count;
            reg [WS-1:0] seats[0:3];
            wire local_pop=local_count!=0 && xw_ready;
            wire [3:0] after_pop={1'b0,local_count}-4'(local_pop);
            always @(posedge clk or negedge rst_c)
                if(!rst_c)local_count<=0;
                else local_count<=3'(after_pop+4'(px_en));
            genvar k;
            for(k=0;k<4;k=k+1)begin:g_seat
                // Separate local row enables: at most64 payload loads, no queue-wide shift/select net.
                (* keep *) wire shift=local_pop && local_count>k+1;
                (* keep *) wire store=px_en && after_pop==k;
                always @(posedge clk)begin
                    if(k<3 && shift)seats[k]<=seats[(k<3)?k+1:k];
                    if(store)seats[k]<=payload[LO+:WS];
                end
            end
            assign head[LO+:WS]=seats[0]; // pure held register boundary, no data mux at the pins
        end
    end else begin:g_no_xw_flow
        assign transport_fault=1'b0;
        assign xw_en=px_en;assign xw_last=px_last;assign xw_addr=px_addr;assign xw_grp=px_grp;assign xw_data=px_data;
        assign x_done=legacy_done;
        always @(posedge clk or negedge rst_c)if(!rst_c)begin go_ctl<=0;go_em<=0;end else begin go_ctl<=1;go_em<=1;end
    end endgenerate
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer RD = 8;             // read pipe: r0 decision, r1 quarter copy, r2 pins, r3 macro out, r4 cap, r5 or4, r6 rw, r7 xb
    reg busy; reg [3:0] pp; reg [17:0] base; reg [17:0] st;
    reg [7:0] gn, g; reg [3:0] p_rd; reg [6:0] j_rd; reg [3:0] t; reg [6:0] b; reg [6:0] nb;
    reg signed [22:0] krem;                // K - g x 512 (elements of this group still inside K)
    // ---- reset: the port drives only the relay (design standard); control flops reset from rst_c, data flops never
    wire rst_c;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_c));
    // ---- read pipeline valids (reset) and metadata (data)
    reg [RD-1:0] rv;
    reg [6:0] rm_addr [0:RD-1]; reg [6:0] rm_b [0:RD-1]; reg rm_ok [0:RD-1];
    reg [2:0] r0_t; reg [6:0] r0_sp;
    reg [2047:0] xb;                       // r7: the assembled beat
    // ---- write pipeline: L1 (selected sector), L2 (converted), W1 (per-quarter copy), W2 (per-macro pins)
    reg l1_v, l2_v; reg [3:0] w1_v;
    reg [273:0] l1_d; reg [127:0] l2_d; reg [1:0] l2_q; reg [6:0] l2_a; reg [3:0] l2_l;
    reg [127:0] w1_d [0:3]; reg [6:0] w1_a [0:3]; reg [3:0] w1_l [0:3];
    // ---- read command per-quarter copy (r1): t one-hot + slot address
    reg [7:0] r1_oh [0:3]; reg [6:0] r1_sp [0:3];
    // ---- smmv 3b WIDE LANDING (WVM): ot_hgi_vm_wrd bursts -> R (rotate VM lane -> x lane, registered) -> C (BF16 + K
    //      range, registered) -> per-macro pins (vp_*) -> the macro write edge.  Every stage is a register; the 8-kb wave
    //      enters at the VM lane face (the block sits at the lane-group face; die stations <= 504 um in lanearb RLY).
    //      A wave = lanes j = 32 h .. 32 h + 31 of (group g, column p): it writes m[t][2 h], m[t][2 h + 1] (16 macros)
    //      at word {g mod 16, p} in ONE edge; wcnt[g mod 16] counts the landed waves (2 P = group complete).
    reg wm;                                // this command lands over the wide group (WVM && !block-dot)
    reg w_go; reg [14:0] w_s0; reg [15:0] w_ns; wire w_busy, w_done, w_fault;
    wire [31:0] wd_v; wire [32*15-1:0] wd_sec; wire [32*256-1:0] wd_dat;
    reg [3:0] wl_p; reg [7:0] wl_sb; reg wl_pend, wl_next; reg [8:0] wv;   // burst column, super-block group base, waves
    reg [4:0] wcnt [0:15];
    reg [20:0] kk;                         // K
    reg r_v; reg r_h; reg [7:0] r_g; reg [3:0] r_p; reg [8:0] r_rem; reg [32*256-1:0] r_d;
    reg cv_v; reg cv_h; reg [6:0] cv_a; reg [32*128-1:0] cv_d;
    generate if (WVM != 0) begin : g_wvm
        ot_hgi_vm_wrd #(.LQ(WLQ), .D(WD), .SW(15), .MUT(MUT_WV >= 2 ? MUT_WV - 1 : 0)) u_wrd (.clk(clk), .rst_n(rst_c),
            .start(w_go), .s0(w_s0), .ns(w_ns), .busy(w_busy), .done(w_done), .fault(w_fault), .req(rg_req), .gnt(rg_gnt),
            .q(wrq), .cr(wrq_cr), .rsp(wrr), .d_v(wd_v), .d_sec(wd_sec), .d_data(wd_dat),
            .g_v(1'b0), .g_s0(15'd0), .g_m(32'd0), .g_rdy(), .g_fin(1'b0), .d_w(), .d_s0(), .d_m());
    end else begin : g_nowvm
        if (BW8 == 0) begin : g_noport assign rg_req = 1'b0; assign wrq = '0; end
        assign w_busy = 1'b0; assign w_done = 1'b0; assign w_fault = 1'b0;
        assign wd_v = '0; assign wd_sec = '0; assign wd_dat = '0;
    end endgenerate
    // R: rotation (x lane l <- VM lane (l + s0) mod 32) + the wave's (g, h, p) and its K remainder clamped to [0, 256]
    always @(posedge clk) begin : wrot
        reg signed [23:0] rm; integer b;
        rm = $signed({3'd0, kk}) - $signed({4'd0, wl_sb + {7'd0, wv[8:1]}, 9'd0}) - $signed({15'd0, wv[0], 8'd0});
        for (integer l = 0; l < 32; l = l + 1) begin
            b = (l + w_s0[4:0] + (MUT_WV == 1 ? 1 : 0)) % 32;
            r_d[l*256 +: 256] <= wd_dat[b*256 +: 256];
        end
        r_h <= wv[0]; r_g <= wl_sb + {7'd0, wv[8:1]}; r_p <= wl_p;
        r_rem <= (rm < 0) ? 9'd0 : (rm > 24'sd256) ? 9'd256 : rm[8:0];
    end
    // C: BF16 (RNE) of every element inside K, 0 past it
    always @(posedge clk) begin
        for (integer l = 0; l < 32; l = l + 1) for (integer tv = 0; tv < 8; tv = tv + 1)
            cv_d[l*128 + 16*tv +: 16] <= ({1'b0, 8'(l * 8 + tv)} < r_rem) ? bf16(r_d[l*256 + 32*tv +: 32]) : 16'd0;
        cv_h <= r_h; cv_a <= {r_g[3:0], r_p[2:0]};
    end
    // ---- macro field
    wire [255:0] cap [0:31];               // gated capture of m[t][q] at index t * 4 + q (zero unless read)
    reg  [255:0] or4 [0:7];                // index h * 4 + q: OR of cap[t][q] over t in half h (t >> 2 == h)
    genvar gt, gq, gs;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
            // per-macro pin flops (kept: one copy a macro, so no register drives pins across the field)
            (* keep = 1 *) reg       rp_ce; (* keep = 1 *) reg rp_fire;  (* keep = 1 *) reg [6:0] rp_a;   (* keep = 1 *) reg rp_sel;
            (* keep = 1 *) reg       wp_ce;  (* keep = 1 *) reg [6:0] wp_a;   reg [15:0] wp_d;  reg [15:0] wp_m;
            // smmv 3b wide landing pins (WVM): a full 256-b row (16 lanes x BF16 of t-value gt) at word {g mod 16, p}
            (* keep = 1 *) reg       vp_ce;  (* keep = 1 *) reg [6:0] vp_a;   reg [255:0] vp_d;
            (* keep *) reg local_emit;
            always @(posedge clk or negedge rst_c)if(!rst_c)local_emit<=0;else local_emit<=go_ctl;
            wire macro_go=(XW_FLOW==0)||local_emit;
            reg [255:0] cq;
            wire [255:0] rd;
            wire [3:0] lsl = w1_l[gq] ^ ((MUT_M != 0) ? 4'd1 : 4'd0);
            always @(posedge clk or negedge rst_c) begin
                if (!rst_c) begin rp_ce <= 1'b0; rp_fire <= 1'b0; rp_sel <= 1'b0; wp_ce <= 1'b0; vp_ce <= 1'b0; end
                else begin
                    // Freeze the SRAM's own synchronous read stage too. Predict the next local
                    // enable phase in a PIN FLOP; a paused pipeline must not overwrite its pending read.
                    rp_fire <= ((XW_FLOW==0)||go_ctl) && (macro_go ? (rv[1] && r1_oh[gq][gt]) : rp_ce);
                    if(macro_go)begin rp_ce <= rv[1] && r1_oh[gq][gt]; rp_sel <= rp_ce; end wp_ce <= w1_v[gq];
                           vp_ce <= (WVM != 0) && cv_v && cv_h == (gq / 2); end
            end
            always @(posedge clk) begin
                if(macro_go)rp_a <= r1_sp[gq];
                wp_a <= w1_a[gq]; wp_d <= w1_d[gq][16 * gt +: 16]; wp_m <= 16'd1 << lsl;
                if(macro_go)cq <= rd & {256{rp_sel}};                                      // capture: zero unless this macro was read
                vp_a <= cv_a;
                for (integer ll = 0; ll < 16; ll = ll + 1) vp_d[16 * ll +: 16] <= cv_d[((gq % 2) * 16 + ll) * 128 + 16 * gt +: 16];
            end
            wire [255:0] wmask;
            for (gs = 0; gs < 16; gs = gs + 1) begin : g_m
                assign wmask[16 * gs +: 16] = {16{wp_m[gs]}};
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk),
                .r_ce_in(rp_fire), .r_addr_in(rp_a), .rd_out(rd),
                .w_ce_in(wp_ce || vp_ce), .w_addr_in(vp_ce ? vp_a : wp_a), .wd_in(vp_ce ? vp_d : {16{wp_d}}),
                .w_mask_in(vp_ce ? {256{1'b1}} : wmask), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            assign cap[gt * 4 + gq] = cq;
        end
    end endgenerate
    always @(posedge clk) for (integer h = 0; h < 2; h = h + 1) for (integer q = 0; q < 4; q = q + 1)
        if(emit_go)or4[h * 4 + q] <= cap[(4 * h + 0) * 4 + q] | cap[(4 * h + 1) * 4 + q] | cap[(4 * h + 2) * 4 + q] |
                          cap[(4 * h + 3) * 4 + q];
    reg [1023:0] rw;                       // the beat's slot word (OR-2 of the halves)
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) if(emit_go)rw[256 * q +: 256] <= or4[q] | or4[4 + q];
    // ---- VM responses
    reg [NXC-1:0] hv;                      // a client's response held, not yet landed
    reg [273:0] hdat [0:NXC-1];
    reg [10:0] got;                        // sectors landed for this group
    integer cl; reg lsel_v; integer lsel;
    always @* begin
        lsel_v = 1'b0; lsel = 0;
        for (cl = NXC - 1; cl >= 0; cl = cl - 1) if (hv[cl]) begin lsel_v = 1'b1; lsel = cl; end
    end
    reg [1:0] ph;                          // 0 read, 1 emit, 2 done
    reg [273:0] vr [0:NXC-1];
    always @(posedge clk) for (integer cv = 0; cv < NXC; cv = cv + 1) vr[cv] <= vmr[cv*274 +: 274];
    reg [NXC-1:0] cbusy;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    // beat b of fragment (g, t): the fragment holds slot p's lanes at [p XC + XOFF, + 1,024); slot blocks are 3,152
    // apart with a 2,128-b gap > the 2,048-b beat, so a beat overlaps AT MOST ONE slot: a static (p, offset) per b
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    function automatic integer bslot(input integer bb);       // the slot a beat overlaps, -1 none
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    wire [3:0] tt = MUT_T ? (4'd7 - t) : t;
    wire [2047:0] beats [0:NBMAX-1];
    genvar gb;
    generate for (gb = 0; gb < NBMAX; gb = gb + 1) begin : g_beat
        localparam integer PS = bslot(gb);
        localparam integer OFF = (PS < 0) ? 0 : PS * XC + XOFF - gb * 2048;   // slot block start rel. to the beat
        if (PS < 0) begin : g_none
            assign beats[gb] = 2048'd0;
        end else if (OFF >= 0) begin : g_pos
            wire [4095:0] sh = {3072'd0, rw} << OFF;
            assign beats[gb] = sh[2047:0];
        end else begin : g_neg
            wire [1023:0] sh = rw >> (-OFF);
            assign beats[gb] = {1024'd0, sh};
        end
    end endgenerate
    function automatic [3:0] slot_of(input [6:0] bb);
        integer x; slot_of = 4'd0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0) slot_of = bslot(x);
    endfunction
    function automatic in_slot(input [6:0] bb, input [3:0] np);
        integer x; in_slot = 1'b0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0 && bslot(x) < np) in_slot = 1'b1;
    endfunction
    // ---- command pin flop (the x_* decode does not run from the pins): +1 edge a command
    reg cmd_v; reg [6:0] c_xb; reg [39:0] c_base; reg [20:0] c_n; reg [3:0] c_p; reg [31:0] c_stride; reg [1:0] c_space, c_fmt;
    assign x_rdy = !busy && !cmd_v;
    always @(posedge clk) if (x_v && x_rdy) begin
        c_base <= x_base; c_n <= x_n; c_p <= x_p; c_stride <= x_stride; c_space <= x_space; c_fmt <= x_fmt; c_xb <= x_xb;
    end
    wire c_bdf = (BD != 0) && (c_fmt == 2'd1 || c_fmt == 2'd2);
    wire c_bad = ((BD == 0) && (c_fmt == 2'd1 || c_fmt == 2'd2)) || c_space != 2'd1 || |c_base[2:0] || |c_stride[2:0] || c_p > PMAX || c_p == 4'd0 ||
                 (c_bdf && (|c_n[4:0] || c_n == 21'd0));
    // ---- block-dot state
    reg bd; reg [3:0] la; reg [15:0] nbk;  // fmt 1 / 2; lanes a fragment column; K / 32 blocks
    reg [1:0] bph;                         // 1 read + quantise address (g, t), 2 emit its beats
    reg [3:0] bp; reg [3:0] bj; reg [1:0] bs; reg asl;   // issue cursor: column, lane, sector, assembly slot
    reg [15:0] bq_exp, bq_got; reg bq_iss_done; reg bflt;
    reg [1023:0] ab [0:1]; reg [2:0] acnt [0:1]; reg [3:0] ap [0:1]; reg [3:0] aj [0:1]; reg [1:0] aact;
    wire aq_vo, aq_f; wire [255:0] aq_q; wire signed [9:0] aq_e;
    reg aq_v; reg [1023:0] aq_x; reg [7:0] aq_tg; reg [7:0] tgf [0:15]; reg [3:0] tgh, tgt;
    // EMIT STORE (hbm-relaunch-1011/xfp, structural): the address's fragment is built in NBQ beat registers bdb[k]
    // (fragment bits [k 2,048 +: 2,048]).  A quantised block (slot p, lane j) is written at its STATIC fragment
    // position p XC + 266 j through a registered write stage (one-hot lane enable + the 266-b word replicated into
    // fragment space: no dynamic part-select).  Emission shifts the chain one beat an edge (bdb[k] <= bdb[k + 1], zero
    // in at the top) and takes bdb[0]: no NBQ:1 x 2,048-b beat mux and no beat-index fanout; after nb shifts the
    // written beats (< nb) are gone and the chain is all-zero again, so no per-address clear.  One clear per command
    // (bclr, a per-beat copy of start).
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    wire bshift;
    localparam integer NL = PMAX * 8;
    reg w_v; reg [NL-1:0] w_oh; reg [265:0] w_d;
    reg [NBQ-1:0] bclr;
    reg [2047:0] bdb [0:NBQ-1];
    wire [NBQ*2048-1:0] fd, fm;
    genvar gl, gk;
    generate if (BD != 0) begin : g_bd
        ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_c), .v(aq_v), .fp4(1'b0), .x(aq_x), .vo(aq_vo), .q(aq_q), .e(aq_e),
                              .y(), .fault(aq_f));
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_l
            localparam integer LO = (gl / 8) * XC + 266 * (gl % 8);
            assign fd[LO +: 266] = w_d;
            assign fm[LO +: 266] = {266{w_oh[gl]}};
            if (gl % 8 == 7) begin : g_gap      // the slot's gap up to the next slot (and the beat padding past PMAX)
                localparam integer GE = ((gl / 8) == PMAX - 1) ? NBQ * 2048 : (gl / 8 + 1) * XC;
                assign fd[GE - 1 : LO + 266] = '0;
                assign fm[GE - 1 : LO + 266] = '0;
            end
        end
        for (gk = 0; gk < NBQ; gk = gk + 1) begin : g_k
            always @(posedge clk) begin
                if (bclr[gk]) bdb[gk] <= 2048'd0;
                else if (bshift) bdb[gk] <= (gk == NBQ - 1) ? 2048'd0 : bdb[(gk == NBQ - 1) ? gk : gk + 1];
                else if (w_v) bdb[gk] <= (bdb[gk] & ~fm[gk*2048 +: 2048]) | (fd[gk*2048 +: 2048] & fm[gk*2048 +: 2048]);
            end
        end
    end else begin : g_nobd
        assign aq_vo = 1'b0; assign aq_f = 1'b0; assign aq_q = '0; assign aq_e = '0;
        assign fd = '0; assign fm = '0;
        always @(posedge clk) bdb[0] <= 2048'd0;
    end endgenerate
    reg be_v; reg [6:0] be_a, be_g; reg [2047:0] be_d;   // a block-dot beat on its way to the xw pins
    wire [15:0] blk = ({8'd0, g} * {12'd0, la} + {12'd0, bj}) * 16'd8 + {12'd0, t};
    wire blk_ok = blk < nbk;
    wire [31:0] wdb = {14'd0, base} + bp * {14'd0, st} + {blk, 5'd0} + {bs, 3'd0};
    wire bd_rd = busy && ph == 2'd3 && bph == 2'd1;
    assign bshift = emit_go && busy && ph == 2'd3 && bph == 2'd2;
    wire bd_issue = bd_rd && !bq_iss_done && bp < pp && blk_ok && found && !aact[asl];
    reg bq_v; reg bq_s;                    // a complete block -> the quantiser (older slot first)
    always @* begin
        bq_v = 1'b0; bq_s = 1'b0;
        if (aact[!asl] && acnt[!asl] == 3'd4) begin bq_v = 1'b1; bq_s = !asl; end
        else if (aact[asl] && acnt[asl] == 3'd4) begin bq_v = 1'b1; bq_s = asl; end
    end
    wire bd_done_rd = bd_rd && bq_iss_done && bq_got == bq_exp && !aact[0] && !aact[1] && !aq_v;
    wire be_last = bph == 2'd2 && b == nb - 7'd1;
    // BW8: block-dot commands go to the 8-lane pipeline (k_take); the command flop holds until taken; a packet / WVM
    // command waits until the BW8 pipeline is empty (the xw pins and legacy_done order are shared)
    wire k_cmd = (BW8 != 0) && c_bdf;
    wire k_take, k_wflt, k_cidle, k_allidle, k_xdone, k_xflt, k_bev; wire [6:0] k_bea, k_beg; wire [2047:0] k_bed;
    wire start = cmd_v && !c_bad && !k_cmd && ((BW8 == 0) || k_allidle);
    // ---- VM packet requests: valid (reset) + payload (data)
    reg [NXC-1:0] vq_v; reg [336:0] vq_d [0:NXC-1];
    genvar gc;
    generate for (gc = 0; gc < NXC; gc = gc + 1) begin : g_vq
        assign vmq[gc*338 +: 338] = {vq_v[gc], vq_d[gc]};
    end endgenerate
    // ---- shared decisions
    reg found; integer cf; reg [31:0] wd;
    always @* begin
        found = 1'b0; cf = 0;
        for (integer cc = NXC - 1; cc >= 0; cc = cc - 1) if (!cbusy[cc]) begin found = 1'b1; cf = cc; end
        wd = {14'd0, base} + p_rd * {14'd0, st} + {g, 9'd0} + {j_rd, 3'd0};
    end
    wire rd_ph = busy && ph == 2'd0, em_ph = busy && ph == 2'd1;
    wire issue = rd_ph && found && p_rd < pp && !wm;
    reg [NXC-1:0] take;
    always @* for (integer ct = 0; ct < NXC; ct = ct + 1) take[ct] = (rd_ph || bd_rd) && cbusy[ct] && !hv[ct] && vr[ct][273] && !vr[ct][256];
    // a landing waits until no read is still on its way to the macro pins (write-after-read order of the field)
    wire rd_pins_busy = |rv[2:0];
    wire land = rd_ph && lsel_v && !rd_pins_busy;
    wire wr_busy = l1_v || l2_v || |w1_v;
    wire [3:0] sob = slot_of(b);
    wire to_emit = rd_ph && (wm ? (wcnt[g[3:0]] == {pp, 1'b0} && g < wl_sb + 8'd16)   // WVM: the group's 2 P waves at the pins
                                : (got == {pp, 6'd0} && !wr_busy));  // every landed sector written (W2 is the macro write edge)
    // WVM bursts: column wl_p of super-block wl_sb (groups [wl_sb, wl_sb + 16) cap gn); the next super-block launches
    // once emission has reached it (its x words reuse the slots of the one before)
    wire [7:0] sb_ng = (gn - wl_sb > 8'd16) ? 8'd16 : gn - wl_sb;
    wire w_launch = busy && wm && wl_pend && !w_busy && !w_go;
    wire sb_adv = busy && wm && wl_next && rd_ph && g == wl_sb + 8'd16 && !w_busy;
    wire last_b = b == nb - 7'd1, last_bt = last_b && t == 4'd7, last_g = g == gn - 8'd1;
    wire fin = busy && ph == 2'd2 && !(|rv) && !be_v && !(wm && (w_busy || w_go));   // last beat out
    // ---- control (reset)
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin cmd_v <= 1'b0; busy <= 1'b0; legacy_done <= 1'b0; x_fault <= 1'b0; px_en <= 1'b0; vq_v <= 0;
                          cbusy <= 0; ph <= 0; hv <= 0; rv <= 0; l1_v <= 1'b0; l2_v <= 1'b0; w1_v <= 4'd0;
                          bd <= 1'b0; bph <= 2'd0; aact <= 2'b00; aq_v <= 1'b0; tgh <= 4'd0; tgt <= 4'd0; be_v <= 1'b0;
                          bflt <= 1'b0; wm <= 1'b0; w_go <= 1'b0; wl_pend <= 1'b0; wl_next <= 1'b0; r_v <= 1'b0;
                          cv_v <= 1'b0; for (integer z = 0; z < 16; z = z + 1) wcnt[z] <= 5'd0; end
        else begin
            legacy_done <= emit_go && ((fin && !(bd && bflt)) || (k_xdone && !k_xflt));
            if ((fin && bd && bflt) || (k_xdone && k_xflt)) x_fault <= 1'b1;
            if(emit_go)rv <= {rv[RD-2:0], em_ph}; px_en <= emit_go && emit_next;
            if(emit_go)px_last<=pin_last_next;
            l1_v <= land; l2_v <= l1_v;
            for (integer wq = 0; wq < 4; wq = wq + 1) w1_v[wq] <= l2_v && l2_q == wq;
            cmd_v <= (x_v && x_rdy) ? 1'b1 : (BW8 != 0 && cmd_v && !c_bad && !start && !k_take) ? 1'b1 : 1'b0;
            if ((cmd_v && c_bad) || k_wflt || transport_fault) x_fault <= 1'b1;
            if (start) begin busy <= 1'b1; ph <= c_bdf ? 2'd3 : 2'd0; bd <= c_bdf; bph <= 2'd1; aact <= 2'b00; bflt <= 1'b0;
                             wm <= (WVM != 0) && !c_bdf; wl_pend <= (WVM != 0) && !c_bdf; wl_next <= 1'b0;
                             for (integer z = 0; z < 16; z = z + 1) wcnt[z] <= 5'd0; end
            // smmv 3b wide landing control
            w_go <= w_launch;
            r_v <= |wd_v; cv_v <= r_v;
            if (cv_v) wcnt[cv_a[6:3]] <= wcnt[cv_a[6:3]] + 5'd1;
            if (wm && w_done) begin
                if (wl_p == pp - 4'd1) begin wl_pend <= 1'b0; wl_next <= ({1'b0, wl_sb} + 9'd16 < {1'b0, gn}); end
            end
            if (sb_adv) begin wl_next <= 1'b0; wl_pend <= 1'b1; for (integer z = 0; z < 16; z = z + 1) wcnt[z] <= 5'd0; end
            if (wm && w_fault) x_fault <= 1'b1;
            vq_v <= {NXC{1'b0}};
            if (issue || bd_issue) begin vq_v[cf] <= 1'b1; cbusy[cf] <= 1'b1; end
            for (integer ch = 0; ch < NXC; ch = ch + 1) if (take[ch]) hv[ch] <= 1'b1;
            if (land) begin hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0; end
            // block-dot: land one held sector an edge into its assembly slot; complete blocks -> the quantiser
            aq_v <= 1'b0; if(emit_go)be_v <= 1'b0;
            if (bd_rd && lsel_v) begin hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0; end
            if (bd_issue && bs == 2'd3) aact[asl] <= 1'b1;
            if (bd_rd && bq_v) begin aq_v <= 1'b1; aact[bq_s] <= 1'b0; end
            if (aq_v) tgt <= tgt + 4'd1;
            if (ph == 2'd3 && aq_vo) begin tgh <= tgh + 4'd1; if (aq_f) bflt <= 1'b1; end
            if (bd_done_rd) bph <= 2'd2;
            if (emit_go && busy && ph == 2'd3 && bph == 2'd2) begin
                be_v <= 1'b1;
                if (be_last) begin
                    if (t == 4'd7 && g == gn - 8'd1) ph <= 2'd2; else bph <= 2'd1;
                end
            end
            if (to_emit) ph <= 2'd1;
            if (emit_go && em_ph && last_bt) ph <= last_g ? 2'd2 : 2'd0;
            if (emit_go && fin) begin busy <= 1'b0; ph <= 2'd0; end
        end
    end
    // ---- data (no reset)
    always @(posedge clk) begin
        if (start) begin
            base <= c_base[17:0]; pp <= c_p; st <= c_stride[17:0]; krem <= {2'b00, c_n}; kk <= c_n;
            wl_p <= 4'd0; wl_sb <= 8'd0;
            gn <= ((c_n - 21'd1) >> 9) + 8'd1; g <= 8'd0; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0;
            nb <= ({12'd0, c_p} * 16'd3152 + 16'd2047) >> 11;    // 16 b: P x XC reaches 25,216
            la <= (c_fmt == 2'd2) ? 4'd8 : 4'd4; nbk <= c_n[20:5];
            if (c_bdf) begin
                // Gn = ceil(ceil(nb / 8) / LA) groups: FP8 ceil(K / 1,024), FP4 ceil(K / 2,048)
                gn <= (c_fmt == 2'd2) ? ((c_n - 21'd1) >> 11) + 8'd1 : ((c_n - 21'd1) >> 10) + 8'd1;
                t <= 4'd0; b <= 7'd0; bp <= 4'd0; bj <= 4'd0; bs <= 2'd0; asl <= 1'b0;
                bq_exp <= 16'd0; bq_got <= 16'd0; bq_iss_done <= 1'b0; acnt[0] <= 3'd0; acnt[1] <= 3'd0;
            end
        end
        // ---- block-dot data path
        if (bd_rd && !bq_iss_done) begin
            if (bp >= pp) bq_iss_done <= 1'b1;
            else if (!blk_ok) begin                     // a block past K / 32: skipped (its lanes stay 0)
                if (bj == la - 4'd1) begin bj <= 4'd0; bp <= bp + 4'd1; end else bj <= bj + 4'd1;
            end else if (bd_issue) begin
                vq_d[cf] <= {1'b0, wdb[29:3], 5'd0, 256'd0, 32'd0, {5'd0, asl, bs, bp, bj}};
                if (bs == 2'd3) begin
                    bs <= 2'd0; ap[asl] <= bp; aj[asl] <= bj; asl <= !asl; bq_exp <= bq_exp + 16'd1;
                    if (bj == la - 4'd1) begin bj <= 4'd0; bp <= bp + 4'd1; end else bj <= bj + 4'd1;
                end else bs <= bs + 2'd1;
            end
        end
        if (bd_rd && lsel_v) begin : bland                   // tag {slot, sector, p, j}
            reg sl_; reg [1:0] ss_; sl_ = hdat[lsel][267]; ss_ = hdat[lsel][266:265];
            ab[sl_][256*ss_ +: 256] <= hdat[lsel][255:0];
            acnt[sl_] <= ((bq_v && bq_s == sl_) ? 3'd0 : acnt[sl_]) + 3'd1;
        end
        if (bd_rd && bq_v) begin
            aq_x <= ab[bq_s]; aq_tg <= {ap[bq_s], aj[bq_s]};
            if (!(lsel_v && hdat[lsel][267] == bq_s)) acnt[bq_s] <= 3'd0;
        end
        if (aq_v) tgf[tgt] <= aq_tg;                         // the quantiser is in order: tags ride
        // registered lane write (W): one-hot lane enable {p, j} + the word; bq_got counts WRITTEN blocks
        w_v <= ph == 2'd3 && aq_vo;
        w_oh <= {NL{1'b0}};
        if (ph == 2'd3 && aq_vo) w_oh[{tgf[tgh][7:4], 3'd0} + {4'd0, tgf[tgh][2:0] ^ MUT_BD[2:0]}] <= 1'b1;
        if (w_v) bq_got <= bq_got + 16'd1;
        bclr <= {NBQ{start}};
        if (ph == 2'd3 && aq_vo) begin
            w_d <= {aq_e, aq_q};
        end
        if (emit_go && busy && ph == 2'd3 && bph == 2'd2) begin
            be_a <= {g[3:0], t[2:0]}; be_g <= b; be_d <= bdb[0];
            if (be_last) begin
                b <= 7'd0;
                bp <= 4'd0; bj <= 4'd0; bs <= 2'd0; bq_exp <= 16'd0; bq_got <= 16'd0; bq_iss_done <= 1'b0;
                if (t == 4'd7) begin t <= 4'd0; if (g != gn - 8'd1) g <= g + 8'd1; end else t <= t + 4'd1;
            end else b <= b + 7'd1;
        end
        if (w_launch) begin
            w_s0 <= 15'(({14'd0, base} + {28'd0, wl_p} * {14'd0, st}) >> 3) + 15'({wl_sb, 6'd0});
            w_ns <= {2'd0, sb_ng, 6'd0}; wv <= 9'd0;
        end
        if (|wd_v) wv <= wv + 9'd1;
        if (wm && w_done && wl_p != pp - 4'd1) wl_p <= wl_p + 4'd1;
        if (sb_adv) begin wl_sb <= wl_sb + 8'd16; wl_p <= 4'd0; end
        if (issue) begin
            vq_d[cf] <= {1'b0, wd[29:3], 5'd0, 256'd0, 32'd0, {5'd0, p_rd, j_rd}};
            if (j_rd == 7'd63) begin j_rd <= 7'd0; p_rd <= p_rd + 4'd1; end else j_rd <= j_rd + 7'd1;
        end
        for (integer cd = 0; cd < NXC; cd = cd + 1) if (take[cd]) hdat[cd] <= vr[cd];
        // landing: L1 = the selected held sector, L2 = BF16 + range, W1 = per-quarter copy (W2 = per-macro pins)
        if (land) l1_d <= hdat[lsel];
        begin : l2c
            reg [3:0] lp; reg [6:0] lj; reg [15:0] v [0:7];
            lp = l1_d[267:264]; lj = l1_d[263:257];                 // tag [272:257] = {p 4, j 7} low bits
            for (integer wv = 0; wv < 8; wv = wv + 1)
                v[wv] = ($signed({13'd0, lj, 3'd0}) + wv < krem) ? bf16(l1_d[32*wv +: 32]) : 16'd0;
            if (l1_v) begin
                l2_q <= lj[5:4]; l2_a <= {3'd0, lp}; l2_l <= lj[3:0];
                l2_d <= {v[7], v[6], v[5], v[4], v[3], v[2], v[1], v[0]};
            end
        end
        for (integer wc = 0; wc < 4; wc = wc + 1) if (l2_v && l2_q == wc) begin
            w1_d[wc] <= l2_d; w1_a[wc] <= l2_a; w1_l[wc] <= l2_l;
        end
        if (rd_ph) got <= got + {10'd0, land};
        if (to_emit) begin t <= 4'd0; b <= 7'd0; end
        // read pipeline: r0 decision -> r1 per-quarter copy -> r2 macro pins -> r3 macro out -> r4 cap -> r5 or4
        //                -> r6 rw -> r7 xb (beat) -> xw pins
        if (emit_go && em_ph) begin
            r0_t <= tt[2:0]; r0_sp <= wm ? {g[3:0], sob[2:0]} : {3'd0, sob};
            rm_addr[0] <= {g[3:0], t[2:0]}; rm_b[0] <= b; rm_ok[0] <= in_slot(b, pp);
            if (last_b) begin
                b <= 7'd0;
                if (t == 4'd7 && !last_g) begin
                    g <= g + 8'd1; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; krem <= krem - 23'sd512;
                end
                t <= t + 4'd1;
            end else b <= b + 7'd1;
        end
        for (integer q = 0; q < 4; q = q + 1) begin if(emit_go)begin r1_oh[q] <= 8'd1 << r0_t; r1_sp[q] <= r0_sp;end end
        for (integer s = 1; s < RD; s = s + 1) begin
            if(emit_go)begin rm_addr[s] <= rm_addr[s - 1]; rm_b[s] <= rm_b[s - 1]; rm_ok[s] <= rm_ok[s - 1];end
        end
        // r7 (xb): the beat assembled from rw (r6) under its stage-6 beat index; xw_* = pin flops of xb
        if (emit_go && rv[RD-2]) xb <= rm_ok[RD-2] ? beats[rm_b[RD-2]] : 2048'd0;
        if (emit_go && rv[RD-1]) begin px_addr <= rm_addr[RD-1] + c_xb; px_grp <= rm_b[RD-1]; px_data <= xb; end
        if (emit_go && be_v) begin px_addr <= be_a + c_xb; px_grp <= be_g; px_data <= be_d; end
        if (emit_go && k_bev) begin px_addr <= k_bea; px_grp <= k_beg; px_data <= k_bed; end
    end
    // =================================================================================================================
    // BDW8: block-dot x over the local 8-lane slice group (BW8 = 1)
    // =================================================================================================================
    generate if (BW8 != 0) begin : g_bw8
        if (BD == 0 || WVM != 0) begin : g_chk
            $error("ot_hgi_sm_xload: BW8 needs BD = 1 and WVM = 0 (the 8-lane group is the block-dot x path)");
        end
        // bx (10-12, structural rate fix): the w8_L1 trace showed ~3.3 edges a wave (262 cyc a K 5,120 load) because the
        // cursor CLAIMED a tpair buffer before issuing its waves, so each of the 2 buffers was held for issue + VM round
        // trip + quantiser + emission (~26 edges) per 4 waves.  Now the cursor runs ahead on LANDING CREDITS (LD) and
        // per-tpair META (MQD, pushed at the tpair's first step) only; the quantised waves land in an LD-deep landing FIFO;
        // the write stage opens a buffer for the head tpair and pops its waves (the tpair's last pushed wave carries a
        // LAST tag; a tpair with no wave inside K opens complete), so a buffer is held for fill + emission only;
        // NBF = 3 buffers in a ring (fill / full / emit) and emission chains buffer to buffer with no bubble, so the xw
        // pins take a beat every edge and the group sustains 1 wave an edge (beats = waves at P 1 FP8).
        localparam integer QD = 32, LD = 32, MQD = 4, NBF = 3;
        // ---- command / cursor (issue side)
        reg cidle; reg [14:0] cb, cs; reg [3:0] cp, cla; reg [15:0] cnbk; reg [7:0] cgn, cg; reg [6:0] cxb, cnb;
        reg [1:0] ctp; reg [3:0] cj, cpi; reg [7:0] cgj; reg [14:0] crow;
        // ---- tpair meta FIFO (cursor -> write stage): {xb 7, g 4, tp 2, nb 7, last command tpair 1, empty 1}
        reg [21:0] mq [0:MQD-1]; reg [1:0] mqh, mqt; reg [2:0] mqn;
        // ---- buffers (NBF ring): bst 0 free, 1 filling (takes waves), 2 every wave taken (landing / complete / emitting)
        reg [1:0] bst [0:NBF-1]; reg [6:0] mxb [0:NBF-1]; reg [3:0] mg [0:NBF-1]; reg [1:0] mtp [0:NBF-1]; reg [6:0] mnb [0:NBF-1];
        reg mlast [0:NBF-1]; reg mfull [0:NBF-1], memp [0:NBF-1]; reg [6:0] mgot [0:NBF-1]; reg mflt [0:NBF-1];
        reg [1:0] wb, eb;
        // ---- wave FIFO (cursor -> wrd), tag FIFO (cursor -> delivery), landing credits
        reg [14:0] rf_s [0:3]; reg [7:0] rf_m [0:3]; reg [1:0] rfh, rft; reg [2:0] rfn;
        reg [8:0] tq [0:QD-1]; reg [4:0] tqh, tqt; reg [5:0] tqn;     // {last, p 4, j 3, hi}
        reg [5:0] lcn;                                                  // waves pushed, not yet popped from the landing FIFO
        wire g_rdy; wire w8_busy, w8_done, w8_fault; wire [7:0] d8_v; wire d8_w; wire [14:0] d8_s0; wire [7:0] d8_m;
        wire [8*15-1:0] d8_sec; wire [8*256-1:0] d8_dat;
        reg wgo;
        assign k_take = cmd_v && !c_bad && c_bdf && cidle;
        assign k_wflt = w8_fault;
        assign k_cidle = cidle;
        function automatic [1:0] nx(input [1:0] b); nx = (b == 2'(NBF - 1)) ? 2'd0 : b + 2'd1; endfunction
        // the cursor's wave: blocks b0 = (g LA + j) 8 + 2 tp and b0 + 1 of slot p
        wire [15:0] b0 = {5'd0, cgj, 3'd0} + {13'd0, ctp, 1'b0};
        wire wlo = b0 < cnbk, whi = (b0 + 16'd1) < cnbk;
        wire cstep = !cidle && mqn < 3'(MQD) && (!wlo || (rfn < 3'd4 && tqn < 6'd31 && lcn < 6'(LD)));
        wire cpush = cstep && wlo;
        wire clast = cj == cla - 4'd1 && cpi == cp - 4'd1;                   // the tpair's last wave
        wire cfirst = cj == 4'd0 && cpi == 4'd0;                             // the tpair's first step: its meta leaves
        wire wlast = cpi == cp - 4'd1 && (cj == cla - 4'd1 || (b0 + 16'd8) >= cnbk);   // the tpair's last pushed wave
        wire rpop = (rfn != 3'd0) && g_rdy;
        wire g_fin = cidle && rfn == 3'd0 && !(cmd_v && c_bdf);
        ot_hgi_vm_wrd #(.LQ(W8LQ), .D(W8D), .SW(15), .NL(8), .GATHER(1)) u_w8 (.clk(clk), .rst_n(rst_c),
            .start(wgo), .s0(15'd0), .ns(16'd0), .busy(w8_busy), .done(w8_done), .fault(w8_fault), .req(rg_req),
            .gnt(rg_gnt), .q(wrq[8*16-1:0]), .cr(wrq_cr[7:0]), .rsp(wrr[8*257-1:0]), .d_v(d8_v), .d_sec(d8_sec),
            .d_data(d8_dat), .g_v(rfn != 3'd0), .g_s0(rf_s[rfh]), .g_m(rf_m[rfh]), .g_rdy(g_rdy), .g_fin(g_fin),
            .d_w(d8_w), .d_s0(d8_s0), .d_m(d8_m));
        assign wrq[32*16-1:8*16] = '0;
        // ---- R: rotate (chunk c <- lane (s0 + c) mod 8) + the wave's tag
        reg rv8; reg [2047:0] rx; reg [8:0] rtg;
        always @(posedge clk) begin
            for (integer c = 0; c < 8; c = c + 1) rx[c*256 +: 256] <= d8_dat[((c + d8_s0[2:0] + MUT_B8) % 8)*256 +: 256];
            rtg <= tq[tqh];
        end
        // ---- two quantisers (lo = block t, hi = block t + 1); tags ride a FIFO (in order, fixed latency)
        wire [1:0] qvo, qf; wire [255:0] qq [0:1]; wire signed [9:0] qe [0:1];
        ot_hdc_actquant u_aq0 (.clk(clk), .rst_n(rst_c), .v(rv8), .fp4(1'b0), .x(rx[1023:0]), .vo(qvo[0]), .q(qq[0]),
                               .e(qe[0]), .y(), .fault(qf[0]));
        ot_hdc_actquant u_aq1 (.clk(clk), .rst_n(rst_c), .v(rv8 && rtg[0]), .fp4(1'b0), .x(rx[2047:1024]), .vo(qvo[1]),
                               .q(qq[1]), .e(qe[1]), .y(), .fault(qf[1]));
        reg [8:0] at [0:15]; reg [3:0] ath, att;                             // {last, p 4, j 3, hi}
        // ---- landing FIFO: {flt, last, hi, p 4, j 3, hi word 266, lo word 266}
        localparam integer LW = 1 + 9 + 532;
        reg [LW-1:0] lf [0:LD-1]; reg [4:0] lfh, lft; reg [5:0] lfn;
        wire [LW-1:0] lfo = lf[lfh];
        // ---- write stage: buffer wb opens on the meta FIFO head when free and takes the head waves up to LAST
        wire wopen = bst[wb] == 2'd0 && mqn != 3'd0;
        wire lpop = lfn != 6'd0 && (bst[wb] == 2'd1 || (wopen && !mq[mqh][0]));
        // ---- W: per (buffer, parity) registered write copy: one-hot lane {p, j} + the 266-b word
        localparam integer NLN = PMAX * 8, NFR = 2 * NBF;
        reg [NFR-1:0] wv8; reg [NLN-1:0] woh [0:NFR-1]; reg [265:0] wdd [0:NFR-1]; reg [NBF-1:0] wl8; reg wfl8, wls8;
        // ---- fragments: index buf * 2 + par, NBQ beat registers each (BD layout); shift copies per beat (kept)
        wire [2047:0] f0 [0:NFR-1];            // beat 0 of each fragment (the emitted beat)
        reg em; reg ep; reg [6:0] ebt;
        reg em_n, ep_n; reg [1:0] eb_n; reg [6:0] ebt_n; reg fr_end, edn_n;
        // a buffer is complete when its LAST wave LANDED in the fragment.  MUT_B8E: it emits as soon as its FIRST wave
        // landed, still filling (r1's mutant only dropped the 2-edge mfull wait after the LAST pop, which the registered
        // emission start already covers: 13,352 = base at +XLJIT=64, so it was not a bug and could not be killed)
        function automatic rdy_b(input [1:0] b);
            rdy_b = (bst[b] == 2'd2 && (memp[b] || mfull[b])) || (MUT_B8E != 0 && bst[b] != 2'd0 && mgot[b] != 7'd0);
        endfunction
        wire est = !em && rdy_b(eb);
        always @* begin
            em_n = em; eb_n = eb; ep_n = ep; ebt_n = ebt; fr_end = 1'b0; edn_n = 1'b0;
            if (em) begin
                if (ebt == mnb[eb] - 7'd1) begin
                    ebt_n = 7'd0;
                    if (!ep) ep_n = 1'b1;
                    else begin      // buffer done: chain straight into the next complete buffer (no bubble)
                        ep_n = 1'b0; eb_n = nx(eb); fr_end = 1'b1; edn_n = mlast[eb]; em_n = rdy_b(nx(eb)) && nx(eb) != eb;
                    end
                end else ebt_n = ebt + 7'd1;
            end else if (est) begin em_n = 1'b1; ep_n = 1'b0; ebt_n = 7'd0; end
        end
        genvar fb, fl;
        for (fb = 0; fb < NFR; fb = fb + 1) begin : g_fb
            wire [NBQ*2048-1:0] fd8, fm8;
            for (fl = 0; fl < NLN; fl = fl + 1) begin : g_l
                localparam integer LO = (fl / 8) * XC + 266 * (fl % 8);
                assign fd8[LO +: 266] = wdd[fb];
                assign fm8[LO +: 266] = {266{woh[fb][fl]}};
                if (fl % 8 == 7) begin : g_gap
                    localparam integer GE = ((fl / 8) == PMAX - 1) ? NBQ * 2048 : (fl / 8 + 1) * XC;
                    assign fd8[GE - 1 : LO + 266] = '0;
                    assign fm8[GE - 1 : LO + 266] = '0;
                end
            end
            reg [NBQ*2048-1:0] fr;                // the fragment (beat k at [k 2,048 +: 2,048])
            (* keep *) reg region_go;
            always @(posedge clk or negedge rst_c)if(!rst_c)region_go<=0;else region_go<=go_ctl;
            wire fragment_go=(XW_FLOW==0)||region_go;
            (* keep = 1 *) reg [NBQ-1:0] sh;     // shift enable, one register copy a beat
            always @(posedge clk or negedge rst_c) if (!rst_c) sh <= '0;
                                                else if(fragment_go)sh <= {NBQ{em_n && {eb_n, ep_n} == 3'(fb)}};
            always @(posedge clk)
                for (integer k = 0; k < NBQ; k = k + 1) begin
                    if (fragment_go && sh[k]) fr[k*2048 +: 2048] <= (k == NBQ - 1) ? 2048'd0 : fr[((k == NBQ - 1) ? k : k + 1)*2048 +: 2048];
                    else if (wv8[fb]) fr[k*2048 +: 2048] <= (fr[k*2048 +: 2048] & ~fm8[k*2048 +: 2048]) | (fd8[k*2048 +: 2048] & fm8[k*2048 +: 2048]);
                end
            assign f0[fb] = fr[2047:0];
        end
        // ---- E: the beat on its way to the xw pins (+ the command's done / fault one edge later, with px_en)
        reg bev; reg [6:0] bea, beg; reg [2047:0] bed; reg edn, eflt, cflt;
        assign k_bev = bev; assign k_bea = bea; assign k_beg = beg; assign k_bed = bed;
        assign k_xdone = edn; assign k_xflt = eflt;
        reg anyb;
        always @* begin anyb = 1'b0; for (integer z = 0; z < NBF; z = z + 1) if (bst[z]) anyb = 1'b1; end
        assign k_allidle = cidle && !anyb && mqn == 3'd0 && lcn == 6'd0 && !bev && !edn;
        always @(posedge clk or negedge rst_c) begin
            if (!rst_c) begin
                cidle <= 1'b1; rfh <= 2'd0; rft <= 2'd0; rfn <= 3'd0; mqh <= 2'd0; mqt <= 2'd0; mqn <= 3'd0;
                tqh <= 5'd0; tqt <= 5'd0; tqn <= 6'd0; lcn <= 6'd0; lfh <= 5'd0; lft <= 5'd0; lfn <= 6'd0;
                wgo <= 1'b0; rv8 <= 1'b0; ath <= 4'd0; att <= 4'd0; wv8 <= '0; wl8 <= '0; wb <= 2'd0; eb <= 2'd0;
                em <= 1'b0; ep <= 1'b0; bev <= 1'b0; edn <= 1'b0; eflt <= 1'b0; cflt <= 1'b0;
                for (integer z = 0; z < NBF; z = z + 1) begin bst[z] <= 2'd0; mflt[z] <= 1'b0; mgot[z] <= 7'd0; mfull[z] <= 1'b0; end
            end else begin : ctl
                reg [2:0] rfn_, mqn_; reg [5:0] tqn_, lcn_, lfn_;
                rfn_ = rfn; tqn_ = tqn; mqn_ = mqn; lcn_ = lcn; lfn_ = lfn;
                if (k_take) cidle <= 1'b0;
                // cursor step: a wave (or a skipped block) a step; the tpair's meta leaves with its first step
                if (cpush) begin rft <= rft + 2'd1; rfn_ = rfn_ + 3'd1; tqt <= tqt + 5'd1; tqn_ = tqn_ + 6'd1; lcn_ = lcn_ + 6'd1; end
                if (cstep && cfirst) begin mqt <= mqt + 2'd1; mqn_ = mqn_ + 3'd1; end
                if (cstep && clast && ctp == 2'd3 && cg == cgn - 8'd1) cidle <= 1'b1;
                // the burst: opens when a wave waits and the group is not ours yet
                wgo <= (rfn != 3'd0) && !w8_busy && !wgo;
                if (rpop) begin rfh <= rfh + 2'd1; rfn_ = rfn_ - 3'd1; end
                // delivery -> R -> quantisers -> landing FIFO
                rv8 <= d8_w;
                if (d8_w) begin tqh <= tqh + 5'd1; tqn_ = tqn_ - 6'd1; end
                if (rv8) att <= att + 4'd1;
                if (qvo[0]) begin ath <= ath + 4'd1; lft <= lft + 5'd1; lfn_ = lfn_ + 6'd1; end
                // write stage: open (an empty tpair opens complete), take waves up to LAST, then the next buffer
                if (wopen) begin
                    bst[wb] <= mq[mqh][0] ? 2'd2 : 2'd1; mgot[wb] <= 7'd0; mflt[wb] <= 1'b0; mfull[wb] <= 1'b0;
                    mqh <= mqh + 2'd1; mqn_ = mqn_ - 3'd1;
                    if (mq[mqh][0]) wb <= nx(wb);
                end
                if (lpop) begin
                    lfh <= lfh + 5'd1; lfn_ = lfn_ - 6'd1; lcn_ = lcn_ - 6'd1;
                    if (lfo[LW-2]) begin bst[wb] <= 2'd2; wb <= nx(wb); end
                end
                for (integer z = 0; z < NFR; z = z + 1) wv8[z] <= lpop && wb == 2'(z / 2) && (z % 2 == 0 || lfo[LW-3]);
                for (integer z = 0; z < NBF; z = z + 1) wl8[z] <= lpop && wb == 2'(z);
                wfl8 <= lfo[LW-1]; wls8 <= lfo[LW-2];
                for (integer z = 0; z < NBF; z = z + 1)
                    if (wl8[z]) begin mgot[z] <= mgot[z] + 7'd1; if (wfl8) mflt[z] <= 1'b1; if (wls8) mfull[z] <= 1'b1; end
                // emission
                if(emit_go)begin em <= em_n; eb <= eb_n; ep <= ep_n; ebt <= ebt_n;
                if (fr_end) bst[eb] <= 2'd0;
                bev <= em;
                edn <= edn_n; eflt <= edn_n && (cflt || mflt[eb]);
                if (fr_end) cflt <= edn_n ? 1'b0 : (cflt || mflt[eb]);end
                rfn <= rfn_; tqn <= tqn_; mqn <= mqn_; lcn <= lcn_; lfn <= lfn_;
            end
        end
        always @(posedge clk) begin
            if (k_take) begin
                cb <= c_base[17:3]; cs <= c_stride[17:3]; cp <= c_p; cla <= (c_fmt == 2'd2) ? 4'd8 : 4'd4;
                cnbk <= c_n[20:5]; cxb <= c_xb; cnb <= 7'(({12'd0, c_p} * 16'd3152 + 16'd2047) >> 11);
                cgn <= (c_fmt == 2'd2) ? 8'(((c_n - 21'd1) >> 11) + 21'd1) : 8'(((c_n - 21'd1) >> 10) + 21'd1);
                cg <= 8'd0; ctp <= 2'd0; cj <= 4'd0; cpi <= 4'd0; cgj <= 8'd0; crow <= c_base[17:3];
            end else if (cstep) begin
                if (cpush) begin
                    rf_s[rft] <= crow + 15'({cgj, 5'd0}) + {10'd0, ctp, 3'd0};
                    rf_m[rft] <= {{4{whi}}, 4'hF};
                    tq[tqt] <= {wlast, cpi, cj[2:0], whi};
                end
                if (cfirst) mq[mqt] <= {cxb, cg[3:0], ctp, cnb, ctp == 2'd3 && cg == cgn - 8'd1, !wlo};
                if (clast) begin
                    cj <= 4'd0; cpi <= 4'd0; crow <= cb;
                    if (ctp == 2'd3) begin ctp <= 2'd0; cg <= cg + 8'd1; cgj <= cgj + 8'd1; end
                    else begin ctp <= ctp + 2'd1; cgj <= cgj - 8'(cla - 4'd1); end
                end else begin
                    if (cpi == cp - 4'd1) begin cpi <= 4'd0; crow <= cb; cj <= cj + 4'd1; cgj <= cgj + 8'd1; end
                    else begin cpi <= cpi + 4'd1; crow <= crow + cs; end
                end
            end
            if (rv8) at[att] <= rtg;
            if (qvo[0]) lf[lft] <= {qf[0] || (at[ath][0] && qf[1]), at[ath][8], at[ath][0], at[ath][7:1], qe[1], qq[1], qe[0], qq[0]};
            if (wopen) begin
                mxb[wb] <= mq[mqh][21:15]; mg[wb] <= mq[mqh][14:11]; mtp[wb] <= mq[mqh][10:9]; mnb[wb] <= mq[mqh][8:2];
                mlast[wb] <= mq[mqh][1]; memp[wb] <= mq[mqh][0];
            end
            for (integer z = 0; z < NFR; z = z + 1) begin
                woh[z] <= {NLN{1'b0}};
                if (lpop && wb == 2'(z / 2)) woh[z][{lfo[LW-4:LW-7], 3'd0} + {4'd0, lfo[LW-8:LW-10]}] <= 1'b1;
                if (lpop) wdd[z] <= (z % 2 == 0) ? lfo[265:0] : lfo[531:266];
            end
            if (emit_go && em) begin
                bea <= {mg[eb], mtp[eb], ep} + mxb[eb]; beg <= ebt; bed <= f0[{eb, ep}];
            end
        end
    end else begin : g_nobw8
        assign k_take = 1'b0; assign k_wflt = 1'b0; assign k_cidle = 1'b1; assign k_allidle = 1'b1; assign k_xdone = 1'b0; assign k_xflt = 1'b0;
        assign k_bev = 1'b0; assign k_bea = '0; assign k_beg = '0; assign k_bed = '0;
    end endgenerate
endmodule
`default_nettype wire
