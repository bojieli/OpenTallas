`timescale 1ns/1ps
module tb_hgi_coll_tkm_head_seam;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg[8159:0]heads;reg[95:0]masks;reg[31:0]epochs;reg[7:0]hn;
 wire[31:0]take,cmd_epoch;wire[3:0]pop;
 integer base[0:3];reg[3:0]pop_pin;reg[31:0]epoch_pin;
 reg[1279:0]seen=0;integer checked=0,cycles=0,l,s,i,id,j;
 ot_hgi_coll_tkm_seq_lane_core #(.KMAX(64),.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.start(1'b0),
 .lane_heads(heads),.lane_masks(masks),.lane_epochs(epochs),.lane_hn(hn),.lane_take(take),.lane_pop(pop),.lane_take_epochs(cmd_epoch),
 .lane_d0v(4'b0),.lane_d1v(4'b0),.lane_dv(4'b0),.lane_permit(4'b0),.lane_fault(4'b0),.lane_fe(4'hf),.lane_ldv(4'b0),
 .lane_he(2720'b0),.lane_nv_mask(32'b0),.lane_hm(32'b0),.lane_dn(32'b0),.lane_occ(32'b0),
 .chain_up(340'b0),.chain_tau(84'b0),.chain_busy(1'b0),
 .cfg_n(12'd1),.cfg_k(13'd64),.cfg_g(8'd1),.cfg_gbase(8'd0),.cfg_pf(16'd1),.cfg_nout(13'd64),.cfg_obase(40'd0),.cfg_rbase(40'd0),.cfg_has_r(1'b0),
 .w_v(1'b0),.pack_empty(1'b1),.pack_queued(4'b0),.pack_lines(10'b0));
 always @*begin
  heads=0;masks=0;epochs=0;hn=0;
  for(integer l=0;l<4;l=l+1)begin
   epochs[8*l+:8]=base[l];hn[2*l+:2]=((40-base[l])>=3)?3:(40-base[l]);
   for(integer s=0;s<3;s=s+1)if(base[l]+s<40)begin
    masks[24*l+8*s+:8]=8'hff;
    for(integer i=0;i<8;i=i+1)begin
     heads[2040*l+680*s+85*i+:85]={1'b0,1'b1,32'hbf800000,~(32'(l*320+(base[l]+s)*8+i)),18'd0,1'b0};
    end
   end
  end
 end
 always @(posedge clk)begin
  cycles=cycles+1;
  if(rst_n)begin
   for(integer l=0;l<4;l=l+1)if(pop_pin[l]&&epoch_pin[8*l+:8]==8'(base[l]))begin
    if(base[l]>=40)$fatal(1,"HEAD_SEAM FAIL empty pop");base[l]<=base[l]+1;
   end
   pop_pin<=pop;epoch_pin<=cmd_epoch;
  end else begin pop_pin<=0;epoch_pin<=0;for(integer l=0;l<4;l=l+1)base[l]<=0;end
  if(dut.e1_v)begin
   for(integer i=0;i<4;i=i+1)if(dut.e1[i][83])begin
    id=~dut.e1[i][50:19];
    if(id>=1280||seen[id])$fatal(1,"HEAD_SEAM FAIL repeated/bad id=%0d checked=%0d",id,checked);
    seen[id]=1;checked=checked+1;
   end
  end
  if(checked==1280)begin $display("HEAD_SEAM PASS checked=%0d cycles=%0d",checked,cycles);$finish;end
  if(cycles>1500)$fatal(1,"HEAD_SEAM FAIL timeout checked=%0d",checked);
 end
 initial begin repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);force dut.ph=4'd1;end
endmodule
