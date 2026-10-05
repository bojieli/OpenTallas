`timescale 1ns/1ps
`default_nettype none
module tb;
reg fast_clk=1,slow_clk=1;
always #3 fast_clk=~fast_clk;
always #4 slow_clk=~slow_clk;
reg cold_n=0,rst_n=0,slow_rst_n=0,abort_fast=0,abort_slow=0;
reg launch=0;wire credit;
reg [255:0] xwe=0;reg [7679:0] addr=0;reg [8191:0] data=0;
wire [3:0] mv,mwe,mready,done;wire [111:0] ma;
wire [1023:0] md;wire [127:0] strb;wire debt,quarantine,fault;
reg release_completion=0;reg full_same_stack=0;integer accepts=0,completes=0,visible=0;
ot_ds_su_kv_related_visible #(.ENABLE(1),.SUN(256),.AW(30)) dut(
.clk(fast_clk),.slow_clk(slow_clk),.cold_n(cold_n),.rst_n(rst_n),.slow_rst_n(slow_rst_n),
.abort_fast(abort_fast),.abort_slow(abort_slow),.src_launch(launch),.src_launch_credit(credit),
.src_xwe(xwe),.src_xwaddr(addr),.src_xwdata(data),.m_wr_done(done),
.base(30'd0),.kvd_v(1'b0),.kvd_wbase(30'd0),.kvd_ts(30'd0),.kvd_ks(30'd0),.kvd_js(30'd0),
.kvd_tiles(16'd0),.kvd_k(16'd0),.kvd_hg(2'd0),.re(1'b0),.raddr(120'd0),
.we(8'd0),.waddr(240'd0),.wdata(256'd0),.m_v(mv),.m_rdy(mready),.m_addr(ma),.m_we(mwe),
.m_wdata(md),.m_wstrb(strb),.s_v(4'd0),.s_tag(64'd0),.s_beat(16'd0),.s_data(1024'd0),
.owner_debt(debt),.owner_quarantined(quarantine),.fault(fault));
// Bounded diagnostic backend only: eight actual SRAM macros, one command per
// stack. Physical write precedes readback and an independently held completion.
// This fixture provides no HBM service, physical timing or protection credit.
genvar s,h;
generate for(s=0;s<4;s=s+1)begin: backend
 reg [2:0] state=0;reg [255:0] captured=0;reg [31:0] mask=0;reg [8:0] a=0;
 wire [255:0] q;
 assign mready[s]=(state==0)&&cold_n;
 assign done[s]=(state==3)&&release_completion;
 for(h=0;h<2;h=h+1)begin: half
  wire [127:0] bitmask;
  for(genvar b=0;b<128;b=b+1)begin: bm
    assign bitmask[b]=mask[h*16+b/8];
  end
  ot_sram_1r1w_512x128_m4_r2c2 mem(.clk(fast_clk),.r_ce_in(state==2),.r_addr_in(a),
    .rd_out(q[h*128+:128]),.w_ce_in(state==1),.w_addr_in(a),
    .wd_in(captured[h*128+:128]),.w_mask_in(bitmask),.rr_en(2'b0),.rr_addr(14'b0),
    .cr_en(2'b0),.cr_sel(14'b0));
 end
 always @(posedge fast_clk)begin
  if(!cold_n)state<=0;
  else case(state)
   0:if(mv[s]&&mwe[s]&&mready[s])begin
     if(!full_same_stack && ma[s*28+:28] != (1<<18))$fatal(1,"wrong sector");
     if(full_same_stack && (s!=0 || ma[s*28+:28] < (1<<18) || ma[s*28+:28] >= (1<<18)+512 || ma[s*28]))$fatal(1,"bad same-stack sector");
     if(md[s*256+:32] !== (32'h3f800000+(full_same_stack ? ((ma[s*28+:28]-(1<<18))/2) : s)))$fatal(1,"producer address/data mismatch");
     captured<=md[s*256+:256];mask<=strb[s*32+:32];a<=9'(ma[s*28+:28]-(1<<18));state<=1;
   end
   1:state<=2;
   2:state<=3;
   3:begin
     if(q[31:0] !== (32'h3f800000+(full_same_stack ? a/2 : s)))$fatal(1,"actual SRAM visibility/data mismatch");
     if(release_completion)state<=0;
   end
   default:$fatal(1,"backend state");
  endcase
 end
end endgenerate
always @(posedge fast_clk)if(cold_n)begin
 accepts<=accepts+$countones(mv&mwe&mready);
 completes<=completes+$countones(done);
end
task issue;
 integer i;
 begin
 wait(credit);@(negedge slow_clk);launch=1;
 @(negedge slow_clk);launch=0;
 for(i=0;i<256;i=i+1)begin addr[i*30+:30]=full_same_stack ? i*64 : i*16;data[i*32+:32]=32'h3f800000+i;end
 xwe=full_same_stack ? {256{1'b1}} : 256'hf;@(negedge slow_clk);xwe=0;
 end
endtask
initial begin
 repeat(4)@(negedge slow_clk);cold_n=1;rst_n=1;slow_rst_n=1;
 issue();wait(accepts==4);repeat(300)@(negedge fast_clk);
 if(!debt||credit||fault||completes!=0)$fatal(1,"grant retired before visible completion");
 release_completion=1;wait(completes==4);wait(!debt);wait(credit);
 if(fault||quarantine)$fatal(1,"clean visible retirement failed");
 release_completion=0;full_same_stack=1;issue();
 wait(dut.native_KV.wq_n[0]==128);repeat(200)@(negedge fast_clk);
 if(fault||!debt||credit||accepts!=5||completes!=4)$fatal(1,"full queue failed finite backpressure");
 release_completion=1;wait(completes==260);wait(!debt);wait(credit);
 if(fault||quarantine)$fatal(1,"full same-stack burst retirement failed");
 full_same_stack=0;release_completion=0;issue();wait(accepts==264);repeat(5)@(negedge fast_clk);
 abort_fast=1;abort_slow=1;rst_n=0;slow_rst_n=0;
 repeat(8)@(negedge slow_clk);rst_n=1;slow_rst_n=1;abort_fast=0;abort_slow=0;
 repeat(20)@(negedge slow_clk);
 if(!debt||!quarantine||credit)$fatal(1,"warm reset erased accepted work");
 $display("PASS SU_KV_VISIBLE cases=3 SUN=256 macros=8 writes=260 grant_not_retirement=1 WQD128_backpressure=1 reset_debt_preserved=1");$finish;
end
initial begin repeat(6000)@(posedge fast_clk);$fatal(1,"directed event bound");end
endmodule
`default_nettype wire
