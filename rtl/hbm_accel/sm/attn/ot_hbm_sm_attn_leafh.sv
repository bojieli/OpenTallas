`timescale 1ns/1ps
`default_nettype none
module ot_hbm_sm_attn_leafh #(
    parameter integer LBS = 2, parameter integer LSB = 16, parameter integer IL = 8, parameter integer TAGW = 16,
    parameter integer XD = 128, parameter integer NBEAT = 13, parameter integer TCK = 1, parameter integer NMG = 32,
    parameter integer A1B = 9, parameter integer A2B = 7
) (
    input wire clk,rst_n,
    input wire [2:0] attn_column,input wire [1:0] attn_row,
    input  wire [A1B-1:0] xs_a1, input wire [4:0] xs_g1, input wire [A2B-1:0] xs_a2, input wire [4:0] xs_g2,
    input  wire [6+TAGW+LBS*266+LSB*16+1+$clog2(XD)-1:0] rl1,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]            bk1,
    input  wire [NBEAT-1:0]                              ohl1,
    output wire gv, output wire gf, output wire [31:0] gy, output wire [TAGW-1:0] gt
);
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;
`ifdef OT_SMH_RSTPIN
    // el1013-smh-r11: the leaf band's reset copy lands in one kept register per consumer (x store, block-dot column, the
    // three BF16 column tiles, the G1 select), each beside its consumer's rst_a pin
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];
`else
    wire r_xs = rst_n, r_bdc = rst_n, r_tcc = rst_n, r_g = rst_n, r_x = rst_n;
`endif
    ot_hbm_accel_smh_xs #(.TAGW(TAGW),.NBEAT(NBEAT)) u_xs (.clk(clk), .rst_a(r_xs), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rl1(rl1), .bk1(bk1), .ohl1(ohl1), .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast),
        .o_ifp4(ifp4), .o_itag(itag), .o_iw(iw), .o_ix(ix), .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e));
    // Reuse the same existing XS, block-dot column, tcl halves and QK tree.
    // Reserved bf+fp4 marker is meaningful only on a valid BF transport beat.
    wire marker=iv_f && ifp4;
    wire input_pv=marker && iw[129];
    wire input_arithmetic=iv_f && (!marker || iw[137]);
    reg bv,bfirst,blast,bfp4,fv,ffirst,fqlast,fplast,frfirst,frlast;
    reg [TAGW-1:0] btag,ftag;
    reg [LBS*266-1:0] bw,bx;
    reg [255:0] fw,fx;
    reg [3:0] publish0;
    always @(posedge clk or negedge r_x)
        if(!r_x)begin bv<=0;fv<=0;publish0<=0;end
        else begin
            bv<=iv_b;fv<=input_arithmetic;
            publish0<={marker&&iw[134],iw[131],iw[136:135]};
        end
    always @(posedge clk)begin
        bfirst<=ifirst;blast<=ilast;bfp4<=ifp4;btag<=itag;
        bw<=iw[0+:LBS*266];bx<=ix[0+:LBS*266];
        ffirst<=ifirst_e;fqlast<=ilast_e&&!input_pv;fplast<=ilast_e&&input_pv;
        frfirst<=iw[132];frlast<=iw[133];ftag<=itag_e;
        fw<=iw[LBS*266+:256];
        fx<=input_pv?{16{iw[16*attn_column+:16]}}:ix[LBS*266+:256];
    end
    wire bov,bfault,fov,ffault,pv_v,ps_v;
    wire [31:0] by,fy,ps_data;
    wire [TAGW-1:0] bt,ft,pv_tag,ps_tag;
    wire [511:0] pv_y;
    wire [3:0] ps_word;
    wire [2:0] ps_slot;
    ot_hbm_accel_smh_bdc #(.LBS(LBS),.IL(IL),.TAGW(TAGW)) u_bdc(
        .clk(clk),.rst_a(r_bdc),.i_v(bv),.i_first(bfirst),.i_last(blast),.i_fp4(bfp4),
        .i_tag(btag),.i_w(bw),.i_x(bx),.ov(bov),.y(by),.otag(bt),.fault(bfault));
    // Fixed16cycle leaf staggering packs four scalar lanes into the existing
    // one-word/column gather. The row strap is static and width is unchanged.
    reg [3:0] pub_pipe[0:48];
    integer d;
    always @(posedge clk or negedge r_x)
        if(!r_x)for(d=0;d<49;d=d+1)pub_pipe[d]<=0;
        else begin
            pub_pipe[0]<=publish0;
            for(d=1;d<49;d=d+1)pub_pipe[d]<=pub_pipe[d-1];
        end
    wire [3:0] pc=pub_pipe[{attn_row,4'b0000}];
    wire [2:0] selected_slot=pc[2]?{attn_column[0],pc[1:0]}:attn_column;
    reg published_h128;
    always @(posedge clk)if(pc[3])published_h128<=pc[2];
    ot_hbm_sm_attn_native_col #(.TAGW(TAGW),.LV(4),.PUBLISH(1)) u_tcc(
        .clk(clk),.rst_n(r_tcc),.i_v(fv),.i_first(ffirst),.i_qk_last(fqlast),.i_pv_last(fplast),
        .i_run_first(frfirst),.i_run_last(frlast),.i_tag(ftag),.i_w(fw),.i_x(fx),
        .ov(fov),.y(fy),.otag(ft),.pv_v(pv_v),.pv_y(pv_y),.pv_tag(pv_tag),.fault(ffault),
        .pub_start(pc[3]),.pub_slot(selected_slot),.pub_v(ps_v),.pub_data(ps_data),
        .pub_word(ps_word),.pub_out_slot(ps_slot),.pub_tag(ps_tag));
    wire [11:0] scalar_row=published_h128?{4'd0,ps_slot[1:0],attn_row,ps_word}:{6'd0,attn_row,ps_word};
    reg gv_q,gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(posedge clk or negedge r_g)
        if(!r_g)begin gv_q<=0;gf_q<=0;end
        else begin gv_q<=bov|fov|ps_v;gf_q<=bfault|ffault|(bov&&fov)|(ps_v&&(bov||fov));end
    always @(posedge clk)begin
        gy_q<=ps_v?ps_data:bov?by:fy;
        gt_q<=ps_v?{scalar_row,1'b1,3'd0}:bov?bt:ft;
    end
    assign gv=gv_q;assign gf=gf_q;assign gy=gy_q;assign gt=gt_q;
endmodule
`default_nettype wire
