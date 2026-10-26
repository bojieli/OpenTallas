`timescale 1ns/1ps
`default_nettype none
// Copy the ACTUAL proven HBM coefficient tail onto resident ROM + S81 VM.
// All sigmoid/exp/div/Sinkhorn arithmetic remains ot_hgi_hc_unit op2 unchanged.
// Four real parameter-ROM macros supply scale/base sectors on a reserved port.
// Normal execution has no ready/credit/backpressure. compiled_cycles is the
// measured compiler price for this exact implementation, not a trace duration.
// Completion fires there unconditionally; core completion is checked, not gated.
// Shared core Sinkhorn /7 step phase needs fixed worst6-edge padding. A540
// serial compiled budget covers measured534base+0..6phase, no runtime waiting.
module ot_s81_hcx_post_native #(parameter integer RL=4,WL=4,MUT_POST=0,EXTERNAL_ROM=0,parameter IMAGE="hcx_post")(
 input wire clk,rst_n,start,ffn,
 input wire [13:0] raw_base_row,coef_base_row,
 input wire [5:0] layer_idx,
 input wire [31:0] norm_eps,
 input wire [15:0] compiled_cycles,
 output reg done,
 output wire rq_v,
 output wire [13:0] rq_row,
 input wire rs_v,
 input wire [511:0] rs_d,
 output wire wq_v,
 output wire [13:0] wq_row,
 output wire [15:0] wq_mask,
 output wire [511:0] wq_d,
 input wire wq_commit,
 output reg fault,
 // Compiler-owned shared parameter/gain ROM face; no request handshake.
 output wire param_ce,
 output wire [11:0] param_addr,
 input wire [255:0] param_data
);
 wire ready,actual_done,core_fault,halted,transport_fault;
 wire [337:0]vmq;wire[273:0]vmr;
 wire hq;wire[34:0]ha;wire[2:0]hl;wire[4:0]ht;
 reg busy,pbusy,observed_done;reg[15:0]age,limit;reg[1:0]beat;reg[4:0]tag;
 reg [34:0]base;
 wire[287:0]pq;
 reg hv;reg[1:0]hb;reg[4:0]htag;
 wire[255:0]hd=EXTERNAL_ROM ? param_data : {pq[216+:64],pq[144+:64],pq[72+:64],pq[0+:64]};
 assign param_ce=pbusy;
 assign param_addr=12'(base+beat);
 wire[255:0]a=256'h100018000000000001 | (256'(raw_base_row)<<12);
 wire[255:0]b=256'h1000000000004 | (256'(8*layer_idx+4*ffn)<<13);
 wire[255:0]o=256'h18000000000001 | (256'(coef_base_row)<<12);
 ot_hgi_hc_unit #(.W(32),.RMAX(2),.PMAX(2),.MUT_POST(MUT_POST))core(
  .clk(clk),.rst_n(rst_n),.cfg_norm_eps(norm_eps),.rec_v(start),.rec_rdy(ready),
  .rec_hdr(128'ha0800002600000000000000000000000),.rec_a(a),.rec_b(b),.rec_o(o),.rec_n_a(21'd24),.rec_n_o(21'd24),
  .rec_done(actual_done),.rec_fault(core_fault),.halted(halted),.vmq(vmq),.vmr(vmr),
  .hq_v(hq),.hq_rdy(1'b1),.hq_addr(ha),.hq_len(hl),.hq_tag(ht),.hr_v(hv),.hr_tag(htag),.hr_beat(hb),.hr_data(hd),
  .rg_req(),.rg_gnt(1'b0),.wrq(),.wrq_cr(32'd0),.wrr(8224'd0),.ap_q(8896'd0),.ap_cr(),.ap_done());
 ot_s81_hcx_vm_scheduled #(.RL(RL),.WL(WL),.READ_BF16(0))transport(
  .clk(clk),.rst_n(rst_n),.job_start(start),.coef_base_row(coef_base_row),.norm_eps(norm_eps),
  .vmq(vmq),.vmr(vmr),.rq_v(rq_v),.rq_row(rq_row),.rs_v(rs_v),.rs_d(rs_d),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),.wq_commit(wq_commit),.fault(transport_fault));
 generate if(!EXTERNAL_ROM)begin:g_internal_rom
 for(genvar m=0;m<4;m=m+1)begin:g_rom
`ifndef SYNTHESIS
  ot_rom_4096x72_m8 #(.INSTANCE($sformatf("%s_p%0d",IMAGE,m)))rom(
`else
  ot_rom_4096x72_m8 rom(
`endif
   .clk(clk),.ce_in(pbusy),.addr_in(12'(base+beat)),.rd_out(pq[72*m+:72]));
 end end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;pbusy<=0;observed_done<=0;age<=0;done<=0;fault<=0;hv<=0;beat<=0;end
  else begin
   done<=0;hv<=pbusy;hb<=beat;htag<=tag;
   if(start)begin
    if(busy||!ready||compiled_cycles==0||raw_base_row[3:0]!=0||layer_idx>42)fault<=1;
    busy<=1;observed_done<=0;age<=0;limit<=compiled_cycles;
   end
   if(busy)begin
    age<=age+1'b1;
    if(age+1'b1==limit)begin done<=1;busy<=0;if(!(actual_done||observed_done))fault<=1;end
   end
   if(actual_done)begin observed_done<=1;if(!busy || age+1'b1>limit)fault<=1;end
   if(hq)begin
    if(pbusy||hl!=4||ht[4:1]!=8||ha>340 || ha[1:0]!=0)fault<=1;
    pbusy<=1;beat<=0;base<=ha;tag<=ht;
   end else if(pbusy)begin
    beat<=beat+1'b1;if(beat==3)pbusy<=0;
   end
   if(core_fault||halted||transport_fault)fault<=1;
  end
 end
endmodule
`default_nettype wire
