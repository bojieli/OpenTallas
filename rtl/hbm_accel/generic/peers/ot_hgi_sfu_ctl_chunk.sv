`timescale 1ns/1ps
// Chronological partition of actual c12 ot_hdc_v41x_ins shift semantics.
// Independent same-edge clock roots, not asynchronous domains. Unassigned physical leaf.
module ot_hgi_sfu_ctl_chunk #(
 parameter integer W=75, OFFSET=0, STAGES=138,
 parameter integer MUT_BOUNDARY=0, PIN_CAPTURE=0, STATUS_REG=0, MUT_STALE_STATUS=0,
 // c6 (Claude group-B6 10-14, native pin audit of CLOSED 60lo c5: capture 414 ps on tail_d (60 bits written straight into
 // 138 slots) / rst_n (raw async to 289 flops), launch 251 ps on q (the 138-way slot read sat in front of q)):
 //   RDK > 1: the output is read RDK-1 stages early into rd_q and q is a pure flop -> flop copy of rd_q (q can sit at the
 //            pins).  RDK = 3 is cycle-exact (stages 1, 2 receive no inject in either chunk); RDK = 4 exports r[1] one edge
 //            EARLY (the high chunk, so the low chunk can capture its tail in pin flops without a cycle).
 //   TAIL_CAPTURE: tail_d / tail_v land in pin flops; with a high chunk at RDK = 4 the slot written is unchanged.
 //   RST_RELAY: rst_n drives only an ot_rst_relay (release 3 edges after the port; the quarter releases on one edge).
 parameter integer RDK=1, TAIL_CAPTURE=0, RST_RELAY=0
)(
 input wire clk,rst_n,v,
 input wire [2:0] sfu,
 input wire [W-1:0] d, tail_d,
 input wire tail_v,
 output wire [W-1:0] q,
 output wire vo,coll,busy
);
 function automatic integer depth(input [2:0] fn);
  case(fn)
   0:depth=0;1:depth=94;2:depth=77;3:depth=35;
   4,5:depth=122;6:depth=276;7:depth=158;
  endcase
 endfunction
 // Optional registered injection face. Insert at depth-1 after this edge, preserving original total depth.
 wire rr_n;
 generate if(RST_RELAY)begin:g_rr
  wire [0:0] rr_o;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr_o));
  assign rr_n=rr_o[0];
 end else begin:g_nrr
  assign rr_n=rst_n;
 end endgenerate
 reg [W-1:0] d_pin;
 reg [2:0] sfu_pin;
 reg v_pin;
 always @(posedge clk)begin d_pin<=d;sfu_pin<=sfu;end
 always @(posedge clk or negedge rr_n)if(!rr_n)v_pin<=1'b0;else v_pin<=v;
 wire [W-1:0] inject_d=PIN_CAPTURE?d_pin:d;
 wire [2:0] inject_fn=PIN_CAPTURE?sfu_pin:sfu;
 wire inject_v=PIN_CAPTURE?v_pin:v;
 // RING (Claude group-B3 10-14; c3 routes TT +21..+144 but FF -94..-156 ps, hold ECO missed: the 138-stage x W-bit shift
 // chain moved every bit every edge and each r[p+1] -> r[p] hop is a neighbour hold race against the leaf clock spread).
 // Timing wheel of the same chunk: stage p at time t lives in slot (h + p - 1) mod STAGES, h = t mod STAGES, so an item
 // never moves.  Inject at stage p writes slot (h + p) mod STAGES at this edge, the tail writes slot h (the slot read out
 // as r[1] this cycle; inject wins as before), and the output register loads slot (h + 1) (or the stage-1 inject).  Same
 // vo / q / coll / busy as the shift form, cycle for cycle; data is written once and read once (no flop-to-flop chain).
 localparam integer HW = $clog2(STAGES);
 reg [W-1:0] slot [0:STAGES-1];
 reg [STAGES-1:0] sv;                                 // slot valid
 reg [HW-1:0] h;
 (* keep="true" *) reg [STAGES-1:0] H;                // one-hot of h, registered
 wire [HW-1:0] h_n = (h == HW'(STAGES-1)) ? HW'(0) : h + HW'(1);
 always @(posedge clk or negedge rr_n)
  if(!rr_n)begin h<=0;H<={{(STAGES-1){1'b0}},1'b1};end
  else begin h<=h_n;for(integer s=0;s<STAGES;s++)H[s]<=h_n==HW'(s);end
 // stage of each function's inject in this chunk (constant; 0 = not in this chunk)
 function automatic integer pstage(input integer fn);
  integer dp;
  begin dp=depth(fn[2:0])-OFFSET-PIN_CAPTURE; pstage=(dp>=1&&dp<=STAGES)?dp:0; end
 endfunction
 reg [7:0] fsel;                                      // one-hot of the injecting function (v and fn decoded)
 always @* for(integer k=0;k<8;k++) fsel[k]=inject_v&&inject_fn==3'(k)&&pstage(k)!=0;
 wire in_chunk = |fsel;
 reg itail;                                           // the inject lands on stage STAGES (slot h, against the tail)
 reg inj1;                                            // the inject lands on stage 1 (straight into the output register)
 always @* begin itail=1'b0;inj1=1'b0;
  for(integer k=0;k<8;k++)begin if(pstage(k)==STAGES&&fsel[k])itail=1'b1; if(pstage(k)==1&&fsel[k])inj1=1'b1; end
 end
 wire [STAGES:1] collision;
 reg [W-1:0] tail_q; reg tail_vq;
 always @(posedge clk) tail_q <= tail_d;
 always @(posedge clk or negedge rr_n) if(!rr_n) tail_vq <= 1'b0; else tail_vq <= tail_v;
 wire [W-1:0] tail_w = TAIL_CAPTURE ? tail_q : tail_d;
 wire tail_valid = MUT_BOUNDARY ? 1'b0 : (TAIL_CAPTURE ? tail_vq : tail_v);
 reg [STAGES-1:0] ihit;                               // slot written by the inject
 always @* for(integer s=0;s<STAGES;s++)begin
  ihit[s]=1'b0;
  for(integer k=0;k<8;k++)
   if(pstage(k)!=0) if(fsel[k] && H[(s-pstage(k)+STAGES)%STAGES]) ihit[s]=1'b1;
 end
 always @(posedge clk)
  for(integer s=0;s<STAGES;s++)
   if(ihit[s])slot[s]<=inject_d; else if(H[s])slot[s]<=tail_w;
 always @(posedge clk or negedge rr_n)
  if(!rr_n)sv<=0;
  else for(integer s=0;s<STAGES;s++) sv[s] <= ihit[s] || (H[s] ? tail_valid : sv[s]);
 // output register = r[1] of the shift form
 reg [W-1:0] q_r; reg vo_r;
 reg [W-1:0] rd; reg rdv;
 always @* begin
  rd='0;rdv=1'b0;
  for(integer s=0;s<STAGES;s++)if(H[(s-1+STAGES)%STAGES])begin rd=rd|slot[s];rdv=rdv|sv[s];end
 end
 generate if(RDK>1)begin:g_rdk
  // stage RDK lives in slot (h + RDK - 1): rd_q(t+1) = r[RDK](t) = r[1](t + RDK - 1); q(t+2) = r[1](t + RDK - 1)
  reg [W-1:0] rk, rd_q; reg rkv, rdv_q;
  always @* begin
   rk='0;rkv=1'b0;
   for(integer s=0;s<STAGES;s++)if(H[(s-(RDK-1)+STAGES)%STAGES])begin rk=rk|slot[s];rkv=rkv|sv[s];end
  end
  always @(posedge clk) begin rd_q <= rk; q_r <= rd_q; end
  always @(posedge clk or negedge rr_n) if(!rr_n)begin rdv_q<=1'b0;vo_r<=1'b0;end else begin rdv_q<=rkv;vo_r<=rdv_q;end
 end else begin:g_rd1
  always @(posedge clk) q_r <= inj1 ? inject_d : rd;
  always @(posedge clk or negedge rr_n) if(!rr_n)vo_r<=1'b0; else vo_r<=inj1||rdv;
 end endgenerate
 // collision (the shift form's collision[p] = inject at p meets an occupied stage p+1, the tail for p == STAGES); only
 // its OR is observed (coll), so it is carried as one bit in collision[1].
 wire coll_any = itail ? tail_valid : |(ihit & sv & ~H);
 assign collision = {{(STAGES-1){1'b0}}, coll_any};
 wire [STAGES:1] rv = sv;                             // occupancy of all stages = all slots
 assign q=q_r;assign vo=vo_r;
 // Data/valid pins are registered. coll/busy are status reductions: registered relay stillrequired physically.
 generate if(STATUS_REG==2)begin:g_local_status_terms
  // These snapshots are payload. Reset only the validity fence and outputs;
  // the first post-reset snapshot replaces stale state before observation.
  reg [STAGES:1] collision_q,occupancy_q;
  reg c,b,front_q,known_q;
  always @(posedge clk)begin
   collision_q<=collision;occupancy_q<=rv;
   front_q<=PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0;
  end
  always @(posedge clk or negedge rr_n)
   if(!rr_n)begin known_q<=0;c<=0;b<=0;end
   else begin known_q<=1;c<=(MUT_STALE_STATUS||known_q)&&(|collision_q);b<=(MUT_STALE_STATUS||known_q)&&((|occupancy_q)||front_q);end
  assign coll=c;assign busy=b;
 end else if(STATUS_REG==1)begin:g_registered_status
  reg c,b;
  always @(posedge clk or negedge rr_n)
   if(!rr_n)begin c<=1'b0;b<=1'b0;end
   else begin c<=|collision;b<=(|rv)||(PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0);end
  assign coll=c;assign busy=b;
 end else begin:g_legacy_status
  assign coll=|collision;assign busy=(|rv)||(PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0);
 end endgenerate
 initial for(integer k=0;k<8;k++) if(RDK>1 && pstage(k)!=0 && pstage(k)<RDK)
  $fatal(1,"SFU chunk RDK=%0d: an inject lands in stage %0d < RDK",RDK,pstage(k));
 initial if((W!=75&&W!=60)||STAGES!=138||(OFFSET!=0&&OFFSET!=138))
  $fatal(1,"SFU chronological chunk requires75/60bit x138stage exact partitions");
endmodule
