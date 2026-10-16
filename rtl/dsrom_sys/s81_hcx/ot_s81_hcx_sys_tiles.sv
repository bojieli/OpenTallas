`timescale 1ns/1ps
`default_nettype none
// S81 HCX projection leaf, SYSTOLIC hardened partition (S-ELEM-PQ/HCX, 2026-10-16).
//
// WHY.  ot_s81_hcx_projection_leaf is 265k flops on one clock root (rule: <= 15k sinks per root).  The flat HCP
// rotates every bank's 1536-bit read to all 8 lane groups (a 12,288-bit crossbar); cutting the flat engine into
// lane children (Codex v9, 46 masters) leaves that crossbar on the child pins (3,171 ingress bits per 8-lane child).
// This partition uses the HCP's own SYSTOLIC organisation (ot_hdc_v41x_hcp SYS = 1, already used by the HBM HC unit):
// stage k multiplies term k from ITS OWN bank and adds it to the partial chunk sum handed over by stage k - 1, so
// csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op (bit-identical chunk sums), and every wire is
// point-to-point between neighbours: bank -> its lanes, lanes(k) -> lanes(k+1), lanes(7) -> controller.
//
// MASTERS (all pins registered in both directions):
//   ot_hdc_v41x_hcp_lanes   EXISTING closed master hc_lanes_ref (8 FP32 MAC lanes, mul LAT 8 / add LAT 7, seam reg),
//                           32 per leaf (stage k = 0..7 x lane group g = 0..3);
//   ot_s81_hcx_hbank        NEW: half bank (4 ROM 4096x266 + 1 SRAM 128x256 = 16 lanes of bank k) + the stage-k
//                           control of those 16 lanes (descriptor taps, addresses, lane enables), 16 per leaf;
//   ot_s81_hcx_sys_ctl      NEW: HCP control (ot_hdc_v41x_hcp SYS = 1: issue, delay line, tree over the 32 chunk sums,
//                           run tail, raw FIFO, rsqrt scalar unit, output multiply) + the leaf's staging/command checks,
//                           1 per leaf.
// ot_s81_hcx_projection_sys is the leaf with the SAME ports as ot_s81_hcx_projection_leaf, wires only.
//
// CYCLES.  Output arrives at a fixed, data-independent cycle; the systolic chain costs T_LEAF 87 against the flat 33
// (+54 cycles: 8 sequential adds at LAT 7 instead of 3, 7 registered seams, LAT-8 multiply, 1 descriptor relay).
// Measured by tb_s81_hcx_projection_sys (both leaves on the same stimulus): see results/rtl/s81_hcx_sys_1016.
// =====================================================================================================================

