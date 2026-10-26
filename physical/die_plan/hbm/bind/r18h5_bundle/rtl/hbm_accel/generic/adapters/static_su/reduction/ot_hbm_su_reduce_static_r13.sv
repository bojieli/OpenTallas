// r13 (HBM-QCORE9 2026-10-20): copy of r12 with module suffix _r13 and the adder = Codex FP6 ot_hdc_fp32_add_n32 (LAT 6 DRST 0, bit-exact).
// HBM-QCORE8 2026-10-20 r12: as r10, plus the SRAM write: data replicated to all 8 words, word chosen by the bit mask from
// two kept per-SRAM copies of pd[5][2:0] (r10/r11 census: each pd one-hot drove 32 mask + 32 data pins on both SRAMs = 96).
// HBM-QCORE8 2026-10-20 r10 (copy of Codex r32): stage-5 write-data
// select (po[5]==1||2, r9 actual 35 loads) carried as 2 kept per-half copies; function / edges unchanged.
// Fixed compiler-issued commands. No runtime scheduling or readiness signals.
// op0 LOAD dst<-operand; op1 ADD_EXT dst<-scratch[a]+operand;
// op2 ADD_TREE dst<-scratch[a]+scratch[b]; op3 MAX_EXT;
// op4 EXPORT scratch[a] to scalar; op5 MAX_TREE scratch[a]/scratch[b].
// All commits and scalar outputs issue+9 edges: command sampled at issue, native SRAM read, ONE registered operand stage
// (r1, H-ELEM-B 10-15: the r0 SRAM clk->Q -> word select -> adder/compare path missed TT setup by 90.8 ps at 833 ps), LAT6
// add. Same-address dependent issue distance 10 (was 9); independent issue interval 1. Arithmetic, operand order and the
// compiler's reduction tree are unchanged (bit-exact), only the fixed latency grows by one edge.
// Two coherent native 128x256 SRAM replicas supply simultaneous A/B reads. scalar_bf16 is registered with scalar_fp32.
module ot_hbm_su_reduce_static_r13 #(parameter AW=10)(
 input wire clk,rst_n,cmd_valid,
 input wire [2:0] cmd_op,
 input wire [AW-1:0] cmd_a,cmd_b,cmd_dst,
 input wire [31:0] operand_fp32,cmd_tag,
 output reg scalar_valid, output reg [31:0] scalar_tag,scalar_fp32,
 output reg [15:0] scalar_bf16,output reg fault
);
 // r3 ingress: pin-register every command before decode and SRAM fanout.
 // Reset reaches one distribution register, never the arithmetic/tag enable cone.
 // A reset pulse must span a rising edge; the local reset is delayed one edge.
 reg rst_local;
 reg iv; reg [2:0] iop; reg [AW-1:0] ia,ib,idst; reg [31:0] ix,itag;
 always @(posedge clk) begin
  rst_local <= rst_n;
  iv <= rst_n && cmd_valid;
  iop <= cmd_op; ia <= cmd_a; ib <= cmd_b; idst <= cmd_dst;
  ix <= operand_fp32; itag <= cmd_tag;
 end
 generate if(AW!=10) begin:g_bad_aw
  ot_hbm_su_reduce_static_requires_AW10 invalid_parameter();
 end endgenerate
 // stage C: the registered command, sampled with the SRAM read
 reg cv;reg [2:0] co;reg [AW-1:0] ca,cb,cd;reg[31:0] cx,ct;
 always @(posedge clk) begin
  if(!rst_local) cv<=0;else cv<=iv;
  co<=iop;ca<=ia;cb<=ib;cd<=idst;cx<=ix;ct<=itag;
 end
 // Same stageC edge as ca/cb; explicit onehotword select avoids a256-load binary mux select.
 (* keep = 1 *) reg [7:0] cw_a[0:1],cw_b[0:1];
 for(genvar h=0;h<2;h=h+1)begin:g_word_capture
  for(genvar n=0;n<8;n=n+1)begin:g_word
   always @(posedge clk) begin cw_a[h][n]<=(ia[2:0]==3'(n));cw_b[h][n]<=(ib[2:0]==3'(n));end
  end
 end
 wire [255:0] qa,qb;wire[31:0] qa_word,qb_word;
 for(genvar h=0;h<2;h=h+1)begin:g_word_select
  reg[15:0] aa,bb;integer n;
  always @*begin aa=0;bb=0;for(n=0;n<8;n=n+1)begin aa=aa|({16{cw_a[h][n]}}&qa[n*32+h*16+:16]);bb=bb|({16{cw_b[h][n]}}&qb[n*32+h*16+:16]);end end
  assign qa_word[h*16+:16]=aa;assign qb_word[h*16+:16]=bb;
 end
 // stage S: selected SRAM words registered (the added physical stage)
 reg sv;reg [2:0] so;reg [AW-1:0] sd;reg [31:0] sx,st,av,bv;
 always @(posedge clk) begin
  if(!rst_local) sv<=0;else sv<=cv;
  so<=co;sd<=cd;sx<=cx;st<=ct;
  av<=qa_word;
  bv<=(co==2||co==5)?qb_word:cx;
 end
 reg [5:0] pv;
 reg [2:0] po[0:5]; reg [AW-1:0] pd[0:5];
 reg [31:0] pt[0:5],px[0:5]; wire [31:0] px0_d;
 wire [31:0] add_y; wire [1:0] add_err;wire add_v;
 wire wr=rst_local&&pv[5]&&(po[5]<4||po[5]==5);
 wire [1:0] wsel;                                  // r10: po[5]==1||po[5]==2, kept per 16-bit half
 for(genvar h=0;h<2;h=h+1)begin:g_wsel
  ot_hbm_su_reduce_r13_pipe6 u_p(.clk(clk),.d(so==1||so==2),.q(wsel[h]));
 end
 wire[31:0] wd={wsel[1]?add_y[31:16]:px[5][31:16],wsel[0]?add_y[15:0]:px[5][15:0]};
 wire [2:0] pdw [0:1];                                // r12: pd[5][2:0] as 2 kept 6-stage copies (one per SRAM)
 for(genvar m=0;m<2;m=m+1)begin:g_pdw
  ot_hbm_su_reduce_r13_pd6 u_p(.clk(clk),.d(sd[2:0]),.q(pdw[m]));
 end
 wire[255:0] wm_a=256'hffffffff << (pdw[0]*32);
 wire[255:0] wm_b=256'hffffffff << (pdw[1]*32);
 wire[255:0] wdata={8{wd}};
 ot_sram_1r1w_128x256_m1_r2c2 ma(.clk(clk),.r_ce_in(iv),.r_addr_in(ia[9:3]),.rd_out(qa),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm_a),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 mb(.clk(clk),.r_ce_in(iv),.r_addr_in(ib[9:3]),.rd_out(qb),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm_b),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 // r13b: the adder's reset is its own kept copy of rst_local (same D, same edge)
 wire rst_add;
 ot_hbm_su_reduce_r13_rcp u_rcp(.clk(clk),.d(rst_n),.q(rst_add));
 ot_hdc_fp32_add_n32 #(.LAT(6),.DRST(0)) u_add(.clk(clk),.rst_n(rst_add),
 .valid_in(sv && (so==1 || so==2)),.a(av),.b(bv),
 .y(add_y),.err(add_err),.valid_out(add_v));
 // finite FP32 ordered compare, canonical positive zero for equal signed zeros.
 // r13b: max select in 2 kept 16-bit halves, each with its own compare and the zero test as agt?az:bz (r13b census:
 // the shared compare = the adder's u_cmp carry after ABC, 39 loads)
 wire [31:0] max_y;
 for(genvar h=0;h<2;h=h+1)begin:g_max
  ot_hbm_su_reduce_r13_max16 #(.H(h)) u_m(.a(av),.b(bv),.y(max_y[h*16+:16]));
 end
 wire [31:0] ex=px[5];
 wire [31:0] rounded=ex+32'h00007fff+{31'b0,ex[16]};
 wire [15:0] ex_bf16=(&ex[30:23])?ex[31:16]:rounded[31:16];
 integer i;
 // r4: datapath/register identity may be arbitrary until its reset-valid bit arrives.
 // Reset only valid/control state; tags, addresses and arithmetic data clock freely.
 // This removes the 1,263-load r3 reset/enable cone without changing command latency.
 always @(posedge clk) begin
   po[0]<=so;pd[0]<=sd;pt[0]<=st;px[0]<=px0_d;
   for(i=1;i<6;i=i+1) begin po[i]<=po[i-1];pd[i]<=pd[i-1];pt[i]<=pt[i-1];px[i]<=px[i-1];end
 end
 always @(posedge clk) begin
  if(!rst_local) begin pv<=0;scalar_valid<=0;fault<=0; end
  else begin
   scalar_valid<=0;
   pv<={pv[4:0],sv};
   if(iv && (iop>5 || ((iop==0||iop==1||iop==3)&&(&ix[30:23])))) fault<=1;
   if(sv && ((so==3||so==5)&&((&av[30:23])||(&bv[30:23])) || so==4&&(&av[30:23]))) fault<=1;
   if(pv[5]) begin
    if(po[5]==1 || po[5]==2) begin
     if(!add_v || add_err!=0) fault<=1;
    end else if(po[5]==4) scalar_valid<=1;
   end
  end
 end
 // r13: scalar data enables from 5 kept copies of the export decision (r13a census: rst_local&&pv[5]&&po[5]==4 = 129
 // loads). exq copy == rst_local&&pv[5]&&po[5]==4 exactly: rst_local(t)=rst_n(t-1), pv[5](t)=rst_local(t-1)&&pv[4](t-1),
 // po[5](t)=po[4](t-1); data are unreset as before.
 wire [4:0] exq;
 for(genvar k=0;k<5;k=k+1)begin:g_exq
  ot_hbm_su_reduce_r13_exq u_e(.clk(clk),.d(rst_n&&rst_local&&pv[4]&&po[4]==3'd4),.q(exq[k]));
 end
 always @(posedge clk) begin
  if(exq[0]) scalar_tag[15:0]<=pt[5][15:0];
  if(exq[1]) scalar_tag[31:16]<=pt[5][31:16];
  if(exq[2]) scalar_fp32[15:0]<=ex[15:0];
  if(exq[3]) scalar_fp32[31:16]<=ex[31:16];
  if(exq[4]) scalar_bf16<=ex_bf16;
 end
 // r13: stage-P0 operand select from 4 kept per-byte one-hot copies registered with so (r13a census: so decode 63 loads)
 wire [1:0] psel [0:3];
 for(genvar k=0;k<4;k=k+1)begin:g_psel
  ot_hbm_su_reduce_r13_k2 u_s(.clk(clk),.d({co==3'd3||co==3'd5,co==3'd0}),.q(psel[k]));
  assign px0_d[k*8+:8]=psel[k][0]?sx[k*8+:8]:(psel[k][1]?max_y[k*8+:8]:av[k*8+:8]);
 end
endmodule

(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_pipe6(input wire clk, input wire d, (* keep = 1 *) output wire q);
 reg [5:0] p; always @(posedge clk) p<={p[4:0],d}; assign q=p[5];
endmodule

(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_pd6(input wire clk, input wire [2:0] d, (* keep = 1 *) output wire [2:0] q);
 reg [2:0] p [0:5]; integer i;
 always @(posedge clk) begin p[0]<=d; for(i=1;i<6;i=i+1) p[i]<=p[i-1]; end
 assign q=p[5];
endmodule

(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_exq(input wire clk, d, (* keep = 1 *) output reg q);
 always @(posedge clk) q<=d;
endmodule

(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_rcp(input wire clk, d, (* keep = 1 *) output reg q);
 always @(posedge clk) q<=d;
endmodule

// finite FP32 ordered compare, canonical positive zero for equal signed zeros; half H of the selected word
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_max16 #(parameter integer H=0)(input wire [31:0] a, b, output wire [15:0] y);
 wire agt=(a[31]!=b[31])?!a[31]:(a[31]?(a[30:0]<b[30:0]):(a[30:0]>b[30:0]));
 wire az=(a[30:0]==0), bz=(b[30:0]==0);
 wire [15:0] raw=agt?a[H*16+:16]:b[H*16+:16];
 assign y=(agt?az:bz)?16'b0:raw;
endmodule

(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_k2(input wire clk, input wire [1:0] d, (* keep = 1 *) output reg [1:0] q);
 always @(posedge clk) q<=d;
endmodule
