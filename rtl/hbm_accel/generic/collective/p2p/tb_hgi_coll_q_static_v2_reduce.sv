`timescale 1ns/1ps
module tb_hgi_coll_q_static_v2_reduce;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg [36:0] cfg=0;
 wire busy,done,fault;
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;
 wire [1023:0] inj_data;
 wire [3:0] dv;wire [2179:0] dd;wire [159:0] ob;
 wire [1:0] txv,retry;wire [1223:0] txd;
 wire [279:0] cwo,ccwo;wire [135:0] rq;wire [2247:0] kq;
 wire rv;wire [2:0] rt;wire [255:0] rdata;wire [31:0] cycles;
 reg [1535:0] code[0:35];reg [54:0] ar;
 reg [15:0] source_index[0:10];
 integer outputs=0,done_count=0;
 // Declared external SU boundary: requests are observed at P+1 and data is
 // stable before P+12. It supplies input vectors, never an internal DUT result.
 always @(posedge clk)begin
  source_index[0]<=inj_idx[15:0];
  for(integer p=1;p<11;p=p+1)source_index[p]<=source_index[p-1];
 end
 function automatic [511:0] source_word(input [15:0] index);
  begin
   for(integer l=0;l<16;l=l+1)source_word[l*32+:32]=(index==0?32'h3f800000:32'h40000000)+32'(l<<23);
  end
 endfunction
 assign inj_data={512'd0,source_word(source_index[10])};
 ot_hfd_coll_q2_static_v2 dut(.rst_n(rst_n),.clk_control(clk),.clk_issue({4{clk}}),
  .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_vmwrite(clk),.clk_link({10{clk}}),
  .qid(2'd1),.hgi_start(start),.hgi_start_pc(6'd0),.program_cfg(cfg),.hgi_busy(busy),.hgi_done(done),.hgi_fault(),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(inj_data),
  .del_valid(dv),.del_flit(dd),.hgi_del_obase(ob),.rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(rv),.rr_tag(rt),.rr_d(rdata),.phy_up(2'b11),.tx_pin_v(txv),.tx_pin_flit(txd),
  .rx_pin_v(2'b0),.rx_pin_flit(1224'd0),.retry_requested(retry),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .vm_rq(rq),.vm_rr(2056'd0),.vm_kq(kq),.fault(fault),.done(),.stat_cycles(cycles));
 task push(input [36:0] value);
  begin @(negedge clk);cfg=value;@(posedge clk);#1;end
 endtask
 task pack_ar(input integer row,input [54:0] control);
  begin code[row][1505+:31]=control[30:0];code[row][688+:24]=control[54:31];end
 endtask
 initial begin
  for(integer n=0;n<36;n=n+1)code[n]=0;
  code[0][90]=1;code[0][284+:33]={1'b1,8'hff,8'd0,16'd0};
  code[1][90]=1;code[1][92+:16]=16'd1;code[1][284+:33]={1'b1,8'hff,8'd1,16'd1};
  code[12][0]=1;code[13][0]=1;
  code[13][10+14]=1;code[13][26+14*4+:4]=0;
  code[14][10+14]=1;code[14][26+14*4+:4]=0;
  ar=0;ar[0]=1;ar[1+:4]=0;pack_ar(15,ar);
  ar=0;ar[5]=1;ar[6+:4]=0;pack_ar(16,ar);
  ar=0;ar[10]=1;pack_ar(MUT==2?18:17,ar);
  ar=0;ar[11]=1;ar[12+:4]=0;ar[21]=1;ar[23+:8]=8'd7;ar[31+:16]=16'd13;pack_ar(26,ar);
  ar=0;ar[22]=1;pack_ar(27,ar);
  code[28][8]=1;
  code[29][10+2]=1;code[29][26+2*4+:4]=(MUT==1?4'd7:4'd8);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<36;row=row+1)begin
   for(integer bank=0;bank<3;bank=bank+1)begin
    push({1'b1,4'd0,24'd0,2'(bank),6'(row)});
    for(integer frag=0;frag<16;frag=frag+1)push({1'b1,4'd1,code[row][bank*512+frag*32+:32]});
   end
   push({1'b1,4'd2,26'd0,6'(row+1)});
   push({1'b1,4'd3,32'(row==35 ? 4096 : 0)});
  end
  push(37'd0);repeat(4)@(negedge clk);
  @(negedge clk);start=1;@(posedge clk);#1;
  for(integer c=1;c<45;c=c+1)begin
   @(negedge clk);start=0;@(posedge clk);#1;
   if(fault)$fatal(1,"native V2 parent fault at compiled cycle%0d",c);
   if(dv!==(c==34?4'b0001:4'b0000))$fatal(1,"native reduction publication cycle%0d got%h",c,dv);
   if(c==34)begin
    if(dd[544:512]!=={1'b1,8'hff,8'd7,16'd13})$fatal(1,"native reduce metadata");
    for(integer l=0;l<16;l=l+1)if(dd[l*32+:32]!==32'h40400000+32'(l<<23))$fatal(1,"native FP32 sum lane%0d",l);
    outputs=outputs+1;
   end
   if(done!==(c==38))$fatal(1,"native issuer halt cycle%0d",c);
   if(done)done_count=done_count+1;
  end
  if(outputs!=1||done_count!=1)$fatal(1,"coverage");
  $display("HCOLL_Q2_V2_NATIVE_REDUCE PASS lanes16 FP32_TX2 sum_at_start34 halt38 actual_issuer1 reduce33roots ring17roots links2x612");
  $finish;
 end
endmodule