// ---------------------------------------------------------------------------------------------------------------------
// Half bank k (h = 0: lanes 0..15, h = 1: lanes 16..31) = the stage-k control of those lanes + their memories.
// Descriptor in through pin flops (local 0); w/x addresses registered (local 1); ROM/SRAM read (local 2); data
// registered at the output pins (local 3 = stage input, ML 2 as the flat leaf); lane enables / gov registered one
// cycle earlier than the lane leaf's pin flops (= ot_hdc_v41x_hcp_stage LG mode).  Descriptor leaves at local LA+SOR
// (8) so the next stage's pin flop makes the hop 9 = LA + 1 + SOR of the lane master.  Staging writes: pin flops
// (= the flat leaf's stage_v_q/stage_word_q/stage_d_q) -> SRAM write port, same cycle as the flat leaf.
module ot_s81_hcx_hbank #(
    parameter IMAGE = "hcx_r0",
    parameter integer BANK = 0,
    parameter integer HALF = 0,
    parameter integer MUT_BANK = 0,
    parameter integer MUT_PAGE = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // descriptor chain
    input  wire          d_v,
    input  wire          d_ss,
    input  wire [4:0]    d_nv,
    input  wire [15:0]   d_wa,
    input  wire [15:0]   d_xa,
    output wire          o_v,
    output wire          o_ss,
    output wire [4:0]    o_nv,
    output wire [15:0]   o_wa,
    output wire [15:0]   o_xa,
    // staging writes (16 BF16 lanes of bank k)
    input  wire          st_v,
    input  wire [6:0]    st_word,
    input  wire [255:0]  st_d,
    // to the two lane leaves (lanes 8j .. 8j+7 of this half)
    output reg  [1:0]    gov,
    output reg  [15:0]   lv,
    output reg  [15:0]   ss,
    output reg  [511:0]  wd,
    output reg  [255:0]  xd,
    // lane-leaf faults in, stage fault out
    input  wire [1:0]    lf,
    output reg           f_o
);
    localparam integer LA = 7, SOR = 1, ML = 2;
    localparam integer NC = LA + SOR;                 // 8 >= 1 + ML
    localparam integer DW = 1 + 5 + 16 + 16;          // ss, nv, wa, xa
    reg  [NC:0]   cv;
    reg  [DW-1:0] cd [0:NC];
    reg           w_re, x_re;
    reg  [15:0]   w_addr, x_addr;
    reg  [1:0]    lf_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cv <= '0; w_re <= 1'b0; x_re <= 1'b0; gov <= 2'b00; lf_q <= 2'b00; f_o <= 1'b0; end
        else begin
            cv <= {cv[NC-1:0], d_v};
            w_re <= cv[0] && !cd[0][DW-1];
            x_re <= cv[0];
            gov <= {2{cv[1 + ML]}};
            lf_q <= lf;
            f_o <= |lf_q;
        end
    end
    always @(posedge clk) begin
        cd[0] <= {d_ss, d_nv, d_wa, d_xa};
        for (integer j = 1; j <= NC; j = j + 1) cd[j] <= cd[j-1];
        w_addr <= cd[0][31:16];
        x_addr <= cd[0][15:0];
    end
    assign o_v = cv[NC];
    assign {o_ss, o_nv, o_wa, o_xa} = cd[NC];
    // lane enables of the task at local ML, registered (local ML + 1); the leaf's pin flop holds them at ML + 2
    wire [4:0] nv_e = cd[ML][DW-2 -: 5];
    always @(posedge clk)
        for (integer l = 0; l < 16; l = l + 1) begin
            lv[l] <= cv[ML] && (5'(l) < nv_e);
            ss[l] <= cd[ML][DW-1];
        end
    // staging pin flops -> x SRAM write
    reg         st_v_q;
    reg [6:0]   st_word_q;
    reg [255:0] st_d_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) st_v_q <= 1'b0; else st_v_q <= st_v;
    always @(posedge clk) begin st_word_q <= st_word; st_d_q <= st_d; end
    // memories: 2 lane columns m = 2*HALF + c, two 4096-row pages each (all 40 main + 3 MTP layer sets, no ECC)
    reg page_q;
    always @(posedge clk) if (w_re) page_q <= w_addr[12];
    wire [511:0] wd1;
    wire [255:0] xd1;
    genvar c, pg;
    generate for (c = 0; c < 2; c = c + 1) begin : g_rom
        wire [265:0] q [0:1];
        for (pg = 0; pg < 2; pg = pg + 1) begin : g_page
