`timescale 1ns/1ps
module tb_hgi_coll_tkm_head_seam;
 parameter MUT=0,MASKED=0,BLOCKS=40;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg[10879:0]heads;reg[127:0]masks;reg[31:0]epochs;reg[11:0]hn;
 wire[31:0]take,cmd_epoch;wire[3:0]pop;
 function automatic[7:0]mask_for(input integer lane,input integer block_);
  mask_for=MASKED?8'(block_*37+lane*11):8'hff;
 endfunction
 function automatic[84:0]entry_for(input integer id_);
  entry_for={1'b0,1'b1,(32'hbf800000^32'(id_*13)),~32'(id_),18'(id_*17),1'(id_%7==0)};
 endfunction
 integer expected_count=0;
 integer base[0:3];reg[3:0]pop_pin;reg[31:0]epoch_pin;
 reg[4*BLOCKS*8-1:0]seen=0;integer checked=0,cycles=0,l,s,i,id,j;
 ot_hgi_coll_tkm_seq_lane_core #(.KMAX(64),.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.start(1'b0),
 .lane_heads0(heads[0+:2720]),.lane_masks0(masks[0+:32]),.lane_epoch0(epochs[0+:8]),.lane_hn0(hn[0+:3]),.lane_heads1(heads[2720+:2720]),.lane_masks1(masks[32+:32]),.lane_epoch1(epochs[8+:8]),.lane_hn1(hn[3+:3]),.lane_heads2(heads[5440+:2720]),.lane_masks2(masks[64+:32]),.lane_epoch2(epochs[16+:8]),.lane_hn2(hn[6+:3]),.lane_heads3(heads[8160+:2720]),.lane_masks3(masks[96+:32]),.lane_epoch3(epochs[24+:8]),.lane_hn3(hn[9+:3]),.lane_take(take),.lane_pop(pop),.lane_take_epochs(cmd_epoch),
 .lane_d0v(4'b0),.lane_d1v(4'b0),.lane_dv(4'b0),.lane_fault(4'b0),.lane_ldv(4'b0),
 .lane_nv_mask(32'b0),.lane_occ(32'b0),
 .chain_up(340'b0),.chain_tau(84'b0),.chain_busy(1'b0),
 .cfg_n(12'd1),.cfg_k(13'd64),.cfg_g(8'd1),.cfg_gbase(8'd0),.cfg_pf(16'd1),.cfg_nout(13'd64),.cfg_obase(40'd0),.cfg_rbase(40'd0),.cfg_has_r(1'b0),
 .buf_rd_v(1'b0),.buf_rd_data(340'b0),.w_v(1'b0),.pack_empty(1'b1),.pack_queued(4'b0),.pack_lines(10'b0));
 always @*begin
  heads=0;masks=0;epochs=0;hn=0;
  for(integer l=0;l<4;l=l+1)begin
   epochs[8*l+:8]=base[l];hn[3*l+:3]=((BLOCKS-base[l])>=5)?5:(BLOCKS-base[l]);
   for(integer s=0;s<4;s=s+1)if(base[l]+s<BLOCKS)begin
    masks[32*l+8*s+:8]=mask_for(l,base[l]+s);
    for(integer i=0;i<8;i=i+1)begin
     heads[2720*l+680*s+85*i+:85]=entry_for(l*BLOCKS*8+(base[l]+s)*8+i);
    end
   end
  end
 end
 always @(posedge clk)begin
  cycles=cycles+1;
  if(rst_n)begin
   for(integer l=0;l<4;l=l+1)if(pop_pin[l]&&epoch_pin[8*l+:8]==8'(base[l]))begin
    if(base[l]>=BLOCKS)$fatal(1,"HEAD_SEAM FAIL empty pop");base[l]<=base[l]+1;
   end
   pop_pin<=pop;epoch_pin<=cmd_epoch;
  end else begin pop_pin<=0;epoch_pin<=0;for(integer l=0;l<4;l=l+1)base[l]<=0;end
  if(dut.e1_v)begin
   for(integer i=0;i<4;i=i+1)if(dut.e1[i][83])begin
    id=~dut.e1[i][50:19];
    if(id>=4*BLOCKS*8||seen[id])$fatal(1,"HEAD_SEAM FAIL repeated/bad id=%0d checked=%0d",id,checked);
    if(((mask_for(id/(BLOCKS*8),(id%(BLOCKS*8))/8)>>(id%8))&1)==0)$fatal(1,"HEAD_SEAM FAIL masked id");
    if(dut.e1[i]!==entry_for(id))$fatal(1,"HEAD_SEAM FAIL full85 data id=%0d",id);
    seen[id]=1;checked=checked+1;
   end
  end
  if(checked==expected_count)begin $display("HEAD_SEAM PASS checked=%0d cycles=%0d",checked,cycles);$finish;end
  if(cycles>BLOCKS*20+100)$fatal(1,"HEAD_SEAM FAIL timeout checked=%0d",checked);
 end
 initial begin
  for(integer l=0;l<4;l=l+1)for(integer b=0;b<BLOCKS;b=b+1)for(integer i=0;i<8;i=i+1)
   expected_count=expected_count+((mask_for(l,b)>>i)&1);
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);force dut.ph=4'd1;end
endmodule
