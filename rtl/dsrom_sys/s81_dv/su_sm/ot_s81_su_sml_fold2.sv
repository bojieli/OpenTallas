`timescale 1ns/1ps
// Two logical lanes share one multiply/add/exp pipeline. The static input
// schedule leaves at least one idle edge after each two-lane operand vector.
// Logical-lane score stores and maxima remain independent; the parent rebuilds
// the original 16-lane vector before its unchanged reduction tree.
module ot_s81_su_sml_fold2 #(
 parameter integer NVMAX=40, LM=5, LA=4, MUT=0
)(
 input wire clk, rst_in, sk_en, i_cv,
 input wire [6:0] i_nv,
 input wire [31:0] i_scale, i_sink,
 input wire i_sv, input wire [63:0] i_s,
 input wire i_mv, input wire [31:0] i_nmb,
 output reg o_mxv, output reg [63:0] o_mx,
 output reg o_ev, o_es, o_el, output reg [63:0] o_e,
 output reg o_fault
);
 localparam integer D_EXP=7*LM+8*LA+4, DE=LA+D_EXP;
 reg rr0,rr1;
 always @(posedge clk or negedge rst_in)
  if(!rst_in) begin rr0<=0;rr1<=0;end else begin rr0<=1;rr1<=rr0;end
 wire rn=rr1;
 function automatic [31:0] okey(input [31:0] x);
  okey=x[31]?~x:{1'b1,x[30:0]};
 endfunction
 reg cv,sv,mv,ske,pending;
 reg [6:0] nvp,nv;
 reg [31:0] scalep,sinkp,scale,sink,nmbp,sp,hi;
 reg ctx;
 always @(posedge clk) begin
  nvp<=i_nv;scalep<=i_scale;sinkp<=i_sink;nmbp<=i_nmb;ske<=sk_en;
  if(i_sv) begin sp<=i_s[31:0];hi<=i_s[63:32];end
  else if(pending) sp<=hi;
  if(cv) begin nv<=nvp;scale<=scalep;sink<=sinkp;end
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin cv<=0;sv<=0;mv<=0;pending<=0;ctx<=0;o_fault<=0;end
  else begin
   cv<=i_cv;mv<=i_mv;sv<=i_sv||pending;ctx<=pending;
   pending<=i_sv;
   if(i_sv&&pending) o_fault<=1;
  end
 wire [LM:0] smv,sctx,inactive;
 ot_hdc_vline #(.D(LM)) u_mv(.clk(clk),.rst_n(rn),.v(sv),.vd(smv));
 ot_hdc_vline #(.D(LM)) u_mc(.clk(clk),.rst_n(rn),.v(ctx),.vd(sctx));
 ot_hdc_vline #(.D(LM)) u_mi(.clk(clk),.rst_n(rn),.v(sv&&sp==32'hff800000),.vd(inactive));
 wire [31:0] raw;
 wire mf;
 ot_dsrom_su_softmax_mul #(LM) u_m(clk,rn,sv,sp==32'hff800000 ? 32'd0:sp,scale,raw,mf);
 wire [31:0] scaled=inactive[LM]?32'hff800000:raw;
 wire wc=sctx[LM]^(MUT==1);
 reg [31:0] sbuf[0:2*NVMAX-1];
 reg [6:0] wcnt[0:1];reg [31:0] rmax[0:1];reg [31:0] mxlo;
 wire [31:0] maxnow=(wcnt[wc]==0 || okey(scaled)>okey(rmax[wc]))?scaled:rmax[wc];
 always @(posedge clk) if(smv[LM]) begin
  sbuf[2*wcnt[wc]+wc]<=scaled;rmax[wc]<=maxnow;
  if(wcnt[wc]+7'd1==nv) begin
   if(!wc) mxlo<=maxnow;
   else o_mx<={maxnow,mxlo};
  end
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin wcnt[0]<=0;wcnt[1]<=0;o_mxv<=0;end
  else begin
   o_mxv<=smv[LM]&&wc&&(wcnt[1]+7'd1==nv);
   if(smv[LM]) wcnt[wc]<=(wcnt[wc]+7'd1==nv)?7'd0:wcnt[wc]+7'd1;
  end
 // Read alternate logical lanes from one score word per edge. A single sink
 // event precedes lane0 of row0; only physical lane0 enables that event.
 reg [31:0] mbn,sd;
 reg [6:0] rcnt;
 reg rd_on,rctx,rv,rsink,rlast,rectx;
 always @(posedge clk) begin
  if(mv) begin mbn<=nmbp;sd<=sink;end
  else if(rd_on) sd<=sbuf[2*rcnt+rctx];
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin rd_on<=0;rcnt<=0;rctx<=0;rv<=0;rsink<=0;rlast<=0;rectx<=0;end
  else begin
   rv<=rd_on;rsink<=mv&&ske;rlast<=rd_on&&rctx&&(rcnt+7'd1==nv);rectx<=rctx;
   if(mv) begin rd_on<=1;rcnt<=0;rctx<=0;end
   else if(rd_on) begin
    rctx<=~rctx;
    if(rctx) begin rcnt<=rcnt+7'd1;if(rcnt+7'd1==nv)rd_on<=0;end
   end
  end
 wire av=rv||rsink;
 wire [DE:0] ev,el,es,ec,ei;
 ot_hdc_vline #(.D(DE)) u_ev(.clk(clk),.rst_n(rn),.v(av),.vd(ev));
 ot_hdc_vline #(.D(DE)) u_el(.clk(clk),.rst_n(rn),.v(rlast),.vd(el));
 ot_hdc_vline #(.D(DE)) u_es(.clk(clk),.rst_n(rn),.v(rsink),.vd(es));
 ot_hdc_vline #(.D(DE)) u_ec(.clk(clk),.rst_n(rn),.v(rectx),.vd(ec));
 ot_hdc_vline #(.D(DE)) u_ei(.clk(clk),.rst_n(rn),.v(rv&&sd==32'hff800000),.vd(ei));
 wire [31:0] ad,ex;wire af,ef;
 ot_dsrom_su_softmax_add #(.ADD6(0),.LA(LA)) u_a(clk,rn,av,sd,mbn,ad,af);
 ot_hdc_v41x_exp #(.LM(LM),.LA(LA)) u_e(.clk(clk),.rst_n(rn),.v(ev[LA]),.x(ad),.y(ex),.vo(),.fault(ef));
 wire [31:0] val=ei[DE]?32'd0:ex;
 reg [31:0] elo;
 always @(posedge clk) if(ev[DE])begin
  if(es[DE])o_e<={32'd0,val};
  else if(!ec[DE])elo<=val;
  else o_e<={val,elo};
 end
 always @(posedge clk or negedge rn)
  if(!rn)begin o_ev<=0;o_es<=0;o_el<=0;end
  else begin o_ev<=ev[DE]&&(es[DE]||ec[DE]);o_es<=ev[DE]&&es[DE];o_el<=ev[DE]&&el[DE];end
endmodule
