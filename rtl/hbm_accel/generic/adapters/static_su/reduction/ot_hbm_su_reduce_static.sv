// Fixed compiler-issued commands. No runtime scheduling or readiness signals.
// op0 LOAD dst<-operand; op1 ADD_EXT dst<-scratch[a]+operand;
// op2 ADD_TREE dst<-scratch[a]+scratch[b]; op3 MAX_EXT;
// op4 EXPORT scratch[a] to scalar; op5 MAX_TREE scratch[a]/scratch[b]. All commits issue+7 edges (one native SRAM read + LAT6 add).
// Two coherent native 128x256 SRAM replicas supply simultaneous A/B reads.
module ot_hbm_su_reduce_static #(parameter AW=10)(
 input wire clk,rst_n,cmd_valid,
 input wire [2:0] cmd_op,
 input wire [AW-1:0] cmd_a,cmd_b,cmd_dst,
 input wire [31:0] operand_fp32,cmd_tag,
 output reg scalar_valid, output reg [31:0] scalar_tag,scalar_fp32,
 output wire [15:0] scalar_bf16,output reg fault
);
 generate if(AW!=10) begin:g_bad_aw
  ot_hbm_su_reduce_static_requires_AW10 invalid_parameter();
 end endgenerate
 reg cv;reg [2:0] co;reg [AW-1:0] ca,cb,cd;reg[31:0] cx,ct;
 always @(posedge clk) begin
  if(!rst_n) cv<=0;else cv<=cmd_valid;
  co<=cmd_op;ca<=cmd_a;cb<=cmd_b;cd<=cmd_dst;cx<=operand_fp32;ct<=cmd_tag;
 end
 wire [255:0] qa,qb;
 wire [31:0] av=qa[ca[2:0]*32+:32];
 wire [31:0] bv=(co==2||co==5)?qb[cb[2:0]*32+:32]:cx;
 wire wr=rst_n&&pv[5]&&(po[5]<4||po[5]==5);
 wire[31:0] wd=(po[5]==1||po[5]==2)?add_y:px[5];
 wire[255:0] wm=256'hffffffff << (pd[5][2:0]*32);
 wire[255:0] wdata={224'b0,wd} << (pd[5][2:0]*32);
 ot_sram_1r1w_128x256_m1_r2c2 ma(.clk(clk),.r_ce_in(cmd_valid),.r_addr_in(cmd_a[9:3]),.rd_out(qa),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 mb(.clk(clk),.r_ce_in(cmd_valid),.r_addr_in(cmd_b[9:3]),.rd_out(qb),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 reg [5:0] pv;
 reg [2:0] po[0:5]; reg [AW-1:0] pd[0:5];
 reg [31:0] pt[0:5],px[0:5];
 wire [31:0] add_y; wire [1:0] add_err;wire add_v;
 ot_hdc_fp32_add_lat #(.LAT(6)) u_add(.clk(clk),.rst_n(rst_n),
 .valid_in(cv && (co==1 || co==2)),.a(av),.b(bv),
 .y(add_y),.err(add_err),.valid_out(add_v));
 // finite FP32 ordered compare, canonical positive zero for equal signed zeros.
 wire agt=(av[31]!=bv[31])?!av[31]:(av[31]?(av[30:0]<bv[30:0]):(av[30:0]>bv[30:0]));
 wire [31:0] raw_max=agt?av:bv;
 wire [31:0] max_y=(raw_max[30:0]==0)?32'b0:raw_max;
 wire [31:0] rounded=scalar_fp32+32'h00007fff+{31'b0,scalar_fp32[16]};
 assign scalar_bf16=(&scalar_fp32[30:23])?scalar_fp32[31:16]:rounded[31:16];
 integer i;
 always @(posedge clk) begin
  if(!rst_n) begin pv<=0;scalar_valid<=0;fault<=0; end
  else begin
   scalar_valid<=0;
   pv<={pv[4:0],cv};
   po[0]<=co;pd[0]<=cd;pt[0]<=ct;
   px[0]<=(co==0)?cx:((co==3||co==5)?max_y:av);
   for(i=1;i<6;i=i+1) begin po[i]<=po[i-1];pd[i]<=pd[i-1];pt[i]<=pt[i-1];px[i]<=px[i-1];end
   if(cmd_valid && (cmd_op>5 || ((cmd_op==0||cmd_op==1||cmd_op==3)&&(&operand_fp32[30:23])))) fault<=1;
   if(cv && ((co==3||co==5)&&((&av[30:23])||(&bv[30:23])) || co==4&&(&av[30:23]))) fault<=1;
   if(pv[5]) begin
    if(po[5]==1 || po[5]==2) begin
     if(!add_v || add_err!=0) fault<=1;
    end else if(po[5]==4) begin scalar_valid<=1;scalar_tag<=pt[5];scalar_fp32<=px[5];end
   end
  end
 end
endmodule
