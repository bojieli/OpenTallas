`timescale 1ns/1ps
`default_nettype none
// HBM-P5-PINS 2026-10-23: the SM plan core "lx" (physical/die_plan/hbm/sm_split, HBM d4g plan v2) as a real module.
// lx = ot_hbm_sm_attn_leafh MINUS its native column (u_tcc, the plan core "ln" = ot_hbm_sm_attn_native_col): the
// x store (u_xs), the block-dot column (u_bdc), the BF16 launch registers, the publish pipe and the G1 select.  The
// body is ot_hbm_sm_attn_leafh's verbatim; u_tcc's pins become the tcc_* ports.  ot_hbm_sm_attn_leafh_q composes
// lx + native_col back into a drop-in ot_hbm_sm_attn_leafh (same ports, same cycle behaviour; lock-step bench
// rtl/hbm_accel/sm/attn/qsplit/tbv_sm_attn_tile_q.sv).
// Boundary registers: every lx -> ln pin is launched from a flop (fv/ffirst/.../fw/fx, pub_pipe, fold0*), except
//   tcc_pub_slot = a 3:1 select of pub_pipe flops by the static attn_column strap (a flop bit or a constant once
//   the strap is tied).  ln -> lx: native_col's result flops -> the G1 select -> gv_q/gy_q/gt_q (the as-built
//   capture, REG->LOGIC->REG; no cycle added).
// tcc_rst_n: with OT_SMH_RSTPIN the leaf's kept reset copy rq[2]; otherwise the leaf reset itself, so the port only
//   exists under OT_SMH_RSTPIN (ot_hbm_sm_attn_leafh_q then drives the native column's reset from rst_n).
module ot_hbm_sm_attn_leafh_lx #(
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
    output wire gv, output wire gf, output wire [31:0] gy, output wire [TAGW-1:0] gt,
    // ---- native column (ln) interface
`ifdef OT_SMH_RSTPIN
    output wire tcc_rst_n,
`endif
    output wire tcc_i_v, tcc_i_first, tcc_i_qk_last, tcc_i_pv_last, tcc_i_run_first, tcc_i_run_last,
    output wire [TAGW-1:0] tcc_i_tag,
    output wire [255:0] tcc_i_w, tcc_i_x,
    output wire tcc_pub_start,
    output wire [2:0] tcc_pub_slot,
    output wire tcc_fold_start,
    output wire [2:0] tcc_fold_a, tcc_fold_b,
    input  wire tcc_ov,
    input  wire [31:0] tcc_y,
    input  wire [TAGW-1:0] tcc_otag,
    input  wire tcc_fault,
    input  wire tcc_pub_v,
    input  wire [31:0] tcc_pub_data,
    input  wire [3:0] tcc_pub_word,
    input  wire [1:0] tcc_pub_out_slot              // native_col pub_out_slot[1:0] (bit 2 and pub_tag unused by the leaf)
);
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;
`ifdef OT_SMH_RSTPIN
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];
    assign tcc_rst_n = r_tcc;
`else
    wire r_xs = rst_n, r_bdc = rst_n, r_g = rst_n, r_x = rst_n;
