`timescale 1ns/1ps
// Default-off source-selected protected CODE successor. Original arithmetic
// and tree modules are reused unchanged; all memory/tag paths gain ONE edge.
// Admission is a REAL complete retained span, not ME per-read ready.
module ot_qwen_hbm_code_tile_logic_w12 #(
    parameter integer ENABLE = 0,
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer TG = 4,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer IREG = 1,
    // MEM_EXTRA = 1: every memory operand is captured at its source before use -- each ROM bank's
    // output at the macro pins (SS clk->q 739 ps leaves no room for the bank OR at 0.833 ns), the KV
    // slice word and the x line -- one cycle the engine's tags wait (ot_qwen_w12_matvec_part MEM_EXTRA)
    parameter integer MEM_EXTRA = 0,
    parameter integer NREG = 1,
    parameter integer KV_LOCAL = 1,
    parameter integer KV_AW = 7,          // local KV words: 2^KV_AW
    parameter integer KV_VB = 262144,     // first V word (4 heads x 65,536)
    parameter integer KV_HB = 16,         // words per head: 2^KV_HB
    parameter integer KV_NH = 4,          // KV heads per die
    parameter integer KV_SK = 7,          // scores split (log2)
    parameter integer KV_SV = 9,          // weighted-sum split (log2)
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
) (
    input wire code_span_retained,code_storage_fault,
    input wire[1:0] code_read_accepted,code_response_valid,
    output wire code_read_request,
    output wire[23:0] code_virtual_address,
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    // instruction broadcast (the i_* fields of ot_qwen_w12_matvec, packed as in ot_qwen_me_array_w12)
    input  wire              ib_go,
    input  wire [3*NW+13*AW+13-1:0] ib,
    // x line: this tile's TG chunk elements
    input  wire [TG*32-1:0]  xl,
    // split tree
    output wire [W*32-1:0]   t_out,
    output wire              t_vout,
    input  wire [W*32-1:0]   n_a,
    input  wire [W*32-1:0]   n_b,
    input  wire              n_va,
    output wire [W*32-1:0]   n_y,
    output wire              n_vy,
    output wire              fault,
    // code ROM macro pins
    output wire [CODE_BANKS-1:0] rom_ce,
    output wire [11:0]       rom_addr,
    input  wire [2*CODE_BANKS*266-1:0] rom_rd,
    // KV slice macro pins (KV_LOCAL = 1)
    output wire              kvs_r_ce,
    output wire [KV_AW-1:0]  kvs_r_addr,
    input  wire [TG*W*8-1:0] kvs_rd,
    // global KV port (KV_LOCAL = 0)
    output wire              kv_re,
    output wire [TG*AW-1:0]  kv_addr,
    input  wire [TG*W*32-1:0] kv_q
);
generate if(!ENABLE)begin:off
ot_qwen_rom_tile_logic_w12 #(
.W(W),
.IL(IL),
.AW(AW),
.NW(NW),
.GT(GT),
.TG(TG),
.SMIN(SMIN),
.CODE_BANKS(CODE_BANKS),
.IREG(IREG),
.MEM_EXTRA(MEM_EXTRA),
.NREG(NREG),
.KV_LOCAL(KV_LOCAL),
.KV_AW(KV_AW),
.KV_VB(KV_VB),
.KV_HB(KV_HB),
.KV_NH(KV_NH),
.KV_SK(KV_SK),
.KV_SV(KV_SV),
.ACC_LAT(ACC_LAT),
.FAST_ISSUE(FAST_ISSUE),
.KV_PREP(KV_PREP),
.MUL_LAT(MUL_LAT),
.TREE_LAT(TREE_LAT)) original(
.clk(clk),
.rst_n(rst_n),
.tile_id(tile_id),
.ib_go(ib_go),
.ib(ib),
.xl(xl),
.t_out(t_out),
.t_vout(t_vout),
.n_a(n_a),
.n_b(n_b),
.n_va(n_va),
.n_y(n_y),
.n_vy(n_vy),
.fault(fault),
.rom_ce(rom_ce),
.rom_addr(rom_addr),
.rom_rd(rom_rd),
.kvs_r_ce(kvs_r_ce),
.kvs_r_addr(kvs_r_addr),
.kvs_rd(kvs_rd),
.kv_re(kv_re),
.kv_addr(kv_addr),
.kv_q(kv_q));
assign code_read_request=|rom_ce;
assign code_virtual_address=0;
end else begin:on
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    reg              go_q;
    reg  [IBW-1:0]   ib_q;
    reg  [TG*32-1:0] xl_q;
    wire             go_i  = IREG ? go_q : (ib_go && code_span_retained);
    wire [IBW-1:0]   ib_i  = IREG ? ib_q : ib;
    wire [TG*32-1:0] xl_r  = IREG ? xl_q : xl;
    wire [TG*32-1:0] xl_i;
    ot_hdc_delay #(.W(TG*32), .D(MEM_EXTRA+1)) u_xm (.clk(clk), .rst_n(rst_n), .d(xl_r), .q(xl_i));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_q <= 1'b0;
        else go_q <= ib_go && code_span_retained;
    end
    always @(posedge clk) begin ib_q <= ib; xl_q <= xl; end

    wire [NW-1:0] b_nout, b_tiles, b_k;
    wire          b_wsrc, b_round, b_mmode, b_oen, b_amax, b_rmax;
    wire [AW-1:0] b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs, b_wcs, b_obase, b_ots, b_ojs, b_mbase;
    wire [2:0]    b_jsh;
    wire [3:0]    b_split;
    assign {b_nout, b_tiles, b_k, b_wsrc, b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs,
            b_jsh, b_split, b_wcs, b_round, b_obase, b_ots, b_ojs, b_mmode, b_oen, b_amax, b_rmax, b_mbase} = ib_i;

    wire              wrom_re;
    wire [AW-1:0]     wrom_addr;
    wire [TG*W*8-1:0] wrom_q;
    wire              me_kv_re;
    wire [TG*AW-1:0]  me_kv_addr;
    wire [TG*W*32-1:0] me_kv_q;
    wire              me_fault;
    ot_qwen_w12_matvec_part #(.W(W), .G(TG), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
        .PART(1), .GT(GT), .GBASE_PORT(1), .SMIN(SMIN), .NX(0), .MEM_EXTRA(MEM_EXTRA+1),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_me (
        .clk(clk), .rst_n(rst_n), .go(go_i), .ready(), .idle(),
        .i_nout(b_nout), .i_tiles(b_tiles), .i_k(b_k), .i_wsrc(b_wsrc),
        .i_wbase(b_wbase), .i_ts(b_ts), .i_ks(b_ks), .i_js(b_js),
        .i_xbase(b_xbase), .i_xks(b_xks), .i_xjs(b_xjs), .i_xcs(b_xcs),
        .i_jsh(b_jsh), .i_split(b_split), .i_wcs(b_wcs), .i_round(b_round),
        .i_obase(b_obase), .i_ots(b_ots), .i_ojs(b_ojs),
        .i_mmode(b_mmode), .i_oen(b_oen), .i_amax(b_amax), .i_rmax(b_rmax), .i_mbase(b_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .scale_re(), .scale_gre(), .scale_addr(), .scale_q({TG*W*16{1'b0}}),
        .kv_re(me_kv_re), .kv_addr(me_kv_addr), .kv_q(me_kv_q),
        .x_re(), .x_addr(), .x_q(xl_i),
        .ov(), .o_we(), .o_addr(), .o_mask(), .o_data(),
        .am_idx(), .am_val(), .am_any(), .mx_we(), .mx_addr(), .mx_mask(), .mx_data(),
        .progress(), .fault(me_fault),
        .i_gbase({16'd0, tile_id} * TG), .t_in({W*32{1'b0}}), .t_fault_in(1'b0),
        .t_out(t_out), .t_vout(t_vout), .t_fault(), .active_o());

    // -- upper tree node ---------------------------------------------------------
    wire node_fault;
    ot_qwen_me_node_w12 #(.W(W), .WS(NREG), .TREE_LAT(TREE_LAT)) u_node (.clk(clk), .rst_n(rst_n), .a(n_a), .b(n_b), .va(n_va),
                                               .y(n_y), .vy(n_vy), .fault(node_fault));
    reg join_fault;
    reg [1:0] code_req_pipe;
    assign code_read_request=wrom_re;
    assign code_virtual_address=wrom_addr;
    always @(posedge clk or negedge rst_n)
      if(!rst_n) begin join_fault<=0;code_req_pipe<=0;end
      else begin
        code_req_pipe<={code_req_pipe[0],wrom_re};
        if((ib_go&&!code_span_retained)||(wrom_re&&!code_span_retained)||
           code_read_accepted!={2{wrom_re}}||code_response_valid!={2{code_req_pipe[1]}})
          join_fault<=1;
      end
    assign fault = me_fault | node_fault | join_fault | code_storage_fault;

    // -- code ROM: bank select -----------------------------------------------------
    reg  [CODE_BANKS-1:0] code_sel_q;
    genvar b, p;
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = wrom_re && (wrom_addr[AW-1:12] == b);
        end
    assign rom_addr = wrom_addr[11:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
        else if (wrom_re) code_sel_q <= rom_ce;
    end
    reg code_rd_q,code_rd_q2;
    reg [CODE_BANKS-1:0] code_sel_leaf,code_sel_extra;
    always @(posedge clk or negedge rst_n)begin
      if(!rst_n)begin code_rd_q<=0;code_rd_q2<=0;code_sel_leaf<=0;code_sel_extra<=0;end
      else begin
        code_rd_q<=wrom_re;code_rd_q2<=code_rd_q;
        if(code_rd_q)code_sel_leaf<=code_sel_q;
        if(code_rd_q2)code_sel_extra<=code_sel_leaf;
      end
    end
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    //: the bank's output register at its pins: captured only when the bank was read
                    reg [PWB-1:0] cap;
                    always @(posedge clk) if (code_sel_leaf[b] && code_rd_q2) cap <= rd;
                    assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_extra[b]}});
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_leaf[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end

    // -- KV slice --------------------------------------------------------------------
    function automatic [31:0] e4m3_f32(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [7:0] fe; reg [22:0] fm;
        begin
            e = c[6:3]; m = c[2:0];
            if (e != 0) begin fe = {4'd0, e} + 8'd120; fm = {m, 20'd0}; end
            else if (m[2]) begin fe = 8'd120; fm = {m[1:0], 21'd0}; end      // 0.1xx * 2^-6 = 1.xx * 2^-7
            else if (m[1]) begin fe = 8'd119; fm = {m[0], 22'd0}; end       // 1.x * 2^-8
            else if (m[0]) begin fe = 8'd118; fm = 23'd0; end               // 2^-9
            else begin fe = 8'd0; fm = 23'd0; end
            e4m3_f32 = {c[7], fe, fm};
        end
    endfunction
    if (KV_LOCAL != 0) begin : g_kv_local
        localparam [KV_AW-1:0] PRK = GT >> KV_SK;
        //: K words a group holds: ceil(KV_PT position tiles / (GT >> SK)) rounds x NH heads (44 at G = 6,144, 8K)
        //: 2^(KV_HB-7) position tiles a head (512 at the 8K window); a literal 512 overlaps V onto K above 8K
        localparam integer KV_PT = 1 << (KV_HB - 7);
        localparam integer KV_KL = ((KV_PT + (GT >> KV_SK) - 1) / (GT >> KV_SK)) * KV_NH;
        wire [AW-1:0] a = me_kv_addr[AW-1:0];            // every group of the tile maps to the same word
        wire          is_v = (a >= KV_VB);
        wire [AW-1:0] w = a - KV_VB;
        wire [KV_HB-8:0] tk = a[KV_HB-1:7];
        wire [KV_HB-4:0] pv = w[KV_HB-1:3];
        wire [KV_AW-1:0] lk = (tk / PRK) * KV_NH + a[KV_HB+1:KV_HB];
        wire [KV_AW-1:0] lv = KV_KL + (pv >> KV_SV) * KV_NH + w[KV_HB+1:KV_HB];
        wire [TG*W*8-1:0] kvs_rd_m,kvs_original;
        if(MEM_EXTRA!=0)begin:original_kv_capture
          reg kv_rd_q;reg[TG*W*8-1:0] cap;
          always @(posedge clk or negedge rst_n)if(!rst_n)kv_rd_q<=0;else kv_rd_q<=me_kv_re;
          always @(posedge clk)if(kv_rd_q)cap<=kvs_rd;
          assign kvs_original=cap;
        end else assign kvs_original=kvs_rd;
        ot_hdc_delay #(.W(TG*W*8),.D(1)) kv_match_code(
          .clk(clk),.rst_n(rst_n),.d(kvs_original),.q(kvs_rd_m));
        assign kvs_r_ce = me_kv_re;
        assign kvs_r_addr = is_v ? lv : lk;
        genvar e;
        for (e = 0; e < TG * W; e = e + 1) begin : g_x
            assign me_kv_q[32*e +: 32] = e4m3_f32(kvs_rd_m[8*e +: 8]);
        end
        assign kv_re = 1'b0;
        assign kv_addr = {TG*AW{1'b0}};
    end else begin : g_kv_global
        assign kvs_r_ce = 1'b0;
        assign kvs_r_addr = {KV_AW{1'b0}};
        assign kv_re = me_kv_re;
        assign kv_addr = me_kv_addr;
        // Preserve original request-qualified capture and HOLD across bubbles.
        // Only then add the same one edge as protected CODE/tag/X.
        wire[TG*W*32-1:0] kv_original;
        if(MEM_EXTRA!=0)begin:original_kv_capture
          reg kv_rd_q;reg[TG*W*32-1:0] cap;
          always @(posedge clk or negedge rst_n)if(!rst_n)kv_rd_q<=0;else kv_rd_q<=me_kv_re;
          always @(posedge clk)if(kv_rd_q)cap<=kv_q;
          assign kv_original=cap;
        end else assign kv_original=kv_q;
        ot_hdc_delay #(.W(TG*W*32),.D(1)) kv_match_code(
          .clk(clk),.rst_n(rst_n),.d(kv_original),.q(me_kv_q));
    end
end endgenerate
endmodule
