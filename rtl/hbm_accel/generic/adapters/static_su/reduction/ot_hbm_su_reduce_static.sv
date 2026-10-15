// Fixed compiler-issued commands. No runtime scheduling or readiness signals.
// op0 LOAD dst<-operand; op1 ADD_EXT dst<-scratch[a]+operand;
// op2 ADD_TREE dst<-scratch[a]+scratch[b]; op3 MAX_EXT;
// op4 EXPORT scratch[a] to scalar; op5 MAX_TREE scratch[a]/scratch[b].
// All commits and scalar outputs issue+9 edges: command pin ingress, native SRAM read, registered operand stage
// (r1, H-ELEM-B 10-15: the r0 SRAM clk->Q -> word select -> adder/compare path missed TT setup by 90.8 ps at 833 ps), LAT6
// add. Same-address dependent issue distance 10 (was 9); independent issue interval 1. Arithmetic, operand order and the
// compiler's reduction tree are unchanged (bit-exact), only the fixed latency grows by one edge.
// Two coherent native 128x256 SRAM replicas supply simultaneous A/B reads. scalar_bf16 is registered with scalar_fp32.
module ot_hbm_su_reduce_static #(parameter AW=10)(
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
 wire [255:0] qa,qb;
 // stage S: selected SRAM words registered (the added physical stage)
 reg sv;reg [2:0] so;reg [AW-1:0] sd;reg [31:0] sx,st,av,bv;
 always @(posedge clk) begin
  if(!rst_local) sv<=0;else sv<=cv;
  so<=co;sd<=cd;sx<=cx;st<=ct;
  av<=qa[ca[2:0]*32+:32];
  bv<=(co==2||co==5)?qb[cb[2:0]*32+:32]:cx;
 end
 reg [5:0] pv;
 reg [2:0] po[0:5]; reg [AW-1:0] pd[0:5];
 reg [31:0] pt[0:5],px[0:5];
 wire [31:0] add_y; wire [1:0] add_err;wire add_v;
 wire wr=rst_local&&pv[5]&&(po[5]<4||po[5]==5);
 wire[31:0] wd=(po[5]==1||po[5]==2)?add_y:px[5];
 wire[255:0] wm=256'hffffffff << (pd[5][2:0]*32);
 wire[255:0] wdata={224'b0,wd} << (pd[5][2:0]*32);
 ot_sram_1r1w_128x256_m1_r2c2 ma(.clk(clk),.r_ce_in(iv),.r_addr_in(ia[9:3]),.rd_out(qa),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 mb(.clk(clk),.r_ce_in(iv),.r_addr_in(ib[9:3]),.rd_out(qb),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_hdc_fp32_add_lat #(.LAT(6)) u_add(.clk(clk),.rst_n(rst_local),
 .valid_in(sv && (so==1 || so==2)),.a(av),.b(bv),
 .y(add_y),.err(add_err),.valid_out(add_v));
 // finite FP32 ordered compare, canonical positive zero for equal signed zeros.
 wire agt=(av[31]!=bv[31])?!av[31]:(av[31]?(av[30:0]<bv[30:0]):(av[30:0]>bv[30:0]));
 wire [31:0] raw_max=agt?av:bv;
 wire [31:0] max_y=(raw_max[30:0]==0)?32'b0:raw_max;
 wire [31:0] ex=px[5];
 wire [31:0] rounded=ex+32'h00007fff+{31'b0,ex[16]};
 wire [15:0] ex_bf16=(&ex[30:23])?ex[31:16]:rounded[31:16];
 integer i;
 always @(posedge clk) begin
  if(!rst_local) begin pv<=0;scalar_valid<=0;fault<=0; end
  else begin
   scalar_valid<=0;
   pv<={pv[4:0],sv};
   po[0]<=so;pd[0]<=sd;pt[0]<=st;
   px[0]<=(so==0)?sx:((so==3||so==5)?max_y:av);
   for(i=1;i<6;i=i+1) begin po[i]<=po[i-1];pd[i]<=pd[i-1];pt[i]<=pt[i-1];px[i]<=px[i-1];end
   if(iv && (iop>5 || ((iop==0||iop==1||iop==3)&&(&ix[30:23])))) fault<=1;
   if(sv && ((so==3||so==5)&&((&av[30:23])||(&bv[30:23])) || so==4&&(&av[30:23]))) fault<=1;
   if(pv[5]) begin
    if(po[5]==1 || po[5]==2) begin
     if(!add_v || add_err!=0) fault<=1;
    end else if(po[5]==4) begin scalar_valid<=1;scalar_tag<=pt[5];scalar_fp32<=ex;scalar_bf16<=ex_bf16;end
   end
  end
 end
endmodule
