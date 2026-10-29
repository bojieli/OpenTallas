`timescale 1ps/1fs
module tb_key_epoch;
 reg clk=0;always #416.5 clk=~clk;
 reg rst=0;wire cpv;wire[7:0]cpbase,cparg;wire[8:0]cpcount;
 reg descv=0,launch=0;reg[11:0]dbase=0;reg[12:0]dlimit=0;reg[15:0]loops=0;wire tf;
 ot_static_run_target #(.AWA(11),.AWB(8),.RBW(8),.RCW(9),.NA(2),.NF(1),.TGT_PIN(1),.RSYNC(1)) target(
 .clk(clk),.rst_n(rst),.tgt(8'd80),.cfg_v(1'b0),.cfg_target(8'd80),.cfg_addr(12'd0),.cfg_data(256'd0),
 .desc_v(descv),.desc_base(dbase),.desc_limit(dlimit),.desc_loops(loops),.launch_v(launch),
 .tgt_active(2'd0),.tgt_fault(1'b0),.a_we(),.a_addr(),.a_data(),.b_we(),.b_addr(),.b_data(),
 .run_v(cpv),.run_base(cpbase),.run_count(cpcount),.run_arg(cparg),.configured(),.fault(tf),.active());
 reg[3:0]iv=0;reg[7:0]rows[0:3];reg[1098:0]packets[0:3];reg cohort=0;
 wire[1111:0]rail[0:3];wire[3:0]nf;
 ot_hnx_idxn_key_prefill_source #(.KEY_BASE(16),.KEY_COUNT(6),.KEY_ARG_MASK(8'hf0),.KEY_ARG_VALUE(8'h10)) src(
 .clk(clk),.rst_n(rst),.cp_run_v(cpv),.cp_run_base(cpbase),.cp_run_count(cpcount),.cp_run_arg(cparg),
 .service_running(1'b0),.program_active(1'b0),.inject_v(iv[0]),.physical_lane(3'd0),.row(rows[0]),.cohort(cohort),.packet(packets[0]),.rail(rail[0]),.fault(nf[0]));
 for(genvar p=1;p<4;p++)begin:g
  ot_hnx_idxn_key_serial_merge node(clk,rst,rail[p-1],iv[p],3'(p),rows[p],cohort,packets[p],rail[p],nf[p]);
 end
 integer mut=0,epoch=0,clear_count=0,checks=0;
 wire second_ctrl=rail[3][1111]&&rail[3][1109:1102]==8'hff&&rail[3][31:16]==16'd2;
 wire[1111:0]rxrail=(mut==1&&second_ctrl)?1112'd0:(mut==3&&second_ctrl)?{rail[3][1111:32],16'd1,rail[3][15:0]}:rail[3];
 wire[1:0]clear,dv,cc,rf;wire[2:0]lane[0:1];wire[7:0]idx[0:1];wire[1098:0]line[0:1];
 wire[1:0]loaded,bf;wire[4395:0]out[0:1];reg pre=0,replay=0;reg[7:0]address=0;
 for(genvar c=0;c<2;c++)begin:b
  wire[1111:0]local_rail=(mut==2&&second_ctrl&&c==1)?1112'd0:rxrail;
  ot_hnx_idxn_key_prefill_receiver rx(clk,rst,local_rail,clear[c],dv[c],cc[c],lane[c],idx[c],line[c],rf[c]);
  ot_hnx_idxn_keybuf_serial_np4 kb(.clk(clk),.rst_n(rst),.clear(clear[c]),.strap_lane_base(3'd0),
   .ingest_v(dv[c]&&cc[c]==1'(c)),.ingest_lane(lane[c][1:0]),.ingest_index(idx[c]),.ingest_line(line[c]),
   .pre_v(pre),.pre_index(address),.replay_v(replay),.replay_index(address),.key_out(out[c]),.fault(bf[c]),.loaded(loaded[c]));
 end
 function automatic[1098:0]value(input integer row_,input integer lane_,input integer e,input integer c);
  reg[1098:0]v;reg[31:0]x;
  begin
   x=32'hf31a91e1^(32'(row_)*32'h01010101)^(32'(lane_)*32'h71e315d7)^(32'(e*2+c)*32'h91f3a517);v=0;
   for(integer j=0;j<1088;j+=32)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);v[11+j+:32]=x;end
   v[10:1]=10'(lane_*128+row_);v[0]=1;return v;
  end
 endfunction
 always @(posedge clk)begin
  if(clear[0])clear_count<=clear_count+1;
  #1;
  if(rst&&(tf||(|rf)||(|nf)||(|bf)))begin
   if(mut!=0&&epoch==2)begin $display("KEY_EPOCH_CONTROL_CAUGHT mut=%0d secondINDEX=1",mut);$finish;end
   else $fatal(1,"KEY_EPOCH_FAULT epoch=%0d rf=%b nf=%b bf=%b",epoch,rf,nf,bf);
  end
 end
 task automatic launch_run(input integer b_,input integer n_,input integer a_);
  @(negedge clk);dbase=12'(b_);dlimit=13'(b_+n_);loops=16'(a_+1);descv=1;
  @(negedge clk);descv=0;repeat(6)@(negedge clk);
  launch=1;@(negedge clk);launch=0;repeat(8)@(negedge clk);
 endtask
 task automatic nonkey(input integer b_,input integer n_,input integer a_);
  launch_run(b_,n_,a_);
  if(clear_count!=0)$fatal(1,"KEY_EPOCH_NONKEY_CLEARED");
 endtask
 initial begin
  integer r;reg[1098:0]v;reg[4395:0]expected;
  void'($value$plusargs("MUT=%d",mut));repeat(4)@(negedge clk);rst=1;repeat(8)@(negedge clk);
  nonkey(15,6,'h12);nonkey(16,5,'h12);nonkey(16,6,'h22);
  for(epoch=1;epoch<=2;epoch++)begin
   launch_run(16,6,'h11+epoch);repeat(12)@(negedge clk);
   for(integer c=0;c<2;c++)begin
    cohort=1'(c);
    for(integer t=0;t<695;t++)begin
     @(negedge clk);iv=0;
     for(integer p=0;p<4;p++)begin
      r=(t-2*p)/4;
      if(t>=2*p&&(t-2*p)%4==0&&r<171)begin
       iv[p]=1;rows[p]=8'(r);v=value(r,p,epoch,c);packets[p]={v[0],v[10:1],v[1098:11]};
      end
     end
    end
    @(negedge clk);iv=0;repeat(12)@(negedge clk);
   end
   if(loaded!=2'b11)$fatal(1,"KEY_EPOCH_NOT_LOADED");
   if(clear_count!=epoch)$fatal(1,"KEY_EPOCH_CLEAR_COUNT actual=%0d expected=%0d",clear_count,epoch);
   for(integer a=0;a<171;a++)begin
    @(negedge clk);pre=1;replay=0;address=8'(a);@(posedge clk);#1;
    @(negedge clk);pre=0;replay=1;#1;
    for(integer c=0;c<2;c++)begin
     for(integer p=0;p<4;p++)expected[p*1099+:1099]=value(a,p,epoch,c);
     if(out[c]!==expected)$fatal(1,"KEY_EPOCH_PAYLOAD epoch=%0d cohort=%0d row=%0d",epoch,c,a);
     checks+=4396;
    end
    @(posedge clk);#1;
   end
   @(negedge clk);pre=0;replay=0;repeat(12)@(negedge clk);
  end
  if(mut!=0)$fatal(1,"KEY_EPOCH_MUTANT_MISSED");
  $display("KEY_EPOCH_PASS recurringINDEX=2 clearcontrols=%0d payloadbits=%0d noreset_between=1",clear_count,checks);$finish;
 end
endmodule
