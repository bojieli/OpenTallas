`timescale 1ns/1ps
// Isolated same-edge XQ consumer successor; selected only by OT_S81ENG_RR_N32.
module ot_s81eng_xq_n32 #(
    parameter integer TXD = 8,
    parameter integer MUT = 0          // bench negative controls: 1 idx = 4 col + beat (not beat / 2), 2 e0 / e1 swapped
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         o_v,
    input  wire [4:0]   o_col,
    input  wire [2:0]   o_beat,
    input  wire [263:0] o_d,
    input  wire [275:0] vi_a, output reg [275:0] vo_a,
    input  wire [275:0] vi_b, output reg [275:0] vo_b,
    output reg          fault
);
    wire [127:0] rl;
    wire mul_reset_early_n;
    ot_s81eng_reset3n32 #(.LEAVES(128)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl),.early_n(mul_reset_early_n));
    // ---------------------------------------------------------------- input flops + decode
    reg         iv; reg [4:0] ic; reg [2:0] ib; wire [263:0] id;
    reg[255:0] id_code; wire[255:0] id_scale_c,wl_scale_c;
    assign id={id_scale_c[7:0],id_code};
    always @(posedge ck or negedge rl[0]) if (!rl[0]) iv <= 1'b0; else iv <= o_v;
    always @(posedge ck) begin ic <= o_col; ib <= o_beat; id_code <= o_d[255:0]; end
    wire [511:0] wl_rd;                 // slang: declared before g_scale_capture uses it (source order only)
    for(genvar sc=0;sc<32;sc=sc+1)begin:g_scale_capture
        ot_s81eng_rr_kq8 u_i(.ck(ck),.d(o_d[263:256]),.q(id_scale_c[8*sc+:8]));
        ot_s81eng_rr_kq8 u_w(.ck(ck),.d(wl_rd[263:256]),.q(wl_scale_c[8*sc+:8]));
    end
    // STW-S81-COLLB 10-21: native census a8b1002b9 FAIL 32 nets x 33 loads = id_code[4+8k] feeding both byte decoders
    // (32 loads) and the wait-line SRAM write port. The SRAM write data now comes from its own kept capture copy
    // (same edge, same value), so every id_code bit drives the decoders only (<=32). No cycle/age change.
    wire [255:0] id_code_w;
    for(genvar wc=0;wc<32;wc=wc+1)begin:g_wl_capture
        ot_s81eng_rr_kq8 u_c(.ck(ck),.d(o_d[8*wc+:8]),.q(id_code_w[8*wc+:8]));
    end
    wire [511:0] bf_x, bf_d;
    wire [263:0] wl;                       // wait line read: the beat 12 edges ago
    genvar g;
    generate for(g=0;g<32;g=g+1)begin:g_dec
        for(genvar by=0;by<2;by=by+1)begin:g_byte
            ot_s81eng_rr_bfraw_byte #(.LO(8*by)) u_x(.code(id[8*g+:8]),.scale(id_scale_c[8*g+:8]),.q(bf_x[16*g+8*by+:8]));
            ot_s81eng_rr_bfraw_byte #(.LO(8*by)) u_d(.code(wl[8*g+:8]),.scale(wl_scale_c[8*g+:8]),.q(bf_d[16*g+8*by+:8]));
        end
    end endgenerate
    wire [1023:0] x, xd;
    // S81-ELEM2-ENGRR 10-21: the wait-line decode is registered (bf_dq) and the line is read one edge earlier, so the
    // AQ grid input keeps its exact age while the scale-capture -> decode -> s12_dd cone (zero-wire -76.7 ps) is cut.
    reg [511:0] bf_dq;
    always @(posedge ck) bf_dq <= bf_d;
    generate for (g = 0; g < 32; g = g + 1) begin : g_x
        assign x[32 * g +: 32]  = {bf_x[16 * g +: 16], 16'h0};
        assign xd[32 * g +: 32] = {bf_dq[16 * g +: 16], 16'h0};
    end endgenerate
    // Wait line: read wp-10 one edge earlier; owned raw landing below restores the original total12-edge age.
    reg [5:0] wp;
    always @(posedge ck or negedge rl[0]) if (!rl[0]) wp <= 6'd0; else wp <= wp + 6'd1;
    ot_sram_1r1w_64x512_m1_r2c2 u_wl (.clk(ck), .r_ce_in(1'b1), .r_addr_in(wp - 6'd9), .rd_out(wl_rd),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in({248'd0, id_scale_c[7:0], id_code_w}), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    reg[255:0] wl_code;
    always @(posedge ck)wl_code<=wl_rd[255:0];
    assign wl={wl_scale_c[7:0],wl_code};
    // ---------------------------------------------------------------- act-quant (closed vq quantiser)
    wire        qv, af; wire[24:0] qv_pair,qodd_pair,rst_pair_n;
    for(genvar qp=0;qp<25;qp=qp+1)begin:g_prst assign rst_pair_n[qp]=rl[12+qp/5];end wire [255:0] qq; wire signed [9:0] qe; wire [511:0] qy_unused;
    ot_s81sl_aq12x_eng_n32 u_aq (.clk(ck), .rst_n(rl[1]), .rst_mul_early_n(mul_reset_early_n), .rst_pair_n(rst_pair_n),.vo_pair(qv_pair), .v(iv), .x(x), .vo(qv), .q(qq), .e(qe), .y(qy_unused), .fault(af), .xd(xd));
    wire [7:0] qtag;                       // {col 5, beat 3} through the quantiser latency
    wire[7:0] qtag_pre;
    ot_hdc_delay #(.W(8), .D(17)) u_tg (.clk(ck), .rst_n(rl[1]), .d({ic, ib}), .q(qtag_pre));
    ot_s81eng_rr_kq8 u_taglast(.ck(ck),.d(qtag_pre),.q(qtag));
    for(genvar qp=0;qp<25;qp=qp+1)begin:g_qodd
        ot_s81eng_rr_bitcap u_b(.ck(ck),.d(qtag_pre[0]),.q(qodd_pair[qp]));
    end
    // ---------------------------------------------------------------- XQ beat assembly -> beat ring
    reg [255:0] q0; reg [9:0] e0;
    reg         bw;                        // beat write this edge
    reg [538:0] bwd;                       // {idx 7, payload 532}
    reg [5:0]   bc;                        // beats written in this window
    reg         first;                     // first block of a window seen (sender armed)
    wire [6:0]  bidx = (MUT == 1) ? {qtag[7:3], 2'b00} + {4'd0, qtag[2:0]} : {qtag[7:3], 2'b00} + {5'd0, qtag[2:1]};
    wire[265:0] pair_hold;
    for(genvar qg=0;qg<25;qg=qg+1)begin:g_pair_hold
        localparam integer W=(qg==24)?2:11;
        wire[265:0] qdata={qe,qq};
        ot_s81eng_rr_paircap #(.W(W)) u_c(.ck(ck),.v(qv_pair[qg]),.odd(qodd_pair[qg]),.d(qdata[11*qg+:W]),.q(pair_hold[11*qg+:W]));
    end
    always @*begin q0=pair_hold[255:0];e0=pair_hold[265:256];end
    always @(posedge ck) bwd <= (MUT == 2) ? {bidx, e0, qq, qe, q0} : {bidx, qe, qq, e0, q0};
    // ---------------------------------------------------------------- sender (static from the first block of a window)
    reg  [7:0]  tc;                        // edges since the first block
    reg         tx;                        // train window
    reg  [6:0]  fc;                        // fragment counter 0..95
    reg[6:0] fc_probe; reg tx_probe;
    wire probe_start=first&&!tx_probe&&tc==8'(TXD-1);
    always @(posedge ck or negedge rl[17])if(!rl[17])begin fc_probe<=0;tx_probe<=0;end
    else if(probe_start)begin fc_probe<=0;tx_probe<=1;end
    else if(tx_probe)begin fc_probe<=fc_probe+1'b1;if(fc_probe==7'd95)tx_probe<=0;end
    reg  [63:0] rv;                        // beat ring row written (window)
    wire[5:0] rv_row;wire[63:0] rv_setmask;wire train_last,rv_seen;
    ot_s81eng_rr_rowmask u_rowmask(.bc(bc),.row(rv_row),.mask(rv_setmask));
    ot_s81eng_rr_trainlast u_last(.fc(fc),.last(train_last));
    ot_s81eng_rr_probe_read u_probe(.ix(fc_probe[6:2]),.rv(rv[31:0]),.seen(rv_seen));
    wire [1023:0] br_rd;
    wire [5:0]  rda = {1'b0, fc[6:2]} + ((fc[1:0] >= 2'd2) ? 6'd1 : 6'd0);   // beat b + 1 read from fragment 2 of b
    ot_sram_1r1w_64x512_m1_r2c2 u_b0 (.clk(ck), .r_ce_in(1'b1), .r_addr_in(tx ? rda : 6'd0), .rd_out(br_rd[511:0]),
        .w_ce_in(bw), .w_addr_in(rv_row), .wd_in(bwd[511:0]), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_b1 (.clk(ck), .r_ce_in(1'b1), .r_addr_in(tx ? rda : 6'd0), .rd_out(br_rd[1023:512]),
        .w_ce_in(bw), .w_addr_in(rv_row), .wd_in({485'd0, bwd[538:512]}), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // the beat being sent: full = {pad, payload 532, idx 8, src 4, hops 5, kind 3, v}
    reg  [538:0] cur;
    wire [1103:0] full = {551'd0, cur[531:0], {1'b0, cur[538:532]}, 4'd0, 5'd1, 3'd1, 1'b1};
    // fanout (safe checklist 3): the 552 rung output muxes take their select from 48 KEPT copies of tx and of fc[1:0]
    // (12 bits a copy), registered with the same next state as tx / fc
    wire[95:0] txk;
    wire[191:0] fck;
    for(genvar cg=0;cg<6;cg=cg+1)begin:g_ctl
        ot_s81eng_rr_ctl16 #(.TXD(TXD)) u_c(.ck(ck),.rn(rl[32+16*cg+:16]),.first(first),.tx(tx),.tc(tc),.fc(fc),
            .txk(txk[16*cg+:16]),.fck(fck[32*cg+:32]));
    end
    reg  [1:0] pa, pb;                     // pass-through train fragments still to come (a -> b, b -> a)
    reg  [275:0] ia, ib_;
    always @(posedge ck) begin ia <= vi_a; ib_ <= vi_b; end
    wire pva = ia[0] || pa != 2'd0, pvb = ib_[0] || pb != 2'd0;
    integer oi;
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin
            bw <= 1'b0; bc <= 6'd0; first <= 1'b0; tc <= 8'd0; tx <= 1'b0; fc <= 7'd0; fault <= 1'b0;
            vo_a[0] <= 1'b0; vo_b[0] <= 1'b0; pa <= 2'd0; pb <= 2'd0;
        end else begin
            bw <= qv && qtag[0];
            if (qv && qtag[0]) bc <= bc + 6'd1;
            if (qv && !first) begin first <= 1'b1; tc <= 8'd0; end
            else if (first && !tx) tc <= tc + 8'd1;
            if (first && !tx && tc == 8'(TXD - 1)) begin tx <= 1'b1; fc <= 7'd0; end
            else if (tx) begin
                fc <= fc + 7'd1;
                if (train_last) begin tx <= 1'b0; first <= 1'b0; bc <= 6'd0; end
            end
            pa <= (ia[0] && (ia[3:1] == 3'd1 || ia[3:1] == 3'd2) && pa == 2'd0) ? 2'd3 : (pa != 2'd0) ? pa - 2'd1 : 2'd0;
            pb <= (ib_[0] && (ib_[3:1] == 3'd1 || ib_[3:1] == 3'd2) && pb == 2'd0) ? 2'd3 : (pb != 2'd0) ? pb - 2'd1 : 2'd0;
            vo_b[0] <= txk[0] ? full[276*fck[1:0]] : ia[0];
            vo_a[0] <= txk[48] ? full[276*fck[97:96]] : ib_[0];
            if ((qv && af) || (tx && fc[1:0] == 2'd0 && !rv_seen) || (tx && (pva || pvb)) ||
                (qv && qtag[0] && bc == 6'd24))
                fault <= 1'b1;
        end
    // Payload never resets: validbit0 remains on the original control reset leaf.
    always @(posedge ck)for(integer vbit=1;vbit<276;vbit=vbit+1)begin
        vo_b[vbit]<=txk[vbit/6]?full[276*fck[2*(vbit/6)+:2]+vbit]:ia[vbit];
        vo_a[vbit]<=txk[48+vbit/6]?full[276*fck[2*(48+vbit/6)+:2]+vbit]:ib_[vbit];
    end
    for(genvar rb=0;rb<8;rb=rb+1)begin:g_rv
        ot_s81eng_rr_rvbyte #(.BANK(rb)) u_b(.ck(ck),.rn(rl[4+rb]),.tx(txk[rb]),.last(train_last),.bw(bw),.mask(rv_setmask[8*rb+:8]),.q(rv[8*rb+:8]));
    end
    for(genvar cb=0;cb<49;cb=cb+1)begin:g_cur
        ot_s81eng_rr_curcap u_c(.ck(ck),.tx(txk[cb]),.fc(fck[2*cb+:2]),.d(br_rd[11*cb+:11]),.q(cur[11*cb+:11]));
    end
endmodule

(* keep_hierarchy = 1 *)module ot_s81eng_rr_kq8(input wire ck,input wire[7:0] d,output reg[7:0] q);
 always @(posedge ck)q<=d;
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_paircap #(parameter integer W=11)(input wire ck,v,odd,input wire[W-1:0] d,output reg[W-1:0] q);
 always @(posedge ck)if(v&&!odd)q<=d;
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_curcap(input wire ck,tx,input wire[1:0] fc,input wire[10:0] d,output reg[10:0] q);
 always @(posedge ck)if(!tx || fc==2'd3)q<=d;
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_ctl16 #(parameter integer TXD=8)(
 input wire ck,input wire[15:0] rn,input wire first,tx,input wire[7:0] tc,input wire[6:0] fc,
 output wire[15:0] txk,output wire[31:0] fck);
 wire local_tx=txk[0];
 wire start=first&&!local_tx&&tc==8'(TXD-1);
 wire txn=start?1'b1:(local_tx&&fc==7'd95)?1'b0:local_tx;
 wire[1:0] fcn=start?2'd0:local_tx?fc[1:0]+2'd1:fc[1:0];
 for(genvar g=0;g<16;g=g+1)begin:g_c
  (* keep=1 *) reg t;(* keep=1 *)reg[1:0] f;
  always @(posedge ck or negedge rn[g])if(!rn[g])begin t<=0;f<=0;end else begin t<=txn;f<=fcn;end
  assign txk[g]=t;assign fck[2*g+:2]=f;
 end
endmodule

// A scale bit enters15 true constant-add consumers (<=30 adder inputpins),
// rather than32 full decoder adders. Each9b table output serves32 local onehot selectors.
(* keep_hierarchy = 1 *)module ot_s81eng_rr_scale9 #(parameter integer DELTA=-136)(input wire[7:0] scale,output wire[8:0] q);
 assign q={1'b0,scale}+9'(DELTA);
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_esel(input wire[3:0] e,input wire[134:0] et,output reg[8:0] q);
 wire[14:0] hit;
 for(genvar eg=0;eg<15;eg=eg+1)begin:g_s
  assign hit[eg]=(eg==0)?(e<=4'd1):(e==4'(eg+1));
 end
 integer b;
 always @*begin q=0;for(b=0;b<15;b=b+1)q=q|({9{hit[b]}}&et[9*b+:9]);end
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_bf16 (
    input  wire [7:0]  code,
    input  wire [134:0] et,
    output reg  [15:0] bf16
);
    wire       s = code[7];
    wire [3:0] e = code[6:3];
    wire [2:0] m = code[2:0];
    wire [3:0] sig = (e != 0) ? {1'b1, m} : {1'b0, m};
    // E: exponent of the significand's unit bit; value = sig * 2^E
    wire[8:0] e9;
    ot_s81eng_rr_esel u_e(.e(e),.et(et),.q(e9));
    wire signed[10:0] E={{2{e9[8]}},e9};
    wire [1:0] p = sig[3] ? 2'd3 : sig[2] ? 2'd2 : sig[1] ? 2'd1 : 2'd0;
    wire signed [10:0] X = E + $signed({9'd0, p});
    wire [3:0] nrm = sig << (2'd3 - p);               // 1.fff
    wire [7:0] xb = X[7:0] + 8'd127;
    wire signed [10:0] k = E + 11'sd133;              // >= -3 on every code and scale
    wire [1:0] r = (k < 0) ? (~k[1:0] + 2'd1) : 2'd0; // -k for k in -3..-1
    wire [3:0] q = sig >> r;
    wire [3:0] rem = sig & ((4'd1 << r) - 4'd1);
    wire [3:0] half = (r == 0) ? 4'd0 : (4'd1 << (r - 2'd1));
    wire       up = (r != 0) && ((rem > half) || (rem == half && q[0]));
    wire [7:0] sub = (k >= 0) ? ({4'd0, sig} << k[2:0]) : ({4'd0, q} + {7'd0, up});
    always @(*) begin
        if (e == 4'hF && m == 3'h7)        bf16 = {s, 15'h7FC0};
        else if (sig == 0)                 bf16 = {s, 15'd0};
        else if (X > 11'sd127)             bf16 = {s, 8'hFF, 7'd0};
        else if (X >= -11'sd126)           bf16 = {s, xb, nrm[2:0], 4'd0};
        else                               bf16 = {s, 7'd0, sub};
    end
endmodule

module ot_s81eng_token_map_n32 (
    input wire clk, rst_n, in_v,
    input wire [20:0] in_tok,
    output reg out_v,
    input wire rst_copy_n, output wire[6:0] out_v_copy,
    output reg [16:0] out_cid,
    output reg fault
);
    wire legal = in_tok < 21'd129280;
    wire [71:0] q [0:7];
    reg pending;
    wire[16:0] selected;
    wire[575:0] qb;
    for(genvar b=0;b<8;b=b+1)begin:g_q assign qb[72*b+:72]=q[b];end
    for(genvar b=0;b<17;b=b+1)begin:g_sel
        ot_s81eng_token_bit #(.BIT(b)) u_b(.clk(clk),.rst_n(rst_n),.v(in_v),.legal(legal),.tag({in_tok[16:14],in_tok[1:0]}),.qb(qb),.sel(selected[b]),.cid(out_cid[b]));
    end
    // S81-ELEM2-ENGRR 10-21: ROM(512 ps clk->q) -> 32-way select -> 17-bit compare -> valid copies was zero-wire -73 ps.
    // The cid range check is an image-integrity fault: it is now taken from the registered out_cid one edge later
    // (same sticky fault), and the valid copies follow pending directly.
    wire valid_next=pending;
    reg chk;
    for(genvar vg=0;vg<7;vg=vg+1)begin:g_outcopy
        ot_s81eng_rr_validcap u_v(.ck(clk),.rn(rst_copy_n),.d(valid_next),.q(out_v_copy[vg]));
    end
    genvar g;
    generate for(g=0;g<8;g=g+1) begin: m
`ifndef SYNTHESIS
        ot_rom_4096x72_m8 #(.INSTANCE($sformatf("tmap%0d",g))) rom (