`endif
    ot_hbm_accel_smh_xs #(.TAGW(TAGW),.NBEAT(NBEAT)) u_xs (.clk(clk), .rst_a(r_xs), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rl1(rl1), .bk1(bk1), .ohl1(ohl1), .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast),
        .o_ifp4(ifp4), .o_itag(itag), .o_iw(iw), .o_ix(ix), .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e));
    wire marker=iv_f && ifp4;
    wire input_pv=marker && iw[129];
    wire input_arithmetic=iv_f && (!marker || iw[137]);
    reg bv,bfirst,blast,bfp4,fv,ffirst,fqlast,fplast,frfirst,frlast;
    reg [TAGW-1:0] btag,ftag;
    reg [LBS*266-1:0] bw,bx;
    reg [255:0] fw,fx;
    reg [4:0] publish0;
    reg fold0; reg [2:0] fold0_a, fold0_b;
    always @(posedge clk or negedge r_x)
        if(!r_x)begin bv<=0;fv<=0;publish0<=0;fold0<=0;end
        else begin
            bv<=iv_b;fv<=input_arithmetic;
            publish0<={iw[145],marker&&iw[134],iw[131],iw[136:135]};
            fold0<=marker&&iw[138];
        end
    always @(posedge clk)begin
        bfirst<=ifirst;blast<=ilast;bfp4<=ifp4;btag<=itag;
        bw<=iw[0+:LBS*266];bx<=ix[0+:LBS*266];
        fold0_a<=iw[141:139];fold0_b<=iw[144:142];
        ffirst<=ifirst_e;fqlast<=ilast_e&&!input_pv;fplast<=ilast_e&&input_pv;
        frfirst<=iw[132];frlast<=iw[133];ftag<=itag_e;
        fw<=iw[LBS*266+:256];
        fx<=input_pv?{16{iw[16*attn_column+:16]}}:ix[LBS*266+:256];
    end
    wire bov,bfault;
    wire [31:0] by;
    wire [TAGW-1:0] bt;
    ot_hbm_accel_smh_bdc #(.LBS(LBS),.IL(IL),.TAGW(TAGW)) u_bdc(
        .clk(clk),.rst_a(r_bdc),.i_v(bv),.i_first(bfirst),.i_last(blast),.i_fp4(bfp4),
        .i_tag(btag),.i_w(bw),.i_x(bx),.ov(bov),.y(by),.otag(bt),.fault(bfault));
    reg [4:0] pub_pipe[0:48];
    integer d;
    always @(posedge clk or negedge r_x)
        if(!r_x)for(d=0;d<49;d=d+1)pub_pipe[d]<=0;
        else begin
            pub_pipe[0]<=publish0;
            for(d=1;d<49;d=d+1)pub_pipe[d]<=pub_pipe[d-1];
        end
    wire [4:0] pc=pub_pipe[{attn_row,4'b0000}];
    wire [2:0] selected_slot=pc[2]?(pc[4]?{2'b00,attn_column[0]}:{attn_column[0],pc[1:0]}):attn_column;
    reg published_h128;
    always @(posedge clk)if(pc[3])published_h128<=pc[2];
    // ---- u_tcc (ln) pins
    assign tcc_i_v=fv; assign tcc_i_first=ffirst; assign tcc_i_qk_last=fqlast; assign tcc_i_pv_last=fplast;
    assign tcc_i_run_first=frfirst; assign tcc_i_run_last=frlast; assign tcc_i_tag=ftag;
    assign tcc_i_w=fw; assign tcc_i_x=fx;
    assign tcc_pub_start=pc[3]; assign tcc_pub_slot=selected_slot;
    assign tcc_fold_start=fold0; assign tcc_fold_a=fold0_a; assign tcc_fold_b=fold0_b;
    wire fov=tcc_ov, ffault=tcc_fault, ps_v=tcc_pub_v;
    wire [31:0] fy=tcc_y, ps_data=tcc_pub_data;
    wire [TAGW-1:0] ft=tcc_otag;
    wire [3:0] ps_word=tcc_pub_word;
    wire [1:0] ps_slot=tcc_pub_out_slot;
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

// lx + ln = a drop-in ot_hbm_sm_attn_leafh (bench/composition only; the die binds lx and native_col as two cores).
module ot_hbm_sm_attn_leafh_q #(
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
    wire t_rst, i_v, i_first, i_qk_last, i_pv_last, i_run_first, i_run_last, pub_start, fold_start;
    wire [TAGW-1:0] i_tag, otag, pub_tag, pv_tag;
    wire [255:0] i_w, i_x;
    wire [2:0] pub_slot, fold_a, fold_b, pub_out_slot;
    wire ov, fault, pub_v, pv_v;
    wire [31:0] y, pub_data;
    wire [3:0] pub_word;
    wire [511:0] pv_y;
`ifndef OT_SMH_RSTPIN
    assign t_rst = rst_n;
`endif
    ot_hbm_sm_attn_leafh_lx #(.LBS(LBS),.LSB(LSB),.IL(IL),.TAGW(TAGW),.XD(XD),.NBEAT(NBEAT),.TCK(TCK),.NMG(NMG),
                              .A1B(A1B),.A2B(A2B)) u_lx (
        .clk(clk),.rst_n(rst_n),.attn_column(attn_column),.attn_row(attn_row),.xs_a1(xs_a1),.xs_g1(xs_g1),
        .xs_a2(xs_a2),.xs_g2(xs_g2),.rl1(rl1),.bk1(bk1),.ohl1(ohl1),.gv(gv),.gf(gf),.gy(gy),.gt(gt),
`ifdef OT_SMH_RSTPIN
        .tcc_rst_n(t_rst),
`endif
        .tcc_i_v(i_v),.tcc_i_first(i_first),.tcc_i_qk_last(i_qk_last),.tcc_i_pv_last(i_pv_last),
        .tcc_i_run_first(i_run_first),.tcc_i_run_last(i_run_last),.tcc_i_tag(i_tag),.tcc_i_w(i_w),.tcc_i_x(i_x),
        .tcc_pub_start(pub_start),.tcc_pub_slot(pub_slot),.tcc_fold_start(fold_start),.tcc_fold_a(fold_a),
        .tcc_fold_b(fold_b),.tcc_ov(ov),.tcc_y(y),.tcc_otag(otag),.tcc_fault(fault),.tcc_pub_v(pub_v),
        .tcc_pub_data(pub_data),.tcc_pub_word(pub_word),.tcc_pub_out_slot(pub_out_slot[1:0]));
    ot_hbm_sm_attn_native_col #(.TAGW(TAGW),.LV(4),.PUBLISH(1)) u_tcc(
        .clk(clk),.rst_n(t_rst),.i_v(i_v),.i_first(i_first),.i_qk_last(i_qk_last),.i_pv_last(i_pv_last),
        .i_run_first(i_run_first),.i_run_last(i_run_last),.i_tag(i_tag),.i_w(i_w),.i_x(i_x),
        .ov(ov),.y(y),.otag(otag),.pv_v(pv_v),.pv_y(pv_y),.pv_tag(pv_tag),.fault(fault),
        .pub_start(pub_start),.pub_slot(pub_slot),.pub_v(pub_v),.pub_data(pub_data),
        .pub_word(pub_word),.pub_out_slot(pub_out_slot),.pub_tag(pub_tag),
        .fold_start(fold_start),.fold_a(fold_a),.fold_b(fold_b));
endmodule
`default_nettype wire