`ifdef SYNTHESIS
            ot_rom_4096x266_m8 rom (
`elsif OT_HCX_ROM_HIERLOAD
            ot_rom_4096x266_m8 rom (
`else
            ot_rom_4096x266_m8 #(.INSTANCE($sformatf("%s_b%0d_l%0d_p%0d", IMAGE, BANK, 2 * HALF + c, pg))) rom (
`endif
                .clk(clk), .ce_in(w_re && w_addr[12] == pg), .addr_in(w_addr[11:0]), .rd_out(q[pg]));
        end
        assign wd1[c*256 +: 256] = ((MUT_BANK != 0 && BANK == 7 && HALF == 0) || (MUT_PAGE != 0 && page_q)) ? 256'd0
                                   : q[page_q][255:0];
    end endgenerate
    ot_sram_1r1w_128x256_m1_r2c2 ram (
        .clk(clk), .r_ce_in(x_re), .r_addr_in(x_addr[6:0]), .rd_out(xd1),
        .w_ce_in(st_v_q), .w_addr_in(st_word_q), .wd_in(st_d_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) begin wd <= wd1; xd <= xd1; end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Controller: the leaf's command/staging checks + ot_hdc_v41x_hcp SYS = 1 (W 32, TL 7, PMAX 2, OMAX 2, ML 2) whose
// chunk sums arrive from the stage-7 lane leaves on sys_sum (straight into the HCP's leaf register = pin flop).
// The task descriptor leaves through one relay register per half chain, with the half's lane count
// (nv0 = min(nv,16), nv1 = nv - 16 saturated at 0).  SYS_LAT 86 = relay 1 + stage-0 pin flop 1 + 7 hops x 9 +
// stage-7 local 21 (data local 3, lane pin 4, operand 5, multiply 8, add 7, seam 1).
module ot_s81_hcx_sys_ctl #(
    parameter integer HLAYOUT = 1,
    parameter integer SYS_LAT = 86
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          stage_begin,
    input  wire          stage_v,
    input  wire [6:0]    stage_word,
    input  wire          cmd_v,
    input  wire          cmd_ffn,
    input  wire [5:0]    cmd_layer,
    input  wire [31:0]   norm_eps,
    // descriptor to the two half chains (stage 0)
    output reg  [1:0]    d_v,
    output reg  [1:0]    d_ss,
    output reg  [9:0]    d_nv,
    output reg  [31:0]   d_wa,
    output reg  [31:0]   d_xa,
    // stage-7 chunk sums (lanes 0..31) and the 16 half-bank stage faults
    input  wire [1023:0] sys_sum,
    input  wire [15:0]   bf,
    output reg           o_v,
    output reg  [31:0]   o_d,
    output reg           fault
);
    reg  [6:0]  staged;
    wire        ready, hfault, last, idle;
    reg         stage_v_q, cmd_v_q, stage_begin_q;
    reg  [6:0]  stage_word_q;
    reg         cmd_ffn_q;
    reg  [5:0]  cmd_layer_q;
    reg  [31:0] norm_eps_q;
    wire        hv;
    wire [31:0] hd;
    wire [0:0]  pos;
    reg  [15:0] bf_q;
    reg         sys_fault;
    // Every input lands in a pin flop.  The flat leaf used stage_begin unregistered; its staging/command CHECK logic
    // (count + sticky fault only, never a cycle of the datapath) therefore runs here one cycle later on delayed
    // copies (begin_q = begin(t), v/word/cmd/ready/layer one cycle older), which is the flat check bit for bit.
    reg        stage_v_qq, cmd_v_qq, ready_q, idle_q;
    reg [6:0]  stage_word_qq;
    reg [5:0]  cmd_layer_qq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            stage_v_q <= 1'b0; cmd_v_q <= 1'b0; o_v <= 1'b0; stage_begin_q <= 1'b0; bf_q <= '0; sys_fault <= 1'b0;
            stage_v_qq <= 1'b0; cmd_v_qq <= 1'b0;
        end else begin
            stage_v_q <= stage_v; cmd_v_q <= cmd_v; o_v <= hv; stage_begin_q <= stage_begin;
            bf_q <= bf; sys_fault <= |bf_q;
            stage_v_qq <= stage_v_q; cmd_v_qq <= cmd_v_q;
        end
    always @(posedge clk) begin
        stage_word_q <= stage_word; cmd_ffn_q <= cmd_ffn; cmd_layer_q <= cmd_layer; norm_eps_q <= norm_eps; o_d <= hd;
        stage_word_qq <= stage_word_q; cmd_layer_qq <= cmd_layer_q; ready_q <= ready; idle_q <= idle;
    end
    wire       sd_v, sd_ss;
    wire [5:0] sd_nv;
    wire [15:0] sd_wa, sd_xa;
    ot_hdc_v41x_hcp #(.W(32), .TL(7), .PMAX(2), .OMAX(2), .AW(16), .CW(16), .ML(2), .SYS(1), .SYS_LAT(SYS_LAT)) hcp (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_v_q), .cmd_ready(ready), .cmd_npos(2'd1), .cmd_nout(2'd1),
        .cmd_nchunk(16'd2560), .cmd_scale(1'b1), .cmd_nf(32'h46a00000), .cmd_eps(norm_eps_q),
        .cmd_wbase(16'((2*cmd_layer_q+cmd_ffn_q)*80)), .cmd_xbase(16'd0),
        .w_re(), .w_addr(), .w_data(8192'd0), .x_re(), .x_addr(), .x_data(4096'd0),
        .o_valid(hv), .o_ready(1'b1), .o_pos(pos), .o_idx(), .o_data(hd), .o_last(last), .fault(hfault), .idle(idle),
        .sd_v(sd_v), .sd_ss(sd_ss), .sd_nv(sd_nv), .sd_wa(sd_wa), .sd_xa(sd_xa), .sys_sum(sys_sum),
        .sys_fault(sys_fault));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) d_v <= 2'b00; else d_v <= {2{sd_v}};
    always @(posedge clk) begin
        d_ss <= {2{sd_ss}};
        d_nv[4:0] <= (sd_nv > 6'd16) ? 5'd16 : sd_nv[4:0];
        d_nv[9:5] <= (sd_nv > 6'd16) ? 5'(sd_nv - 6'd16) : 5'd0;
        d_wa <= {2{sd_wa}};
        d_xa <= {2{sd_xa}};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin staged <= 0; fault <= 0; end
        else begin
            if (stage_begin_q) begin if (!idle_q) fault <= 1; staged <= 0; end
            if (stage_v_qq) begin
                if (stage_word_qq != (HLAYOUT ? 7'(20*staged[1:0]+staged[6:2]) : staged) || staged >= 80 || !idle_q) fault <= 1;
                staged <= staged + 1'b1;
            end
            // Availability is a check; it never moves the command's compiled cycle.
            if (cmd_v_qq && (!ready_q || staged != 80 || cmd_layer_qq > 42)) fault <= 1;
            if (hfault) fault <= 1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The leaf: same ports as ot_s81_hcx_projection_leaf; wires only (16 half banks, 32 lane leaves, 1 controller).
// Lane leaf (k, g): stage k, lanes 8g .. 8g+7, fed by half bank (k, g/2) port j = g%2.  Stage 0 adds to +0 through
// the lane master's fst strap (the flat engine's `first`, its sum input then unused), exactly as the HBM SYS tile.
module ot_s81_hcx_projection_sys #(
    parameter IMAGE = "hcx_r0",
    parameter integer MUT_BANK = 0,
    parameter integer MUT_PAGE = 0,
    parameter integer HLAYOUT = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          stage_begin,
    input  wire          stage_v,
    input  wire [6:0]    stage_word,
    input  wire [4095:0] stage_d,
    input  wire          cmd_v,
    input  wire          cmd_ffn,
    input  wire [5:0]    cmd_layer,
    input  wire [31:0]   norm_eps,
    output wire          o_v,
    output wire [31:0]   o_d,
    output wire          fault
);
    // descriptor chain per half: index k = into stage k (k = 0 from the controller)
    wire [8:0]  cv [0:1];
    wire [8:0]  css [0:1];
    wire [44:0] cnv [0:1];
    wire [143:0] cwa [0:1];
    wire [143:0] cxa [0:1];
    // partial sums: lsum[k][g] = output of lane leaf (k, g)
    wire [255:0] lsum [0:7][0:3];
    wire [15:0]  bf;
    wire [1023:0] sys_sum;
    wire [1:0]  dv, dss; wire [9:0] dnv; wire [31:0] dwa, dxa;
    ot_s81_hcx_sys_ctl #(.HLAYOUT(HLAYOUT)) ctl (
        .clk(clk), .rst_n(rst_n), .stage_begin(stage_begin), .stage_v(stage_v), .stage_word(stage_word),
        .cmd_v(cmd_v), .cmd_ffn(cmd_ffn), .cmd_layer(cmd_layer), .norm_eps(norm_eps),
        .d_v(dv), .d_ss(dss), .d_nv(dnv), .d_wa(dwa), .d_xa(dxa), .sys_sum(sys_sum), .bf(bf),
        .o_v(o_v), .o_d(o_d), .fault(fault));
    genvar k, h, j, i;
    generate
        for (h = 0; h < 2; h = h + 1) begin : g_hd
            assign cv[h][0] = dv[h]; assign css[h][0] = dss[h]; assign cnv[h][4:0] = dnv[5*h +: 5];
            assign cwa[h][15:0] = dwa[16*h +: 16]; assign cxa[h][15:0] = dxa[16*h +: 16];
        end
        for (k = 0; k < 8; k = k + 1) begin : g_stage
            for (h = 0; h < 2; h = h + 1) begin : g_half
                wire [1:0] gov; wire [15:0] lv, ss; wire [511:0] wd; wire [255:0] xd; wire [1:0] lf;
                wire [255:0] st_d;
                for (i = 0; i < 16; i = i + 1) begin : g_scatter
                    assign st_d[16*i +: 16] = stage_d[16*(8*(16*h+i)+k) +: 16];
                end
                ot_s81_hcx_hbank #(.IMAGE(IMAGE), .BANK(k), .HALF(h), .MUT_BANK(MUT_BANK), .MUT_PAGE(MUT_PAGE)) bank (
                    .clk(clk), .rst_n(rst_n),
                    .d_v(cv[h][k]), .d_ss(css[h][k]), .d_nv(cnv[h][5*k +: 5]), .d_wa(cwa[h][16*k +: 16]),
                    .d_xa(cxa[h][16*k +: 16]),
                    .o_v(cv[h][k+1]), .o_ss(css[h][k+1]), .o_nv(cnv[h][5*(k+1) +: 5]), .o_wa(cwa[h][16*(k+1) +: 16]),
                    .o_xa(cxa[h][16*(k+1) +: 16]),
                    .st_v(stage_v), .st_word(stage_word), .st_d(st_d),
                    .gov(gov), .lv(lv), .ss(ss), .wd(wd), .xd(xd), .lf(lf), .f_o(bf[2*k+h]));
                for (j = 0; j < 2; j = j + 1) begin : g_lane
                    localparam integer G = 2 * h + j;
                    wire [255:0] s_in;
                    if (k == 0) begin : g_s0
                        assign s_in = 256'd0;          // unused: fst = 1 (stage 0 adds to +0)
                    end else begin : g_sk
                        assign s_in = lsum[k-1][G];
                    end
                    ot_hdc_v41x_hcp_lanes lanes (
                        .clk(clk), .rst_n(rst_n), .fst(k == 0 ? 1'b1 : 1'b0), .gov_i(gov[j]),
                        .lv_i(lv[8*j +: 8]), .ss_i(ss[8*j +: 8]), .w_i(wd[256*j +: 256]), .x_i(xd[128*j +: 128]),
                        .s_i(s_in), .y(lsum[k][G]), .lf(lf[j]));
                end
            end
        end
        for (i = 0; i < 4; i = i + 1) begin : g_out
            assign sys_sum[256*i +: 256] = lsum[7][i];
        end
    endgenerate
endmodule
`default_nettype wire