`else
        ot_rom_4096x72_m8 rom (
`endif
            .clk(clk), .ce_in(in_v && legal && in_tok[16:14]==g),
            .addr_in(in_tok[13:2]), .rd_out(q[g]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin pending<=0;out_v<=0;fault<=0;chk<=0;end
        else begin
            pending<=in_v && legal;
            out_v<=pending;
            chk<=pending;
            if(in_v && !legal) fault<=1;
            if(chk && out_cid>=17'd99092) fault<=1;
        end
    end
endmodule

(* keep_hierarchy = 1 *)module ot_s81eng_token_bit #(parameter integer BIT=0)(
 input wire clk,rst_n,v,legal,input wire[4:0] tag,input wire[575:0] qb,output reg sel,output reg cid);
 reg pending;reg[4:0] selq;
 always @(posedge clk or negedge rst_n)if(!rst_n)pending<=0;else pending<=v&&legal;
 always @(posedge clk)selq<=tag;
 integer b,l;
 always @*begin
  sel=0;
  for(b=0;b<8;b=b+1)for(l=0;l<4;l=l+1)sel=sel|(qb[72*b+17*l+BIT] && selq==5'(4*b+l));
 end
 always @(posedge clk)if(pending)cid<=sel;
endmodule

module ot_s81eng_win_n32 #(
    parameter integer NUSER = 64,
    parameter [16:0] PAD = 17'd2
) (
    input  wire        ck,
    input  wire        rst_n,       // landed regional leaf
    input wire[1:0] rst_copy_n,
    input  wire        en,          // strap: Engram home die
    input  wire        ks_v,
    input  wire [9:0]  ks_user,
    input  wire [20:0] ks_tok,
    input  wire [20:0] ks_pos,
    output reg         win_v,
    output reg  [2:0]  win_slot,
    output reg  [67:0] win_ids,
    output reg         fault
);
    wire        t_v = ks_v && en;
    wire        m_v; wire [6:0] m_v_copy,v2_copy; wire [16:0] m_cid; wire m_f;
    ot_s81eng_token_map_n32 u_map (.clk(ck), .rst_n(rst_n), .in_v(t_v), .in_tok(ks_tok), .out_v(m_v),.rst_copy_n(rst_copy_n[0]),.out_v_copy(m_v_copy), .out_cid(m_cid),
                                     .fault(m_f));
    // user / pos ride the map latency (2 edges); the user row is read on the start edge, captured one edge later
    reg  [9:0]  u1, u2; reg [20:0] p1, p2; reg v1, v2;
    wire [127:0] rd;
    reg  [50:0] h2;
    always @(posedge ck) begin u1 <= ks_user; u2 <= u1; p1 <= ks_pos; p2 <= p1; h2 <= rd[50:0]; end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; end else begin v1 <= t_v; v2 <= v1; end
    for(genvar vg=0;vg<7;vg=vg+1)begin:g_v2copy
        ot_s81eng_rr_validcap u_v(.ck(ck),.rn(rst_copy_n[1]),.d(v1),.q(v2_copy[vg]));
    end
    wire         b1 = (p2 < 21'd1), b2 = b1 | (p2 < 21'd2), b3 = b2 | (p2 < 21'd3);
    wire         wr = m_v && v2;
    ot_sram_1r1w_512x128_m4_r2c2 u_h (.clk(ck), .r_ce_in(t_v), .r_addr_in({3'd0, ks_user[5:0]}), .rd_out(rd),
        .w_ce_in(wr), .w_addr_in({3'd0, u2[5:0]}), .wd_in({77'd0, h2[33:0], m_cid}), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    wire[67:0] ids_next={b3 ? PAD : h2[50:34], b2 ? PAD : h2[33:17], b1 ? PAD : h2[16:0], m_cid};
    for(genvar wg=0;wg<7;wg=wg+1)begin:g_wi
        localparam integer W=(wg==6)?2:11;
        ot_s81eng_rr_wincap #(.W(W)) u_c(.ck(ck),.a(m_v_copy[wg]),.b(v2_copy[wg]),.d(ids_next[11*wg+:W]),.q(win_ids[11*wg+:W]));
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin win_v <= 1'b0; win_slot <= 3'd7; fault <= 1'b0; end
        else begin
            win_v <= wr;
            if (wr) win_slot <= win_slot + 3'd1;
            if ((t_v && ks_user >= 10'(NUSER)) || m_f || (v2 && !m_v) ||
                (t_v && ((v1 && ks_user == u1) || (v2 && ks_user == u2))))
                fault <= 1'b1;
        end
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_wincap #(parameter integer W=11)(input wire ck,a,b,input wire[W-1:0] d,output reg[W-1:0] q);
 always @(posedge ck)if(a&&b)q<=d;
endmodule

module ot_s81eng_head_n32 #(
    parameter [29:0] PCBASE = 30'd0   // Engram region base sector inside every PC (compiler image placement)
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         win_v,
    input  wire [2:0]   win_slot,
    input  wire         hq_v,
    input  wire [30:0]  hq_atom,
    input  wire [2:0]   hq_tag,
    output reg  [42:0]  rco,         // request chain {tag 7, sec 30, pc 5, v}
    input  wire [267:0] pci,         // response chain {d 256, tag 7, own 4, v}
    output reg          hr_v,
    output reg  [2:0]   hr_slot,
    output reg  [2:0]   hr_tag,
    output reg  [3:0]   hr_idx,
    output reg  [255:0] hr_d,
    output reg          fault
);
    wire[33:0] rq_word;
    reg [2:0]  nw;                    // rows written (this window)
    reg [2:0]  rr;                    // row being expanded
    reg [3:0]  ai;                    // atom of that row
    reg        run;
    reg [2:0]  slot;
    for(genvar hg=0;hg<3;hg=hg+1)begin:g_hw
        localparam integer W=(hg==2)?10:12;
        wire[33:0] req={hq_tag,hq_atom};
        wire[5:0] wsel,rsel;
        ot_s81eng_rr_headsel u_ws(.ix(nw),.v(hq_v),.q(wsel));
        ot_s81eng_rr_headsel u_rs(.ix(rr),.v(1'b1),.q(rsel));
        ot_s81eng_rr_headword #(.W(W)) u_w(.ck(ck),.wsel(wsel),.rsel(rsel),.d(req[12*hg+:W]),.q(rq_word[12*hg+:W]));
    end
    always @(posedge ck) if (win_v) slot <= win_slot;
    reg run_a, run_b;                   // slang: declared before the run FSM uses them (source order only)
    // row j arrives at t0 + j and is expanded from t0 + 1 + 9 j: always present, no wait, no check needed
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin nw <= 3'd0; rr <= 3'd0; ai <= 4'd0; run <= 1'b0; run_a <= 1'b0; run_b <= 1'b0; rco[0] <= 1'b0; fault <= 1'b0; end
        else begin
            if (hq_v && nw == 3'd6) fault <= 1'b1;                    // a 7th request in a window
            if (!run && nw != 3'd0) begin run <= 1'b1; rr <= 3'd0; ai <= 4'd0; end
            else if (run) begin
                if (ai == 4'd8) begin
                    ai <= 4'd0; rr <= rr + 3'd1;
                    if (rr == 3'd5) run <= 1'b0;
                end else ai <= ai + 4'd1;
            end
            if (run && ai == 4'd8 && rr == 3'd5) nw <= 3'd0;
            else if (hq_v && nw != 3'd6) nw <= nw + 3'd1;
            run_a <= run; run_b <= run_a; rco[0] <= run_b;
        end
    // S81-ELEM2-ENGRR 10-21: rr -> row select -> 31-b atom add -> PCBASE add -> rco was zero-wire -84.4 ps (836 ps).
    // Three registered stages (+2 edges on the request chain only, priced): A row word/ai, B atom add, C PCBASE add.
    // Both adds are 8-bit-chunk carry-selects.
    function automatic [30:0] csa31(input [30:0] a, input [30:0] b);
        reg [8:0] z, o; reg c; integer k;
        begin
            c = 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                z = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]};
                o = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]} + 9'd1;
                if (k < 3) csa31[8*k +: 8] = c ? o[7:0] : z[7:0]; else csa31[30:24] = c ? o[6:0] : z[6:0];
                c = c ? o[8] : z[8];
            end
        end
    endfunction
    reg [33:0] rq_a; reg [3:0] ai_a, ai_b; reg [30:0] at_b; reg [2:0] tg_b;
    always @(posedge ck) begin rq_a <= rq_word; ai_a <= ai; end
    always @(posedge ck) begin at_b <= csa31(rq_a[30:0], {27'd0, ai_a}); ai_b <= ai_a; tg_b <= rq_a[33:31]; end
    wire [30:0] pc_c = csa31({1'b0, PCBASE}, {5'd0, at_b[30:5]});
    always @(posedge ck) begin
        rco[5:1]   <= at_b[4:0];
        rco[35:6]  <= pc_c[29:0];
        rco[42:36] <= {tg_b, ai_b};
    end
    // response chain -> lookup
    always @(posedge ck or negedge rst_n)
        if (!rst_n) hr_v <= 1'b0; else hr_v <= pci[0];
    always @(posedge ck) begin hr_slot <= slot; hr_tag <= pci[11:9]; hr_idx <= pci[8:5]; hr_d <= pci[267:12]; end
endmodule
(* keep_hierarchy = 1 *)module ot_s81eng_rr_headword #(parameter integer W=11)(
 input wire ck,input wire[5:0] wsel,rsel,input wire[W-1:0] d,output reg[W-1:0] q);
 reg[W-1:0] row[0:5];
 for(genvar h=0;h<6;h=h+1)begin:g_row
  always @(posedge ck)if(wsel[h])row[h]<=d;
 end
 integer i;
 always @*begin q=0;for(i=0;i<6;i=i+1)q=q|({W{rsel[i]}}&row[i]);end
endmodule

(* keep_hierarchy = 1 *)module ot_s81eng_rr_bfraw_byte #(parameter integer LO=0)(input wire[7:0] code,scale,output wire[7:0] q);
    reg[15:0] bf16;
    wire       s = code[7];
    wire [3:0] e = code[6:3];
    wire [2:0] m = code[2:0];
    wire [3:0] sig = (e != 0) ? {1'b1, m} : {1'b0, m};
    // E: exponent of the significand's unit bit; value = sig * 2^E
    wire signed[8:0] e9=$signed({1'b0,scale})+$signed({5'd0,(e==0?4'd1:e)})-9'sd137;
    wire signed[10:0] E={{2{e9[8]}},e9};
    wire [1:0] p = sig[3] ? 2'd3 : sig[2] ? 2'd2 : sig[1] ? 2'd1 : 2'd0;
    wire signed [10:0] X = E + $signed({9'd0, p});
    wire [3:0] nrm = sig << (2'd3 - p);               // 1.fff
    wire [7:0] xb = X[7:0] + 8'd127;
    wire signed [10:0] k = E + 11'sd133;              // >= -3 on every code and scale
    wire [1:0] r = (k < 0) ? (~k[1:0] + 2'd1) : 2'd0; // -k for k in -3..-1
    wire [3:0] quotient = sig >> r;
    wire [3:0] rem = sig & ((4'd1 << r) - 4'd1);
    wire [3:0] half = (r == 0) ? 4'd0 : (4'd1 << (r - 2'd1));
    wire       up = (r != 0) && ((rem > half) || (rem == half && quotient[0]));
    wire [7:0] sub = (k >= 0) ? ({4'd0, sig} << k[2:0]) : ({4'd0, quotient} + {7'd0, up});
    always @(*) begin
        if (e == 4'hF && m == 3'h7)        bf16 = {s, 15'h7FC0};
        else if (sig == 0)                 bf16 = {s, 15'd0};
        else if (X > 11'sd127)             bf16 = {s, 8'hFF, 7'd0};
        else if (X >= -11'sd126)           bf16 = {s, xb, nrm[2:0], 4'd0};
        else                               bf16 = {s, 7'd0, sub};
    end
    assign q=bf16[LO+:8];
endmodule

(* keep_hierarchy=1 *)module ot_s81eng_rr_validcap(input wire ck,rn,d,output reg q);
 always @(posedge ck or negedge rn)if(!rn)q<=0;else q<=d;
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_bitcap(input wire ck,d,output reg q);
 always @(posedge ck)q<=d;
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_rvbyte #(parameter integer BANK=0)(input wire ck,rn,tx,last,bw,input wire[7:0]mask,output reg[7:0]q);
 wire clear_word,set_word;
 ot_s81eng_rr_rvselect u_sel(.tx(tx),.last(last),.bw(bw),.mask(mask),.clear_word(clear_word),.set_word(set_word));
 always @(posedge ck or negedge rn)if(!rn)q<=0;
 else if(clear_word)q<=0;
 else if(set_word)q<=q|mask;
endmodule

(* keep_hierarchy=1 *)module ot_s81eng_rr_rvselect(input wire tx,last,bw,input wire[7:0]mask,output wire clear_word,set_word);
 assign clear_word=tx&&last;
 assign set_word=bw&&(|mask);
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_pre3(input wire[2:0]a,output wire[7:0]y);
 for(genvar b=0;b<8;b=b+1)begin:g_d assign y[b]=(a==3'(b));end
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_pre2(input wire[1:0]a,output wire[3:0]y);
 for(genvar b=0;b<4;b=b+1)begin:g_d assign y[b]=(a==2'(b));end
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_rowmask(input wire[5:0]bc,output wire[5:0]row,output wire[63:0]mask);
 assign row=bc-6'd1;
 wire[7:0]lo,hi;
 ot_s81eng_rr_pre3 u_lo(.a(row[2:0]),.y(lo));
 ot_s81eng_rr_pre3 u_hi(.a(row[5:3]),.y(hi));
 for(genvar b=0;b<64;b=b+1)begin:g_d assign mask[b]=hi[b/8]&&lo[b%8];end
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_trainlast(input wire[6:0]fc,output wire last);
 assign last=fc==7'd95;
endmodule
(* keep_hierarchy=1 *)module ot_s81eng_rr_probe_read(input wire[4:0]ix,input wire[31:0]rv,output wire seen);
 wire[7:0]lo;wire[3:0]hi;wire[31:0]hit;
 ot_s81eng_rr_pre3 u_lo(.a(ix[2:0]),.y(lo));
 ot_s81eng_rr_pre2 u_hi(.a(ix[4:3]),.y(hi));
 for(genvar b=0;b<32;b=b+1)begin:g_d assign hit[b]=rv[b]&&hi[b/8]&&lo[b%8];end
 assign seen=|hit;
endmodule

(* keep_hierarchy=1 *)module ot_s81eng_rr_headsel(input wire[2:0]ix,input wire v,output wire[5:0]q);
 for(genvar h=0;h<6;h=h+1)begin:g_s assign q[h]=v&&(ix==3'(h));end
endmodule
