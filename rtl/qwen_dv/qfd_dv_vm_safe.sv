// GENERATED OPT-IN VM SAFE CANDIDATE; native qualification pending.
`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_vm -- the Q-DV slice's local memories (vector memory slice, constant memory, BF16 table, SU program store).
//
// Every array is the SAME 1R1W macro family the central VM uses (qvm_su_bank_native: ot_sram_1r1w_1024x256_m2_r2c2);
// one 256-b macro word = 8 FP32 = one SU vector of the 8-lane slice.  Fixed-latency, no ready / credit: every read
// answers exactly 2 edges after the lane's request register (macro read edge + one capture flop at the macro pins =
// ot_hdc_vstream_lane ML = 1); a schedule violation (operand vector spanning two words, read address outside the
// array, two writers in one bank on one edge, malformed table write) raises the sticky `fault`, never a stall.
//
//   Same-row read and write on one edge: the macro read is gated off (1R1W macros do not define it); the lane
//   operand of that edge is then the previous read word.  The SU issues reads for operands an op does not use
//   (vb/vc with ma/ad bypassing them), so this is legal; a CONSUMED operand on the row being written is a compiler
//   schedule error, exactly as in the central VM.
//   VM    3 operand replicas (A, B, C: one read port each) x 2 banks (element bit 3) x 1024 words x 8 FP32
//         = 16,384 FP32 per replica.  Every write goes to all three replicas.  Element e: bank e[3], word e[13:4],
//         lane e[2:0].  Write sources: SU lanes (8 el, one bank), 16-el words (station / AR return / D2D return:
//         both banks), single elements (reducer, scalar-tree r, root total).
//   CROM  2 banks x {lo, hi} x 1024 x 8 x 32 b = 16,384 (lo, hi) FP32 pairs (gamma / QK gains: lo; RoPE: lo = cos,
//         hi = sin).  Per-lane reads as the VM; written 16 pairs per edge by a stream table word.
//   BTAB  BF16 table (row scales; the SU weight-ROM operand port): 2 copies (station port, SU port) x 4 banks
//         (word bit [1:0]) x 128 x 256 b = 512 words x 16 BF16 = 8,192 BF16 per copy; written 4 words per edge.
//   PROG  SU instruction store: 2 banks (pidx bit 0) x 256 x 457 b (2 macros of 256 wide each) = 512 instructions;
//         written 2 instructions per edge.
// MUT (bench negative controls): 4 = CROM lo / hi swapped (cos <-> sin, gain <-> 0); 5 = the B operand port answers
// with the C replica's word (both must FAIL).
// =====================================================================================================================
module qfd_dv_vm #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // SU operand reads: per lane request (registered in the lane), answer 2 edges later
    input  wire [7:0]    a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]    cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    // BF16 table: SU weight-ROM port (word = element >> 4) and station scale port (word address)
    input  wire          bs_re,
    input  wire [23:0]   bs_addr,            // word index (element >> 4)
    output wire [255:0]  bs_q,
    input  wire          bt_re,
    input  wire [8:0]    bt_word,
    output wire [255:0]  bt_q,
    // SU program store
    input  wire          p_re,
    input  wire [8:0]    p_idx,
    output wire [456:0]  p_q,
    // writes (VM window addresses only: the slice top routes other windows elsewhere)
    input  wire [7:0]    su_we,
    input  wire [8*24-1:0] su_waddr,
    input  wire [8*32-1:0] su_wdata,
    input  wire          w16_we,
    input  wire [23:0]   w16_addr,
    input  wire [511:0]  w16_data,
    input  wire          w1_we,
    input  wire [23:0]   w1_addr,
    input  wire [31:0]   w1_data,
    // table writes from the stream tap: kind 1 CROM (16 pairs at 16-pair word tw_addr), 2 BTAB (4 words at 4-aligned
    // word tw_addr), 3 PROG (2 instructions at even pidx tw_addr)
    input  wire          tw_we,
    input  wire [1:0]    tw_kind,
    input  wire [23:0]   tw_addr,
    input  wire [1023:0] tw_data,
    output reg           fault
);
    integer l;
    integer b;
    // ------------------------------------------------------------------ read-side address check (lane 0 = reference)
    function automatic bad_vec(input [7:0] re, input [8*24-1:0] ad);
        integer k;
        reg [17:0] bad;
        begin
            for(k=0;k<8;k=k+1) begin
                bad[k]=re[k] && ad[24*k+4+:20]!=ad[4+:20];
                bad[8+k]=re[k] && ad[24*k+3]!=ad[3];
            end
            bad[16]=re[0] && ad[23:14]!=0;
            bad[17]=(|re) && !re[0];
            bad_vec=|bad;
        end
    endfunction
    // ------------------------------------------------------------------ VM: 3 replicas x 2 banks

    // Same combinational write edge, fixed destinations. Last active SU lane
    // wins a repeated low-slot address, including faulty schedules, as before.
    wire su_active=|su_we;
    wire [1:0] wb_we;
    wire [9:0] wb_row[0:1];
    wire [255:0] wb_d[0:1],wb_m[0:1];
    wire w_coll=(su_active && w1_we && su_waddr[3]==w1_addr[3]) ||
                (w16_we && (su_active || w1_we));
    wire [7:0] bad_su_lane;
    genvar wl;
    generate for(wl=0;wl<8;wl=wl+1) begin:g_write_check
        assign bad_su_lane[wl]=su_we[wl] &&
            ((su_waddr[24*wl+3+:21]!=su_waddr[3+:21]) || !su_we[0]);
    end endgenerate
    wire w_bad=(w1_we && w1_addr[23:14]!=0) ||
        (su_active && ((|bad_su_lane) || su_waddr[23:14]!=0)) ||
        (w16_we && (w16_addr[3:0]!=0 || w16_addr[23:14]!=0));
    genvar wb,ws,wi;
    generate for(wb=0;wb<2;wb=wb+1) begin:g_write_bank
        wire take_su=su_active && su_waddr[3]==wb;
        wire take_one=w1_we && w1_addr[3]==wb;
        assign wb_we[wb]=w16_we || take_su || take_one;
        assign wb_row[wb]=w16_we ? w16_addr[13:4] :
                            take_su ? su_waddr[13:4] :
                            take_one ? w1_addr[13:4] : 10'd0;
        for(ws=0;ws<8;ws=ws+1) begin:g_slot
            wire [7:0] hit,pick;
            for(wi=0;wi<8;wi=wi+1) begin:g_lane
                assign hit[wi]=su_we[wi] && su_waddr[24*wi+:3]==ws;
                if(wi==7) assign pick[wi]=hit[wi];
                else assign pick[wi]=hit[wi] && !(|(hit >> (wi+1)));
            end
            wire [31:0] sd=
                ({32{pick[0]}} & su_wdata[0+:32]) |
                ({32{pick[1]}} & su_wdata[32+:32]) |
                ({32{pick[2]}} & su_wdata[64+:32]) |
                ({32{pick[3]}} & su_wdata[96+:32]) |
                ({32{pick[4]}} & su_wdata[128+:32]) |
                ({32{pick[5]}} & su_wdata[160+:32]) |
                ({32{pick[6]}} & su_wdata[192+:32]) |
                ({32{pick[7]}} & su_wdata[224+:32]);
            wire one_slot=take_one && w1_addr[2:0]==ws;
            assign wb_d[wb][32*ws+:32]=w16_we ? w16_data[256*wb+32*ws+:32] :
                                      take_su ? sd : one_slot ? w1_data : 32'd0;
            assign wb_m[wb][32*ws+:32]={32{w16_we ||
                                      (take_su ? (|hit) : one_slot)}};
        end
    end endgenerate
    // read requests: lane 0's word, bank; per-lane element offsets travel to the capture stage
    wire [2:0] rq_re = {c_re[0], b_re[0], a_re[0]};
    wire [24*3-1:0] rq_a0 = {c_addr[23:0], b_addr[23:0], a_addr[23:0]};
    wire [3*256*2-1:0] vm_rd;                 // [op][bank]
    genvar op, bk;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rep
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
            ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck),
                .r_ce_in(rq_re[op] && rq_a0[24*op+3] == bk[0] && !(wb_we[bk] && wb_row[bk] == rq_a0[24*op+4 +: 10])),
                .r_addr_in(rq_a0[24*op+4 +: 10]),
                .rd_out(vm_rd[(2*op+bk)*256 +: 256]),
                .w_ce_in(wb_we[bk]), .w_addr_in(wb_row[bk]), .wd_in(wb_d[bk]), .w_mask_in(wb_m[bk]),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate

    // Stage1 captures per-lane address controls on the macro-read edge;
    // stage2 captures the macro outputs and onehot controls on the same edge.
    // Every select output drives <=32 data gates, with explicit kept identity.
    reg [3*512-1:0] cap;
    always @(posedge ck) cap<=vm_rd;
    wire [3*256-1:0] ext_q;
    genvar vo,vl,vs;
    generate for(vo=0;vo<3;vo=vo+1) begin:g_operand
        for(vl=0;vl<8;vl=vl+1) begin:g_lane
            wire [23:0] addr=(vo==0) ? a_addr[24*vl+:24] :
                               (vo==1) ? b_addr[24*vl+:24] : c_addr[24*vl+:24];
            wire [3:0] stage1;
            for(vs=0;vs<4;vs=vs+1) begin:g_s1
                // All lanes use lane0 bank, but each has its own kept copy.
                wire d=(vs==3) ? rq_a0[24*vo+3] : addr[vs];
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(1000+vo*128+vl*4+vs)) u_k
                    (.ck(ck),.d(d),.q(stage1[vs]));
            end
            wire [15:0] sel;
            wire [31:0] terms[0:15];
            for(vs=0;vs<16;vs=vs+1) begin:g_s2
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(2000+vo*128+vl*16+vs)) u_k
                    (.ck(ck),.d(stage1==vs),.q(sel[vs]));
                assign terms[vs]={32{sel[vs]}} & cap[512*vo+32*vs+:32];
            end
            assign ext_q[256*vo+32*vl+:32]=
                terms[0]|terms[1]|terms[2]|terms[3]|terms[4]|terms[5]|terms[6]|terms[7]|
                terms[8]|terms[9]|terms[10]|terms[11]|terms[12]|terms[13]|terms[14]|terms[15];
        end
    end endgenerate
    assign a_q=ext_q[0+:256];
    assign b_q=(MUT==5) ? ext_q[512+:256] : ext_q[256+:256];
    assign c_q=ext_q[512+:256];
    // ------------------------------------------------------------------ CROM: 2 banks x {lo, hi}
    wire [4*256-1:0] cr_rd;                   // [bank][lo/hi]
    reg  [255:0] cw_lo [0:1], cw_hi [0:1];
    always @(*) begin
        for (b = 0; b < 2; b = b + 1)
            for (l = 0; l < 8; l = l + 1) begin
                cw_lo[b][32*l +: 32] = tw_data[64*(8*b+l) +: 32];
                cw_hi[b][32*l +: 32] = tw_data[64*(8*b+l) + 32 +: 32];
            end
    end
    wire cr_w = tw_we && tw_kind == 2'd1;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crom
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_lo[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk+1)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_hi[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate

    reg [1023:0] ccap;
    always @(posedge ck) ccap<=cr_rd;
    genvar cl,cs,ch;
    generate for(cl=0;cl<8;cl=cl+1) begin:g_c_lane
        wire [3:0] stage1;
        for(cs=0;cs<4;cs=cs+1) begin:g_s1
            wire d=(cs==3) ? cr_addr[3] : cr_addr[24*cl+cs];
            (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(3000+cl*4+cs)) u_k
                (.ck(ck),.d(d),.q(stage1[cs]));
        end
        wire [63:0] value;
        for(ch=0;ch<2;ch=ch+1) begin:g_half
            wire [15:0] sel;
            wire [31:0] terms[0:15];
            for(cs=0;cs<16;cs=cs+1) begin:g_s2
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(4000+cl*32+ch*16+cs)) u_k
                    (.ck(ck),.d(stage1==cs),.q(sel[cs]));
                assign terms[cs]={32{sel[cs]}} & ccap[512*(cs/8)+256*ch+32*(cs%8)+:32];
            end
            assign value[32*ch+:32]=
                terms[0]|terms[1]|terms[2]|terms[3]|terms[4]|terms[5]|terms[6]|terms[7]|
                terms[8]|terms[9]|terms[10]|terms[11]|terms[12]|terms[13]|terms[14]|terms[15];
        end
        assign cr_q[64*cl+:64]=(MUT==4) ? {value[31:0],value[63:32]} : value;
    end endgenerate
    // ------------------------------------------------------------------ BTAB: 2 copies x 4 banks x 128 x 256
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [8:0] bs_word = bs_addr[8:0];        // the lane's weight-ROM word index (lane: cura >> log2(WR))
    wire [2*4*256-1:0] bt_rd;
    genvar cp;
    generate for (cp = 0; cp < 2; cp = cp + 1) begin : g_btc
        wire       re = (cp == 0) ? bt_re : bs_re;
        wire [8:0] wd = (cp == 0) ? bt_word : bs_word;
        for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(re && wd[1:0] == bk[1:0]), .r_addr_in(wd[8:2]),
                .rd_out(bt_rd[(4*cp+bk)*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
                .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate

    reg [1:0] t1_bank,s1b_bank;
    reg [2047:0] btcap;
    always @(posedge ck) begin
        t1_bank<=bt_word[1:0];s1b_bank<=bs_word[1:0];btcap<=bt_rd;
    end
    genvar tc,tg,ts;
    generate for(tc=0;tc<2;tc=tc+1) begin:g_bt_port
        for(tg=0;tg<8;tg=tg+1) begin:g_chunk
            wire [3:0] sel;
            wire [31:0] terms[0:3];
            for(ts=0;ts<4;ts=ts+1) begin:g_s2
                wire [1:0] bank=(tc==0) ? t1_bank : s1b_bank;
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(5000+tc*32+tg*4+ts)) u_k
                    (.ck(ck),.d(bank==ts),.q(sel[ts]));
                assign terms[ts]={32{sel[ts]}} & btcap[1024*tc+256*ts+32*tg+:32];
            end
            if(tc==0) assign bt_q[32*tg+:32]=terms[0]|terms[1]|terms[2]|terms[3];
            else assign bs_q[32*tg+:32]=terms[0]|terms[1]|terms[2]|terms[3];
        end
    end endgenerate
    // ------------------------------------------------------------------ PROG: 2 banks x (256 + 201) x 256
    wire pw = tw_we && tw_kind == 2'd3;
    wire [4*256-1:0] p_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_prog
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in(tw_data[512*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk+1)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in({55'd0, tw_data[512*bk + 256 +: 201]}), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate

    reg p1_bank;
    reg [1023:0] pcap;
    always @(posedge ck) begin p1_bank<=p_idx[0];pcap<=p_rd;end
    genvar pg,ps;
    generate for(pg=0;pg<15;pg=pg+1) begin:g_p_chunk
        localparam integer CW=(457-32*pg<32) ? 457-32*pg : 32;
        wire [1:0] sel;
        wire [CW-1:0] term[0:1];
        for(ps=0;ps<2;ps=ps+1) begin:g_s2
            (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(6000+pg*2+ps)) u_k
                (.ck(ck),.d(p1_bank==ps),.q(sel[ps]));
            assign term[ps]={CW{sel[ps]}} & pcap[512*ps+32*pg+:CW];
        end
        assign p_q[32*pg+:CW]=term[0]|term[1];
    end endgenerate
    // ------------------------------------------------------------------ faults (sticky)
    wire rd_bad = bad_vec(a_re, a_addr) || bad_vec(b_re, b_addr) || bad_vec(c_re, c_addr) ||
                  (cr_re != 8'd0 && (!cr_re[0] || cr_addr[23:14] != 10'd0)) ||
                  (cr_re != 8'd0 && bad_vec(cr_re, cr_addr & {8{24'h003FFF}}));
    wire tw_bad = tw_we && ((tw_kind == 2'd0) || (tw_kind == 2'd1 && tw_addr[23:10] != 0) ||
                            (tw_kind == 2'd2 && (tw_addr[1:0] != 0 || tw_addr[23:9] != 0)) ||
                            (tw_kind == 2'd3 && tw_addr[23:8] != 0));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | rd_bad | w_bad | w_coll | tw_bad | (bs_re && bs_addr[23:9] != 0);
endmodule

// Independent parameter identities preserve each physical select copy.
module qfd_dv_vm_keep_bit #(parameter integer ID=0)(input wire ck,d, (* keep *) output reg q);
    always @(posedge ck) q<=d;
endmodule
